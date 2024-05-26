from quart import Blueprint, request, jsonify, render_template, send_file
from scrapers.create_directory import create_directory, shorten_url
from scrapers.fetch_content import scrape_website
from scrapers.scraper import run_package_creator
import os
import logging

# Logger konfigurieren
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

main = Blueprint('main', __name__)

@main.route('/')
async def index():
    """
    Rendert die Startseite der Anwendung.
    """
    return await render_template('index.html')

@main.route('/scrape', methods=['POST'])
async def scrape():
    """
    API-Endpunkt zum Scrapen einer einzelnen Webseite.

    Expects JSON:
        {
            "url": "<URL>"
        }

    Returns:
        JSON response with the content of the website or an error message.
    """
    data = await request.json
    url = data.get('url')
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        content = await scrape_website(url)
        if 'error' in content:
            return jsonify(content), 500
        return jsonify(content)
    except Exception as e:
        logger.error(f"Error scraping website: {e}")
        return jsonify({"error": str(e)}), 500

@main.route('/archive', methods=['POST'])
async def archive():
    """
    API-Endpunkt zum Scrapen und Archivieren einer Hauptseite und ihrer Unterseiten.

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
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    folder_name = shorten_url(url)
    base_folder = os.path.join('outputs', folder_name)
    create_directory(base_folder)

    try:
        # Scrape and screenshot the main URL and selected URLs
        zip_file_path = await run_package_creator(url, urls, os.path.join(base_folder, 'website_archive.zip'))
        return jsonify({"message": "Website archived successfully", "zip_path": zip_file_path}), 200
    except Exception as e:
        logger.error(f"Error during archiving process: {e}")
        return jsonify({"error": str(e)}), 500

@main.route('/generate_zip', methods=['POST'])
async def generate_zip():
    """
    API-Endpunkt zum Generieren eines ZIP-Archivs der gescrapten Webseiten.

    Expects JSON:
        {
            "urls": ["<URL1>", "<URL2>", ...]
        }

    Returns:
        ZIP file as an attachment.
    """
    data = await request.json
    urls = data.get('urls', [])
    if not urls:
        return jsonify({"error": "No URLs provided"}), 400

    base_url = urls[0] if urls else ''
    folder_name = shorten_url(base_url)
    base_folder = os.path.join('outputs', folder_name)
    create_directory(base_folder)

    try:
        # Run the package creator to scrape and screenshot the URLs and generate a ZIP file
        zip_file_path = await run_package_creator(base_url, urls, os.path.join(base_folder, 'website_archive.zip'))
        return await send_file(zip_file_path, as_attachment=True)
    except Exception as e:
        logger.error(f"Error during zip generation process: {e}")
        return jsonify({"error": str(e)}), 500
