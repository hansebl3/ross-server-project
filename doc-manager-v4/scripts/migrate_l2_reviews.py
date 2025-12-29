import os
import psycopg2
from dotenv import load_dotenv

# Load env from root
basedir = os.path.dirname(os.path.abspath(__file__))
# scripts -> doc-manager-v4 -> pythonproject -> .env (3 levels up)
env_path = os.path.join(basedir, '..', '..', '.env')
load_dotenv(env_path)

# DB Config (Directly use envs for script)
HOST = os.getenv("POSTGRES_HOST", "localhost")
PORT = os.getenv("POSTGRES_PORT", 5432)
USER = os.getenv("POSTGRES_USER", "postgres")
PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
DB_NAME = os.getenv("DOC_MANAGER_DB", "doc_manager_v4")

def migrate():
    print(f"Connecting to {DB_NAME} at {HOST}...")
    try:
        conn = psycopg2.connect(
            host=HOST,
            port=PORT,
            user=USER,
            password=PASSWORD,
            dbname=DB_NAME
        )
        conn.autocommit = True
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    sql = """
    CREATE TABLE IF NOT EXISTS l2_reviews (
        review_id UUID PRIMARY KEY,
        l2_id UUID REFERENCES l2_versions(l2_id) ON DELETE CASCADE,
        rating VARCHAR(50),
        decision VARCHAR(50),
        issues JSONB,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE INDEX IF NOT EXISTS idx_l2_reviews_l2_id ON l2_reviews(l2_id);
    """
    
    with conn.cursor() as cur:
        print("Creating l2_reviews table...")
        cur.execute(sql)
        print("Done.")

    conn.close()

if __name__ == "__main__":
    migrate()
