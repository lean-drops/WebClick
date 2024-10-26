import os
import re
from PyPDF2 import PdfMerger

def merge_pdfs(pdf_dir, output_filename):
    """
    Fügt alle PDF-Dateien im angegebenen Verzeichnis, die mit zweistelliger Nummer beginnen,
    in ein einziges PDF-Dokument zusammen.

    :param pdf_dir: Verzeichnis, das die einzelnen PDF-Dateien enthält
    :param output_filename: Name der finalen PDF-Datei
    """
    merger = PdfMerger()

    # Regulärer Ausdruck, um Dateien zu filtern, die mit zwei Ziffern und einem Unterstrich beginnen
    pattern = re.compile(r'^\d{2}_.*\.pdf$')

    # Liste aller PDF-Dateien im Verzeichnis, die dem Muster entsprechen
    pdf_files = [f for f in os.listdir(pdf_dir) if pattern.match(f)]

    if not pdf_files:
        print("Keine passenden PDF-Dateien gefunden. Stelle sicher, dass die Dateien im richtigen Format sind.")
        return

    # Sortiere die Dateien basierend auf dem Kapitelnummern-Präfix (z.B. 01, 02, ...)
    pdf_files_sorted = sorted(pdf_files, key=lambda x: int(x.split('_')[0]))

    print("Die folgenden Dateien werden zusammengeführt:")
    for pdf in pdf_files_sorted:
        print(pdf)

    # Füge jede PDF-Datei dem Merger hinzu
    for pdf in pdf_files_sorted:
        pdf_path = os.path.join(pdf_dir, pdf)
        merger.append(pdf_path)
        print(f"Hinzugefügt: {pdf_path}")

    # Schreibe das zusammengeführte PDF
    output_path = os.path.join(pdf_dir, output_filename)
    merger.write(output_path)
    merger.close()

    print(f"Alle PDFs wurden erfolgreich zu '{output_path}' zusammengeführt.")

if __name__ == "__main__":
    # Verzeichnis, das die einzelnen PDFs enthält
    pdf_directory = "pdfs"  # Passe diesen Pfad an dein Setup an

    # Name der finalen PDF-Datei
    final_pdf = "Complete_Chapters.pdf"

    merge_pdfs(pdf_directory, final_pdf)
