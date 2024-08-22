import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def setup_webdriver(chrome_driver_path, chrome_binary_path):
    options = Options()
    options.binary_location = chrome_binary_path
    # Entferne die nächste Zeile, wenn du das Fenster sichtbar haben möchtest
    options.add_argument('--headless')  # Run in headless mode (without a GUI)
    options.add_argument('--disable-gpu')  # Disable GPU acceleration
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')  # Ensure all elements load correctly
    options.add_argument('--remote-debugging-port=9222')  # Optional: Debugging port for headless check

    # Positioniere das Fenster außerhalb des sichtbaren Bildschirms
    options.add_argument('--window-position=-100000,-100000')  # Move window far out of the visible screen area

    # Enable capturing of network requests
    caps = DesiredCapabilities.CHROME
    caps['goog:loggingPrefs'] = {'performance': 'ALL'}

    # Integrate the capabilities into options
    options.set_capability('goog:loggingPrefs', caps['goog:loggingPrefs'])

    service = Service(executable_path=chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=options)

    return driver


def load_full_page(driver, url, timeout=30):
    driver.get(url)

    # Wait until the page is fully loaded by checking for a specific element
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(('tag name', 'body'))
        )
    except Exception as e:
        print(f"Timeout or error while loading page: {e}")

    # Additional wait to ensure all resources are loaded
    time.sleep(5)

    # Capture all network requests made by the browser
    logs = get_network_logs(driver)
    return logs


def get_network_logs(driver):
    # Get browser logs from the performance log
    logs = driver.get_log('performance')
    return [log['message'] for log in logs]


def fetch_resources(driver, url):
    logs = load_full_page(driver, url)
    driver.quit()
    return logs
