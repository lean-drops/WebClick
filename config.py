# config.py

import os
import logging

# Base directory (the directory where config.py is located)
BASE_DIR = "/Users/python/Satelite 1 Python Projekte/Archiv/WebClick"
print(BASE_DIR)
# App directory
APP_DIR = os.path.join(BASE_DIR, 'app')
print(APP_DIR)
# Static directory inside app
STATIC_DIR = os.path.join(APP_DIR, 'static')
print(STATIC_DIR)
# Cache directories
CACHE_DIR = os.path.join(STATIC_DIR, 'cache')
MAPPING_DIR = os.path.join(CACHE_DIR, 'mapping_cache')
print(CACHE_DIR)
print(MAPPING_DIR)
# JSON files directory
JSON_DIR = os.path.join(STATIC_DIR, 'json')
print(JSON_DIR)
# Ensure the cache directories exist
os.makedirs(MAPPING_DIR, exist_ok=True)

# Thread pool settings
MAX_WORKERS = 4

# Taboo terms JSON file path
TABOO_JSON_PATH = os.path.join(JSON_DIR, 'taboo.json')

# Logging configuration
# Configure Logging
def setup_logging():
    logger = logging.getLogger("WebClickScraper")
    logger.setLevel(logging.DEBUG)  # Set to DEBUG for detailed logs

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )

    # Stream handler (console)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)  # Set to INFO to reduce console verbosity
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File handler
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    fh = logging.FileHandler(os.path.join(log_dir, "scraper.log"))
    fh.setLevel(logging.DEBUG)  # File logs will capture all details
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # Prevent log messages from being propagated to the root logger
    logger.propagate = False

    return logger

logger = setup_logging()
