import os
import shutil
import logging
from dotenv import load_dotenv

# Add src to path
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from database import Database

# Load Envs
project_env = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
load_dotenv(project_env)
app_env = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(app_env)

VAULT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'obsidian_vault_v4'))

def reset_db():
    print(f"Connecting to DB...")
    db = Database()
    try:
        conn = db.get_connection()
    except Exception as e:
        print(f"DB Connection Failed: {e}")
        return

    with conn.cursor() as cur:
        print("Truncating tables...")
        tables = [
            "l1_reviews", "l1_embeddings", "l1_versions",
            "l2_reviews", "l2_members", "l2_embeddings", "l2_versions",
            "documents",
            "prompt_versions"
        ]
        for t in tables:
            try:
                cur.execute(f"TRUNCATE TABLE {t} CASCADE;")
                print(f"  Truncated {t}")
            except Exception as ex:
                print(f"  Error truncating {t}: {ex}")
    print("DB Reset Complete.")

def reset_files():
    shadow_dir = os.path.join(VAULT_ROOT, "99_Shadow_Library")
    print(f"Cleaning Shadow Library: {shadow_dir}")
    if os.path.exists(shadow_dir):
        for d in ["L1", "L2"]:
            target = os.path.join(shadow_dir, d)
            if os.path.exists(target):
                shutil.rmtree(target)
                os.makedirs(target)
                print(f"  Wiped {target}")
    print("File Reset Complete.")

def touch_sources():
    source_dir = os.path.join(VAULT_ROOT, "01_Sources")
    print(f"Touching Source Files to trigger re-processing...")
    count = 0
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.endswith(".md"):
                path = os.path.join(root, file)
                try:
                    os.utime(path, None)
                    count += 1
                except Exception: pass
    print(f"Touched {count} source files.")

if __name__ == "__main__":
    if "--force" in sys.argv:
        choice = 'y'
    else:
        choice = input("WARNING: This will DELETE ALL Generated Data (DB + Shadow Files). Continue? (y/n): ")
        
    if choice.lower() == 'y':
        reset_db()
        reset_files()
        touch_sources()
        print("\nSystem Reset. Please ensure Watcher is running.")
    else:
        print("Aborted.")
