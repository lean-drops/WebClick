# WSGI-Konfigurationsdatei für PythonAnywhere

import sys
import os

# Der Pfad zu deinem Projektverzeichnis (Anpassung an deine Verzeichnisstruktur)
project_home = '/Users/python/Satelite 1 Python Projekte/Archiv/WebClick'
if project_home not in sys.path:
    sys.path.append(project_home)

# Setze die Umgebungsvariable für das Flask-Anwendungspaket (falls erforderlich)
os.environ['FLASK_APP'] = 'app'  # Passe den Namen deines Flask-App-Pakets an

# Flask-Anwendung importieren
from app import create_app

# Flask-Anwendung für WSGI
application = create_app()

