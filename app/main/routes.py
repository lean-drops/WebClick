from quart import Blueprint, request, jsonify, render_template, send_file
from scrapers.create_directory import create_directory, shorten_url
from scrapers.fetch_content import scrape_website
from scrapers.screenshot import take_screenshot
from scrapers.scraper import run_package_creator
import os
import logging

# Configure logger
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/application.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Define Blueprint
main = Blueprint('main', __name__)


@main.route('/')
async def index():
    """
    Renders the homepage of the application.
    """
    logger.debug("Rendering the homepage")
    return await render_template('index.html')


@main.route('/scrape', methods=['POST'])
async def scrape():
    """
    API endpoint to scrape a single webpage.

    Expects JSON:
        {
            "url": "<URL>"
        }

    Returns:
        JSON response with the content of the website or an error message.
    """
    data = await request.json
    url = data.get('url')
    logger.debug(f"Scrape request received for URL: {url}")
    if not url:
        logger.warning("No URL provided in the request")
        return jsonify({"error": "No URL provided"}), 400

    try:
        content = await scrape_website(url)
        logger.info(f"Scraping successful for URL: {url}")
        if 'error' in content:
            return jsonify(content), 500

        # Take a screenshot of the scraped website
        output_dir = os.path.join('outputs', shorten_url(url))
        os.makedirs(output_dir, exist_ok=True)
        screenshot_path = os.path.join(output_dir, 'screenshot.png')
        take_screenshot(url, screenshot_path, countdown_seconds=3)

        return jsonify(content)
    except Exception as e:
        logger.error(f"Error scraping website: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@main.route('/archive', methods=['POST'])
async def archive():
    """
    API endpoint to scrape and archive a main webpage and its subpages.

    Expects JSON:
        {
            "url": "<URL>",
            "urls": ["<URL1>", "<URL2>", ...]
        }

    Returns:
        JSON response with a success message or an error message.
    """
    data = await request.json
    url = data.get('url')
    urls = data.get('urls', [])
    logger.debug(f"Archive request received for URL: {url} with subpages: {urls}")
    if not url:
        logger.warning("No URL provided in the archive request")
        return jsonify({"error": "No URL provided"}), 400

    folder_name = shorten_url(url)
    base_folder = os.path.join('outputs', folder_name)
    create_directory(base_folder)

    try:
        # Run the package creator to scrape and archive the website and its subpages
        zip_file_path = await run_package_creator(url, urls, os.path.join(base_folder, 'website_archive.zip'))
        logger.info(f"Website archived successfully: {zip_file_path}")
        return jsonify({"message": "Website archived successfully", "zip_path": zip_file_path}), 200
    except Exception as e:
        logger.error(f"Error during archiving process: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@main.route('/generate_zip', methods=['POST'])
async def generate_zip():
    """
    API endpoint to generate a ZIP archive of the scraped webpages.

    Expects JSON:
        {
            "urls": ["<URL1>", "<URL2>", ...]
        }

    Returns:
        ZIP file as an attachment.
    """
    data = await request.json
    urls = data.get('urls', [])
    logger.debug(f"Generate ZIP request received for URLs: {urls}")
    if not urls:
        logger.warning("No URLs provided in the generate_zip request")
        return jsonify({"error": "No URLs provided"}), 400

    base_url = urls[0] if urls else ''
    folder_name = shorten_url(base_url)
    base_folder = os.path.join('outputs', folder_name)
    create_directory(base_folder)

    try:
        # Run the package creator to scrape, screenshot, and zip the webpages
        zip_file_path = await run_package_creator(base_url, urls, os.path.join(base_folder, 'website_archive.zip'))
        logger.info(f"ZIP generation successful: {zip_file_path}")
        return await send_file(zip_file_path, as_attachment=True)
    except Exception as e:
        logger.error(f"Error during zip generation process: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
