import sys
import os
from config import BASE_DIR
from app.main import app  # Import the FastAPI app directly
import logging

# Add the project directory to the Python path
project_home = str(BASE_DIR)
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Optional: Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(BASE_DIR, 'logs', 'app.log'))
    ]
)
logger = logging.getLogger(__name__)
logger.debug("FastAPI application has been initialized.")

# Define the application entry point
application = app
