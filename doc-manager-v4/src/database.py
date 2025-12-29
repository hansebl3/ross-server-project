import os
import psycopg2
import psycopg2.extras
from psycopg2.extensions import connection
import logging
import json
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.host = os.getenv("POSTGRES_HOST", "127.0.0.1")
        self.port = int(os.getenv("POSTGRES_PORT", 5432))
        self.user = os.getenv("POSTGRES_USER", "postgres")
        self.db_name = os.getenv("DOC_MANAGER_DB", "doc_manager_v4")
        
        # Security: Fail if password is not set
        self.password = os.getenv("POSTGRES_PASSWORD")
        if self.password is None:
            raise ValueError("POSTGRES_PASSWORD environment variable is not set. Cannot connect to database.")
            
        self._conn: Optional[connection] = None

    def get_connection(self) -> connection:
        if self._conn is None or self._conn.closed:
            try:
                self._conn = psycopg2.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    dbname=self.db_name
                )
                self._conn.autocommit = True
                # Set session timezone to KST
                with self._conn.cursor() as cur:
                    cur.execute("SET TIME ZONE 'Asia/Seoul';")
            except Exception as e:
                logger.error(f"Failed to connect to PostgreSQL: {e}")
                raise
        return self._conn

    def create_db_if_missing(self):
        conn = psycopg2.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            dbname="postgres"
        )
        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (self.db_name,))
                if not cur.fetchone():
                    logger.info(f"Database '{self.db_name}' not found. Creating...")
                    cur.execute(f"CREATE DATABASE {self.db_name}")
                else:
                    logger.info(f"Database '{self.db_name}' already exists.")
        finally:
            conn.close()

    def init_db(self):
        self.create_db_if_missing()
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                schema_path = os.path.join(os.path.dirname(__file__), 'db', 'schema.sql')
                with open(schema_path, 'r') as f:
                    schema_sql = f.read()
                cur.execute(schema_sql)
            logger.info("Schema initialized successfully.")
        except Exception as e:
            logger.error(f"Schema initialization failed: {e}")
            raise

    # --- Document Methods ---

    def get_document_by_path(self, path: str) -> Optional[Dict[str, Any]]:
        conn = self.get_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT * FROM documents WHERE path = %s", (path,))
            result = cur.fetchone()
            return dict(result) if result else None

    def get_document_by_uuid(self, uuid: str) -> Optional[Dict[str, Any]]:
        conn = self.get_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT * FROM documents WHERE uuid = %s", (uuid,))
            result = cur.fetchone()
            return dict(result) if result else None

    def upsert_document(self, uuid: str, path: str, content: str, content_hash: str, category: str = "General"):
        conn = self.get_connection()
        query = """
        INSERT INTO documents (uuid, path, content, content_hash, category, updated_at)
        VALUES (%s, %s, %s, %s, %s, NOW())
        ON CONFLICT (uuid) DO UPDATE SET
            path = EXCLUDED.path,
            content = EXCLUDED.content,
            content_hash = EXCLUDED.content_hash,
            category = EXCLUDED.category,
            updated_at = NOW();
        """
        with conn.cursor() as cur:
            cur.execute(query, (uuid, path, content, content_hash, category))

    def delete_document(self, uuid: str):
        """Deletes a document and its associated L1 versions (manual cascade)."""
        conn = self.get_connection()
        with conn.cursor() as cur:
            # 1. Get L1 IDs
            cur.execute("SELECT l1_id FROM l1_versions WHERE source_uuid = %s", (uuid,))
            l1_ids = [row[0] for row in cur.fetchall()]
            
            if l1_ids:
                # 2. Delete L1 Embeddings & Reviews
                cur.execute("DELETE FROM l1_embeddings WHERE l1_id = ANY(%s::uuid[])", (l1_ids,))
                cur.execute("DELETE FROM l1_reviews WHERE l1_id = ANY(%s::uuid[])", (l1_ids,))
                # 3. Delete L2 Members
                cur.execute("DELETE FROM l2_members WHERE l1_id = ANY(%s::uuid[])", (l1_ids,))
                # 4. Delete L1 Versions
                cur.execute("DELETE FROM l1_versions WHERE source_uuid = %s", (uuid,))
            
            # 5. Delete Document
            cur.execute("DELETE FROM documents WHERE uuid = %s", (uuid,))

    # --- Prompt Methods ---

    def ensure_prompt_version(self, prompt_id: str, category: str, content: str, model_config: Dict[str, Any]) -> str:
        conn = self.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT prompt_id FROM prompt_versions WHERE prompt_id = %s", (prompt_id,))
            if cur.fetchone():
                return prompt_id
            
            cur.execute("""
                INSERT INTO prompt_versions (prompt_id, category, content, model_config, active)
                VALUES (%s, %s, %s, %s, TRUE)
            """, (prompt_id, category, content, json.dumps(model_config)))
            return prompt_id

    # --- L1 Summary Methods ---

    def save_l1_version(self, l1_id: str, source_uuid: str, content: str, model_config: Dict[str, Any], prompt_id: str) -> int:
        conn = self.get_connection()
        with conn.cursor() as cur:
            # Get next version number
            cur.execute("SELECT MAX(version) FROM l1_versions WHERE source_uuid = %s", (source_uuid,))
            res = cur.fetchone()
            next_version = (res[0] if res[0] else 0) + 1
            
            # Supersede existing active version
            cur.execute("SELECT l1_id FROM l1_versions WHERE source_uuid = %s AND status = 'ACTIVE'", (source_uuid,))
            old_l1_ids = [row[0] for row in cur.fetchall()]
            
            if old_l1_ids:
                # 1. Delete old embeddings to keep Vector DB clean
                cur.execute("DELETE FROM l1_embeddings WHERE l1_id = ANY(%s::uuid[])", (old_l1_ids,))
                # 2. Update status to SUPERSEDED
                cur.execute("UPDATE l1_versions SET status = 'SUPERSEDED' WHERE l1_id = ANY(%s::uuid[])", (old_l1_ids,))
            
            # Insert new version
            cur.execute("""
                INSERT INTO l1_versions (l1_id, source_uuid, version, content, status, model_id, prompt_id, created_at)
                VALUES (%s, %s, %s, %s, 'ACTIVE', %s, %s, NOW())
            """, (l1_id, source_uuid, next_version, content, json.dumps(model_config), prompt_id))
            return next_version

    def get_source_uuid_by_l1(self, l1_id: str) -> Optional[str]:
        """Returns the source_uuid associated with an L1 version."""
        conn = self.get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT source_uuid FROM l1_versions WHERE l1_id = %s", (l1_id,))
            result = cur.fetchone()
            return result[0] if result else None

    def insert_l1_embedding(self, l1_id: str, embedding: List[float]):
        """Inserts a new L1 embedding."""
        conn = self.get_connection()
        with conn.cursor() as cur:
            cur.execute("INSERT INTO l1_embeddings (l1_id, embedding) VALUES (%s, %s)", (l1_id, embedding))

    def update_l1_content_and_embedding(self, l1_id: str, content: str, embedding: List[float]):
        """Updates content and embedding for an existing L1 version (for manual sync)."""
        conn = self.get_connection()
        with conn.cursor() as cur:
            # Update content and flag it as manual refinement
            cur.execute("""
                UPDATE l1_versions 
                SET content = %s, 
                    model_id = 'manual_refinement',
                    created_at = NOW() 
                WHERE l1_id = %s
            """, (content, l1_id))
            
            # Update embedding
            cur.execute("DELETE FROM l1_embeddings WHERE l1_id = %s", (l1_id,))
        
        self.insert_l1_embedding(l1_id, embedding)

    def upsert_l1_review(self, review_id: str, l1_id: str, rating: str, decision: str, issues: List[str], notes: str):
        conn = self.get_connection()
        query = """
        INSERT INTO l1_reviews (review_id, l1_id, rating, decision, issues, notes, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (review_id) DO UPDATE SET
            rating = EXCLUDED.rating,
            decision = EXCLUDED.decision,
            issues = EXCLUDED.issues,
            notes = EXCLUDED.notes;
        """
        with conn.cursor() as cur:
            cur.execute(query, (review_id, l1_id, rating, decision, issues, notes))

    def delete_review(self, review_id: str):
        """Deletes a review record from the database."""
        conn = self.get_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM l1_reviews WHERE review_id = %s", (review_id,))
            cur.execute("DELETE FROM l2_reviews WHERE review_id = %s", (review_id,))

    # --- L2 Insight Methods ---

    def save_l2_version(self, l2_id: str, title: str, content: str, category: str) -> str:
        conn = self.get_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO l2_versions (l2_id, title, content, category, created_at)
                VALUES (%s, %s, %s, %s, NOW())
            """, (l2_id, title, content, category))
        return l2_id

    def add_l2_members(self, l2_id: str, l1_uuids: List[str]):
        conn = self.get_connection()
        with conn.cursor() as cur:
            for l1_id in l1_uuids:
                cur.execute("INSERT INTO l2_members (l2_id, l1_id) VALUES (%s, %s)", (l2_id, l1_id))

    def get_l1_data_for_l2(self, l1_uuids: List[str]) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        data = []
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            for uid in l1_uuids:
                cur.execute("""
                    SELECT v.content, d.path, d.category 
                    FROM l1_versions v
                    JOIN documents d ON v.source_uuid = d.uuid
                    WHERE v.l1_id = %s
                """, (uid,))
                row = cur.fetchone()
                if row:
                    data.append({
                        "id": uid,
                        "content": row['content'],
                        "path": row['path'],
                        "category": row['category']
                    })
        return data

    def upsert_l2_review(self, review_id: str, l2_id: str, rating: str, decision: str, issues: List[str], notes: str):
        conn = self.get_connection()
        query = """
        INSERT INTO l2_reviews (review_id, l2_id, rating, decision, issues, notes, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (review_id) DO UPDATE SET
            rating = EXCLUDED.rating,
            decision = EXCLUDED.decision,
            issues = EXCLUDED.issues,
            notes = EXCLUDED.notes;
        """
        with conn.cursor() as cur:
            cur.execute(query, (review_id, l2_id, rating, decision, issues, notes))

    def close(self):
        if self._conn and not self._conn.closed:
            self._conn.close()
