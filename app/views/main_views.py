# app/routes/main_views.py

import time
from flask import render_template

from . import main

@main.route('/')
def index():
    version = str(int(time.time()))  # Zeitstempel für Caching von Ressourcen
    return render_template('index.html', version=version)
