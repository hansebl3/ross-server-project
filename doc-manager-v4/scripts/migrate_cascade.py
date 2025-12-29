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
    
    queries = [
        # L1 Versions -> Documents
        "ALTER TABLE l1_versions DROP CONSTRAINT IF EXISTS l1_versions_source_uuid_fkey",
        "ALTER TABLE l1_versions ADD CONSTRAINT l1_versions_source_uuid_fkey FOREIGN KEY (source_uuid) REFERENCES documents(uuid) ON DELETE CASCADE",
        
        # L1 Embeddings -> L1 Versions
        "ALTER TABLE l1_embeddings DROP CONSTRAINT IF EXISTS l1_embeddings_l1_id_fkey",
        "ALTER TABLE l1_embeddings ADD CONSTRAINT l1_embeddings_l1_id_fkey FOREIGN KEY (l1_id) REFERENCES l1_versions(l1_id) ON DELETE CASCADE",
        
        # L1 Reviews -> L1 Versions
        "ALTER TABLE l1_reviews DROP CONSTRAINT IF EXISTS l1_reviews_l1_id_fkey",
        "ALTER TABLE l1_reviews ADD CONSTRAINT l1_reviews_l1_id_fkey FOREIGN KEY (l1_id) REFERENCES l1_versions(l1_id) ON DELETE CASCADE",
        
        # L2 Members -> L1 Versions
        "ALTER TABLE l2_members DROP CONSTRAINT IF EXISTS l2_members_l1_id_fkey",
        "ALTER TABLE l2_members ADD CONSTRAINT l2_members_l1_id_fkey FOREIGN KEY (l1_id) REFERENCES l1_versions(l1_id) ON DELETE CASCADE"
    ]
    
    with conn.cursor() as cur:
        for q in queries:
            try:
                print(f"Executing: {q}")
                cur.execute(q)
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    migrate()
