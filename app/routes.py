# app/routes.py

import os
import logging
import hashlib
import asyncio
import threading
import time
import uuid
from typing import List

from flask import Blueprint, request, render_template, redirect, url_for, jsonify, send_from_directory
import json

from app.processing.download import (
    OUTPUT_DIRECTORY,
    PDFConverter,
    merge_pdfs_with_bookmarks,
    apply_ocr_to_all_pdfs,
    create_zip_archive
)
from app.scrapers.scraping_helpers import (
    scrape_lock,
    scrape_tasks,
    run_scrape_task,  # Stelle sicher, dass dies eine async Funktion ist
    render_links_recursive
)
from config import MAPPING_DIR

# Logger konfigurieren
logger = logging.getLogger(__name__)

# Blueprint initialisieren
main = Blueprint('main', __name__)

# Task Management
pdf_tasks = {}
pdf_lock = threading.Lock()

# Index Route
@main.route('/')
def index():
    version = str(int(time.time()))  # Zeitstempel für Caching von Ressourcen
    return render_template('index.html', version=version)

# Route zum Starten des Scraping-Tasks
@main.route('/scrape_links', methods=['POST'])
def scrape():
    url = request.form.get('url')
    logger.info(f"Scrape-Anfrage erhalten für URL: {url}")

    if not url:
        return render_template('error.html', message='Keine URL angegeben'), 400

    try:
        # Generiere eine eindeutige Task-ID basierend auf der URL
        task_id = hashlib.md5(url.encode()).hexdigest()

        # Pfad zur gecachten JSON-Datei basierend auf der URL
        cache_filename = f"{task_id}.json"
        cache_filepath = os.path.join(MAPPING_DIR, cache_filename)

        # Überprüfe, ob die gecachte Datei existiert
        if os.path.exists(cache_filepath):
            logger.info(f"Gecachte Datei gefunden: {cache_filepath}")
            # Lade die gecachten Daten und speichere sie in scrape_tasks
            with scrape_lock:
                with open(cache_filepath, 'r', encoding='utf-8') as f:
                    cached_url_mapping = json.load(f)
                scrape_tasks[task_id] = {
                    'status': 'completed',
                    'result': {'url_mapping': cached_url_mapping}
                }
            # Weiterleitung zur Ergebnisanzeige
            return redirect(url_for('main.scrape_result', task_id=task_id))

        else:
            # Starte das Scraping im Hintergrund in einem neuen Thread
            threading.Thread(target=lambda: asyncio.run(run_scrape_task(task_id, url))).start()
            logger.info(f"Keine gecachte Datei gefunden. Scraping gestartet für URL: {url}")

            # Weiterleitung zu einer Status-Seite, während das Scraping läuft
            return redirect(url_for('main.scrape_status', task_id=task_id))

    except Exception as e:
        logger.error(f"Fehler beim Starten des Scrapings: {e}", exc_info=True)
        return render_template('error.html', message=str(e)), 500

# Route zur Anzeige des Scraping-Status
@main.route('/scrape_status/<task_id>', methods=['GET'])
def scrape_status(task_id):
    with scrape_lock:
        task_info = scrape_tasks.get(task_id)

    if not task_info:
        logger.error(f"Task {task_id} nicht gefunden.")
        return render_template('error.html', message='Task nicht gefunden.'), 404

    if task_info['status'] == 'completed':
        return redirect(url_for('main.scrape_result', task_id=task_id))

    elif task_info['status'] == 'failed':
        error_message = task_info.get('error', 'Unbekannter Fehler.')
        logger.error(f"Task {task_id} fehlgeschlagen: {error_message}")
        return render_template('error.html', message=error_message), 500

    else:
        # Übergeben Sie 'task_id' an das Template, um es für das Status-Update-Skript zu verwenden
        return render_template('scrape_status.html', task_id=task_id)

# API-Endpunkt zum Abrufen des Scraping-Status
@main.route('/get_status/<task_id>', methods=['GET'])
def get_status(task_id):
    with scrape_lock:
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
def scrape_result(task_id):
    version = str(int(time.time()))  # Timestamp for resource caching

    with scrape_lock:
        task_info = scrape_tasks.get(task_id)

    if not task_info:
        logger.error(f"Task {task_id} not found.")
        return render_template('error.html', message='Task not found.'), 404

    if task_info['status'] == 'failed':
        error_message = task_info.get('error', 'Unknown error.')
        logger.error(f"Task {task_id} failed: {error_message}")
        return render_template('error.html', message=error_message), 500

    if task_info['status'] != 'completed':
        return redirect(url_for('main.scrape_status', task_id=task_id))

    # Check if url_mapping exists
    result = task_info.get('result', {})
    url_mapping = result.get('url_mapping', {})
    base_page_id = result.get('base_page_id', None)

    if not url_mapping:
        logger.error(f"URL Mapping not found for Task {task_id}")
        return render_template('error.html', message='No data found.'), 404

    # Generate the tree structure for the template
    tree_html = render_links_recursive(url_mapping)

    if base_page_id:
        main_link_data = url_mapping.get(base_page_id, {})
        main_link_title = main_link_data.get('title', 'No Title')
        main_link_url = main_link_data.get('url', '#')
    else:
        main_link_title = 'No Main Link'
        main_link_url = '#'

    return render_template(
        'scrape_result.html',
        tree_html=tree_html,
        url_mapping=url_mapping,
        version=version,
        main_link_title=main_link_title,
        main_link_url=main_link_url
    )
# Route zum Starten des PDF-Tasks
@main.route('/start_pdf_task', methods=['POST'])
def start_pdf_task():
    try:
        data = request.get_json()
        selected_links = data.get('selected_links', [])

        if not selected_links:
            return jsonify({'status': 'error', 'message': 'Keine Links ausgewählt.'}), 400

        # Generiere eine eindeutige Task-ID
        task_id = str(uuid.uuid4())

        # Starte den PDF-Task im Hintergrund
        threading.Thread(target=lambda: asyncio.run(run_pdf_task(task_id, selected_links))).start()

        logger.info(f"PDF-Task gestartet mit Task-ID: {task_id}")

        return jsonify({'status': 'success', 'task_id': task_id}), 200

    except Exception as e:
        logger.error(f"Fehler beim Starten des PDF-Tasks: {e}")
        return jsonify({'status': 'error', 'message': 'Fehler beim Erstellen des PDF-Tasks'}), 500

def run_pdf_task(task_id: str, urls: List[str]):
    with pdf_lock:
        pdf_tasks[task_id] = {'status': 'running', 'result': {}, 'error': None}

    try:
        asyncio.run(_run_pdf_task(task_id, urls))

    except Exception as e:
        logger.error(f"Fehler bei PDF-Task {task_id}: {e}")
        with pdf_lock:
            pdf_tasks[task_id]['status'] = 'failed'
            pdf_tasks[task_id]['error'] = str(e)

async def _run_pdf_task(task_id: str, urls: List[str]):
    try:
        pdf_converter = PDFConverter(max_concurrent_tasks=20)
        await pdf_converter.initialize()

        # Erstelle PDFs mit eingeklapptem Inhalt
        collapsed_results = await pdf_converter.convert_urls_to_pdfs(urls, expanded=False)
        # Fasse die eingeklappten PDFs zusammen
        merged_collapsed_pdf = os.path.join(OUTPUT_DIRECTORY, f"combined_pdfs_collapsed_{task_id}.pdf")
        merge_pdfs_with_bookmarks(collapsed_results, merged_collapsed_pdf)

        # Erstelle PDFs mit ausgeklapptem Inhalt
        expanded_results = await pdf_converter.convert_urls_to_pdfs(urls, expanded=True)
        # Fasse die ausgeklappten PDFs zusammen
        merged_expanded_pdf = os.path.join(OUTPUT_DIRECTORY, f"combined_pdfs_expanded_{task_id}.pdf")
        merge_pdfs_with_bookmarks(expanded_results, merged_expanded_pdf)

        await pdf_converter.close()

        # Anwenden von OCR auf die PDFs
        apply_ocr_to_all_pdfs(
            individual_collapsed_dir=pdf_converter.output_dir_collapsed,
            individual_expanded_dir=pdf_converter.output_dir_expanded,
            merged_collapsed_pdf=merged_collapsed_pdf,
            merged_expanded_pdf=merged_expanded_pdf
        )

        # Erstelle ein ZIP-Archiv mit allen generierten PDFs und OCR-Versionen
        zip_filename = os.path.join(OUTPUT_DIRECTORY, f"output_pdfs_{task_id}.zip")
        create_zip_archive(OUTPUT_DIRECTORY, zip_filename)

        # Update Task Info
        with pdf_lock:
            pdf_tasks[task_id]['status'] = 'completed'
            pdf_tasks[task_id]['result'] = {'zip_file': zip_filename}

        logger.info(f"PDF-Task abgeschlossen: {task_id}")

    except Exception as e:
        logger.error(f"Fehler bei PDF-Task {task_id}: {e}")
        with pdf_lock:
            pdf_tasks[task_id]['status'] = 'failed'
            pdf_tasks[task_id]['error'] = str(e)

# Route zur Anzeige des PDF-Status
@main.route('/pdf_status/<task_id>', methods=['GET'])
def pdf_status(task_id):
    with pdf_lock:
        task_info = pdf_tasks.get(task_id)

    if not task_info:
        logger.error(f"Task {task_id} nicht gefunden.")
        return render_template('error.html', message='PDF Task nicht gefunden.'), 404

    if task_info['status'] == 'completed':
        return redirect(url_for('main.pdf_result', task_id=task_id))

    elif task_info['status'] == 'failed':
        error_message = task_info.get('error', 'Unbekannter Fehler.')
        logger.error(f"Task {task_id} fehlgeschlagen: {error_message}")
        return render_template('error.html', message=error_message), 500

    else:
        # Übergeben Sie 'task_id' an das Template, um es für das Status-Update-Skript zu verwenden
        return render_template('pdf_status.html', task_id=task_id)


# Route zum Abrufen des PDF-Task-Status
@main.route('/get_pdf_status/<task_id>', methods=['GET'])
def get_pdf_status(task_id):
    with pdf_lock:
        task_info = pdf_tasks.get(task_id)

    if not task_info:
        logger.debug(f"PDF Task {task_id} nicht gefunden.")
        return jsonify({'status': 'not_found'})

    # Gib den Status als JSON zurück
    response_data = {
        'status': task_info['status'],
        'error': task_info.get('error', None),
    }

    logger.debug(f"PDF Task {task_id} Status: {response_data}")
    return jsonify(response_data)

# Route zur Anzeige des PDF-Ergebnisses
@main.route('/pdf_result/<task_id>', methods=['GET'])
def pdf_result(task_id):
    with pdf_lock:
        task_info = pdf_tasks.get(task_id)

    if not task_info:
        logger.error(f"Task {task_id} nicht gefunden.")
        return render_template('error.html', message='Task nicht gefunden.'), 404

    if task_info['status'] == 'failed':
        error_message = task_info.get('error', 'Unbekannter Fehler.')
        logger.error(f"Task {task_id} fehlgeschlagen: {error_message}")
        return render_template('error.html', message=error_message), 500

    if task_info['status'] != 'completed':
        return redirect(url_for('main.pdf_status', task_id=task_id))

    # Überprüfe, ob zip_file vorhanden ist
    zip_file_path = task_info['result'].get('zip_file')
    if not zip_file_path or not os.path.exists(zip_file_path):
        logger.error(f"ZIP-Datei nicht vorhanden für Task {task_id}: {zip_file_path}")
        return render_template('error.html', message='ZIP-Datei nicht gefunden.'), 404

    return render_template(
        'convert_result.html',
        zip_filename=os.path.basename(zip_file_path),
        task_id=task_id
    )

# Route zum Herunterladen der ZIP-Datei
@main.route('/download_pdfs/<task_id>', methods=['GET'])
def download_pdfs(task_id):
    with pdf_lock:
        task_info = pdf_tasks.get(task_id)

    if not task_info:
        logger.error(f"PDF Task {task_id} nicht gefunden.")
        return render_template('error.html', message='PDF Task nicht gefunden.'), 404

    if task_info['status'] != 'completed':
        logger.warning(f"PDF Task {task_id} ist noch nicht abgeschlossen.")
        return render_template('error.html', message='PDF Task ist noch nicht abgeschlossen.'), 400

    zip_file_path = task_info['result'].get('zip_file')
    if not zip_file_path or not os.path.exists(zip_file_path):
        logger.error(f"ZIP-Datei nicht gefunden für Task {task_id}: {zip_file_path}")
        return render_template('error.html', message='ZIP-Datei nicht gefunden.'), 404

    # Verwenden Sie send_from_directory für eine bessere Handhabung von Pfaden
    directory = os.path.dirname(zip_file_path)
    filename = os.path.basename(zip_file_path)

    return send_from_directory(
        directory,
        filename,
        as_attachment=True,
        download_name=filename,
        mimetype='application/zip'
    )
