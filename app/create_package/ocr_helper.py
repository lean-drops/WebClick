import asyncio
import logging
import os

import ocrmypdf
from pdf2image import convert_from_path
import pytesseract
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO

OUTPUT_DIRECTORY = os.getenv("OUTPUT_DIRECTORY", "output_pdfs")
os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)
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

