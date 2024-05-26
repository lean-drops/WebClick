import subprocess
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import requests
import logging
import re

# Logger konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_directory(path):
    """Create a directory if it doesn't exist."""
    if not os.path.exists(path):
        os.makedirs(path)
        logger.info(f"Directory created at {path}")

def run_screenshot_script(url, screenshot_path):
    """Run the screenshot script using Node.js and Puppeteer."""
    try:
        result = subprocess.run(['node', 'app/static/js/screenshot.js', url, screenshot_path], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Failed to create screenshot for {url}: {result.stderr}")
            return False, f"Failed to create screenshot for {url}: {result.stderr}"
        logger.info(f"Screenshot saved at {screenshot_path}")
        return True, ""
    except Exception as e:
        logger.error(f"Error running screenshot script for {url}: {e}")
        return False, f"Error running screenshot script for {url}: {e}"

def fetch_website_content(url):
    """Fetch the HTML content of a website."""
    try:
        response = requests.get(url, timeout=10)  # Set timeout to prevent hanging
        response.raise_for_status()
        logger.info(f"Successfully fetched content from {url}")
        return response.content, ""
    except requests.RequestException as e:
        logger.error(f"Failed to fetch content from {url}: {e}")
        return None, f"Failed to fetch content from {url}: {e}"

def extract_links(soup, base_url):
    """Extract all links from the HTML soup."""
    pages = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        full_url = urljoin(base_url, href)
        title = link.text.strip() or full_url
        pages.append({'title': title, 'url': full_url})
    logger.info(f"Extracted {len(pages)} links from {base_url}")
    return pages

def scrape_website(url):
    """Scrape the website and return links without creating screenshots."""
    content, message = fetch_website_content(url)
    if content is None:
        return {'error': message}

    soup = BeautifulSoup(content, 'html.parser')
    pages = extract_links(soup, url)

    return {
        'url': url,
        'pages': pages
    }

def scrape_and_screenshot(url, output_path):
    """Scrape the website and save its main screenshot."""
    create_directory(output_path)
    screenshot_path = os.path.join(output_path, 'main.png')

    success, message = run_screenshot_script(url, screenshot_path)
    if not success:
        return {'error': message}

    return {'screenshot': screenshot_path}

def scrape_multiple_websites(urls, base_folder):
    """Scrape multiple websites and save their screenshots."""
    all_contents = []
    create_directory(base_folder)
    for i, url in enumerate(urls):
        folder_name = shorten_url(url)
        screenshot_path = os.path.join(base_folder, folder_name, f'page_{i+1}.png')
        create_directory(os.path.join(base_folder, folder_name))
        content = scrape_website(url)
        if 'error' in content:
            logger.warning(f"Skipping {url} due to error: {content['error']}")
            continue
        screenshot_result = scrape_and_screenshot(url, os.path.join(base_folder, folder_name))
        if 'error' in screenshot_result:
            logger.warning(f"Skipping screenshot for {url} due to error: {screenshot_result['error']}")
            continue
        content['screenshot'] = screenshot_result['screenshot']
        all_contents.append(content)
    logger.info(f"Scraped content from {len(all_contents)} out of {len(urls)} websites")
    return all_contents

def shorten_url(url):
    """Shorten the URL to create a folder-friendly name."""
    parsed_url = urlparse(url)
    short_name = re.sub(r'\W+', '', parsed_url.netloc)
    return short_name
