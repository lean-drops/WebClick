import asyncio
import time
import hashlib
import os
import json

import aiofiles

from app.scrapers.fetch_content import scrape_website
from config import MAPPING_DIR, logger

# Fortschrittsverfolgung
scrape_tasks = {}
scrape_lock = asyncio.Lock()


async def run_scrape_task(task_id, url):
    try:
        start_time = time.time()
        async with scrape_lock:
            scrape_tasks[task_id] = {'status': 'running'}  # Setze Status auf "running"

        # Führe das Scraping durch
        result = await scrape_website(
            url, max_depth=2, max_concurrency=500, use_cache=True
        )
        elapsed_time = time.time() - start_time

        # Cache speichern
        cache_filename = hashlib.md5(url.encode()).hexdigest() + ".json"
        cache_filepath = os.path.join(MAPPING_DIR, cache_filename)

        # Stelle sicher, dass das Verzeichnis existiert
        os.makedirs(os.path.dirname(cache_filepath), exist_ok=True)

        async with aiofiles.open(cache_filepath, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(result['url_mapping']))

        # Ergebnisse speichern und Fortschritt aktualisieren
        async with scrape_lock:
            scrape_tasks[task_id].update({
                'status': 'completed',
                'result': result,
                'num_pages': len(result['url_mapping']),
                'elapsed_time': elapsed_time,
                'time_per_page': elapsed_time / len(result['url_mapping'])
                if len(result['url_mapping']) > 0 else 0
            })
        logger.info(f"Scraping erfolgreich für {result['url']}")

    except Exception as e:
        logger.error(f"Fehler beim Scrapen der Website: {e}", exc_info=True)
        async with scrape_lock:
            scrape_tasks[task_id] = {'status': 'failed', 'error': str(e)}


def render_links_recursive(url_mapping, parent_id=None, rendered_ids=None):
    if rendered_ids is None:
        rendered_ids = set()

    html_output = ""

    for page_id, page_data in url_mapping.items():
        if page_id in rendered_ids:
            continue  # Avoid duplicates

        if page_data.get("parent_id") == parent_id:
            rendered_ids.add(page_id)
            has_children = len(page_data.get('children', [])) > 0

            # Toggle icon
            if has_children:
                toggle_icon = '<i class="fas fa-plus-square toggle-icon"></i>'
            else:
                toggle_icon = '<i class="fas fa-square"></i>'

            # Count direct children only
            num_direct_children = len(page_data.get('children', []))

            # Start list item
            html_output += '<li>'
            html_output += f'''
                {toggle_icon}
                <a href="{page_data["url"]}" class="link-item" target="_blank">{page_data["title"]}</a>
                <input type="checkbox" class="link-checkbox" data-url="{page_data["url"]}" data-title="{page_data["title"]}">
                <span class="child-count">({num_direct_children})</span>
            '''

            # Recursively render child links
            if has_children:
                child_html = render_links_recursive(
                    url_mapping,
                    parent_id=page_id,
                    rendered_ids=rendered_ids
                )
                html_output += f'<ul>{child_html}</ul>'
            html_output += '</li>'

    return html_output
