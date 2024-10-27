# app/processing/pdf_converter.py

import os
import asyncio
from typing import List, Dict
from playwright.async_api import async_playwright, Page
import logging
from urllib.parse import urlparse
import hashlib
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO
import ocrmypdf
import zipfile

# Konfiguration
OUTPUT_DIRECTORY = os.getenv("OUTPUT_DIRECTORY", "output_pdfs")
os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def sanitize_filename(url: str) -> str:
    """Erstellt einen sicheren und eindeutigen Dateinamen aus einer URL."""
    parsed_url = urlparse(url)
    path = parsed_url.path.replace('/', '_').strip('_') or 'root'
    hash_digest = hashlib.sha256(url.encode()).hexdigest()[:10]  # Kurzer Hash zur Einzigartigkeit
    return f"{parsed_url.netloc}_{path}_{hash_digest}.pdf"

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

class PDFConverter:
    """Verwaltet die Konvertierung von URLs in PDFs mit Playwright."""

    def __init__(self, max_concurrent_tasks: int = 5):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.playwright = None
        self.browser = None
        self.output_dir_collapsed = os.path.join(OUTPUT_DIRECTORY, 'individual_pdfs_collapsed')
        self.output_dir_expanded = os.path.join(OUTPUT_DIRECTORY, 'individual_pdfs_expanded')
        os.makedirs(self.output_dir_collapsed, exist_ok=True)
        os.makedirs(self.output_dir_expanded, exist_ok=True)

    async def initialize(self):
        """Initialisiert Playwright und startet den Browser."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
        )
        logging.info("Playwright Browser gestartet.")

    async def close(self):
        """Schließt den Browser und stoppt Playwright."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logging.info("Playwright Browser geschlossen.")

    async def render_page(self, url: str, expanded: bool = False) -> Dict:
        """Rendert eine Webseite und speichert sie als PDF."""
        context = None
        page = None
        try:
            context = await self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                device_scale_factor=2,
                locale='de-DE',
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/94.0.4606.81 Safari/537.36"
                )
            )
            page = await context.new_page()
            logging.info(f"Öffne Seite: {url}")
            await page.goto(url, timeout=120000, wait_until='networkidle')  # Timeout erhöht

            # Verstecke unerwünschte Banner
            await page.evaluate("""
                () => {
                    const bannerSelectors = ['.header-banner', '#top-banner', '.unwanted-banner'];
                    bannerSelectors.forEach(selector => {
                        const elements = document.querySelectorAll(selector);
                        elements.forEach(el => el.style.display = 'none');
                    });

                    // Optional: Entferne allgemeine feste Elemente
                    const style = document.createElement('style');
                    style.innerHTML = `
                        header, footer, .fixed, .sticky, .banner, .navbar {
                            display: none !important;
                        }
                    `;
                    document.head.appendChild(style);
                }
            """)

            logging.info("Unerwünschte Banner versteckt.")

            # Sicherstellen, dass alle Inhalte geladen sind
            await asyncio.sleep(2)

            # Scrollen der Seite, um Lazy-Loading zu triggern
            await self._scroll_page(page)

            # Warten, bis alle Bilder geladen sind
            await self._wait_for_images_to_load(page)

            if expanded:
                # Alle collapsible/expandable Elemente aufklappen
                await self._expand_all_elements(page)
            else:
                logging.info("Erweitere keine kollabierbaren Elemente.")

            # Erstelle einen sicheren Dateinamen
            filename = sanitize_filename(url)
            if expanded:
                pdf_path = os.path.join(self.output_dir_expanded, f"{filename}")
            else:
                pdf_path = os.path.join(self.output_dir_collapsed, f"{filename}")

            # PDF erstellen mit optimierten Optionen
            await page.emulate_media(media="screen")
            await page.pdf(
                path=pdf_path,
                format='A4',
                print_background=True,
                margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
                prefer_css_page_size=True,
                scale=1,
                display_header_footer=False
            )
            logging.info(f"PDF erstellt: {pdf_path}")

            # Extrahiere den Seitentitel für das Inhaltsverzeichnis
            title = await page.title()

            return {"url": url, "status": "success", "path": pdf_path, "title": title}

        except Exception as e:
            logging.error(f"Fehler beim Rendern der Seite {url}: {e}")
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
                logging.error(f"Fehler bei der Verarbeitung einer URL: {result}")
                processed_results.append({"url": "unknown", "status": "error", "error": str(result)})
            else:
                processed_results.append(result)
        return processed_results

    async def _scroll_page(self, page: Page):
        """Scrollt die Seite nach unten, um Lazy-Loading von Inhalten zu ermöglichen."""
        logging.info("Scrolle die Seite, um Lazy-Loading zu triggern.")
        total_height = await page.evaluate("() => document.body.scrollHeight")
        scroll_step = 500  # Pixel pro Scroll-Schritt
        for i in range(0, total_height, scroll_step):
            await page.evaluate(f"window.scrollTo(0, {i});")
            await asyncio.sleep(0.1)
        await page.evaluate("window.scrollTo(0, 0);")  # Zurück zum Anfang scrollen

    async def _wait_for_images_to_load(self, page: Page):
        """Wartet, bis alle Bilder auf der Seite geladen sind."""
        logging.info("Warte, bis alle Bilder geladen sind.")
        await page.evaluate("""
            async () => {
                const images = Array.from(document.images);
                await Promise.all(images.map(img => {
                    if (img.complete) return Promise.resolve();
                    return new Promise(resolve => {
                        img.onload = img.onerror = resolve;
                    });
                }));
            }
        """)

    async def _expand_all_elements(self, page: Page):
        """Erweitert alle kollabierbaren Elemente auf der Seite."""
        logging.info("Erweitere alle kollabierbaren Elemente.")
        await page.evaluate("""
            () => {
                const elements = document.querySelectorAll('*');
                elements.forEach(el => {
                    if (el.tagName.toLowerCase() === 'details') {
                        el.open = true;
                    }
                    if (['collapsible', 'expandable', 'accordion', 'toggle'].some(cls => el.classList.contains(cls))) {
                        el.click();
                    }
                });
            }
        """)

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
        reader = PdfReader(entry['path'])
        for page in reader.pages:
            writer.add_page(page)
        toc_entries.append({
            'title': entry['title'],
            'page_number': current_page
        })
        current_page += len(reader.pages)

    # Erstelle das Inhaltsverzeichnis
    toc_pdf = create_table_of_contents(toc_entries)
    toc_reader = PdfReader(toc_pdf)
    toc_page = toc_reader.pages[0]
    writer.insert_page(toc_page, index=0)

    # Füge Lesezeichen hinzu
    for entry in toc_entries:
        writer.add_outline_item(entry['title'], entry['page_number'] + 1)  # Inhaltsverzeichnis ist Seite 1

    # Schreibe das zusammengeführte PDF
    with open(output_path, 'wb') as f_out:
        writer.write(f_out)

    logging.info(f"Alle PDFs wurden zu einem zusammengeführt: {output_path}")

def apply_ocr_to_pdf(input_pdf_path, output_pdf_path):
    try:
        ocrmypdf.ocr(
            input_pdf_path,
            output_pdf_path,
            language='deu',
            progress_bar=True,
            force_ocr=True,  # OCR erzwingen
            redo_ocr=True     # Falls verfügbar, um OCR nochmals durchzuführen
        )
        logging.info(f"OCR angewendet auf {input_pdf_path}")
    except Exception as e:
        logging.error(f"Fehler beim Anwenden von OCR auf {input_pdf_path}: {e}")

def apply_ocr_to_pdfs_in_directory(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for filename in os.listdir(input_dir):
        if filename.endswith('.pdf'):
            input_pdf_path = os.path.join(input_dir, filename)
            output_pdf_path = os.path.join(output_dir, filename)
            apply_ocr_to_pdf(input_pdf_path, output_pdf_path)

def apply_ocr_to_all_pdfs(individual_collapsed_dir, individual_expanded_dir, merged_collapsed_pdf, merged_expanded_pdf):
    # OCR-Verzeichnisse erstellen
    ocr_individual_collapsed_dir = os.path.join(OUTPUT_DIRECTORY, 'ocr_individual_pdfs_collapsed')
    ocr_individual_expanded_dir = os.path.join(OUTPUT_DIRECTORY, 'ocr_individual_pdfs_expanded')
    ocr_combined_collapsed_pdf = os.path.join(OUTPUT_DIRECTORY, 'ocr_combined_pdfs_collapsed.pdf')
    ocr_combined_expanded_pdf = os.path.join(OUTPUT_DIRECTORY, 'ocr_combined_pdfs_expanded.pdf')

    # OCR auf individuelle eingeklappte PDFs
    apply_ocr_to_pdfs_in_directory(individual_collapsed_dir, ocr_individual_collapsed_dir)

    # OCR auf individuelle ausgeklappte PDFs
    apply_ocr_to_pdfs_in_directory(individual_expanded_dir, ocr_individual_expanded_dir)

    # OCR auf kombiniertes eingeklapptes PDF
    apply_ocr_to_pdf(merged_collapsed_pdf, ocr_combined_collapsed_pdf)

    # OCR auf kombiniertes ausgeklapptes PDF
    apply_ocr_to_pdf(merged_expanded_pdf, ocr_combined_expanded_pdf)

def create_zip_archive(output_directory, zip_filename):
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for root, dirs, files in os.walk(output_directory):
            for file in files:
                if not file.endswith('.zip'):
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, output_directory)
                    zipf.write(file_path, arcname=arcname)
    logging.info(f"ZIP-Archiv erstellt: {zip_filename}")

# Entferne den if __name__ == "__main__" Block, da wir das Modul in Flask integrieren werden.
