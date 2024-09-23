import logging
from quart import Blueprint, request, jsonify, render_template, send_file
from app.create_package.create_directory import shorten_url, create_directory
from app.scrapers.fetch_content import scrape_website
import os

from app.scrapers.scraper import run_package_creator

# Logging configuration
if not os.path.exists('../../logs'):
    os.makedirs('../../logs')

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
        return await render_template('index.html', error="Keine URL angegeben")

    try:
        # Passen Sie die max_depth nach Bedarf an
        result = await scrape_website(url, max_depth=2)
        if 'error' in result:
            return await render_template('index.html', error=result['error'])

        # Übergeben Sie die URL-Mapping und die Basis-Seiten-ID an das Template
        return await render_template(
            'index.html',
            links=result['url_mapping'],
            url=url,
            base_page_id=result['base_page_id']
        )
    except Exception as e:
        logger.error(f"Error scraping website: {e}", exc_info=True)
        return await render_template('index.html', error=str(e))

@main.route('/archive', methods=['POST'])
async def archive():
    """
    API endpoint to archive selected links.

    Expects form data with:
        - 'url': base URL
        - 'urls': list of selected URLs to archive

    Returns:
        JSON response with a success message or an error message.
    """
    form_data = await request.form
    base_url = form_data.get('url')
    urls = form_data.getlist('urls')
    logger.info(f"Archive request received for URL: {base_url} with selected links: {urls}")

    if not base_url or not urls:
        logger.warning("No URL or links provided in the archive request")
        return jsonify({"error": "Keine URL oder Links angegeben"}), 400

    folder_name = shorten_url(base_url)
    base_folder = os.path.join('outputs_directory', folder_name)
    create_directory(base_folder)

    try:
        # Run the package creator to scrape and archive the selected links
        zip_file_path = await run_package_creator(base_url, urls, os.path.join(base_folder, 'website_archive.zip'))
        logger.info(f"Website archived successfully: {zip_file_path}")
        return jsonify({
            "message": "Website erfolgreich archiviert",
            "zip_path": zip_file_path,
            "archived_urls": urls
        }), 200
    except Exception as e:
        logger.error(f"Error during archiving process: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
