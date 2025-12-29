import sys
import os
import time
import yaml
from dotenv import load_dotenv

sys.path.append(os.path.join(os.getcwd(), 'doc-manager-v4', 'src'))
from database import Database
from l1_builder import L1Builder
from watcher import ReviewEventHandler

# Load envs
load_dotenv(os.path.join(os.getcwd(), '.env'))
load_dotenv(os.path.join(os.getcwd(), 'doc-manager-v4', '.env'))
os.environ["DOC_MANAGER_DB"] = "doc_manager_v4"

def run_test():
    print(">>> 1. Initializing System...")
    db = Database()
    vault_root = os.path.join(os.getcwd(), 'obsidian_vault_v4')
    config_dir = os.path.join(vault_root, '90_Configuration')
    shadow_dir = os.path.join(vault_root, '99_Shadow_Library')
    l1_dir = os.path.join(shadow_dir, 'L1')
    
    # 2. Trigger L1 Builder to generate updated L1 + Review Template
    # We need a valid UUID from DB. Let's pick one.
    conn = db.get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT uuid FROM documents LIMIT 1")
        doc_uuid = cur.fetchone()[0]
        
    print(f">>> 2. Running L1Builder for {doc_uuid}...")
    builder = L1Builder(db, config_dir, shadow_dir)
    builder.build_l1(str(doc_uuid))
    
    # Check if review file created
    # We don't know exact filename easily without logic, but let's assume DreamRecorder
    review_file = os.path.join(l1_dir, "[L1] DreamRecorder.review.md")
    
    if os.path.exists(review_file):
        print(f"    [OK] Review Template Created: {review_file}")
    else:
        print(f"!!! FAILED: Review file not found at {review_file}")
        return

    # 3. Simulate User Editing Review
    print(">>> 3. Simulating User Review...")
    with open(review_file, 'r') as f:
        content = f.read()
        
    # Edit content
    updated_content = content.replace("rating: PENDING", "rating: GOOD")
    updated_content = updated_content.replace("decision: PENDING", "decision: ACCEPT")
    updated_content += "\nThis is a test note from the user."
    
    with open(review_file, 'w') as f:
        f.write(updated_content)
        
    print(f"    [OK] User edited {review_file}")

    # 4. Trigger Watcher Logic (Manually)
    print(">>> 4. Triggering ReviewEventHandler...")
    handler = ReviewEventHandler(db, shadow_dir)
    handler._process_review(review_file)
    
    # 5. Check DB
    print(">>> 5. Verifying DB Insertion...")
    with conn.cursor() as cur:
        # Extract review_id from file to check DB
        blocks = updated_content.split('---')
        meta = yaml.safe_load(blocks[1])
        r_id = meta['review_id']
        
        cur.execute("SELECT rating, decision, notes FROM l1_reviews WHERE review_id = %s", (r_id,))
        row = cur.fetchone()
        
    if row:
        print(f"    [OK] Review Found in DB: {row}")
        if row[0] == 'GOOD' and row[1] == 'ACCEPT':
            print("    [SUCCESS] Review content matches.")
        else:
            print("    [FAIL] Content mismatch.")
    else:
        print("!!! TEST FAILED: Review not found in DB.")

if __name__ == "__main__":
    run_test()
