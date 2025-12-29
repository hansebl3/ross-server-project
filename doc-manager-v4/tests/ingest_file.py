import sys
import os
import argparse
from dotenv import load_dotenv

sys.path.append(os.path.join(os.getcwd(), 'doc-manager-v4', 'src'))
from database import Database
from watcher import DocEventHandler
from l1_builder import L1Builder

# Load envs
load_dotenv(os.path.join(os.getcwd(), '.env'))
load_dotenv(os.path.join(os.getcwd(), 'doc-manager-v4', '.env'))
os.environ["DOC_MANAGER_DB"] = "doc_manager_v4"

def ingest(file_path):
    print(f"Ingesting: {file_path}")
    db = Database()
    
    vault_root = os.path.join(os.getcwd(), 'obsidian_vault_v4')
    source_dir = os.path.join(vault_root, '01_Sources')
    config_dir = os.path.join(vault_root, '90_Configuration')
    shadow_dir = os.path.join(vault_root, '99_Shadow_Library')
    
    # 1. Watcher (Insert to DB)
    watcher = DocEventHandler(db, source_dir)
    watcher._process_file(file_path)
    
    # 2. Fetch UUID
    rel_path = os.path.relpath(file_path, os.path.dirname(source_dir))
    conn = db.get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT uuid FROM documents WHERE path = %s", (rel_path,))
        row = cur.fetchone()
        
    if not row:
        print("Error: Document insertion failed.")
        return
        
    doc_uuid = str(row[0])
    print(f"Document UUID: {doc_uuid}")
    
    # 3. Builder (LLM + Embedding)
    builder = L1Builder(db, config_dir, shadow_dir)
    builder.build_l1(doc_uuid)
    print("Ingestion Complete.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ingest_file.py <abs_path_to_md>")
        sys.exit(1)
    
    ingest(sys.argv[1])
