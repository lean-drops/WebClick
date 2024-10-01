import os
import shutil
import logging

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,  # Ändere zu logging.DEBUG für detailliertere Ausgaben
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

# Pfad zum Cache-Verzeichnis
CACHE_DIR = "../static/cache"

def delete_cache(cache_dir):
    if os.path.exists(cache_dir):
        try:
            # Rekursiv den gesamten Cache-Ordner löschen
            shutil.rmtree(cache_dir)
            logger.info(f"Cache erfolgreich gelöscht: {cache_dir}")
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Caches: {e}")
    else:
        logger.info(f"Cache-Verzeichnis existiert nicht: {cache_dir}")

if __name__ == "__main__":
    delete_cache(CACHE_DIR)
