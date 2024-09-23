import os
import logging
import re
from urllib.parse import urlparse

# Logger konfigurieren
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def shorten_url(url):
    """
    Kürzt die URL, um einen ordnerfreundlichen Namen zu erstellen.

    Args:
        url (str): Die zu kürzende URL.

    Returns:
        str: Eine gekürzte Version der URL.
    """
    parsed_url = urlparse(url)
    short_name = re.sub(r'\W+', '', parsed_url.netloc)
    logger.debug(f"Shortened URL: {url} to {short_name}")
    return short_name


import os

def create_directory(path):
    """
    Erstellt ein Verzeichnis, falls es nicht existiert.

    Args:
        path (str): Der Pfad des zu erstellenden Verzeichnisses.

    Returns:
        str: Der Pfad zum erstellten Verzeichnis.
    """
    if not os.path.exists(path):
        os.makedirs(path)
        logger.info(f"Directory created at {path}")
    else:
        logger.debug(f"Directory already exists at {path}")

    return path