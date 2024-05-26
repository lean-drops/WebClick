import re
import unicodedata
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

def sanitize_filename(filename):
    """
    Normalize the filename, remove non-ASCII characters, and replace spaces and special characters.

    Args:
        filename (str): The filename to sanitize.

    Returns:
        str: The sanitized filename.
    """
    filename = unicodedata.normalize('NFC', filename)
    filename = filename.encode('ascii', 'ignore').decode('ascii')
    filename = filename.replace(' ', '_')
    filename = re.sub(r'[^A-Za-z0-9_\-]', '', filename)
    return filename

def format_filename(filename):
    """
    Format the filename by removing unwanted characters and replacing underscores with spaces.

    Args:
        filename (str): The filename to format.

    Returns:
        str: The formatted filename.
    """
    filename = unicodedata.normalize('NFC', filename)
    filename = filename.encode('ascii', 'ignore').decode('ascii')
    filename = filename.replace('_', ' ')
    filename = re.sub(r'[^A-Za-z0-9 \-\.]', '', filename)
    filename = filename.strip()
    return filename

def shorten_url(url):
    """
    Shorten the URL to create a folder-friendly name.

    Args:
        url (str): The URL to shorten.

    Returns:
        str: A shortened version of the URL.
    """
    parsed_url = urlparse(url)
    netloc = parsed_url.netloc.replace('www.', '').replace('http://', '').replace('https://', '')
    path = parsed_url.path.replace('/', '_')
    short_name = f"{netloc}{path}"
    short_name = re.sub(r'\W+', '_', short_name)  # Replace non-word characters with underscores
    short_name = short_name.replace('_', ' ')  # Replace underscores with spaces
    logger.debug(f"Shortened URL: {url} to {short_name}")
    return short_name
