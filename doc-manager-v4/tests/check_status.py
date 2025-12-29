import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.join(os.getcwd(), 'doc-manager-v4', 'src'))
from database import Database

# Load envs
load_dotenv(os.path.join(os.getcwd(), '.env')) # Root
load_dotenv(os.path.join(os.getcwd(), 'doc-manager-v4', '.env')) # Local
os.environ["DOC_MANAGER_DB"] = "doc_manager_v4"

def check():
    db = Database()
    conn = db.get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM l1_versions")
        count = cur.fetchone()[0]
        print(f"L1 Version Count: {count}")
        
        if count > 0:
            cur.execute("SELECT version, status, model_id FROM l1_versions ORDER BY created_at DESC LIMIT 1")
            print(f"Latest L1: {cur.fetchone()}")
            
        cur.execute("SELECT count(*) FROM l1_embeddings")
        embed_count = cur.fetchone()[0]
        print(f"Embedding Count: {embed_count}")

if __name__ == "__main__":
    check()
