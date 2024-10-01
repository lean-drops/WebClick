# pdf_combined.py

import os
import sys
import logging
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PyPDF2 import PdfReader, PdfWriter

# ============================================
# Konfiguration und Logging
# ============================================

# Logging-Konfiguration
logging.basicConfig(
    level=logging.DEBUG,  # Setzt das Logging-Level auf DEBUG für detaillierte Logs
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("pdf_combined.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ============================================
# Funktionen zur PDF-Erstellung
# ============================================

def generate_toc_entries(image_folder):
    """
    Generiert die TOC-Einträge basierend auf den Bilddateien im Ordner.

    :param image_folder: Ordner, der die Screenshot-Bilder enthält.
    :return: Liste von Dicts mit 'title', 'subtitle', 'filename'.
    """
    toc_entries = []
    for file_name in sorted(os.listdir(image_folder)):
        if file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            # Extrahieren Sie den Titel aus dem Dateinamen oder definieren Sie eine andere Logik
            title = os.path.splitext(file_name)[0].replace('_', ' ').title()
            toc_entries.append({
                'title': title,
                'subtitle': '',  # Optional: Fügen Sie hier einen Untertitel hinzu
                'filename': file_name
            })
    return toc_entries

def create_interactive_pdf(image_folder, output_pdf_path, toc_entries):
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
    page_numbers = []

    # TOC-Einträge zeichnen
    for idx, entry in enumerate(toc_entries, start=1):
        title = entry['title']
        subtitle = entry.get('subtitle', '')
        filename = entry['filename']
        toc_text = f"{idx}. {title}"
        c.drawString(50, y_position, toc_text)
        page_numbers.append(idx + 1)  # Inhaltsverzeichnis ist auf Seite 1
        y_position -= 20

    c.showPage()

    # Seiten mit Screenshots hinzufügen
    for idx, entry in enumerate(toc_entries, start=1):
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

        # Bookmark setzen
        bookmark_name = f"page_{idx}"
        c.bookmarkPage(bookmark_name)
        c.addOutlineEntry(title, bookmark_name, level=1, closed=True)

        c.showPage()

    c.save()

    # Nachbearbeitung mit PyPDF2, um interaktive Bookmarks hinzuzufügen
    try:
        reader = PdfReader(output_pdf_path)
        writer = PdfWriter()

        # Alle Seiten hinzufügen
        for page in reader.pages:
            writer.add_page(page)

        # Bookmarks hinzufügen
        writer.add_outline_item("Inhaltsverzeichnis", 0)
        for idx, entry in enumerate(toc_entries, start=1):
            title = entry['title']
            page_number = idx  # Inhaltsverzeichnis ist auf Seite 0
            writer.add_outline_item(title, page_number)

        # Speichern des neuen PDFs mit Bookmarks
        with open(output_pdf_path, "wb") as f_out:
            writer.write(f_out)

        logger.info(f"PDF mit interaktivem Inhaltsverzeichnis erstellt unter: {output_pdf_path}")

    except ImportError:
        logger.error("PyPDF2 ist nicht installiert. Installieren Sie es mit 'pip install PyPDF2', um interaktive Bookmarks hinzuzufügen.")
    except Exception as e:
        logger.error(f"Fehler bei der Nachbearbeitung des PDFs: {e}")

# ============================================
# Hauptfunktion zur PDF-Erstellung
# ============================================

def main():
    if len(sys.argv) != 3:
        print("Usage: python pdf_combined.py <screenshots_folder> <output_pdf_path>")
        sys.exit(1)

    screenshots_folder = sys.argv[1]
    output_pdf_path = sys.argv[2]

    if not os.path.isdir(screenshots_folder):
        logger.error(f"Der angegebene Screenshot-Ordner existiert nicht: {screenshots_folder}")
        sys.exit(1)

    toc_entries = generate_toc_entries(screenshots_folder)
    if not toc_entries:
        logger.error("Keine Screenshot-Bilder im angegebenen Ordner gefunden.")
        sys.exit(1)

    create_interactive_pdf(screenshots_folder, output_pdf_path, toc_entries)

if __name__ == "__main__":
    main()
