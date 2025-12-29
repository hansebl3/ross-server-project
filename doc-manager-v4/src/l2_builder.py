import os
import logging
from datetime import datetime
from typing import List
from collections import Counter

from database import Database
from llm_client import LLMClient
from prompt_loader import PromptLoader
from utils import generate_uuid_v7, PathManager, set_file_permissions, extract_tags

logger = logging.getLogger("L2Builder")

class L2Builder:
    def __init__(self, db: Database, shadow_dir: str):
        self.db = db
        self.llm_client = LLMClient()
        self.paths = PathManager(shadow_dir)
        
        # Derive config dir
        parent = os.path.dirname(os.path.abspath(shadow_dir))
        config_dir = os.path.join(parent, "90_Configuration")
        self.prompt_loader = PromptLoader(config_dir)

    def build_l2_from_cluster(self, l1_uuids: List[str]):
        """Creates an L2 Insight from a list of L1 UUIDs."""
        if not l1_uuids:
            logger.warning("No L1 UUIDs provided for L2 build.")
            return

        logger.info(f"Building L2 from {len(l1_uuids)} L1s...")
        
        # 1. Fetch L1 Content
        l1_data = self.db.get_l1_data_for_l2(l1_uuids)
        if not l1_data:
            logger.error("Could not fetch L1 data.")
            return

        # 2. Construct Prompt Context
        context = ""
        for i, item in enumerate(l1_data):
            context += f"--- Source {i+1}: {item['path']} ---\n{item['content']}\n\n"
            
        # 3. Load L2 Prompt
        try:
            prompt_obj = self.prompt_loader.load_prompt_for_category("L2")
            system_prompt = prompt_obj.content
            cfg = prompt_obj.config
            model_val = cfg.get("model")
            
            if isinstance(model_val, dict):
                 # Legacy nested style
                 model_name = model_val.get("name", "gpt-oss-120b")
                 provider = model_val.get("provider", "llama.cpp")
                 temp = model_val.get("temperature", 0.7)
            else:
                 # New flat style
                 model_name = model_val or "gpt-oss-120b"
                 provider = cfg.get("provider", "llama.cpp")
                 temp = cfg.get("temperature", 0.7)
        except Exception as e:
            logger.error(f"Failed to load L2 prompt: {e}")
            system_prompt = "Synthesize these notes into an L2 Insight."
            model_name, provider, temp = "gpt-oss-120b", "llama.cpp", 0.7

        # 4. Generate Response
        response = self.llm_client.generate_text_summary(
            system_prompt=system_prompt,
            user_content=context,
            model=model_name, 
            temperature=temp,
            provider=provider
        )
        
        if not response:
            logger.error("L2 LLM Generation Failed.")
            return

        # 5. Parse Title & Category
        lines = response.split('\n')
        title = "Untitled Insight"
        content_start_idx = 0
        for i, line in enumerate(lines):
            clean = line.strip().replace('*', '').replace('#', '').strip()
            if clean.lower().startswith("title:"):
                title = clean.split(":", 1)[1].strip()
                content_start_idx = i + 1
                break
        
        content_body = "\n".join(lines[content_start_idx:]).strip() or response
        safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')]).strip()
        
        # Category majority logic
        categories = [item['category'] for item in l1_data if item.get('category')]
        most_common = Counter(categories).most_common(1)
        l2_category = most_common[0][0] if most_common and most_common[0][1] >= len(categories) / 2 else "General"
        
        # 6. Save to DB
        l2_uuid = generate_uuid_v7()
        self.db.save_l2_version(l2_uuid, title, content_body, l2_category)
        self.db.add_l2_members(l2_uuid, l1_uuids)
        logger.info(f"Saved L2 Version (UUID: {l2_uuid})")

        # 7. Write Shadow File
        path = self.paths.get_l2_path(l2_category, safe_title)
        self.paths.ensure_dirs_for_path(path)
        
        # 7a. Extract Keywords for Tags
        tags = extract_tags(content_body)

        try:
            with open(path, 'w', encoding='utf-8') as f:
                header = {
                    "l2_uuid": l2_uuid,
                    "sources": [d['path'] for d in l1_data],
                    "tags": tags,
                    "created": datetime.now().isoformat()
                }
                f.write(f"---\n{json.dumps(header, indent=2, ensure_ascii=False)}\n---\n\n# {title}\n\n{content_body}")
            set_file_permissions(path)
            logger.info(f"Wrote L2 Shadow File: {path}")
        except Exception as e:
            logger.error(f"L2 File Write Failed: {e}")

        # 8. Review Template
        self._generate_review_template(l2_uuid, path, content_body, l2_category)

    def _generate_review_template(self, l2_uuid: str, shadow_path: str, content_body: str, category: str):
        review_path = self.paths.get_l2_review_path(category, os.path.basename(shadow_path).replace("[L2] ", "").replace(".md", ""))
        self.paths.ensure_dirs_for_path(review_path)
        new_review_id = generate_uuid_v7()
        quoted_content = "\n".join([f"> {line}" for line in content_body.split('\n')])
        
        template = f"""---
review_id: {new_review_id}
l2_id: {l2_uuid}
rating: PENDING     # GOOD, OK, BAD
decision: PENDING   # ACCEPT, REBUILD, DISCARD
issues: []
created_at: {datetime.now().isoformat()}
---
# Review for {os.path.basename(shadow_path)}

### Notes
Please write your feedback here...

## Reference: Original L2 Insight
{quoted_content}
"""
        try:
            with open(review_path, 'w', encoding='utf-8') as f:
                f.write(template)
            set_file_permissions(review_path)
            logger.info(f"Generated L2 Review Template: {review_path}")
        except Exception as e:
            logger.error(f"Failed to generate L2 review template: {e}")
