# wsgi.py

import sys
import os
from config import BASE_DIR, check_system_and_port
import logging

# Der Pfad zu deinem Projektverzeichnis (Anpassung an deine Verzeichnisstruktur)
project_home = BASE_DIR
if project_home not in sys.path:
    sys.path.append(project_home)

# Setze die Umgebungsvariable für das Flask-Anwendungspaket (falls erforderlich)
os.environ['FLASK_APP'] = 'app'  # Passe den Namen deines Flask-App-Pakets an

# Flask-Anwendung importieren
from app import create_app

# Überprüfe System und Port
config = check_system_and_port()
MAX_WORKERS = config['max_workers']
PORT = config['port']

logger = logging.getLogger(__name__)
logger.info(f"Starte Anwendung mit {MAX_WORKERS} Workern auf Port {PORT}")
print(f"Starte Anwendung mit {MAX_WORKERS} Workern auf Port {PORT}")

# Flask-Anwendung für WSGI
application = create_app()
