import os
import logging
import uvicorn
from dotenv import load_dotenv
from config import BASE_DIR

# Laden Sie Umgebungsvariablen aus der .env-Datei
load_dotenv()


# Zentralisierte Logging-Konfiguration mit Datei-Handler
def configure_logging():
    log_level = logging.DEBUG if os.getenv('DEBUG', 'True').lower() in ['true', '1', 't'] else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(os.path.join(BASE_DIR, "app.log"), mode="a")
        ],
    )
    return logging.getLogger(__name__)


logger = configure_logging()

if __name__ == "__main__":
    debug_mode = os.getenv("DEBUG", "True").lower() in ["true", "1", "t"]
    logger.info(f"Starting FastAPI application with debug mode {'enabled' if debug_mode else 'disabled'}.")

    # Verwenden Sie den Import-String "app.main:app" für Uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=debug_mode)
