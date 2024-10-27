import asyncio
from pdf2image import convert_from_path
import pytesseract
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO

async def apply_ocr_to_pdf(input_pdf_path, output_pdf_path, language='deu'):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _apply_ocr_sync, input_pdf_path, output_pdf_path, language)

def _apply_ocr_sync(input_pdf_path, output_pdf_path, language):
    pages = convert_from_path(input_pdf_path)
    pdf_writer = PdfWriter()

    for page_image in pages:
        ocr_result = pytesseract.image_to_pdf_or_hocr(page_image, lang=language, extension='pdf')
        pdf_reader = PdfReader(BytesIO(ocr_result))
        pdf_writer.add_page(pdf_reader.pages[0])

    with open(output_pdf_path, 'wb') as f_out:
        pdf_writer.write(f_out)
