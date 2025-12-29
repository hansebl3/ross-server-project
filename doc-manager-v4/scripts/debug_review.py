import os
import sys
from dotenv import load_dotenv

# Setup paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from database import Database
from watcher import ReviewEventHandler, DocEventHandler
from l1_builder import L1Builder
from l2_builder import L2Builder

def debug_review():
    abs_sources_dir = "/home/ross/pythonproject/obsidian_vault_v4/01_Sources"
    abs_shadow_dir = "/home/ross/pythonproject/obsidian_vault_v4/99_Shadow_Library"
    abs_config_dir = "/home/ross/pythonproject/obsidian_vault_v4/90_Configuration"

    db = Database()
    l1_builder = L1Builder(db, abs_config_dir, abs_shadow_dir)
    l2_builder = L2Builder(db, abs_shadow_dir)
    handler = ReviewEventHandler(db, l1_builder, l2_builder)
    
    # Target review file
    target = "/home/ross/pythonproject/obsidian_vault_v4/99_Shadow_Library/L1/Lightspray/TroubleShooting/Reviews/[L1] 노즐에 금속성 이물질 끼임.review.md"
    
    print(f"DEBUG: Processing Review {target}")
    handler._process_review(target)
    print("DEBUG: Done.")

if __name__ == "__main__":
    debug_review()
