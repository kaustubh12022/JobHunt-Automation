import queue
from loguru import logger
import sys

# Fix Windows console encoding for CP1252 to prevent crash on unicode arrows and currency symbols
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Queue to stream logs to Flask frontend
log_queue = queue.Queue()

class QueueSink:
    def write(self, message):
        log_queue.put(message.strip())

class SafeConsoleSink:
    """Console sink with robust CP1252/Unicode fallback for Windows shells."""
    def __init__(self, stream=sys.stdout):
        self.stream = stream

    def write(self, message):
        try:
            self.stream.write(message)
            self.stream.flush()
        except UnicodeEncodeError:
            # Replace common problematic unicode characters with safe ascii replacements
            safe = message.replace('\u2192', '->').replace('\u20b9', 'Rs. ')
            encoding = getattr(self.stream, 'encoding', None) or 'utf-8'
            sanitized = safe.encode(encoding, errors='replace').decode(encoding, errors='replace')
            self.stream.write(sanitized)
            self.stream.flush()

# Remove default
logger.remove()

# Add console logging with safe unicode handling
logger.add(SafeConsoleSink(sys.stdout), format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}")

# Add queue logging for dashboard
logger.add(QueueSink(), format="{time:HH:mm:ss} [{level}] {message}")

