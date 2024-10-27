# app/routes/scrape_views.py

import os
import json
import time
import asyncio
import threading
import hashlib
import logging
from flask import request, render_template, redirect, url_for, jsonify, flash

from app.scrapers.scraping_helpers import (
    scrape_lock, scrape_tasks, run_scrape_task, render_links_recursive
)
from config import MAPPING_DIR

from . import main

logger = logging.getLogger(__name__)

@main.route('/scrape_links', methods=['POST'])
def scrape_links():
    url = request.form.get('url')
    logger.info(f"Scrape-Anfrage erhalten für URL: {url}")

    if not url:
        flash('Keine URL angegeben.', 'error')
        return redirect(url_for('main.index'))

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
                    'result': {'url_mapping': cached_url_mapping},
                    'error': None
                }
            # Weiterleitung zur Ergebnisanzeige
            return redirect(url_for('main.scrape_result', task_id=task_id))

        else:
            # Starte das Scraping im Hintergrund in einem neuen Thread
            threading.Thread(
                target=lambda: asyncio.run(run_scrape_task(task_id, url))
            ).start()
            logger.info(f"Keine gecachte Datei gefunden. Scraping gestartet für URL: {url}")

            # Weiterleitung zu einer Status-Seite, während das Scraping läuft
            return redirect(url_for('main.scrape_status', task_id=task_id))

    except Exception as e:
        logger.error(f"Fehler beim Starten des Scrapings: {e}", exc_info=True)
        return render_template('error.html', message=str(e)), 500


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
    }

    logger.debug(f"Task {task_id} Status: {response_data}")
    return jsonify(response_data)


@main.route('/scrape_result/<task_id>', methods=['GET'])
def scrape_result(task_id):
    version = str(int(time.time()))  # Zeitstempel für Caching

    with scrape_lock:
        task_info = scrape_tasks.get(task_id)

    if not task_info:
        logger.error(f"Task {task_id} nicht gefunden.")
        return render_template('error.html', message='Task nicht gefunden.'), 404

    if task_info['status'] == 'failed':
        error_message = task_info.get('error', 'Unbekannter Fehler.')
        logger.error(f"Task {task_id} fehlgeschlagen: {error_message}")
        return render_template('error.html', message=error_message), 500

    if task_info['status'] != 'completed':
        return redirect(url_for('main.scrape_status', task_id=task_id))

    # Überprüfe, ob url_mapping vorhanden ist
    url_mapping = task_info['result'].get('url_mapping', {})
    if not url_mapping:
        logger.error(f"URL Mapping nicht vorhanden für Task {task_id}")
        return render_template('error.html', message='Keine Daten gefunden.'), 404

    # Extrahiere den Hauptlink (erste Seite im Mapping)
    main_link_id = next(iter(url_mapping), None)
    if main_link_id:
        main_link_title = url_mapping[main_link_id].get('title', 'Kein Titel')
        main_link_url = url_mapping[main_link_id].get('url', '#')
    else:
        main_link_title = 'Kein Hauptlink'
        main_link_url = '#'

    # Definieren Sie submitted_url basierend auf main_link_url
    submitted_url = main_link_url

    # Erzeuge die Baumstruktur für das Template
    tree_html = render_links_recursive(url_mapping)

    return render_template(
        'scrape_result.html',
        tree_html=tree_html,
        url_mapping=url_mapping,
        version=version,
        main_link_title=main_link_title,
        main_link_url=main_link_url,
        submitted_url=submitted_url  # Übergeben der submitted_url
    )
