# app/processing/download.py

import os
import asyncio
import logging
from typing import List, Dict
from playwright.async_api import async_playwright, Page
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO
import ocrmypdf
import shutil

from app.create_package.create_zipfile import create_zip_archive
from app.create_package.ocr_helper import apply_ocr_to_all_pdfs
from app.processing.utils import (
    get_url, sanitize_filename, extract_domain, expand_hidden_elements,
    remove_unwanted_elements, remove_fixed_elements, scroll_page,
    setup_directories, remove_navigation_and_sidebars, inject_custom_css,
    load_js_file
)

# ======================= Konfiguration =======================

# Ausgabe-Verzeichnis
OUTPUT_PDFS_DIR = os.getenv("OUTPUT_PDFS_DIR", "output_pdfs")
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
    can.setFont("Helvetica-Bold", 16)
    can.drawString(100, height - 50, "Inhaltsverzeichnis")
    can.setFont("Helvetica", 12)
    y_position = height - 80
    for entry in toc_entries:
        title = entry['title']
        page_number = entry['page_number'] + 1  # 1-basierte Seitennummerierung
        can.drawString(100, y_position, f"{title} ...... {page_number}")
        y_position -= 20
        if y_position < 50:
            can.showPage()
            y_position = height - 50
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

    # app/processing/download.py

    async def render_page(self, url: str, expanded: bool = False) -> Dict:
        """Renders a webpage and saves it as PDF."""
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
            logger.info(f"Opening page: {url}")
            await page.goto(url, timeout=120000, wait_until='networkidle')

            # Ensure all content is loaded
            await asyncio.sleep(2)

            if expanded == True:
                # Step 1: Expand hidden elements
                await expand_hidden_elements(page)
                # Step 2: Remove unwanted elements
                await remove_unwanted_elements(page, expanded=expanded)

                if self.remove_elements_js:
                    await page.evaluate(self.remove_elements_js)
                    logger.info("Injected external JS to remove elements in expanded mode.")


            else:
                await remove_fixed_elements(page)
                # Remove navigation bar and sidebars
                await remove_navigation_and_sidebars(page)
                # Step 4: Inject custom CSS for normal mode
                await inject_custom_css(page, expanded=False)




            # Optionally: Scroll to trigger lazy-loading
            await scroll_page(page)

            # Create a safe filename
            filename = sanitize_filename(url)
            if expanded:
                pdf_path = os.path.join(self.output_dir_expanded, filename)
            else:
                pdf_path = os.path.join(self.output_dir_collapsed, filename)

            # Generate PDF with optimized options
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
            logger.info(f"PDF created: {pdf_path}")

            # Extract the page title for the table of contents
            title = await page.title()

            return {"url": url, "status": "success", "path": pdf_path, "title": title}

        except Exception as e:
            logger.error(f"Error rendering page {url}: {e}")
            return {"url": url, "status": "error", "error": str(e)}
        finally:
            if page:
                await page.close()
            if context:
                await context.close()

    async def convert_urls_to_pdfs(self, urls: List[str], expanded: bool = False) -> List[Dict]:
        """Konvertiert eine Liste von URLs zu PDFs."""
        semaphore = asyncio.Semaphore(self.max_concurrent_tasks)

        async def sem_task(url):
            async with semaphore:
                return await self.render_page(url, expanded=expanded)

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

# ======================= Main Block =======================

if __name__ == "__main__":
    import asyncio

    async def main():
        # Vorbereitung: Einrichtung der Verzeichnisse
        setup_directories(OUTPUT_PDFS_DIR)

        # Initialisiere den PDFConverter
        converter = PDFConverter(max_concurrent_tasks=5)
        await converter.initialize()

        # Lade die URLs
        urls = [
            "https://www.zh.ch/de/sicherheit-justiz/strafvollzug-und-strafrechtliche-massnahmen/jahresbericht-2023.html",
            "https://www.zh.ch/de/wirtschaft-arbeit/handelsregister/stiftung.html",
            "https://www.zh.ch/de/sicherheit-justiz/strafvollzug-und-strafrechtliche-massnahmen.html"
        ]
        if not urls:
            logger.error("Keine URLs zum Verarbeiten gefunden. Programm beendet.")
            return

        # ======================= Individuelle PDFs (Collapsed) =======================
        logger.info("Starte die Konvertierung der URLs zu PDFs (eingeklappte Version).")
        collapsed_results = await converter.convert_urls_to_pdfs(urls, expanded=False)
        merged_collapsed_pdf = os.path.join(OUTPUT_PDFS_DIR, "combined_collapsed.pdf")
        merge_pdfs_with_bookmarks(collapsed_results, merged_collapsed_pdf)

        # ======================= Individuelle PDFs (Expanded) =======================
        logger.info("Starte die Konvertierung der URLs zu PDFs (ausgeklappte Version).")
        expanded_results = await converter.convert_urls_to_pdfs(urls, expanded=True)
        merged_expanded_pdf = os.path.join(OUTPUT_PDFS_DIR, "combined_expanded.pdf")
        merge_pdfs_with_bookmarks(expanded_results, merged_expanded_pdf)

        # ======================= OCR Anwenden =======================
        logger.info("Wende OCR auf alle PDFs an.")
        apply_ocr_to_all_pdfs(
            individual_collapsed_dir=converter.output_dir_collapsed,
            individual_expanded_dir=converter.output_dir_expanded,
            merged_collapsed_pdf=merged_collapsed_pdf,
            merged_expanded_pdf=merged_expanded_pdf
        )

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
            if item_path != zip_filename:
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

    # Starte das asynchrone Hauptprogramm
    asyncio.run(main())
