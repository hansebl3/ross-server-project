import os
import sys
import psycopg2
from dotenv import load_dotenv

# Setup paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from database import Database

def diag():
    # Load Envs like dashboard
    root_env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
    local_env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
    load_dotenv(root_env_path)
    load_dotenv(local_env_path)
    
    db = Database()
    conn = db.get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT l1_id, source_uuid, status, version FROM l1_versions")
        print("--- L1 Versions ---")
        for row in cur.fetchall():
            print(row)
            
        cur.execute("SELECT uuid, path FROM documents")
        print("\n--- Documents ---")
        for row in cur.fetchall():
            print(row)

if __name__ == "__main__":
    diag()
