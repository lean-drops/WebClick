import hashlib
import os
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import aiofiles
from collections import defaultdict
import asyncio
import aiohttp

from app.create_package.create_directory import logger

# Cache directories
CACHE_DIR = "../../cache"
MAPPING_DIR = "../../cache/mapping_cache"

# Tabu-Begriffe aus der JSON-Datei laden
TABOO_JSON_PATH = os.path.join(os.path.dirname(__file__), '..', 'static', 'json', 'taboo.json')
with open(TABOO_JSON_PATH, 'r', encoding='utf-8') as f:
    taboo_data = json.load(f)
    TABOO_TERMS = set([term.lower() for term in taboo_data.get('taboo_terms', [])])

# Utility functions
def url_to_filename(url):
    return hashlib.md5(url.encode('utf-8')).hexdigest()

def sanitize_filename(filename):
    return "".join(x for x in filename if (x.isalnum() or x in "._- "))

def is_valid_url(url, base_netloc):
    parsed_url = urlparse(url)
    return parsed_url.scheme in ('http', 'https') and parsed_url.netloc == base_netloc

def is_binary_file(url):
    binary_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar', '.exe', '.svg', '.mp3', '.mp4', '.avi', '.mov', '.wmv')
    return url.lower().endswith(binary_extensions)

def contains_taboo_term(text):
    text_lower = text.lower()
    return any(term in text_lower for term in TABOO_TERMS)

# Asynchrone Funktion zum Abrufen von Webseiteninhalten mit Fehlerbehandlung
async def fetch_website_content(session, url):
    try:
        async with session.get(url, timeout=10) as response:
            if response.status != 200:
                logger.error(f"Failed to fetch content from {url}: HTTP {response.status}")
                return None, None
            content_type = response.headers.get('Content-Type', '').lower()
            if 'text/html' in content_type:
                content = await response.text()
                return content, content_type
            else:
                return None, content_type
    except Exception as e:
        logger.error(f"Error fetching {url}: {str(e)}")
        return None, None

# Asynchrone Funktion zum Extrahieren von Links und Struktur aus dem HTML-Inhalt
async def extract_links(url, session, url_mapping, base_netloc, parent_id=None, max_depth=2, current_depth=0, visited_urls=None, semaphore=None):
    if visited_urls is None:
        visited_urls = set()

    if current_depth > max_depth:
        return

    parsed_url = urlparse(url)
    normalized_url = parsed_url._replace(fragment='').geturl()

    if normalized_url in visited_urls:
        return

    visited_urls.add(normalized_url)

    # Semaphore verwenden, um die Anzahl gleichzeitiger Verbindungen zu begrenzen
    async with semaphore:
        content, content_type = await fetch_website_content(session, normalized_url)

    if content is None and content_type is None:
        return

    soup = BeautifulSoup(content, 'lxml') if content else None
    page_id = url_to_filename(normalized_url)
    title = sanitize_filename(soup.title.string.strip() if soup and soup.title else normalized_url)

    # Check if the title contains taboo terms
    if contains_taboo_term(title):
        logger.info(f"Skipping link due to taboo term in title: {title} ({normalized_url})")
        return

    # Add the page to the mapping structure
    if page_id not in url_mapping:
        url_mapping[page_id] = {
            'title': title,
            'url': normalized_url,
            'parent': [] if parent_id is None else [parent_id],
            'children': [],
            'is_download': is_binary_file(normalized_url)
        }
    else:
        # Add parent ID if not already present
        if parent_id and parent_id not in url_mapping[page_id]['parent']:
            url_mapping[page_id]['parent'].append(parent_id)

    # Add this page to the parent's children
    if parent_id:
        if page_id not in url_mapping[parent_id]['children']:
            url_mapping[parent_id]['children'].append(page_id)

    # Only extract further links if the page is HTML
    if soup:
        tasks = []
        # Extract and process links
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(normalized_url, href)

            if not is_valid_url(full_url, base_netloc):
                continue

            if is_binary_file(full_url):
                continue

            link_text = link.get_text(strip=True)
            if contains_taboo_term(link_text):
                logger.info(f"Skipping link due to taboo term in link text: {link_text} ({full_url})")
                continue

            task = extract_links(
                full_url,
                session,
                url_mapping,
                base_netloc,
                parent_id=page_id,
                max_depth=max_depth,
                current_depth=current_depth+1,
                visited_urls=visited_urls,
                semaphore=semaphore
            )
            tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks)

# Funktion zum Scrapen einer Website und Speichern der Struktur im Cache
async def scrape_website(url, max_depth=2, max_concurrency=100):
    logger.debug(f"Starting to scrape website: {url}")
    url_mapping = defaultdict(dict)

    semaphore = asyncio.Semaphore(max_concurrency)

    parsed_base_url = urlparse(url)
    base_netloc = parsed_base_url.netloc

    timeout = aiohttp.ClientTimeout(total=30)
    connector = aiohttp.TCPConnector(limit_per_host=max_concurrency, ssl=False)

    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; Bot/1.0; +http://yourwebsite.com/bot)'
    }

    base_page_id = url_to_filename(url)

    # Lade bestehenden Cache, falls vorhanden
    cache_file = os.path.join(MAPPING_DIR, f"{hashlib.md5(url.encode()).hexdigest()}.json")
    if os.path.exists(cache_file):
        async with aiofiles.open(cache_file, 'r', encoding='utf-8') as f:
            cached_data = await f.read()
            url_mapping.update(json.loads(cached_data))
            logger.info(f"Using cached data for {url}")
            return {
                'url': url,
                'url_mapping': url_mapping,
                'base_page_id': base_page_id
            }

    async with aiohttp.ClientSession(timeout=timeout, connector=connector, headers=headers) as session:
        await extract_links(url, session, url_mapping, base_netloc, parent_id=None, max_depth=max_depth, semaphore=semaphore)

    # Speichere den Cache am Ende
    async with aiofiles.open(cache_file, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(url_mapping, indent=4))

    logger.info(f"Successfully scraped and cached website mapping for {url}")
    return {
        'url': url,
        'url_mapping': url_mapping,
        'base_page_id': base_page_id
    }

# Test block
if __name__ == "__main__":
    import asyncio

    async def main():
        os.makedirs(CACHE_DIR, exist_ok=True)
        os.makedirs(MAPPING_DIR, exist_ok=True)

        test_url = "https://www.reddit.com/r/excel/comments/ypx45u/office_scripts_for_excel_online/"
        result = await scrape_website(test_url, max_depth=2, max_concurrency=100)

        if 'error' in result:
            print(f"Error scraping website: {result['error']}")
        else:
            print(f"Scraping successful for {result['url']}")
            output_file = "output.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result['url_mapping'], f, indent=4)
            print(f"Result saved to {output_file}")

    asyncio.run(main())
