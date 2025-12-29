
import os
import sys
from dotenv import load_dotenv
import psycopg2

# Load Env
root_env = os.path.abspath(os.path.join(os.path.dirname(__file__), '.env'))
load_dotenv(root_env)

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "doc_manager")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "password")

def migrate():
    print(f"Connecting to {DB_NAME} on {DB_HOST}...")
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        conn.autocommit = True
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    with conn.cursor() as cur:
        # Check if column exists
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='l2_versions' AND column_name='category';
        """)
        if cur.fetchone():
            print("'category' column already exists in l2_versions.")
        else:
            print("Adding 'category' column to l2_versions...")
            cur.execute("ALTER TABLE l2_versions ADD COLUMN category TEXT DEFAULT 'General';")
            print("Done.")

    conn.close()

if __name__ == "__main__":
    migrate()
