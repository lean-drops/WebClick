import hashlib
import os
import json
import aiohttp
import ssl
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import aiofiles
from collections import defaultdict
from scrapers.create_zipfile import logger

# Cache directories
CACHE_DIR = "../app/cache"
MAPPING_DIR = "mapping_cache"

# Utility functions
def url_to_filename(url):
    return hashlib.md5(url.encode('utf-8')).hexdigest()

def sanitize_filename(filename):
    return "".join(x for x in filename if (x.isalnum() or x in "._- "))

# Function to fetch website content with caching and error handling
import aiohttp
import ssl

import aiohttp
import ssl
import asyncio


async def fetch_website_content(url, retries=3):
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    for attempt in range(retries):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, ssl=ssl_context, timeout=10) as response:
                    if response.status == 200:
                        content = await response.text()
                        return content, ""
                    else:
                        return None, f"Failed to fetch content from {url}: HTTP {response.status}"
            except aiohttp.ClientConnectorError as e:
                print(f"Attempt {attempt + 1} failed: Cannot connect to host {url}: {str(e)}")
                await asyncio.sleep(2)  # Wartezeit zwischen den Versuchen
            except aiohttp.ClientError as e:
                return None, f"Aiohttp client error {url}: {str(e)}"
            except Exception as e:
                return None, f"An unexpected error occurred: {str(e)}"

    return None, f"Failed to fetch content from {url} after {retries} attempts"


# Function to extract links and structure from the HTML content
def extract_links(soup, base_url, url_mapping):
    pages = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        full_url = urljoin(base_url, href)
        title = sanitize_filename(link.text.strip() or full_url)

        # Create hashtable entry
        page_id = url_to_filename(full_url)
        url_mapping[page_id] = {
            'title': title,
            'url': full_url,
            'parent': url_to_filename(base_url)
        }

        pages.append({'id': page_id, 'title': title, 'url': full_url})

    return pages

# Function to scrape a website and store the structure in a cache
async def scrape_website(url, url_mapping):
    logger.debug(f"Starting to scrape website: {url}")
    content, message = await fetch_website_content(url)
    if content is None:
        logger.error(f"Failed to scrape website: {url}, Error: {message}")
        return {'error': message}

    # Hash the URL to create a unique filename for the mapping cache
    mapping_file = os.path.join(MAPPING_DIR, f"{hashlib.md5(url.encode()).hexdigest()}.json")

    # Ensure the mapping cache directory exists
    os.makedirs(MAPPING_DIR, exist_ok=True)

    # Process the content and extract links
    soup = BeautifulSoup(content, 'html.parser')
    pages = extract_links(soup, url, url_mapping)

    # Save the mapping information to the mapping cache
    async with aiofiles.open(mapping_file, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(pages, indent=4))

    logger.info(f"Successfully scraped and cached website mapping for {url}")
    return {
        'url': url,
        'pages': pages
    }

# Test block
if __name__ == "__main__":
    import asyncio

    async def main():
        os.makedirs(CACHE_DIR, exist_ok=True)
        os.makedirs(MAPPING_DIR, exist_ok=True)

        test_url = "https://www.walternagel.de/webarchivierung?keyword=internetseiten%20archivieren&device=c&network=g&gad_source=1&gclid=Cj0KCQjww5u2BhDeARIsALBuLnMAf__pqsYDTWVd-J7eouzpTVlFYJiR4qeg0qBJuQSZJtMYD58RF5caArKLEALw_wcB"
        url_mapping = defaultdict(dict)

        result = await scrape_website(test_url, url_mapping)

        if 'error' in result:
            print(f"Error scraping website: {result['error']}")
        else:
            print(f"Scraping successful for {result['url']}")
            print(json.dumps(url_mapping, indent=4))

    asyncio.run(main())
