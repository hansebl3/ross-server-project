import time
import json
import logging
from db_manager import DBManager
from llm_client import LLMClient, RetryableLLMError

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("worker.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Worker")

class BackgroundWorker:
    def __init__(self):
        self.db = DBManager()
        self.llm = LLMClient()
        logger.info("Worker Initialized")
        self._recover_stuck_tasks()

    def _recover_stuck_tasks(self):
        """Reset any tasks stuck in processing state back to queued on startup."""
        # Recover L processing
        stuck_l = self.db.get_tasks_by_status('processing_l')
        for task in stuck_l:
            logger.warning(f"Recovering stuck task {task['doc_id']} from processing_l to queued")
            self.db.update_task(task['doc_id'], status='queued')
            
        # Recover R processing
        stuck_r = self.db.get_tasks_by_status('processing_r')
        for task in stuck_r:
            logger.warning(f"Recovering stuck task {task['doc_id']} from processing_r to queued_r")
            self.db.update_task(task['doc_id'], status='queued_r')

        # Backward compatibility for old 'processing' status
        old_processing = self.db.get_tasks_by_status('processing')
        for task in old_processing:
             # Assume if results_l exists, it was doing R. Else it was doing L.
             if task.get('results_model_l'):
                 self.db.update_task(task['doc_id'], status='queued_r')
             else:
                 self.db.update_task(task['doc_id'], status='queued')
                 
        logger.info("Task recovery complete.")

    def run(self):
        logger.info("Worker Interrupted. Starting loop...")
        while True:
            try:
                # --- STAGE 1: LEFT MODEL (Queue 1) ---
                tasks_q1 = self.db.get_tasks_by_status('queued')
                
                if tasks_q1:
                    logger.info(f"Found {len(tasks_q1)} tasks in Queue 1 (Left). Processing...")
                    for task in tasks_q1:
                        doc_id = task['doc_id']
                        try:
                            config = task['config']
                            doc = self.db.get_document(doc_id)
                            if not doc: 
                                logger.error(f"Doc {doc_id} not found. Skipping.")
                                continue

                            # 1. Update Status -> processing_l
                            self.db.update_task(doc_id, status='processing_l')
                            logger.info(f"[Queue 1] Processing {doc_id} with {config['model_l']}")
                            
                            # 2. Run LLM
                            meta_l = self.llm.extract_metadata(doc['content'], config['model_l'], config['prompt_meta'])
                            sum_l = self.llm.generate_content(doc['content'], config['model_l'], config['prompt_summary'])
                            
                            res_l = {"metadata": meta_l, "summary": sum_l}
                            
                            # 3. Update Results & Move to Queue 2 (queued_r)
                            self.db.update_task(doc_id, status='queued_r', results_l=res_l)
                            logger.info(f"[Queue 1] Task {doc_id} complete. Moved to Queue 2.")

                        except RetryableLLMError as re:
                            logger.warning(f"LLM Busy/Timeout during task {doc_id} (L): {re}. Skipping for now...")
                            # Revert to queued so it can be picked up again
                            self.db.update_task(doc_id, status='queued')
                        except Exception as e:
                            logger.error(f"Error processing task {doc_id} (L): {e}")
                            # Keep in processing_l or move to error state? 
                            # For simplicity, revert to queued to retry or manual fix
                            self.db.update_task(doc_id, status='queued')

                # --- STAGE 2: RIGHT MODEL (Queue 2) ---
                tasks_q2 = self.db.get_tasks_by_status('queued_r')
                
                if tasks_q2:
                    logger.info(f"Found {len(tasks_q2)} tasks in Queue 2 (Right). Processing...")
                    for task in tasks_q2:
                        doc_id = task['doc_id']
                        try:
                            config = task['config']
                            doc = self.db.get_document(doc_id)
                            if not doc: continue

                            model_r = config.get('model_r')
                            if not model_r: 
                                # No R model configured? Mark done.
                                self.db.update_task(doc_id, status='done')
                                continue

                            # 1. Update Status -> processing_r
                            self.db.update_task(doc_id, status='processing_r')
                            logger.info(f"[Queue 2] Processing {doc_id} with {model_r}")
                            
                            # 2. Run LLM
                            meta_r = self.llm.extract_metadata(doc['content'], model_r, config['prompt_meta'])
                            sum_r = self.llm.generate_content(doc['content'], model_r, config['prompt_summary'])
                            
                            res_r = {"metadata": meta_r, "summary": sum_r}
                            
                            # 3. Update Results & Mark Done
                            self.db.update_task(doc_id, status='done', results_r=res_r)
                            logger.info(f"[Queue 2] Task {doc_id} FULLY DONE.")

                        except RetryableLLMError as re:
                            logger.warning(f"LLM Busy/Timeout during task {doc_id} (R): {re}. Skipping for now...")
                            self.db.update_task(doc_id, status='queued_r')
                        except Exception as e:
                            logger.error(f"Error processing task {doc_id} (R): {e}")
                            self.db.update_task(doc_id, status='queued_r')

                
                if not tasks_q1 and not tasks_q2:
                    time.sleep(2)
                
            except Exception as main_e:
                logger.error(f"Worker Loop Error: {main_e}")
                time.sleep(5)

if __name__ == "__main__":
    worker = BackgroundWorker()
    worker.run()
