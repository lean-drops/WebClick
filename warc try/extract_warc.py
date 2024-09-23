import os
import logging
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from warcio.archiveiterator import ArchiveIterator
import webbrowser
import shutil
import urllib.parse
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def sanitize_filename(filename):
    """
    Remove invalid characters from filenames.
    """
    return re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', filename)

def extract_warc(warc_file, output_dir, original_url):
    """
    Extract contents from a WARC file and save them to the specified directory.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    extracted_files = []
    main_html_file = None

    with open(warc_file, 'rb') as stream:
        for record in ArchiveIterator(stream):
            if record.rec_type == 'response':
                url = record.rec_headers.get_header('WARC-Target-URI')
                content_type = record.http_headers.get_header('Content-Type')

                parsed_url = urllib.parse.urlparse(url)
                url_path = parsed_url.netloc + parsed_url.path
                filename = Path(url_path).name or "index"
                sanitized_filename = sanitize_filename(filename)
                file_extension = content_type.split('/')[-1].split(';')[0] if content_type else 'bin'

                output_file_path = output_dir / f"{sanitized_filename}.{file_extension}"
                extracted_files.append(output_file_path)

                with open(output_file_path, 'wb') as f:
                    f.write(record.content_stream().read())

                if original_url in url and "html" in content_type:
                    main_html_file = output_file_path

    logging.info("Extracted files:")
    for f in extracted_files:
        logging.info(f)

    return main_html_file, extracted_files

def create_zip_from_directory(directory, zip_name):
    shutil.make_archive(zip_name, 'zip', directory)
    logging.info(f"ZIP archive {zip_name}.zip created.")

def start_server(directory, port=8080):
    os.chdir(directory)
    handler = SimpleHTTPRequestHandler
    while True:
        try:
            httpd = HTTPServer(('localhost', port), handler)
            break
        except OSError:
            logging.warning(f"Port {port} is in use, trying port {port + 1}")
            port += 1

    logging.info(f"Serving on port {port}")
    webbrowser.open(f"http://localhost:{port}")
    httpd.serve_forever()

def move_file(src, dst):
    src = Path(src)
    dst = Path(dst)

    if not src.exists():
        logging.error(f"Source file {src} does not exist.")
        return

    if dst.exists():
        dst = dst.with_name(f"{dst.stem}_{int(dst.suffix[1:]) + 1}{dst.suffix}")

    try:
        shutil.move(src, dst)
        logging.info(f"Moved {src} to {dst}")
    except FileNotFoundError as e:
        logging.error(f"Error moving file {src} to {dst}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")

def create_unique_directory(base_dir, base_name):
    """
    Create a unique directory based on the base name and a counter if necessary.
    """
    base_dir = Path(base_dir)
    counter = 1
    output_dir = base_dir / base_name
    while output_dir.exists():
        output_dir = base_dir / f"{base_name}_{counter}"
        counter += 1
    output_dir.mkdir()
    return output_dir

def main():
    warc_file = Path(r"C:\Users\BZZ1391\Bingo\WebClick\warc try\scrapers\archives\www_bs_ch_20240822154517.warc.gz")
    base_output_dir = Path(r"C:\Users\BZZ1391\Bingo\WebClick\warc try\output")
    original_url = "https://www.bs.ch"

    temp_output_dir = base_output_dir / "temp_extract"
    main_html_file, extracted_files = extract_warc(warc_file, temp_output_dir, original_url)

    session_output_dir = create_unique_directory(base_output_dir, "website_content")

    for file in extracted_files:
        dest_path = session_output_dir / file.name
        move_file(file, dest_path)

    shutil.rmtree(temp_output_dir)

    if main_html_file:
        os.rename(session_output_dir / main_html_file.name, session_output_dir / "index.html")

    create_zip_from_directory(session_output_dir, base_output_dir / 'website_content')

    # Convert Path to string before passing it to webbrowser.open
    webbrowser.open(str(session_output_dir / "index.html"))

    start_server(session_output_dir)

if __name__ == "__main__":
    main()
