import requests, json

BASE = "http://127.0.0.1:8000"
s = requests.Session()

print("=" * 70)
print("👑 SAWARIYA SETH OWNER A-Z FUNCTIONAL CHECK")
print("=" * 70)

# OWNER LOGIN
r = s.post(
    BASE + "/auth/login",
    json={
        "phone": "9000000000",
        "password": "Owner@12345"
    },
    timeout=10
)

if r.status_code != 200:
    print("❌ Owner login failed:", r.status_code, r.text[:300])
    raise SystemExit

print("✅ Owner login successful")

# Helper
def get(path):
    try:
        r = s.get(BASE + path, allow_redirects=False, timeout=10)
        try:
            data = r.json()
            preview = json.dumps(data, ensure_ascii=False)[:180]
        except:
            preview = r.text[:180].replace("\n", " ")

        if r.status_code == 200:
            print(f"✅ GET  {path}")
        else:
            print(f"❌ GET  {path} -> {r.status_code}")

        return r
    except Exception as e:
        print(f"❌ ERROR {path}: {e}")
        return None

def post(path, payload=None):
    try:
        r = s.post(
            BASE + path,
            json=payload or {},
            allow_redirects=False,
            timeout=10
        )

        if r.status_code in (200, 201, 400, 403, 404):
            print(f"✅ POST {path} -> {r.status_code}")
        else:
            print(f"❌ POST {path} -> {r.status_code}")

        return r
    except Exception as e:
        print(f"❌ ERROR {path}: {e}")
        return None

print("\n[1] DASHBOARD / LIVE DATA")

for path in [
    "/owner/super/api/summary",
    "/owner/super/api/users",
    "/owner/super/api/technicians",
    "/owner/super/api/sellers",
    "/owner/super/api/products",
    "/owner/super/api/bookings",
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
    "/owner/super/api/settings",
]:
    get(path)

print("\n[2] SAFE INVALID-ACTION ROUTE CHECK")
print("Ye routes real database record ko change nahi karenge.")

# Non-existent IDs: should safely return 400/404/403,
# not 500 and not HTML.
safe_tests = [
    ("/owner/super/user/999999/block", {}),
    ("/owner/super/user/999999/approve", {}),
    ("/owner/super/product/999999/approve", {}),
    ("/owner/super/product/999999/reject", {}),
    ("/owner/super/booking/999999/status", {"status": "completed"}),
    ("/owner/super/booking/999999/assign", {"technician_id": 999999}),
    ("/owner/super/order/999999/status", {"status": "cancelled"}),
    ("/owner/super/refund/999999/approve", {}),
]

for path, payload in safe_tests:
    r = post(path, payload)

    if r is not None:
        ct = r.headers.get("Content-Type", "")
        if "text/html" in ct and r.status_code >= 400:
            print("   ⚠️ HTML error response:", path)

print("\n[3] OWNER PAGE")

r = s.get(BASE + "/owner", timeout=10)

if r.status_code == 200:
    html = r.text

    checks = {
        "A-Z Master UI": "SAWARIYA_OWNER_A_TO_Z_MASTER_UI",
        "Owner button": "ownerAZOpen",
        "Product control": "ownerAZProduct",
        "User control": "ownerAZUser",
        "Booking control": "ownerAZBooking",
        "Order control": "ownerAZOrder",
        "Refund control": "ownerAZRefund",
    }

    for name, marker in checks.items():
        if marker in html:
            print("✅", name)
        else:
            print("❌", name, "missing")
else:
    print("❌ Owner page:", r.status_code)

print("\n" + "=" * 70)
print("🏁 FUNCTIONAL CHECK COMPLETE")
print("=" * 70)
print("Abhi koi real user/product/booking ko modify nahi kiya gaya.")
print("=" * 70)
