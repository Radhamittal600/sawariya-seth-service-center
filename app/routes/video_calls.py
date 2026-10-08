
from flask import Blueprint, jsonify, request
from datetime import datetime, time

from app.auth import get_current_user, role_required
from app.database.db import get_db

video_bp = Blueprint("video", __name__, url_prefix="/video")


# =========================================================
# HELPERS
# =========================================================

def current_user():
    return get_current_user()


def allowed_video_time():
    """
    Video calling allowed only between 07:00 and 20:00.
    Server-side restriction.
    """
    now = datetime.now().time()
    return time(7, 0) <= now <= time(20, 0)


def json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def active_call_exists(conn, technician_id, booking_id):
    row = conn.execute("""
        SELECT id
        FROM video_calls
        WHERE technician_id = ?
          AND booking_id = ?
          AND status IN ('requested','accepted')
        LIMIT 1
    """, (technician_id, booking_id)).fetchone()

    return row


# =========================================================
# TECHNICIAN PERMISSIONS
# =========================================================

@video_bp.get("/permissions")
@role_required("technician")
def get_permissions():

    user = current_user()

    conn = get_db()

    row = conn.execute("""
        SELECT camera_enabled, mic_enabled, updated_at
        FROM video_permissions
        WHERE technician_id = ?
    """, (user["id"],)).fetchone()

    if not row:
        conn.execute("""
            INSERT INTO video_permissions
            (technician_id, camera_enabled, mic_enabled, updated_at)
            VALUES (?,0,0,?)
        """, (
            user["id"],
            datetime.utcnow().isoformat()
        ))

        conn.commit()

        row = {
            "camera_enabled": 0,
            "mic_enabled": 0,
            "updated_at": datetime.utcnow().isoformat()
        }

    conn.close()

    return jsonify({
        "camera_enabled": bool(row["camera_enabled"]),
        "mic_enabled": bool(row["mic_enabled"]),
        "updated_at": row["updated_at"]
    })


@video_bp.post("/permissions")
@role_required("technician")
def update_permissions():

    user = current_user()
    data = json_body()

    camera = data.get("camera_enabled")
    mic = data.get("mic_enabled")

    conn = get_db()

    existing = conn.execute("""
        SELECT technician_id
        FROM video_permissions
        WHERE technician_id = ?
    """, (user["id"],)).fetchone()

    if existing:

        if camera is None and mic is None:
            conn.close()
            return jsonify({"error": "No permission change supplied"}), 400

        if camera is None:
            camera = conn.execute("""
                SELECT camera_enabled
                FROM video_permissions
                WHERE technician_id = ?
            """, (user["id"],)).fetchone()["camera_enabled"]

        if mic is None:
            mic = conn.execute("""
                SELECT mic_enabled
                FROM video_permissions
                WHERE technician_id = ?
            """, (user["id"],)).fetchone()["mic_enabled"]

        conn.execute("""
            UPDATE video_permissions
            SET camera_enabled = ?,
                mic_enabled = ?,
                updated_at = ?
            WHERE technician_id = ?
        """, (
            1 if bool(camera) else 0,
            1 if bool(mic) else 0,
            datetime.utcnow().isoformat(),
            user["id"]
        ))

    else:

        conn.execute("""
            INSERT INTO video_permissions
            (technician_id,camera_enabled,mic_enabled,updated_at)
            VALUES (?,?,?,?)
        """, (
            user["id"],
            1 if bool(camera) else 0,
            1 if bool(mic) else 0,
            datetime.utcnow().isoformat()
        ))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Video permissions updated",
        "camera_enabled": bool(camera),
        "mic_enabled": bool(mic)
    })


# =========================================================
# REQUEST VIDEO CALL
# =========================================================

@video_bp.post("/request")
def request_call():

    user = current_user()

    if not user:
        return jsonify({"error": "Login required"}), 401

    if user["role"] not in ("customer", "owner"):
        return jsonify({
            "error": "Only customer or owner can start a video call"
        }), 403

    if not allowed_video_time():
        return jsonify({
            "error": "Video calling is available only from 7:00 AM to 8:00 PM"
        }), 403

    data = json_body()

    try:
        booking_id = int(data.get("booking_id"))
        technician_id = int(data.get("technician_id"))
    except (TypeError, ValueError):
        return jsonify({
            "error": "Invalid booking_id or technician_id"
        }), 400

    conn = get_db()

    booking = conn.execute("""
        SELECT id, customer_id, technician_id, status
        FROM bookings
        WHERE id = ?
    """, (booking_id,)).fetchone()

    if not booking:
        conn.close()
        return jsonify({"error": "Booking not found"}), 404

    # Customer can only call on their own booking.
    if user["role"] == "customer":
        if booking["customer_id"] != user["id"]:
            conn.close()
            return jsonify({"error": "Permission denied"}), 403

    # Technician must actually be assigned to booking.
    if booking["technician_id"] != technician_id:
        conn.close()
        return jsonify({
            "error": "This technician is not assigned to this booking"
        }), 403

    technician = conn.execute("""
        SELECT id, role, status
        FROM users
        WHERE id = ?
    """, (technician_id,)).fetchone()

    if not technician or technician["role"] != "technician":
        conn.close()
        return jsonify({"error": "Technician not found"}), 404

    if technician["status"] != "approved":
        conn.close()
        return jsonify({
            "error": "Technician is not approved"
        }), 403

    # Technician must explicitly enable camera.
    permission = conn.execute("""
        SELECT camera_enabled, mic_enabled
        FROM video_permissions
        WHERE technician_id = ?
    """, (technician_id,)).fetchone()

    if not permission or not permission["camera_enabled"]:
        conn.close()
        return jsonify({
            "error": "Technician has not enabled video permission"
        }), 403

    # Prevent duplicate active calls.
    existing = active_call_exists(
        conn,
        technician_id,
        booking_id
    )

    if existing:
        call_id = existing["id"]
        conn.close()

        return jsonify({
            "message": "Active video call already exists",
            "call_id": call_id
        })

    now = datetime.utcnow().isoformat()

    cur = conn.execute("""
        INSERT INTO video_calls
        (booking_id,caller_id,technician_id,status,created_at)
        VALUES (?,?,?,?,?)
    """, (
        booking_id,
        user["id"],
        technician_id,
        "requested",
        now
    ))

    call_id = cur.lastrowid

    conn.execute("""
        INSERT OR IGNORE INTO video_signals
        (call_id,offer,answer,caller_candidates,technician_candidates,updated_at)
        VALUES (?,?,?,?,?,?)
    """, (
        call_id,
        None,
        None,
        "[]",
        "[]",
        now
    ))

    # Notification for technician.
    conn.execute("""
        INSERT INTO notifications
        (user_id,title,message,created_at)
        VALUES (?,?,?,?)
    """, (
        technician_id,
        "Incoming Video Call",
        f"New video call request for booking #{booking_id}",
        now
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Video call requested",
        "call_id": call_id,
        "status": "requested"
    }), 201


# =========================================================
# INCOMING CALLS
# =========================================================

@video_bp.get("/incoming")
@role_required("technician")
def incoming_calls():

    user = current_user()

    conn = get_db()

    rows = conn.execute("""
        SELECT
            vc.id,
            vc.booking_id,
            vc.caller_id,
            vc.status,
            vc.created_at,
            u.name AS caller_name
        FROM video_calls vc
        LEFT JOIN users u
            ON u.id = vc.caller_id
        WHERE vc.technician_id = ?
          AND vc.status = 'requested'
        ORDER BY vc.id DESC
    """, (user["id"],)).fetchall()

    conn.close()

    calls = []

    for row in rows:
        calls.append({
            "id": row["id"],
            "booking_id": row["booking_id"],
            "caller_id": row["caller_id"],
            "caller_name": row["caller_name"],
            "status": row["status"],
            "created_at": row["created_at"]
        })

    return jsonify({
        "calls": calls
    })


# =========================================================
# ACCEPT
# =========================================================

@video_bp.post("/accept/<int:call_id>")
@role_required("technician")
def accept_call(call_id):

    user = current_user()

    if not allowed_video_time():
        return jsonify({
            "error": "Video calling is available only from 7:00 AM to 8:00 PM"
        }), 403

    conn = get_db()

    call = conn.execute("""
        SELECT id, technician_id, status
        FROM video_calls
        WHERE id = ?
    """, (call_id,)).fetchone()

    if not call:
        conn.close()
        return jsonify({"error": "Call not found"}), 404

    if call["technician_id"] != user["id"]:
        conn.close()
        return jsonify({"error": "Permission denied"}), 403

    if call["status"] != "requested":
        conn.close()
        return jsonify({
            "error": "Call is no longer waiting"
        }), 400

    permission = conn.execute("""
        SELECT camera_enabled, mic_enabled
        FROM video_permissions
        WHERE technician_id = ?
    """, (user["id"],)).fetchone()

    if not permission or not permission["camera_enabled"]:
        conn.close()
        return jsonify({
            "error": "Enable camera permission first"
        }), 403

    conn.execute("""
        UPDATE video_calls
        SET status = 'accepted',
            started_at = ?
        WHERE id = ?
    """, (
        datetime.utcnow().isoformat(),
        call_id
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Call accepted",
        "call_id": call_id,
        "status": "accepted"
    })


# =========================================================
# REJECT
# =========================================================

@video_bp.post("/reject/<int:call_id>")
@role_required("technician")
def reject_call(call_id):

    user = current_user()

    conn = get_db()

    call = conn.execute("""
        SELECT id, technician_id, status
        FROM video_calls
        WHERE id = ?
    """, (call_id,)).fetchone()

    if not call:
        conn.close()
        return jsonify({"error": "Call not found"}), 404

    if call["technician_id"] != user["id"]:
        conn.close()
        return jsonify({"error": "Permission denied"}), 403

    if call["status"] != "requested":
        conn.close()
        return jsonify({
            "error": "Call cannot be rejected now"
        }), 400

    conn.execute("""
        UPDATE video_calls
        SET status = 'rejected',
            ended_at = ?
        WHERE id = ?
    """, (
        datetime.utcnow().isoformat(),
        call_id
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Call rejected",
        "call_id": call_id
    })


# =========================================================
# END CALL
# =========================================================

@video_bp.post("/end/<int:call_id>")
def end_call(call_id):

    user = current_user()

    if not user:
        return jsonify({"error": "Login required"}), 401

    conn = get_db()

    call = conn.execute("""
        SELECT id, caller_id, technician_id, status
        FROM video_calls
        WHERE id = ?
    """, (call_id,)).fetchone()

    if not call:
        conn.close()
        return jsonify({"error": "Call not found"}), 404

    if user["id"] not in (
        call["caller_id"],
        call["technician_id"]
    ):
        conn.close()
        return jsonify({"error": "Permission denied"}), 403

    conn.execute("""
        UPDATE video_calls
        SET status = 'ended',
            ended_at = ?
        WHERE id = ?
    """, (
        datetime.utcnow().isoformat(),
        call_id
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Call ended"
    })


# =========================================================
# SIGNALING
# =========================================================

@video_bp.get("/signal/<int:call_id>")
def get_signal(call_id):

    user = current_user()

    if not user:
        return jsonify({"error": "Login required"}), 401

    conn = get_db()

    call = conn.execute("""
        SELECT caller_id, technician_id, status
        FROM video_calls
        WHERE id = ?
    """, (call_id,)).fetchone()

    if not call:
        conn.close()
        return jsonify({"error": "Call not found"}), 404

    if user["id"] not in (
        call["caller_id"],
        call["technician_id"]
    ):
        conn.close()
        return jsonify({"error": "Permission denied"}), 403

    if call["status"] not in ("requested", "accepted"):
        conn.close()
        return jsonify({
            "error": "Call is not active"
        }), 400

    signal = conn.execute("""
        SELECT
            offer,
            answer,
            caller_candidates,
            technician_candidates,
            updated_at
        FROM video_signals
        WHERE call_id = ?
    """, (call_id,)).fetchone()

    conn.close()

    if not signal:
        return jsonify({
            "offer": None,
            "answer": None,
            "caller_candidates": [],
            "technician_candidates": []
        })

    import json

    try:
        caller_candidates = json.loads(
            signal["caller_candidates"] or "[]"
        )
    except Exception:
        caller_candidates = []

    try:
        technician_candidates = json.loads(
            signal["technician_candidates"] or "[]"
        )
    except Exception:
        technician_candidates = []

    return jsonify({
        "offer": signal["offer"],
        "answer": signal["answer"],
        "caller_candidates": caller_candidates,
        "technician_candidates": technician_candidates,
        "updated_at": signal["updated_at"]
    })


@video_bp.post("/signal/<int:call_id>")
def update_signal(call_id):

    user = current_user()

    if not user:
        return jsonify({"error": "Login required"}), 401

    data = json_body()

    conn = get_db()

    call = conn.execute("""
        SELECT caller_id, technician_id, status
        FROM video_calls
        WHERE id = ?
    """, (call_id,)).fetchone()

    if not call:
        conn.close()
        return jsonify({"error": "Call not found"}), 404

    if user["id"] not in (
        call["caller_id"],
        call["technician_id"]
    ):
        conn.close()
        return jsonify({"error": "Permission denied"}), 403

    if call["status"] not in ("requested", "accepted"):
        conn.close()
        return jsonify({
            "error": "Call is not active"
        }), 400

    import json

    signal = conn.execute("""
        SELECT
            offer,
            answer,
            caller_candidates,
            technician_candidates
        FROM video_signals
        WHERE call_id = ?
    """, (call_id,)).fetchone()

    if not signal:

        conn.execute("""
            INSERT INTO video_signals
            (call_id,offer,answer,caller_candidates,technician_candidates,updated_at)
            VALUES (?,?,?,?,?,?)
        """, (
            call_id,
            None,
            None,
            "[]",
            "[]",
            datetime.utcnow().isoformat()
        ))

        signal = {
            "offer": None,
            "answer": None,
            "caller_candidates": "[]",
            "technician_candidates": "[]"
        }

    offer = data.get("offer")
    answer = data.get("answer")

    caller_candidates = data.get("caller_candidates")
    technician_candidates = data.get("technician_candidates")

    if not isinstance(caller_candidates, list):
        caller_candidates = []

    if not isinstance(technician_candidates, list):
        technician_candidates = []

    # Preserve existing candidates.
    try:
        old_caller = json.loads(
            signal["caller_candidates"] or "[]"
        )
    except Exception:
        old_caller = []

    try:
        old_technician = json.loads(
            signal["technician_candidates"] or "[]"
        )
    except Exception:
        old_technician = []

    if isinstance(data.get("caller_candidate"), dict):
        old_caller.append(
            data["caller_candidate"]
        )

    if isinstance(data.get("technician_candidate"), dict):
        old_technician.append(
            data["technician_candidate"]
        )

    if caller_candidates:
        old_caller.extend(caller_candidates)

    if technician_candidates:
        old_technician.extend(technician_candidates)

    # Remove duplicates by JSON representation.
    def unique(items):
        result = []
        seen = set()

        for item in items:
            try:
                key = json.dumps(
                    item,
                    sort_keys=True
                )
            except Exception:
                continue

            if key not in seen:
                seen.add(key)
                result.append(item)

        return result

    old_caller = unique(old_caller)
    old_technician = unique(old_technician)

    conn.execute("""
        UPDATE video_signals
        SET
            offer = COALESCE(?, offer),
            answer = COALESCE(?, answer),
            caller_candidates = ?,
            technician_candidates = ?,
            updated_at = ?
        WHERE call_id = ?
    """, (
        json.dumps(offer) if isinstance(offer, dict) else None,
        json.dumps(answer) if isinstance(answer, dict) else None,
        json.dumps(old_caller),
        json.dumps(old_technician),
        datetime.utcnow().isoformat(),
        call_id
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Signal updated"
    })
