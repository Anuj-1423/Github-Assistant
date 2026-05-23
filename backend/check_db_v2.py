import sqlite3
import os

# Check both possible locations
paths = [
    r"c:\Users\Ishaan\Documents\Codebase Knowledge AI\backend\storage\metadata.db",
    r"c:\Users\Ishaan\Documents\Codebase Knowledge AI\storage\metadata.db"
]

for db_path in paths:
    print(f"\n--- Checking {db_path} ---")
    if not os.path.exists(db_path):
        print("File not found")
        continue
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("--- Repositories ---")
    cursor.execute("SELECT id, name, status FROM repositories")
    for row in cursor.fetchall():
        print(row)

    print("\n--- Users ---")
    cursor.execute("SELECT * FROM users")
    for row in cursor.fetchall():
        print(row)

    conn.close()
