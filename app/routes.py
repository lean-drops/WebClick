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

    # Überprüfe, ob url_mapping vorhanden ist
    url_mapping = task_info['result'].get('url_mapping', {})
    if not url_mapping:
        logger.error(f"URL Mapping nicht vorhanden für Task {task_id}")
        return await render_template('error.html', message='Keine Daten gefunden.'), 404

    # Erzeuge die Baumstruktur für das Template
    tree_html = render_links_recursive(url_mapping)

    # Extrahiere den Hauptlink (erste Seite im Mapping)
    main_link_id = list(url_mapping.keys())[0]  # Annahme: Der Hauptlink ist der erste Eintrag
    main_link_title = url_mapping[main_link_id].get('title')
    main_link_url = url_mapping[main_link_id].get('url')

    # Render the template and pass the 'tree_html' and 'version'
    return await render_template(
        'scrape_result.html',
        tree_html=tree_html,
        url_mapping=url_mapping,  # Füge url_mapping hinzu
        version=version,
        main_link_title=main_link_title,  # Hauptlink-Titel an das Template übergeben
        main_link_url=main_link_url  # Hauptlink-URL an das Template übergeben
    )

# Route zum Starten des Screenshot-Tasks
# Route zum Starten des Screenshot-Tasks
@main.route('/start_screenshot_task', methods=['POST'])
async def start_screenshot_task():
    try:
        data = await request.get_json()
        selected_links = data.get('selected_links', [])

        if not selected_links:
            return jsonify({'status': 'error', 'message': 'Keine Links ausgewählt.'}), 400

        logger.info(f"Screenshots werden erstellt für Links: {selected_links}")

        # Generiere eine eindeutige Task-ID basierend auf den ausgewählten Links
        task_id = hashlib.md5(''.join(selected_links).encode()).hexdigest()

        # Starte den Screenshot-Task im Hintergrund
        asyncio.create_task(run_screenshot_task(task_id, selected_links))
        logger.info(f"Screenshot-Task gestartet für Task-ID: {task_id}")

        # Rückgabe als JSON an den Client, damit er die Umleitung handhabt
        return jsonify({'status': 'success', 'task_id': task_id}), 200

    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Screenshot-Tasks: {e}")
        return jsonify({'status': 'error', 'message': 'Fehler beim Erstellen des Tasks'}), 500

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
        return await render_template('screenshot_load.html', task_id=task_id)


# API-Endpunkt zum Abrufen des Screenshot-Status
@main.route('/get_screenshot_status/<task_id>', methods=['GET'])
async def get_screenshot_status(task_id):
    """
    API-Endpunkt zum Abrufen des aktuellen Status eines Screenshot-Tasks.
    Gibt den Status als JSON zurück.
    """
    try:
        async with screenshot_lock:
            task_info = screenshot_tasks.get(task_id)

        if not task_info:
            logger.debug(f"Screenshot Task {task_id} nicht gefunden.")
            return jsonify({'status': 'not_found'}), 404

        status = task_info.get('status', 'unknown')
        response_data = {'status': status}

        logger.debug(f"Screenshot Task {task_id} Status: {status}")
        return jsonify(response_data), 200

    except Exception as e:
        logger.exception(f"Fehler beim Abrufen des Screenshot-Status für Task {task_id}:")
        return jsonify({'status': 'error', 'message': 'Fehler beim Abrufen des Task-Status.'}), 500


# Route zur Anzeige des Screenshot-Ergebnisses
@main.route('/screenshot_result/<task_id>', methods=['GET'])
async def screenshot_result(task_id):
    """
    Anzeige der Screenshot-Ergebnisse für einen abgeschlossenen Task.
    """
    zip_dir = r"C:\Users\BZZ1391\Bingo\WebClick\output directory\zipped screenshots"  # Pfad anpassen

    try:
        async with screenshot_lock:
            task_info = screenshot_tasks.get(task_id)

        if not task_info:
            logger.error(f"Screenshot Task {task_id} nicht gefunden.")
            return await render_template('error.html', message='Screenshot Task nicht gefunden.'), 404

        status = task_info.get('status')

        if status == 'failed':
            error_message = task_info.get('error', 'Unbekannter Fehler.')
            logger.error(f"Screenshot Task {task_id} fehlgeschlagen: {error_message}")
            return await render_template('error.html', message=error_message), 500

        if status != 'completed':
            logger.info(f"Screenshot Task {task_id} ist noch {status}. Weiterleitung zur Statusseite.")
            return redirect(url_for('main.screenshot_status', task_id=task_id))

        # Überprüfe, ob zip_file vorhanden ist
        zip_filename = task_info['result'].get('zip_file')
        if not zip_filename:
            logger.error(f"ZIP-Dateiname nicht vorhanden für Task {task_id}.")
            return await render_template('error.html', message='ZIP-Datei nicht gefunden.'), 404

        zip_filepath = os.path.join(zip_dir, zip_filename)

        # Überprüfen, ob die ZIP-Datei existiert
        if not os.path.exists(zip_filepath):
            logger.error(f"ZIP-Datei {zip_filepath} nicht gefunden.")
            return await render_template('error.html', message='Screenshots nicht verfügbar.'), 404

        return await render_template('screenshot_result.html', zip_filename=zip_filename, task_id=task_id)

    except Exception as e:
        logger.exception(f"Fehler beim Anzeigen der Screenshot-Ergebnisse für Task {task_id}:")
        return await render_template('error.html', message='Fehler beim Anzeigen der Screenshot-Ergebnisse.'), 500


# Route zum Herunterladen der Screenshots
@main.route('/download_screenshots/<task_id>', methods=['GET'])
async def download_screenshots(task_id):
    """
    Ermöglicht den Download der erstellten Screenshots als ZIP-Datei für einen abgeschlossenen Task.
    """
    zip_dir = r"C:\Users\BZZ1391\Bingo\WebClick\output directory\zipped screenshots"  # Pfad anpassen

    try:
        async with screenshot_lock:
            task_info = screenshot_tasks.get(task_id)

        if not task_info:
            logger.error(f"Screenshots für Task {task_id} nicht gefunden.")
            return await render_template('error.html', message='Screenshots nicht verfügbar.'), 404

        status = task_info.get('status')
        if status != 'completed':
            logger.warning(f"Screenshots für Task {task_id} sind noch nicht abgeschlossen.")
            return await render_template('error.html', message='Screenshots sind noch nicht verfügbar.'), 404

        zip_filename = task_info['result'].get('zip_file')
        if not zip_filename:
            logger.error(f"ZIP-Dateiname nicht vorhanden für Task {task_id}.")
            return await render_template('error.html', message='ZIP-Datei nicht gefunden.'), 404

        zip_filepath = os.path.join(zip_dir, zip_filename)

        if not os.path.exists(zip_filepath):
            logger.error(f"ZIP-Datei {zip_filepath} nicht gefunden.")
            return await render_template('error.html', message='Screenshots nicht verfügbar.'), 404

        return await send_file(
            zip_filepath,
            as_attachment=True,
            attachment_filename=zip_filename,  # Verwende 'attachment_filename' statt 'download_name'
            mimetype='application/zip'
        )

    except Exception as e:
        logger.exception(f"Fehler beim Herunterladen der Screenshots für Task {task_id}:")
        return await render_template('error.html', message='Fehler beim Herunterladen der Screenshots.'), 500


# Route zur Anzeige des kombinierten Bildes
@main.route('/combined_image/<task_id>', methods=['GET'])
async def combined_image(task_id):
    """
    Anzeige des kombinierten Bildes für einen abgeschlossenen Screenshot-Task.
    """
    try:
        async with screenshot_lock:
            task_info = screenshot_tasks.get(task_id)

        if not task_info:
            logger.error(f"Kombiniertes Bild für Task {task_id} nicht gefunden.")
            return await render_template('error.html', message='Kombiniertes Bild nicht verfügbar.'), 404

        status = task_info.get('status')
        if status != 'completed':
            logger.warning(f"Kombiniertes Bild für Task {task_id} ist noch {status}.")
            return await render_template('error.html', message='Kombiniertes Bild ist noch nicht verfügbar.'), 404

        combined_image_path = task_info['result'].get('combined_image')
        if not combined_image_path:
            logger.error(f"Kombiniertes Bildpfad nicht vorhanden für Task {task_id}.")
            return await render_template('error.html', message='Kombiniertes Bildpfad nicht gefunden.'), 404

        if not os.path.exists(combined_image_path):
            logger.error(f"Kombiniertes Bild {combined_image_path} nicht gefunden.")
            return await render_template('error.html', message='Kombiniertes Bild nicht verfügbar.'), 404

        return await send_file(
            combined_image_path,
            mimetype='image/png',
            download_name=os.path.basename(combined_image_path)  # Optional: Dateiname für Download festlegen
        )

    except Exception as e:
        logger.exception(f"Fehler beim Anzeigen des kombinierten Bildes für Task {task_id}:")
        return await render_template('error.html', message='Fehler beim Anzeigen des kombinierten Bildes.'), 500
