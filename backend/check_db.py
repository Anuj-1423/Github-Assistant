import sqlite3
import os

db_path = r"c:\Users\Ishaan\Documents\Codebase Knowledge AI\storage\metadata.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("--- Repositories ---")
cursor.execute("SELECT * FROM repositories")
for row in cursor.fetchall():
    print(row)

print("\n--- Users ---")
cursor.execute("SELECT * FROM users")
for row in cursor.fetchall():
    print(row)

conn.close()
