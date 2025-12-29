import os
import sys
from dotenv import load_dotenv

# Setup paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from database import Database
from watcher import DocEventHandler
from l1_builder import L1Builder

def debug_process():
    # Use real absolute paths
    abs_sources_dir = "/home/ross/pythonproject/obsidian_vault_v4/01_Sources"
    abs_shadow_dir = "/home/ross/pythonproject/obsidian_vault_v4/99_Shadow_Library"
    abs_config_dir = "/home/ross/pythonproject/obsidian_vault_v4/90_Configuration"

    db = Database()
    l1_builder = L1Builder(db, abs_config_dir, abs_shadow_dir)
    handler = DocEventHandler(db, l1_builder, abs_sources_dir)
    
    # Target file
    target = "/home/ross/pythonproject/obsidian_vault_v4/01_Sources/Lightspray/TroubleShooting/노즐에 금속성 이물질 끼임.md"
    
    print(f"DEBUG: Processing {target}")
    handler._process_file(target)
    print("DEBUG: Done.")

if __name__ == "__main__":
    debug_process()
