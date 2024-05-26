import requests
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Logger konfigurieren
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_website_content(url):
    """
    Fetch the HTML content of a website.

    Args:
        url (str): The URL of the website to fetch.

    Returns:
        tuple: A tuple containing the content (str or None) and a message (str).
    """
    try:
        response = requests.get(url, timeout=10)  # Set timeout to prevent hanging
        response.raise_for_status()
        logger.info(f"Successfully fetched content from {url}")
        return response.content, ""
    except requests.RequestException as e:
        logger.error(f"Failed to fetch content from {url}: {e}")
        return None, f"Failed to fetch content from {url}: {e}"

def extract_links(soup, base_url):
    """
    Extract all links from the HTML soup.

    Args:
        soup (BeautifulSoup): Parsed HTML content.
        base_url (str): Base URL for resolving relative links.

    Returns:
        list: A list of dictionaries containing link titles and URLs.
    """
    pages = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        full_url = urljoin(base_url, href)
        title = link.text.strip() or full_url
        pages.append({'title': title, 'url': full_url})
    logger.info(f"Extracted {len(pages)} links from {base_url}")
    return pages

def scrape_website(url):
    """
    Scrape the website and return links without creating screenshots.

    Args:
        url (str): The URL of the website to scrape.

    Returns:
        dict: A dictionary containing the URL and the list of pages or an error message.
    """
    logger.debug(f"Starting to scrape website: {url}")
    content, message = fetch_website_content(url)
    if content is None:
        logger.error(f"Failed to scrape website: {url}, Error: {message}")
        return {'error': message}

    soup = BeautifulSoup(content, 'html.parser')
    pages = extract_links(soup, url)

    return {
        'url': url,
        'pages': pages
    }
