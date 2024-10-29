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

# Centralized logging configuration with file handler
def configure_logging():
    logging.basicConfig(
        level=logging.DEBUG if app.debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("app.log", mode='a')
        ],
    )
    return logging.getLogger(__name__)

logger = configure_logging()

if __name__ == '__main__':
    logger.info(f"Starting Flask application with debug mode {'enabled' if app.debug else 'disabled'}.")
    # On PythonAnywhere, we can omit host and port as it defaults to their WSGI configuration.
    app.run()
