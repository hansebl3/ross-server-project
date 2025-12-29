import os
import sys
import yaml
from typing import Dict, Any, Tuple

# Mock parse_frontmatter if needed, but let's use the real one
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from utils import parse_frontmatter

def test_loader_logic():
    config_path = "/home/ross/pythonproject/obsidian_vault_v4/90_Configuration/Prompts/prompt_config.md"
    print(f"Reading from {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    metadata, _ = parse_frontmatter(content)
    mapping = metadata.get('mappings', metadata)
    
    print(f"Parsed Mapping: {mapping}")
    
    target_category = "Lightspray/TroubleShooting"
    print(f"Target Category: {target_category}")
    
    search_path = target_category
    while search_path:
        filename = mapping.get(search_path)
        print(f"Checking '{search_path}': {filename}")
        if filename:
            break
        if os.sep in search_path:
            search_path = os.path.dirname(search_path)
        elif '/' in search_path:
            search_path = search_path.rsplit('/', 1)[0]
        else:
            search_path = ""
    
    if not filename:
        filename = mapping.get('default', 'prompt.md')
        print(f"Fallback to default: {filename}")

if __name__ == "__main__":
    test_loader_logic()
