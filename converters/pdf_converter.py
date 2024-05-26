from fpdf import FPDF
import os
import zipfile

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Website Archive', 0, 1, 'C')

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def create_directory(path):
    """Create a directory if it doesn't exist."""
    if not os.path.exists(path):
        os.makedirs(path)

def create_zip(folder_path, zip_path):
    """Create a zip file from the specified folder."""
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, start=folder_path)
                zipf.write(file_path, arcname)
    return zip_path

def convert_to_pdf(contents, base_folder):
    """Convert the scraped content to PDF and create a zip archive."""
    create_directory(base_folder)
    main_pdf = PDF()
    main_pdf.set_auto_page_break(auto=True, margin=15)

    # Create a subdirectory for individual page screenshots
    screenshots_folder = os.path.join(base_folder, 'screenshots')
    create_directory(screenshots_folder)

    # Convert each PNG to PDF in the screenshots folder
    for i, content in enumerate(contents):
        screenshot_path = content.get('screenshot', '')
        if screenshot_path and os.path.exists(screenshot_path):
            pdf_file = os.path.join(screenshots_folder, f'page_{i+1}.pdf')
            pdf = PDF()
            pdf.add_page()
            pdf.image(screenshot_path, x=10, y=10, w=pdf.w - 20)
            pdf.output(pdf_file)

    # Create the main PDF with hyperlinks to the PDFs
    main_pdf.add_page()
    main_pdf.set_xy(10, 10)
    main_pdf.set_font('Arial', '', 12)

    # Add main screenshot
    main_screenshot_path = os.path.join(base_folder, 'main.png')
    if os.path.exists(main_screenshot_path):
        main_pdf.image(main_screenshot_path, x=10, y=main_pdf.get_y(), w=main_pdf.w - 20)
        main_pdf.ln(10)

    # Add hyperlinks to corresponding PDFs
    for i, content in enumerate(contents):
        for j, page in enumerate(content['pages']):
            link_text = f"{j+1}. {page['title']}"
            main_pdf.set_font('Arial', 'U', 12)
            main_pdf.set_text_color(0, 0, 255)
            pdf_filename = f'page_{i+1}.pdf'
            link_path = os.path.join('screenshots', pdf_filename)
            main_pdf.cell(0, 10, link_text, ln=True, link=pdf_filename)
            main_pdf.set_text_color(0, 0, 0)  # Reset text color
            main_pdf.ln(5)

    main_pdf_file = os.path.join(base_folder, 'main.pdf')
    main_pdf.output(main_pdf_file)

    zip_path = os.path.join(base_folder, 'website_archive.zip')
    create_zip(base_folder, zip_path)

    return zip_path
