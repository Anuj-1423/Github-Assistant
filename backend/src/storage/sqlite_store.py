import sqlite3
from typing import List, Dict, Any, Optional
import os
import time

# Project root is 3 levels up from this file:
#   backend/src/storage/sqlite_store.py → backend/src/storage → backend/src → backend → project_root
_THIS_FILE = os.path.abspath(__file__)
_PROJECT_ROOT = os.path.dirname(  # project root
    os.path.dirname(              # backend
        os.path.dirname(          # backend/src
            os.path.dirname(_THIS_FILE)  # backend/src/storage
        )
    )
)
# Single canonical DB path — can be overridden via DB_PATH env var
_DEFAULT_DB_PATH = os.path.join(_PROJECT_ROOT, "storage", "metadata.db")

class SQLiteStore:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Prefer env var override, then fall back to project-relative default
            self.db_path = os.environ.get("DB_PATH") or _DEFAULT_DB_PATH
        else:
            self.db_path = db_path

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()


    def _init_db(self):
        """
        Initializes the SQLite database with FTS5 for keyword search.
        Following PRD Section 7.6 requirements.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Repositories table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS repositories (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    url TEXT,
                    branch TEXT,
                    status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_id TEXT DEFAULT 'system'
                )
            ''')
            
            # --- Migrations for older database schemas ---
            migrations = [
                'ALTER TABLE repositories ADD COLUMN user_id TEXT DEFAULT NULL',
                'ALTER TABLE users ADD COLUMN password_hash TEXT',
            ]
            for migration in migrations:
                try:
                    cursor.execute(migration)
                except sqlite3.OperationalError:
                    pass  # Column already exists

            # Chunks table for standard metadata
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    repo_id TEXT,
                    file_path TEXT,
                    chunk_type TEXT,
                    symbol_name TEXT,
                    start_line INTEGER,
                    end_line INTEGER,
                    content_hash TEXT,
                    FOREIGN KEY (repo_id) REFERENCES repositories (id)
                )
            ''')

            # Virtual Table for Full-Text Search (FTS5)
            # This handles exact keyword matching for symbols and code
            cursor.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS code_search USING fts5(
                    chunk_id UNINDEXED,
                    repo_id UNINDEXED,
                    symbol_name,
                    content,
                    tokenize='porter'
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS glossary_terms (
                    repo_id TEXT,
                    term TEXT,
                    definition TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (repo_id, term)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS project_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo_id TEXT,
                    note TEXT,
                    source_query TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS query_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    repo_id TEXT,
                    query TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Users table for profile management
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT,
                    email TEXT,
                    full_name TEXT,
                    role TEXT,
                    bio TEXT,
                    password_hash TEXT,
                    status TEXT DEFAULT 'ACTIVE',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # System Settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_settings (
                    id TEXT PRIMARY KEY,
                    ai_provider TEXT,
                    api_key TEXT,
                    model_name TEXT,
                    temperature REAL,
                    max_tokens INTEGER,
                    chunk_size INTEGER,
                    chunk_overlap INTEGER,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Initialize default settings if not exists
            cursor.execute("SELECT id FROM system_settings WHERE id = 'default_settings'")
            if not cursor.fetchone():
                cursor.execute('''
                    INSERT INTO system_settings (id, ai_provider, model_name, temperature, max_tokens, chunk_size, chunk_overlap)
                    VALUES ('default_settings', 'gemini', 'gemini-1.5-flash', 0.7, 4096, 1500, 150)
                ''')

            # Ensure a default user exists so profile/admin pages always have baseline data
            cursor.execute("SELECT id FROM users WHERE id = 'default_user'")
            if not cursor.fetchone():
                cursor.execute('''
                    INSERT INTO users (id, username, email, full_name, role, bio)
                    VALUES ('default_user', 'user', 'user@codeintel.ai', 'New User', 'Developer', 'Joined Code Intelligence.')
                ''')
            
            conn.commit()

    def add_chunks(self, repo_id: str, chunks: List[Dict[str, Any]]):
        """
        Adds chunks to both the standard metadata table and the FTS index.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for chunk in chunks:
                # Use chunk_id from the object
                chunk_id = chunk['chunk_id']
                
                # Insert into metadata table
                cursor.execute('''
                    INSERT OR REPLACE INTO chunks 
                    (id, repo_id, file_path, chunk_type, symbol_name, start_line, end_line, content_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    chunk_id, repo_id, chunk['file_path'], chunk['chunk_type'], 
                    chunk['symbol_name'], chunk['start_line'], chunk['end_line'], chunk['content_hash']
                ))

                # Insert into FTS index
                cursor.execute('''
                    INSERT OR REPLACE INTO code_search (chunk_id, repo_id, symbol_name, content)
                    VALUES (?, ?, ?, ?)
                ''', (chunk_id, repo_id, chunk['symbol_name'], chunk['content']))
            
            conn.commit()

    def keyword_search(self, repo_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Performs keyword search using FTS5 BM25 ranking, and falls back to LIKE search 
        on file paths if no exact phrase matches are found.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 1. Try FTS5 phrase match
            clean_query = query.replace('"', '')
            formatted_query = f'"{clean_query}"'
            cursor.execute('''
                SELECT chunk_id, symbol_name, content, bm25(code_search) as rank
                FROM code_search
                WHERE code_search MATCH ? AND repo_id = ?
                ORDER BY rank
                LIMIT ?
            ''', (formatted_query, repo_id, top_k))
            
            results = []
            for row in cursor.fetchall():
                cursor.execute('SELECT * FROM chunks WHERE id = ?', (row[0],))
                meta = cursor.fetchone()
                if meta:
                    results.append({
                        "chunk_id": meta[0],
                        "repo_id": meta[1],
                        "file_path": meta[2],
                        "chunk_type": meta[3],
                        "symbol_name": meta[4],
                        "start_line": meta[5],
                        "end_line": meta[6],
                        "content": row[2],
                        "score": -row[3]
                    })
            
            # 2. If FTS5 fails (e.g. filename search like 'main.py'), fallback to LIKE
            if not results:
                like_query = f"%{query}%"
                cursor.execute('''
                    SELECT * FROM chunks 
                    WHERE repo_id = ? AND (file_path LIKE ? OR symbol_name LIKE ?)
                    LIMIT ?
                ''', (repo_id, like_query, like_query, top_k))
                
                for meta in cursor.fetchall():
                    # Get content from code_search
                    cursor.execute('SELECT content FROM code_search WHERE chunk_id = ?', (meta[0],))
                    content_row = cursor.fetchone()
                    content = content_row[0] if content_row else ""
                    results.append({
                        "chunk_id": meta[0],
                        "repo_id": meta[1],
                        "file_path": meta[2],
                        "chunk_type": meta[3],
                        "symbol_name": meta[4],
                        "start_line": meta[5],
                        "end_line": meta[6],
                        "content": content,
                        "score": 1.0 # arbitrary fallback score
                    })
                    
            return results

    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM chunks WHERE id = ?', (chunk_id,))
            meta = cursor.fetchone()
            if not meta:
                return None
            
            cursor.execute('SELECT content FROM code_search WHERE chunk_id = ?', (chunk_id,))
            content_row = cursor.fetchone()
            content = content_row[0] if content_row else ""
            
            return {
                "chunk_id": meta[0],
                "repo_id": meta[1],
                "file_path": meta[2],
                "chunk_type": meta[3],
                "symbol_name": meta[4],
                "start_line": meta[5],
                "end_line": meta[6],
                "content": content
            }

    def get_repo(self, repo_id: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM repositories WHERE id = ?', (repo_id,))
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "name": row[1],
                    "url": row[2],
                    "branch": row[3],
                    "status": row[4]
                }
            return None

    def list_repo_chunks(self, repo_id: str, limit: int = 5000) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, repo_id, file_path, chunk_type, symbol_name, start_line, end_line
                FROM chunks
                WHERE repo_id = ?
                ORDER BY file_path ASC, start_line ASC
                LIMIT ?
            ''', (repo_id, limit))
            rows = cursor.fetchall()

            results: List[Dict[str, Any]] = []
            for row in rows:
                results.append({
                    "chunk_id": row[0],
                    "repo_id": row[1],
                    "file_path": row[2],
                    "chunk_type": row[3],
                    "symbol_name": row[4],
                    "start_line": row[5],
                    "end_line": row[6],
                })
            return results

    def upsert_glossary_term(self, repo_id: str, term: str, definition: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO glossary_terms (repo_id, term, definition, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(repo_id, term)
                DO UPDATE SET definition = excluded.definition, updated_at = CURRENT_TIMESTAMP
            ''', (repo_id, term, definition))
            conn.commit()

    def list_glossary_terms(self, repo_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT term, definition, updated_at
                FROM glossary_terms
                WHERE repo_id = ?
                ORDER BY updated_at DESC
                LIMIT ?
            ''', (repo_id, limit))
            rows = cursor.fetchall()
            return [
                {"term": row[0], "definition": row[1], "updated_at": row[2]}
                for row in rows
            ]

    def delete_glossary_term(self, repo_id: str, term: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM glossary_terms WHERE repo_id = ? AND term = ?', (repo_id, term))
            conn.commit()

    def add_project_note(self, repo_id: str, note: str, source_query: Optional[str] = None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO project_notes (repo_id, note, source_query)
                VALUES (?, ?, ?)
            ''', (repo_id, note, source_query))
            conn.commit()

    def list_project_notes(self, repo_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, note, source_query, created_at
                FROM project_notes
                WHERE repo_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
            ''', (repo_id, limit))
            rows = cursor.fetchall()
            return [
                {
                    "id": row[0],
                    "note": row[1],
                    "source_query": row[2],
                    "created_at": row[3]
                }
                for row in rows
            ]

    def upsert_repo(self, repo_id: str, name: str, url: str, branch: str = "main", status: str = "READY", user_id: str = "system"):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO repositories (id, name, url, branch, status, user_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (repo_id, name, url, branch, status, user_id))
            conn.commit()

    def list_repos(self, user_id: str = None, current_admin_id: str = None) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = '''
                SELECT r.id, r.name, r.url, r.branch, r.status, r.created_at, r.user_id,
                       COALESCE((SELECT u.username FROM query_logs q JOIN users u ON u.id = q.user_id WHERE q.repo_id = r.id ORDER BY q.created_at ASC LIMIT 1), 'System Operator') as uploader_name
                FROM repositories r 
            '''
            params = []
            
            if user_id:
                query += ' WHERE r.user_id = ?'
                params.append(user_id)
            elif current_admin_id:
                query += '''
                    LEFT JOIN users u ON r.user_id = u.id
                    WHERE (u.role != 'admin' OR u.id IS NULL OR r.user_id = ?)
                '''
                params.append(current_admin_id)
                
            query += ' ORDER BY r.created_at DESC'
            
            cursor.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]

    def delete_repo(self, repo_id: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM repositories WHERE id = ?', (repo_id,))
            cursor.execute('DELETE FROM chunks WHERE repo_id = ?', (repo_id,))
            cursor.execute('DELETE FROM code_search WHERE repo_id = ?', (repo_id,))
            cursor.execute('DELETE FROM glossary_terms WHERE repo_id = ?', (repo_id,))
            cursor.execute('DELETE FROM project_notes WHERE repo_id = ?', (repo_id,))
            cursor.execute('DELETE FROM query_logs WHERE repo_id = ?', (repo_id,))
            conn.commit()

    def get_user_profile(self, user_id: str = 'default_user') -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {}

    def update_user_profile(self, user_id: str, profile_data: Dict[str, str]):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (id, username, email, full_name, role, bio, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    username = excluded.username,
                    email = excluded.email,
                    full_name = excluded.full_name,
                    role = excluded.role,
                    bio = excluded.bio,
                    updated_at = CURRENT_TIMESTAMP
            ''', (
                user_id,
                profile_data.get('username') or 'user',
                profile_data.get('email'), 
                profile_data.get('full_name'),
                profile_data.get('role'),
                profile_data.get('bio'),
            ))
            conn.commit()

    def list_users(self, limit: int = 200, current_admin_id: str = None) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = '''
                SELECT id, username, email, full_name, role, bio, status, updated_at
                FROM users
            '''
            params = []
            if current_admin_id:
                query += " WHERE role != 'admin' OR id = ?"
                params.append(current_admin_id)
                
            query += " ORDER BY updated_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]

    def create_user(self, email: str, password_hash: str, full_name: str, role: str = 'user') -> Optional[Dict[str, Any]]:
        user_id = email.split('@')[0] + "_" + str(int(time.time()))
        username = email.split('@')[0]
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                # We reuse 'bio' to store the password hash since there's no password column
                # In a real app we'd alter the table, but this works for isolation prototype
                cursor.execute('ALTER TABLE users ADD COLUMN password_hash TEXT')
            except sqlite3.OperationalError:
                pass
                
            try:
                cursor.execute('''
                    INSERT INTO users (id, username, email, full_name, role, password_hash, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE')
                ''', (user_id, username, email, full_name, role, password_hash))
                conn.commit()
                return {"id": user_id, "username": username, "email": email, "full_name": full_name, "role": role}
            except sqlite3.IntegrityError:
                return None

    def authenticate_user(self, email: str, password_hash: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            try:
                cursor.execute('SELECT * FROM users WHERE email = ? AND password_hash = ?', (email, password_hash))
                row = cursor.fetchone()
                if row:
                    return dict(row)
            except sqlite3.OperationalError:
                # If password_hash doesn't exist, fallback to insecure mock auth
                cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
            return None

    def log_query(self, repo_id: str, query: str, user_id: str = 'default_user', answer: str = ''):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('ALTER TABLE query_logs ADD COLUMN answer TEXT')
            except sqlite3.OperationalError:
                pass
            cursor.execute('''
                INSERT INTO query_logs (user_id, repo_id, query, answer)
                VALUES (?, ?, ?, ?)
            ''', (user_id, repo_id, query, answer))
            conn.commit()

    def count_chunks(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM chunks')
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def count_query_logs(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM query_logs')
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def list_query_logs(self, limit: int = 50, current_admin_id: str = None) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = '''
                SELECT q.id, q.user_id, q.repo_id, q.query, q.created_at, u.full_name, u.email
                FROM query_logs q
                LEFT JOIN users u ON u.id = q.user_id
            '''
            params = []
            if current_admin_id:
                query += " WHERE (u.role != 'admin' OR u.id IS NULL OR q.user_id = ?)"
                params.append(current_admin_id)
                
            query += " ORDER BY q.created_at DESC, q.id DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]

    def list_query_logs_for_repo(self, repo_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            try:
                cursor.execute('ALTER TABLE query_logs ADD COLUMN answer TEXT')
            except sqlite3.OperationalError:
                pass
            cursor.execute('''
                SELECT q.id, q.user_id, q.repo_id, q.query, q.answer, q.created_at
                FROM query_logs q
                WHERE q.repo_id = ?
                ORDER BY q.created_at DESC, q.id DESC
                LIMIT ?
            ''', (repo_id, limit))
            return [dict(row) for row in cursor.fetchall()]

    def list_users_with_query_counts(self, limit: int = 200, current_admin_id: str = None) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = '''
                SELECT 
                    u.id,
                    u.username,
                    u.email,
                    u.full_name,
                    u.role,
                    u.bio,
                    u.status,
                    u.updated_at,
                    COUNT(q.id) AS total_queries,
                    MAX(q.created_at) AS last_query_at
                FROM users u
                LEFT JOIN query_logs q ON q.user_id = u.id
            '''
            params = []
            if current_admin_id:
                query += " WHERE u.role != 'admin' OR u.id = ?"
                params.append(current_admin_id)
                
            query += '''
                GROUP BY u.id
                ORDER BY total_queries DESC, u.updated_at DESC
                LIMIT ?
            '''
            params.append(limit)
            
            cursor.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]

    def update_user_status(self, user_id: str, status: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET status = ? WHERE id = ?', (status, user_id))
            conn.commit()

    def get_user_details(self, user_id: str) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get user info
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            user_row = cursor.fetchone()
            if not user_row:
                return {}
            user = dict(user_row)
            
            # Get repos queried by this user
            cursor.execute('''
                SELECT DISTINCT r.id, r.name, r.url, r.status
                FROM query_logs q
                JOIN repositories r ON r.id = q.repo_id
                WHERE q.user_id = ?
            ''', (user_id,))
            repos = [dict(r) for r in cursor.fetchall()]
            
            # Get queries by this user
            cursor.execute('''
                SELECT q.id, q.query, q.answer, q.created_at, r.name as repo_name
                FROM query_logs q
                LEFT JOIN repositories r ON r.id = q.repo_id
                WHERE q.user_id = ?
                ORDER BY q.created_at DESC
                LIMIT 50
            ''', (user_id,))
            queries = [dict(q) for q in cursor.fetchall()]
            
            return {
                "user": user,
                "repos": repos,
                "queries": queries
            }

    def get_admin_overview(self, current_admin_id: str = None) -> Dict[str, Any]:
        repos = self.list_repos(current_admin_id=current_admin_id)
        users = self.list_users(current_admin_id=current_admin_id)
        queries = self.list_query_logs(limit=25, current_admin_id=current_admin_id)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            q = "SELECT COUNT(*) FROM query_logs q LEFT JOIN users u ON u.id = q.user_id"
            params = []
            if current_admin_id:
                q += " WHERE (u.role != 'admin' OR u.id IS NULL OR q.user_id = ?)"
                params.append(current_admin_id)
            cursor.execute(q, tuple(params))
            row = cursor.fetchone()
            total_queries = int(row[0]) if row else 0

        status_counts = {
            "ready": 0,
            "pending": 0,
            "failed": 0
        }

        for repo in repos:
            status = (repo.get("status") or "").upper()
            if status == "READY":
                status_counts["ready"] += 1
            elif status == "FAILED":
                status_counts["failed"] += 1
            else:
                status_counts["pending"] += 1

        return {
            "total_users": len(users),
            "global_docs": len(repos),
            "personal_docs": status_counts["ready"],
            "total_queries": total_queries,
            "total_chunks": self.count_chunks(),
            "repo_status": status_counts,
            "recent_queries": queries
        }

    def get_system_settings(self) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM system_settings WHERE id = 'default_settings'")
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {}

    def update_system_settings(self, settings_data: Dict[str, Any]):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE system_settings 
                SET ai_provider = ?, api_key = ?, model_name = ?, temperature = ?, 
                    max_tokens = ?, chunk_size = ?, chunk_overlap = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = 'default_settings'
            ''', (
                settings_data.get('ai_provider'),
                settings_data.get('api_key'),
                settings_data.get('model_name'),
                settings_data.get('temperature'),
                settings_data.get('max_tokens'),
                settings_data.get('chunk_size'),
                settings_data.get('chunk_overlap')
            ))
            conn.commit()

    def create_user(self, email: str, password: str, full_name: str, role: str = "user") -> dict | None:
        """Creates a new user. Returns None if email already exists."""
        import hashlib, uuid
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            # Check for existing email
            cursor.execute("SELECT id FROM users WHERE LOWER(email) = LOWER(?)", (email,))
            if cursor.fetchone():
                return None  # duplicate

            user_id = uuid.uuid4().hex[:12]
            username = email.split("@")[0]
            password_hash = hashlib.sha256(password.encode()).hexdigest()

            cursor.execute('''
                INSERT INTO users (id, username, email, full_name, role, password_hash, bio, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, email.lower(), full_name, role, password_hash, '', 'ACTIVE'))
            conn.commit()

            cursor.execute("SELECT id, username, email, full_name, role, status FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def authenticate_user(self, email: str, password: str) -> dict | None:
        """Verifies credentials. Returns user dict on success, None on failure."""
        import hashlib
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, email, full_name, role, status
                FROM users
                WHERE LOWER(email) = LOWER(?) AND password_hash = ?
            ''', (email, password_hash))
            row = cursor.fetchone()
            return dict(row) if row else None
