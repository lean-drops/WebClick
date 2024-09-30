import os
import socket
import logging
from importlib import reload
from app import create_app
import urllib3
from contextlib import closing

# Disable SSL warnings for unverified HTTPS requests, ensuring this is done carefully
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Initialize the application
app = create_app()

# Centralized logging configuration following industry best practices
def configure_logging():
    """Configure logging with a structured and scalable format."""
    logging.basicConfig(
        level=logging.DEBUG if os.getenv('FLASK_DEBUG', 'True').lower() in ['true', '1', 't'] else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()],
    )
    logger = logging.getLogger(__name__)
    return logger

logger = configure_logging()

def ensure_module_reloaded(module_name):
    """Reload a module to ensure the latest version is used."""
    try:
        logger.debug(f"Reloading module: {module_name}")
        module = __import__(module_name)
        reload(module)
        logger.debug(f"Successfully reloaded module: {module_name}")
    except Exception as e:
        logger.exception(f"Failed to reload module {module_name}", exc_info=True)

def find_free_port(default_port=5000, max_attempts=10):
    """Find an available port starting from the default, with retries."""
    for attempt in range(max_attempts):
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            if sock.connect_ex(('127.0.0.1', default_port)) != 0:
                logger.info(f"Port {default_port} is free.")
                return default_port
            logger.warning(f"Port {default_port} is occupied. Trying port {default_port + 1}.")
            default_port += 1
    raise RuntimeError(f"Could not find a free port after {max_attempts} attempts.")

def start_application():
    """Start the Quart application."""
    # Ensure 'app' module is reloaded to reflect any recent changes
    ensure_module_reloaded('app')

    # Get debug mode from environment or default to True
    debug_mode = os.getenv('FLASK_DEBUG', 'True').lower() in ['true', '1', 't']
    logger.debug(f"Debug mode is {'enabled' if debug_mode else 'disabled'}")

    # Find an available port or default to 5000
    port = find_free_port(int(os.getenv('PORT', 5000)))

    try:
        # Start the application with logging on port and mode
        logger.info(f"Starting application on port {port} with debug mode {'enabled' if debug_mode else 'disabled'}.")
        app.run(debug=debug_mode, port=port)
    except Exception as e:
        logger.exception(f"Failed to start application: {e}", exc_info=True)
        raise

if __name__ == '__main__':
    start_application()
