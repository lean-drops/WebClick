import os
import zipfile
import logging
from urllib.parse import urlparse
import re

# Logger konfigurieren
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levellevel)s - %(message)s')
logger = logging.getLogger(__name__)


def shorten_url(url):
    """
    Shorten the URL to create a folder-friendly name.

    Args:
        url (str): The URL to shorten.

    Returns:
        str: A shortened version of the URL.
    """
    parsed_url = urlparse(url)
    short_name = re.sub(r'\W+', '', parsed_url.netloc)
    logger.debug(f"Shortened URL: {url} to {short_name}")
    return short_name


def create_zip_file(source_folder, output_file):
    """
    Create a zip file from the contents of a folder.

    Args:
        source_folder (str): The folder containing the files to be zipped.
        output_file (str): The path to save the output zip file.

    Returns:
        None
    """
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_folder):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, start=source_folder)
                zipf.write(file_path, arcname)
    logger.info(f"Created zip file at {output_file}")
