# app/views/pdf_views.py
import os
import asyncio
import threading
import uuid
import logging
from typing import List
from flask import (
    Blueprint,
    request,
    render_template,
    redirect,
    url_for,
    jsonify,
    send_file
)

from app.processing.pdf_converter import (
    PDFConverter,
    create_zip_archive,
    OUTPUT_DIRECTORY,
    merge_pdfs_with_bookmarks
)
from app.utils.naming_utils import extract_website_name, sanitize_filename

main = Blueprint('main', __name__)

logger = logging.getLogger(__name__)

pdf_tasks = {}
pdf_lock = threading.Lock()

# Definieren Sie ein separates Verzeichnis für ZIP-Dateien
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIP_OUTPUT_DIRECTORY = os.path.join(BASE_DIR, 'zip_archives')
os.makedirs(ZIP_OUTPUT_DIRECTORY, exist_ok=True)

@main.route('/start_pdf_task', methods=['POST'])
def start_pdf_task():
    try:
        data = request.get_json()
        logger.debug(f"Empfangene Daten: {data}")
        selected_links = data.get('selected_links', [])
        custom_main_name = data.get('custom_main_name', '').strip()

        if not selected_links:
            return jsonify({'status': 'error', 'message': 'Keine Links ausgewählt.'}), 400

        if not custom_main_name:
            return jsonify({'status': 'error', 'message': 'Kein Name für die Hauptseite angegeben.'}), 400

        main_website_name = sanitize_filename(custom_main_name)

        # Generiere eine eindeutige Task-ID
        task_id = str(uuid.uuid4())

        # Initialisiere den Task vor dem Start des Threads
        with pdf_lock:
            pdf_tasks[task_id] = {'status': 'running', 'result': {}, 'error': None}

        # Starte den PDF-Task im Hintergrund
        threading.Thread(
            target=lambda: run_pdf_task(task_id, selected_links, main_website_name)
        ).start()
        logger.info(f"PDF-Task gestartet mit Task-ID: {task_id}")

        return jsonify({'status': 'success', 'task_id': task_id}), 200

    except Exception as e:
        logger.error(f"Fehler beim Starten des PDF-Tasks: {e}")
        return jsonify({'status': 'error', 'message': 'Fehler beim Erstellen des PDF-Tasks'}), 500


def run_pdf_task(task_id: str, urls: List[str], main_website_name: str):
    try:
        # Erstelle eine neue Event-Loop für den Thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        # Starte die Coroutine in der neuen Event-Loop
        loop.run_until_complete(_run_pdf_task(task_id, urls, main_website_name))
    except Exception as e:
        logger.error(f"Fehler bei PDF-Task {task_id}: {e}")
        with pdf_lock:
            pdf_tasks[task_id]['status'] = 'failed'
            pdf_tasks[task_id]['error'] = str(e)
    finally:
        # Schließe die Event-Loop
        loop.close()


async def _run_pdf_task(task_id: str, urls: List[str], main_website_name: str):
    try:
        pdf_converter = PDFConverter(max_concurrent_tasks=20)
        await pdf_converter.initialize()

        # Konvertiere URLs zu individuellen PDFs
        pdf_results = await pdf_converter.convert_urls_to_pdfs(urls)

        # Schließe den Browser
        await pdf_converter.close()

        # Pfad zum kombinierten PDF
        combined_pdf_filename = f"{main_website_name}_{task_id}.pdf"
        combined_pdf_path = os.path.join(OUTPUT_DIRECTORY, combined_pdf_filename)

        # Kombiniere die individuellen PDFs
        merge_pdfs_with_bookmarks(pdf_results, combined_pdf_path)

        # Erstelle ein ZIP-Archiv im ZIP_OUTPUT_DIRECTORY
        zip_filename = os.path.join(ZIP_OUTPUT_DIRECTORY, f"{main_website_name}_{task_id}.zip")
        create_zip_archive(OUTPUT_DIRECTORY, zip_filename)

        # Update Task Info
        with pdf_lock:
            pdf_tasks[task_id]['status'] = 'completed'
            pdf_tasks[task_id]['result'] = {'zip_file': zip_filename}

        logger.info(f"PDF-Task abgeschlossen: {task_id}")

        # Lösche die einzelnen PDFs, nachdem das ZIP-Archiv erstellt wurde
        clean_up_output_directory()

    except Exception as e:
        logger.error(f"Fehler bei PDF-Task {task_id}: {e}")
        with pdf_lock:
            pdf_tasks[task_id]['status'] = 'failed'
            pdf_tasks[task_id]['error'] = str(e)


@main.route('/pdf_status/<task_id>', methods=['GET'])
def pdf_status(task_id):
    with pdf_lock:
        task_info = pdf_tasks.get(task_id)
    if not task_info:
        logger.error(f"PDF Task {task_id} nicht gefunden.")
        return render_template('error.html', message='Task nicht gefunden.'), 404

    # Rendern der pdf_status.html mit Übergabe von task_id
    return render_template('pdf_status.html', task_id=task_id)


@main.route('/pdf_result/<task_id>', methods=['GET'])
def pdf_result(task_id):
    with pdf_lock:
        task_info = pdf_tasks.get(task_id)
    if not task_info or task_info['status'] != 'completed':
        return render_template('error.html', message='PDF Task nicht abgeschlossen oder nicht gefunden.'), 404

    zip_file_path = task_info['result'].get('zip_file')
    if not zip_file_path or not os.path.exists(zip_file_path):
        return render_template('error.html', message='ZIP-Datei nicht gefunden.'), 404

    # Rendern der convert_result.html mit Übergabe von task_id
    return render_template('convert_result.html', task_id=task_id)


def clean_up_output_directory():
    try:
        # Lösche alle Dateien im OUTPUT_DIRECTORY
        for root, dirs, files in os.walk(OUTPUT_DIRECTORY):
            for file in files:
                file_path = os.path.join(root, file)
                os.remove(file_path)
                logger.info(f"Gelöschte Datei: {file_path}")
        logger.info("Ausgabeverzeichnis bereinigt.")
    except Exception as e:
        logger.error(f"Fehler beim Bereinigen des Ausgabeverzeichnisses: {e}")


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
    zip_file_path = os.path.abspath(zip_file_path)
    logger.debug(f"ZIP-Dateipfad für Task {task_id}: {zip_file_path}")
    if not zip_file_path or not os.path.exists(zip_file_path):
        logger.error(f"ZIP-Datei nicht gefunden für Task {task_id}: {zip_file_path}")
        return render_template('error.html', message='ZIP-Datei nicht gefunden.'), 404

    # Optionaler Dateiname aus der Query-String
    file_name = request.args.get('file_name', os.path.basename(zip_file_path))

    # Verwenden Sie sanitize_filename aus naming_utils.py
    file_name = sanitize_filename(file_name)
    if not file_name.endswith('.zip'):
        file_name += '.zip'

    logger.info(f"Beginne Download der ZIP-Datei für Task {task_id}: {zip_file_path}")
    try:
        return send_file(
            zip_file_path,
            as_attachment=True,
            download_name=file_name,
            mimetype='application/zip'
        )
    except Exception as e:
        logger.error(f"Fehler beim Senden der ZIP-Datei für Task {task_id}: {e}")
        return render_template('error.html', message='Fehler beim Herunterladen der ZIP-Datei.'), 500


@main.route('/get_pdf_status/<task_id>', methods=['GET'])
def get_pdf_status(task_id):
    with pdf_lock:
        task_info = pdf_tasks.get(task_id)
    if not task_info:
        return jsonify({'status': 'error', 'message': 'Task nicht gefunden.'}), 404
    return jsonify({'status': task_info['status']})
