import pdfkit
import logging
import os
from datetime import datetime

# Setup for logging
logging.basicConfig(filename="pdf_conversion.log",
                    level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

# Path to wkhtmltopdf executable
path_to_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
pdfkit_config = pdfkit.configuration(wkhtmltopdf=path_to_wkhtmltopdf)


# Function to convert a website to PDF
def website_to_pdf(url: str, output_dir: str = "pdf_output", filename: str = None):
    try:
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logging.info(f"Output directory created at {output_dir}")

        # Generate filename if not provided
        if not filename:
            filename = f"website_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        # Full path for the PDF
        pdf_path = os.path.join(output_dir, filename)

        # PDF conversion
        logging.info(f"Starting PDF conversion for {url}")
        pdfkit.from_url(url, pdf_path, configuration=pdfkit_config)
        logging.info(f"PDF successfully saved at {pdf_path}")

        return pdf_path

    except Exception as e:
        logging.error(f"Error converting website to PDF: {e}")
        raise


# Usage Example
if __name__ == "__main__":
    # Example URL and output path
    website_url = "https://www.example.com"
    pdf_output_directory = "pdfs"
    pdf_filename = "example_website.pdf"

    # Call the conversion function
    try:
        pdf_file = website_to_pdf(website_url, pdf_output_directory, pdf_filename)
        print(f"PDF successfully created: {pdf_file}")
    except Exception as e:
        print(f"Failed to create PDF: {e}")
