# app/routes/__init__.py

from flask import Blueprint

# Blueprint initialisieren
main = Blueprint('main', __name__)

# Importieren der Views
from . import main_views
from . import scrape_views
from . import pdf_views
