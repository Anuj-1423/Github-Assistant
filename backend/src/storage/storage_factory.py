import os
import logging
from src.storage.sqlite_store import SQLiteStore
from src.storage.mysql_store import MySQLStore

logger = logging.getLogger(__name__)

_storage_instance = None

def get_storage():
    """
    Factory function to get the storage backend based on environment variables.
    Defaults to SQLite if MySQL is not configured or fails.
    Uses a singleton pattern to avoid re-initializing the database on every request.
    """
    global _storage_instance
    if _storage_instance is not None:
        return _storage_instance

    db_type = os.getenv("DB_TYPE", "mysql").lower()
    
    if db_type == "mysql":
        try:
            logger.info("Initializing MySQL Storage Connection...")
            _storage_instance = MySQLStore(
                host=os.getenv("MYSQL_HOST", "mysql-7da3a01-anujsingh41086-09c5.l.aivencloud.com"),
                port=int(os.getenv("MYSQL_PORT", 18549)),
                user=os.getenv("MYSQL_USER", "avnadmin"),
                password=os.getenv("MYSQL_PASSWORD", ""),
                database=os.getenv("MYSQL_DATABASE", "defaultdb")
            )
            return _storage_instance
        except Exception as e:
            logger.error(f"Failed to connect to MySQL, falling back to SQLite: {e}")
            _storage_instance = SQLiteStore()
            return _storage_instance
            
    _storage_instance = SQLiteStore()
    return _storage_instance
