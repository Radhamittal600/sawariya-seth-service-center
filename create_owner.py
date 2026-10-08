from app.database.db import get_db, init_db
from app.auth import hash_password


NAME = "Sawariya Owner"
PHONE = "9000000000"
PASSWORD = "Owner@12345"


init_db()

conn = get_db()

existing = conn.execute(
    "SELECT id FROM users WHERE role = 'owner' LIMIT 1"
).fetchone()

if existing:
    print("OWNER ALREADY EXISTS")
else:
    conn.execute(
        """
        INSERT INTO users
        (name, phone, password_hash, role, status)
        VALUES (?, ?, ?, 'owner', 'approved')
        """,
        (NAME, PHONE, hash_password(PASSWORD)),
    )

    conn.commit()
    print("OWNER CREATED")
    print("PHONE:", PHONE)
    print("PASSWORD:", PASSWORD)

conn.close()
