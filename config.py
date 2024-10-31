# config.py

import os
import json
from pathlib import Path
import logging
from dotenv import load_dotenv
import socket
import psutil
import multiprocessing
import sys
from colorama import init, Fore, Style

# Initialisiere colorama
init(autoreset=True)

# Lade die .env Datei
load_dotenv()

# Prüfen, ob die Anwendung auf Heroku läuft
IS_HEROKU = os.getenv('IS_HEROKU', 'False').lower() in ['true', '1', 't']

def get_base_dir():
    # Bestimmt das Basisverzeichnis des Skripts
    return os.path.dirname(os.path.abspath(__file__))

# Basisverzeichnis festlegen
if IS_HEROKU:
    # Verwende das temporäre Verzeichnis auf Heroku
    BASE_DIR = Path('/tmp')
else:
    # Verwende das Basisverzeichnis des Skripts
    BASE_DIR = Path(get_base_dir())

# App-Verzeichnis
APP_DIR = BASE_DIR / os.getenv('APP_DIR', 'app')

# Static-Verzeichnis innerhalb der App
STATIC_DIR = APP_DIR / os.getenv('STATIC_DIR', 'static')

# Weitere Verzeichnisse innerhalb Static
CSS_DIR = STATIC_DIR / os.getenv('CSS_DIR', 'css')
IMG_DIR = STATIC_DIR / os.getenv('IMG_DIR', 'img')
JS_DIR = STATIC_DIR / os.getenv('JS_DIR', 'js')
JSON_DIR = STATIC_DIR / os.getenv('JSON_DIR', 'json')
TEMPLATES_DIR = APP_DIR / os.getenv('TEMPLATES_DIR', 'templates')
UTILS_DIR = APP_DIR / os.getenv('UTILS_DIR', 'utils')

# Cache-Verzeichnisse
CACHE_DIR = STATIC_DIR / os.getenv('CACHE_DIR', 'cache')
MAPPING_CACHE_DIR = CACHE_DIR / os.getenv('MAPPING_CACHE_DIR', 'mapping_cache')

# Logs-Verzeichnis
LOGS_DIR = BASE_DIR / os.getenv('LOGS_DIR', 'logs')

# Output PDFs-Verzeichnis
OUTPUT_PDFS_DIR = BASE_DIR / os.getenv('OUTPUT_PDFS_DIR', 'output_pdfs')

# Pfade zu spezifischen Dateien
OUTPUT_MAPPING_PATH = CACHE_DIR / os.getenv('OUTPUT_MAPPING_PATH', 'output_mapping.json')
TABOO_JSON_PATH = JSON_DIR / os.getenv('TABOO_JSON_FILE', 'taboo.json')
COOKIES_SELECTOR_JSON_PATH = JSON_DIR / os.getenv('COOKIES_SELECTOR_JSON_FILE', 'cookies_selector.json')
EXCLUDE_SELECTORS_JSON_PATH = JSON_DIR / os.getenv('EXCLUDE_SELECTORS_JSON_FILE', 'exclude_selectors.json')
URLS_JSON_PATH = JSON_DIR / os.getenv('URLS_JSON_FILE', 'urls.json')

# Zusätzliche Verzeichnisse für Remove Elements Konfiguration
REMOVE_ELEMENTS_CONFIG_DIR = JSON_DIR / 'remove_elements'
ELEMENTS_COLLAPSED_CONFIG = REMOVE_ELEMENTS_CONFIG_DIR / 'elements_collapsed.json'
ELEMENTS_EXPANDED_CONFIG = REMOVE_ELEMENTS_CONFIG_DIR / 'elements_expanded.json'

# Einstellungen
DEFAULT_MAX_WORKERS = int(os.getenv('DEFAULT_MAX_WORKERS', '4'))
LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG').upper()
ENABLE_LOGGING = os.getenv('ENABLE_LOGGING', 'True').lower() in ['true', '1', 't']

# Logging-Konfiguration
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL, logging.DEBUG))

# Handler für die Konsole mit Farbcodes
console_handler = logging.StreamHandler()
console_handler.setLevel(getattr(logging, LOG_LEVEL, logging.DEBUG))

# Verwende das Logs-Verzeichnis im /tmp-Verzeichnis auf Heroku
if IS_HEROKU:
    file_handler = logging.FileHandler('/tmp/app.log')
else:
    file_handler = logging.FileHandler(LOGS_DIR / 'app.log')
file_handler.setLevel(getattr(logging, LOG_LEVEL, logging.DEBUG))

# Formatter ohne Farbcodes für die Datei
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

# Funktion zur farbcodierten Formatierung basierend auf Log-Level
class ColorFormatter(logging.Formatter):
    LEVEL_COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.MAGENTA
    }

    def format(self, record):
        color = self.LEVEL_COLORS.get(record.levelno, Fore.WHITE)
        message = super().format(record)
        return f"{color}{message}{Style.RESET_ALL}"

# Formatter mit Farbcodes für die Konsole
console_formatter = ColorFormatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

# Logging nur aktivieren, wenn ENABLE_LOGGING True ist
if ENABLE_LOGGING:
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
else:
    # Wenn Logging deaktiviert ist, verwende einen NullHandler
    logger.addHandler(logging.NullHandler())

logger.debug("Konfiguration geladen und Logger eingerichtet.")

# Sicherstellen, dass alle wichtigen Verzeichnisse existieren
directories = [
    MAPPING_CACHE_DIR,
    LOGS_DIR,
    OUTPUT_PDFS_DIR,
    CSS_DIR,
    IMG_DIR,
    JS_DIR,
    JSON_DIR,
    TEMPLATES_DIR,
    UTILS_DIR,
    CACHE_DIR,
    REMOVE_ELEMENTS_CONFIG_DIR,
]

# Überprüfung der Verzeichnisse
def ensure_directories_exist(directories):
    all_exist = True
    for directory in directories:
        if not directory.exists():
            logger.error(f"{Fore.RED}Verzeichnis fehlt: {directory}{Style.RESET_ALL}")
            try:
                directory.mkdir(parents=True, exist_ok=True)
                logger.info(f"{Fore.GREEN}Verzeichnis erstellt: {directory}{Style.RESET_ALL}")
                all_exist = False
            except Exception as e:
                logger.error(f"Fehler beim Erstellen des Verzeichnisses {directory}: {e}")
                all_exist = False
        else:
            logger.info(f"{Fore.GREEN}Verzeichnis existiert bereits: {directory}{Style.RESET_ALL}")
    return all_exist

# Verzeichnisse sicherstellen
if ensure_directories_exist(directories):
    logger.info(f"{Fore.GREEN}All ready.{Style.RESET_ALL}")
else:
    logger.warning(f"{Fore.YELLOW}Setup started.{Style.RESET_ALL}")

# Rest Ihres Codes bleibt unverändert
