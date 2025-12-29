import logging
import json
from typing import List, Tuple, Dict
from database import Database

logger = logging.getLogger("Clustering")

class SimilaritySearch:
    def __init__(self, db: Database):
        self.db = db

    def find_related_l1(self, target_l1_uuid: str, limit: int = 5, threshold: float = 0.70) -> List[Dict]:
        """
        Finds L1 summaries related to the target L1 UUID based on embedding similarity.
        Returns a list of dicts: { 'l1_id': ..., 'similarity': ..., 'content': ..., 'path': ... }
        """
        conn = self.db.get_connection()
        
        # 1. Get Target Embedding
        with conn.cursor() as cur:
            cur.execute("SELECT embedding FROM l1_embeddings WHERE l1_id = %s", (target_l1_uuid,))
            row = cur.fetchone()
            
        if not row:
            logger.warning(f"No embedding found for L1 {target_l1_uuid}")
            return []
            
        target_embedding = row[0] # String representation of vector
        
        # 2. Search
        # We join with l1_versions and documents to get content and context.
        # We filter out the target itself.
        # We ensure we only look at ACTIVE versions? Review: "ACTIVE" constraint is on l1_versions.
        # But embeddings are per l1_id.
        
        query = """
            SELECT 
                e.l1_id, 
                1 - (e.embedding <=> %s) as similarity,
                v.content,
                d.path,
                d.category
            FROM l1_embeddings e
            JOIN l1_versions v ON e.l1_id = v.l1_id
            JOIN documents d ON v.source_uuid = d.uuid
            WHERE e.l1_id != %s
            AND v.status = 'ACTIVE' 
            AND 1 - (e.embedding <=> %s) > %s
            ORDER BY similarity DESC
            LIMIT %s;
        """
        
        results = []
        try:
            with conn.cursor() as cur:
                cur.execute(query, (target_embedding, target_l1_uuid, target_embedding, threshold, limit))
                rows = cur.fetchall()
                
            for row in rows:
                results.append({
                    "l1_id": str(row[0]),
                    "similarity": float(row[1]),
                    "content": row[2],
                    "path": row[3],
                    "category": row[4]
                })
                
        except Exception as e:
            logger.error(f"Similarity Search Failed: {e}")
            
        return results

    def format_for_prompt(self, related_docs: List[Dict]) -> str:
        """Helper to format related docs for LLM Context."""
        text = ""
        for i, doc in enumerate(related_docs):
            text += f"--- Document {i+1} ---\n"
            text += f"Source: {doc['path']}\n"
            text += f"Content:\n{doc['content']}\n\n"
        return text
