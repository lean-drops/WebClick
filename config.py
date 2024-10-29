# config.py
import os
from pathlib import Path
import logging
from dotenv import load_dotenv

# Lade die .env Datei
load_dotenv()

# Basisverzeichnis des Projekts
BASE_DIR = Path(os.getenv('BASE_DIR', '.')).resolve()

# App-Verzeichnis
APP_DIR = BASE_DIR / os.getenv('APP_DIR', 'app')

# Static-Verzeichnis innerhalb der App
STATIC_DIR = APP_DIR / os.getenv('STATIC_DIR', 'static')

# Weitere Verzeichnisse innerhalb Static
CSS_DIR = STATIC_DIR / os.getenv('CSS_DIR', 'css')
IMG_DIR = STATIC_DIR / os.getenv('IMG_DIR', 'img')
JS_DIR = STATIC_DIR / os.getenv('JS_DIR', 'js')
JSON_DIR = STATIC_DIR / os.getenv('JSON_DIR', 'json')
TEMPLATES_DIR = APP_DIR / os.getenv('TEMPLATES_DIR', 'templates')
UTILS_DIR = APP_DIR / os.getenv('UTILS_DIR', 'utils')

# Cache-Verzeichnisse
CACHE_DIR = STATIC_DIR / os.getenv('CACHE_DIR', 'cache')
MAPPING_CACHE_DIR = CACHE_DIR / os.getenv('MAPPING_CACHE_DIR', 'mapping_cache')
# config.py (Add the following lines)

# File path for the mapping cache

# Logs-Verzeichnis
LOGS_DIR = BASE_DIR / os.getenv('LOGS_DIR', 'logs')

# Output PDFs-Verzeichnis
OUTPUT_PDFS_DIR = BASE_DIR / os.getenv('OUTPUT_PDFS_DIR', 'output_pdfs')

# Sicherstellen, dass alle wichtigen Verzeichnisse existieren
directories = [
    MAPPING_CACHE_DIR,
    LOGS_DIR,
    OUTPUT_PDFS_DIR,
]

for directory in directories:
    directory.mkdir(parents=True, exist_ok=True)
    print(f"Stelle sicher, dass das Verzeichnis existiert: {directory}")

# Pfade zu spezifischen Dateien
OUTPUT_MAPPING_PATH = CACHE_DIR / os.getenv('OUTPUT_MAPPING_PATH', 'output_mapping.json')

TABOO_JSON_PATH = JSON_DIR / os.getenv('TABOO_JSON_FILE', 'taboo.json')
COOKIES_SELECTOR_JSON_PATH = JSON_DIR / os.getenv('COOKIES_SELECTOR_JSON_FILE', 'cookies_selector.json')
EXCLUDE_SELECTORS_JSON_PATH = JSON_DIR / os.getenv('EXCLUDE_SELECTORS_JSON_FILE', 'exclude_selectors.json')
URLS_JSON_PATH = JSON_DIR / os.getenv('URLS_JSON_FILE', 'urls.json')

# Einstellungen
MAX_WORKERS = int(os.getenv('MAX_WORKERS', '4'))
LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG').upper()

# Logging-Konfiguration
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.DEBUG),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / 'app.log')
    ]
)
logger = logging.getLogger(__name__)

logger.debug("Konfiguration geladen und Logger eingerichtet.")

if __name__ == "__main__":
    print(f"BASE_DIR: {BASE_DIR}")
    print(f"APP_DIR: {APP_DIR}")
    print(f"STATIC_DIR: {STATIC_DIR}")
    print(f"CSS_DIR: {CSS_DIR}")
    print(f"IMG_DIR: {IMG_DIR}")
    print(f"JS_DIR: {JS_DIR}")
    print(f"JSON_DIR: {JSON_DIR}")
    print(f"TEMPLATES_DIR: {TEMPLATES_DIR}")
    print(f"UTILS_DIR: {UTILS_DIR}")
    print(f"CACHE_DIR: {CACHE_DIR}")
    print(f"MAPPING_CACHE_DIR: {MAPPING_CACHE_DIR}")
    print(f"OUTPUT_MAPPING_PATH: {OUTPUT_MAPPING_PATH}")

    print(f"LOGS_DIR: {LOGS_DIR}")
    print(f"OUTPUT_PDFS_DIR: {OUTPUT_PDFS_DIR}")
    print(f"TABOO_JSON_PATH: {TABOO_JSON_PATH}")
    print(f"COOKIES_SELECTOR_JSON_PATH: {COOKIES_SELECTOR_JSON_PATH}")
    print(f"EXCLUDE_SELECTORS_JSON_PATH: {EXCLUDE_SELECTORS_JSON_PATH}")
    print(f"URLS_JSON_PATH: {URLS_JSON_PATH}")
    print(f"MAX_WORKERS: {MAX_WORKERS}")
    print(f"LOG_LEVEL: {LOG_LEVEL}")
