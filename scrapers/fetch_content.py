import aiohttp
import ssl
import logging
import json
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from utils.naming_utils import sanitize_filename, logger

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fetch_website_content(url):
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, ssl=ssl_context, timeout=10) as response:
                response.raise_for_status()

                # Versuche, die Zeichenkodierung aus den Headern zu erhalten
                content_type = response.headers.get('Content-Type', '').lower()
                encoding = 'utf-8'  # Standard auf UTF-8 setzen
                if 'charset=' in content_type:
                    encoding = content_type.split('charset=')[-1]

                # Inhalte dekodieren und ungültige Zeichen durch "?" ersetzen
                content = await response.text(encoding=encoding, errors='replace')
                logger.info(f"Successfully fetched content from {url}")
                return content, ""
    except aiohttp.ClientError as e:
        logger.error(f"Failed to fetch content from {url}: {e}", exc_info=True)
        return None, f"Failed to fetch content from {url}: {e}"


def load_taboo_terms():
    try:
        with open('taboo.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("taboo.json not found, continuing without taboo terms.")
        return {"taboo_terms": [], "taboo_patterns": []}


def is_taboo(link_text, link_url, taboo_terms, taboo_patterns):
    text_lower = link_text.lower()
    url_lower = link_url.lower()

    if any(term in text_lower or term in url_lower for term in taboo_terms):
        return True

    if any(re.search(pattern, text_lower) or re.search(pattern, url_lower) for pattern in taboo_patterns):
        return True

    return False


def extract_links(soup, base_url):
    taboo_data = load_taboo_terms()
    taboo_terms = taboo_data.get("taboo_terms", [])
    taboo_patterns = taboo_data.get("taboo_patterns", [])

    pages = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        full_url = urljoin(base_url, href)
        title = sanitize_filename(link.text.strip() or full_url)

        if is_taboo(title, full_url, taboo_terms, taboo_patterns):
            logger.info(f"Filtered out taboo link: {title} ({full_url})")
            continue

        pages.append({'title': title, 'url': full_url})

    logger.info(f"Extracted {len(pages)} links from {base_url}")
    return pages


async def scrape_website(url):
    logger.debug(f"Starting to scrape website: {url}")
    content, message = await fetch_website_content(url)
    if content is None:
        logger.error(f"Failed to scrape website: {url}, Error: {message}")
        return {'error': message}

    soup = BeautifulSoup(content, 'html.parser')
    pages = extract_links(soup, url)

    return {
        'url': url,
        'pages': pages
    }


# Main Block zum Testen des Skripts
if __name__ == "__main__":
    import asyncio


    async def main():
        test_url = "https://www.zh.ch/de/direktion-der-justiz-und-des-innern/staatsarchiv.html"
        result = await scrape_website(test_url)

        if 'error' in result:
            logger.error(f"Error scraping website: {result['error']}")
        else:
            logger.info(f"Scraping successful for {result['url']}")
            for page in result['pages']:
                logger.info(f"Found page: {page['title']} - {page['url']}")


    asyncio.run(main())
