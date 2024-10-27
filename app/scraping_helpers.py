# app/scraping_helpers.py

import asyncio
import threading
import logging
import time
import hashlib
import os
import json

from app.scrapers.fetch_content import scrape_website
from config import MAPPING_DIR, logger

# Fortschrittsverfolgung
# Gemeinsames Dictionary für Scraping-Tasks (optional, je nach Anwendung)
scrape_tasks = {}
scrape_lock = asyncio.Lock()

def run_scrape_task(task_id, url):
    try:
        # Aktualisieren Sie den Task-Status auf 'running'
        with scrape_lock:
            scrape_tasks[task_id] = {'status': 'running', 'result': {}}

        # Führen Sie das Scraping asynchron durch
        result = asyncio.run(scrape_website(url))

        url_mapping = result['url_mapping']

        # Speichern Sie das Ergebnis
        cache_filepath = os.path.join(MAPPING_DIR, f"{task_id}.json")
        with open(cache_filepath, 'w', encoding='utf-8') as f:
            json.dump(url_mapping, f)

        # Aktualisieren Sie den Task-Status auf 'completed'
        with scrape_lock:
            scrape_tasks[task_id]['status'] = 'completed'
            scrape_tasks[task_id]['result'] = {'url_mapping': url_mapping}

        logger.info(f"Scraping abgeschlossen für Task {task_id}")
    except Exception as e:
        logger.error(f"Fehler beim Scraping für Task {task_id}: {e}", exc_info=True)
        with scrape_lock:
            scrape_tasks[task_id]['status'] = 'failed'
            scrape_tasks[task_id]['error'] = str(e)

def render_links_recursive(url_mapping, parent_id=None, rendered_ids=None):
    if rendered_ids is None:
        rendered_ids = set()

    html_output = ""

    for page_id, page_data in url_mapping.items():
        if page_id in rendered_ids:
            continue  # Vermeide Duplikate

        if page_data.get("parent_id") == parent_id:
            rendered_ids.add(page_id)
            has_children = len(page_data.get('children', [])) > 0

            # Toggle Icon
            if has_children:
                toggle_icon = '<i class="fas fa-plus-square toggle-icon"></i>'
            else:
                toggle_icon = '<i class="fas fa-square"></i>'

            # Anzahl direkter Kinder
            num_direct_children = len(page_data.get('children', []))

            # Beginne Listenelement
            html_output += '<li>'
            html_output += f'''
                {toggle_icon}
                <a href="{page_data["url"]}" class="link-item" target="_blank">{page_data["title"]}</a>
                <input type="checkbox" class="link-checkbox" data-url="{page_data["url"]}" data-title="{page_data["title"]}">
                <span class="child-count">({num_direct_children})</span>
            '''

            # Rekursives Rendern der Kind-Links
            if has_children:
                child_html = render_links_recursive(
                    url_mapping,
                    parent_id=page_id,
                    rendered_ids=rendered_ids
                )
                html_output += f'<ul>{child_html}</ul>'
            html_output += '</li>'

    return html_output
