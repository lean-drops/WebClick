# app/routes.py

import os
import logging
import hashlib
import asyncio
import shutil
import threading
import time
import uuid
from typing import List

from flask import Blueprint, request, render_template, redirect, url_for, jsonify, send_file
import json

from app.processing.website_downloader import (
    PDFConverter,
    merge_pdfs_with_bookmarks,
    create_zip_archive
)
from app.scrapers.scraping_helpers import (
    scrape_lock,
    scrape_tasks,
    run_scrape_task,
    render_links_recursive
)
from config import MAPPING_CACHE_DIR, logger, OUTPUT_PDFS_DIR, BASE_DIR, TEMPLATES_DIR, STATIC_DIR

# Blueprint initialisieren
main = Blueprint('main', __name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)

# Task Management
pdf_tasks = {}
pdf_lock = threading.Lock()

@main.route('/')
def index():
    version = str(int(time.time()))
    return render_template('index.html', version=version)

@main.route('/scrape_links', methods=['POST'])
def scrape():
    data = request.get_json()
    url = data.get('url')
    logger.info(f"Scrape request received for URL: {url}")

    if not url:
        return jsonify({'status': 'error', 'message': 'Keine URL angegeben.'}), 400

    try:
        task_id = hashlib.md5(url.encode()).hexdigest()
        cache_filepath = os.path.join(MAPPING_CACHE_DIR, f"{task_id}.json")

        if os.path.exists(cache_filepath):
            load_cached_task(task_id, cache_filepath)
            return jsonify({'status': 'success', 'task_id': task_id})
        else:
            threading.Thread(target=start_scrape_task, args=(task_id, url)).start()
            logger.info(f"No cached data found. Scraping started for URL: {url}")
            return jsonify({'status': 'success', 'task_id': task_id})
    except Exception as e:
        logger.error(f"Error starting scraping: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

def load_cached_task(task_id, cache_filepath):
    with scrape_lock:
        with open(cache_filepath, 'r', encoding='utf-8') as f:
            cached_url_mapping = json.load(f)
        scrape_tasks[task_id] = {
            'status': 'completed',
            'result': {'url_mapping': cached_url_mapping}
        }

def start_scrape_task(task_id, url):
    asyncio.run(run_scrape_task(task_id, url))

@main.route('/scrape_status/<task_id>', methods=['GET'])
def scrape_status(task_id):
    with scrape_lock:
        task_info = scrape_tasks.get(task_id)

    if not task_info:
        logger.error(f"Task {task_id} not found.")
        return render_template('error.html', message='Task nicht gefunden.'), 404

    status = task_info['status']
    if status == 'completed':
        return redirect(url_for('main.scrape_result', task_id=task_id))
    elif status == 'failed':
        error_message = task_info.get('error', 'Unbekannter Fehler.')
        return render_template('error.html', message=error_message), 500
    else:
        return render_template('scrape_status.html', task_id=task_id)

@main.route('/get_status/<task_id>', methods=['GET'])
def get_status(task_id):
    with scrape_lock:
        task_info = scrape_tasks.get(task_id)

    if not task_info:
        return jsonify({'status': 'not_found'})

    response_data = {
        'status': task_info['status'],
        'error': task_info.get('error'),
        # 'progress': task_info.get('progress', 0)  # Falls Fortschrittsdaten implementiert sind
    }
    return jsonify(response_data)

@main.route('/scrape_result/<task_id>')
def scrape_result(task_id):
    cache_filepath = os.path.join(MAPPING_CACHE_DIR, f"{task_id}.json")
    if not os.path.exists(cache_filepath):
        return "Result not found", 404

    with open(cache_filepath, 'r', encoding='utf-8') as f:
        result = json.load(f)
    url_mapping = result.get('url_mapping')
    base_page_id = result.get('base_page_id')

    links_html = render_links_recursive(url_mapping, base_page_id)

    main_link_info = url_mapping.get(base_page_id, {})
    main_link_url = main_link_info.get('url', '#')
    main_link_title = main_link_info.get('title', 'No Title')

    return render_template(
        'scrape_result.html',
        links_html=links_html,
        url_mapping=url_mapping,
        base_page_id=base_page_id,
        main_link_url=main_link_url,
        main_link_title=main_link_title
    )

@main.route('/start_pdf_task', methods=['POST'])
def start_pdf_task():
    try:
        data = request.get_json()
        selected_links = data.get('selected_links', [])
        conversion_mode = data.get('conversion_mode', 'collapsed')

        if not selected_links:
            return jsonify({'status': 'error', 'message': 'Keine Links ausgewählt.'}), 400

        if conversion_mode not in ['collapsed', 'expanded', 'both']:
            return jsonify({'status': 'error', 'message': 'Ungültiger Konvertierungsmodus.'}), 400

        task_id = str(uuid.uuid4())
        threading.Thread(target=run_pdf_task, args=(task_id, selected_links, conversion_mode)).start()
        logger.info(f"PDF-Task gestartet mit Task-ID: {task_id} und Modus: {conversion_mode}")

        return jsonify({'status': 'success', 'task_id': task_id}), 200

    except Exception as e:
        logger.error(f"Fehler beim Starten des PDF-Tasks: {e}")
        return jsonify({'status': 'error', 'message': 'Fehler beim Erstellen des PDF-Tasks'}), 500

def run_pdf_task(task_id, urls, conversion_mode):
    with pdf_lock:
        pdf_tasks[task_id] = {'status': 'running', 'result': {}, 'error': None, 'progress': 0}

    try:
        asyncio.run(_run_pdf_task(task_id, urls, conversion_mode))
    except Exception as e:
        logger.error(f"Fehler bei PDF-Task {task_id}: {e}", exc_info=True)
        with pdf_lock:
            pdf_tasks[task_id]['status'] = 'failed'
            pdf_tasks[task_id]['error'] = str(e)
            pdf_tasks[task_id]['progress'] = 0

async def _run_pdf_task(task_id, urls, conversion_mode):
    try:
        pdf_converter = PDFConverter(max_concurrent_tasks=5)
        await pdf_converter.initialize()

        results = {}
        total_steps = len(urls) * (2 if conversion_mode == 'both' else 1)
        current_step = 0

        def progress_callback(completed, total):
            nonlocal current_step, total_steps
            current_step += 1
            with pdf_lock:
                progress = int((current_step / total_steps) * 100)
                pdf_tasks[task_id]['progress'] = progress
                logger.info(f"Task {task_id} Fortschritt: {progress}% ({current_step}/{total_steps})")

        if conversion_mode in ['collapsed', 'both']:
            logger.info(f"PDF-Task {task_id}: Starte Konvertierung im 'collapsed' Modus.")
            collapsed_results = await pdf_converter.convert_urls_to_pdfs(urls, expanded=False, progress_callback=progress_callback)
            merged_collapsed_pdf = os.path.join(OUTPUT_PDFS_DIR, f"combined_pdfs_collapsed_{task_id}.pdf")
            merge_pdfs_with_bookmarks(collapsed_results, merged_collapsed_pdf)
            results['collapsed_pdf'] = merged_collapsed_pdf

        if conversion_mode in ['expanded', 'both']:
            logger.info(f"PDF-Task {task_id}: Starte Konvertierung im 'expanded' Modus.")
            expanded_results = await pdf_converter.convert_urls_to_pdfs(urls, expanded=True, progress_callback=progress_callback)
            merged_expanded_pdf = os.path.join(OUTPUT_PDFS_DIR, f"combined_pdfs_expanded_{task_id}.pdf")
            merge_pdfs_with_bookmarks(expanded_results, merged_expanded_pdf)
            results['expanded_pdf'] = merged_expanded_pdf

        await pdf_converter.close()

        # Speichere die individuellen PDFs für die spätere Auswahl
        with pdf_lock:
            pdf_tasks[task_id]['status'] = 'completed'
            pdf_tasks[task_id]['result'] = {'pdf_files': results}
            pdf_tasks[task_id]['progress'] = 100

        logger.info(f"PDF-Task abgeschlossen: {task_id}")

    except Exception as e:
        logger.error(f"Fehler bei PDF-Task {task_id}: {e}", exc_info=True)
        with pdf_lock:
            pdf_tasks[task_id]['status'] = 'failed'
            pdf_tasks[task_id]['error'] = str(e)
            pdf_tasks[task_id]['progress'] = 0

@main.route('/get_pdf_status/<task_id>', methods=['GET'])
def get_pdf_status(task_id):
    with pdf_lock:
        task_info = pdf_tasks.get(task_id)

    if not task_info:
        return jsonify({'status': 'not_found'})

    response_data = {
        'status': task_info['status'],
        'error': task_info.get('error'),
        'progress': task_info.get('progress', 0),
    }
    return jsonify(response_data)

@main.route('/pdf_result/<task_id>', methods=['GET'])
def pdf_result(task_id):
    with pdf_lock:
        task_info = pdf_tasks.get(task_id)

    if not task_info:
        logger.error(f"Task {task_id} not found.")
        return render_template('error.html', message='Task nicht gefunden.'), 404

    if task_info['status'] == 'failed':
        error_message = task_info.get('error', 'Unbekannter Fehler.')
        return render_template('error.html', message=error_message), 500

    if task_info['status'] != 'completed':
        return redirect(url_for('main.pdf_status', task_id=task_id))

    pdf_files = task_info['result'].get('pdf_files')
    if not pdf_files:
        return render_template('error.html', message='Keine PDF-Dateien gefunden.'), 404

    return render_template(
        'convert_result.html',
        pdf_files=pdf_files,
        task_id=task_id
    )

@main.route('/finalize_pdfs', methods=['POST'])
def finalize_pdfs():
    try:
        data = request.get_json()
        task_id = data.get('task_id')
        pdfs_to_include = data.get('pdfs_to_include', [])
        folder_name = data.get('folder_name').strip()

        logger.info(f"Empfangene Daten in finalize_pdfs - task_id: {task_id}, pdfs_to_include: {pdfs_to_include}, folder_name: {folder_name}")

        if not task_id or not pdfs_to_include or not folder_name:
            return jsonify({'status': 'error', 'message': 'Ungültige Daten.'}), 400

        with pdf_lock:
            task_info = pdf_tasks.get(task_id)

        if not task_info or task_info['status'] != 'completed':
            return jsonify({'status': 'error', 'message': 'Task nicht gefunden oder nicht abgeschlossen.'}), 404

        pdf_files = task_info['result'].get('pdf_files')
        if not pdf_files:
            return jsonify({'status': 'error', 'message': 'Keine PDF-Dateien gefunden.'}), 404

        # Verwende die Schlüssel direkt
        selected_pdfs = [pdf_files[key] for key in pdfs_to_include if key in pdf_files]

        if not selected_pdfs:
            return jsonify({'status': 'error', 'message': 'Keine gültigen PDFs ausgewählt.'}), 400

        logger.info(f"Ausgewählte PDFs für ZIP-Erstellung: {selected_pdfs}")

        zip_filename = os.path.join(OUTPUT_PDFS_DIR, f"{folder_name}_{task_id}.zip")
        create_zip_archive(selected_pdfs, zip_filename)

        # Speichere den Pfad der ZIP-Datei
        with pdf_lock:
            task_info['result']['zip_file'] = zip_filename
            logger.info(f"ZIP-Dateipfad gespeichert: {zip_filename}")

        download_url = url_for('main.download_pdfs', task_id=task_id, _external=True)

        return jsonify({'status': 'success', 'download_url': download_url}), 200

    except Exception as e:
        logger.error(f"Fehler bei finalize_pdfs: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Fehler bei der Finalisierung der PDFs.'}), 500

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

    logger.info(f"ZIP-Datei wird heruntergeladen: {zip_file_path}")

    return send_file(
        zip_file_path,
        as_attachment=True,
        download_name=os.path.basename(zip_file_path),
        mimetype='application/zip'
    )