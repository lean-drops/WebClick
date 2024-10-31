import os
import shutil
import logging

from config import CACHE_DIR, OUTPUT_MAPPING_PATH, MAPPING_CACHE_DIR

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,  # Ändere zu logging.DEBUG für detailliertere Ausgaben
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

# Pfade für die zu löschenden Elemente
output_mapping_path = OUTPUT_MAPPING_PATH

mapping_cache_dir = MAPPING_CACHE_DIR
def delete_cache_content():
    # Löschen der Datei output_mapping.json
    if os.path.exists(output_mapping_path):
        try:
            os.remove(output_mapping_path)
            logger.info(f"Datei erfolgreich gelöscht: {output_mapping_path}")
        except Exception as e:
            logger.error(f"Fehler beim Löschen der Datei {output_mapping_path}: {e}")
    else:
        logger.info(f"Datei existiert nicht: {output_mapping_path}")

    # Löschen des Ordners mapping_cache
    if os.path.exists(mapping_cache_dir):
        try:
            shutil.rmtree(mapping_cache_dir)
            logger.info(f"Ordner erfolgreich gelöscht: {mapping_cache_dir}")
        except Exception as e:
            logger.error(f"Fehler beim Löschen des Ordners {mapping_cache_dir}: {e}")
    else:
        logger.info(f"Ordner existiert nicht: {mapping_cache_dir}")


if __name__ == "__main__":
    delete_cache_content()
