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
    if not os.path.exists(path):
        os.makedirs(path)

def create_zip(folder_path, zip_path):
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, start=folder_path)
                zipf.write(file_path, arcname)
    return zip_path

def convert_to_pdf(contents, base_folder):
    create_directory(base_folder)
    main_pdf = PDF()
    main_pdf.set_auto_page_break(auto=True, margin=15)

    # Create a subdirectory for individual page screenshots
    screenshots_folder = os.path.join(base_folder, 'screenshots')
    create_directory(screenshots_folder)

    for i, content in enumerate(contents):
        pdf = PDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf_file = os.path.join(screenshots_folder, f'page_{i+1}.pdf') if i > 0 else os.path.join(base_folder, 'main.pdf')

        pdf.add_page()
        pdf.set_xy(10, 10)
        pdf.set_font('Arial', '', 12)

        # Add screenshot
        screenshot_path = content.get('screenshot', '')
        if screenshot_path and os.path.exists(screenshot_path):
            pdf.image(screenshot_path, x=10, y=pdf.get_y(), w=pdf.w - 20)
            pdf.ln(10)

        # Add hyperlinks
        for j, page in enumerate(content['pages']):
            link_text = f"{j+1}. {page['title']}"
            pdf.set_font('Arial', 'U', 12)
            pdf.set_text_color(0, 0, 255)
            pdf.cell(0, 10, link_text, ln=True, link=page['url'])
            pdf.set_text_color(0, 0, 0)  # Reset text color
            pdf.ln(5)

        pdf.output(pdf_file)

    zip_path = os.path.join(base_folder, 'website_archive.zip')
    create_zip(base_folder, zip_path)

    return zip_path
