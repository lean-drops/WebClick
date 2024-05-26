import subprocess
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from scrapers.create_directory import create_directory
from scrapers.link_processor import create_zip_file

from utils.naming_utils import sanitize_filename  # Import the sanitize function

# Logger konfigurieren
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levellevel)s - %(message)s')
logger = logging.getLogger(__name__)

def run_screenshot_script(url, screenshot_path):
    """
    Run the screenshot script using Node.js and Puppeteer.

    Args:
        url (str): The URL of the website to capture.
        screenshot_path (str): The path to save the screenshot.

    Returns:
        tuple: A tuple containing success status (bool) and message (str).
    """
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

def scrape_and_screenshot(url, output_path):
    """
    Scrape the website and save its main screenshot.

    Args:
        url (str): The URL of the website to scrape.
        output_path (str): The path to save the screenshot.

    Returns:
        dict: A dictionary containing the screenshot path or an error message.
    """
    logger.debug(f"Starting to scrape and screenshot website: {url}")
    sanitized_url = sanitize_filename(url)  # Sanitize URL for filename
    screenshot_path = os.path.join(output_path, f'{sanitized_url}.png')

    success, message = run_screenshot_script(url, screenshot_path)
    if not success:
        logger.error(f"Failed to create screenshot for {url}: {message}")
        return {'error': message}

    return {'screenshot': screenshot_path}

def scrape_multiple_websites(urls, base_folder):
    """
    Scrape multiple websites and save their screenshots.

    Args:
        urls (list): A list of URLs to scrape.
        base_folder (str): The base folder to save the screenshots.

    Returns:
        list: A list of dictionaries containing the scraped content and screenshots.
    """
    logger.debug(f"Starting to scrape multiple websites: {urls}")
    all_contents = []
    subpages_folder = os.path.join(base_folder, 'subpages')
    create_directory(subpages_folder)  # Create subpages directory

    with ThreadPoolExecutor(max_workers=4) as executor:  # Adjust max_workers as needed
        future_to_url = {executor.submit(scrape_and_screenshot, url, subpages_folder): url for url in urls}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                screenshot_result = future.result()
                if 'error' in screenshot_result:
                    logger.warning(f"Skipping screenshot for {url} due to error: {screenshot_result['error']}")
                    continue
                all_contents.append({'url': url, 'screenshot': screenshot_result['screenshot']})
            except Exception as e:
                logger.error(f"Error scraping {url}: {e}")

    logger.info(f"Scraped content from {len(all_contents)} out of {len(urls)} websites")
    return all_contents

def run_package_creator(base_url, urls, output_zip_path):
    """
    Main function to scrape, screenshot and create a zip package.

    Args:
        base_url (str): The base URL for the main website.
        urls (list): A list of URLs to scrape.
        output_zip_path (str): The path to save the output zip file.

    Returns:
        str: The path to the created zip file.
    """
    sanitized_base_url = sanitize_filename(base_url)  # Sanitize base URL for folder name
    base_folder = os.path.join('outputs', sanitized_base_url)
    create_directory(base_folder)

    # Scrape and screenshot main website
    scrape_and_screenshot(base_url, base_folder)

    # Scrape and screenshot sub-websites
    scrape_multiple_websites(urls, base_folder)

    # Create zip file
    create_zip_file(base_folder, output_zip_path)

    logger.info(f"Package created at {output_zip_path}")
    return output_zip_path
