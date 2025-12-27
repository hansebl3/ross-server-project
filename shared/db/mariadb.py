import pymysql
import os
import logging

logger = logging.getLogger(__name__)

class MariaDBConnector:
    """
    Unified MariaDB Connector using MARIADB_* environment variables.
    """
    def __init__(self):
        self.host = os.getenv("MARIADB_HOST", "127.0.0.1")
        self.port = int(os.getenv("MARIADB_PORT", 3306))
        self.user = os.getenv("MARIADB_USER", "root")
        self.password = os.getenv("MARIADB_PASSWORD")
        self.db_name = os.getenv("MARIADB_DB", "rag_diary_db")
        
    def get_connection(self, db_name=None, host=None, port=None, user=None, password=None, use_dict_cursor=True):
        """
        Returns a pymysql connection.
        If params are provided, they override the defaults (env vars).
        If db_name is None, uses MARIADB_DB from env (or self.db_name).
        If db_name is "", connects without selecting a database.
        """
        if db_name == "":
            target_db = None
        else:
            target_db = db_name if db_name else self.db_name
            
        target_host = host if host else self.host
        target_port = int(port) if port else self.port
        target_user = user if user else self.user
        target_password = password if password else self.password
        
        cursor_class = pymysql.cursors.DictCursor if use_dict_cursor else pymysql.cursors.Cursor
            
        try:
            conn = pymysql.connect(
                host=target_host,
                port=target_port,
                user=target_user,
                password=target_password,
                database=target_db,
                charset='utf8mb4',
                cursorclass=cursor_class,
                autocommit=True
            )
            return conn
        except pymysql.MySQLError as e:
            logger.error(f"MariaDB Connection Error: {e}")
            return None
