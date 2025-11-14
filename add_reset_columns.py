import sqlite3, os, sys

db_path = os.path.join(os.getcwd(), "users.db")
if not os.path.exists(db_path):
    print("ERROR: users.db not found at", db_path)
    sys.exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# list tables
tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("Tables in DB:", tables)

if 'users' not in tables:
    print("WARNING: 'users' table not found. Please send me the table names above.")
    conn.close()
    sys.exit(1)

cols = [c[1] for c in cur.execute("PRAGMA table_info(users)").fetchall()]
print("Existing columns:", cols)

if "reset_code_hash" not in cols:
    cur.execute("ALTER TABLE users ADD COLUMN reset_code_hash TEXT")
    print("Added: reset_code_hash")
else:
    print("Already exists: reset_code_hash")

if "reset_code_expiry" not in cols:
    cur.execute("ALTER TABLE users ADD COLUMN reset_code_expiry DATETIME")
    print("Added: reset_code_expiry")
else:
    print("Already exists: reset_code_expiry")

conn.commit()
conn.close()
print("DONE: Columns added or already existed.")
