import os
import json
import logging
import asyncio
import zipfile
import psutil
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementNotInteractableException,
    WebDriverException,
)
from datetime import datetime
from app.utils.naming_utils import sanitize_filename, shorten_url
import requests
from requests.exceptions import RequestException
from PIL import Image
import traceback
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader

# ============================================
# Konfiguration und Logging
# ============================================

# Pfad zur cookies_selector.json
COOKIES_SELECTOR_PATH = r"/app/static/js/cookies_selector.json"

# Logging-Konfiguration
logging.basicConfig(
    level=logging.DEBUG,  # Level auf DEBUG setzen
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("screenshot.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Globale Variablen zur Verfolgung von Aufgaben und Thread-Sicherheit
screenshot_tasks = {}
screenshot_lock = asyncio.Lock()

# ============================================
# Hilfsfunktionen
# ============================================

def load_cookie_selectors(file_path):
    """Lädt die Cookie-Selektoren aus einer JSON-Datei."""
    if not os.path.exists(file_path):
        logger.warning(f"Cookie-Selektoren-Datei nicht gefunden unter {file_path}. Cookie-Behandlung wird übersprungen.")
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            selectors = json.load(f)
            logger.info(f"{len(selectors)} Cookie-Selektoren von {file_path} geladen.")
            return selectors
    except Exception as e:
        logger.error(f"Fehler beim Laden der Cookie-Selektoren von {file_path}: {e}")
        return []

def normalize_url(url):
    """Normalisiert die URL, um sicherzustellen, dass sie das Protokoll enthält."""
    parsed_url = urlparse(url)
    if not parsed_url.scheme:
        url = "https://" + url
    return url

def is_valid_url(url):
    """Überprüft, ob die URL erreichbar ist, mit deaktivierter SSL-Verifizierung."""
    try:
        response = requests.get(url, timeout=3, verify=False)
        response.raise_for_status()
        return True
    except RequestException as e:
        logger.error(f"URL-Validierung fehlgeschlagen für {url}: {e}")
        return False

def handle_cookies(driver, selectors):
    """Automatisches Ablehnen von Cookies mithilfe von Selektoren aus einer JSON-Datei."""
    if not selectors:
        return  # Keine Selektoren vorhanden

    for selector in selectors:
        try:
            if selector["type"] == "css":
                button = driver.find_element(By.CSS_SELECTOR, selector["selector"])
            elif selector["type"] == "xpath":
                button = driver.find_element(By.XPATH, selector["selector"])

            if button:
                button.click()
                logger.info(f"Cookies abgelehnt mit Selektor: {selector['selector']}")
                break
        except (NoSuchElementException, ElementNotInteractableException) as ex:
            logger.debug(f"Selektor {selector['selector']} nicht gefunden oder nicht interagierbar: {ex}")
            continue
        except WebDriverException as ex:
            logger.error(f"WebDriver-Ausnahme: {ex}")
            break

def optimize_media_display(driver):
    """Optimiert die Darstellung von Bildern und Videos für den Screenshot."""
    try:
        driver.execute_script(
            """
            let elements = document.querySelectorAll('img, video');
            for (let el of elements) {
                el.style.maxWidth = '100%';
                el.style.height = 'auto';
                el.style.objectFit = 'contain';
                if (el.tagName.toLowerCase() === 'video') {
                    el.controls = false;
                }
            }
        """
        )
        logger.info("Medienelemente für die Anzeige optimiert.")
    except WebDriverException as e:
        logger.error(f"Fehler bei der Optimierung der Medienelemente: {e}")

def wait_for_page_load(driver):
    """Wartet, bis die Seite vollständig geladen ist."""
    try:
        page_state = driver.execute_script("return document.readyState;")
        while page_state != "complete":
            asyncio.sleep(0.1)  # Kurze Pause hinzufügen
            page_state = driver.execute_script("return document.readyState;")
        logger.info("Seite vollständig geladen.")
    except WebDriverException as e:
        logger.error(f"Fehler beim Warten auf das Laden der Seite: {e}")

def take_full_page_screenshot(driver, output_path):
    """Erstellt einen Vollbild-Screenshot, indem die Fenstergröße auf die Gesamthöhe der Seite eingestellt wird."""
    try:
        total_width = driver.execute_script("return document.body.scrollWidth")
        total_height = driver.execute_script("return document.body.scrollHeight")

        # Fenstergröße einstellen, um die gesamte Seite in einem Screenshot zu erfassen
        driver.set_window_size(total_width, total_height)
        driver.execute_script("window.scrollTo(0, 0);")  # Nach oben scrollen
        wait_for_page_load(driver)  # Sicherstellen, dass die Seite vollständig geladen ist

        driver.save_screenshot(output_path)
        logger.info(f"Vollbild-Screenshot gespeichert unter {output_path}")

        # Überprüfen, ob die Datei tatsächlich existiert
        if not os.path.exists(output_path):
            logger.error(f"Screenshot wurde nicht gespeichert: {output_path}")
        else:
            logger.debug(f"Screenshot erfolgreich gespeichert: {output_path}")

    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Vollbild-Screenshots: {e}")
        logger.debug(traceback.format_exc())

def sync_take_screenshot(
    url, output_path, selectors, driver_path, chrome_binary_path
):
    chrome_options = Options()
    chrome_options.binary_location = chrome_binary_path
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--window-position=-10000,-10000")  # Fenster unsichtbar machen

    service = ChromeService(
        executable_path=os.path.join(driver_path, "chromedriver.exe")
    )

    logger.info(f"Verwende ChromeDriver-Pfad: {driver_path}")
    logger.info(f"Verwende Chrome-Binary-Pfad: {chrome_binary_path}")

    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30)
        driver.get(url)
        handle_cookies(driver, selectors)
        optimize_media_display(driver)
        take_full_page_screenshot(driver, output_path)
    except Exception as e:
        logger.error(f"Fehler während des Screenshot-Prozesses für URL {url}: {e}")
        logger.debug(traceback.format_exc())
    finally:
        driver.quit()

async def take_screenshot_sequentially(
    url, output_path, selectors, driver_path, chrome_binary_path
):
    """Erstellt Screenshots sequentiell ohne Überlappungen."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        sync_take_screenshot,
        url,
        output_path,
        selectors,
        driver_path,
        chrome_binary_path,
    )
    await adjust_pause_based_on_system_load()

async def take_screenshot_parallel(urls, base_folder, selectors, driver_paths, chrome_binary_paths):
    """Verarbeitet eine Liste von URLs und erstellt Screenshots parallel, speichert sie im angegebenen Ordner."""
    tasks = []
    for i, url in enumerate(urls):
        url = normalize_url(url)
        if is_valid_url(url):
            sanitized_name = sanitize_filename(shorten_url(url))
            output_path = os.path.join(base_folder, f"{sanitized_name}.png")
            driver_path = driver_paths[i % len(driver_paths)]
            chrome_binary_path = chrome_binary_paths[i % len(chrome_binary_paths)]
            # Aufgaben zur parallelen Ausführung planen
            tasks.append(
                asyncio.create_task(
                    take_screenshot_sequentially(
                        url, output_path, selectors, driver_path, chrome_binary_path
                    )
                )
            )
        else:
            logger.warning(f"Ungültige URL übersprungen: {url}")

    if tasks:
        await asyncio.gather(*tasks)  # Alle Aufgaben parallel ausführen
        logger.info("Alle Screenshots wurden erstellt.")
    else:
        logger.warning("Keine gültigen URLs zum Verarbeiten vorhanden.")

async def adjust_pause_based_on_system_load():
    """Passt die Pause dynamisch basierend auf der aktuellen Systemauslastung an."""
    cpu_usage = psutil.cpu_percent(interval=0.5)
    memory_usage = psutil.virtual_memory().percent

    # Schwellenwerte für aggressivere Leistung anpassen
    if cpu_usage > 80 or memory_usage > 80:
        pause_duration = 2
    elif cpu_usage > 50 or memory_usage > 50:
        pause_duration = 0.5
    else:
        pause_duration = 0.1

    logger.info(
        f"Systemauslastung: CPU={cpu_usage}%, Speicher={memory_usage}%. Pausiere für {pause_duration} Sekunden."
    )
    await asyncio.sleep(pause_duration)

def combine_images(image_folder, output_path, direction='vertical'):
    """Fügt Bilder im angegebenen Ordner zu einem einzigen Bild zusammen."""
    images = []
    for file_name in sorted(os.listdir(image_folder)):
        if file_name.endswith('.png') and not file_name.startswith('combined_'):
            image_path = os.path.join(image_folder, file_name)
            if os.path.exists(image_path):
                images.append(Image.open(image_path))
            else:
                logger.warning(f"Bilddatei nicht gefunden: {image_path}")

    if not images:
        logger.warning("Keine Bilder zum Zusammenfügen gefunden.")
        return

    # Gesamte Breite und Höhe bestimmen
    widths, heights = zip(*(img.size for img in images))

    if direction == 'vertical':
        total_width = max(widths)
        total_height = sum(heights)
        combined_image = Image.new('RGB', (total_width, total_height))
        y_offset = 0
        for img in images:
            combined_image.paste(img, (0, y_offset))
            y_offset += img.size[1]
    else:  # horizontal
        total_width = sum(widths)
        total_height = max(heights)
        combined_image = Image.new('RGB', (total_width, total_height))
        x_offset = 0
        for img in images:
            combined_image.paste(img, (x_offset, 0))
            x_offset += img.size[0]

    combined_image.save(output_path)
    logger.info(f"Kombiniertes Bild gespeichert unter {output_path}")

def create_pdf(image_folder, output_pdf_path, toc_entries):
    """
    Erstellt ein PDF aus den Bildern im angegebenen Ordner mit einem interaktiven Inhaltsverzeichnis.

    :param image_folder: Ordner, der die Screenshot-Bilder enthält.
    :param output_pdf_path: Pfad zur Ausgabepdf.
    :param toc_entries: Liste von Dicts mit 'title', 'subtitle', 'filename'.
    """
    c = canvas.Canvas(output_pdf_path, pagesize=A4)
    width, height = A4

    # Inhaltsverzeichnis erstellen
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 50, "Inhaltsverzeichnis")
    c.setFont("Helvetica", 12)
    y_position = height - 80
    toc_links = []

    for idx, entry in enumerate(toc_entries, start=1):
        title = entry['title']
        subtitle = entry.get('subtitle', '')
        filename = entry['filename']
        toc_text = f"{idx}. {title}"
        c.drawString(50, y_position, toc_text)
        # Bookmark-Position speichern
        toc_links.append({
            'title': title,
            'page_number': idx + 1,  # Inhaltsverzeichnis ist auf Seite 1
            'y_position': y_position
        })
        y_position -= 20

    c.showPage()

    # Seiten mit Screenshots hinzufügen
    for entry in toc_entries:
        title = entry['title']
        subtitle = entry.get('subtitle', '')
        filename = entry['filename']
        image_path = os.path.join(image_folder, filename)

        # Seite mit Titel und Untertitel
        c.setFont("Helvetica-Bold", 16)
        c.drawString(20, height - 40, title)
        if subtitle:
            c.setFont("Helvetica", 12)
            c.drawString(20, height - 60, subtitle)

        # Screenshot einfügen
        try:
            img = Image.open(image_path)
            img_width, img_height = img.size
            aspect = img_height / float(img_width)

            # Maximale Breite und Höhe im PDF (unter Berücksichtigung von Rändern)
            max_width = width - 40
            max_height = height - 100

            if img_width > max_width or img_height > max_height:
                if (max_height / aspect) < max_width:
                    display_height = max_height
                    display_width = max_height / aspect
                else:
                    display_width = max_width
                    display_height = max_width * aspect
            else:
                display_width = img_width
                display_height = img_height

            c.drawImage(ImageReader(img), 20, height - 80 - display_height, width=display_width, height=display_height)
        except Exception as e:
            logger.error(f"Fehler beim Einfügen des Bildes {image_path} in das PDF: {e}")

        c.showPage()

    # Inhaltsverzeichnis verlinken
    c.save()

    # Nachbearbeitung mit PyPDF2, um echte interaktive Links hinzuzufügen
    try:
        from PyPDF2 import PdfReader, PdfWriter

        reader = PdfReader(output_pdf_path)
        writer = PdfWriter()

        # Inhaltsverzeichnis auf Seite 0
        toc_page = reader.pages[0]
        writer.add_page(toc_page)

        # Weitere Seiten
        for page in reader.pages[1:]:
            writer.add_page(page)

        # Lese die TOC-Links und füge Links hinzu
        for idx, entry in enumerate(toc_entries, start=1):
            title = entry['title']
            page_number = idx + 1  # Inhaltsverzeichnis ist Seite 1
            writer.add_outline_item(title, page_number - 1)  # Zero-based

        with open(output_pdf_path, "wb") as f_out:
            writer.write(f_out)

        logger.info(f"PDF mit interaktivem Inhaltsverzeichnis erstellt unter {output_pdf_path}")

    except ImportError:
        logger.error("PyPDF2 ist nicht installiert. Installieren Sie es mit 'pip install PyPDF2', um interaktive Links hinzuzufügen.")
    except Exception as e:
        logger.error(f"Fehler bei der Nachbearbeitung des PDFs: {e}")

# ============================================
# Hauptfunktion zur Screenshot-Aufgabe
# ============================================

async def run_screenshot_task(task_id, urls):
    logger.info(f"Starte Screenshot-Aufgabe {task_id} für URLs: {urls}")
    try:
        # Aufgabenstatus auf 'running' setzen
        async with screenshot_lock:
            screenshot_tasks[task_id] = {'status': 'running', 'result': None}

        run_number = task_id
        single_dir = r"C:\Users\BZZ1391\Bingo\WebClick\output directory\single screenshots"
        output_dir = os.path.join(single_dir, f'screenshots_run_{run_number}')
        os.makedirs(output_dir, exist_ok=True)

        cookie_selectors = load_cookie_selectors(COOKIES_SELECTOR_PATH)

        driver_paths = [
            r"C:\Google Neu\chromedriver-win32",
            # Fügen Sie weitere Pfade hinzu, wenn Sie mehrere Instanzen möchten
        ]

        chrome_binary_paths = [
            r"C:\Google Neu\chrome-win32\chrome.exe",
            # Entsprechend anpassen, falls mehrere Chrome-Instanzen verwendet werden
        ]

        # Liste der URLs bearbeiten und Screenshots erstellen
        await take_screenshot_parallel(urls, output_dir, cookie_selectors, driver_paths, chrome_binary_paths)

        # Zusammenführen der Bilder (optional)
        combined_image_path = os.path.join(output_dir, f"combined_{run_number}.png")
        combine_images(output_dir, combined_image_path, direction='vertical')  # 'vertical' oder 'horizontal'

        # Erstellen des PDFs
        # Vorbereitung der TOC-Einträge
        toc_entries = []
        for file_name in sorted(os.listdir(output_dir)):
            if file_name.endswith('.png') and not file_name.startswith('combined_'):
                # Extrahieren Sie den Titel aus dem Dateinamen oder definieren Sie eine andere Logik
                title = os.path.splitext(file_name)[0].replace('_', ' ').title()
                toc_entries.append({
                    'title': title,
                    'subtitle': 'Untertitel hier einfügen',  # Passen Sie dies nach Bedarf an
                    'filename': file_name
                })

        output_pdf_path = os.path.join(output_dir, f"screenshots_run_{run_number}.pdf")
        create_pdf(output_dir, output_pdf_path, toc_entries)

        # Optional: ZIPpen der Ergebnisse
        zip_dir = r"C:\Users\BZZ1391\Bingo\WebClick\output directory\zipped screenshots"
        os.makedirs(zip_dir, exist_ok=True)
        zip_filename = f"screenshots_run_{run_number}.zip"
        zip_filepath = os.path.join(zip_dir, zip_filename)

        with zipfile.ZipFile(zip_filepath, "w") as zipf:
            for root, dirs, files in os.walk(output_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, output_dir))

        logger.info(f"Alle Screenshots wurden erstellt, das PDF wurde generiert und alles wurde in {zip_filepath} gezippt.")

        # Aufgabenstatus auf 'completed' setzen
        async with screenshot_lock:
            screenshot_tasks[task_id]['status'] = 'completed'
            screenshot_tasks[task_id]['result'] = {
                'zip_file': zip_filename,
                'combined_image': combined_image_path,  # Pfad zum kombinierten Bild
                'pdf_file': output_pdf_path  # Pfad zum generierten PDF
            }

    except Exception as e:
        logger.error(f"Fehler während der Screenshot-Aufgabe {task_id}: {e}", exc_info=True)
        logger.debug(traceback.format_exc())
        async with screenshot_lock:
            screenshot_tasks[task_id]['status'] = 'failed'
            screenshot_tasks[task_id]['error'] = str(e)

# ============================================
# Hauptblock zur Ausführung des Skripts
# ============================================

if __name__ == "__main__":
    try:
        # Hauptfunktion definieren
        async def main():
            # Beispiel-Task-ID basierend auf Zeitstempel
            task_id = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Liste der URLs
            urls = [
        "https://www.pointerpointer.com/",
            "http://eelslap.com/"
            ]

            # Screenshot-Aufgabe starten
            await run_screenshot_task(task_id, urls)

            # Ergebnis abrufen
            async with screenshot_lock:
                result = screenshot_tasks.get(task_id)

            if result and result['status'] == 'completed':
                pdf_path = result['result']['pdf_file']
                print(f"PDF verfügbar unter: {pdf_path}")
            else:
                print("Die Screenshot-Aufgabe wurde nicht erfolgreich abgeschlossen.")

        # Ausführung starten
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Ein unerwarteter Fehler ist aufgetreten: {e}")
