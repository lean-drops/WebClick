import os
import logging
from app import create_app
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize the Flask app with debug mode based on environment
app = create_app()
app.debug = os.getenv('DEBUG', 'True').lower() in ['true', '1', 't']

# Centralized logging configuration with file handler
def configure_logging():
    """Configure logging with a structured and scalable format."""
    logging.basicConfig(
        level=logging.DEBUG if app.debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("app.log", mode='a')  # Logs to a file for persistence
        ],
    )
    return logging.getLogger(__name__)

logger = configure_logging()

if __name__ == '__main__':
    logger.info(f"Starting Flask application with debug mode {'enabled' if app.debug else 'disabled'}.")
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8022)))
