# app/scraping_helpers.py

import json
import os
from typing import Dict, Any
import threading
from collections import defaultdict

from config import logger, MAPPING_CACHE_DIR, CACHE_DIR, OUTPUT_MAPPING_PATH

from app.scrapers.fetch_content import scrape_website

# Shared dictionary for scraping tasks
scrape_tasks: Dict[str, Dict] = {}
# Use threading.Lock for synchronous contexts
scrape_lock = threading.Lock()


def remove_duplicate_links_per_level(url_mapping: Dict[str, Any], base_page_id: str = None) -> Dict[str, Any]:
    if not base_page_id:
        base_page_id = next(iter(url_mapping))

    seen_urls_per_level = defaultdict(set)
    cleaned_url_mapping = {}
    visited_pages = set()

    def clean_node(page_id, level):
        if page_id in visited_pages:
            logger.debug(f"Already visited page_id {page_id}, skipping to prevent infinite recursion.")
            return
        visited_pages.add(page_id)

        page = url_mapping.get(page_id, {})
        url = page.get('url', '#')

        if url in seen_urls_per_level[level]:
            logger.debug(f"Duplicate URL '{url}' found at level {level}, skipping.")
            return
        seen_urls_per_level[level].add(url)

        cleaned_url_mapping[page_id] = page

        for child_id in page.get('children', []):
            clean_node(child_id, level + 1)

    clean_node(base_page_id, 0)
    return cleaned_url_mapping


async def run_scrape_task(task_id: str, url: str):
    with scrape_lock:
        scrape_tasks[task_id] = {'status': 'running', 'result': {}, 'error': None}

    try:
        logger.info(f"Starting scrape task {task_id} for URL: {url}")

        result = await scrape_website(url)

        if not result or not result.get('url_mapping'):
            logger.error(f"Scrape task {task_id} returned no data.")
            with scrape_lock:
                scrape_tasks[task_id]['status'] = 'failed'
                scrape_tasks[task_id]['error'] = 'No data returned from scrape_website.'
            return

        base_page_id = result.get('base_page_id')
        cleaned_url_mapping = remove_duplicate_links_per_level(result['url_mapping'], base_page_id)

        # Sicherstellen, dass das Cache-Verzeichnis existiert
        MAPPING_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Cache directory ensured: {MAPPING_CACHE_DIR}")

        # Ergebnis in einer individuellen Cache-Datei speichern
        cache_filename = f"{task_id}.json"
        cache_file_path = MAPPING_CACHE_DIR / cache_filename
        logger.debug(f"Saving individual cache to: {cache_file_path}")

        with open(cache_file_path, 'w', encoding='utf-8') as f:
            json.dump({'url_mapping': cleaned_url_mapping, 'base_page_id': base_page_id}, f, ensure_ascii=False,
                      indent=4)
            logger.info(f"Individual cache saved for task {task_id}")

        # Ergebnis in 'output_mapping.json' speichern
        logger.debug(f"Saving combined output to: {OUTPUT_MAPPING_PATH}")

        with open(OUTPUT_MAPPING_PATH, 'w', encoding='utf-8') as f:
            json.dump(cleaned_url_mapping, f, ensure_ascii=False, indent=4)
            logger.info(f"Combined output saved in {OUTPUT_MAPPING_PATH}")

        with scrape_lock:
            scrape_tasks[task_id]['status'] = 'completed'
            scrape_tasks[task_id]['result'] = {'url_mapping': cleaned_url_mapping, 'base_page_id': base_page_id}

        logger.info(f"Scrape task {task_id} completed successfully.")

    except Exception as e:
        logger.error(f"Error during scraping task {task_id}: {e}", exc_info=True)
        with scrape_lock:
            scrape_tasks[task_id]['status'] = 'failed'
            scrape_tasks[task_id]['error'] = str(e)


def render_links_recursive(url_mapping: Dict[str, Any], base_page_id: str = None) -> str:
    if not base_page_id:
        base_page_id = next(iter(url_mapping))

    visited_pages = set()
    seen_urls_per_level = defaultdict(set)

    def render_node(page_id, level):
        if page_id in visited_pages:
            logger.debug(f"Already visited page_id {page_id}, skipping to prevent infinite recursion.")
            return ''
        visited_pages.add(page_id)

        page = url_mapping.get(page_id, {})
        title = page.get('title', 'No Title')
        url = page.get('url', '#')

        if url in seen_urls_per_level[level]:
            logger.debug(f"Duplicate URL '{url}' found at level {level}, skipping.")
            return ''
        seen_urls_per_level[level].add(url)

        children_html = ''

        for child_id in page.get('children', []):
            children_html += render_node(child_id, level + 1)

        checked_attribute = 'checked' if page_id == base_page_id else ''

        return f"""
        <li>
            <input type="checkbox" id="{page_id}" name="selected_links" value="{url}" {checked_attribute}>
            <label for="{page_id}">{title}</label>
            {f'<ul>{children_html}</ul>' if children_html else ''}
        </li>
        """

    html_content = render_node(base_page_id, 0)
    return f"<ul>{html_content}</ul>"
