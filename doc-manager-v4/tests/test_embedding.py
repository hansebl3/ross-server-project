import sys
import os
import logging
from dotenv import load_dotenv

sys.path.append(os.path.join(os.getcwd(), 'doc-manager-v4', 'src'))
# Load envs manually before import since llm_client does it too but let's be safe
load_dotenv(os.path.join(os.getcwd(), '.env')) 
load_dotenv(os.path.join(os.getcwd(), 'doc-manager-v4', '.env'))

from llm_client import LLMClient

logging.basicConfig(level=logging.INFO)

def test_embed():
    client = LLMClient()
    print(f"Testing Embedding on {client.text_base_url}...")
    
    text = "This is a test summary for embedding generation."
    embedding = client.get_embedding(text)
    
    if embedding:
        print(f"SUCCESS: Generated embedding with {len(embedding)} dimensions.")
    else:
        print("FAILURE: No embedding returned.")

if __name__ == "__main__":
    test_embed()
