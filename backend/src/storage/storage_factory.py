import os
import logging
from src.storage.sqlite_store import SQLiteStore
from src.storage.mysql_store import MySQLStore

logger = logging.getLogger(__name__)

def get_storage():
    """
    Factory function to get the storage backend based on environment variables.
    Defaults to SQLite if MySQL is not configured or fails.
    """
    db_type = os.getenv("DB_TYPE", "mysql").lower()
    
    if db_type == "mysql":
        try:
            return MySQLStore(
                host=os.getenv("MYSQL_HOST", "mysql-7da3a01-anujsingh41086-09c5.l.aivencloud.com"),
                port=int(os.getenv("MYSQL_PORT", 18549)),
                user=os.getenv("MYSQL_USER", "avnadmin"),
                password=os.getenv("MYSQL_PASSWORD", ""),
                database=os.getenv("MYSQL_DATABASE", "defaultdb")
            )
        except Exception as e:
            logger.error(f"Failed to connect to MySQL, falling back to SQLite: {e}")
            return SQLiteStore()
            
    return SQLiteStore()
