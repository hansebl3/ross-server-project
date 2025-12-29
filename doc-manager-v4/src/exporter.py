import os
import json
import logging
from typing import List, Dict

from database import Database
from prompt_loader import PromptLoader

logger = logging.getLogger("Exporter")

class DatasetExporter:
    def __init__(self, db: Database, config_dir: str):
        self.db = db
        self.prompt_loader = PromptLoader(config_dir)

    def export_sft(self, output_path: str):
        """
        Exports Supervised Fine-Tuning (SFT) dataset.
        Format: {"messages": [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}]}
        Source: Active L1 versions.
        """
        logger.info("Exporting SFT Dataset...")
        
        conn = self.db.get_connection()
        query = """
            SELECT 
                d.uuid, d.content as l0_content, d.category,
                v.content as l1_content, v.model_id
            FROM l1_versions v
            JOIN documents d ON v.source_uuid = d.uuid
            WHERE v.status = 'ACTIVE'
        """
        
        count = 0
        try:
            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()
                
            with open(output_path, 'w', encoding='utf-8') as f:
                for row in rows:
                    l0_content = row[1]
                    category = row[2] or "General"
                    l1_content = row[3]
                    
                    # Try to load prompt for category to be accurate
                    try:
                        prompt_obj = self.prompt_loader.load_prompt_for_category(category)
                        system_content = prompt_obj.content
                    except:
                        system_content = "You are a helpful assistant."
                        
                    entry = {
                        "messages": [
                            {"role": "system", "content": system_content},
                            {"role": "user", "content": l0_content},
                            {"role": "assistant", "content": l1_content}
                        ]
                    }
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                    count += 1
            
            logger.info(f"Exported {count} SFT samples to {output_path}")
            
        except Exception as e:
            logger.error(f"SFT Export Failed: {e}")

    def export_dpo(self, output_path: str):
        """
        Exports Direct Preference Optimization (DPO) dataset.
        Format: {"prompt": ..., "chosen": ..., "rejected": ...}
        Source: Pairs of (Active L1) vs (Superseded L1) for same document.
        """
        logger.info("Exporting DPO Dataset...")
        
        conn = self.db.get_connection()
        
        # Strategy: For each Source UUID, get Active (Chosen) and one Superseded (Rejected)
        query_docs = "SELECT DISTINCT source_uuid FROM l1_versions WHERE status = 'ACTIVE'"
        
        count = 0
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                with conn.cursor() as cur:
                    cur.execute(query_docs)
                    doc_uuids = [r[0] for r in cur.fetchall()]
                    
                    for doc_uuid in doc_uuids:
                        # Fetch Chosen
                        cur.execute("""
                            SELECT v.content, d.content as l0_content, d.category
                            FROM l1_versions v
                            JOIN documents d ON v.source_uuid = d.uuid
                            WHERE v.source_uuid = %s AND v.status = 'ACTIVE'
                        """, (doc_uuid,))
                        chosen_row = cur.fetchone()
                        if not chosen_row: continue
                        
                        chosen_text = chosen_row[0]
                        prompt_text = chosen_row[1] # L0 content is the prompt usually
                        category = chosen_row[2] or "General"
                        
                        # Fetch Rejected (Just pick one random Superseded)
                        cur.execute("""
                            SELECT content FROM l1_versions 
                            WHERE source_uuid = %s AND status = 'SUPERSEDED'
                            LIMIT 1
                        """, (doc_uuid,))
                        rejected_row = cur.fetchone()
                        
                        if rejected_row:
                            rejected_text = rejected_row[0]
                            
                            # Construct Prompt (System + User)
                            try:
                                prompt_obj = self.prompt_loader.load_prompt_for_category(category)
                                system_content = prompt_obj.content
                            except:
                                system_content = "You are a helpful assistant."
                            
                            full_prompt = f"{system_content}\n\nUser: {prompt_text}\n\nAssistant:"
                            
                            entry = {
                                "prompt": full_prompt,
                                "chosen": chosen_text,
                                "rejected": rejected_text
                            }
                            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                            count += 1
                            
            logger.info(f"Exported {count} DPO pairs to {output_path}")

        except Exception as e:
            logger.error(f"DPO Export Failed: {e}")
