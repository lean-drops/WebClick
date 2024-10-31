import os
import zipfile
import logging

logger = logging.getLogger(__name__)


def create_zip_file(source_folder, output_zip_path):
    """
    Create a zip file from the contents of a folder.

    Args:
        source_folder (str): The folder to zip.
        output_zip_path (str): The path to save the zip file.

    Returns:
        None
    """
    # Ensure the directory for the zip file exists
    os.makedirs(os.path.dirname(output_zip_path), exist_ok=True)

    try:
        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, start=source_folder)
                    zipf.write(file_path, arcname)
        logger.info(f"Zip file created at {output_zip_path}")
    except Exception as e:
        logger.error(f"Failed to create zip file {output_zip_path}: {e}")
        raise


def create_zip_archive(pdf_files, zip_filename):
    """
    Erstellt ein ZIP-Archiv aus einer Liste von PDF-Dateien.

    Args:
        pdf_files (List[str]): Liste der PDF-Dateipfade.
        zip_filename (str): Pfad zur zu erstellenden ZIP-Datei.

    Returns:
        None
    """
    # Stelle sicher, dass das Verzeichnis für die ZIP-Datei existiert
    os.makedirs(os.path.dirname(zip_filename), exist_ok=True)

    try:
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in pdf_files:
                if os.path.exists(file_path):
                    arcname = os.path.basename(file_path)
                    zipf.write(file_path, arcname)
                    logger.info(f"Datei zum ZIP hinzugefügt: {file_path}")
                else:
                    logger.warning(f"Datei nicht gefunden und wird übersprungen: {file_path}")
        logger.info(f"ZIP-Archiv erstellt: {zip_filename}")
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des ZIP-Archivs {zip_filename}: {e}")
        raise

