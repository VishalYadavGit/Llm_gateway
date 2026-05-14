import logging
import sys

# Configure logging for the worker process
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

print("[WORKER_INIT] Dramatiq worker starting...")
print(f"[WORKER_INIT] Python version: {sys.version}")

import workers.tasks  # noqa: F401

print("[WORKER_INIT] Tasks module loaded. Worker ready to process tasks.")
