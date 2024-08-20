import os
import logging
import traceback
import asyncio

import aiohttp
from quart import Blueprint, request, jsonify, render_template, send_file, Response
from datetime import datetime
import zipfile

from scrapers.fetch_content import scrape_website_links
from scrapers.screenshot import load_cookie_selectors, start_screenshot_process_sequentially, is_valid_url

# Logger configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/application.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Path to cookies_selector.json and loading selectors
COOKIES_SELECTOR_PATH = r"C:\Users\BZZ1391\Bingo\WebClick\app\static\js\cookies_selector.json"
selectors = load_cookie_selectors(COOKIES_SELECTOR_PATH)

# Blueprint definition
main = Blueprint('main', __name__)

@main.route('/')
async def index():
    """
    Renders the homepage of the application.
    """
    timestamp = datetime.now().timestamp()

    logger.info("Rendering the homepage")
    return await render_template('index.html', timestamp=timestamp)


@main.route('/scrape_sub_links', methods=['POST'])
async def scrape_sub_links():
    """
    API endpoint to scrape sub-links from a given website.
    """
    data = await request.json
    url = data.get('url')

    if not url:
        logger.warning("No URL provided in the request")
        return jsonify({"error": "No URL provided"}), 400

    if not is_valid_url(url):
        logger.warning(f"Invalid URL provided: {url}")
        return jsonify({"error": "Invalid URL provided"}), 400

    logger.info(f"Scrape sub-links request received for URL: {url}")

    try:
        content = await scrape_website_links(url)

        if 'error' in content:
            logger.error(f"Scraping failed with error: {content['error']}")
            return jsonify(content), 500

        logger.info(f"Scraping sub-links successful for URL: {url}")
        return jsonify(content)

    except asyncio.TimeoutError:
        logger.error(f"Timeout occurred while scraping {url}")
        return jsonify({"error": "Timeout occurred while scraping the website"}), 500

    except aiohttp.ClientError as e:
        logger.error(f"Network-related error while scraping {url}: {e}")
        return jsonify({"error": f"Network error occurred: {str(e)}"}), 500

    except Exception as e:
        logger.error(f"Unexpected error scraping sub-links: {e}", exc_info=True)
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@main.route('/archive', methods=['POST'])
async def archive():
    """
    API endpoint to take screenshots of selected links and archive them.
    """
    data = await request.json
    urls = data.get('urls', [])
    main_url = data.get('url')
    save_path = data.get('save_path')  # Benutzerdefinierter Speicherpfad

    if not main_url:
        logger.warning("No main URL provided in the archive request")
        return jsonify({"error": "No main URL provided"}), 400

    if not save_path:
        logger.warning("No save path provided in the archive request")
        return jsonify({"error": "No save path provided"}), 400

    # Ensure the main URL is always included
    if not urls:
        urls = [main_url]
    elif main_url not in urls:
        urls.insert(0, main_url)

    logger.info(f"Archive request received for URLs: {urls}")

    try:
        run_number = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_folder = os.path.join(save_path, f'screenshots_run_{run_number}')
        os.makedirs(base_folder, exist_ok=True)

        driver_paths = [
            r"C:\Google Neu\chromedriver-win32",
            r"C:\Google Neu\chromedriver-win32 Parallel 1",
            r"C:\Google Neu\chromedriver-win32 Parallel 2"
        ]

        chrome_binary_paths = [
            r"C:\Google Neu\chrome-win32\chrome.exe",
            r"C:\Google Neu\chrome-win32 Parallel 1\chrome.exe",
            r"C:\Google Neu\chrome-win32 Parallel 2\chrome.exe"
        ]

        await start_screenshot_process_sequentially(urls, base_folder, selectors, driver_paths, chrome_binary_paths)

        zip_filename = f"screenshots_run_{run_number}.zip"
        zip_filepath = os.path.join(save_path, zip_filename)

        with zipfile.ZipFile(zip_filepath, 'w') as zipf:
            for root, dirs, files in os.walk(base_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, base_folder))

        logger.info(f"All screenshots have been taken and zipped into {zip_filepath}")
        return jsonify({"zip_path": zip_filepath})

    except Exception as e:
        logger.error(f"Error during archiving process: {e}", exc_info=True)
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500
