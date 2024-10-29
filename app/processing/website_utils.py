# app/processing/utils.py

import os
import logging
from typing import List
from urllib.parse import urlparse
import hashlib
import asyncio

from playwright.async_api import Page

from config import logger


# ======================= Hilfsfunktionen =======================


def extract_domain(url: str) -> str:
    """Extrahiert den Domain-Namen ohne 'www' und TLD."""
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    if domain.startswith('www.'):
        domain = domain[4:]
    domain_main = domain.split('.')[0]
    logger.debug(f"Extracted Domain: {domain_main}")
    return domain_main

def get_url(json_daten=None, eigene_urls=None) -> str:
    """
    Wählt eine zufällige URL aus einer Liste von URLs aus.

    :param json_daten: Ein JSON-Objekt mit einem Schlüssel "links", der eine Liste von URLs enthält.
    :param eigene_urls: Eine eigene Liste von URLs, die verwendet werden soll.
    :return: Eine zufällige URL als String.
    """
    if eigene_urls:
        urls = eigene_urls
    elif json_daten and "links" in json_daten:
        urls = json_daten["links"]
    else:
        # Standard-URLs, falls keine Eingabe erfolgt
        urls = [
            "https://www.zh.ch/de/staatskanzlei/regierungskommunikation.html",
            "https://www.zh.ch/de/wirtschaft-arbeit/handelsregister.html",
            "https://www.zh.ch/de/arbeiten-beim-kanton.html"
        ]

    if not urls:
        raise ValueError("Die URL-Liste ist leer.")

    import random
    return random.choice(urls)




def setup_directories(OUTPUT_PDFS_DIR: str):
    """
    Richtet die erforderlichen Ausgabe-Verzeichnisse ein.
    """
    os.makedirs(OUTPUT_PDFS_DIR, exist_ok=True)
    individual_collapsed = os.path.join(OUTPUT_PDFS_DIR, 'individual_pdfs_collapsed')
    individual_expanded = os.path.join(OUTPUT_PDFS_DIR, 'individual_pdfs_expanded')
    os.makedirs(individual_collapsed, exist_ok=True)
    os.makedirs(individual_expanded, exist_ok=True)
    logger.info(f"Ausgabe-Verzeichnisse eingerichtet: {individual_collapsed}, {individual_expanded}")


def load_js_file(file_path: str) -> str:
    """
    Lädt den Inhalt eines JS-Files und gibt ihn als String zurück.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            js_content = file.read()
        logger.debug(f"JS-Datei erfolgreich geladen: {file_path}")
        return js_content
    except FileNotFoundError:
        logger.error(f"JS-Datei nicht gefunden: {file_path}")
        return ""
    except Exception as e:
        logger.error(f"Fehler beim Laden der JS-Datei {file_path}: {e}")
        return ""


async def inject_custom_css(page: Page, expanded: bool = False):
    """Fügt benutzerdefiniertes CSS in die Seite ein."""
    try:
        if expanded:
            css = '''
                /* Verstecke Navbar und Sidebar */
                header, nav, .sidebar, #navigation, .mdl-anchornav, #header, .mdl-header, #toc, .mdl-footer, #footer {
                    display: none !important;
                }
                /* Passe die Seitenbreite an */
                body {
                    margin: 0 auto;
                    width: 100%;
                }
                /* Weitere CSS-Anpassungen für ein sauberes Layout */
                .lyt-wrapper {
                    max-width: 100% !important;
                    padding: 0 !important;
                }
            '''
            await page.add_style_tag(content=css)
            logger.debug("Benutzerdefiniertes CSS für expanded Modus eingefügt.")
        else:
            # Benutzerdefiniertes CSS für collapsed Modus, falls benötigt
            css = '''
                /* Optional: CSS für collapsed Modus */
                body {
                    margin: 0 auto;
                    width: 100%;
                }
                /* Weitere Anpassungen für collapsed Modus */
            '''
            await page.add_style_tag(content=css)
            logger.debug("Benutzerdefiniertes CSS für collapsed Modus eingefügt.")
    except Exception as e:
        logger.error(f"Fehler beim Einfügen von benutzerdefiniertem CSS: {e}")

# ======================= Haupttestfunktion =======================


