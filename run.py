import os
import socket
import logging
from importlib import reload
from app import create_app
import time
# Deactivate SSL warnings for unverified HTTPS requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Create the Quart application
app = create_app()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG level
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def ensure_module_reloaded(module_name):
    """Reloads a module to ensure the latest version is used."""
    try:
        logger.debug(f"Reloading module: {module_name}")
        module = __import__(module_name)
        reload(module)
        logger.debug(f"Successfully reloaded module: {module_name}")
    except Exception as e:
        logger.error(f"Failed to reload module {module_name}: {e}", exc_info=True)

if __name__ == '__main__':
    # Always reload the 'app' module to ensure the latest version is used
    ensure_module_reloaded('app')

    # Determine debug mode from environment variable
    debug_mode = os.getenv('FLASK_DEBUG', 'True').lower() in ['true', '1', 't']
    logger.debug(f"Debug mode set to: {debug_mode}")

    # Check if the default port 5000 is occupied, and switch if necessary
    port = int(os.getenv('PORT', 5000))
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if sock.connect_ex(('127.0.0.1', port)) == 0:
        logger.warning(f"Port {port} is occupied. Switching to port {port + 1}.")
        port += 1
    sock.close()

    try:
        # Start the application
        logger.info(f"Starting the application on port {port} with debug mode {'enabled' if debug_mode else 'disabled'}.")
        app.run(debug=debug_mode, port=port)
    except Exception as e:
        logger.error(f"An error occurred while running the application: {e}", exc_info=True)
