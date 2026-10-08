import sqlite3
import requests
from pathlib import Path

BASE = "http://127.0.0.1:8000"
DB = Path("sawariya.db")
HTML = Path("app/templates/owner.html")
SUPER = Path("app/routes/owner_super.py")
INIT = Path("app/__init__.py")

P = 0
F = 0
W = 0

def PASS(x):
    global P
    P += 1
    print("✅ PASS:", x)

def FAIL(x):
    global F
    F += 1
    print("❌ FAIL:", x)

def WARN(x):
    global W
    W += 1
    print("⚠️ WARN:", x)

print()
print("=" * 60)
print("👑 SAWARIYA SETH OWNER A-Z CHECK")
print("=" * 60)

# -------------------------------------------------
# FILES
# -------------------------------------------------

print("\n[1] PROJECT FILES")

for f in [
    "run.py",
    "sawariya.db",
    "app/__init__.py",
    "app/templates/owner.html",
    "app/routes/owner_super.py"
]:
    if Path(f).exists():
        PASS(f)
    else:
        FAIL(f"Missing: {f}")

# -------------------------------------------------
# PYTHON COMPILE
# -------------------------------------------------

print("\n[2] PYTHON")

import subprocess

r = subprocess.run(
    ["python", "-m", "compileall", "-q", "app"],
    capture_output=True,
    text=True
)

if r.returncode == 0:
    PASS("Python compile")
else:
    FAIL("Python compile")
    print(r.stderr)

# -------------------------------------------------
# DATABASE
# -------------------------------------------------

print("\n[3] DATABASE")

try:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row

    integrity = con.execute(
        "PRAGMA integrity_check"
    ).fetchone()[0]

    if integrity == "ok":
        PASS("SQLite integrity")
    else:
        FAIL("SQLite integrity: " + str(integrity))

    tables = {
        x["name"]
        for x in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }

    required = [
        "users",
        "services",
        "bookings",
        "seller_products",
        "orders",
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

    for t in required:
        if t in tables:
            PASS("DB table: " + t)
        else:
            WARN("DB table missing: " + t)

    for role in [
        "customer",
        "technician",
        "seller",
        "owner"
    ]:
        n = con.execute(
            "SELECT COUNT(*) FROM users WHERE role=?",
            (role,)
        ).fetchone()[0]

        PASS(f"{role} count = {n}")

    con.close()

except Exception as e:
    FAIL("Database error: " + str(e))

# -------------------------------------------------
# SERVER
# -------------------------------------------------

print("\n[4] SERVER")

try:
    r = requests.get(
        BASE + "/",
        timeout=5
    )

    if r.status_code < 500:
        PASS("Server online HTTP " + str(r.status_code))
    else:
        FAIL("Server HTTP " + str(r.status_code))

except Exception as e:
    FAIL("Server not reachable: " + str(e))

# -------------------------------------------------
# OWNER PAGE
# -------------------------------------------------

print("\n[5] OWNER PAGE")

try:
    r = requests.get(
        BASE + "/owner",
        timeout=8
    )

    if r.status_code in [200, 302]:
        PASS("/owner responds HTTP " + str(r.status_code))
    else:
        FAIL("/owner HTTP " + str(r.status_code))

    html = r.text.lower()

    if "<html" in html:
        PASS("Owner HTML detected")
    else:
        WARN("Owner HTML tag not detected")

    if "sawariya" in html:
        PASS("Sawariya branding detected")

except Exception as e:
    FAIL("Owner page: " + str(e))

# -------------------------------------------------
# OWNER SUPER HEALTH
# -------------------------------------------------

print("\n[6] OWNER SUPER")

try:
    r = requests.get(
        BASE + "/owner/super/health",
        timeout=8
    )

    if r.status_code == 200:

        try:
            data = r.json()

            if data.get("ok") is True:
                PASS("Owner Super Health")
            else:
                FAIL("Owner Super returned bad response")

        except Exception:
            FAIL("Owner Super returned non-JSON")

    elif r.status_code == 302:
        WARN("Owner Super redirected to login")
    else:
        FAIL(
            "Owner Super HTTP " +
            str(r.status_code)
        )

except Exception as e:
    FAIL("Owner Super: " + str(e))

# -------------------------------------------------
# OWNER SUPER FILE
# -------------------------------------------------

print("\n[7] OWNER SUPER CODE")

if SUPER.exists():

    s = SUPER.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    checks = [
        "owner_super_bp",
        "owner_only",
        "/health",
        "/api/summary",
        "/api/users",
        "/api/technicians",
        "/api/sellers",
        "/api/products",
        "/api/bookings",
        "/api/orders",
        "/api/payments",
        "/api/refunds",
        "/api/complaints",
        "/api/reviews",
        "/api/kyc",
        "/api/support",
        "/api/notifications",
        "/api/security",
        "/api/audit",
        "/api/permissions",
        "/api/analytics",
        "/api/settings",
        "/product/<int:product_id>/<action>",
        "/booking/<int:booking_id>/status",
        "/booking/<int:booking_id>/assign",
        "/order/<int:order_id>/status",
        "/refund/<int:refund_id>/<action>"
    ]

    for x in checks:
        if x in s:
            PASS("Backend: " + x)
        else:
            FAIL("Backend missing: " + x)

else:
    FAIL("owner_super.py missing")

# -------------------------------------------------
# BLUEPRINT
# -------------------------------------------------

print("\n[8] BLUEPRINT")

if INIT.exists():

    s = INIT.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    if "owner_super" in s:
        PASS("Owner Super blueprint found")
    else:
        FAIL("Owner Super blueprint not registered")

# -------------------------------------------------
# FRONTEND
# -------------------------------------------------

print("\n[9] OWNER FRONTEND")

if HTML.exists():

    s = HTML.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    checks = [
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

    for x in checks:

        if x in s:
            PASS("Frontend: " + x)
        else:
            FAIL("Frontend missing: " + x)

    if len(s) > 10000:
        PASS("owner.html size OK")
    else:
        WARN("owner.html unusually small")

else:
    FAIL("owner.html missing")

# -------------------------------------------------
# OLD JSON ERROR DETECTION
# -------------------------------------------------

print("\n[10] JSON / HTML ERROR CHECK")

if HTML.exists():

    s = HTML.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    if "Unexpected token" in s:
        WARN("Unexpected token text exists in HTML")

    if "<!doctype" in s.lower():
        PASS("HTML document exists")

# -------------------------------------------------
# FINAL
# -------------------------------------------------

print()
print("=" * 60)
print("👑 FINAL A-Z OWNER TEST")
print("=" * 60)

print("✅ PASS :", P)
print("⚠️ WARN :", W)
print("❌ FAIL :", F)

print("=" * 60)

Path(
    "OWNER_AZ_RESULT.txt"
).write_text(
    f"PASS={P}\nWARN={W}\nFAIL={F}\n",
    encoding="utf-8"
)

if F == 0:
    print("🎉 OWNER SYSTEM BASIC A-Z CHECK PASSED")
else:
    print("🚨 OWNER SYSTEM में problems मिली हैं")

print("📄 Result: OWNER_AZ_RESULT.txt")
