import logging
from collections import defaultdict

from quart import Blueprint, request, jsonify, render_template, send_file

from app.create_package.create_directory import shorten_url, create_directory
from app.scrapers.fetch_content import scrape_website, url_to_filename
from app.scrapers.scraper import run_package_creator
import os

# Logging configuration
# Ensure the 'logs' directory exists
if not os.path.exists('../../logs'):
    os.makedirs('../../logs')

# Setup the logging handler
logging.basicConfig(
    handlers=[logging.FileHandler("../../logs/routes.log")],
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Define Blueprint
main = Blueprint('main', __name__)


@main.route('/')
async def index():
    """
    Renders the homepage of the application.
    """
    logger.info("Rendering the homepage")
    return await render_template('index.html')


@main.route('/scrape', methods=['POST'])
async def scrape():
    form_data = await request.form
    url = form_data.get('url')
    logger.info(f"Scrape request received for URL: {url}")

    if not url:
        logger.warning("No URL provided in the request")
        return await render_template('index.html', error="No URL provided")

    try:
        # Scrape the website and get the links
        content = await scrape_website(url, url_mapping={})
        logger.info(f"Scraping successful for URL: {url}")

        if 'error' in content:
            return await render_template('index.html', error=content['error'])

        # Render the template with the scraped links
        return await render_template('index.html', links=content['pages'], url=url)
    except Exception as e:
        logger.error(f"Error scraping website: {e}", exc_info=True)
        return await render_template('index.html', error=str(e))



@main.route('/archive', methods=['POST'])
async def archive():
    """
    API endpoint to archive selected links.

    Expects JSON:
        {
            "url": "<URL>",
            "urls": ["<URL1>", "<URL2>", ...]
        }

    Returns:
        JSON response with a success message or an error message.
    """
    data = await request.json
    base_url = data.get('url')
    urls = data.get('urls', [])
    logger.info(f"Archive request received for URL: {base_url} with selected links: {urls}")

    if not base_url or not urls:
        logger.warning("No URL or links provided in the archive request")
        return jsonify({"error": "No URL or links provided"}), 400

    folder_name = shorten_url(base_url)
    base_folder = os.path.join('outputs_directory', folder_name)
    create_directory(base_folder)

    try:
        # Run the package creator to scrape and archive the selected links
        zip_file_path = await run_package_creator(base_url, urls, os.path.join(base_folder, 'website_archive.zip'))
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
    logger.info(f"Generate ZIP request received for URLs: {urls}")
    if not urls:
        logger.warning("No URLs provided in the generate_zip request")
        return jsonify({"error": "No URLs provided"}), 400

    base_url = urls[0] if urls else ''
    folder_name = shorten_url(base_url)
    base_folder = os.path.join('outputs_directory', folder_name)
    create_directory(base_folder)

    try:
        # Run the package creator to scrape, screenshot, and zip the webpages
        zip_file_path = await run_package_creator(base_url, urls, os.path.join(base_folder, 'website_archive.zip'))
        logger.info(f"ZIP generation successful: {zip_file_path}")
        return await send_file(zip_file_path, as_attachment=True)
    except Exception as e:
        logger.error(f"Error during zip generation process: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
