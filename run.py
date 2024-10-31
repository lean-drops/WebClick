# run.py

import os
import logging
from app.main import create_app
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize the Flask app
app = create_app()
app.debug = os.getenv('DEBUG', 'True').lower() in ['true', '1', 't']

# Determine if running on Heroku
IS_HEROKU = os.getenv('IS_HEROKU', 'False').lower() in ['true', '1', 't']

# Centralized logging configuration with file handler
def configure_logging():
    log_level = logging.DEBUG if app.debug else logging.INFO
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    handlers = [logging.StreamHandler()]

    if IS_HEROKU:
        # Logfile im /tmp-Verzeichnis auf Heroku
        handlers.append(logging.FileHandler('/tmp/app.log', mode='a'))
    else:
        # Lokales Logfile
        handlers.append(logging.FileHandler('app.log', mode='a'))

    logging.basicConfig(level=log_level, format=log_format, handlers=handlers)
    return logging.getLogger(__name__)

logger = configure_logging()

if __name__ == '__main__':
    logger.info(f"Starting Flask application with debug mode {'enabled' if app.debug else 'disabled'}.")
    # On Heroku, bind to the PORT environment variable
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
