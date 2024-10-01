import asyncio
import subprocess
import logging
import os

from app.create_package.create_directory import create_directory
from app.create_package.create_zipfile import create_zip_file
from app.utils.naming_utils import sanitize_filename, logger  # Import the sanitize function



async def run_screenshot_script(url, screenshot_path, countdown_seconds=0):
    """
    Run the screenshot script using Node.js and Puppeteer.

    Args:
        url (str): The URL of the website to capture.
        screenshot_path (str): The path to save the screenshot.
        countdown_seconds (int): Countdown seconds before starting the process.

    Returns:
        tuple: A tuple containing success status (bool) and message (str).
    """
    logger.info(f"Starting screenshot script for {url} with countdown {countdown_seconds} seconds...")
    if countdown_seconds > 0:
        for i in range(countdown_seconds, 0, -1):
            logger.info(f"Countdown: {i} Sekunden")
            await asyncio.sleep(1)

    try:
        process = await asyncio.create_subprocess_exec(
            'node', 'app/static/js/screenshot.js', url, screenshot_path, str(countdown_seconds),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        logger.info(f"Output from script: {stdout.decode()}")
        if process.returncode != 0:
            logger.error(f"Failed to create screenshot for {url}: {stderr.decode()}")
            return False, f"Failed to create screenshot for {url}: {stderr.decode()}"
        logger.info(f"Screenshot saved at {screenshot_path}")
        return True, ""
    except Exception as e:
        logger.error(f"Error running screenshot script for {url}: {e}")
        return False, f"Error running screenshot script for {url}: {e}"

async def scrape_and_screenshot(url, output_path, countdown_seconds=0):
    """
    Scrape the website and save its main screenshot.

    Args:
        url (str): The URL of the website to scrape.
        output_path (str): The path to save the screenshot.
        countdown_seconds (int): Countdown seconds before starting the process.

    Returns:
        dict: A dictionary containing the screenshot path or an error message.
    """
    logger.debug(f"Starting to scrape and screenshot website: {url}")
    sanitized_url = sanitize_filename(url)  # Sanitize URL for filename
    screenshot_path = os.path.join(output_path, f'{sanitized_url}.png')

    logger.info(f"Scraping and taking screenshot of {url}")
    success, message = await run_screenshot_script(url, screenshot_path, countdown_seconds)
    if not success:
        logger.error(f"Failed to create screenshot for {url}: {message}")
        return {'error': message}

    logger.info(f"Screenshot for {url} saved successfully.")
    return {'screenshot': screenshot_path}

async def scrape_multiple_websites(urls, base_folder, countdown_seconds=0):
    """
    Scrape multiple websites and save their screenshots.

    Args:
        urls (list): A list of URLs to scrape.
        base_folder (str): The base folder to save the screenshots.
        countdown_seconds (int): Countdown seconds before starting the process.

    Returns:
        list: A list of dictionaries containing the scraped content and screenshots.
    """
    logger.debug(f"Starting to scrape multiple websites: {urls}")

    all_contents = []
    subpages_folder = os.path.join(base_folder, 'subpages')
    create_directory(subpages_folder)  # Create subpages directory

    tasks = [scrape_and_screenshot(url, subpages_folder, countdown_seconds) for url in urls]
    for future in asyncio.as_completed(tasks):
        screenshot_result = await future
        url = urls[tasks.index(future)]
        if 'error' in screenshot_result:
            logger.warning(f"Skipping screenshot for {url} due to error: {screenshot_result['error']}")
            continue
        all_contents.append({'url': url, 'screenshot': screenshot_result['screenshot']})

    logger.info(f"Scraped content from {len(all_contents)} out of {len(urls)} websites")
    return all_contents

async def run_package_creator(base_url, urls, output_zip_path, countdown_seconds=0):
    """
    Main function to scrape, screenshot and create a zip package.

    Args:
        base_url (str): The base URL for the main website.
        urls (list): A list of URLs to scrape.
        output_zip_path (str): The path to save the output zip file.
        countdown_seconds (int): Countdown seconds before starting the process.

    Returns:
        str: The path to the created zip file.
    """
    logger.info(f"Starting package creation for {base_url} with countdown {countdown_seconds} seconds.")
    sanitized_base_url = sanitize_filename(base_url)  # Sanitize base URL for folder name
    base_folder = os.path.join('outputs_directory', sanitized_base_url)
    create_directory(base_folder)

    # Scrape and screenshot main website
    await scrape_and_screenshot(base_url, base_folder, countdown_seconds)

    # Scrape and screenshot sub-websites
    await scrape_multiple_websites(urls, base_folder, countdown_seconds)

    # Create zip file
    create_zip_file(base_folder, output_zip_path)

    logger.info(f"Package created at {output_zip_path}")
    return output_zip_path


