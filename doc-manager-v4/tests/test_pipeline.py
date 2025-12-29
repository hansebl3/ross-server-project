import sys
import os
import time

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'doc-manager-v4', 'src'))

from database import Database
from watcher import DocEventHandler
from l1_builder import L1Builder
from dotenv import load_dotenv

# Load envs
root_env = os.path.join(os.getcwd(), '.env')
local_env = os.path.join(os.getcwd(), 'doc-manager-v4', '.env')

print(f"DEBUG: Loading Root Env: {root_env} (Exists: {os.path.exists(root_env)})")
load_dotenv(root_env) # Root

print(f"DEBUG: Loading Local Env: {local_env} (Exists: {os.path.exists(local_env)})")
load_dotenv(local_env) # Local

pwd = os.getenv("POSTGRES_PASSWORD", "")
print(f"DEBUG: Loaded POSTGRES_PASSWORD length: {len(pwd)}")
if len(pwd) > 2:
    print(f"DEBUG: Loaded POSTGRES_PASSWORD starts with: {pwd[:2]}***")
else:
    print("DEBUG: POSTGRES_PASSWORD is empty or too short.")

# Force DB name for V4 to avoid conflict with shared/test_db
os.environ["POSTGRES_DB"] = "doc_manager_v4"

def run_test():
    print(">>> 1. Initializing System...")
    db = Database()
    try:
        db.init_db()
    except Exception as e:
        print(f"DB Init failed: {e}")
        # Assuming DB might exist or connection issue, but let's try to proceed if it's just 'already exists'
    
    vault_root = os.path.join(os.getcwd(), 'obsidian_vault_v4')
    source_dir = os.path.join(vault_root, '01_Sources')
    config_dir = os.path.join(vault_root, '90_Configuration')
    shadow_dir = os.path.join(vault_root, '99_Shadow_Library')
    
    # Target File
    sample_file = os.path.join(source_dir, 'Idea', 'DreamRecorder.md')
    
    print(f">>> 2. Watcher Processing: {sample_file}")
    watcher = DocEventHandler(db, source_dir)
    # Simulate 'Modified' event
    watcher._process_file(sample_file)
    
    # Check DB
    conn = db.get_connection()
    with conn.cursor() as cur:
        # Get the UUID we just inserted. 
        # Since we put a UUID in frontmatter, our watcher SHOULD parse it?
        # WAIT: Code in watcher.py says: 
        # uuid = generate_uuid_v7() # Placeholder...
        # It DOES NOT parse frontmatter yet (Phase 1 placeholder).
        # So we need to find it by path.
        
        rel_path = "01_Sources/Idea/DreamRecorder.md" # Watcher stores relative to Vault Root
        cur.execute("SELECT uuid, category FROM documents WHERE path = %s", (rel_path,))
        row = cur.fetchone()
        
    if not row:
        print("!!! TEST FAILED: Document not found in DB after Watcher run.")
        return
        
    doc_uuid, doc_category = row
    print(f"    [OK] Document Inserted. UUID: {doc_uuid}, Category: {doc_category}")
    
    if doc_category != "Idea":
        print(f"!!! WARNING: Category mismatch. Expected 'Idea', got '{doc_category}'")

    print(f">>> 3. L1 Builder Triggering")
    builder = L1Builder(db, config_dir, shadow_dir)
    builder.build_l1(doc_uuid)
    
    # Check Output
    expected_shadow = os.path.join(shadow_dir, 'L1', '[L1] DreamRecorder.md')
    if os.path.exists(expected_shadow):
        print(f"    [OK] Shadow File Created: {expected_shadow}")
        with open(expected_shadow, 'r') as f:
            print("\n--- Shadow Content Preview ---")
            print(f.read()[:500])
            print("...\n------------------------------")
    else:
        print(f"!!! TEST FAILED: Shadow file not found at {expected_shadow}")

if __name__ == "__main__":
    run_test()
