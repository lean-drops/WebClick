import os
import re
import requests
import zipfile
import subprocess
import winreg

def get_chrome_version():
    """
    Retrieves the version of the installed Chrome browser from the Windows registry.
    """
    try:
        key_path = r"SOFTWARE\Google\Chrome\BLBeacon"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path)
        version, _ = winreg.QueryValueEx(key, "version")
        winreg.CloseKey(key)
        return version
    except Exception as e:
        print(f"Error retrieving Chrome version from registry: {e}")
    return None

def download_chromedriver(version, download_path):
    """
    Downloads the ChromeDriver for the specified version.
    """
    major_version = version.split('.')[0]
    url = f"https://chromedriver.storage.googleapis.com/LATEST_RELEASE_{major_version}"
    response = requests.get(url)
    if response.status_code == 200:
        driver_version = response.text.strip()
        download_url = f"https://chromedriver.storage.googleapis.com/{driver_version}/chromedriver_win32.zip"
        zip_path = os.path.join(download_path, 'chromedriver.zip')

        # Download and extract ChromeDriver
        print(f"Downloading ChromeDriver version {driver_version}...")
        with open(zip_path, 'wb') as file:
            file.write(requests.get(download_url).content)

        # Extract the downloaded file
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(download_path)

        print(f"ChromeDriver downloaded and extracted to {download_path}")
        os.remove(zip_path)  # Clean up zip file
    else:
        print("Failed to get the ChromeDriver version from the internet.")

def ensure_chromedriver_path(driver_path='C:\\Driver'):
    """
    Ensures that the ChromeDriver is installed at the specified path.
    """
    if not os.path.exists(driver_path):
        os.makedirs(driver_path)

    chrome_version = get_chrome_version()
    if chrome_version is None:
        print("Could not find Chrome installation.")
        return

    print(f"Detected Chrome version: {chrome_version}")
    chromedriver_path = os.path.join(driver_path, 'chromedriver.exe')

    if os.path.exists(chromedriver_path):
        print("ChromeDriver already exists.")
    else:
        download_chromedriver(chrome_version, driver_path)

if __name__ == "__main__":
    ensure_chromedriver_path()
