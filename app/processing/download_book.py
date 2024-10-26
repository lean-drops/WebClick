import pdfkit
from bs4 import BeautifulSoup
import os

# Pfade konfigurieren
html_file = "input.html"  # Pfad zur deiner HTML-Datei
output_directory = "Reading"  # Verzeichnis, in dem die PDFs gespeichert werden sollen
base_url = "https://third-bit.com/sdxpy/intro/"  # Basis-URL für relative Links

# Stelle sicher, dass das Ausgabeverzeichnis existiert
os.makedirs(output_directory, exist_ok=True)

# PDFKit-Optionen
options = {
    "enable-local-file-access": None,  # Notwendig für einige Systeme
    "quiet": "",  # Unterdrückt wkhtmltopdf-Ausgaben
}


def extract_links(html_file):
    """Extrahiert Kapitelnummern, Namen und Links aus der HTML-Datei."""
    with open(html_file, "r", encoding="utf-8") as file:
        soup = BeautifulSoup(file, "html.parser")

    chapters = []
    # Wähle die Links innerhalb von <ol class="toc-chapter">
    for idx, li in enumerate(soup.select("ol.toc-chapter li a"), start=1):
        chapter_number = f"{idx:02d}"
        chapter_name = li.get_text(strip=True)
        chapter_link = li['href']

        # Handle relative Links
        if not chapter_link.startswith("http"):
            chapter_link = os.path.join(base_url, chapter_link.lstrip("/"))

        chapters.append((chapter_number, chapter_name, chapter_link))

    return chapters


def create_pdfs(chapters, output_dir):
    """Erstellt für jeden Kapitel-Link eine separate PDF-Datei."""
    for chapter_number, chapter_name, url in chapters:
        # Erstelle einen sauberen Dateinamen
        safe_chapter_name = "_".join(chapter_name.split())
        pdf_filename = f"{chapter_number}_{safe_chapter_name}.pdfs"
        pdf_path = os.path.join(output_dir, pdf_filename)

        try:
            print(f"Erstelle PDF für Kapitel {chapter_number}: {chapter_name} ...")
            pdfkit.from_url(url, pdf_path, options=options)
            print(f"PDF erstellt: {pdf_path}")
        except Exception as e:
            print(f"Fehler beim Erstellen von {pdf_filename}: {e}")


def main():
    # Extrahiere Kapitelinformationen aus der HTML-Datei
    chapters = extract_links(html_file)

    if not chapters:
        print("Keine Kapitel-Links gefunden. Bitte überprüfe die HTML-Datei.")
        return

    # Erstelle PDFs für alle Kapitel
    create_pdfs(chapters, output_directory)
    print("Alle PDFs wurden erfolgreich erstellt.")


if __name__ == "__main__":
    main()
