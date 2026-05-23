import os
import sqlite3

db_path = './storage/metadata.db'
os.makedirs(os.path.dirname(db_path), exist_ok=True)
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create users table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT,
        email TEXT,
        full_name TEXT,
        role TEXT,
        bio TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Seed default user
cursor.execute("SELECT id FROM users WHERE id = 'default_user'")
if not cursor.fetchone():
    cursor.execute('''
        INSERT INTO users (id, username, email, full_name, role, bio)
        VALUES ('default_user', 'User', 'user@codeintel.ai', 'New User', 'Developer', 'Joined Code Intelligence.')
    ''')
    print("Seeded default user")
else:
    print("Default user already exists")

conn.commit()
conn.close()
print("DB Initialized Successfully")
