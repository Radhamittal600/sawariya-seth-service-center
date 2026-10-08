import sqlite3
import requests
import re
from pathlib import Path

BASE = "http://127.0.0.1:8000"
COOKIE_FILE = Path("owner-cookies.txt")
DB = Path("sawariya.db")
HTML = Path("app/templates/owner.html")

PASS = 0
FAIL = 0
WARN = 0

def ok(name, detail=""):
    global PASS
    PASS += 1
    print(f"✅ PASS  {name}" + (f" — {detail}" if detail else ""))

def fail(name, detail=""):
    global FAIL
    FAIL += 1
    print(f"❌ FAIL  {name}" + (f" — {detail}" if detail else ""))

def warn(name, detail=""):
    global WARN
    WARN += 1
    print(f"⚠️ WARN  {name}" + (f" — {detail}" if detail else ""))

print("\n" + "="*65)
print("👑 SAWARIYA SETH — OWNER A-Z FULL DIAGNOSTIC")
print("="*65)

# ============================================================
# 1. FILE CHECK
# ============================================================

print("\n[1] PROJECT FILES")

for f in [
    "app/__init__.py",
    "app/templates/owner.html",
    "app/routes/owner_super.py",
    "sawariya.db",
    "run.py"
]:
    if Path(f).exists():
        ok(f"File exists: {f}")
    else:
        fail(f"Missing: {f}")

# ============================================================
# 2. PYTHON COMPILE
# ============================================================

print("\n[2] PYTHON COMPILE")

import subprocess

r = subprocess.run(
    ["python", "-m", "compileall", "-q", "app"],
    capture_output=True,
    text=True
)

if r.returncode == 0:
    ok("Python compile")
else:
    fail("Python compile", r.stderr[-1000:])

# ============================================================
# 3. DATABASE
# ============================================================

print("\n[3] DATABASE")

if not DB.exists():
    fail("SQLite database")
else:
    ok("SQLite database exists")

    try:
        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row

        tables = [
            "users",
            "services",
            "bookings",
            "products",
            "seller_products",
            "orders",
            "order_items",
            "payments",
            "commissions",
            "refunds",
            "complaints",
            "reviews",
            "notifications",
            "kyc_documents",
            "support_tickets",
            "audit_logs",
            "security_events",
            "app_settings",
            "owner_permissions"
        ]

        existing = {
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table'"
            ).fetchall()
        }

        for t in tables:
            if t in existing:
                ok(f"DB table: {t}")
            else:
                warn(f"DB table missing: {t}")

        # User counts
        for role in ["customer","technician","seller","owner"]:
            n = conn.execute(
                "SELECT COUNT(*) FROM users WHERE role=?",
                (role,)
            ).fetchone()[0]
            ok(f"{role} users", str(n))

        conn.close()

    except Exception as e:
        fail("Database read", str(e))

# ============================================================
# 4. OWNER COOKIE
# ============================================================

print("\n[4] OWNER SESSION")

cookies = {}

if COOKIE_FILE.exists():
    for line in COOKIE_FILE.read_text().splitlines():
        line=line.strip()
        if not line or line.startswith("#"):
            continue

        parts=line.split()

        if len(parts) >= 7:
            cookies[parts[5]] = parts[6]

    ok("owner-cookies.txt found")
else:
    fail("owner-cookies.txt missing")

# ============================================================
# 5. SERVER
# ============================================================

print("\n[5] SERVER")

try:
    r = requests.get(
        BASE + "/",
        timeout=5
    )

    if r.status_code < 500:
        ok("Server reachable", f"HTTP {r.status_code}")
    else:
        fail("Server reachable", f"HTTP {r.status_code}")

except Exception as e:
    fail("Server unreachable", str(e))
    print("\nServer start करो: python run.py")
    raise SystemExit

# ============================================================
# 6. OWNER PAGE
# ============================================================

print("\n[6] OWNER PAGE")

try:
    r = requests.get(
        BASE + "/owner",
        cookies=cookies,
        timeout=8
    )

    if r.status_code == 200:
        ok("/owner page", f"HTTP {r.status_code}")

        if "<!doctype" in r.text.lower() or "<html" in r.text.lower():
            ok("Owner HTML received")

        if "SAWARIYA" in r.text.upper():
            ok("Owner branding")

    elif r.status_code in [301,302]:
        warn(
            "/owner redirected",
            f"HTTP {r.status_code} → {r.headers.get('Location')}"
        )
    else:
        fail("/owner page", f"HTTP {r.status_code}")

except Exception as e:
    fail("/owner request", str(e))

# ============================================================
# 7. OWNER GET APIs
# ============================================================

print("\n[7] OWNER GET API TEST")

GET_APIS = [
    "/owner/master/summary",
    "/owner/master/users",
    "/owner/master/technicians",
    "/owner/master/sellers",
    "/owner/master/bookings",
    "/owner/master/products",
    "/owner/master/orders",
    "/owner/master/payments",
    "/owner/master/complaints",
    "/owner/master/reviews",
    "/owner/master/kyc",
    "/owner/master/support",
    "/owner/master/notifications",
    "/owner/master/security",
    "/owner/master/audit",

    "/owner/users",
    "/owner/users/summary",
    "/owner/technicians",
    "/owner/sellers",
    "/owner/bookings",
    "/owner/payments",
    "/owner/payments/summary",
    "/owner/pending-users",
    "/owner/security/events",
    "/owner/security/summary",
    "/owner/security/audit",
    "/owner/settings",
    "/owner/analytics/overview",
    "/owner/analytics/services",
    "/owner/analytics/technicians",
    "/owner/operations/active",
    "/owner/operations/technicians",
    "/owner/trust/summary",
    "/owner/trust/complaints",
    "/owner/trust/reviews",
    "/owner/trust/tickets",
    "/owner/marketplace/products",
    "/owner/marketplace/orders",

    "/owner/actions/refunds",

    "/owner/super/health",
    "/owner/super/api/summary",
    "/owner/super/api/users",
    "/owner/super/api/technicians",
    "/owner/super/api/sellers",
    "/owner/super/api/bookings",
    "/owner/super/api/products",
    "/owner/super/api/orders",
    "/owner/super/api/payments",
    "/owner/super/api/refunds",
    "/owner/super/api/complaints",
    "/owner/super/api/reviews",
    "/owner/super/api/kyc",
    "/owner/super/api/support",
    "/owner/super/api/notifications",
    "/owner/super/api/security",
    "/owner/super/api/audit",
    "/owner/super/api/permissions",
    "/owner/super/api/commissions",
    "/owner/super/api/services",
    "/owner/super/api/analytics",
    "/owner/super/api/settings"
]

for endpoint in GET_APIS:

    try:
        r = requests.get(
            BASE + endpoint,
            cookies=cookies,
            timeout=8
        )

        ct = r.headers.get("Content-Type","").lower()

        if r.status_code == 200:

            if "application/json" in ct:
                try:
                    r.json()
                    ok(endpoint, "JSON")
                except Exception:
                    fail(endpoint, "HTTP 200 but invalid JSON")
            else:
                warn(
                    endpoint,
                    f"HTTP 200 but Content-Type={ct}"
                )

        elif r.status_code in [401,403]:

            fail(
                endpoint,
                f"Owner authorization failed HTTP {r.status_code}"
            )

        elif r.status_code == 404:

            fail(
                endpoint,
                "404 route not found"
            )

        else:

            fail(
                endpoint,
                f"HTTP {r.status_code}"
            )

    except Exception as e:
        fail(endpoint, str(e))

# ============================================================
# 8. ACTION ROUTES — SAFE INVALID-ID TEST
# ============================================================

print("\n[8] ACTION ROUTES — SAFE TEST")

# Invalid ID means database is NOT modified.
ACTION_GETS = [
    ("POST", "/owner/super/user/999999999/approve", None),
    ("POST", "/owner/super/user/999999999/block", None),
    ("POST", "/owner/super/user/999999999/unblock", None),

    ("POST", "/owner/super/product/999999999/approve", None),
    ("POST", "/owner/super/product/999999999/reject", None),

    ("POST", "/owner/super/booking/999999999/status",
     {"status":"completed"}),

    ("POST", "/owner/super/booking/999999999/assign",
     {"technician_id":2}),

    ("POST", "/owner/super/order/999999999/status",
     {"status":"delivered"}),

    ("POST", "/owner/super/refund/999999999/approve", None),
    ("POST", "/owner/super/refund/999999999/reject", None),

    ("POST", "/owner/actions/product/999999999/approve", None),
    ("POST", "/owner/actions/product/999999999/reject", None),

    ("POST", "/owner/actions/refund/999999999/approve", None),
    ("POST", "/owner/actions/refund/999999999/reject", None)
]

for method, endpoint, payload in ACTION_GETS:

    try:

        if payload is None:
            r = requests.post(
                BASE + endpoint,
                cookies=cookies,
                timeout=8
            )
        else:
            r = requests.post(
                BASE + endpoint,
                json=payload,
                cookies=cookies,
                timeout=8
            )

        ct = r.headers.get("Content-Type","").lower()

        if "application/json" in ct:

            try:
                data=r.json()

                if r.status_code in [400,404]:
                    ok(
                        endpoint,
                        f"JSON action response HTTP {r.status_code}"
                    )
                elif r.status_code == 200:
                    warn(
                        endpoint,
                        "returned 200 for invalid ID"
                    )
                else:
                    warn(
                        endpoint,
                        f"HTTP {r.status_code}"
                    )

            except Exception:
                fail(
                    endpoint,
                    "JSON Content-Type but invalid JSON"
                )

        elif "<!doctype" in r.text.lower():

            fail(
                endpoint,
                "HTML returned instead of JSON"
            )

        else:

            warn(
                endpoint,
                f"HTTP {r.status_code}, Content-Type={ct}"
            )

    except Exception as e:
        fail(endpoint,str(e))

# ============================================================
# 9. FRONTEND OWNER HTML WIRING
# ============================================================

print("\n[9] OWNER FRONTEND WIRING")

if HTML.exists():

    s=HTML.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    required_strings = [
        "ownerAZOpen",
        "ownerAZProduct",
        "ownerAZUser",
        "ownerAZBooking",
        "ownerAZOrder",
        "ownerAZRefund",
        "SAWARIYA_OWNER_A_TO_Z_MASTER_UI",
        "/owner/super/",
        "Product Hub",
        "Security",
        "Notifications",
        "Permissions",
        "Marketplace"
    ]

    for item in required_strings:

        if item in s:
            ok("Frontend wiring", item)
        else:
            fail("Frontend wiring missing", item)

else:
    fail("owner.html not found")

# ============================================================
# 10. BAD HTML-AS-JSON DETECTION
# ============================================================

print("\n[10] JSON SAFETY")

bad_patterns = [
    "response.json()",
    ".json()"
]

# We cannot say every .json() is bad; just report count.
if HTML.exists():

    count = s.count(".json()")

    if count:
        warn(
            "Frontend JSON parser usage",
            f"{count} occurrence(s) — endpoints should return JSON"
        )
    else:
        ok("No direct .json() parser found")

# ============================================================
# 11. OWNER SUPER BLUEPRINT
# ============================================================

print("\n[11] OWNER SUPER BACKEND")

super_file=Path("app/routes/owner_super.py")

if super_file.exists():

    ss=super_file.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    for item in [
        "owner_super_bp",
        "owner_only",
        "/health",
        "/api/summary",
        "/api/users",
        "/api/products",
        "/product/<int:product_id>/<action>",
        "/booking/<int:booking_id>/assign",
        "/refund/<int:refund_id>/<action>"
    ]:

        if item in ss:
            ok("Backend feature", item)
        else:
            fail("Backend feature missing", item)

else:
    fail("owner_super.py missing")

# ============================================================
# 12. FINAL REPORT
# ============================================================

print("\n" + "="*65)
print("👑 FINAL OWNER WEBSITE TEST REPORT")
print("="*65)

print(f"✅ PASS : {PASS}")
print(f"⚠️ WARN : {WARN}")
print(f"❌ FAIL : {FAIL}")

if FAIL == 0:
    print("\n🎉 OWNER BACKEND TEST: PASS")
    print("All tested Owner routes are responding correctly.")
else:
    print("\n🚨 OWNER BACKEND TEST: PROBLEMS FOUND")
    print("ऊपर जिन lines में ❌ FAIL है वही पहले fix करनी हैं.")

if WARN:
    print("\n⚠️ WARNINGS मौजूद हैं — उन्हें भी review करना चाहिए.")

print("="*65)

# Save report marker
Path("OWNER_TEST_RESULT.txt").write_text(
    f"PASS={PASS}\nWARN={WARN}\nFAIL={FAIL}\n",
    encoding="utf-8"
)

print("\nReport saved: OWNER_TEST_RESULT.txt")
