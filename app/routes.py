from quart import Blueprint, request, render_template, redirect, url_for
import hashlib
import os
import logging
import asyncio
import threading
import uuid
import time
from concurrent.futures import ThreadPoolExecutor
from app.scrapers.fetch_content import scrape_website

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
scrape_lock = threading.Lock()

# Thread-Pool für Hintergrundaufgaben
executor = ThreadPoolExecutor(max_workers=4)

# Index Route
@main.route('/')
async def index():
    version = str(int(time.time()))  # Zeitstempel für Caching von Ressourcen
    return await render_template('index.html', version=version)

# Scraping-Funktion
async def run_scrape_task(task_id, url):
    try:
        start_time = time.time()
        with scrape_lock:
            scrape_tasks[task_id] = {'status': 'running'}  # Setze Status auf "running"

        # Führe das Scraping durch
        result = await scrape_website(url, max_depth=2, max_concurrency=500, use_cache=True)
        elapsed_time = time.time() - start_time

        # Ergebnisse speichern und Fortschritt aktualisieren
        with scrape_lock:
            scrape_tasks[task_id] = {
                'status': 'completed',
                'result': result,
                'num_pages': len(result['url_mapping']),
                'elapsed_time': elapsed_time,
                'time_per_page': elapsed_time / len(result['url_mapping']) if len(result['url_mapping']) > 0 else 0
            }
        logger.info(f"Scraping erfolgreich für {result['url']}")
    except Exception as e:
        logger.error(f"Fehler beim Scrapen der Website: {e}", exc_info=True)
        with scrape_lock:
            scrape_tasks[task_id] = {'status': 'failed', 'error': str(e)}

# Scrape-Route für POST-Anfragen
@main.route('/scrape_links', methods=['POST'])
async def scrape():
    url = (await request.form).get('url')
    logger.info(f"Scrape-Anfrage erhalten für URL: {url}")

    if not url:
        return await render_template('error.html', message='Keine URL angegeben'), 400

    try:
        # Generiere eine eindeutige Task-ID
        task_id = str(uuid.uuid4())

        # Der Pfad zur gecachten JSON-Datei basierend auf der URL
        cache_filename = hashlib.md5(url.encode()).hexdigest() + ".json"
        cache_filepath = os.path.join(MAPPING_DIR, cache_filename)

        # Überprüfe, ob die gecachte Datei existiert
        if os.path.exists(cache_filepath):
            logger.info(f"Gecachte Datei gefunden: {cache_filepath}")
            # Hier direkt die Links aus der Cache-Datei anzeigen
            with open(cache_filepath, 'r', encoding='utf-8') as f:
                cached_data = f.read()
            return await render_template('scrape_result.html', url_mapping=cached_data)

        else:
            # Starte das Scraping im Hintergrund
            loop = asyncio.get_event_loop()
            loop.run_in_executor(executor, asyncio.run, run_scrape_task(task_id, url))
            logger.info(f"Keine gecachte Datei gefunden. Scraping gestartet für URL: {url}")
            # Weiterleitung zu einer Status-Seite oder zu den Ergebnissen, wenn abgeschlossen
            return redirect(url_for('main.scrape_result', task_id=task_id))

    except Exception as e:
        logger.error(f"Fehler beim Starten des Scrapings: {e}", exc_info=True)
        return await render_template('error.html', message=str(e)), 500

# Route für das Anzeigen der gescrapten Links
@main.route('/scrape_result/<task_id>', methods=['GET'])
async def scrape_result(task_id):
    with scrape_lock:
        task_info = scrape_tasks.get(task_id)

    if not task_info or task_info['status'] != 'completed':
        return await render_template('error.html', message='Task noch nicht abgeschlossen oder nicht gefunden.'), 404

    # Kopiere das URL-Mapping, um den Fehler zu verhindern
    url_mapping = dict(task_info['result']['url_mapping'])

    # Debug: Logge den gesamten Inhalt des url_mapping, um sicherzustellen, dass alles korrekt geladen wurde
    for page_id, page_data in url_mapping.items():
        print(f"Page ID: {page_id}, Title: {page_data.get('title')}, Children: {len(page_data.get('children', []))}")

    return await render_template('scrape_result.html', url_mapping=url_mapping)
