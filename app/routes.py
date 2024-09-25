import hashlib
import os
import logging
import asyncio
import threading
import uuid
import time
from quart import Blueprint, request, jsonify, render_template
from app.scrapers.fetch_content import scrape_website  # Verwende dein existierendes fetch_content.py

# Blueprint initialisieren
main = Blueprint('main', __name__)

# Logging konfigurieren
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Cache-Verzeichnisse
CACHE_DIR = "/static/cache"
MAPPING_DIR = "/static/cache/mapping_cache"

# Fortschrittsverfolgung
scrape_tasks = {}

# Index Route
@main.route('/')
async def index():
    version = str(int(time.time()))  # Zeitstempel für Caching von Ressourcen
    return await render_template('index.html', version=version)

# Funktion zum Scraping im Hintergrund-Thread
def run_scrape_in_thread(task_id, url):
    async def scrape_task():
        try:
            start_time = time.time()
            scrape_tasks[task_id] = {'status': 'running'}  # Setze Status auf "running"

            # Führe das Scraping durch
            result = await scrape_website(
                url,
                max_depth=2,
                max_concurrency=500,
                use_cache=True
            )
            elapsed_time = time.time() - start_time

            # Ergebnisse speichern und Fortschritt aktualisieren
            scrape_tasks[task_id] = {
                'status': 'completed',
                'result': result,
                'num_pages': len(result['url_mapping']),
                'elapsed_time': elapsed_time,
                'time_per_page': elapsed_time / len(result['url_mapping']) if len(result['url_mapping']) > 0 else 0
            }
            logger.info(f"Scraping erfolgreich für {result['url']}")
            logger.debug(f"Scraping abgeschlossen. Ergebnis: {scrape_tasks[task_id]}")
        except Exception as e:
            logger.error(f"Fehler beim Scrapen der Website: {e}", exc_info=True)
            scrape_tasks[task_id] = {'status': 'failed', 'error': str(e)}

    # Event-Loop erstellen und ausführen
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(scrape_task())
    loop.close()

# Scrape-Route für POST-Anfragen
@main.route('/scrape_links', methods=['POST'])
async def scrape():
    if request.is_json:
        data = await request.get_json()
        url = data.get('url')
        logger.info(f"Scrape-Anfrage erhalten für URL: {url}")

        if not url:
            return jsonify({'error': 'Keine URL angegeben'}), 400

        try:
            # Erstelle die Cache-Verzeichnisse falls nötig
            os.makedirs(CACHE_DIR, exist_ok=True)
            os.makedirs(MAPPING_DIR, exist_ok=True)

            # Generiere eine eindeutige Task-ID
            task_id = str(uuid.uuid4())

            # Der Pfad zur gecachten JSON-Datei basierend auf der URL
            cache_filename = hashlib.md5(url.encode()).hexdigest() + ".json"
            cache_filepath = os.path.join(MAPPING_DIR, cache_filename)

            # Überprüfe, ob die gecachte Datei existiert
            if os.path.exists(cache_filepath):
                logger.info(f"Gecachte Datei gefunden: {cache_filepath}")
                # Hier direkt die Links aus der Cache-Datei zurückgeben
                with open(cache_filepath, 'r', encoding='utf-8') as f:
                    cached_data = f.read()
                return jsonify({'task_id': task_id, 'links': cached_data}), 202
            else:
                # Starte das Scraping in einem separaten Thread
                thread = threading.Thread(target=run_scrape_in_thread, args=(task_id, url))
                thread.start()
                logger.info(f"Keine gecachte Datei gefunden. Scraping gestartet für URL: {url}")
                return jsonify({'task_id': task_id, 'cache_filepath': None}), 202

        except Exception as e:
            logger.error(f"Fehler beim Starten des Scrapings: {e}", exc_info=True)
            return jsonify({'error': str(e)}), 500
    else:
        logger.error("Anfrage enthält kein JSON.")
        return jsonify({'error': 'Anfrage muss JSON-Daten enthalten'}), 400

# Fortschritt der Scraping-Tasks abfragen
@main.route('/scrape/status/<task_id>', methods=['GET'])
async def scrape_status(task_id):
    task_info = scrape_tasks.get(task_id)

    if not task_info:
        return jsonify({'error': 'Task-ID nicht gefunden'}), 404

    return jsonify(task_info)

# Route für das Anzeigen der gescrapten Links
# Route für das Anzeigen der gescrapten Links
@main.route('/scrape_result/<task_id>', methods=['GET'])
async def scrape_result(task_id):
    task_info = scrape_tasks.get(task_id)

    if not task_info or task_info['status'] != 'completed':
        return jsonify({'error': 'Task noch nicht abgeschlossen oder nicht gefunden.'}), 404

    # Extrahiere die Links aus dem Task-Ergebnis und zeige sie an
    url_mapping = task_info['result']['url_mapping']

    return await render_template('scrape_result.html', url_mapping=url_mapping)
