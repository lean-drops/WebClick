import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from PIL import Image
from urllib.parse import urlparse
from urllib.request import urlretrieve

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("screenshot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_cookie_selectors(file_path='app/static/js/cookies_selector.json'):
    try:
        import json
        with open(file_path, 'r') as file:
            selectors = json.load(file)
            logger.debug(f"Loaded {len(selectors)} cookie selectors")
            return selectors
    except Exception as e:
        logger.error(f"Error loading cookie selectors: {e}")
        return []


def auto_reject_cookies(driver, selectors):
    for selector in selectors:
        try:
            elements = driver.find_elements_by_css_selector(selector)
            for element in elements:
                if element.is_displayed():
                    element.click()
                    logger.info(f"Clicked cookie reject button with selector: {selector}")
                    time.sleep(1)  # Wait for any UI changes to take effect
                    break
        except Exception as e:
            logger.debug(f"Could not click selector {selector}: {e}")


def take_full_page_screenshot(driver, output_path):
    """Takes a screenshot of the entire page."""
    logger.info("Calculating total page height for full-page screenshot...")
    total_height = driver.execute_script("return document.body.scrollHeight")
    driver.set_window_size(1920, total_height)
    time.sleep(2)  # Wait for resizing

    # Save the screenshot
    driver.save_screenshot(output_path)
    logger.info(f"Full-page screenshot saved at {output_path}")


def save_background_images(driver, output_dir):
    """Find and save all background images on the page."""
    logger.info("Collecting background images...")
    background_images = set()
    elements = driver.find_elements_by_xpath('//*[@style]')

    for element in elements:
        style = element.get_attribute('style')
        if 'background-image' in style:
            url = style.split('url("')[1].split('")')[0]
            if url not in background_images:
                background_images.add(url)

    for idx, img_url in enumerate(background_images):
        try:
            parsed_url = urlparse(img_url)
            img_name = os.path.basename(parsed_url.path)
            img_path = os.path.join(output_dir, f"background_{idx}_{img_name}")
            urlretrieve(img_url, img_path)
            logger.info(f"Saved background image {img_url} to {img_path}")
        except Exception as e:
            logger.error(f"Error saving background image {img_url}: {e}")


def take_screenshot(url, output_path, countdown_seconds=0,
                    driver_path=r"C:\Driver\chromedriver-win32\chromedriver.exe"):
    """
    Take a screenshot of a webpage using Selenium.

    Args:
        url (str): The URL of the webpage.
        output_path (str): Path to save the screenshot.
        countdown_seconds (int): Countdown before taking a screenshot.
        driver_path (str): Path to the chromedriver executable.
    """
    logger.info(f"Starting screenshot process for URL: {url}")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920x1080")

    # Set the binary location for Chrome Dev
    chrome_options.binary_location = r"C:\Program Files\Google\Chrome Dev\Application\chrome.exe"

    service = ChromeService(driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get(url)
        logger.debug(f"Page loaded: {url}")

        cookie_selectors = load_cookie_selectors()
        auto_reject_cookies(driver, cookie_selectors)

        other_banner_selectors = [
            '#age-gate', '.rating-popup', '.ad-banner', '.newsletter-popup', '.modal-overlay',
            '.subscription-banner', '#age-verification', '.survey-popup', '.feedback-popup',
            '.welcome-screen', '.promo-banner', '.gdpr-banner', '.cc-window', '.cookie-consent-banner',
            '.interstitial'
        ]

        for selector in other_banner_selectors:
            try:
                elements = driver.find_elements_by_css_selector(selector)
                for element in elements:
                    driver.execute_script("arguments[0].remove();", element)
                    logger.info(f"Removed element with selector: {selector}")
            except Exception as e:
                logger.debug(f"Could not remove element with selector {selector}: {e}")

        # Countdown before screenshot
        logger.info(f"Countdown started: {countdown_seconds} seconds")
        for i in range(countdown_seconds, 0, -1):
            logger.info(f"Countdown: {i} seconds")
            time.sleep(1)

        # Take the full-page screenshot
        take_full_page_screenshot(driver, output_path)

        # Save background images
        background_dir = os.path.join(os.path.dirname(output_path), "hintergrundbilder")
        os.makedirs(background_dir, exist_ok=True)
        save_background_images(driver, background_dir)

    except Exception as e:
        logger.error(f"Error taking screenshot of {url}: {e}")
    finally:
        driver.quit()
        logger.debug("Driver closed")


if __name__ == "__main__":
    # Example usage
    test_url = "https://schlosskyburg.ch/"
    output_dir = "outputs/schlosskyburgch"
    os.makedirs(output_dir, exist_ok=True)
    take_screenshot(test_url, os.path.join(output_dir, "screenshot.png"), countdown_seconds=3)
