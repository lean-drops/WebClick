# wsgi.py

import sys
import os
from config import BASE_DIR
from app import create_app
import logging

# Füge das Projektverzeichnis zum Python-Pfad hinzu
project_home = BASE_DIR
if str(project_home) not in sys.path:
    sys.path.insert(0, str(project_home))

# Setze die Umgebungsvariable für die Flask-Anwendung, falls erforderlich
os.environ['FLASK_APP'] = 'wsgi.py'

# Erstelle die Flask-Anwendung
application = create_app()

# Optional: Logging konfigurieren, falls benötigt
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(BASE_DIR / 'logs' / 'app.log')
    ]
)
logger = logging.getLogger(__name__)
logger.debug("Flask-Anwendung wurde erstellt.")
