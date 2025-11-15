import sqlite3

conn = sqlite3.connect("users.db")
cur = conn.cursor()

cur.execute("SELECT id, username, email FROM users")
rows = cur.fetchall()

for row in rows:
    print("ID:", row[0], " | Username:", row[1], " | Email:", row[2])

conn.close()
