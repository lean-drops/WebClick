# config.py

import os
import logging

# Base directory (the directory where config.py is located)
BASE_DIR = "/Users/programming/PycharmProjects/Money/WebClick"
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
logging.basicConfig(
    level=logging.DEBUG,  # Change to logging.INFO in production
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
