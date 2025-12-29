import os
import logging
import psycopg2.extras
from database import Database
from utils import PathManager

logger = logging.getLogger("Deleter")

class Deleter:
    def __init__(self, db: Database, vault_root: str):
        self.db = db
        self.vault_root = vault_root
        shadow_dir = os.path.join(vault_root, "99_Shadow_Library")
        self.paths = PathManager(shadow_dir)

    def delete_l0(self, doc_uuid: str) -> dict:
        """Deletes L0 and its associated L1/L2 records from DB."""
        impact = {"l0": 0, "l1": 0, "l2": 0, "files": []}
        doc = self.db.get_document_by_uuid(doc_uuid)
        if not doc: return impact

        conn = self.db.get_connection()
        with conn.cursor() as cur:
            # 1. Find all L1s
            cur.execute("SELECT l1_id FROM l1_versions WHERE source_uuid = %s", (doc_uuid,))
            l1_ids = [r[0] for r in cur.fetchall()]
            
            for l1_id in l1_ids:
                res = self.delete_l1(l1_id)
                impact['l1'] += 1
                impact['files'].extend(res['files'])

            # 2. Delete L0
            cur.execute("DELETE FROM documents WHERE uuid = %s", (doc_uuid,))
            impact['l0'] = 1
            
        logger.info(f"Deleted L0: {doc_uuid}")
        return impact

    def delete_l1(self, l1_id: str) -> dict:
        """Deletes L1 and its shadow files/embeddings/reviews."""
        impact = {"l1": 1, "l2": 0, "reviews": 0, "files": []}
        conn = self.db.get_connection()
        
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) if hasattr(psycopg2.extras, 'DictCursor') else conn.cursor() as cur:
            # Get info for file deletion
            cur.execute("""
                SELECT v.content, d.path as doc_path, d.category 
                FROM l1_versions v 
                JOIN documents d ON v.source_uuid = d.uuid 
                WHERE v.l1_id = %s
            """, (l1_id,))
            row = cur.fetchone()
            if not row: return impact
            
            # Handle both dict and tuple results
            row_dict = dict(row) if not isinstance(row, dict) else row
            category = row_dict['category']
            doc_path = row_dict['doc_path']

            # 1. Paths
            shadow_path = self.paths.get_l1_path(category, doc_path)
            review_path = self.paths.get_l1_review_path(category, shadow_path)
            
            for p in [shadow_path, review_path]:
                if os.path.exists(p):
                    os.remove(p)
                    impact['files'].append(p)

            # 2. Reviews count for impact
            cur.execute("SELECT COUNT(*) FROM l1_reviews WHERE l1_id = %s", (l1_id,))
            impact['reviews'] = cur.fetchone()[0]

            # 3. DB (Order matters for constraints)
            cur.execute("DELETE FROM l2_members WHERE l1_id = %s", (l1_id,))
            cur.execute("DELETE FROM l1_embeddings WHERE l1_id = %s", (l1_id,))
            cur.execute("DELETE FROM l1_reviews WHERE l1_id = %s", (l1_id,))
            cur.execute("DELETE FROM l1_versions WHERE l1_id = %s", (l1_id,))
            
        logger.info(f"Deleted L1: {l1_id}")
        return impact

    def preview_delete_l0(self, doc_uuid: str) -> dict:
        """Previews the impact of deleting an L0 document."""
        impact = {"l0": 1, "l1": 0, "l2": 0, "reviews": 0, "files": []}
        conn = self.db.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT l1_id FROM l1_versions WHERE source_uuid = %s", (doc_uuid,))
            l1_ids = [r[0] for r in cur.fetchall()]
            impact["l1"] = len(l1_ids)
            for l1_id in l1_ids:
                l1_impact = self.preview_delete_l1(l1_id)
                impact["reviews"] += l1_impact["reviews"]
                impact["files"].extend(l1_impact["files"])
        return impact

    def preview_delete_l1(self, l1_id: str) -> dict:
        """Previews the impact of deleting an L1 summary."""
        impact = {"l1": 1, "l2": 0, "reviews": 0, "files": []}
        conn = self.db.get_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) if hasattr(psycopg2.extras, 'DictCursor') else conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM l1_reviews WHERE l1_id = %s", (l1_id,))
            impact["reviews"] = cur.fetchone()[0]
            
            cur.execute("""
                SELECT v.content, d.path as doc_path, d.category 
                FROM l1_versions v 
                JOIN documents d ON v.source_uuid = d.uuid 
                WHERE v.l1_id = %s
            """, (l1_id,))
            row = cur.fetchone()
            if row:
                row_dict = dict(row) if not isinstance(row, dict) else row
                shadow_path = self.paths.get_l1_path(row_dict['category'], row_dict['doc_path'])
                review_path = self.paths.get_l1_review_path(row_dict['category'], shadow_path)
                for p in [shadow_path, review_path]:
                    if os.path.exists(p): impact["files"].append(p)
        return impact

    def delete_l2(self, l2_id: str) -> dict:
        """Deletes L2 and its shadow files/reviews."""
        impact = {"l2": 1, "reviews": 0, "files": []}
        conn = self.db.get_connection()
        
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) if hasattr(psycopg2.extras, 'DictCursor') else conn.cursor() as cur:
            cur.execute("SELECT title, category FROM l2_versions WHERE l2_id = %s", (l2_id,))
            row = cur.fetchone()
            if not row: return impact
            
            row_dict = dict(row) if not isinstance(row, dict) else row
            category = row_dict['category']
            safe_title = "".join([c for c in row_dict['title'] if c.isalnum() or c in (' ', '-', '_')]).strip()

            # 1. Paths
            shadow_path = self.paths.get_l2_path(category, safe_title)
            review_path = self.paths.get_l2_review_path(category, safe_title)
            
            for p in [shadow_path, review_path]:
                if os.path.exists(p):
                    os.remove(p)
                    impact['files'].append(p)

            # 2. Reviews count for impact
            cur.execute("SELECT COUNT(*) FROM l2_reviews WHERE l2_id = %s", (l2_id,))
            impact['reviews'] = cur.fetchone()[0]

            # 3. DB
            cur.execute("DELETE FROM l2_embeddings WHERE l2_id = %s", (l2_id,))
            cur.execute("DELETE FROM l2_reviews WHERE l2_id = %s", (l2_id,))
            cur.execute("DELETE FROM l2_members WHERE l2_id = %s", (l2_id,))
            cur.execute("DELETE FROM l2_versions WHERE l2_id = %s", (l2_id,))

        logger.info(f"Deleted L2: {l2_id}")
        return impact

    def preview_delete_l2(self, l2_id: str) -> dict:
        """Previews the impact of deleting an L2 insight."""
        impact = {"l2": 1, "reviews": 0, "files": []}
        conn = self.db.get_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) if hasattr(psycopg2.extras, 'DictCursor') else conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM l2_reviews WHERE l2_id = %s", (l2_id,))
            impact["reviews"] = cur.fetchone()[0]
            
            cur.execute("SELECT title, category FROM l2_versions WHERE l2_id = %s", (l2_id,))
            row = cur.fetchone()
            if row:
                row_dict = dict(row) if not isinstance(row, dict) else row
                safe_title = "".join([c for c in row_dict['title'] if c.isalnum() or c in (' ', '-', '_')]).strip()
                shadow_path = self.paths.get_l2_path(row_dict['category'], safe_title)
                review_path = self.paths.get_l2_review_path(row_dict['category'], safe_title)
                for p in [shadow_path, review_path]:
                    if os.path.exists(p): impact["files"].append(p)
        return impact


