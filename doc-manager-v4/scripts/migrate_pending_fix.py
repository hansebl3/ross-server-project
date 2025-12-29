import os
import sys
import psycopg2
from dotenv import load_dotenv

# Setup paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from database import Database

def migrate():
    # Load Envs
    root_env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
    local_env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
    load_dotenv(root_env_path)
    load_dotenv(local_env_path)
    
    db = Database()
    conn = db.get_connection()
    conn.autocommit = True
    
    with conn.cursor() as cur:
        try:
            print("Updating L1 Review Constraints...")
            # Decision
            cur.execute("ALTER TABLE l1_reviews DROP CONSTRAINT IF EXISTS l1_reviews_decision_check;")
            cur.execute("ALTER TABLE l1_reviews ADD CONSTRAINT l1_reviews_decision_check CHECK (decision IN ('PENDING', 'ACCEPT', 'REBUILD', 'DISCARD'));")
            
            # Rating
            cur.execute("ALTER TABLE l1_reviews DROP CONSTRAINT IF EXISTS l1_reviews_rating_check;")
            cur.execute("ALTER TABLE l1_reviews ADD CONSTRAINT l1_reviews_rating_check CHECK (rating IN ('PENDING', 'GOOD', 'OK', 'BAD'));")
            
            print("Migration successful.")
        except Exception as e:
            print(f"Error during migration: {e}")

if __name__ == "__main__":
    migrate()
