import sys
import os
import json
from dotenv import load_dotenv

sys.path.append(os.path.join(os.getcwd(), 'doc-manager-v4', 'src'))
from database import Database
from exporter import DatasetExporter

# Load envs
load_dotenv(os.path.join(os.getcwd(), '.env'))
load_dotenv(os.path.join(os.getcwd(), 'doc-manager-v4', '.env'))
os.environ["DOC_MANAGER_DB"] = "doc_manager_v4"

def run_test():
    print(">>> Testing Dataset Export...")
    db = Database()
    vault_root = os.path.join(os.getcwd(), 'obsidian_vault_v4')
    config_dir = os.path.join(vault_root, '90_Configuration')
    
    exporter = DatasetExporter(db, config_dir)
    
    # 1. Test SFT
    sft_file = os.path.join(os.getcwd(), "dataset_sft.jsonl")
    exporter.export_sft(sft_file)
    
    if os.path.exists(sft_file):
        lines = open(sft_file).readlines()
        print(f"    [OK] SFT Exported: {len(lines)} samples.")
        if len(lines) > 0:
            sample = json.loads(lines[0])
            if "messages" in sample:
                print("    [PASS] SFT Format correct.")
            else:
                print("    [FAIL] SFT Format invalid.")
    else:
        print("    [FAIL] SFT File not created.")

    # 2. Test DPO
    dpo_file = os.path.join(os.getcwd(), "dataset_dpo.jsonl")
    exporter.export_dpo(dpo_file)
    
    if os.path.exists(dpo_file):
        lines = open(dpo_file).readlines()
        print(f"    [OK] DPO Exported: {len(lines)} pairs.")
        # We expect at least 1 pair for DreamRecorder (Version 3 vs 1 or 2)
        if len(lines) > 0:
            sample = json.loads(lines[0])
            if "chosen" in sample and "rejected" in sample:
                print("    [PASS] DPO Format correct.")
            else:
                print("    [FAIL] DPO Format invalid.")
    else:
        print("    [FAIL] DPO File not created.")

if __name__ == "__main__":
    run_test()
