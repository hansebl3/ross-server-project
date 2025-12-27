
import sys
import os
import time

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from db_manager import DBManager
from utils.worker_manager import is_worker_running

def test_auto_start():
    print("Checking initial worker state...")
    if is_worker_running():
        print("Worker is running. Killing it for test...")
        os.system("pkill -f worker.py")
        time.sleep(2)
        if is_worker_running():
            print("Failed to kill worker. Test aborted.")
            return
        print("Worker killed.")
    else:
        print("Worker is not running.")

    print("Enqueueing dummy task...")
    db = DBManager()
    # Create a dummy task ID
    import uuid
    dummy_id = str(uuid.uuid4())
    
    # This should trigger ensure_worker_running
    db.enqueue_task(dummy_id, {"test": "true"})
    
    print("Task enqueued. Waiting for worker to start...")
    # Wait up to 5 seconds
    for _ in range(10):
        if is_worker_running():
            print("SUCCESS: Worker started automatically!")
            # Clean up dummy task
            db.delete_task(dummy_id)
            return
        time.sleep(0.5)
        
    print("FAILURE: Worker did not start within 5 seconds.")
    # Clean up
    db.delete_task(dummy_id)

if __name__ == "__main__":
    test_auto_start()
