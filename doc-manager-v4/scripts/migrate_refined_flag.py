import os
import sys
import psycopg2
from dotenv import load_dotenv

# Setup paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from database import Database

def migrate():
    load_dotenv('../.env')
    db = Database()
    conn = db.get_connection()
    conn.autocommit = True
    
    with conn.cursor() as cur:
        try:
            print("Executing: ALTER TABLE l1_versions ADD COLUMN IF NOT EXISTS refined_by_user BOOLEAN DEFAULT FALSE;")
            cur.execute("ALTER TABLE l1_versions ADD COLUMN IF NOT EXISTS refined_by_user BOOLEAN DEFAULT FALSE;")
            print("Migration successful.")
        except Exception as e:
            print(f"Error during migration: {e}")

if __name__ == "__main__":
    migrate()
