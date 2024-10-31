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
BASE_DIR = Path(get_base_dir())

# App-Verzeichnis
APP_DIR = BASE_DIR / os.getenv('APP_DIR', 'app')

# Config-Verzeichnis (für die JSON-Dateien)
CONFIG_DIR = APP_DIR / os.getenv('CONFIG_DIR', 'config')

# Static-Verzeichnis innerhalb der App (nur für statische Assets)
STATIC_DIR = APP_DIR / os.getenv('STATIC_DIR', 'static')

# Weitere Verzeichnisse innerhalb Static
CSS_DIR = STATIC_DIR / os.getenv('CSS_DIR', 'css')
IMG_DIR = STATIC_DIR / os.getenv('IMG_DIR', 'img')
JS_DIR = STATIC_DIR / os.getenv('JS_DIR', 'js')

# Templates und Utils Verzeichnisse
TEMPLATES_DIR = APP_DIR / os.getenv('TEMPLATES_DIR', 'templates')
UTILS_DIR = APP_DIR / os.getenv('UTILS_DIR', 'utils')

# Cache-Verzeichnisse
if IS_HEROKU:
    CACHE_DIR = Path('/tmp') / os.getenv('CACHE_DIR', 'cache')
    LOGS_DIR = Path('/tmp') / os.getenv('LOGS_DIR', 'logs')
else:
    CACHE_DIR = BASE_DIR / os.getenv('CACHE_DIR', 'cache')
    LOGS_DIR = BASE_DIR / os.getenv('LOGS_DIR', 'logs')

MAPPING_CACHE_DIR = CACHE_DIR / os.getenv('MAPPING_CACHE_DIR', 'mapping_cache')
MAPPING_CACHE_FILE = os.getenv('MAPPING_CACHE_FILE', 'output_mapping.json')  # Nur der Dateiname

# Output PDFs-Verzeichnis
OUTPUT_PDFS_DIR = BASE_DIR / os.getenv('OUTPUT_PDFS_DIR', 'output_pdfs')

# Pfade zu spezifischen Dateien im CONFIG_DIR
TABOO_JSON_PATH = CONFIG_DIR / os.getenv('TABOO_JSON_FILE', 'taboo.json')
COOKIES_SELECTOR_JSON_PATH = CONFIG_DIR / os.getenv('COOKIES_SELECTOR_JSON_FILE', 'cookies_selector.json')
EXCLUDE_SELECTORS_JSON_PATH = CONFIG_DIR / os.getenv('EXCLUDE_SELECTORS_JSON_FILE', 'exclude_selectors.json')
URLS_JSON_PATH = CONFIG_DIR / os.getenv('URLS_JSON_FILE', 'urls.json')

# Zusätzliche Verzeichnisse für Remove Elements Konfiguration
REMOVE_ELEMENTS_CONFIG_DIR = CONFIG_DIR / 'remove_elements'
ELEMENTS_COLLAPSED_CONFIG = REMOVE_ELEMENTS_CONFIG_DIR / 'elements_collapsed.json'
ELEMENTS_EXPANDED_CONFIG = REMOVE_ELEMENTS_CONFIG_DIR / 'elements_expanded.json'

# Pfad zur Output Mapping Datei
OUTPUT_MAPPING_PATH = CACHE_DIR / MAPPING_CACHE_FILE

# Einstellungen
DEFAULT_MAX_WORKERS = int(os.getenv('MAX_WORKERS', '4'))
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
    TEMPLATES_DIR,
    UTILS_DIR,
    CACHE_DIR,
    CONFIG_DIR,  # Config-Verzeichnis hinzugefügt
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

# Pfade zu spezifischen Dateien
files = [
    OUTPUT_MAPPING_PATH,
    TABOO_JSON_PATH,
    COOKIES_SELECTOR_JSON_PATH,
    EXCLUDE_SELECTORS_JSON_PATH,
    URLS_JSON_PATH,
    ELEMENTS_COLLAPSED_CONFIG,
    ELEMENTS_EXPANDED_CONFIG,
]

# Überprüfung der Dateien
def ensure_files_exist(files):
    all_exist = True
    for file in files:
        if not file.exists():
            if file == OUTPUT_MAPPING_PATH:
                try:
                    # Erstelle eine leere JSON-Datei
                    with open(file, 'w') as f:
                        json.dump({}, f, indent=4)
                    logger.info(f"{Fore.GREEN}Erstellte leere Datei: {file}{Style.RESET_ALL}")
                except Exception as e:
                    logger.error(f"Fehler beim Erstellen der Datei {file}: {e}")
                    all_exist = False
            else:
                logger.error(f"{Fore.RED}Fehler: Die Datei existiert nicht: {file}{Style.RESET_ALL}")
                all_exist = False
        else:
            logger.info(f"{Fore.GREEN}OK: Die Datei existiert: {file}{Style.RESET_ALL}")
    return all_exist

# Dateien sicherstellen
if not ensure_files_exist(files):
    logger.critical(f"{Fore.RED}Ein oder mehrere erforderliche Dateien fehlen. Bitte erstelle sie und starte die Anwendung neu.{Style.RESET_ALL}")
    sys.exit(1)
else:
    logger.info(f"{Fore.GREEN}All files are ready.{Style.RESET_ALL}")

# Funktion zur Bestimmung der maximal möglichen Anzahl von Workern
def get_max_workers(default=DEFAULT_MAX_WORKERS):
    cpu_count = multiprocessing.cpu_count()
    memory = psutil.virtual_memory()
    available_memory_gb = memory.available / (1024 ** 3)

    # Beispielhafte Logik: Je nach verfügbarem Speicher mehr Worker erlauben
    # Dies kann an die spezifischen Anforderungen deiner Anwendung angepasst werden
    max_workers = min(cpu_count * 2, default)

    logger.debug(f"CPU-Kerne: {cpu_count}")
    logger.debug(f"Verfügbarer Speicher: {available_memory_gb:.2f} GB")
    logger.debug(f"Berechnete maximale Worker: {max_workers}")

    return max_workers

# Funktion zur Überprüfung der Port-Verfügbarkeit und Finden eines freien Ports
def find_available_port(start_port=5000):
    port = start_port
    while port < 65535:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(('localhost', port))
                sock.close()
                logger.debug(f"Port {port} ist verfügbar.")
                return port
            except socket.error:
                logger.debug(f"Port {port} ist belegt. Versuche nächsten Port...")
                port += 1
    raise RuntimeError("Kein verfügbarer Port gefunden.")

# Funktion zur Systemüberwachung
def get_system_stats():
    cpu_usage = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    memory_usage = memory.percent
    disk = psutil.disk_usage('/')
    disk_usage = disk.percent

    stats = {
        'cpu_usage_percent': cpu_usage,
        'memory_usage_percent': memory_usage,
        'disk_usage_percent': disk_usage,
    }

    logger.debug(f"Systemstatistiken: {stats}")
    return stats

# Funktion zur Überprüfung von verfügbaren Workern und Port
def check_system_and_port(start_port=5000):
    max_workers = get_max_workers()
    port = find_available_port(start_port)
    system_stats = get_system_stats()
    return {
        'max_workers': max_workers,
        'port': port,
        'system_stats': system_stats
    }

if __name__ == "__main__":
    config = check_system_and_port()
    logger.info(f"{Fore.GREEN}Maximale Anzahl der Worker: {config['max_workers']}{Style.RESET_ALL}")
    logger.info(f"{Fore.GREEN}Verwendeter Port: {config['port']}{Style.RESET_ALL}")
    logger.info(f"{Fore.GREEN}Systemstatistiken: {config['system_stats']}{Style.RESET_ALL}")
