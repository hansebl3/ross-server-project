
import sys
import os
import uuid
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from database import Database
from l1_builder import L1Builder
from llm_client import LLMClient
from utils import generate_uuid_v7, PathManager

def test_prompt_flow():
    print("Initializing Database...")
    db = Database()
    
    # Mock LLMClient
    print("Mocking LLMClient...")
    original_generate = LLMClient.generate_text_summary
    original_embedding = LLMClient.get_embedding
    
    LLMClient.generate_text_summary = MagicMock(return_value="This is a mocked summary using prompts.")
    LLMClient.get_embedding = MagicMock(return_value=[0.1] * 384)
    
    try:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        config_dir = os.path.join(project_root, 'obsidian_vault_v4', '90_Configuration')
        shadow_dir = os.path.join(project_root, 'obsidian_vault_v4', '99_Shadow_Library')
        paths = PathManager(shadow_dir)

        builder = L1Builder(db, config_dir, shadow_dir)
        
        # 1. Create Dummy Doc
        doc_uuid = generate_uuid_v7()
        doc_path = f"01_Sources/Test_Prompt_{doc_uuid}.md"
        print(f"Creating Dummy Doc: {doc_uuid}")
        
        db.upsert_document(doc_uuid, doc_path, "Dummy content for prompt test.", "hash123", "Personal")
            
        # 2. Run Build
        print("Running build_l1...")
        builder.build_l1(doc_uuid)
        
        # 3. Verify DB
        print("Verifying DB...")
        conn = db.get_connection()
        with conn.cursor() as cur:
            # Check L1 Version
            cur.execute("SELECT prompt_id, l1_id FROM l1_versions WHERE source_uuid = %s", (doc_uuid,))
            res = cur.fetchone()
            if not res:
                print("FAIL: No L1 Version created.")
                return
            
            prompt_id, l1_id = res
            print(f"L1 linked to Prompt ID: {prompt_id}")
            
            # Check Prompt Version
            cur.execute("SELECT active FROM prompt_versions WHERE prompt_id = %s", (prompt_id,))
            res2 = cur.fetchone()
            if not res2:
                print("FAIL: Prompt ID not found in prompt_versions.")
                return
            
            print("SUCCESS: Prompt Version found in DB.")

        # 4. Verify Review File
        print("Verifying Review File...")
        review_path = paths.get_l1_review_path("Personal", paths.get_l1_path("Personal", doc_path))
        
        if not os.path.exists(review_path):
            print(f"FAIL: Review file not found at {review_path}")
            return
            
        with open(review_path, 'r') as f:
            content = f.read()
            if "prompt_file:" in content:
                print("SUCCESS: Review file contains 'prompt_file'.")
            else:
                print("FAIL: Review file missing 'prompt_file'.")
                
        print("\nALL TESTS PASSED.")

    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        # Cleanup
        print("\nCleaning up...")
        # Since this is a test, we don't necessarily want to wipe everything but let's remove the test doc
        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM l1_embeddings WHERE l1_id IN (SELECT l1_id FROM l1_versions WHERE source_uuid = %s)", (doc_uuid,))
            cur.execute("DELETE FROM l1_reviews WHERE l1_id IN (SELECT l1_id FROM l1_versions WHERE source_uuid = %s)", (doc_uuid,))
            cur.execute("DELETE FROM l1_versions WHERE source_uuid = %s", (doc_uuid,))
            cur.execute("DELETE FROM documents WHERE uuid = %s", (doc_uuid,))
            
        # Restore Mocks
        LLMClient.generate_text_summary = original_generate
        LLMClient.get_embedding = original_embedding

if __name__ == "__main__":
    test_prompt_flow()
