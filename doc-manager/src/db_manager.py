import psycopg2
from psycopg2.extras import RealDictCursor, Json
import psycopg2.pool
import pgvector.psycopg2
import logging
import uuid
import json
from contextlib import contextmanager
from utils.config_loader import load_config
from utils.worker_manager import ensure_worker_running

logger = logging.getLogger(__name__)

class DBManager:
    """
    Database Manager for handling MariaDB connections and schema migrations.
    
    Responsibilities:
    1. **Connection Pooling**: Manages `psycopg2` connection pool (min=1, max=20).
    2. **Schema Management**: Auto-initializes tables (`documents`, `categories`) and applied migrations.
    3. **Vector Support**: Enables `pgvector` extension for embedding storage.
    
    Configuration:
    - Reads connection params from `config.json` (overridden by `.env` variables).
    """
    def __init__(self):
        config = load_config()
        self.conn_params = config['database']
        
        # Initialize Connection Pool
        self.pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1, 
            maxconn=20, 
            **self.conn_params
        )
        self._init_db()

    @contextmanager
    def get_conn(self):
        conn = self.pool.getconn()
        try:
            yield conn
        finally:
            self.pool.putconn(conn)

    def _init_db(self):
        with self.get_conn() as conn:
            try:
                with conn.cursor() as cur:
                    # Enable pgvector and register it
                    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                    pgvector.psycopg2.register_vector(cur)
                    
                    # Create documents table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS documents (
                            id UUID PRIMARY KEY,
                            title TEXT,
                            category TEXT NOT NULL,
                            level TEXT,
                            metadata JSONB,
                            content TEXT,
                            summary_uuids JSONB DEFAULT '[]'::jsonb,
                            source_uuids JSONB DEFAULT '[]'::jsonb,
                            embedding vector(384),
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    
                    # Migration: Add level column if not exists and migrate data
                    try:
                        cur.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS level TEXT;")
                        cur.execute("""
                            UPDATE documents 
                            SET level = category, category = 'General' 
                            WHERE level IS NULL AND category IN ('L0', 'L1', 'L2', 'L3');
                        """)
                        cur.execute("UPDATE documents SET level = 'L0' WHERE level IS NULL;")
                    except Exception as e:
                        logger.warning(f"Migration error (level): {e}")

                    # Migration: Add title column
                    try:
                        cur.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS title TEXT;")
                        cur.execute("""
                            UPDATE documents 
                            SET title = SUBSTRING(content FROM 1 FOR 20)
                            WHERE title IS NULL;
                        """)
                    except Exception as e:
                        logger.warning(f"Migration error (title): {e}")

                    # Migration: Add source_uuids
                    try:
                        cur.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_uuids JSONB DEFAULT '[]'::jsonb;")
                    except Exception as e:
                        logger.warning(f"Migration error (source_uuids): {e}")

                    # Create categories table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS categories (
                            name TEXT PRIMARY KEY,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    
                    # Initialize default categories if table is empty
                    cur.execute("SELECT COUNT(*) FROM categories;")
                    # Fetch the result from the cursor
                    count_result = cur.fetchone()
                    if count_result and count_result[0] == 0: # Access by index for non-RealDictCursor
                        defaults = ["General", "Personal", "CTC", "Proposal"]
                        for d in defaults:
                            cur.execute("INSERT INTO categories (name) VALUES (%s) ON CONFLICT DO NOTHING;", (d,))

                    # Create processing tasks table (QUEUE)
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS processing_tasks (
                            doc_id UUID PRIMARY KEY,
                            status TEXT DEFAULT 'created', 
                            config JSONB DEFAULT '{}'::jsonb, 
                            results JSONB DEFAULT '{}'::jsonb,
                            results_model_l JSONB,
                            results_model_r JSONB,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    
                    # Migration: Add results_model_l/r if they don't exist
                    try:
                        cur.execute("ALTER TABLE processing_tasks ADD COLUMN IF NOT EXISTS results_model_l JSONB;")
                        cur.execute("ALTER TABLE processing_tasks ADD COLUMN IF NOT EXISTS results_model_r JSONB;")
                    except:
                        pass
                    
                    # Create prompts table (Prompt Lab)
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS prompts (
                            alias TEXT PRIMARY KEY,
                            prompt_text TEXT NOT NULL,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        );
                    """)

                    # Indexes
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_docs_category ON documents(category);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_docs_level ON documents(level);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_docs_metadata ON documents USING gin(metadata);")
                    cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON processing_tasks(status);")
                    
                    conn.commit()
                    # Also register on the connection level for the session
                    pgvector.psycopg2.register_vector(conn)
            except Exception as e:
                logger.error(f"Error initializing DB: {e}")
                conn.rollback()

    def save_prompt(self, alias, prompt_text):
        with self.get_conn() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO prompts (alias, prompt_text)
                        VALUES (%s, %s)
                        ON CONFLICT (alias) DO UPDATE SET
                            prompt_text = EXCLUDED.prompt_text;
                    """, (alias, prompt_text))
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"Error saving prompt: {e}")
                conn.rollback()
                return False

    def get_prompts(self):
        with self.get_conn() as conn:
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("SELECT * FROM prompts ORDER BY created_at DESC")
                    return cur.fetchall()
            except Exception as e:
                logger.error(f"Error getting prompts: {e}")
                return []

    def delete_prompt(self, alias):
        with self.get_conn() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM prompts WHERE alias = %s", (alias,))
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"Error deleting prompt: {e}")
                conn.rollback()
                return False

    def upsert_document(self, doc_id, category, level, meta, content, embedding=None, title=None):
        with self.get_conn() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO documents (id, title, category, level, metadata, content, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            title = EXCLUDED.title,
                            category = EXCLUDED.category,
                            level = EXCLUDED.level,
                            metadata = EXCLUDED.metadata,
                            content = EXCLUDED.content,
                            embedding = COALESCE(EXCLUDED.embedding, documents.embedding);
                    """, (doc_id, title, category, level, Json(meta), content, embedding))
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"Error upserting document: {e}")
                conn.rollback()
                return False

    def link_documents(self, source_id, summary_id):
        with self.get_conn() as conn:
            try:
                with conn.cursor() as cur:
                    # Add summary_id to source's summary_uuids
                    cur.execute("""
                        UPDATE documents 
                        SET summary_uuids = (
                            SELECT jsonb_agg(DISTINCT value)
                            FROM (
                                SELECT jsonb_array_elements(COALESCE(summary_uuids, '[]'::jsonb)) AS value 
                                FROM documents WHERE id = %s
                                UNION ALL
                                SELECT jsonb_build_array(%s::text)->0
                            ) s
                        )
                        WHERE id = %s;
                    """, (source_id, str(summary_id), source_id))
                    
                    # Add source_id to summary's source_uuids
                    cur.execute("""
                        UPDATE documents 
                        SET source_uuids = (
                            SELECT jsonb_agg(DISTINCT value)
                            FROM (
                                SELECT jsonb_array_elements(COALESCE(source_uuids, '[]'::jsonb)) AS value 
                                FROM documents WHERE id = %s
                                UNION ALL
                                SELECT jsonb_build_array(%s::text)->0
                            ) s
                        )
                        WHERE id = %s;
                    """, (str(summary_id), source_id, str(summary_id)))
                    
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"Error linking documents: {e}")
                conn.rollback()
                return False

    def remove_summary_link(self, source_id, summary_id):
        with self.get_conn() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE documents
                        SET summary_uuids = (
                            SELECT COALESCE(jsonb_agg(value), '[]'::jsonb)
                            FROM jsonb_array_elements(summary_uuids) AS value
                            WHERE value #>> '{}' != %s
                        )
                        WHERE id = %s;
                    """, (str(summary_id), source_id))
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"Error removing summary link: {e}")
                conn.rollback()
                return False

    def clear_summary_links(self, source_id):
        with self.get_conn() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("UPDATE documents SET summary_uuids = '[]'::jsonb WHERE id = %s", (source_id,))
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"Error clearing summary links: {e}")
                conn.rollback()
                return False

    def add_summary_link(self, parent_id, summary_id):
        return self.link_documents(parent_id, summary_id)

    def get_impact_analysis(self, doc_id):
        """Recursively finds all downstream documents that would be affected by deleting doc_id."""
        impact_list = []
        queue = [str(doc_id)]
        visited = set()

        with self.get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                while queue:
                    current_id = queue.pop(0)
                    if current_id in visited:
                        continue
                    visited.add(current_id)
                    
                    if current_id != str(doc_id): # Don't add the root doc itself to impact list (optional, but cleaner)
                         # We'll re-fetch title/level for UI display
                         cur.execute("SELECT id, title, level, category FROM documents WHERE id = %s", (current_id,))
                         res = cur.fetchone()
                         if res:
                             impact_list.append(res)

                    # Find children (documents where this doc is listed in source_uuids OR this doc lists them in summary_uuids)
                    # We primarily follow summary_uuids as that's the L0->L1->L2 direction.
                    cur.execute("SELECT summary_uuids FROM documents WHERE id = %s", (current_id,))
                    row = cur.fetchone()
                    if row and row.get('summary_uuids'):
                        for child_id in row['summary_uuids']:
                            if str(child_id) not in visited:
                                queue.append(str(child_id))
        
        return impact_list

    def delete_document(self, doc_id):
        """Recursively deletes a document and all its downstream summaries."""
        # 1. Get all descendants
        impacts = self.get_impact_analysis(doc_id)
        all_ids_to_delete = [str(doc_id)] + [str(i['id']) for i in impacts]
        
        with self.get_conn() as conn:
            try:
                with conn.cursor() as cur:
                    for target_id in all_ids_to_delete:
                        # Cascade delete task first
                        cur.execute("DELETE FROM processing_tasks WHERE doc_id = %s", (target_id,))
                        cur.execute("DELETE FROM documents WHERE id = %s", (target_id,))
                        # Also clean up references in other docs (e.g. if an L1 is deleted, remove it from L0's summary_uuids)
                        # but since we are deleting the whole chain, checking upstream links is redundant for the chain itself.
                        # However, for safety/cleanliness, we might want to ensure upstream links are clean?
                        # Actually, if we delete L0, L1 is deleted. 
                        # If we delete L1, we should remove L1 from L0.
                        
                    # Clean up upstream references for the ROOT document only (doc_id)
                    # If we delete L1 (root of this op), we must remove it from its L0 parent.
                    # This is tricky because we need to know who the parent was.
                    # But remove_summary_link requires knowing the parent ID.
                    # Simpler: After deleting, any `summary_uuids` pointing to these IDs will just point to non-existent docs.
                    # We can leave them as "broken links" or try to clean them.
                    # Given the current scope, broken links inside `summary_uuids` are benign but messy.
                    # Let's try to clean up the parent of the *root* doc being deleted.
                    
                    # (Quick fetch parent before delete? - Already too late in this block if we just delete? No, we haven't committed yet)
                    # Let's keep it simple: Just recursive delete for now. The standard update later will clean up if we edit the parent.
                    
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"Error recursively deleting document {doc_id}: {e}")
                conn.rollback()
                return False

    def get_document(self, doc_id):
        with self.get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM documents WHERE id = %s", (doc_id,))
                return cur.fetchone()

    def search_documents(self, query_text=None, category=None, level=None, doc_id=None, metadata_filters=None):
        with self.get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                sql = "SELECT * FROM documents WHERE 1=1"
                params = []
                
                if doc_id:
                    sql += " AND id = %s"
                    params.append(doc_id)
                if category:
                    sql += " AND category = %s"
                    params.append(category)
                if level:
                    sql += " AND level = %s"
                    params.append(level)
                if query_text:
                    sql += " AND content ILIKE %s"
                    params.append(f"%{query_text}%")
                if metadata_filters:
                    for k, v in metadata_filters.items():
                        sql += " AND metadata->>%s = %s"
                        params.extend([k, str(v)])
                
                sql += " ORDER BY created_at DESC"
                cur.execute(sql, params)
                return cur.fetchall()

    def vector_search(self, embedding, limit=5, category=None, level=None):
        with self.get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                sql = "SELECT *, 1 - (embedding <=> %s) AS cosine_similarity FROM documents"
                params = [embedding]
                
                where_clauses = []
                if category:
                    where_clauses.append("category = %s")
                    params.append(category)
                if level:
                    where_clauses.append("level = %s")
                    params.append(level)
                
                if where_clauses:
                    sql += " WHERE " + " AND ".join(where_clauses)
                
                sql += " ORDER BY embedding <=> %s LIMIT %s"
                params.extend([embedding, limit])
                
                cur.execute(sql, params)
                return cur.fetchall()

    def enqueue_task(self, doc_id, config=None):
        with self.get_conn() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO processing_tasks (doc_id, status, config)
                        VALUES (%s, 'created', %s)
                        ON CONFLICT (doc_id) DO UPDATE SET
                            status = 'created',
                            config = EXCLUDED.config,
                            updated_at = CURRENT_TIMESTAMP;
                    """, (doc_id, Json(config or {})))
                conn.commit()
                # Trigger worker check/start
                ensure_worker_running()
                return True
            except Exception as e:
                logger.error(f"Error enqueueing task: {e}")
                conn.rollback()
                return False

    def update_task(self, doc_id, status=None, results=None, config=None, results_l=None, results_r=None):
        sql = "UPDATE processing_tasks SET updated_at = CURRENT_TIMESTAMP"
        params = []
        
        if status:
            sql += ", status = %s"
            params.append(status)
        if results:
            sql += ", results = %s"
            params.append(Json(results))
        if config:
            sql += ", config = %s"
            params.append(Json(config))
        if results_l:
            sql += ", results_model_l = %s"
            params.append(Json(results_l))
        if results_r:
            sql += ", results_model_r = %s"
            params.append(Json(results_r))
            
        sql += " WHERE doc_id = %s"
        params.append(str(doc_id))
        
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(params))
            conn.commit()
    def get_tasks_by_status(self, status):
        with self.get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM processing_tasks WHERE status = %s ORDER BY created_at ASC", (status,))
                return cur.fetchall()

    def get_task(self, doc_id):
        with self.get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM processing_tasks WHERE doc_id = %s", (doc_id,))
                return cur.fetchone()

    def get_all_tasks(self):
        with self.get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM processing_tasks")
                return {str(t['doc_id']): t for t in cur.fetchall()}

    def get_documents_by_ids(self, doc_ids):
        if not doc_ids:
            return {}
        with self.get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM documents WHERE id IN %s", (tuple(doc_ids),))
                return {str(d['id']): d for d in cur.fetchall()}

    def delete_task(self, doc_id):
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM processing_tasks WHERE doc_id = %s", (doc_id,))
                conn.commit()

    def get_categories(self):
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                # Use RealDictCursor to fetch results as dictionaries, then extract 'name'
                cur.execute("SELECT name FROM categories ORDER BY name ASC")
                return [r[0] for r in cur.fetchall()] # Access by index for non-RealDictCursor

    def add_category(self, name):
        with self.get_conn() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("INSERT INTO categories (name) VALUES (%s) ON CONFLICT DO NOTHING", (name,))
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"Error adding category: {e}")
                conn.rollback()
                return False

    def migrate_embedding_schema(self, new_dim):
        """
        Alters the embedding column to match the new dimension of the selected model.
        
        CRITICAL DATABASE OPERATION:
        1. This runs `ALTER TABLE ... TYPE vector(new_dim)`.
        2. If the dimensions differ (e.g., changing from 384 to 768), Postgres may 
           invalidate or cast existing data.
        3. In the context of "Re-indexing", invalidating old data is acceptable 
           because we immediately overwrite it with new embeddings in the next step.
           
        Args:
            new_dim (int): The dimension size of the new embedding model.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        with self.get_conn() as conn:
            try:
                with conn.cursor() as cur:
                    # Using string interpolation for DDL statement (cannot use parameters for ALTER TABLE)
                    # This is safe because new_dim is derived from the model instance, not user input.
                    cur.execute(f"ALTER TABLE documents ALTER COLUMN embedding TYPE vector({new_dim});")
                conn.commit()
                return True
            except Exception as e:
                logger.error(f"Error migrating schema_embedding: {e}")
                conn.rollback()
                return False

    def reindex_all_documents(self, embedder, progress_callback=None):
        """
        Re-calculates embeddings for ALL documents using the provided embedder.
        
        Process:
        1. Dimension Check: Gets the dimension from the new model.
        2. Schema Migration: Alters the DB column to match this dimension.
        3. Fetch Docs: Loads all documents (id, content).
        4. Re-Embed: Generates new vectors for each document.
        5. Update DB: Saves the new vectors back to the 'documents' table.
        
        Args:
            embedder (SentenceTransformer): The loaded embedding model instance.
            progress_callback (function, optional): Callback(current, total) for UI updates.
            
        Returns:
            tuple: (bool success, str message)
        """
        
        # 1. Get new dimension
        try:
            # sentence-transformers model.get_sentence_embedding_dimension()
            new_dim = embedder.get_sentence_embedding_dimension()
        except:
            # Fallback for some models/mocks
            new_dim = 384
            
        logger.info(f"Starting Re-indexing. New Dimension: {new_dim}")
        
        # 2. Migrate Schema
        if not self.migrate_embedding_schema(new_dim):
            return False, "Schema migration failed."
            
        # 3. Fetch all documents
        docs = []
        with self.get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, content FROM documents WHERE content IS NOT NULL")
                docs = cur.fetchall()
        
        total = len(docs)
        logger.info(f"Found {total} documents to re-index.")
        
        if progress_callback:
            progress_callback(0, total)
            
        success_count = 0
        
        # 4. Process (Batching could be optimized for huge datasets)
        with self.get_conn() as conn:
            with conn.cursor() as cur:
                for i, doc in enumerate(docs):
                    try:
                        embedding = embedder.encode(doc['content']).tolist()
                        cur.execute("UPDATE documents SET embedding = %s WHERE id = %s", (embedding, doc['id']))
                        success_count += 1
                    except Exception as e:
                        logger.error(f"Failed to re-embed doc {doc['id']}: {e}")
                    
                    if progress_callback and i % 5 == 0:
                        progress_callback(i + 1, total)
            conn.commit()
            
        return True, f"Successfully re-indexed {success_count}/{total} documents."
