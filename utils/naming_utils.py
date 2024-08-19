import re
import unicodedata
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

def sanitize_filename(filename):
    """
    Sanitize the filename by removing non-ASCII characters, replacing spaces and special characters.

    Args:
        filename (str): The filename to sanitize.

    Returns:
        str: The sanitized filename.
    """
    filename = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('ascii')
    filename = re.sub(r'[^A-Za-z0-9\-_]', '', filename)
    return filename

def shorten_url(url):
    """
    Shorten the URL to create a more concise, folder-friendly name.

    Args:
        url (str): The URL to shorten.

    Returns:
        str: A shortened version of the URL.
    """
    parsed_url = urlparse(url)
    netloc = parsed_url.netloc.replace('www.', '').replace('http://', '').replace('https://', '')
    path = parsed_url.path.replace('/', '_')
    short_name = f"{netloc}{path}".strip('_')  # Remove leading/trailing underscores
    short_name = re.sub(r'[_]+', '_', short_name)  # Replace multiple underscores with a single one
    short_name = sanitize_filename(short_name)
    logger.debug(f"Shortened URL: {url} to {short_name}")
    return short_name
