
import sys
import os
import psycopg2
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from prompt_loader import PromptLoader

# Load Env from Project Root (pythonproject/.env)
project_env = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
load_dotenv(project_env)

# Load Env from App Root (doc-manager-v4/.env)
app_env = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(app_env)

def debug_loader():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    config_dir = os.path.join(root_dir, 'obsidian_vault_v4', '90_Configuration')
    
    print(f"Config Dir: {config_dir}")
    
    loader = PromptLoader(config_dir)
    try:
        prompt = loader.load_prompt_for_category("Personal")
        print(f"Loaded Prompt for 'Personal'")
        print(f"Content Length: {len(prompt.content)}")
        print("-" * 20)
        print(f"First 100 chars:\n{prompt.content[:100]}")
        print("-" * 20)
        print(f"Last 100 chars:\n{prompt.content[-100:]}")
        print("-" * 20)
    except Exception as e:
        print(f"Error loading prompt: {e}")

from database import Database

def debug_db():
    print("\nChecking DB Content...")
    try:
        db = Database()
        conn = db.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT prompt_id, content FROM prompt_versions")
            rows = cur.fetchall()
            print(f"Found {len(rows)} prompts in DB.")
            for row in rows:
                pid, content = row
                print(f"Prompt ID: {pid}")
                print(f"Content Len: {len(content)}")
                print(f"Content Preview (repr): {repr(content[:100])}...")
                if len(content) < 100:
                    print(f"FULL CONTENT: {content}")
        # conn.close() # Database class manages pool, usually don't need to close manually or it's fine.
    except Exception as e:
        print(f"DB Error: {e}")

if __name__ == "__main__":
    debug_loader()
    debug_db()
