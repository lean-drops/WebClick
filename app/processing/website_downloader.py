# app/processing/download.py

import os
import asyncio
import logging
import json
from typing import List, Dict, Callable
from playwright.async_api import async_playwright
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO
import shutil

from app.create_package.create_zipfile import create_zip_archive
from app.processing.website_cleaner import remove_unwanted_elements, remove_fixed_elements, remove_navigation_and_sidebars
from app.processing.website_handler import expand_hidden_elements, scroll_page
from app.processing.website_utils import load_js_file, extract_domain, setup_directories, inject_custom_css
from app.utils.naming_utils import sanitize_filename
from app.archiver.local_archiver import LocalArchiver

from config import ELEMENTS_COLLAPSED_CONFIG, ELEMENTS_EXPANDED_CONFIG, OUTPUT_PDFS_DIR

# ======================= Konfiguration =======================

# Ausgabe-Verzeichnis
os.makedirs(OUTPUT_PDFS_DIR, exist_ok=True)

# Logging konfigurieren mit RotatingFileHandler
logger = logging.getLogger("download_logger")
logger.setLevel(logging.INFO)

# Erstelle einen Console-Handler
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# Erstelle einen RotatingFileHandler
from logging.handlers import RotatingFileHandler

fh = RotatingFileHandler(
    os.path.join(OUTPUT_PDFS_DIR, 'download.log'),
    maxBytes=5*1024*1024,  # 5 MB
    backupCount=3
)
fh.setLevel(logging.INFO)

# Erstelle einen Formatter und füge ihn den Handlern hinzu
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
fh.setFormatter(formatter)

# Füge die Handler dem Logger hinzu, falls noch nicht vorhanden
if not logger.handlers:
    logger.addHandler(ch)
    logger.addHandler(fh)

# ======================= Hilfsfunktionen =======================

def create_table_of_contents(toc_entries: List[Dict]) -> BytesIO:
    """
    Erstellt eine Inhaltsverzeichnis-Seite und gibt sie als BytesIO-Objekt zurück.
    """
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)
    width, height = A4

    # Überschrift des Inhaltsverzeichnisses
    can.setFont("Helvetica-Bold", 13)  # Größere Schrift für die Überschrift
    can.drawString(100, height - 50, "Inhaltsverzeichnis")

    # Schrift für die Einträge
    can.setFont("Helvetica", 12)

    # Anfangsposition für die Einträge
    y_position = height - 80
    line_height = 20  # Erhöhter Zeilenabstand

    for entry in toc_entries:
        title = entry['title']
        page_number = entry['page_number'] + 1  # 1-basierte Seitennummerierung

        # Trunkiere lange Titel, um Überlappungen zu vermeiden
        max_title_length = 30  # Maximale Anzahl an Zeichen für den Titel
        if len(title) > max_title_length:
            title = title[:max_title_length - 3] + "..."

        # Zeichne den Eintrag
        can.drawString(100, y_position, f"{title} ...... {page_number}")
        y_position -= line_height

        # Neue Seite, wenn nicht genug Platz ist
        if y_position < 50:
            can.showPage()
            can.setFont("Helvetica-Bold", 18)
            can.drawString(100, height - 50, "Inhaltsverzeichnis (Fortsetzung)")
            can.setFont("Helvetica", 12)
            y_position = height - 80

    can.save()
    packet.seek(0)
    return packet

def merge_pdfs_with_bookmarks(pdf_entries: List[Dict], output_path: str):
    """
    Fasst mehrere PDFs zu einem zusammen, fügt ein Inhaltsverzeichnis hinzu und setzt Lesezeichen.
    """
    writer = PdfWriter()
    toc_entries = []
    current_page = 0

    # Sammle die Titel und Pfade der erfolgreichen PDFs
    successful_pdfs = [
        entry for entry in pdf_entries if entry['status'] == 'success'
    ]

    for entry in successful_pdfs:
        try:
            reader = PdfReader(entry['path'])
            for page in reader.pages:
                writer.add_page(page)
            toc_entries.append({
                'title': entry['title'],
                'page_number': current_page
            })
            current_page += len(reader.pages)
        except Exception as e:
            logger.error(f"Fehler beim Lesen der PDF {entry['path']}: {e}")

    if toc_entries:
        # Erstelle das Inhaltsverzeichnis
        toc_pdf = create_table_of_contents(toc_entries)
        toc_reader = PdfReader(toc_pdf)
        toc_page = toc_reader.pages[0]
        writer.insert_page(toc_page, index=0)

        # Füge Lesezeichen hinzu
        for entry in toc_entries:
            writer.add_outline_item(entry['title'], entry['page_number'] + 1)  # Inhaltsverzeichnis ist Seite 1

    # Schreibe das zusammengeführte PDF
    try:
        with open(output_path, 'wb') as f_out:
            writer.write(f_out)
        logger.info(f"Alle PDFs wurden zu einem zusammengeführt: {output_path}")
    except Exception as e:
        logger.error(f"Fehler beim Schreiben des zusammengeführten PDFs: {e}")

# ======================= PDFConverter Klasse =======================

class PDFConverter:
    """Verwaltet die Konvertierung von URLs in PDFs mit Playwright."""

    def __init__(self, max_concurrent_tasks: int = 5):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.playwright = None
        self.browser = None
        self.output_dir_collapsed = os.path.join(OUTPUT_PDFS_DIR, 'individual_pdfs_collapsed')
        self.output_dir_expanded = os.path.join(OUTPUT_PDFS_DIR, 'individual_pdfs_expanded')
        os.makedirs(self.output_dir_collapsed, exist_ok=True)
        os.makedirs(self.output_dir_expanded, exist_ok=True)

        # Pfad zum externen JS-File
        self.remove_elements_js_path = os.path.join(os.path.dirname(__file__), 'js', 'remove_elements.js')
        self.remove_elements_js = load_js_file(self.remove_elements_js_path)

        # Laden der JSON-Konfigurationsdateien
        try:
            with open(ELEMENTS_COLLAPSED_CONFIG, 'r', encoding='utf-8') as f:
                self.elements_collapsed = json.load(f)
            logger.info(f"Loaded collapsed elements configuration from {ELEMENTS_COLLAPSED_CONFIG}")
        except Exception as e:
            logger.error(f"Failed to load collapsed elements configuration: {e}")
            self.elements_collapsed = {"remove": []}

        try:
            with open(ELEMENTS_EXPANDED_CONFIG, 'r', encoding='utf-8') as f:
                self.elements_expanded = json.load(f)
            logger.info(f"Loaded expanded elements configuration from {ELEMENTS_EXPANDED_CONFIG}")
        except Exception as e:
            logger.error(f"Failed to load expanded elements configuration: {e}")
            self.elements_expanded = {"remove": []}

    async def initialize(self):
        """Initialisiert Playwright und startet den Browser."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-infobars',
                '--window-size=2560,1440',  # Größere Fenstergröße
            ]
        )
        logger.info("Playwright Browser gestartet.")

    async def close(self):
        """Schließt den Browser und stoppt Playwright."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Playwright Browser geschlossen.")

    async def render_page(self, url: str, expanded: bool = False) -> Dict:
        """Rendert eine Webseite und speichert sie als PDF."""
        context = None
        page = None
        try:
            context = await self.browser.new_context(
                viewport={"width": 2560, "height": 1440},
                device_scale_factor=2,
                locale='de-DE',
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/94.0.4606.81 Safari/537.36"
                )
            )
            page = await context.new_page()
            logger.info(f"Öffne Seite: {url}")
            await page.goto(url, timeout=120000, wait_until='networkidle')

            # Stelle sicher, dass alle Inhalte geladen sind
            await asyncio.sleep(2)

            if expanded:
                # Schritt 1: Versteckte Elemente expandieren
                await expand_hidden_elements(page)
                # Schritt 2: Unerwünschte Elemente basierend auf der JSON-Konfiguration entfernen
                await remove_unwanted_elements(page, expanded=expanded)

                if self.remove_elements_js and self.elements_expanded:
                    # Injecte das remove_elements.js Skript
                    await page.add_script_tag(content=self.remove_elements_js)
                    # Warte, bis das Skript geladen ist
                    await page.wait_for_function("typeof removeElements === 'function'")
                    # Übergebe die JSON-Konfiguration an die removeElements-Funktion
                    await page.evaluate(f"removeElements({json.dumps(self.elements_expanded)})")
                    logger.info("Externes JS zum Entfernen von Elementen im expanded-Modus injiziert.")
            else:
                await remove_fixed_elements(page)
                # Navigationsleiste und Seitenleisten entfernen
                await remove_navigation_and_sidebars(page)
                # Schritt 4: Benutzerdefiniertes CSS für den normalen Modus injizieren
                await inject_custom_css(page, expanded=False)

                if self.remove_elements_js and self.elements_collapsed:
                    # Injecte das remove_elements.js Skript
                    await page.add_script_tag(content=self.remove_elements_js)
                    # Warte, bis das Skript geladen ist
                    await page.wait_for_function("typeof removeElements === 'function'")
                    # Übergebe die JSON-Konfiguration an die removeElements-Funktion
                    await page.evaluate(f"removeElements({json.dumps(self.elements_collapsed)})")
                    logger.info("Externes JS zum Entfernen von Elementen im collapsed-Modus injiziert.")

            # Optional: Scrollen, um Lazy-Loading auszulösen
            await scroll_page(page)

            # Erstelle einen sicheren Dateinamen
            filename = sanitize_filename(url) + '.pdf'

            if expanded:
                pdf_path = os.path.join(self.output_dir_expanded, filename)
            else:
                pdf_path = os.path.join(self.output_dir_collapsed, filename)

            # Generiere das PDF mit optimierten Optionen
            await page.emulate_media(media="screen")
            await page.pdf(
                path=pdf_path,
                format='A3',
                print_background=True,
                margin={"top": "10mm", "bottom": "10mm", "left": "10mm", "right": "10mm"},
                prefer_css_page_size=False,
                scale=1,
                display_header_footer=False
            )
            logger.info(f"PDF erstellt: {pdf_path}")

            # Extrahiere den Seitentitel für das Inhaltsverzeichnis
            title = await page.title()

            return {"url": url, "status": "success", "path": pdf_path, "title": title}

        except Exception as e:
            logger.error(f"Fehler beim Rendern der Seite {url}: {e}")
            return {"url": url, "status": "error", "error": str(e)}
        finally:
            if page:
                await page.close()
            if context:
                await context.close()

    async def convert_urls_to_pdfs(self, urls: List[str], expanded: bool = False, progress_callback: Callable[[int, int], None] = None) -> List[Dict]:
        """Konvertiert eine Liste von URLs zu PDFs und aktualisiert den Fortschritt nach jeder URL."""
        semaphore = asyncio.Semaphore(self.max_concurrent_tasks)
        total_urls = len(urls)
        completed_urls = 0

        async def sem_task(url):
            async with semaphore:
                result = await self.render_page(url, expanded=expanded)
                nonlocal completed_urls
                completed_urls += 1
                if progress_callback:
                    progress_callback(completed_urls, total_urls)
                return result

        tasks = [asyncio.create_task(sem_task(url)) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Fehler bei der Verarbeitung einer URL: {result}")
                processed_results.append({"url": "unknown", "status": "error", "error": str(result)})
            else:
                processed_results.append(result)
        return processed_results

# ======================= Hauptfunktion =======================

async def main():
    # Vorbereitung: Einrichtung der Verzeichnisse
    setup_directories(OUTPUT_PDFS_DIR)

    # Initialisiere den PDFConverter
    converter = PDFConverter(max_concurrent_tasks=5)
    await converter.initialize()

    # Lade die URLs
    urls = [
        "https://www.beispielseite.de",
        "https://www.andere-seite.de",
        # Fügen Sie hier weitere URLs hinzu
    ]
    if not urls:
        logger.error("Keine URLs zum Verarbeiten gefunden. Programm beendet.")
        return

    # Fortschrittsvariable
    total_steps = len(urls) * 2  # Angenommen, sowohl collapsed als auch expanded Modus
    current_step = 0

    # Fortschritts-Callback-Funktion
    def progress_callback(completed, total):
        nonlocal current_step
        current_step += 1
        progress = int((current_step / total_steps) * 100)
        # Hier können Sie den Fortschritt speichern oder anzeigen
        logger.info(f"Fortschritt: {progress}% ({current_step}/{total_steps})")
        # Wenn Sie den Fortschritt extern benötigen, speichern Sie ihn in einer globalen Variable oder Datenstruktur

    # ======================= Individuelle PDFs (Collapsed) =======================
    logger.info("Starte die Konvertierung der URLs zu PDFs (eingeklappte Version).")
    collapsed_results = await converter.convert_urls_to_pdfs(urls, expanded=False, progress_callback=progress_callback)
    merged_collapsed_pdf = os.path.join(OUTPUT_PDFS_DIR, "combined_collapsed.pdf")
    merge_pdfs_with_bookmarks(collapsed_results, merged_collapsed_pdf)

    # ======================= Individuelle PDFs (Expanded) =======================
    logger.info("Starte die Konvertierung der URLs zu PDFs (ausgeklappte Version).")
    expanded_results = await converter.convert_urls_to_pdfs(urls, expanded=True, progress_callback=progress_callback)
    merged_expanded_pdf = os.path.join(OUTPUT_PDFS_DIR, "combined_expanded.pdf")
    merge_pdfs_with_bookmarks(expanded_results, merged_expanded_pdf)

    # ======================= Backup erstellen =======================
    logger.info("Erstelle Backup der generierten PDFs.")
    archiver = LocalArchiver(source_dir=OUTPUT_PDFS_DIR, backup_dir=os.path.join(OUTPUT_PDFS_DIR, "backups"), manifest_format="csv")
    backup_manifest = archiver.backup()

    # ======================= ZIP Archiv erstellen =======================
    logger.info("Erstelle ein ZIP-Archiv der generierten PDFs.")

    # Extrahiere Domain-Namen ohne 'www' und TLD
    domains = [extract_domain(url) for url in urls]
    # Entferne doppelte Domains, falls vorhanden
    unique_domains = list(dict.fromkeys(domains))
    # Begrenze die Länge des ZIP-Namens, falls notwendig
    zip_name_base = "_".join(unique_domains)
    zip_name_base = zip_name_base[:50]  # Begrenze auf 50 Zeichen, um Probleme zu vermeiden
    zip_filename = os.path.join(OUTPUT_PDFS_DIR, f"{zip_name_base}.zip")
    create_zip_archive(OUTPUT_PDFS_DIR, zip_filename)

    # ======================= Bereinigen der Ausgabeordner =======================
    logger.info("Bereinige die Ausgabeordner, um nur das ZIP-Archiv zu behalten.")
    for item in os.listdir(OUTPUT_PDFS_DIR):
        item_path = os.path.join(OUTPUT_PDFS_DIR, item)
        if item_path != zip_filename and item_path != os.path.join(OUTPUT_PDFS_DIR, "backups"):
            try:
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.remove(item_path)
                    logger.info(f"Datei entfernt: {item_path}")
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    logger.info(f"Verzeichnis entfernt: {item_path}")
            except Exception as e:
                logger.error(f"Fehler beim Entfernen von {item_path}: {e}")

    # ======================= Abschluss =======================
    await converter.close()
    logger.info(f"Alle Prozesse abgeschlossen. ZIP-Archiv befindet sich unter: {zip_filename}")
    print(f"ZIP-Archiv erstellt: {zip_filename}")

if __name__ == "__main__":
    asyncio.run(main())
