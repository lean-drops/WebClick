# app/scrape_helpers.py
import json
import os
from typing import Dict, Optional, Any
import threading

from config import logger, MAPPING_DIR

# Import the configuration
from app.scrapers.fetch_content import scrape_website

# Shared dictionary for scraping tasks
scrape_tasks: Dict[str, Dict] = {}
# Use threading.Lock for synchronous contexts
scrape_lock = threading.Lock()


# app/scrapers/scraping_helpers.py

async def run_scrape_task(task_id: str, url: str):
    with scrape_lock:
        scrape_tasks[task_id] = {'status': 'running', 'result': {}, 'error': None}

    try:
        logger.info(f"Starting scrape task {task_id} for URL: {url}")

        result = await scrape_website(url)

        # Save result to cache (include both 'url_mapping' and 'base_page_id')
        cache_filename = f"{task_id}.json"
        cache_filepath = os.path.join(MAPPING_DIR, cache_filename)
        with open(cache_filepath, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)

        with scrape_lock:
            scrape_tasks[task_id]['status'] = 'completed'
            scrape_tasks[task_id]['result'] = result

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

    def render_node(page_id):
        if page_id in visited_pages:

            logger.debug(f"Already visited page_id {page_id}, skipping to prevent infinite recursion.")
            return ''
        visited_pages.add(page_id)

        page = url_mapping.get(page_id, {})
        title = page.get('title', 'No Title')
        url = page.get('url', '#')
        children_html = ''

        for child_id in page.get('children', []):
            children_html += render_node(child_id)

        checked_attribute = 'checked' if page_id == base_page_id else ''

        return f"""
        <li>
            <input type="checkbox" id="{page_id}" name="selected_links" value="{url}" {checked_attribute}>
            <label for="{page_id}">{title}</label>
            <ul>{children_html}</ul>
        </li>
        """

    html_content = render_node(base_page_id)
    return f"<ul>{html_content}</ul>"
