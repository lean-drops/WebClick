from flask import Blueprint, request, jsonify, render_template, send_file
from scrapers.scraper import scrape_website, scrape_multiple_websites
from converters.pdf_converter import convert_to_pdf
import os
import re
from urllib.parse import urlparse

main = Blueprint('main', __name__)

def shorten_url(url):
    parsed_url = urlparse(url)
    short_name = re.sub(r'\W+', '', parsed_url.netloc)
    return short_name

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/scrape', methods=['POST'])
def scrape():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    folder_name = shorten_url(url)
    base_folder = os.path.join('outputs', folder_name)

    content = scrape_website(url, base_folder)
    if 'error' in content:
        return jsonify(content), 500

    return jsonify(content), 200

@main.route('/archive', methods=['POST'])
def archive():
    data = request.json
    url = data.get('url')
    urls = data.get('urls', [])
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    folder_name = shorten_url(url)
    base_folder = os.path.join('outputs', folder_name)

    # Scrape the main URL
    content = scrape_website(url, base_folder)
    if 'error' in content:
        return jsonify(content), 500

    # Scrape the selected URLs
    if urls:
        results = scrape_multiple_websites(urls, base_folder)
        if not results:
            return jsonify({"error": "No URLs scraped"}), 400

    return jsonify({"message": "Website archived successfully"}), 200

@main.route('/generate_zip', methods=['POST'])
def generate_zip():
    data = request.json
    urls = data.get('urls', [])
    if not urls:
        return jsonify({"error": "No URLs provided"}), 400

    base_url = urls[0] if urls else ''
    folder_name = shorten_url(base_url)
    base_folder = os.path.join('outputs', folder_name)

    results = scrape_multiple_websites(urls, base_folder)

    zip_file = convert_to_pdf(results, base_folder)

    return send_file(zip_file, as_attachment=True)
