import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.join(os.getcwd(), 'doc-manager-v4', 'src'))
from database import Database
from clustering import SimilaritySearch

# Load envs
load_dotenv(os.path.join(os.getcwd(), '.env'))
load_dotenv(os.path.join(os.getcwd(), 'doc-manager-v4', '.env'))
os.environ["DOC_MANAGER_DB"] = "doc_manager_v4"

def test_similarity():
    print(">>> Testing Similarity Search...")
    db = Database()
    search = SimilaritySearch(db)
    
    # 1. Identify "AI Gardener" and "DreamRecorder" L1 UUIDs
    conn = db.get_connection()
    with conn.cursor() as cur:
        # Find AI Gardener L1
        cur.execute("""
            SELECT v.l1_id, d.path 
            FROM l1_versions v 
            JOIN documents d ON v.source_uuid = d.uuid 
            WHERE d.path LIKE '%AI_Gardener.md' AND v.status = 'ACTIVE'
        """)
        gardener_row = cur.fetchone()
        
        # Find DreamRecorder L1
        cur.execute("""
            SELECT v.l1_id, d.path 
            FROM l1_versions v 
            JOIN documents d ON v.source_uuid = d.uuid 
            WHERE d.path LIKE '%DreamRecorder.md' AND v.status = 'ACTIVE'
        """)
        dream_row = cur.fetchone()
        
    if not gardener_row:
        print("Error: AI Gardener L1 not found.")
        return
    if not dream_row:
        print("Error: DreamRecorder L1 not found.")
        return
        
    gardener_l1_uuid = str(gardener_row[0])
    dream_l1_uuid = str(dream_row[0])
    
    print(f"Target: AI Gardener ({gardener_l1_uuid})")
    print(f"Expected Match: DreamRecorder ({dream_l1_uuid})")
    
    # 2. Run Search from Gardener perspective
    results = search.find_related_l1(gardener_l1_uuid, limit=5, threshold=0.1) # Low threshold for test
    
    print(f"\nFound {len(results)} related docs:")
    found_dream = False
    for r in results:
        print(f" - [{r['similarity']:.4f}] {r['path']}")
        if r['l1_id'] == dream_l1_uuid:
            found_dream = True
            
    if found_dream:
        print("\n[PASS] Successfully found linked document.")
    else:
        print("\n[FAIL] Did not find DreamRecorder in results.")
        return

    # 3. Trigger L2 Builder
    print("\n>>> Testing L2 Generation...")
    from l2_builder import L2Builder
    
    vault_root = os.path.join(os.getcwd(), 'obsidian_vault_v4')
    shadow_dir = os.path.join(vault_root, '99_Shadow_Library')
    
    builder = L2Builder(db, shadow_dir)
    
    # Create cluster from found results + target
    cluster_ids = [gardener_l1_uuid] + [r['l1_id'] for r in results] # Gardener + DreamRecorder
    
    builder.build_l2_from_cluster(cluster_ids)
    print("L2 Build Triggered.")

if __name__ == "__main__":
    test_similarity()
