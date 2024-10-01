import json
import hashlib
import os
import asyncio
import time
from quart import Blueprint, request, render_template, redirect, url_for, jsonify, send_file
import aiofiles
from app.processing.screenshot import run_screenshot_task, screenshot_tasks, screenshot_lock
from config import MAPPING_DIR, logger
from app.scraping_helpers import run_scrape_task, render_links_recursive, scrape_tasks, scrape_lock

# Blueprint initialisieren
main = Blueprint('main', __name__)

# Index Route
@main.route('/')
async def index():
    version = str(int(time.time()))  # Zeitstempel für Caching von Ressourcen
    return await render_template('index.html', version=version)

# Route zum Starten des Scrapings
@main.route('/scrape_links', methods=['POST'])
async def scrape():
    form = await request.form
    url = form.get('url')
    logger.info(f"Scrape-Anfrage erhalten für URL: {url}")

    if not url:
        return await render_template('error.html', message='Keine URL angegeben'), 400

    try:
        # Generiere eine eindeutige Task-ID basierend auf der URL
        task_id = hashlib.md5(url.encode()).hexdigest()

        # Der Pfad zur gecachten JSON-Datei basierend auf der URL
        cache_filename = f"{task_id}.json"
        cache_filepath = os.path.join(MAPPING_DIR, cache_filename)

        # Überprüfe, ob die gecachte Datei existiert
        if os.path.exists(cache_filepath):
            logger.info(f"Gecachte Datei gefunden: {cache_filepath}")
            # Lade die gecachten Daten und speichere sie in scrape_tasks
            async with scrape_lock:
                async with aiofiles.open(cache_filepath, 'r', encoding='utf-8') as f:
                    cached_url_mapping = json.loads(await f.read())
                scrape_tasks[task_id] = {
                    'status': 'completed',
                    'result': {'url_mapping': cached_url_mapping}
                }
            # Weiterleitung zur Ergebnisanzeige
            return redirect(url_for('main.scrape_result', task_id=task_id))

        else:
            # Starte das Scraping im Hintergrund
            asyncio.create_task(run_scrape_task(task_id, url))
            logger.info(f"Keine gecachte Datei gefunden. Scraping gestartet für URL: {url}")

            # Weiterleitung zu einer Status-Seite, während das Scraping läuft
            return redirect(url_for('main.scrape_status', task_id=task_id))

    except Exception as e:
        logger.error(f"Fehler beim Starten des Scrapings: {e}", exc_info=True)
        return await render_template('error.html', message=str(e)), 500

# Route zur Anzeige des Scraping-Status
@main.route('/scrape_status/<task_id>', methods=['GET'])
async def scrape_status(task_id):
    # Hier den task_info Status abfragen, um Fortschritt anzuzeigen
    async with scrape_lock:
        task_info = scrape_tasks.get(task_id)

    if not task_info:
        logger.error(f"Task {task_id} nicht gefunden.")
        return await render_template('error.html', message='Task nicht gefunden.'), 404

    if task_info['status'] == 'completed':
        return redirect(url_for('main.scrape_result', task_id=task_id))

    elif task_info['status'] == 'failed':
        error_message = task_info.get('error', 'Unbekannter Fehler.')
        logger.error(f"Task {task_id} fehlgeschlagen: {error_message}")
        return await render_template('error.html', message=error_message), 500

    else:
        # Übergeben Sie 'task_id' an das Template, um es für das Status-Update-Skript zu verwenden
        return await render_template('scrape_status.html', task_id=task_id)

# API-Endpunkt zum Abrufen des Scraping-Status
@main.route('/get_status/<task_id>', methods=['GET'])
async def get_status(task_id):
    async with scrape_lock:
        task_info = scrape_tasks.get(task_id)

    if not task_info:
        logger.debug(f"Task {task_id} nicht gefunden.")
        return jsonify({'status': 'not_found'})

    # Gib den Status und andere Details als JSON zurück
    response_data = {
        'status': task_info['status'],
        'error': task_info.get('error', None),
        'url_mapping': task_info['result'].get('url_mapping', None) if task_info['status'] == 'completed' else None
    }

    logger.debug(f"Task {task_id} Status: {response_data}")
    return jsonify(response_data)

# Route zur Anzeige des Scraping-Ergebnisses
@main.route('/scrape_result/<task_id>', methods=['GET'])
async def scrape_result(task_id):
    version = str(int(time.time()))  # Zeitstempel für Caching

    async with scrape_lock:
        task_info = scrape_tasks.get(task_id)

    if not task_info:
        logger.error(f"Task {task_id} nicht gefunden.")
        return await render_template('error.html', message='Task nicht gefunden.'), 404

    if task_info['status'] == 'failed':
        error_message = task_info.get('error', 'Unbekannter Fehler.')
        logger.error(f"Task {task_id} fehlgeschlagen: {error_message}")
        return await render_template('error.html', message=error_message), 500

    if task_info['status'] != 'completed':
        return redirect(url_for('main.scrape_status', task_id=task_id))

    url_mapping = task_info['result'].get('url_mapping', {})

    # Erzeuge die Baumstruktur für das Template
    tree_html = render_links_recursive(url_mapping)

    return await render_template(
        'scrape_result.html',
        tree_html=tree_html,
        version=version
    )

# Route zum Starten des Screenshot-Tasks
@main.route('/start_screenshot_task', methods=['POST'])
async def start_screenshot_task():
    form = await request.form
    selected_links_json = form.get('selected_links')
    if not selected_links_json:
        return await render_template('error.html', message='Keine Links ausgewählt.'), 400
    selected_links = json.loads(selected_links_json)
    logger.info(f"Screenshots werden erstellt für Links: {selected_links}")

    # Generiere eine eindeutige Task-ID basierend auf den ausgewählten Links
    task_id = hashlib.md5(''.join(selected_links).encode()).hexdigest()

    # Starte den Screenshot-Task im Hintergrund
    asyncio.create_task(run_screenshot_task(task_id, selected_links))
    logger.info(f"Screenshot-Task gestartet für Task-ID: {task_id}")

    # Weiterleitung zur Status-Seite
    return redirect(url_for('main.screenshot_status', task_id=task_id))

# Route zur Anzeige des Screenshot-Status
@main.route('/screenshot_status/<task_id>', methods=['GET'])
async def screenshot_status(task_id):
    async with screenshot_lock:
        task_info = screenshot_tasks.get(task_id)

    if not task_info:
        logger.error(f"Screenshot Task {task_id} nicht gefunden.")
        return await render_template('error.html', message='Screenshot Task nicht gefunden.'), 404

    if task_info['status'] == 'completed':
        return redirect(url_for('main.screenshot_result', task_id=task_id))

    elif task_info['status'] == 'failed':
        error_message = task_info.get('error', 'Unbekannter Fehler.')
        logger.error(f"Screenshot Task {task_id} fehlgeschlagen: {error_message}")
        return await render_template('error.html', message=error_message), 500

    else:
        # Zeige die Ladeanzeige
        return await render_template('screenshot_status.html', task_id=task_id)

# API-Endpunkt zum Abrufen des Screenshot-Status
@main.route('/get_screenshot_status/<task_id>', methods=['GET'])
async def get_screenshot_status(task_id):
    async with screenshot_lock:
        task_info = screenshot_tasks.get(task_id)

    if not task_info:
        logger.debug(f"Screenshot Task {task_id} nicht gefunden.")
        return jsonify({'status': 'not_found'})

    logger.debug(f"Screenshot Task {task_id} Status: {task_info['status']}")
    return jsonify({'status': task_info['status']})

# Route zur Anzeige des Screenshot-Ergebnisses
@main.route('/screenshot_result/<task_id>', methods=['GET'])
async def screenshot_result(task_id):
    async with screenshot_lock:
        task_info = screenshot_tasks.get(task_id)

    if not task_info:
        logger.error(f"Screenshot Task {task_id} nicht gefunden.")
        return await render_template('error.html', message='Screenshot Task nicht gefunden.'), 404

    if task_info['status'] == 'failed':
        error_message = task_info.get('error', 'Unbekannter Fehler.')
        logger.error(f"Screenshot Task {task_id} fehlgeschlagen: {error_message}")
        return await render_template('error.html', message=error_message), 500

    if task_info['status'] != 'completed':
        return redirect(url_for('main.screenshot_status', task_id=task_id))

    zip_filename = task_info['result']['zip_file']
    zip_dir = r"C:\Users\BZZ1391\Bingo\WebClick\output directory\zipped screenshots"  # Pfad anpassen
    zip_filepath = os.path.join(zip_dir, zip_filename)

    # Überprüfen, ob die ZIP-Datei existiert
    if not os.path.exists(zip_filepath):
        logger.error(f"ZIP-Datei {zip_filepath} nicht gefunden.")
        return await render_template('error.html', message='Screenshots nicht verfügbar.'), 404

    return await render_template('screenshot_result.html', zip_filename=zip_filename, task_id=task_id)

# Route zum Herunterladen der Screenshots
@main.route('/download_screenshots/<task_id>', methods=['GET'])
async def download_screenshots(task_id):
    async with screenshot_lock:
        task_info = screenshot_tasks.get(task_id)

    if not task_info or task_info['status'] != 'completed':
        logger.error(f"Screenshots für Aufgabe {task_id} nicht verfügbar.")
        return await render_template('error.html', message='Screenshots nicht verfügbar.'), 404

    zip_filename = task_info['result']['zip_file']
    zip_dir = r"C:\Users\BZZ1391\Bingo\WebClick\output directory\zipped screenshots"  # Pfad anpassen
    zip_filepath = os.path.join(zip_dir, zip_filename)

    # Überprüfen, ob die ZIP-Datei existiert
    if not os.path.exists(zip_filepath):
        logger.error(f"ZIP-Datei {zip_filepath} nicht gefunden.")
        return await render_template('error.html', message='Screenshots nicht verfügbar.'), 404

    return await send_file(
        zip_filepath,
        as_attachment=True,
        attachment_filename=zip_filename
    )

# Route zur Anzeige des kombinierten Bildes
@main.route('/combined_image/<task_id>', methods=['GET'])
async def combined_image(task_id):
    async with screenshot_lock:
        task_info = screenshot_tasks.get(task_id)

    if not task_info or task_info['status'] != 'completed':
        logger.error(f"Kombiniertes Bild für Aufgabe {task_id} nicht verfügbar.")
        return await render_template('error.html', message='Kombiniertes Bild nicht verfügbar.'), 404

    combined_image_path = task_info['result'].get('combined_image')
    if not combined_image_path or not os.path.exists(combined_image_path):
        logger.error(f"Kombiniertes Bild {combined_image_path} nicht gefunden.")
        return await render_template('error.html', message='Kombiniertes Bild nicht verfügbar.'), 404

    return await send_file(
        combined_image_path,
        mimetype='image/png'
    )
