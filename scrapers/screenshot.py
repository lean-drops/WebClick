import subprocess
import logging

# Logger konfigurieren
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
        result = subprocess.run(['node', 'screenshot.js', url, screenshot_path], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Failed to create screenshot for {url}: {result.stderr}")
            return False, f"Failed to create screenshot for {url}: {result.stderr}"
        logger.info(f"Screenshot saved at {screenshot_path}")
        return True, ""
    except Exception as e:
        logger.error(f"Error running screenshot script for {url}: {e}")
        return False, f"Error running screenshot script for {url}: {e}"

# Beispiel für die Ausführung des Skripts
if __name__ == "__main__":
    url = "https://example.com"
    screenshot_path = "example.png"
    success, message = run_screenshot_script(url, screenshot_path)
    if not success:
        print("Fehler:", message)
    else:
        print("Screenshot erfolgreich erstellt.")
