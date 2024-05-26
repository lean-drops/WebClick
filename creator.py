import os
import shutil


# Funktion zum Erstellen eines Verzeichnisses, wenn es nicht existiert
def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Directory created: {path}")
    else:
        print(f"Directory already exists: {path}")


# Funktion zum Erstellen und Schreiben einer Datei
def create_file(path, content):
    with open(path, 'w') as file:
        file.write(content)
    print(f"File created: {path}")


# Projektstruktur und Inhalte
project_structure = {
    "app": {
        "__init__.py": """from flask import Flask
from app.main.routes import main

def create_app():
    app = Flask(__name__)
    app.register_blueprint(main)
    return app
""",
        "main": {
            "__init__.py": "",
            "routes.py": """from flask import Blueprint, request, jsonify, render_template
import asyncio
from scrapers.scraper import scrape_website
from converters.pdf_converter import convert_to_pdf

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/archive', methods=['POST'])
async def archive():
    data = request.json
    urls = data.get('urls', [])
    if not urls:
        return jsonify({"error": "No URLs provided"}), 400

    loop = asyncio.get_event_loop()
    futures = [loop.run_in_executor(None, scrape_website, url) for url in urls]
    results = await asyncio.gather(*futures)

    pdf_file = await convert_to_pdf(results)

    return jsonify({"pdf_file": pdf_file}), 200

@main.route('/scrape', methods=['POST'])
async def scrape():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    content = scrape_website(url)
    return jsonify(content), 200

@main.route('/generate_pdf', methods=['POST'])
async def generate_pdf():
    data = request.json
    urls = data.get('urls', [])
    if not urls:
        return jsonify({"error": "No URLs provided"}), 400

    loop = asyncio.get_event_loop()
    futures = [loop.run_in_executor(None, scrape_website, url) for url in urls]
    results = await asyncio.gather(*futures)

    pdf_file = await convert_to_pdf(results)

    return jsonify({"pdf_file": pdf_file}), 200
"""
        },
        "templates": {
            "index.html": """<!DOCTYPE html>
<html lang="en" x-data="app()">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Website Archiver</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/alpinejs/3.9.1/cdn.min.js" defer></script>
</head>
<body>
    <div class="container">
        <h1>Website Archiver</h1>
        <input type="text" x-model="url" placeholder="Enter website URL">
        <button @click="scrapeWebsite">Scrape Website</button>
        <div x-show="pages.length > 0">
            <h2>Pages</h2>
            <table>
                <thead>
                    <tr>
                        <th>Select</th>
                        <th>Title</th>
                        <th>URL</th>
                    </tr>
                </thead>
                <tbody>
                    <template x-for="page in pages">
                        <tr>
                            <td><input type="checkbox" x-model="selectedUrls" :value="page.url"></td>
                            <td x-text="page.title"></td>
                            <td><a :href="page.url" target="_blank" x-text="page.url"></a></td>
                        </tr>
                    </template>
                </tbody>
            </table>
            <button @click="generatePDF">Generate PDF</button>
        </div>
        <div x-show="error" x-text="error" class="error"></div>
    </div>
    <script>
        function app() {
            return {
                url: '',
                pages: [],
                selectedUrls: [],
                error: '',
                scrapeWebsite() {
                    fetch('/scrape', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ url: this.url })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.error) {
                            this.error = data.error;
                            this.pages = [];
                        } else {
                            this.error = '';
                            this.pages = data.pages.map(page => ({ title: page.title, url: page.url }));
                        }
                    });
                },
                generatePDF() {
                    fetch('/generate_pdf', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ urls: this.selectedUrls })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.error) {
                            this.error = data.error;
                        } else {
                            window.location.href = data.pdf_file;
                        }
                    });
                }
            }
        }
    </script>
</body>
</html>
"""
        },
        "static": {
            "styles.css": """body {
    font-family: Arial, sans-serif;
    background-color: #f0f0f0;
    margin: 0;
    padding: 0;
}
.container {
    max-width: 800px;
    margin: 20px auto;
    padding: 20px;
    background-color: #fff;
    border-radius: 8px;
    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
}
h1 {
    font-size: 24px;
    margin-bottom: 20px;
}
input[type="text"] {
    width: calc(100% - 120px);
    padding: 10px;
    margin-right: 10px;
    border: 1px solid #ccc;
    border-radius: 4px;
}
button {
    padding: 10px 20px;
    border: none;
    background-color: #007bff;
    color: #fff;
    border-radius: 4px;
    cursor: pointer;
}
button:hover {
    background-color: #0056b3;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 20px;
}
th, td {
    padding: 10px;
    text-align: left;
    border-bottom: 1px solid #ddd;
}
th {
    background-color: #f2f2f2;
}
.error {
    color: red;
    margin-top: 20px;
}
"""
        }
    },
    "scrapers": {
        "__init__.py": "",
        "scraper.py": """import requests
from bs4 import BeautifulSoup

def scrape_website(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    pages = [{'title': link.text, 'url': link['href']} for link in soup.find_all('a', href=True)]
    content = {
        'pages': pages,
    }
    return content
"""
    },
    "converters": {
        "__init__.py": "",
        "pdf_converter.py": """from fpdf import FPDF

async def convert_to_pdf(contents):
    pdf = FPDF()
    pdf.add_page()
    for content in contents:
        pdf.set_xy(10, 10)
        pdf.set_font('Arial', 'B', 12)
        pdf.multi_cell(0, 10, content['html'])

        for img_url in content['images']:
            pdf.image(img_url, x=10, y=pdf.get_y(), w=100)

    pdf_output = 'output.pdf'
    pdf.output(pdf_output)
    return pdf_output
"""
    },
    "utils": {
        "__init__.py": "",
        "logger.py": """import logging

def setup_logger():
    logger = logging.getLogger('archive_logger')
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

logger = setup_logger()
"""
    },
    "run.py": """from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
""",
    "requirements.txt": """Flask
requests
beautifulsoup4
fpdf
alpinejs
"""
}


# Hauptfunktion zur Erstellung des Projekts
def create_project(structure, root="."):
    for name, content in structure.items():
        path = os.path.join(root, name)
        if isinstance(content, dict):
            create_directory(path)
            create_project(content, path)
        else:
            create_file(path, content)


# Projekt erstellen
create_project(project_structure)

# Kopieren des creator.py-Skripts in das aktuelle Verzeichnis
source = __file__
destination = os.path.join(".", "creator.py")
shutil.copy(source, destination)
print(f"creator.py copied to {destination}")
