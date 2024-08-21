from flask import Blueprint, request, jsonify, render_template
import asyncio
from scrapers.scraper import scrape_website
from converters.pdf_converter import convert_to_pdf

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/archive', methods=['POST'])
async def archive():
    data = request.json
    urls = data.get('urls', [])
    if not urls:
        return jsonify({"error": "No URLs provided"}), 400

    loop = asyncio.get_event_loop()
    futures = [loop.run_in_executor(None, scrape_website, url) for url in urls]
    results = await asyncio.gather(*futures)

    pdf_file = await convert_to_pdf(results)

    return jsonify({"pdf_file": pdf_file}), 200

@main.route('/scrape', methods=['POST'])
async def scrape():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    content = scrape_website(url)
    return jsonify(content), 200

@main.route('/generate_pdf', methods=['POST'])
async def generate_pdf():
    data = request.json
    urls = data.get('urls', [])
    if not urls:
        return jsonify({"error": "No URLs provided"}), 400

    loop = asyncio.get_event_loop()
    futures = [loop.run_in_executor(None, scrape_website, url) for url in urls]
    results = await asyncio.gather(*futures)

    pdf_file = await convert_to_pdf(results)

    return jsonify({"pdf_file": pdf_file}), 200
