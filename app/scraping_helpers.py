# app/scraping_helpers.py

import asyncio
import logging
from typing import Dict, List, Optional
import aiohttp
from bs4 import BeautifulSoup
import threading

logger = logging.getLogger(__name__)

# Gemeinsames Dictionary für Scraping-Tasks
scrape_tasks: Dict[str, Dict] = {}
# Verwende threading.Lock für synchrone Kontexte
scrape_lock = threading.Lock()


async def run_scrape_task(task_id: str, url: str):
    """
    Führt das Scraping für die gegebene URL aus und aktualisiert den Task-Status.

    :param task_id: Eindeutige ID für den Scraping-Task
    :param url: URL, die gescraped werden soll
    """
    try:
        logger.info(f"Starte Scraping für Task ID: {task_id}, URL: {url}")
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"HTTP-Status {response.status} beim Abrufen der URL")
                html = await response.text()

        soup = BeautifulSoup(html, 'html.parser')
        # Beispiel: Extrahiere alle Links der ersten Ebene
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            title = link.get_text(strip=True) or href
            # Normalisiere die URL, falls nötig
            href = normalize_url(url, href)
            links.append({'url': href, 'title': title, 'level': 1, 'children': []})

        # Erstelle eine URL-Mapping-Struktur
        url_mapping = {}
        for idx, link in enumerate(links):
            page_id = f"page_{idx}"
            url_mapping[page_id] = link

        # Aktualisiere den Task-Status sicher
        with scrape_lock:
            scrape_tasks[task_id] = {
                'status': 'completed',
                'result': {'url_mapping': url_mapping}
            }

        logger.info(f"Scraping abgeschlossen für Task ID: {task_id}")
    except Exception as e:
        logger.error(f"Fehler beim Scraping für Task ID: {task_id}: {e}")
        with scrape_lock:
            scrape_tasks[task_id] = {
                'status': 'failed',
                'error': str(e)
            }
        raise e  # Damit der Fehler in routes.py behandelt werden kann


def normalize_url(base_url: str, link: str) -> str:
    """
    Normalisiert relative URLs zu absoluten URLs basierend auf der Basis-URL.

    :param base_url: Basis-URL der gescrapten Seite
    :param link: Gefundener Link, der normalisiert werden soll
    :return: Normalisierte absolute URL
    """
    from urllib.parse import urljoin
    return urljoin(base_url, link)


def render_links_recursive(url_mapping: Dict[str, Dict], parent_id: Optional[str] = None) -> str:
    """
    Erstellt eine rekursive HTML-Darstellung der Links basierend auf der URL-Mapping-Struktur.

    :param url_mapping: Dictionary mit URL-Mappings
    :param parent_id: ID des übergeordneten Links (für rekursive Aufrufe)
    :return: HTML-String der Links
    """
    html = ""
    # Finde alle Links, die zu diesem Parent gehören
    for page_id, page_data in url_mapping.items():
        if parent_id is None and page_data['level'] == 1:
            # Hauptlinks
            html += f"""
            <tr class="parent-row">
                <td>
                    <span class="toggle-btn-label" data-page-id="{page_id}" role="button" aria-expanded="false" aria-controls="child-{page_id}"></span>
                    <a href="{page_data['url']}" class="toggle-link" data-page-id="{page_id}" data-title="{page_data['title']}" data-url="{page_data['url']}">{page_data['title']}</a>
                </td>
                <td>
                    <input type="checkbox" name="selected_links" value="{page_data['url']}"
                        {"checked disabled" if page_data['url'] == url_mapping.get('main_link_url', '#') else ""}>
                </td>
            </tr>
            """
            # Suche nach Kindern dieses Links
            children = find_children(url_mapping, page_id)
            for child_id in children:
                child_data = url_mapping.get(child_id)
                if child_data:
                    html += f"""
                    <tr class="child-row child-of-{page_id}" id="child-{page_id}" style="display: none;">
                        <td style="padding-left: 40px;">
                            <a href="{child_data['url']}" class="toggle-link" data-page-id="{page_id}" data-title="{child_data['title']}" data-url="{child_data['url']}">{child_data['title']}</a>
                        </td>
                        <td><input type="checkbox" name="selected_links" value="{child_data['url']}"></td>
                    </tr>
                    """
    return html


def find_children(url_mapping: Dict[str, Dict], parent_id: str) -> List[str]:
    """
    Findet alle Kinder eines gegebenen Elternteils.

    :param url_mapping: Dictionary mit URL-Mappings
    :param parent_id: ID des Elternteils
    :return: Liste der Kinder-IDs
    """
    children = []
    for page_id, page_data in url_mapping.items():
        # Beispiel: Annahme, dass 'children' eine Liste von IDs ist
        if 'children' in page_data and parent_id in page_data['children']:
            children.append(page_id)
    return children
