# app/processing/utils.py

import os
import logging

logger = logging.getLogger("utils_logger")

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
