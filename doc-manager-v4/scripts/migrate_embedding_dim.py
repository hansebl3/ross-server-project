import sys
import os
from dotenv import load_dotenv
import psycopg2

sys.path.append(os.path.join(os.getcwd(), 'doc-manager-v4', 'src'))
from database import Database

# Load envs
load_dotenv(os.path.join(os.getcwd(), '.env'))
load_dotenv(os.path.join(os.getcwd(), 'doc-manager-v4', '.env'))
os.environ["DOC_MANAGER_DB"] = "doc_manager_v4"

def migrate():
    print("Migrating Embedding Dimension to 384...")
    db = Database()
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            # We must truncate because dimensions mismatch prevents direct cast if data exists
            cur.execute("TRUNCATE l1_embeddings;") 
            cur.execute("ALTER TABLE l1_embeddings ALTER COLUMN embedding TYPE vector(384);")
        print("Migration Successful.")
    except Exception as e:
        print(f"Migration Failed: {e}")

if __name__ == "__main__":
    migrate()
