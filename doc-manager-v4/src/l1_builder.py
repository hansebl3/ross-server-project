import os
import logging
import json
from datetime import datetime
from typing import Optional, List, Any

from database import Database
from llm_client import LLMClient
from prompt_loader import PromptLoader
from utils import generate_uuid_v7, PathManager, parse_frontmatter, calculate_file_hash, set_file_permissions, extract_tags
import globals

logger = logging.getLogger("L1Builder")

class L1Builder:
    def __init__(self, db: Database, config_dir: str, shadow_dir: str):
        self.db = db
        self.prompt_loader = PromptLoader(config_dir)
        self.llm_client = LLMClient()
        self.paths = PathManager(shadow_dir)

    def build_l1(self, doc_uuid: str, review_notes: Optional[str] = None):
        """Generates L1 summary for the given document UUID."""
        if not globals.try_acquire_build(doc_uuid):
            logger.info(f"Build already in progress for {doc_uuid}. Skipping.")
            return

        try:
            logger.info(f"Starting Build for Doc UUID: {doc_uuid}")
            if review_notes:
                logger.info(f"Incorporating Review Notes: {review_notes}")
            
            # 1. Fetch document
            doc = self.db.get_document_by_uuid(doc_uuid)
            if not doc:
                logger.error(f"Document {doc_uuid} not found in DB.")
                return

            doc_content = doc['content']
            if review_notes:
                doc_content = f"{doc_content}\n\n[USER FEEDBACK FOR REBUILD]:\n{review_notes}"
                
            doc_path = doc['path']
            
            # 2. Resolve hierarchical category for prompt matching
            # 01_Sources/A/B/file.md -> A/B
            parts = doc_path.split(os.sep)
            
            # Find the index of the source root (e.g., '01_Sources')
            source_root_idx = -1
            for i, part in enumerate(parts):
                if part.endswith('_Sources'): # Matches '01_Sources', etc.
                    source_root_idx = i
                    break
            
            if source_root_idx != -1 and len(parts) > source_root_idx + 2:
                # Base category is the first folder after 01_Sources
                base_cat = parts[source_root_idx+1]
                # Extract everything between source root and filename for prompt match
                hierarchical_cat = os.path.join(*parts[source_root_idx+1:-1])
            elif len(parts) > 2:
                base_cat = parts[1]
                hierarchical_cat = os.path.join(*parts[1:-1])
            else:
                base_cat = "General"
                hierarchical_cat = "General"

            # 3. Load prompt
            try:
                active_prompt = self.prompt_loader.load_prompt_for_category(hierarchical_cat)
            except Exception as e:
                logger.error(f"Failed to load active prompt for {hierarchical_cat}: {e}")
                return

            # 4. Prepare model config (Supports flat keys and legacy nested 'model' dict)
            cfg = active_prompt.config
            model_val = cfg.get("model")
            
            if isinstance(model_val, dict):
                # Legacy nested style
                model_info = {
                    "model": model_val.get("name", "gpt-oss-120b"),
                    "provider": model_val.get("provider", "llama.cpp"),
                    "temperature": model_val.get("temperature", 0.7),
                    "max_tokens": model_val.get("max_tokens", 2048)
                }
            else:
                # New flat style OR legacy string style
                model_info = {
                    "model": model_val or "gpt-oss-120b",
                    "provider": cfg.get("provider", "llama.cpp"),
                    "temperature": cfg.get("temperature", 0.7),
                    "max_tokens": cfg.get("max_tokens", 2048)
                }

            # 4. Generate Summary
            logger.info(f"Generating Summary for {doc_path} using {model_info['model']}...")
            summary = self.llm_client.generate_text_summary(
                system_prompt=active_prompt.content,
                user_content=doc_content,
                **model_info
            )
            
            if not summary:
                logger.error("LLM Generation failed.")
                return

            # 5. Track Prompt Version
            import uuid as py_uuid
            config_str = json.dumps(active_prompt.config, sort_keys=True)
            prompt_id = str(py_uuid.uuid5(py_uuid.NAMESPACE_DNS, f"{active_prompt.content}|{config_str}"))
            self.db.ensure_prompt_version(prompt_id, hierarchical_cat, active_prompt.content, active_prompt.config)

            # 6. Save L1 Version
            new_l1_uuid = generate_uuid_v7()
            version = self.db.save_l1_version(new_l1_uuid, doc_uuid, summary, model_info, prompt_id)
            logger.info(f"Saved L1 Version {version} (UUID: {new_l1_uuid})")

            # 7. Embedding
            if embedding := self.llm_client.get_embedding(summary):
                self.db.insert_l1_embedding(new_l1_uuid, embedding)
                logger.info("Saved Embedding.")

            # 8. Shadow Library Creation
            shadow_path = self.paths.get_l1_path(base_cat, doc_path)
            self.paths.ensure_dirs_for_path(shadow_path)
            
            # 8a. Extract Keywords for Tags
            # 8a. Extract Keywords for Tags
            tags = extract_tags(summary)
            
            try:
                with open(shadow_path, 'w', encoding='utf-8') as f:
                    # Create Obsidian-friendly links
                    source_link = f"[[{doc_path}]]"
                    prompt_link = f"[[{os.path.basename(active_prompt.path)}]]" if hasattr(active_prompt, 'path') else "Unknown"

                    header = {
                        "source_uuid": str(doc_uuid),
                        "source": source_link,
                        "l1_uuid": str(new_l1_uuid),
                        "prompt_id": str(prompt_id),
                        "prompt": prompt_link,
                        "version": version,
                        "tags": tags
                    }
                    
                    # Build body with summary and source reference
                    # Remove review notes if they were injected
                    clean_summary = summary
                    if review_notes and "[USER FEEDBACK FOR REBUILD]:" in summary:
                        clean_summary = summary.split("[USER FEEDBACK FOR REBUILD]:")[0].strip()
                    
                    body = clean_summary
                    f.write(globals.format_frontmatter(header, body))
                
                # Update system write cache to prevent Watcher loop
                try:
                    with open(shadow_path, 'r', encoding='utf-8') as f:
                        new_content = f.read()
                    h = calculate_file_hash(new_content, shadow_path)
                    globals.mark_system_write(shadow_path, h)
                except Exception: pass
                
                set_file_permissions(shadow_path)
                logger.info(f"Wrote Shadow File: {shadow_path}")
            except Exception as e:
                logger.error(f"Shadow File Write Failed: {e}")

            # 9. Review Template
            self._generate_review_template(new_l1_uuid, shadow_path, summary, active_prompt, doc_path)
        
        finally:
            globals.release_build(doc_uuid)

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Utility to get embedding for a text."""
        return self.llm_client.get_embedding(text)

    def _generate_review_template(self, l1_uuid: str, shadow_path: str, summary_content: str, prompt, doc_path: str):
        review_path = self.paths.get_l1_review_path(prompt.category, shadow_path)
        
        # Always generate fresh review for new L1 versions
        # (If this is a REBUILD, the new l1_uuid will be different and needs a new review)
        
        self.paths.ensure_dirs_for_path(review_path)
        new_review_id = generate_uuid_v7()
        quoted_summary = "\n".join([f"> {line}" for line in summary_content.split('\n')])
        # Use filename instead of full path if available
        prompt_fname = os.path.basename(getattr(prompt, 'path', 'Unknown'))
        
        header = {
            "review_id": str(new_review_id),
            "l1_id": str(l1_uuid),
            "rating": "PENDING",
            "decision": "PENDING",
            "issues": [],
            "prompt_file": prompt_fname,
            "created_at": datetime.now().isoformat()
        }
        
        body = f"# Review for {os.path.basename(shadow_path)}\n\n### Notes\nPlease write your feedback here...\n\n## Reference: Original Summary\n{quoted_summary}\n"
        
        # Obsidian Links
        source_link = f"[[{doc_path}]]"
        prompt_link = f"[[{prompt_fname}]]"

        # Manual YAML construction with inline comments for user guidance
        template = f"""---
review_id: {header['review_id']}
l1_id: {header['l1_id']}
rating: {header['rating']}  # GOOD, OK, BAD
decision: {header['decision']}  # ACCEPT: 승인, REBUILD: 재생성, DISCARD: 삭제
issues: []  # 예: ["typo", "hallucination", "missing_context"]
source: '{source_link}'
prompt: '{prompt_link}'
prompt_file: {header['prompt_file']}
created_at: {header['created_at']}
---

{body}"""
        
        try:
            with open(review_path, 'w', encoding='utf-8') as f:
                f.write(template)
            
            # Update system write cache to prevent Watcher loop
            try:
                h = calculate_file_hash(template, review_path)
                globals.mark_system_write(review_path, h)
            except Exception: pass
                
            set_file_permissions(review_path)
            logger.info(f"Generated Review Template: {review_path}")
        except Exception as e:
            logger.error(f"Failed to generate review template: {e}")
