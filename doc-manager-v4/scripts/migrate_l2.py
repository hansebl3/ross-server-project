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

def migrate_l2():
    print("Migrating L2 Schema...")
    db = Database()
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            # 6. L2 Versions
            cur.execute("""
            CREATE TABLE IF NOT EXISTS l2_versions (
                l2_id UUID PRIMARY KEY,
                title TEXT,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
            
            # 7. L2 Members
            cur.execute("""
            CREATE TABLE IF NOT EXISTS l2_members (
                l2_id UUID REFERENCES l2_versions(l2_id),
                l1_id UUID REFERENCES l1_versions(l1_id),
                PRIMARY KEY (l2_id, l1_id)
            );
            """)
            
            # 8. L2 Embeddings
            cur.execute("""
            CREATE TABLE IF NOT EXISTS l2_embeddings (
                l2_id UUID PRIMARY KEY REFERENCES l2_versions(l2_id),
                embedding vector(384)
            );
            """)
            
        print("L2 Migration Successful.")
    except Exception as e:
        print(f"L2 Migration Failed: {e}")

if __name__ == "__main__":
    migrate_l2()
