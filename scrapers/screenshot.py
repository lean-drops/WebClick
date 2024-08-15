import os
import time
import logging
import json
from urllib.parse import urlparse
import requests
from requests.exceptions import RequestException
import tkinter as tk
from tkinter import messagebox
from ttkbootstrap import Style
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException

# Logging configuration
logging.basicConfig(
    level=logging.INFO,  # Set to INFO to reduce verbosity
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("screenshot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def normalize_url(url):
    """Normalize the URL to ensure it includes the protocol."""
    parsed_url = urlparse(url)
    if not parsed_url.scheme:
        url = 'https://' + url  # Default to https if no scheme is provided
    return url

def is_valid_url(url):
    """Check if the URL is reachable."""
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return True
    except RequestException as e:
        logger.error(f"URL validation failed: {e}")
        return False

def load_cookie_selectors(file_path='cookie_selectors.json'):
    """Load cookie selectors from a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        logger.error(f"Error loading cookie selectors: {e}")
        return []

def auto_reject_cookies(driver, selectors):
    """
    Automatically click on cookie rejection buttons if found.
    Tries multiple strategies to reject non-essential cookies.
    """
    for selector_info in selectors:
        try:
            selector_type = selector_info.get('type', 'css')
            selector_value = selector_info['selector']
            if selector_type == 'css':
                elements = driver.find_elements("css selector", selector_value)
            elif selector_type == 'xpath':
                elements = driver.find_elements("xpath", selector_value)
            else:
                continue  # Unsupported selector type

            for element in elements:
                if element.is_displayed():
                    driver.execute_script("arguments[0].click();", element)
                    logger.info(f"Clicked cookie reject button: {selector_value}")
                    time.sleep(1)  # Wait a moment after clicking
                    return  # Exit after successful click
        except (NoSuchElementException, ElementClickInterceptedException) as e:
            logger.debug(f"Cookie reject button not found or not clickable: {e}")
        except Exception as e:
            logger.error(f"Error during cookie rejection: {e}")

def remove_unwanted_elements(driver, selectors):
    """Remove unwanted elements like ads, banners, popups from the page."""
    for selector in selectors:
        try:
            elements = driver.find_elements("css selector", selector)
            for element in elements:
                driver.execute_script("arguments[0].remove();", element)
                logger.info(f"Removed unwanted element: {selector}")
        except Exception as e:
            logger.debug(f"Failed to remove element with selector {selector}: {e}")

def take_screenshot(url, output_path, countdown_seconds=0, driver_path=r"C:\Driver\chromedriver-win32\chromedriver.exe"):
    """
    Take a screenshot of a webpage using Selenium.

    Args:
        url (str): The URL of the webpage.
        output_path (str): Path to save the screenshot.
        countdown_seconds (int): Countdown before taking a screenshot.
        driver_path (str): Path to the chromedriver executable.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Runs Chrome in headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--disable-gpu")  # Disable GPU hardware acceleration
    chrome_options.add_argument("--disable-extensions")  # Disable extensions
    chrome_options.add_argument("--disable-popup-blocking")  # Disable popups
    chrome_options.add_argument("--disable-plugins-discovery")  # Disable plugins discovery
    chrome_options.binary_location = r"C:\Program Files\Google\Chrome Dev\Application\chrome.exe"

    # Integrate "I don't care about cookies" extension
    idc_extension_path = r"C:\Path\to\idoncareaboutcookies.crx"  # Update this path
    if os.path.exists(idc_extension_path):
        chrome_options.add_extension(idc_extension_path)
    else:
        logger.warning("I don't care about cookies extension not found. Proceeding without it.")

    service = ChromeService(driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get(url)
        time.sleep(2)  # Wait for the page to load

        # Load and apply cookie rejection
        cookie_selectors = load_cookie_selectors()
        auto_reject_cookies(driver, cookie_selectors)

        # Remove unwanted elements
        unwanted_selectors = [
            '#age-gate', '.rating-popup', '.ad-banner', '.newsletter-popup', '.modal-overlay',
            '.subscription-banner', '#age-verification', '.survey-popup', '.feedback-popup',
            '.welcome-screen', '.promo-banner', '.gdpr-banner', '.cc-window', '.cookie-consent-banner',
            '.interstitial'
        ]
        remove_unwanted_elements(driver, unwanted_selectors)

        if countdown_seconds > 0:
            time.sleep(countdown_seconds)

        # Full-page screenshot
        total_height = driver.execute_script("return document.body.scrollHeight")
        driver.set_window_size(1920, total_height)
        time.sleep(1)  # Shortened sleep time for faster execution
        driver.save_screenshot(output_path)
        logger.info(f"Screenshot saved at {output_path}")

    except Exception as e:
        logger.error(f"Error processing {url}: {e}")
        messagebox.showerror("Error", f"An error occurred: {e}")
    finally:
        driver.quit()

def start_screenshot_process():
    url = entry_url.get().strip()
    if not url:
        messagebox.showerror("Input Error", "Please enter a valid URL.")
        return

    normalized_url = normalize_url(url)

    if not is_valid_url(normalized_url):
        messagebox.showerror("Invalid URL", "The URL provided cannot be reached. Please check and try again.")
        return

    output_dir = os.path.join(os.getcwd(), 'screenshots')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "screenshot.png")

    take_screenshot(normalized_url, output_path, countdown_seconds=2)
    messagebox.showinfo("Success", f"Screenshot saved to {output_path}")

if __name__ == "__main__":
    # Set up the GUI
    style = Style(theme='superhero')  # ttkbootstrap theme
    root = style.master
    root.title("Website Screenshot Tool")
    root.geometry("400x200")

    # URL Entry
    lbl_url = tk.Label(root, text="Enter URL:")
    lbl_url.pack(pady=10)

    entry_url = tk.Entry(root, width=50)
    entry_url.pack(pady=10)

    # Start Button
    btn_start = tk.Button(root, text="Take Screenshot", command=start_screenshot_process, width=25)
    btn_start.pack(pady=20)

    root.mainloop()
