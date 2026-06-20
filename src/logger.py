import queue
from loguru import logger
import sys

# Queue to stream logs to Flask frontend
log_queue = queue.Queue()

class QueueSink:
    def write(self, message):
        log_queue.put(message.strip())

# Remove default
logger.remove()

# Add console logging
logger.add(sys.stdout, format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}")

# Add queue logging for dashboard
logger.add(QueueSink(), format="{time:HH:mm:ss} [{level}] {message}")
