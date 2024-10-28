# app/scrapers/fetch_content.py

import hashlib
import os
import json
import logging
import time
import random
from urllib.parse import urljoin, urlparse
import asyncio
import httpx
from collections import defaultdict
from lxml import html
import aiofiles

# Adjust the import path to include the project root directory
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, project_root)  # Ensure project_root is at the start of sys.path

# Now import the configuration
from config import CACHE_DIR, MAPPING_DIR, TABOO_JSON_PATH, logger

# Import the 'rich' library for visual display
from rich import print
from rich.tree import Tree

# Error tracking
error_counts = defaultdict(int)

# Load taboo terms from the JSON file
with open(TABOO_JSON_PATH, 'r', encoding='utf-8') as f:
    taboo_data = json.load(f)
    TABOO_TERMS = set(term.lower() for term in taboo_data.get('taboo_terms', []))

# Maximum number of concurrent connections
MAX_CONCURRENCY = 100  # Adjust as needed for performance

# Semaphore for limiting concurrency
semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

# Utility functions
def url_to_filename(url):
    filename = hashlib.md5(url.encode('utf-8')).hexdigest()
    logger.debug(f"Generated filename for URL {url}: {filename}")
    return filename

def sanitize_filename(filename):
    sanitized = "".join(x for x in filename if (x.isalnum() or x in "._- "))
    logger.debug(f"Sanitized filename: {sanitized}")
    return sanitized

def is_valid_url(url, base_netloc):
    parsed_url = urlparse(url)
    is_valid = parsed_url.scheme in ('http', 'https') and parsed_url.netloc == base_netloc
    logger.debug(f"URL {url} is {'valid' if is_valid else 'invalid'}")
    return is_valid

def is_binary_file(url):
    binary_extensions = (
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.pdf', '.doc', '.docx', '.xls',
        '.xlsx', '.zip', '.rar', '.exe', '.svg', '.mp3', '.mp4', '.avi', '.mov', '.wmv',
        '.php', '.aspx', '.jsp'  # Add more unwanted extensions here
    )
    is_binary = url.lower().endswith(binary_extensions)
    logger.debug(f"URL {url} is {'a binary file' if is_binary else 'not a binary file'}")
    return is_binary

def contains_taboo_term(text):
    if not text:
        return False
    text_lower = text.lower()
    has_taboo = any(term in text_lower for term in TABOO_TERMS)
    logger.debug(f"Text '{text}' {'contains' if has_taboo else 'does not contain'} a taboo term")
    return has_taboo

# Asynchronous function to fetch website content with error handling and rate limiting
async def fetch_website_content(client, url, retries=3, delay=1):
    for attempt in range(retries):
        try:
            async with semaphore:
                await asyncio.sleep(random.uniform(0.1, 0.3))  # Random wait time to avoid overloading servers
                response = await client.get(url, timeout=10)
            if response.status_code == 429:  # If rate limit is reached
                logger.warning(f"Rate limit reached for {url}. Waiting: {delay} seconds.")
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff
                continue
            if response.status_code != 200:
                error_message = f"Error fetching {url}: HTTP {response.status_code}"
                logger.warning(error_message)
                error_counts[error_message] += 1  # Count errors
                return None, None
            content_type = response.headers.get('Content-Type', '').lower()
            logger.debug(f"Content type of {url}: {content_type}")
            if 'text/html' in content_type:
                content = response.text
                logger.debug(f"Successfully fetched HTML content from {url}")
                return content, content_type
            else:
                logger.debug(f"No HTML content at {url}")
                return None, content_type
        except Exception as e:
            error_message = f"Error fetching {url}: {e}"
            logger.error(error_message)
            error_counts[error_message] += 1  # Count errors
            await asyncio.sleep(delay)
            delay *= 2
    return None, None

# Asynchronous function to extract links and structure from HTML content
async def extract_links(url, client, url_mapping, base_netloc, level=0, max_depth=2, visited_urls=None, parent_id=None):
    if visited_urls is None:
        visited_urls = set()

    if level > max_depth:
        logger.debug(f"Maximum depth reached at {url}")
        return

    parsed_url = urlparse(url)
    normalized_url = parsed_url._replace(fragment='').geturl()

    if normalized_url in visited_urls:
        logger.debug(f"URL already visited: {normalized_url}")
        return

    visited_urls.add(normalized_url)
    logger.debug(f"Visiting URL: {normalized_url}")

    content, content_type = await fetch_website_content(client, normalized_url)

    if content is None and content_type is None:
        logger.debug(f"Content is None for URL: {normalized_url}")
        return

    parser = html.fromstring(content) if content else None  # Use lxml

    page_id = url_to_filename(normalized_url)
    if parser is not None:
        title_element = parser.find(".//title")
        if title_element is not None and title_element.text is not None:
            title_text = title_element.text.strip()
        else:
            title_text = normalized_url  # Fallback if no title is present
    else:
        title_text = normalized_url  # Fallback if the parser fails

    title = sanitize_filename(title_text)

    # Check for taboo terms in the title
    if contains_taboo_term(title):
        logger.info(f"Skipping page due to taboo term in title: {title} ({normalized_url})")
        return

    # Add the page to the mapping structure and set the parent_id
    if page_id not in url_mapping:
        url_mapping[page_id] = {
            'title': title,
            'url': normalized_url,
            'children': [],
            'level': level,
            'parent_id': parent_id  # Set the parent_id here
        }
        logger.debug(f"Page added: {title} (ID: {page_id}) with parent_id: {parent_id}")

    # Only continue extracting if the page is HTML
    if parser is not None:
        tasks = []
        links = []
        # Extract and process links
        for element in parser.xpath('//a[@href]'):
            href = element.get('href')
            full_url = urljoin(normalized_url, href)

            if not is_valid_url(full_url, base_netloc):
                continue

            if is_binary_file(full_url):
                logger.debug(f"Skipping binary file or unwanted extension: {full_url}")
                continue

            link_text = element.text_content().strip()
            if contains_taboo_term(link_text):
                continue

            links.append((full_url, link_text))

        # Remove duplicates immediately to improve performance
        unique_links = list(set(links))

        for full_url, link_text in unique_links:
            child_id = url_to_filename(full_url)
            if child_id not in url_mapping[page_id]['children']:
                url_mapping[page_id]['children'].append(child_id)
                logger.debug(f"Link added: {full_url} as child of {normalized_url}")

            # Recursive call with the current page_id as parent_id
            task = extract_links(
                full_url,
                client,
                url_mapping,
                base_netloc,
                level=level + 1,
                max_depth=max_depth,
                visited_urls=visited_urls,
                parent_id=page_id  # Pass the parent_id to the child
            )
            tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks)

# Ensure directory exists
def ensure_directory_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)
        logger.info(f"Directory created: {path}")

# Asynchronous function to scrape a website and save the structure in the cache
async def scrape_website(url, max_depth=2, max_concurrency=100, use_cache=True):
    logger.info(f"Starting scraping for {url}")
    url_mapping = {}

    parsed_base_url = urlparse(url)
    base_netloc = parsed_base_url.netloc

    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; Bot/1.0; +http://yourwebsite.com/bot)'
    }

    limits = httpx.Limits(max_keepalive_connections=max_concurrency, max_connections=max_concurrency)

    base_page_id = url_to_filename(url)

    # Load existing cache if available
    cache_file = os.path.join(MAPPING_DIR, f"{hashlib.md5(url.encode()).hexdigest()}.json")

    ensure_directory_exists(MAPPING_DIR)  # Check and create the cache directory

    if use_cache and os.path.exists(cache_file):
        logger.info(f"Using cached data for {url}")
        async with aiofiles.open(cache_file, 'r', encoding='utf-8') as f:
            cached_data = await f.read()
            logger.debug(f"Cached data loaded: {cached_data[:100]}...")  # Show first 100 characters
            url_mapping = json.loads(cached_data)

            # Check if the cache contains data
            if url_mapping:
                logger.info(f"Cache successfully loaded for {url}")
                return {
                    'url': url,
                    'url_mapping': url_mapping,
                    'base_page_id': base_page_id
                }
            else:
                logger.info(f"Cache is empty or invalid for {url}. Starting new scraping.")

    # Disable SSL verification with verify=False
    async with httpx.AsyncClient(headers=headers, limits=limits, http2=True, verify=False) as client:
        await extract_links(url, client, url_mapping, base_netloc, level=0, max_depth=max_depth)

    # Check if scraping was successful
    if not url_mapping:
        logger.warning(f"No data found after scraping for {url}.")
    else:
        logger.info(f"Scraping completed. Pages found: {len(url_mapping)}")

    # Save the cache at the end
    ensure_directory_exists(MAPPING_DIR)  # Check and create the cache directory
    async with aiofiles.open(cache_file, 'w', encoding='utf-8') as f:
        cache_data = json.dumps(url_mapping, indent=4)
        await f.write(cache_data)
        logger.debug(f"Cache saved for {url}: {cache_data[:100]}...")  # Show first 100 characters

    return {
        'url': url,
        'url_mapping': url_mapping,
        'base_page_id': base_page_id
    }

# Function to output the error report
def log_error_summary():
    if error_counts:
        logger.info("\n--- Error Report ---")
        for error_message, count in error_counts.items():
            logger.info(f"{error_message} - occurred {count} times")
    else:
        logger.info("No errors occurred.")

# Function to get URLs from a JSON file
def get_urls_from_json(json_path):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            urls = data.get('urls', [])
            if not urls:
                logger.error("No URLs found in the JSON file.")
            return urls
    except Exception as e:
        logger.error(f"Error reading JSON file: {e}")
        return []

# Function to display the mapping using rich.Tree
def display_mapping(url_mapping, base_page_id):
    if base_page_id not in url_mapping:
        print("Base page ID not found in the URL mapping.")
        return

    base_page = url_mapping[base_page_id]
    tree = Tree(f"[link={base_page['url']}] {base_page['title']}", guide_style="bold bright_blue")

    def add_children(node, page_id):
        page = url_mapping.get(page_id)
        if not page:
            return
        for child_id in page.get('children', []):
            child = url_mapping.get(child_id)
            if not child:
                continue
            child_node = node.add(f"[link={child['url']}] {child['title']}")
            add_children(child_node, child_id)

    add_children(tree, base_page_id)
    print(tree)

# Main block for testing
if __name__ == "__main__":
    async def main():
        # Path to the JSON file containing URLs
        urls_json_path = os.path.join(current_dir, 'urls.json')
        urls = get_urls_from_json(urls_json_path)

        if not urls:
            print("No URLs to process.")
            return

        for test_url in urls:
            start_time = time.time()
            result = await scrape_website(test_url, max_depth=2, max_concurrency=MAX_CONCURRENCY, use_cache=False)
            end_time = time.time()

            elapsed_time = end_time - start_time

            if 'error' in result:
                logger.error(f"Error scraping the website: {result['error']}")
            else:
                num_pages = len(result['url_mapping'])
                time_per_page = elapsed_time / num_pages if num_pages > 0 else 0
                logger.info(f"Scraping successful for {result['url']}")
                logger.info(f"Total pages collected: {num_pages}")
                logger.info(f"Execution time: {elapsed_time:.2f} seconds")
                logger.info(f"Average time per page: {time_per_page:.4f} seconds")

                output_file = os.path.join(CACHE_DIR, f"output_mapping_{url_to_filename(test_url)}.json")
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result['url_mapping'], f, indent=4)
                logger.info(f"Result saved in {output_file}")

                # Display the mapping visually
                print(f"\nVisual representation of the mapping for {test_url}:\n")
                display_mapping(result['url_mapping'], result['base_page_id'])

            # At the end, output the error report
            log_error_summary()

    asyncio.run(main())
