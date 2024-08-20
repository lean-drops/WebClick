import aiohttp
import ssl
import logging
import json
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from utils.naming_utils import sanitize_filename, logger
import asyncio
# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_taboo_terms():
    try:
        with open('taboo.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning("taboo.json not found, continuing without taboo terms.")
        return {"taboo_terms": [], "taboo_patterns": []}
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding taboo.json: {e}")
        return {"taboo_terms": [], "taboo_patterns": []}


def is_taboo(link_text, link_url, taboo_terms, taboo_patterns):
    text_lower = link_text.lower()
    url_lower = link_url.lower()

    # Check for taboo terms
    if any(term in text_lower or term in url_lower for term in taboo_terms):
        return True

    # Check for taboo patterns
    if any(re.search(pattern, text_lower) or re.search(pattern, url_lower) for pattern in taboo_patterns):
        return True

    return False


async def fetch_website_links(url, session):
    """Fetches only the links from a website without loading the entire content."""
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE  # Deaktiviert die Zertifikatsprüfung

    try:
        async with session.get(url, ssl=ssl_context, timeout=10) as response:
            response.raise_for_status()
            content = await response.text()  # Wir laden nur den HTML-Text, ohne ihn komplett zu analysieren
            soup = BeautifulSoup(content, 'html.parser')

            # Load taboo terms and patterns
            taboo_data = load_taboo_terms()
            taboo_terms = taboo_data.get("taboo_terms", [])
            taboo_patterns = taboo_data.get("taboo_patterns", [])

            links = []
            for a in soup.find_all('a', href=True):
                link_url = urljoin(url, a['href'])
                link_text = a.get_text(strip=True) or a['href']

                if not is_taboo(link_text, link_url, taboo_terms, taboo_patterns):
                    links.append({
                        'title': sanitize_filename(link_text),
                        'url': link_url
                    })

            logger.info(f"Extracted {len(links)} non-taboo links from {url}")
            return links, ""
    except aiohttp.ClientError as e:
        logger.error(f"Failed to fetch links from {url}: {e}", exc_info=True)
        return None, f"Failed to fetch links from {url}: {e}"
    except asyncio.TimeoutError:
        logger.error(f"Timeout error fetching links from {url}")
        return None, f"Timeout error fetching links from {url}"
    except Exception as e:
        logger.error(f"Unexpected error fetching links from {url}: {e}", exc_info=True)
        return None, f"Unexpected error fetching links from {url}: {e}"


async def scrape_website_links(url):
    """Scrapes only the links from a website."""
    logger.debug(f"Starting to scrape links from website: {url}")
    async with aiohttp.ClientSession() as session:
        links, message = await fetch_website_links(url, session)
        if links is None:
            logger.error(f"Failed to scrape links from website: {url}, Error: {message}")
            return {'error': message}

        return {
            'url': url,
            'links': links
        }


# Testfunktion
if __name__ == "__main__":
    import asyncio


    async def main():
        test_url = r"https://www.zh.ch/de/sicherheit-justiz/strafvollzug-und-strafrechtliche-massnahmen/jahresbericht-2023.html"
        result = await scrape_website_links(test_url)

        if 'error' in result:
            logger.error(f"Error scraping website: {result['error']}")
        else:
            logger.info(f"Scraping successful for {result['url']}")
            for link in result['links']:
                logger.info(f"Found link: {link['title']} - {link['url']}")


    asyncio.run(main())
