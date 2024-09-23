from quart import Blueprint, request, jsonify, render_template, send_file

from app.create_package.create_directory import shorten_url, create_directory
from app.scrapers.fetch_content import scrape_website
import os
import logging

main = Blueprint('main', __name__)

# Logging konfigurieren
logging.basicConfig(
    handlers=[logging.FileHandler("../../logs/routes.log")],
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

@main.route('/')
async def index():
    return await render_template('index.html')

@main.route('/scrape', methods=['POST'])
async def scrape():
    form_data = await request.form
    url = form_data.get('url')
    logger.info(f"Scrape request received for URL: {url}")

    if not url:
        return await render_template('index.html', error="Keine URL angegeben")

    try:
        # max_depth und max_concurrency nach Bedarf anpassen
        result = await scrape_website(url, max_depth=2, max_concurrency=100)
        if 'error' in result:
            return await render_template('index.html', error=result['error'])

        # Daten an das Template übergeben
        return await render_template(
            'index.html',
            links=result['url_mapping'],
            url=url,
            base_page_id=result['base_page_id']
        )
    except Exception as e:
        logger.error(f"Error scraping website: {e}", exc_info=True)
        return await render_template('index.html', error=str(e))
