import os
import zipfile
import logging
from urllib.parse import urlparse
import re

# Logger konfigurieren
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levellevel)s - %(message)s')
logger = logging.getLogger(__name__)


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
