import os
import yaml
import logging
from typing import Dict, Any, Tuple
from utils import parse_frontmatter

logger = logging.getLogger(__name__)

class Prompt:
    def __init__(self, content: str, config: Dict[str, Any], path: str):
        self.content = content
        self.config = config
        self.path = path
        self.category = config.get('category', 'General')
        self.is_active = True

class PromptLoader:
    def __init__(self, config_dir: str):
        self.prompts_dir = os.path.join(config_dir, "Prompts")
        if not os.path.exists(self.prompts_dir):
            os.makedirs(self.prompts_dir)

    def load_prompt_for_category(self, category: str = "General") -> Prompt:
        """Loads a prompt based on category path with hierarchical fallback."""
        config_path = os.path.join(self.prompts_dir, "prompt_config.md")
        mapping = {}
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                metadata, _ = parse_frontmatter(content)
                mapping = metadata.get('mappings', metadata) # Use top-level metadata if 'mappings' key is missing
            except Exception as e:
                logger.error(f"Failed to load prompt_config.md: {e}")

        # Hierarchical lookup: A/B/C -> A/B -> A -> default
        search_path = category
        filename = None
        
        while search_path:
            filename = mapping.get(search_path)
            if filename:
                logger.info(f"Matched prompt '{filename}' for category path '{search_path}'")
                break
            # Move up one level
            if os.sep in search_path:
                search_path = os.path.dirname(search_path)
            elif '/' in search_path: # Fallback for forward slashes
                search_path = search_path.rsplit('/', 1)[0]
            else:
                search_path = ""
                
        if not filename:
            filename = mapping.get('default', 'prompt.md')
             
        prompt_path = os.path.join(self.prompts_dir, filename)
        if not os.path.exists(prompt_path):
            logger.warning(f"Prompt '{filename}' not found. Falling back to 'prompt.md'.")
            prompt_path = os.path.join(self.prompts_dir, "prompt.md")

        if os.path.exists(prompt_path):
            return self._parse_prompt_file(prompt_path)

        raise FileNotFoundError(f"No prompt found for category '{category}'")

    def _parse_prompt_file(self, path: str) -> Prompt:
        """Parses a markdown file with YAML frontmatter."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            metadata, body = parse_frontmatter(content)
            if not metadata and not content.startswith('---'):
                metadata = {"model": "default"}
            return Prompt(body, metadata, path)
        except Exception as e:
            logger.error(f"Failed to load prompt {path}: {e}")
            raise
