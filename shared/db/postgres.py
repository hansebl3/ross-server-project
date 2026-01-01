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

    def get_connection(self, host=None, port=None, user=None, password=None, db_name=None):
        """Returns a psycopg2 connection. Allows overriding defaults."""
        try:
            conn = psycopg2.connect(
                host=host or self.host,
                port=port or self.port,
                user=user or self.user,
                password=password or self.password,
                dbname=db_name or self.db_name
            )
            return conn
        except Exception as e:
            logger.error(f"PostgreSQL Connection Error: {e}")
            return None

    def get_cursor(self, conn):
        return conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
