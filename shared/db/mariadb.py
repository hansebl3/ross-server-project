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
        
    def get_connection(self, db_name=None):
        """
        Returns a pymysql connection.
        If db_name is None, uses MARIADB_DB from env.
        If db_name is "", connects without selecting a database.
        """
        if db_name == "":
            target_db = None
        else:
            target_db = db_name if db_name else self.db_name
            
        try:
            conn = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=target_db,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True
            )
            return conn
        except pymysql.MySQLError as e:
            logger.error(f"MariaDB Connection Error: {e}")
            return None
