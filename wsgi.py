import sys
import os

# Pfad zu deinem Projekt hinzufügen
project_home = '/home/digitalherodot/your_project_directory'  # Ersetze mit deinem Pfad
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Virtuelle Umgebung aktivieren
activate_env = '/home/digitalherodot/webclick-venv/bin/activate_this.py'
if os.path.exists(activate_env):
    with open(activate_env) as f:
        exec(f.read(), {'__file__': activate_env})

# Flask-Anwendung importieren
from app import app as application
