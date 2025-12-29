import sys
import time
import os
import logging
from datetime import datetime as dt
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer
from dotenv import load_dotenv

from threading import Timer, Thread
import queue
import json
import globals

task_queue = queue.Queue()

def worker():
    """Background worker to process build tasks."""
    while True:
        try:
            func, args, kwargs = task_queue.get()
            func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Worker task failed: {e}")
        finally:
            task_queue.task_done()

from database import Database
from utils import generate_uuid_v7, calculate_file_hash, parse_frontmatter
from l1_builder import L1Builder
from l2_builder import L2Builder

# Shared cache logic moved to globals.py
from jobs import run_daily_job

# Environment loading
root_env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
local_env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(root_env_path)
load_dotenv(local_env_path)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FSWatcher")

class DocEventHandler(FileSystemEventHandler):
    """Handles L0 (Source) document changes."""
    def __init__(self, db: Database, l1_builder: L1Builder, root_dir: str):
        self.db = db
        self.l1_builder = l1_builder
        self.root_dir = root_dir
        self._pending_tasks = {} # path -> timer

    def _get_relative_path(self, abs_path: str) -> str:
        return os.path.relpath(abs_path, os.path.dirname(self.root_dir))

    def _process_file(self, file_path: str):
        # Clean up timer
        if file_path in self._pending_tasks:
            del self._pending_tasks[file_path]

        if any(part.startswith('.') for part in file_path.split(os.sep)): return
        basename = os.path.basename(file_path)
        if not basename.endswith('.md') or basename.lower() == 'readme.md': return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            metadata, body = parse_frontmatter(content)
            # Handle both 'draft: true' and 'draft: "true"'
            is_draft = metadata.get('draft')
            if isinstance(is_draft, str): is_draft = is_draft.lower() == 'true'
            
            if metadata.get('status') == 'draft' or is_draft:
                logger.info(f"Skipping Draft: {file_path}")
                return

            rel_path = self._get_relative_path(file_path)
            
            # Use hash check to avoid redundant builds if only metadata changed but not content
            file_hash = calculate_file_hash(content, rel_path)
            existing_doc = self.db.get_document_by_path(rel_path)
            if existing_doc and existing_doc['content_hash'] == file_hash:
                # Still check if we need to build L1 (e.g. if it was deleted)
                cur = self.db.get_connection().cursor()
                cur.execute("SELECT COUNT(*) FROM l1_versions WHERE source_uuid = %s AND status = 'ACTIVE'", (existing_doc['uuid'],))
                if cur.fetchone()[0] > 0:
                    logger.info(f"Skipping redundant build for {rel_path} (No content change)")
                    return

            # 1. Resolve UUID - Fixed: compare as strings
            file_uuid = metadata.get('uuid')
            if file_uuid:
                if existing_doc and str(existing_doc['uuid']) != str(file_uuid):
                    logger.warning(f"UUID mismatch for {rel_path}. File has {file_uuid}, DB has {existing_doc['uuid']}. Re-syncing...")
                    self.db.delete_document(existing_doc['uuid'])
                uuid = file_uuid
            else:
                uuid = str(existing_doc['uuid']) if existing_doc else generate_uuid_v7()
            
            category = "General"
            parts = rel_path.split(os.sep)
            for i, part in enumerate(parts):
                if part.endswith('_Sources') and len(parts) > i + 1:
                    category = parts[i+1]
                    break

            self.db.upsert_document(uuid, rel_path, content, file_hash, category)
            logger.info(f"Queued L1 Build for {uuid}...")
            task_queue.put((self.l1_builder.build_l1, (uuid,), {}))
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")

    def on_created(self, event: FileSystemEvent):
        # on_modified will handle this after debouncing
        if not event.is_directory: self.on_modified(event)
    def on_modified(self, event: FileSystemEvent):
        if event.is_directory: return
        file_path = event.src_path
        
        # Debouncing: wait 2 seconds for stability
        if file_path in self._pending_tasks:
            self._pending_tasks[file_path].cancel()
        
        t = Timer(2.0, self._process_file, [file_path])
        self._pending_tasks[file_path] = t
        t.start()

class ReviewEventHandler(FileSystemEventHandler):
    """Handles review file (.review.md) changes."""
    def __init__(self, db: Database, l1_builder: L1Builder, l2_builder: L2Builder):
        self.db = db
        self.l1_builder = l1_builder
        self.l2_builder = l2_builder

    def _process_review(self, file_path: str):
        if not file_path.endswith('.review.md'): return
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Skip system-generated template writes
            file_hash = calculate_file_hash(content, file_path)
            if globals.is_system_write(file_path, file_hash):
                return
                
            metadata, notes = parse_frontmatter(content)
            review_id = metadata.get('review_id')
            if not review_id: return

            rating = metadata.get('rating', 'PENDING')
            if isinstance(rating, str): rating = rating.strip().upper()
            
            decision = metadata.get('decision', 'PENDING')
            if isinstance(decision, str): decision = decision.strip().upper()

            issues = metadata.get('issues', [])
            
            if l1_id := metadata.get('l1_id'):
                logger.info(f"Syncing L1 Review {review_id}")
                self.db.upsert_l1_review(review_id, l1_id, rating, decision, issues, notes)
                
                if decision == "REBUILD":
                    source_uuid = self.db.get_source_uuid_by_l1(l1_id)
                    if source_uuid:
                        logger.info(f"Decision 'REBUILD' detected for L1. Queuing rebuild for Doc {source_uuid} with notes...")
                        task_queue.put((self.l1_builder.build_l1, (source_uuid,), {'review_notes': notes}))
                    else:
                        logger.warning(f"Could not find source_uuid for L1 {l1_id}. Rebuild failed.")
                elif decision == "DISCARD":
                    logger.info(f"Decision 'DISCARD' detected for Review {review_id}. Deleting record...")
                    self.db.delete_review(review_id)

            elif l2_id := metadata.get('l2_id'):
                logger.info(f"Syncing L2 Review {review_id}")
                self.db.upsert_l2_review(review_id, l2_id, rating, decision, issues, notes)
                
        except Exception as e:
            logger.error(f"Error processing review {file_path}: {e}")

    def on_created(self, event: FileSystemEvent):
        if not event.is_directory: self._process_review(event.src_path)
    def on_modified(self, event: FileSystemEvent):
        if not event.is_directory: self._process_review(event.src_path)

class ShadowSyncEventHandler(FileSystemEventHandler):
    """Handles manual edits to [L1]/[L2] shadow files and syncs back to DB."""
    def __init__(self, db: Database, l1_builder: L1Builder):
        self.db = db
        self.l1_builder = l1_builder
        self._last_processed = {} # path -> hash
        self._pending_tasks = {} # path -> timer

    def _process_shadow(self, file_path: str):
        if file_path in self._pending_tasks:
            del self._pending_tasks[file_path]

        fname = os.path.basename(file_path)
        if not (fname.startswith('[L1]') and fname.endswith('.md')): return
        if '.review.md' in file_path: return # Skip reviews
            
        try:
            if not os.path.exists(file_path): return
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            file_hash = calculate_file_hash(content, file_path)
            # Check shared system write cache
            if globals.is_system_write(file_path, file_hash):
                logger.info(f"Ignoring system write for {fname}")
                return
                
            if self._last_processed.get(file_path) == file_hash:
                return # Avoid cycle
            
            metadata, body = parse_frontmatter(content)
            l1_id = metadata.get('l1_uuid') or metadata.get('l1_id')
            if not l1_id: return
            
            logger.info(f"Manual edit detected for {fname}. Syncing to DB...")
            
            # Re-embed corrected text
            embedding = self.l1_builder.get_embedding(body)
            if embedding:
                self.db.update_l1_content_and_embedding(l1_id, body, embedding)
                logger.info(f"Shadow Sync project: {fname} (ID: {l1_id}) updated.")
                self._last_processed[file_path] = file_hash
            
        except Exception as e:
            logger.error(f"Error syncing shadow file {file_path}: {e}")

    def on_modified(self, event: FileSystemEvent):
        if event.is_directory: return
        file_path = event.src_path
        
        # Debouncing: wait 1 second for stability (AI writes need a moment to be logged in globals)
        if file_path in self._pending_tasks:
            self._pending_tasks[file_path].cancel()
        
        t = Timer(1.0, self._process_shadow, [file_path])
        self._pending_tasks[file_path] = t
        t.start()

if __name__ == "__main__":
    db = Database()
    db.init_db()

    WATCH_DIR_SOURCES = os.getenv("WATCH_DIR_SOURCES", "../01_Sources")
    WATCH_DIR_SHADOW = os.getenv("WATCH_DIR_SHADOW", "../99_Shadow_Library")
    CONFIG_DIR = os.getenv("CONFIG_DIR", "../90_Configuration")

    abs_sources_dir = os.path.abspath(WATCH_DIR_SOURCES)
    abs_shadow_dir = os.path.abspath(WATCH_DIR_SHADOW)
    abs_config_dir = os.path.abspath(CONFIG_DIR)

    l1_builder = L1Builder(db, abs_config_dir, abs_shadow_dir)
    l2_builder = L2Builder(db, abs_shadow_dir)

    source_observer = Observer()
    source_observer.schedule(DocEventHandler(db, l1_builder, abs_sources_dir), abs_sources_dir, recursive=True)
    
    review_observer = Observer()
    review_observer.schedule(ReviewEventHandler(db, l1_builder, l2_builder), abs_shadow_dir, recursive=True)
    
    shadow_observer = Observer()
    shadow_observer.schedule(ShadowSyncEventHandler(db, l1_builder), abs_shadow_dir, recursive=True)
    
    logger.info("FSWatcher started.")
    
    # Start worker thread
    worker_thread = Thread(target=worker, daemon=True)
    worker_thread.start()
    
    source_observer.start()
    review_observer.start()
    shadow_observer.start()
    
    last_run_date = None
    try:
        while True:
            now = dt.now()
            if now.hour == 1 and now.minute == 0 and last_run_date != now.date():
                run_daily_job(db, l2_builder)
                last_run_date = now.date()
            time.sleep(10)
    except KeyboardInterrupt:
        source_observer.stop()
        review_observer.stop()
    source_observer.join()
    review_observer.join()
