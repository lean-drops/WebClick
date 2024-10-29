import hashlib
import os
import json
import logging
import time
import random
from urllib.parse import urljoin, urlparse
import asyncio
import httpx
from collections import defaultdict
from lxml import html  # Import lxml
import aiofiles

from config import OUTPUT_MAPPING_PATH

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,  # Ändere zu logging.DEBUG für detailliertere Ausgaben
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Fehlerverfolgung
error_counts = defaultdict(int)

# Cache-Verzeichnisse
CACHE_DIR = "../static/cache"
MAPPING_DIR = "../static/cache/mapping_cache"


# Tabu-Begriffe aus der JSON-Datei laden
TABOO_JSON_PATH = os.path.join(os.path.dirname(__file__), '..', 'static', 'json', 'taboo.json')
with open(TABOO_JSON_PATH, 'r', encoding='utf-8') as f:
    taboo_data = json.load(f)
    TABOO_TERMS = set(term.lower() for term in taboo_data.get('taboo_terms', []))

# Utility-Funktionen
def url_to_filename(url):
    filename = hashlib.md5(url.encode('utf-8')).hexdigest()
    logger.debug(f"Generierter Dateiname für URL {url}: {filename}")
    return filename

def sanitize_filename(filename):
    sanitized = "".join(x for x in filename if (x.isalnum() or x in "._- "))
    logger.debug(f"Bereinigter Dateiname: {sanitized}")
    return sanitized

def is_valid_url(url, base_netloc):
    parsed_url = urlparse(url)
    is_valid = parsed_url.scheme in ('http', 'https') and parsed_url.netloc == base_netloc
    logger.debug(f"URL {url} ist {'gültig' if is_valid else 'ungültig'}")
    return is_valid

def is_binary_file(url):
    binary_extensions = (
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.pdf', '.doc', '.docx', '.xls',
        '.xlsx', '.zip', '.rar', '.exe', '.svg', '.mp3', '.mp4', '.avi', '.mov', '.wmv',
        '.php', '.aspx', '.jsp'  # Füge hier weitere unerwünschte Endungen hinzu
    )
    is_binary = url.lower().endswith(binary_extensions)
    logger.debug(f"URL {url} ist {'eine Binärdatei' if is_binary else 'keine Binärdatei'}")
    return is_binary

def contains_taboo_term(text):
    if not text:
        return False
    text_lower = text.lower()
    has_taboo = any(term in text_lower for term in TABOO_TERMS)
    logger.debug(f"Text '{text}' enthält {'einen Tabu-Begriff' if has_taboo else 'keinen Tabu-Begriff'}")
    return has_taboo

# Asynchrone Funktion zum Abrufen von Webseiteninhalten mit Fehlerbehandlung und Rate Limiting
async def fetch_website_content(client, url, retries=5, delay=1):
    for i in range(retries):
        try:
            await asyncio.sleep(random.uniform(0.5, 1.5))  # Zufällige Wartezeit zwischen den Anfragen
            response = await client.get(url, timeout=10)
            if response.status_code == 429:  # Falls Rate Limit erreicht wird
                logger.warning(f"Rate Limit erreicht für {url}. Wartezeit: {delay} Sekunden.")
                await asyncio.sleep(delay)
                delay *= 2  # Exponentielles Backoff
                continue
            if response.status_code != 200:
                error_message = f"Fehler beim Abrufen von {url}: HTTP {response.status_code}"
                logger.warning(error_message)
                error_counts[error_message] += 1  # Fehler zählen
                return None, None
            content_type = response.headers.get('Content-Type', '').lower()
            logger.debug(f"Inhaltstyp von {url}: {content_type}")
            if 'text/html' in content_type:
                content = response.text
                logger.debug(f"Erfolgreich HTML-Inhalt von {url} abgerufen")
                return content, content_type
            else:
                logger.debug(f"Kein HTML-Inhalt bei {url}")
                return None, content_type
        except Exception as e:
            error_message = f"Fehler beim Abrufen von {url}: {e}"
            logger.error(error_message)
            error_counts[error_message] += 1  # Fehler zählen
            return None, None
    return None, None

# Asynchrone Funktion zum Extrahieren von Links und Struktur aus dem HTML-Inhalt
async def extract_links(url, client, url_mapping, base_netloc, level=0, max_depth=2, visited_urls=None, parent_id=None):
    if visited_urls is None:
        visited_urls = set()

    if level > max_depth:
        logger.debug(f"Maximale Tiefe erreicht bei {url}")
        return

    parsed_url = urlparse(url)
    normalized_url = parsed_url._replace(fragment='').geturl()

    if normalized_url in visited_urls:
        logger.debug(f"URL bereits besucht: {normalized_url}")
        return

    visited_urls.add(normalized_url)
    logger.debug(f"Besuche URL: {normalized_url}")

    content, content_type = await fetch_website_content(client, normalized_url)

    if content is None and content_type is None:
        logger.debug(f"Inhalt ist None für URL: {normalized_url}")
        return

    parser = html.fromstring(content) if content else None  # Verwenden von lxml

    page_id = url_to_filename(normalized_url)
    if parser is not None:
        title_element = parser.find(".//title")
        if title_element is not None and title_element.text is not None:
            title_text = title_element.text.strip()
        else:
            title_text = normalized_url  # Fallback, falls kein Titel vorhanden ist
    else:
        title_text = normalized_url  # Fallback, falls der Parser fehlschlägt

    title = sanitize_filename(title_text)

    # Check auf Tabu-Begriffe im Titel
    if contains_taboo_term(title):
        logger.info(f"Überspringe Seite wegen Tabu-Begriff im Titel: {title} ({normalized_url})")
        return

    # Füge die Seite zur Mapping-Struktur hinzu und setze den parent_id
    if page_id not in url_mapping:
        url_mapping[page_id] = {
            'title': title,
            'url': normalized_url,
            'children': [],
            'level': level,
            'parent_id': parent_id  # Hier setzen wir den parent_id
        }
        logger.debug(f"Seite hinzugefügt: {title} (ID: {page_id}) mit parent_id: {parent_id}")

    # Nur weiter extrahieren, wenn die Seite HTML ist
    if parser is not None:
        tasks = []
        links = []
        # Links extrahieren und verarbeiten
        for element in parser.xpath('//a[@href]'):
            href = element.get('href')
            full_url = urljoin(normalized_url, href)

            if not is_valid_url(full_url, base_netloc):
                continue

            if is_binary_file(full_url):
                logger.debug(f"Überspringe Binärdatei oder unerwünschte Endung: {full_url}")
                continue

            link_text = element.text_content().strip()
            if contains_taboo_term(link_text):
                continue

            links.append((full_url, link_text))

        # Entferne Duplikate sofort, um Leistung zu verbessern
        unique_links = list(set(links))

        for full_url, link_text in unique_links:
            child_id = url_to_filename(full_url)
            if child_id not in url_mapping[page_id]['children']:
                url_mapping[page_id]['children'].append(child_id)
                logger.debug(f"Link hinzugefügt: {full_url} als Kind von {normalized_url}")

            # Rekursiver Aufruf mit dem aktuellen page_id als parent_id
            task = extract_links(
                full_url,
                client,
                url_mapping,
                base_netloc,
                level=level+1,
                max_depth=max_depth,
                visited_urls=visited_urls,
                parent_id=page_id  # Übergebe den parent_id an das Kind
            )
            tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks)

# Funktion zum Scrapen einer Website und Speichern der Struktur im Cache
def ensure_directory_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)
        logger.info(f"Verzeichnis erstellt: {path}")

# Asynchrone Funktion zum Scrapen einer Website und Speichern der Struktur im Cache
async def scrape_website(url, max_depth=2, max_concurrency=500, use_cache=True):
    logger.info(f"Starte Scraping für {url}")
    url_mapping = defaultdict(dict)

    parsed_base_url = urlparse(url)
    base_netloc = parsed_base_url.netloc

    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; Bot/1.0; +http://yourwebsite.com/bot)'
    }

    limits = httpx.Limits(max_keepalive_connections=max_concurrency, max_connections=max_concurrency)

    base_page_id = url_to_filename(url)

    # Lade bestehenden Cache, falls vorhanden
    cache_file = os.path.join(MAPPING_DIR, f"{hashlib.md5(url.encode()).hexdigest()}.json")

    ensure_directory_exists(MAPPING_DIR)  # Überprüfe und erstelle das Cache-Verzeichnis

    if use_cache and os.path.exists(cache_file):
        logger.info(f"Verwende gecachte Daten für {url}")
        async with aiofiles.open(cache_file, 'r', encoding='utf-8') as f:
            cached_data = await f.read()
            logger.debug(f"Gecachte Daten geladen: {cached_data[:100]}...")  # Zeige die ersten 100 Zeichen
            url_mapping.update(json.loads(cached_data))

            # Überprüfen, ob der Cache Daten enthält
            if url_mapping:
                logger.info(f"Cache erfolgreich geladen für {url}")
                return {
                    'url': url,
                    'url_mapping': url_mapping,
                    'base_page_id': base_page_id
                }
            else:
                logger.info(f"Cache ist leer oder ungültig für {url}. Starte erneutes Scraping.")

    # SSL-Überprüfung deaktivieren mit verify=False
    async with httpx.AsyncClient(headers=headers, limits=limits, http2=True, verify=False) as client:
        await extract_links(url, client, url_mapping, base_netloc, level=0, max_depth=max_depth)

    # Überprüfe, ob das Scraping erfolgreich war
    if not url_mapping:
        logger.warning(f"Keine Daten nach Scraping gefunden für {url}.")
    else:
        logger.info(f"Scraping abgeschlossen. Gefundene Seiten: {len(url_mapping)}")

    # Speichere den Cache am Ende
    ensure_directory_exists(MAPPING_DIR)  # Überprüfe und erstelle das Cache-Verzeichnis
    async with aiofiles.open(cache_file, 'w', encoding='utf-8') as f:
        cache_data = json.dumps(url_mapping, indent=4)
        await f.write(cache_data)
        logger.debug(f"Cache gespeichert für {url}: {cache_data[:100]}...")  # Zeige die ersten 100 Zeichen

    return {
        'url': url,
        'url_mapping': url_mapping,
        'base_page_id': base_page_id
    }

# Funktion zur Ausgabe des Fehlerberichts
def log_error_summary():
    if error_counts:
        logger.info("\n--- Fehlerbericht ---")
        for error_message, count in error_counts.items():
            logger.info(f"{error_message} - aufgetreten {count} mal")
    else:
        logger.info("Keine Fehler aufgetreten.")

if __name__ == "__main__":
    async def main():
        os.makedirs(CACHE_DIR, exist_ok=True)
        os.makedirs(MAPPING_DIR, exist_ok=True)

        test_url = "https://www.zh.ch/de/sicherheit-justiz/strafvollzug-und-strafrechtliche-massnahmen/jahresbericht-2023/jahresbericht-2022.html"  # Ersetzen Sie dies durch die gewünschte URL

        start_time = time.time()
        result = await scrape_website(test_url, max_depth=2, max_concurrency=500, use_cache=True)
        end_time = time.time()

        elapsed_time = end_time - start_time

        if 'error' in result:
            logger.error(f"Fehler beim Scrapen der Website: {result['error']}")
        else:
            num_pages = len(result['url_mapping'])
            time_per_page = elapsed_time / num_pages if num_pages > 0 else 0
            logger.info(f"Scraping erfolgreich für {result['url']}")
            logger.info(f"Gesamtzahl der gesammelten Seiten: {num_pages}")
            logger.info(f"Ausführungszeit: {elapsed_time:.2f} Sekunden")
            logger.info(f"Durchschnittliche Zeit pro Seite: {time_per_page:.4f} Sekunden")

            output_file = OUTPUT_MAPPING_PATH
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result['url_mapping'], f, indent=4)
            logger.info(f"Ergebnis gespeichert in {output_file}")

        # Am Ende den Fehlerbericht ausgeben
        log_error_summary()

    asyncio.run(main())
