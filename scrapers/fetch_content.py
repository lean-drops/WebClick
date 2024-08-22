import aiohttp
import ssl
import logging
import json
import re
import time
import uuid

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
import asyncio
import aiofiles
import hashlib
import os

# Logging konfigurieren
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CACHE_DIR = "cache"
SESSION_CACHE_DIR = "session_cache"
MAX_DEPTH = 2  # Auf 2 Ebenen beschränken
visited_urls = set()
taboo_terms = []
taboo_patterns = []

def load_taboo_terms():
    global taboo_terms, taboo_patterns
    try:
        with open('taboo.json') as f:
            taboo_data = json.load(f)
            taboo_terms = taboo_data.get("taboo_terms", [])
            taboo_patterns = taboo_data.get("taboo_patterns", [])
    except FileNotFoundError:
        logger.warning("taboo.json not found, continuing without taboo terms.")
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding taboo.json: {e}")

def is_taboo(link_text, link_url):
    text_lower = link_text.lower()
    url_lower = link_url.lower()

    if any(term in text_lower or term in url_lower for term in taboo_terms):
        return True

    if any(re.search(pattern, text_lower) or re.search(pattern, url_lower) for pattern in taboo_patterns):
        return True

    return False

def normalize_url(url):
    parsed_url = urlparse(url)
    if not parsed_url.scheme:
        url = 'http://' + url  # Füge 'http://' hinzu, wenn kein Schema vorhanden ist
    return urlunparse(parsed_url._replace(fragment=''))

def url_to_filename(url):
    return hashlib.md5(url.encode('utf-8')).hexdigest()

async def save_cache(url, links, session_id):
    # Speichere im zentralen Cache
    global_cache_filename = os.path.join(CACHE_DIR, url_to_filename(url) + ".json")
    os.makedirs(CACHE_DIR, exist_ok=True)
    async with aiofiles.open(global_cache_filename, 'w') as f:
        await f.write(json.dumps(links))

    # Speichere im Session-spezifischen Cache
    session_cache_filename = os.path.join(SESSION_CACHE_DIR, session_id, url_to_filename(url) + ".json")
    os.makedirs(os.path.join(SESSION_CACHE_DIR, session_id), exist_ok=True)
    async with aiofiles.open(session_cache_filename, 'w') as f:
        await f.write(json.dumps(links))

async def load_cache(url):
    # Zuerst im globalen Cache nachsehen
    global_cache_filename = os.path.join(CACHE_DIR, url_to_filename(url) + ".json")
    if os.path.exists(global_cache_filename):
        async with aiofiles.open(global_cache_filename, 'r') as f:
            content = await f.read()
            return json.loads(content)
    return None

import aiohttp
import ssl

async def fetch_website_links(url, session, ssl_context=None):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.zh.ch/',
        'Connection': 'keep-alive',
        'DNT': '1',  # Do Not Track Header
        'Upgrade-Insecure-Requests': '1',
    }

    async with session.get(url, headers=headers, ssl=ssl_context) as response:
        response.raise_for_status()
        return await response.text()

def log_request_details(response, url, start_time):
    elapsed_time = time.time() - start_time
    logger.debug(f"URL: {url} - Status: {response.status} - Time: {elapsed_time:.2f} seconds")

async def scrape_website_links(url, session_id, depth=0, semaphore=None, ssl_context=None):
    if semaphore is None:
        raise ValueError("Semaphore must be provided and not None")

    url = normalize_url(url)

    if url in visited_urls or depth > MAX_DEPTH:
        return {}

    visited_urls.add(url)
    cached_links = await load_cache(url)
    if cached_links:
        return cached_links

    async with semaphore:
        async with aiohttp.ClientSession() as session:
            links = await fetch_website_links(url, session, ssl_context=ssl_context)
            if links is None:
                return {}

            hierarchical_links = {'url': url, 'links': []}

            if depth < MAX_DEPTH:
                tasks = [scrape_website_links(link['url'], session_id, depth + 1, semaphore, ssl_context=ssl_context) for link in links if
                         link['url'] not in visited_urls]
                results = await asyncio.gather(*tasks)

                for i, result in enumerate(results):
                    if result:
                        links[i]['children'] = result

            hierarchical_links['links'].extend(links)

            await save_cache(url, hierarchical_links, session_id)

            return hierarchical_links

async def scrape_url(url, session_id, max_concurrent_tasks=30):
    """
    Funktion, die die URL entgegennimmt und die Scraping-Logik ausführt.
    """
    semaphore = asyncio.Semaphore(max_concurrent_tasks)
    result_structure = await scrape_website_links(url, session_id, semaphore=semaphore)
    return result_structure


def fetch_website_links_simple(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
    }

    # Bypassing SSL verification for simplicity
    response = requests.get(url, headers=headers, verify=False)
    response.raise_for_status()

    # Parse the page content
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract links
    links = []
    for a_tag in soup.find_all('a', href=True):
        link_url = urljoin(url, a_tag['href'])
        links.append({'url': link_url, 'text': a_tag.get_text(strip=True)})

    return links


def scrape_website_links_simple(url):
    try:
        links = fetch_website_links_simple(url)
        return {'url': url, 'links': links}
    except requests.RequestException as e:
        logger.error(f"Error fetching links from {url}: {e}")
        return {'url': url, 'error': str(e)}
# Testfunktion (Nur ausführen, wenn dieses Skript direkt gestartet wird)
if __name__ == "__main__":
    load_taboo_terms()

    async def main():
        session_id = str(uuid.uuid4())  # Eindeutige Session-ID generieren
        test_url = "https://www.zh.ch/de.html"
        result_structure = await scrape_url(test_url, session_id)

        logger.info(f"Scraping completed for {test_url}")
        logger.info(f"Resulting structure: {json.dumps(result_structure, indent=4)}")

    asyncio.run(main())