import psycopg2
import psycopg2.extras
import os
import logging

logger = logging.getLogger(__name__)

class PostgresConnector:
    """
    Unified PostgreSQL Connector using POSTGRES_* environment variables.
    """
    def __init__(self):
        self.host = os.getenv("POSTGRES_HOST", "127.0.0.1")
        self.port = int(os.getenv("POSTGRES_PORT", 5432))
        self.user = os.getenv("POSTGRES_USER", "root")
        self.password = os.getenv("POSTGRES_PASSWORD")
        self.db_name = os.getenv("POSTGRES_DB", "doc_manager_db")

    def get_connection(self):
        """Returns a psycopg2 connection."""
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                dbname=self.db_name
            )
            return conn
        except Exception as e:
            logger.error(f"PostgreSQL Connection Error: {e}")
            return None

    def get_cursor(self, conn):
        return conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
