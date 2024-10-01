import os
import logging

# Basisverzeichnis (2 Ebenen höher, um von 'app' auszugehen)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Cache-Verzeichnisse
CACHE_DIR = os.path.join(BASE_DIR, "static", "cache")
MAPPING_DIR = os.path.join(CACHE_DIR, "mapping_cache")

# Stelle sicher, dass die Cache-Verzeichnisse existieren
os.makedirs(MAPPING_DIR, exist_ok=True)

# Thread-Pool Einstellungen
MAX_WORKERS = 4

# Logging konfigurieren
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
