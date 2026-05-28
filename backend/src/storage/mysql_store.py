import mysql.connector
import logging
from typing import List, Dict, Any, Optional
import os
import time

logger = logging.getLogger(__name__)

class MySQLStore:
    def __init__(self, host="localhost", port=3306, user="root", password="", database="code_intel"):
        self.config = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database
        }
        
        # Create a connection pool to avoid opening a new TCP connection on every query (which causes massive lag)
        import mysql.connector.pooling
        self.pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name="code_intel_pool",
            pool_size=10,
            pool_reset_session=True,
            **self.config
        )
        self._init_db()

    def _get_connection(self):
        return self.pool.get_connection()

    def _init_db(self):
        try:
            conn = mysql.connector.connect(
                host=self.config["host"],
                port=self.config["port"],
                user=self.config["user"],
                password=self.config["password"],
                database=self.config["database"]
            )
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.config['database']}")
            conn.close()

            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id VARCHAR(255) PRIMARY KEY,
                        username VARCHAR(255),
                        email VARCHAR(255),
                        full_name VARCHAR(255),
                        role VARCHAR(50),
                        bio TEXT,
                        password_hash VARCHAR(255),
                        status VARCHAR(50) DEFAULT 'ACTIVE',
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                ''')

                # Repositories table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS repositories (
                        id VARCHAR(255) PRIMARY KEY,
                        name TEXT,
                        url TEXT,
                        branch TEXT,
                        status TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Chunks table - Using FULLTEXT index for keyword search
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS chunks (
                        id VARCHAR(255) PRIMARY KEY,
                        repo_id VARCHAR(255),
                        file_path TEXT,
                        chunk_type TEXT,
                        symbol_name VARCHAR(255),
                        start_line INTEGER,
                        end_line INTEGER,
                        content_hash TEXT,
                        content MEDIUMTEXT,
                        FOREIGN KEY (repo_id) REFERENCES repositories (id),
                        FULLTEXT (symbol_name, content)
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS glossary_terms (
                        repo_id VARCHAR(255),
                        term VARCHAR(255),
                        definition TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        PRIMARY KEY (repo_id, term)
                    )
                ''')

                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS project_notes (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        repo_id VARCHAR(255),
                        note TEXT,
                        source_query TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                # Schema migrations for older DB instances
                try:
                    cursor.execute("ALTER TABLE users ADD COLUMN username VARCHAR(255)")
                except mysql.connector.Error as err:
                    if err.errno != 1060: # 1060 is Duplicate column name
                        logger.warning(f"Error adding username column: {err}")
                        
                try:
                    cursor.execute("ALTER TABLE users ADD COLUMN status VARCHAR(50) DEFAULT 'ACTIVE'")
                except mysql.connector.Error as err:
                    if err.errno != 1060:
                        logger.warning(f"Error adding status column: {err}")

                try:
                    cursor.execute("ALTER TABLE users ADD COLUMN bio TEXT")
                except mysql.connector.Error as err:
                    if err.errno != 1060:
                        logger.warning(f"Error adding bio column: {err}")

                try:
                    cursor.execute("ALTER TABLE repositories ADD COLUMN description TEXT")
                except mysql.connector.Error as err:
                    if err.errno != 1060:
                        logger.warning(f"Error adding description column: {err}")
                        
                try:
                    cursor.execute("ALTER TABLE repositories ADD COLUMN is_public BOOLEAN DEFAULT FALSE")
                except mysql.connector.Error as err:
                    if err.errno != 1060:
                        logger.warning(f"Error adding is_public column: {err}")

                try:
                    cursor.execute("ALTER TABLE repositories ADD COLUMN user_id VARCHAR(255)")
                except mysql.connector.Error as err:
                    if err.errno != 1060:
                        logger.warning(f"Error adding user_id column: {err}")
                        
                conn.commit()
                logger.info("MySQL Database initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize MySQL: {e}")
            raise

    def add_chunks(self, repo_id: str, chunks: List[Dict[str, Any]]):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for chunk in chunks:
                cursor.execute('''
                    INSERT INTO chunks 
                    (id, repo_id, file_path, chunk_type, symbol_name, start_line, end_line, content_hash, content)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                    file_path=VALUES(file_path), symbol_name=VALUES(symbol_name), content=VALUES(content)
                ''', (
                    chunk['chunk_id'], repo_id, chunk['file_path'], chunk['chunk_type'], 
                    chunk['symbol_name'], chunk['start_line'], chunk['end_line'], 
                    chunk['content_hash'], chunk['content']
                ))
            conn.commit()

    def keyword_search(self, repo_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            # Use MySQL Natural Language Mode for Fulltext search
            cursor.execute('''
                SELECT *, MATCH(symbol_name, content) AGAINST (%s) as score
                FROM chunks
                WHERE repo_id = %s AND MATCH(symbol_name, content) AGAINST (%s)
                ORDER BY score DESC
                LIMIT %s
            ''', (query, repo_id, query, top_k))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "chunk_id": row['id'],
                    "repo_id": row['repo_id'],
                    "file_path": row['file_path'],
                    "chunk_type": row['chunk_type'],
                    "symbol_name": row['symbol_name'],
                    "start_line": row['start_line'],
                    "end_line": row['end_line'],
                    "content": row['content'],
                    "score": row['score']
                })
            return results

    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM chunks WHERE id = %s', (chunk_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "chunk_id": row['id'],
                "repo_id": row['repo_id'],
                "file_path": row['file_path'],
                "chunk_type": row['chunk_type'],
                "symbol_name": row['symbol_name'],
                "start_line": row['start_line'],
                "end_line": row['end_line'],
                "content": row['content']
            }

    def get_repo(self, repo_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM repositories WHERE id = %s', (repo_id,))
            return cursor.fetchone()

    def list_repo_chunks(self, repo_id: str, limit: int = 5000) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('''
                SELECT id, repo_id, file_path, chunk_type, symbol_name, start_line, end_line
                FROM chunks
                WHERE repo_id = %s
                ORDER BY file_path ASC, start_line ASC
                LIMIT %s
            ''', (repo_id, limit))
            rows = cursor.fetchall()
            return [
                {
                    "chunk_id": row["id"],
                    "repo_id": row["repo_id"],
                    "file_path": row["file_path"],
                    "chunk_type": row["chunk_type"],
                    "symbol_name": row["symbol_name"],
                    "start_line": row["start_line"],
                    "end_line": row["end_line"],
                }
                for row in rows
            ]

    def upsert_glossary_term(self, repo_id: str, term: str, definition: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO glossary_terms (repo_id, term, definition)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE definition = VALUES(definition)
            ''', (repo_id, term, definition))
            conn.commit()

    def list_glossary_terms(self, repo_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('''
                SELECT term, definition, updated_at
                FROM glossary_terms
                WHERE repo_id = %s
                ORDER BY updated_at DESC
                LIMIT %s
            ''', (repo_id, limit))
            return cursor.fetchall()

    def delete_glossary_term(self, repo_id: str, term: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM glossary_terms WHERE repo_id = %s AND term = %s', (repo_id, term))
            conn.commit()

    def add_project_note(self, repo_id: str, note: str, source_query: Optional[str] = None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO project_notes (repo_id, note, source_query)
                VALUES (%s, %s, %s)
            ''', (repo_id, note, source_query))
            conn.commit()

    def list_project_notes(self, repo_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('''
                SELECT id, note, source_query, created_at
                FROM project_notes
                WHERE repo_id = %s
                ORDER BY created_at DESC, id DESC
                LIMIT %s
            ''', (repo_id, limit))
            return cursor.fetchall()

    def upsert_repo(self, repo_id: str, name: str, url: str, branch: str = "main", status: str = "READY", user_id: str = "system"):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO repositories (id, name, url, branch, status, user_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE name=VALUES(name), url=VALUES(url), branch=VALUES(branch), status=VALUES(status), user_id=VALUES(user_id)
            ''', (repo_id, name, url, branch, status, user_id))
            conn.commit()

    def list_repos(self, user_id: str = None, current_admin_id: str = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            query = '''
                SELECT r.*, u.email as uploader_email, u.full_name as uploader_name
                FROM repositories r
                LEFT JOIN users u ON r.user_id = u.id
            '''
            if current_admin_id:
                # Admins see all repos
                cursor.execute(f'{query} ORDER BY r.created_at DESC')
            elif user_id:
                # Users see only their repos (or global repos where user_id='system' if you want)
                cursor.execute(f"{query} WHERE r.user_id = %s OR r.user_id = 'system' OR r.user_id IS NULL ORDER BY r.created_at DESC", (user_id,))
            else:
                cursor.execute(f'{query} ORDER BY r.created_at DESC')
            return cursor.fetchall()

    def delete_repo(self, repo_id: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM project_notes WHERE repo_id = %s', (repo_id,))
            cursor.execute('DELETE FROM glossary_terms WHERE repo_id = %s', (repo_id,))
            cursor.execute('DELETE FROM chunks WHERE repo_id = %s', (repo_id,))
            cursor.execute('DELETE FROM repositories WHERE id = %s', (repo_id,))
            conn.commit()

    def create_user(self, email: str, password: str, full_name: str, role: str = "user") -> dict | None:
        import hashlib, uuid
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        user_id = uuid.uuid4().hex[:12]
        username = email.split("@")[0]
        
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id FROM users WHERE LOWER(email) = LOWER(%s)", (email,))
            if cursor.fetchone():
                return None
            
            cursor.execute('''
                INSERT INTO users (id, username, email, full_name, role, password_hash, bio, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (user_id, username, email.lower(), full_name, role, password_hash, '', 'ACTIVE'))
            conn.commit()
            
            cursor.execute("SELECT id, username, email, full_name, role, status FROM users WHERE id = %s", (user_id,))
            return cursor.fetchone()

    def authenticate_user(self, email: str, password: str) -> dict | None:
        import hashlib
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('''
                SELECT id, username, email, full_name, role, status
                FROM users
                WHERE LOWER(email) = LOWER(%s) AND password_hash = %s
            ''', (email, password_hash))
            return cursor.fetchone()

    def get_user_profile(self, user_id: str = 'default_user'):
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()
            return row if row else {}

    def list_users(self, limit: int = 200, current_admin_id: str = None):
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT id, username, email, full_name, role, bio, status, updated_at FROM users"
            params = []
            if current_admin_id:
                query += " WHERE role != 'admin' OR id = %s"
                params.append(current_admin_id)
            query += " ORDER BY updated_at DESC LIMIT %s"
            params.append(limit)
            cursor.execute(query, tuple(params))
            return cursor.fetchall()

    def update_user_status(self, user_id: str, status: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET status = %s WHERE id = %s", (status, user_id))
            conn.commit()

    def update_user_profile(self, user_id: str, profile_data: dict):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (id, username, email, full_name, role, bio, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON DUPLICATE KEY UPDATE
                    username = VALUES(username),
                    email = VALUES(email),
                    full_name = VALUES(full_name),
                    role = VALUES(role),
                    bio = VALUES(bio),
                    updated_at = CURRENT_TIMESTAMP
            ''', (
                user_id,
                profile_data.get('username') or 'user',
                profile_data.get('email'), 
                profile_data.get('full_name'),
                profile_data.get('role'),
                profile_data.get('bio')
            ))
            conn.commit()

    def log_query(self, repo_id: str, query: str, user_id: str = 'default_user', answer: str = ''):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS query_logs (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(255),
                    repo_id VARCHAR(255),
                    query TEXT,
                    answer TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                INSERT INTO query_logs (user_id, repo_id, query, answer)
                VALUES (%s, %s, %s, %s)
            ''', (user_id, repo_id, query, answer))
            conn.commit()

    def count_chunks(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM chunks')
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def list_query_logs(self, limit: int = 50, current_admin_id: str = None):
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS query_logs (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(255),
                    repo_id VARCHAR(255),
                    query TEXT,
                    answer TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            q = '''
                SELECT q.id, q.user_id, q.repo_id, q.query, q.created_at, u.full_name, u.email
                FROM query_logs q
                LEFT JOIN users u ON u.id = q.user_id
            '''
            params = []
            if current_admin_id:
                q += " WHERE (u.role != 'admin' OR u.id IS NULL OR q.user_id = %s)"
                params.append(current_admin_id)
            q += " ORDER BY q.created_at DESC, q.id DESC LIMIT %s"
            params.append(limit)
            cursor.execute(q, tuple(params))
            return cursor.fetchall()
            
    def list_query_logs_for_repo(self, repo_id: str, limit: int = 50):
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS query_logs (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(255),
                    repo_id VARCHAR(255),
                    query TEXT,
                    answer TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                SELECT q.id, q.user_id, q.repo_id, q.query, q.answer, q.created_at
                FROM query_logs q
                WHERE q.repo_id = %s
                ORDER BY q.created_at DESC, q.id DESC
                LIMIT %s
            ''', (repo_id, limit))
            return cursor.fetchall()

    def get_admin_overview(self, current_admin_id: str = None):
        repos = self.list_repos()
        users = self.list_users(current_admin_id=current_admin_id)
        queries = self.list_query_logs(limit=25, current_admin_id=current_admin_id)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            q = "SELECT COUNT(*) FROM query_logs q LEFT JOIN users u ON u.id = q.user_id"
            params = []
            if current_admin_id:
                q += " WHERE (u.role != 'admin' OR u.id IS NULL OR q.user_id = %s)"
                params.append(current_admin_id)
            try:
                cursor.execute(q, tuple(params))
                row = cursor.fetchone()
                total_queries = int(row[0]) if row else 0
            except:
                total_queries = 0

        status_counts = {"ready": 0, "pending": 0, "failed": 0}
        for repo in repos:
            status = (repo.get("status") or "").upper()
            if status == "READY": status_counts["ready"] += 1
            elif status == "FAILED": status_counts["failed"] += 1
            else: status_counts["pending"] += 1

        return {
            "total_users": len(users),
            "global_docs": len(repos),
            "personal_docs": status_counts["ready"],
            "total_queries": total_queries,
            "total_chunks": self.count_chunks(),
            "repo_status": status_counts,
            "recent_queries": queries
        }

    def count_query_logs(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM query_logs')
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def list_users_with_query_counts(self, limit: int = 200, current_admin_id: str = None):
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
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
                query += " WHERE u.role != 'admin' OR u.id = %s"
                params.append(current_admin_id)
                
            query += '''
                GROUP BY u.id
                ORDER BY total_queries DESC, u.updated_at DESC
                LIMIT %s
            '''
            params.append(limit)
            cursor.execute(query, tuple(params))
            return cursor.fetchall()

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM query_logs WHERE user_id = %s
            ''', (user_id,))
            row = cursor.fetchone()
            queries_count = row[0] if row else 0

            cursor.execute('''
                SELECT COUNT(*) FROM chunks c
                JOIN repositories r ON c.repo_id = r.id
                WHERE r.user_id = %s
            ''', (user_id,))
            row = cursor.fetchone()
            chunks_count = row[0] if row else 0
            
            return {
                "total_queries": queries_count,
                "total_chunks": chunks_count
            }

    def get_user_details(self, user_id: str):
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
            user_row = cursor.fetchone()
            if not user_row:
                return {}
            
            cursor.execute('''
                SELECT DISTINCT r.id, r.name, r.url, r.status
                FROM query_logs q
                JOIN repositories r ON r.id = q.repo_id
                WHERE q.user_id = %s
            ''', (user_id,))
            repos = cursor.fetchall()
            
            cursor.execute('''
                SELECT q.id, q.query, q.answer, q.created_at, r.name as repo_name
                FROM query_logs q
                LEFT JOIN repositories r ON r.id = q.repo_id
                WHERE q.user_id = %s
                ORDER BY q.created_at DESC
                LIMIT 50
            ''', (user_id,))
            queries = cursor.fetchall()
            
            return {
                "user": user_row,
                "repos": repos,
                "queries": queries
            }

    def get_system_settings(self):
        with self._get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_settings (
                    id VARCHAR(255) PRIMARY KEY,
                    ai_provider VARCHAR(255),
                    api_key VARCHAR(255),
                    model_name VARCHAR(255),
                    temperature FLOAT,
                    max_tokens INT,
                    chunk_size INT,
                    chunk_overlap INT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute("SELECT id FROM system_settings WHERE id = 'default_settings'")
            if not cursor.fetchone():
                cursor.execute('''
                    INSERT INTO system_settings (id, ai_provider, model_name, temperature, max_tokens, chunk_size, chunk_overlap)
                    VALUES ('default_settings', 'gemini', 'gemini-1.5-flash', 0.7, 4096, 1500, 150)
                ''')
                conn.commit()
                
            cursor.execute("SELECT * FROM system_settings WHERE id = 'default_settings'")
            row = cursor.fetchone()
            return row if row else {}

    def update_system_settings(self, settings_data: dict):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE system_settings 
                SET ai_provider = %s, api_key = %s, model_name = %s, temperature = %s, 
                    max_tokens = %s, chunk_size = %s, chunk_overlap = %s, updated_at = CURRENT_TIMESTAMP
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
