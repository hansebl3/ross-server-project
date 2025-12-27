import subprocess
import logging
import os
import sys

logger = logging.getLogger(__name__)

def is_worker_running():
    """Check if src/worker.py is currently running using ps."""
    try:
        # Check for python process running worker.py
        # We use pgrep -f which matches against the full command line
        result = subprocess.run(['pgrep', '-f', 'worker.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Error checking worker status: {e}")
        return False

def start_worker():
    """Start the worker.py process in the background."""
    try:
        # Assuming we are running from the project root or src directory
        # We need to find the absolute path to worker.py
        
        # Get the directory of this file (src/utils)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up one level to src
        src_dir = os.path.dirname(current_dir)
        project_root = os.path.dirname(src_dir)
        
        worker_path = os.path.join(src_dir, 'worker.py')
        
        if not os.path.exists(worker_path):
            logger.error(f"Worker script not found at {worker_path}")
            return False

        # Use the same python interpreter as the current process
        python_executable = sys.executable

        logger.info(f"Starting worker: {python_executable} {worker_path}")
        
        # Start the worker detached
        # We redirect stdout/stderr to files to avoid blocking
        with open(os.path.join(src_dir, 'worker_stdout.log'), 'a') as out, \
             open(os.path.join(src_dir, 'worker.log'), 'a') as err:
            subprocess.Popen(
                [python_executable, worker_path],
                cwd=src_dir,
                stdout=out,
                stderr=err,
                start_new_session=True # Detach from parent
            )
        return True
    except Exception as e:
        logger.error(f"Failed to start worker: {e}")
        return False

def ensure_worker_running():
    """Check if worker is running, and start it if not."""
    if not is_worker_running():
        logger.warning("Worker process not found. Attempting to start...")
        if start_worker():
            logger.info("Worker process started successfully.")
        else:
            logger.error("Failed to auto-start worker process.")
    else:
        logger.debug("Worker is already running.")
