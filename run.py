import os
import socket
import logging
import traceback
from app import create_app

# Erstelle die Quart-Anwendung
app = create_app()

# Konfiguriere Logging
logging.basicConfig(
    level=logging.DEBUG,  # Setze auf DEBUG-Level
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    # Setze Debug-Modus basierend auf einer Umgebungsvariablen
    debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() in ['true', '1', 't']
    logger.debug(f"Debug mode set to: {debug_mode}")

    # Finde einen freien Port, falls der Standardport 5000 belegt ist
    port = int(os.environ.get('PORT', 5001))
    if port == 5001:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        if result == 0:
            logger.warning(f"Port {port} is occupied. Switching to port 5001.")
            port = 5001  # Ändere den Port, wenn 5000 belegt ist
        else:
            logger.debug(f"Port {port} is available.")
        sock.close()

    try:
        # Starte die Anwendung
        logger.info(f"Starting the application on port {port} with debug mode {'enabled' if debug_mode else 'disabled'}.")
        app.run(debug=debug_mode, port=port)
    except Exception as e:
        # Fange Ausnahmen ab und gib eine detaillierte Fehlermeldung aus
        logger.error(f"An error occurred while running the application: {e}")
        logger.debug("Detailed traceback information: ", exc_info=True)
