# config.py
import os
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

# Basisverzeichnis des Projekts
BASE_DIR = Path(os.getenv('BASE_DIR', '.')).resolve()

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

# Einstellungen
DEFAULT_MAX_WORKERS = int(os.getenv('DEFAULT_MAX_WORKERS', '4'))
LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG').upper()

# Logging-Konfiguration
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.DEBUG),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / 'app.log')
    ]
)
logger = logging.getLogger(__name__)

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
]

# Überprüfung der Verzeichnisse
def ensure_directories_exist(directories):
    all_exist = True
    for directory in directories:
        if not directory.exists():
            print(f"{Fore.RED}Fehler: Das Verzeichnis existiert nicht: {directory}")
            all_exist = False
        else:
            print(f"{Fore.GREEN}OK: Das Verzeichnis existiert: {directory}")
    if not all_exist:
        print(f"{Fore.RED}Ein oder mehrere erforderliche Verzeichnisse fehlen. Bitte erstelle sie und starte die Anwendung neu.")
        sys.exit(1)

ensure_directories_exist(directories)

# Pfade zu spezifischen Dateien
files = [
    OUTPUT_MAPPING_PATH,
    TABOO_JSON_PATH,
    COOKIES_SELECTOR_JSON_PATH,
    EXCLUDE_SELECTORS_JSON_PATH,
    URLS_JSON_PATH,
]

# Überprüfung der Dateien
def ensure_files_exist(files):
    all_exist = True
    for file in files:
        if not file.exists():
            print(f"{Fore.RED}Fehler: Die Datei existiert nicht: {file}")
            all_exist = False
        else:
            print(f"{Fore.GREEN}OK: Die Datei existiert: {file}")
    if not all_exist:
        print(f"{Fore.RED}Ein oder mehrere erforderliche Dateien fehlen. Bitte erstelle sie und starte die Anwendung neu.")
        sys.exit(1)

ensure_files_exist(files)

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
    print(f"{Fore.GREEN}Maximale Anzahl der Worker: {config['max_workers']}")
    print(f"{Fore.GREEN}Verwendeter Port: {config['port']}")
    print(f"{Fore.GREEN}Systemstatistiken: {config['system_stats']}")
