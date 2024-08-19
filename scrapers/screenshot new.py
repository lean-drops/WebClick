import asyncio
from playwright.async_api import async_playwright
import os
import random
import json
import logging
import zipfile
from datetime import datetime
import greenlet
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

# Load cookie selectors from a JSON file
COOKIES_SELECTOR_PATH = r"C:\Users\BZZ1391\Bingo\WebClick\app\static\js\cookies_selector.json"


def load_cookie_selectors(file_path):
    """Load the cookie selectors from the JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            selectors = json.load(f)
            logger.info(f"Loaded {len(selectors)} cookie selectors from {file_path}")
            return selectors
    except Exception as e:
        logger.error(f"Error loading cookie selectors from {file_path}: {e}")
        return []


async def reject_cookies(page, selectors):
    """Automatically reject cookies using selectors loaded from a JSON file."""
    for selector in selectors:
        try:
            await page.wait_for_selector(selector['selector'], timeout=5000)
            await page.click(selector['selector'])
            logger.info(f"Cookies rejected using selector: {selector['selector']}")
            break
        except Exception as e:
            logger.warning(f"Could not interact with selector {selector['selector']}: {e}")


async def capture_screenshot(url, output_path, selectors):
    """Captures a full-page screenshot."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1920, "height": 1080})

        try:
            await page.goto(url, wait_until='networkidle')
            await reject_cookies(page, selectors)
            await page.screenshot(path=output_path, full_page=True)
            logger.info(f"Screenshot saved at {output_path}")
        except Exception as e:
            logger.error(f"Error during screenshot process for URL {url}: {e}")
        finally:
            await browser.close()


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
    # Load cookie selectors
    cookie_selectors = load_cookie_selectors(COOKIES_SELECTOR_PATH)

    # Select random Swiss government URLs
    random_gov_urls = select_random_gov_urls()

    test_urls = [
                    "https://www.zh.ch/de/direktion-der-justiz-und-des-innern/justizvollzug-wiedereingliederung/untersuchungsgefaengnisse-zuerich/gefaengnis-zuerich.html",
                    "https://www.wikipedia.org"
                ] + random_gov_urls

    # Create output directory
    run_number = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(os.getcwd(), f'screenshots_run_{run_number}')
    os.makedirs(output_dir, exist_ok=True)

    # Capture screenshots
    for url in test_urls:
        sanitized_name = url.replace('https://', '').replace('/', '_')
        output_path = os.path.join(output_dir, f"{sanitized_name}.png")
        await capture_screenshot(url, output_path, cookie_selectors)

    # Create ZIP file of screenshots
    zip_filename = f"screenshots_run_{run_number}.zip"
    zip_filepath = os.path.join(os.getcwd(), zip_filename)

    with zipfile.ZipFile(zip_filepath, 'w') as zipf:
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, output_dir))

    logger.info(f"All screenshots have been taken and zipped into {zip_filepath}")


# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
