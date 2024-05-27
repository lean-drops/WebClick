import subprocess
import logging
import os

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
        # Ensure the directory exists
        os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)

        result = subprocess.run(['node', 'app/static/js/screenshot.js', url, screenshot_path], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Failed to create screenshot for {url}: {result.stderr}")
            return False, f"Failed to create screenshot for {url}: {result.stderr}"
        logger.info(f"Screenshot saved at {screenshot_path}")
        return True, ""
    except Exception as e:
        logger.error(f"Error running screenshot script for {url}: {e}")
        return False, f"Error running screenshot script for {url}: {e}"
