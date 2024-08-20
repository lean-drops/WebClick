import os
import json
import logging
import asyncio
import zipfile
import psutil
import random
from urllib.parse import urlparse
from PIL import Image
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException, WebDriverException
from datetime import datetime
from utils.naming_utils import sanitize_filename, shorten_url
import requests
from requests.exceptions import RequestException
from concurrent.futures import ThreadPoolExecutor

# Pfad zur cookies_selector.json
COOKIES_SELECTOR_PATH = r"/app/static/js/cookies_selector.json"

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("screenshot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_cookie_selectors(file_path):
    """Lädt die Cookie-Selektoren aus der JSON-Datei."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            selectors = json.load(f)
            logger.info(f"Loaded {len(selectors)} cookie selectors from {file_path}")
            return selectors
    except Exception as e:
        logger.error(f"Error loading cookie selectors from {file_path}: {e}")
        return []


def normalize_url(url):
    """Normalize the URL to ensure it includes the protocol."""
    parsed_url = urlparse(url)
    if not parsed_url.scheme:
        url = 'https://' + url
    return url


def is_valid_url(url):
    """Check if the URL is reachable with SSL verification disabled."""
    try:
        response = requests.get(url, timeout=5, verify=False)
        response.raise_for_status()
        return True
    except RequestException as e:
        logger.error(f"URL validation failed: {e}")
        return False


def handle_cookies(driver, selectors):
    """Automatically reject cookies using selectors loaded from a JSON file."""
    for selector in selectors:
        try:
            if selector["type"] == "css":
                button = driver.find_element(By.CSS_SELECTOR, selector["selector"])
            elif selector["type"] == "xpath":
                button = driver.find_element(By.XPATH, selector["selector"])

            if button:
                button.click()
                logger.info(f"Cookies rejected using selector: {selector['selector']}")
                break
        except (NoSuchElementException, ElementNotInteractableException) as ex:
            logger.debug(f"Selector {selector['selector']} not found or not interactable: {ex}")
            continue
        except WebDriverException as ex:
            logger.error(f"WebDriver exception: {ex}")
            break


def optimize_media_display(driver):
    """Optimize the display of images and videos for the screenshot."""
    try:
        driver.execute_script("""
            let images = document.querySelectorAll('img');
            for (let img of images) {
                img.style.maxWidth = '100%';
                img.style.height = 'auto';
                img.style.objectFit = 'contain';
            }

            let videos = document.querySelectorAll('video');
            for (let video of videos) {
                video.style.maxWidth = '100%';
                video.style.height = 'auto';
                video.style.objectFit = 'contain';
                video.controls = false;
            }
        """)
        logger.info("Media elements optimized for display.")
    except WebDriverException as e:
        logger.error(f"Error optimizing media display: {e}")


def wait_for_page_load(driver):
    """Wait until the page has completely loaded."""
    try:
        page_state = driver.execute_script('return document.readyState;')
        while page_state != 'complete':
            page_state = driver.execute_script('return document.readyState;')
        logger.info("Page fully loaded.")
    except WebDriverException as e:
        logger.error(f"Error waiting for page to load: {e}")


def take_full_page_screenshot(driver, output_path):
    """Takes a full-page screenshot by setting the window size to the page's total height."""
    try:
        total_width = driver.execute_script("return document.body.scrollWidth")
        total_height = driver.execute_script("return document.body.scrollHeight")

        # Set window size to capture full page in one screenshot
        driver.set_window_size(total_width, total_height)
        driver.execute_script("window.scrollTo(0, 0);")  # Scroll to the top of the page
        wait_for_page_load(driver)  # Ensure the page is fully loaded

        driver.save_screenshot(output_path)
        logger.info(f"Full page screenshot saved at {output_path}")
    except Exception as e:
        logger.error(f"Error taking full page screenshot: {e}")


def sync_take_screenshot(url, output_path, selectors, driver_path, chrome_binary_path):
    chrome_options = Options()
    chrome_options.binary_location = chrome_binary_path
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--window-position=-10000,-10000")  # Fenster unsichtbar machen

    service = ChromeService(executable_path=os.path.join(driver_path, "chromedriver.exe"))

    logger.info(f"Using ChromeDriver path: {driver_path}")
    logger.info(f"Using Chrome binary path: {chrome_binary_path}")

    with webdriver.Chrome(service=service, options=chrome_options) as driver:
        try:
            driver.get(url)
            handle_cookies(driver, selectors)
            optimize_media_display(driver)
            take_full_page_screenshot(driver, output_path)
        except Exception as e:
            logger.error(f"Error during screenshot process for URL {url}: {e}")


async def take_screenshot_sequentially(url, output_path, selectors, driver_path, chrome_binary_path):
    """Takes screenshots sequentially without overlapping."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, sync_take_screenshot, url, output_path, selectors, driver_path, chrome_binary_path)
    await adjust_pause_based_on_system_load()


async def start_screenshot_process_sequentially(urls, base_folder, selectors, driver_paths, chrome_binary_paths):
    """Process a list of URLs and take screenshots sequentially, storing them in the specified folder."""
    tasks = []
    for i, url in enumerate(urls):
        if is_valid_url(url):
            sanitized_name = sanitize_filename(shorten_url(url))
            output_path = os.path.join(base_folder, f"{sanitized_name}.png")
            driver_path = driver_paths[i % len(driver_paths)]
            chrome_binary_path = chrome_binary_paths[i % len(chrome_binary_paths)]
            tasks.append(take_screenshot_sequentially(url, output_path, selectors, driver_path, chrome_binary_path))
        else:
            logger.warning(f"Invalid URL skipped: {url}")

    await asyncio.gather(*tasks)
    logger.info("All screenshots have been taken.")


async def adjust_pause_based_on_system_load():
    """Dynamically adjust the pause based on current system load."""
    cpu_usage = psutil.cpu_percent(interval=1)
    memory_usage = psutil.virtual_memory().percent

    if cpu_usage > 80 or memory_usage > 80:
        pause_duration = 10
    elif cpu_usage > 50 or memory_usage > 50:
        pause_duration = 1.5
    else:
        pause_duration = 1

    logger.info(f"System load: CPU={cpu_usage}%, Memory={memory_usage}%. Pausing for {pause_duration} seconds.")
    await asyncio.sleep(pause_duration)


def select_random_gov_urls():
    """Select 2-3 random Swiss government URLs."""
    swiss_gov_urls = [
        "https://www.admin.ch/",
        "https://www.eda.admin.ch/",
        "https://www.efv.admin.ch/",
        "https://www.bag.admin.ch/",
        "https://www.zh.ch/",
        "https://www.be.ch/",
        "https://www.baselland.ch/",
        "https://www.lu.ch/",
        "https://www.ti.ch/",
        "https://www.ag.ch/"
    ]
    return random.sample(swiss_gov_urls, random.randint(2, 3))


async def main():
    # Zufällige Auswahl von Schweizer Verwaltungswebseiten
    random_gov_urls = select_random_gov_urls()

    test_urls = [
                    "https://www.zh.ch/de/direktion-der-justiz-und-des-innern/justizvollzug-wiedereingliederung/untersuchungsgefaengnisse-zuerich/gefaengnis-zuerich.html",
                    "https://www.wikipedia.org"
                ] + random_gov_urls

    run_number = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(os.getcwd(), f'screenshots_run_{run_number}')
    os.makedirs(output_dir, exist_ok=True)

    cookie_selectors = load_cookie_selectors(COOKIES_SELECTOR_PATH)

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

    await start_screenshot_process_sequentially(test_urls, output_dir, cookie_selectors, driver_paths,
                                                chrome_binary_paths)

    zip_filename = f"screenshots_run_{run_number}.zip"
    zip_filepath = os.path.join(os.getcwd(), zip_filename)

    with zipfile.ZipFile(zip_filepath, 'w') as zipf:
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, output_dir))

    logger.info(f"All screenshots have been taken and zipped into {zip_filepath}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
