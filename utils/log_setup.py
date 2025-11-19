from os import makedirs
from os.path import join
from datetime import datetime
import logging

def setup_logging(log_dir="log", level=logging.INFO):
    """Configure global logging for the entire application."""
    makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = join(log_dir, f"{timestamp}.log")
    root = logging.getLogger()
    root.setLevel(level)

    if root.handlers:
        return

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    file_handler = logging.FileHandler(log_filename)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)
