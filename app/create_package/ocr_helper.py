# app/create_package/ocr_helpers.py

import asyncio
import logging
import zipfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import shutil
import sys
from typing import List, Dict

import ocrmypdf
from PyPDF2 import PdfReader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ocr_helpers')

# Configure ThreadPoolExecutor for parallel OCR tasks
MAX_WORKERS = 4  # Adjust the number of workers as needed
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

async def apply_ocr_to_pdf(input_pdf: Path, output_pdf: Path, languages: str = 'deu+eng') -> bool:
    """
    Applies OCR to a single PDF file.

    :param input_pdf: Path to the input PDF.
    :param output_pdf: Path to save the OCR-processed PDF.
    :param languages: Languages to use for OCR (default: 'deu+eng').
    :return: True if OCR was successful, False otherwise.
    """
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(
            executor,
            ocrmypdf.ocr,
            str(input_pdf),
            str(output_pdf),
            '--language', languages,
            '--force-ocr',
            '--redo-ocr',
            '--output-type', 'pdf-a'
        )
        logger.info(f"OCR successfully applied to {input_pdf} -> {output_pdf}")
        return True
    except ocrmypdf.exceptions.OCRError as e:
        logger.error(f"OCR error on {input_pdf}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during OCR on {input_pdf}: {e}")
    return False

async def apply_ocr_to_directory(input_dir: Path, output_dir: Path, languages: str = 'deu+eng') -> List[Dict]:
    """
    Applies OCR to all PDF files in a specified directory.

    :param input_dir: Path to the input directory containing PDFs.
    :param output_dir: Path to the output directory for OCR-processed PDFs.
    :param languages: Languages to use for OCR (default: 'deu+eng').
    :return: List of dictionaries with PDF processing results.
    """
    pdf_files = list(input_dir.rglob('*.pdf'))
    logger.info(f"Found {len(pdf_files)} PDF(s) in {input_dir} for OCR processing.")

    if not pdf_files:
        logger.warning(f"No PDF files found in {input_dir} to process with OCR.")
        return []

    output_dir.mkdir(parents=True, exist_ok=True)

    async def process_pdf(pdf_path: Path) -> Dict:
        relative_path = pdf_path.relative_to(input_dir)
        output_pdf = output_dir / relative_path
        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        success = await apply_ocr_to_pdf(pdf_path, output_pdf, languages=languages)
        return {
            'input_path': pdf_path,
            'output_path': output_pdf,
            'status': 'success' if success else 'error'
        }

    tasks = [process_pdf(pdf) for pdf in pdf_files]
    results = await asyncio.gather(*tasks)
    logger.info("Completed OCR processing for directory.")
    return results

async def apply_ocr_to_all_pdfs(
    individual_collapsed_dir: Path,
    individual_expanded_dir: Path,
    merged_collapsed_pdf: Path,
    merged_expanded_pdf: Path,
    languages: str = 'deu+eng'
) -> None:
    """
    Applies OCR to all individual and merged PDFs.

    :param individual_collapsed_dir: Directory containing individual collapsed PDFs.
    :param individual_expanded_dir: Directory containing individual expanded PDFs.
    :param merged_collapsed_pdf: Path to the merged collapsed PDF.
    :param merged_expanded_pdf: Path to the merged expanded PDF.
    :param languages: Languages to use for OCR (default: 'deu+eng').
    """
    try:
        logger.info("Starting OCR on individual collapsed PDFs.")
        collapsed_results = await apply_ocr_to_directory(
            input_dir=individual_collapsed_dir,
            output_dir=individual_collapsed_dir.parent / f"{individual_collapsed_dir.name}_ocr",
            languages=languages
        )

        logger.info("Starting OCR on individual expanded PDFs.")
        expanded_results = await apply_ocr_to_directory(
            input_dir=individual_expanded_dir,
            output_dir=individual_expanded_dir.parent / f"{individual_expanded_dir.name}_ocr",
            languages=languages
        )

        # Apply OCR to merged collapsed PDF
        if merged_collapsed_pdf.exists():
            logger.info(f"Starting OCR on merged collapsed PDF: {merged_collapsed_pdf}")
            merged_collapsed_output = merged_collapsed_pdf.parent / f"{merged_collapsed_pdf.stem}_ocr.pdf"
            merged_collapsed_success = await apply_ocr_to_pdf(
                input_pdf=merged_collapsed_pdf,
                output_pdf=merged_collapsed_output,
                languages=languages
            )
            if merged_collapsed_success:
                logger.info(f"OCR applied to merged collapsed PDF: {merged_collapsed_output}")
            else:
                logger.warning(f"OCR failed for merged collapsed PDF: {merged_collapsed_pdf}")
        else:
            logger.warning(f"Merged collapsed PDF does not exist: {merged_collapsed_pdf}")

        # Apply OCR to merged expanded PDF
        if merged_expanded_pdf.exists():
            logger.info(f"Starting OCR on merged expanded PDF: {merged_expanded_pdf}")
            merged_expanded_output = merged_expanded_pdf.parent / f"{merged_expanded_pdf.stem}_ocr.pdf"
            merged_expanded_success = await apply_ocr_to_pdf(
                input_pdf=merged_expanded_pdf,
                output_pdf=merged_expanded_output,
                languages=languages
            )
            if merged_expanded_success:
                logger.info(f"OCR applied to merged expanded PDF: {merged_expanded_output}")
            else:
                logger.warning(f"OCR failed for merged expanded PDF: {merged_expanded_pdf}")
        else:
            logger.warning(f"Merged expanded PDF does not exist: {merged_expanded_pdf}")

    except Exception as e:
        logger.error(f"An error occurred during OCR processing: {e}")
    finally:
        logger.info("Completed applying OCR to all PDFs.")

def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Extracts text from a PDF file.

    :param pdf_path: Path to the PDF file.
    :return: Extracted text.
    """
    try:
        reader = PdfReader(str(pdf_path))
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
        return text
    except Exception as e:
        logger.error(f"Error extracting text from {pdf_path}: {e}")
        return ""

async def verify_ocr_output(output_pdf: Path) -> bool:
    """
    Verifies that the OCR output PDF is machine-readable by checking for extracted text.

    :param output_pdf: Path to the OCR-processed PDF.
    :return: True if text is extracted successfully, False otherwise.
    """
    loop = asyncio.get_event_loop()
    try:
        text = await loop.run_in_executor(None, extract_text_from_pdf, output_pdf)
        if text.strip():
            logger.info(f"Machine-readable text found in {output_pdf}.")
            return True
        else:
            logger.warning(f"No machine-readable text found in {output_pdf}.")
            return False
    except Exception as e:
        logger.error(f"Error verifying OCR output for {output_pdf}: {e}")
        return False

async def verify_ocr_for_all_pdfs(
    individual_collapsed_dir: Path,
    individual_expanded_dir: Path,
    merged_collapsed_pdf: Path,
    merged_expanded_pdf: Path
) -> bool:
    """
    Verifies OCR outputs for all individual and merged PDFs.

    :param individual_collapsed_dir: Directory containing OCR-processed individual collapsed PDFs.
    :param individual_expanded_dir: Directory containing OCR-processed individual expanded PDFs.
    :param merged_collapsed_pdf: Path to the OCR-processed merged collapsed PDF.
    :param merged_expanded_pdf: Path to the OCR-processed merged expanded PDF.
    :return: True if all OCR outputs are machine-readable, False otherwise.
    """
    try:
        logger.info("Starting verification of OCR on individual collapsed PDFs.")
        collapsed_ocr_dir = individual_collapsed_dir.parent / f"{individual_collapsed_dir.name}_ocr"
        collapsed_pdfs = list(collapsed_ocr_dir.rglob('*.pdf'))

        logger.info("Starting verification of OCR on individual expanded PDFs.")
        expanded_ocr_dir = individual_expanded_dir.parent / f"{individual_expanded_dir.name}_ocr"
        expanded_pdfs = list(expanded_ocr_dir.rglob('*.pdf'))

        all_pdfs = collapsed_pdfs + expanded_pdfs

        logger.info(f"Verifying OCR for {len(all_pdfs)} individual PDFs.")
        verification_tasks = [verify_ocr_output(pdf) for pdf in all_pdfs]
        results = await asyncio.gather(*verification_tasks)

        # Verify merged PDFs
        merged_results = []
        if merged_collapsed_pdf.exists():
            logger.info(f"Verifying OCR for merged collapsed PDF: {merged_collapsed_pdf}")
            merged_collapsed_ocr = merged_collapsed_pdf.parent / f"{merged_collapsed_pdf.stem}_ocr.pdf"
            merged_results.append(await verify_ocr_output(merged_collapsed_ocr))
        else:
            logger.warning(f"Merged collapsed OCR PDF does not exist: {merged_collapsed_pdf}")

        if merged_expanded_pdf.exists():
            logger.info(f"Verifying OCR for merged expanded PDF: {merged_expanded_pdf}")
            merged_expanded_ocr = merged_expanded_pdf.parent / f"{merged_expanded_pdf.stem}_ocr.pdf"
            merged_results.append(await verify_ocr_output(merged_expanded_ocr))
        else:
            logger.warning(f"Merged expanded OCR PDF does not exist: {merged_expanded_pdf}")

        all_verified = all(results) and all(merged_results)
        if all_verified:
            logger.info("All OCR-processed PDFs are machine-readable.")
        else:
            logger.warning("Some OCR-processed PDFs are not machine-readable.")

        return all_verified

    except Exception as e:
        logger.error(f"An error occurred during OCR verification: {e}")
        return False

def apply_ocr_to_zip(input_zip_path: Path, output_zip_path: Path, languages: str = 'deu+eng') -> None:
    """
    Applies OCR to all PDFs within a ZIP archive and creates a new ZIP with OCR-processed PDFs.

    :param input_zip_path: Path to the input ZIP file.
    :param output_zip_path: Path to save the output ZIP file with OCR-processed PDFs.
    :param languages: Languages to use for OCR (default: 'deu+eng').
    """
    try:
        with TemporaryDirectory() as temp_input_dir, TemporaryDirectory() as temp_output_dir:
            temp_input = Path(temp_input_dir)
            temp_output = Path(temp_output_dir)
            logger.info(f"Temporary directories created: {temp_input}, {temp_output}")

            # Extract ZIP contents
            with zipfile.ZipFile(input_zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_input)
            logger.info(f"Extracted {input_zip_path} to {temp_input}")

            # Find all PDF files
            pdf_files = list(temp_input.rglob('*.pdf'))
            logger.info(f"Found {len(pdf_files)} PDF(s) for OCR processing in ZIP.")

            if not pdf_files:
                logger.warning("No PDF files found in the ZIP to process with OCR.")
                return

            async def process_pdf(pdf: Path):
                relative_path = pdf.relative_to(temp_input)
                output_pdf = temp_output / relative_path
                output_pdf.parent.mkdir(parents=True, exist_ok=True)
                success = await apply_ocr_to_pdf(pdf, output_pdf, languages=languages)
                if not success:
                    logger.error(f"OCR failed for {pdf}")

            # Create and run OCR tasks
            loop = asyncio.get_event_loop()
            tasks = [process_pdf(pdf) for pdf in pdf_files]
            loop.run_until_complete(asyncio.gather(*tasks))
            logger.info("Completed OCR processing for ZIP contents.")

            # Create a new ZIP with OCR-processed PDFs
            with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_out:
                for file in temp_output.rglob('*.pdf'):
                    zip_out.write(file, arcname=file.relative_to(temp_output))
            logger.info(f"Created OCR-processed ZIP: {output_zip_path}")

    except zipfile.BadZipFile as e:
        logger.error(f"Invalid ZIP file: {input_zip_path} - {e}")
    except Exception as e:
        logger.error(f"An error occurred while applying OCR to ZIP: {e}")

    finally:
        logger.info("OCR application to ZIP completed.")

# Ensure TemporaryDirectory is imported
from tempfile import TemporaryDirectory

