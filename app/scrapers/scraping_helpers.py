# app/scrape_helpers.py

from typing import Dict, Optional
import threading

from config import logger

# Import the configuration
from fetch_content import scrape_website

# Shared dictionary for scraping tasks
scrape_tasks: Dict[str, Dict] = {}
# Use threading.Lock for synchronous contexts
scrape_lock = threading.Lock()


async def run_scrape_task(task_id: str, url: str):
    """
    Performs scraping for the given URL and updates the task status.

    :param task_id: Unique ID for the scraping task
    :param url: URL to be scraped
    """
    try:
        logger.info(f"Starting scraping for Task ID: {task_id}, URL: {url}")

        # Use fetch_content.py's scrape_website function
        result = await scrape_website(url, max_depth=2, max_concurrency=20, use_cache=True)

        # Check if an error occurred
        if 'error' in result:
            error_message = result['error']
            logger.error(f"Error during scraping for Task ID: {task_id}: {error_message}")
            with scrape_lock:
                scrape_tasks[task_id] = {
                    'status': 'failed',
                    'error': error_message
                }
        else:
            url_mapping = result['url_mapping']
            base_page_id = result['base_page_id']

            # Update the task status safely
            with scrape_lock:
                scrape_tasks[task_id] = {
                    'status': 'completed',
                    'result': {
                        'url_mapping': url_mapping,
                        'base_page_id': base_page_id
                    }
                }

            logger.info(f"Scraping completed for Task ID: {task_id}")

    except Exception as e:
        logger.error(f"Error during scraping for Task ID: {task_id}: {e}")
        with scrape_lock:
            scrape_tasks[task_id] = {
                'status': 'failed',
                'error': str(e)
            }
        raise e  # To handle the error in routes.py


def render_links_recursive(url_mapping: Dict[str, Dict], page_id: Optional[str] = None, level: int = 0) -> str:
    """
    Creates a recursive HTML representation of links based on the URL mapping structure.

    :param url_mapping: Dictionary with URL mappings
    :param page_id: ID of the current page
    :param level: Recursion depth
    :return: HTML string of the links
    """
    html = ""
    indent = "    " * level  # Indentation for readability

    if page_id is None:
        # If no page_id is given, start with root pages (without parent_id)
        root_pages = [pid for pid, pdata in url_mapping.items() if pdata.get('parent_id') is None]
        for pid in root_pages:
            html += render_links_recursive(url_mapping, page_id=pid, level=level)
        return html

    page_data = url_mapping.get(page_id)
    if not page_data:
        return ""

    title = page_data.get('title', 'No Title')
    url = page_data.get('url', '#')

    # Generate HTML for the current page
    html += f"""
{indent}<tr class="level-{level}">
{indent}    <td>
{indent}        <span class="toggle-btn-label" data-page-id="{page_id}" role="button" aria-expanded="false" aria-controls="child-{page_id}"></span>
{indent}        <a href="{url}" class="toggle-link" data-page-id="{page_id}" data-title="{title}" data-url="{url}">{title}</a>
{indent}    </td>
{indent}    <td>
{indent}        <input type="checkbox" name="selected_links" value="{url}">
{indent}    </td>
{indent}</tr>
"""

    # Process the children of the current page
    children = page_data.get('children', [])
    for child_id in children:
        html += render_links_recursive(url_mapping, page_id=child_id, level=level + 1)

    return html
