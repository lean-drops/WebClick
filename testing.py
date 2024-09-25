import webbrowser
import random
from quart import Blueprint, render_template

# Blueprint initialisieren
main = Blueprint('main', __name__)

# Liste von echten Begriffen (Beispiele)
sample_terms = [
    'https://example.com', 'https://google.com', 'https://github.com',
    'https://stackoverflow.com', 'https://python.org', 'https://quart.palletsprojects.com',
    'https://wikipedia.org', 'https://reddit.com', 'https://twitter.com', 'https://linkedin.com'
]

# Route für das Testen, die eine randomisierte Liste von Links ins Modal lädt
@main.route('/test_modal', methods=['GET'])
async def test_modal_route():
    # Nimm eine Zufallsstichprobe von Links (z.B. 5 Links)
    random_links = random.sample(sample_terms, 5)

    # Rendere die HTML-Vorlage 'scrape_result.html' mit den randomisierten Links
    return await render_template('scrape_result.html', links=random_links)

# Funktion, um den Browser nach Start automatisch zu öffnen
def open_browser():
    webbrowser.open_new('http://127.0.0.1:5000/test_modal')

# App-Start logik
if __name__ == '__main__':
    from quart import Quart
    app = Quart(__name__)

    # Registriere das Blueprint
    app.register_blueprint(main)

    # Starte die App in einem neuen Thread und öffne den Browser
    import threading
    threading.Timer(1.25, open_browser).start()  # Warte ein wenig, um sicherzustellen, dass der Server läuft
    app.run()
