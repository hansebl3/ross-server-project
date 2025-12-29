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

def fix_schema():
    print("Fixing Schema: Dropping unique_active_l1 constraint...")
    db = Database()
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            # Drop the named constraint if it exists. 
            # Note: The name 'unique_active_l1' was defined in CREATE TABLE.
            cur.execute("ALTER TABLE l1_versions DROP CONSTRAINT IF EXISTS unique_active_l1;")
        print("Schema Fix Successful: Constraint Dropped.")
    except Exception as e:
        print(f"Schema Fix Failed: {e}")

if __name__ == "__main__":
    fix_schema()
