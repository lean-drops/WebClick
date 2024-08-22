import ssl
import aiohttp
import aiofiles
import asyncio
import warcio
from warcio.warcwriter import WARCWriter
from warcio.statusandheaders import StatusAndHeaders
import io
import os
from urllib.parse import urlparse
from datetime import datetime
import json
import random

# Deactivate SSL warnings for unverified HTTPS requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
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

url_list = [
    "https://www.ag.ch",  # Aargau
    "https://www.ai.ch",  # Appenzell Innerrhoden
    "https://www.ar.ch",  # Appenzell Ausserrhoden
    "https://www.be.ch",  # Bern
    "https://www.bl.ch",  # Basel-Landschaft
    "https://www.bs.ch",  # Basel-Stadt
    "https://www.fr.ch",  # Freiburg
    "https://www.ge.ch",  # Genf
    "https://www.gl.ch",  # Glarus
    "https://www.gr.ch",  # Graubünden
    "https://www.ju.ch",  # Jura
    "https://www.lu.ch",  # Luzern
    "https://www.ne.ch",  # Neuenburg
    "https://www.nw.ch",  # Nidwalden
    "https://www.ow.ch",  # Obwalden
    "https://www.sg.ch",  # St. Gallen
    "https://www.sh.ch",  # Schaffhausen
    "https://www.so.ch",  # Solothurn
    "https://www.sz.ch",  # Schwyz
    "https://www.ti.ch",  # Tessin
    "https://www.tg.ch",  # Thurgau
    "https://www.ur.ch",  # Uri
    "https://www.vd.ch",  # Waadt
    "https://www.vs.ch",  # Wallis
    "https://www.zh.ch",  # Zürich
    "https://www.zg.ch",  # Zug
    "https://www.admin.ch"  # Bund (Schweizer Regierung)
]


# Randomly choose a URL from the list
url = random.choice(url_list)

async def fetch_and_save_warc(url, warc_file):
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    chrome_driver_path = r"C:\Google Neu\chromedriver-win32\chromedriver.exe"  # Update with your actual path
    chrome_binary_path = r"C:\Google Neu\chrome-win32\chrome.exe"  # Update with your actual path

    # Use Selenium to load the page and get all resources
    driver = setup_webdriver(chrome_driver_path, chrome_binary_path)

    # Move window off-screen
    driver.set_window_position(-2000, 0)  # Position the window outside the visible area

    logs = fetch_resources(driver, url)

    # Initialize counters for the summary
    total_resources = 0
    total_size = 0

    # Parse and fetch each resource found in the network logs asynchronously
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
        with io.BytesIO() as stream:
            writer = WARCWriter(stream, gzip=True)

            tasks = []
            for log in logs:
                log_data = json.loads(log)
                if 'message' in log_data and 'params' in log_data['message']:
                    params = log_data['message']['params']
                    if 'request' in params and 'url' in params['request']:
                        resource_url = params['request']['url']
                        tasks.append(fetch_and_write_resource(session, resource_url, writer))

            # Run all fetch tasks concurrently
            results = await asyncio.gather(*tasks)

            # Update counters based on results
            for res_size in results:
                if res_size:
                    total_resources += 1
                    total_size += res_size

            # Write all collected WARC data to file
            warc_data = stream.getvalue()
            async with aiofiles.open(warc_file, 'wb') as f:
                await f.write(warc_data)

        # Display a summary of the download process
        display_summary(warc_file, total_resources, total_size)


async def fetch_and_write_resource(session, url, writer, retries=3):
    try:
        async with session.get(url) as response:
            content = await response.read()
            content_type = response.headers.get('Content-Type', '').lower()

            # Prüfen, ob die Ressource HTML ist
            if 'text/html' in content_type:
                print(f"HTML content found at {url}")
            else:
                print(f"Non-HTML content found at {url}: {content_type}")

            headers = StatusAndHeaders('200 OK', response.headers.items(), protocol='HTTP/1.1')
            record = writer.create_warc_record(url, 'response', payload=io.BytesIO(content), http_headers=headers)
            writer.write_record(record)
            return len(content)  # Return size of the resource for summary
    except Exception as e:
        if retries > 0:
            print(f"Retrying {url} due to error: {e}. Attempts left: {retries}")
            return await fetch_and_write_resource(session, url, writer, retries - 1)
        else:
            print(f"Skipping resource {url} due to repeated errors: {e}")
            return None

def display_summary(warc_file, total_resources, total_size):
    print("\n=== Download Summary ===")
    print(f"WARC file saved to: {warc_file}")
    print(f"Total resources downloaded: {total_resources}")
    print(f"Total size of resources: {total_size / 1024:.2f} KB")
    print("========================\n")


def generate_filenames(url):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.replace('.', '_')
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    warc_filename = f"{domain}_{timestamp}.warc.gz"

    # Ensure the directory exists
    warc_dir = os.path.join("scrapers", "archives")
    os.makedirs(warc_dir, exist_ok=True)

    return os.path.join(warc_dir, warc_filename)


def main():
    warc_file = generate_filenames(url)
    print(f"Starting download of {url}")
    print(f"WARC file will be saved to {warc_file}")

    asyncio.run(fetch_and_save_warc(url, warc_file))

    print("Download completed!")


if __name__ == "__main__":
    main()
