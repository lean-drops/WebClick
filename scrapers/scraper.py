import subprocess
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import requests
import logging

# Logger konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)
        logger.info(f"Directory created at {path}")

def run_screenshot_script(url, screenshot_path):
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
    try:
        response = requests.get(url)
        response.raise_for_status()
        logger.info(f"Successfully fetched content from {url}")
        return response.content, ""
    except requests.RequestException as e:
        logger.error(f"Failed to fetch content from {url}: {e}")
        return None, f"Failed to fetch content from {url}: {e}"

def extract_links(soup, base_url):
    pages = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        full_url = urljoin(base_url, href)  # Absolute URL erstellen
        title = link.text.strip() or full_url  # Fallback auf URL, falls kein Text vorhanden
        pages.append({'title': title, 'url': full_url})
    logger.info(f"Extracted {len(pages)} links from {base_url}")
    return pages

def scrape_website(url, output_path):
    create_directory(output_path)
    screenshot_path = os.path.join(output_path, 'main.png')

    # Run the screenshot script
    success, message = run_screenshot_script(url, screenshot_path)
    if not success:
        return {'error': message}

    # Fetch website content
    content, message = fetch_website_content(url)
    if content is None:
        return {'error': message}

    # Parse the content
    soup = BeautifulSoup(content, 'html.parser')
    pages = extract_links(soup, url)

    return {
        'url': url,
        'screenshot': screenshot_path,
        'pages': pages
    }

def scrape_multiple_websites(urls, base_folder):
    all_contents = []
    create_directory(base_folder)
    for url in urls:
        content = scrape_website(url, base_folder)
        if 'error' in content:
            logger.warning(f"Skipping {url} due to error: {content['error']}")
            continue
        all_contents.append(content)
    logger.info(f"Scraped content from {len(all_contents)} out of {len(urls)} websites")
    return all_contents
