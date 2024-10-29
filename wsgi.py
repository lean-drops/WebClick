# /var/www/www_e-archival_ch_wsgi.py

import sys
import os
import logging
from starlette.middleware.wsgi import WSGIMiddleware
from app.main import app  # Deine FastAPI-App

# Projektverzeichnis zum Python-Pfad hinzufügen
project_home = '/home/digitalherodot/WebClick'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Logging konfigurieren (optional)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
logger.debug("WSGI-Konfiguration gestartet.")

# FastAPI-App in WSGI umwandeln
application = WSGIMiddleware(app)
logger.debug("WSGIMiddleware gesetzt.")
