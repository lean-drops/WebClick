"""
Routes for the Quart web application.

This script defines the main routes for a web scraping and archiving application using Quart. It includes the following routes:
1. `/` - Renders the homepage.
2. `/scrape` - API endpoint for scraping a single webpage. Expects JSON with a URL and returns the scraped content or an error message.
3. `/archive` - API endpoint for scraping and archiving a main webpage and its subpages. Expects JSON with a main URL and a list of subpage URLs. Returns a success message and the path to the ZIP archive or an error message.
4. `/generate_zip` - API endpoint for generating a ZIP archive of scraped webpages. Expects JSON with a list of URLs. Returns the ZIP file as an attachment or an error message.

Each route handles asynchronous requests and includes detailed logging for debugging and monitoring purposes.
"""

from quart import Blueprint, request, jsonify, render_template, send_file
from scrapers.create_directory import create_directory, shorten_url
from scrapers.fetch_content import scrape_website
from scrapers.scraper import run_package_creator
import os
import logging

# Configure logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define Blueprint
main = Blueprint('main', __name__)

@main.route('/')
async def index():
    """
    Renders the homepage of the application.
    """
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
