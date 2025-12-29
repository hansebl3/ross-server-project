import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from prompt_loader import PromptLoader
from unittest.mock import patch, mock_open

def test_hierarchical_matching():
    # Mocking prompt_config.md
    config_content = """---
mappings:
  A/B: prompt.AB.md
  A: prompt.A.md
  default: prompt.default.md
---"""
    
    loader = PromptLoader("/tmp/config_test")
    
    with patch("builtins.open", mock_open(read_data=config_content)), \
         patch("os.path.exists", return_value=True), \
         patch.object(PromptLoader, "_parse_prompt_file", side_effect=lambda x: x):
        
        # Test 1: Exact match
        res = loader.load_prompt_for_category("A/B")
        print(f"Match 'A/B': {res}")
        if "prompt.AB.md" in res: print("SUCCESS 1")
        
        # Test 2: Subfolder match (A/B/C -> A/B)
        res = loader.load_prompt_for_category("A/B/C")
        print(f"Match 'A/B/C': {res}")
        if "prompt.AB.md" in res: print("SUCCESS 2")
        
        # Test 3: Parent match (A/D -> A)
        res = loader.load_prompt_for_category("A/D")
        print(f"Match 'A/D': {res}")
        if "prompt.A.md" in res: print("SUCCESS 3")
        
        # Test 4: Default match (E -> default)
        res = loader.load_prompt_for_category("E")
        print(f"Match 'E': {res}")
        if "prompt.default.md" in res: print("SUCCESS 4")

if __name__ == "__main__":
    test_hierarchical_matching()
