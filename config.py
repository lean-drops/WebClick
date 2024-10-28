import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, ConfigDict
import logging
import logging.config


class Settings(BaseSettings):
    # Basisverzeichnis des Projekts
    BASE_DIR: Path = Path('.').resolve()

    # App-Verzeichnis
    APP_DIR: Path = Field(default=Path('app'))

    # Static-Verzeichnis innerhalb der App
    STATIC_DIR: Path = Field(default=Path('static'))

    # Weitere Verzeichnisse innerhalb Static
    CSS_DIR: Path = Field(default=Path('css'))
    IMG_DIR: Path = Field(default=Path('img'))
    JS_DIR: Path = Field(default=Path('js'))
    JSON_DIR: Path = Field(default=Path('json'))

    # Weitere Verzeichnisse innerhalb App
    TEMPLATES_DIR: Path = Field(default=Path('templates'))
    UTILS_DIR: Path = Field(default=Path('utils'))

    # Cache-Verzeichnisse
    CACHE_DIR: Path = Field(default=Path('cache'))
    MAPPING_CACHE_DIR: Path = Field(default=Path('mapping_cache'))

    # Logs-Verzeichnis
    LOGS_DIR: Path = Field(default=Path('logs'))

    # Output PDFs-Verzeichnis
    OUTPUT_PDFS_DIR: Path = Field(default=Path('output_pdfs'))

    # Pfade zu spezifischen Dateien
    TABOO_JSON_FILE: Path = Field(default=Path('taboo.json'))
    COOKIES_SELECTOR_JSON_FILE: Path = Field(default=Path('cookies_selector.json'))
    EXCLUDE_SELECTORS_JSON_FILE: Path = Field(default=Path('exclude_selectors.json'))
    URLS_JSON_FILE: Path = Field(default=Path('urls.json'))

    # Einstellungen
    MAX_WORKERS: int = 4
    LOG_LEVEL: str = 'DEBUG'

    # Konfigurationsoptionen für Pydantic V2
    model_config = ConfigDict(
        env_file='.env',
        extra='forbid',  # Verhindert das Zulassen unerwarteter Felder
    )

    # Validatoren zur Sicherstellung, dass alle Pfade als `Path` Objekte behandelt werden



def setup_logging(log_level: str, log_file: Path) -> logging.Logger:
    log_dict = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'standard',
                'level': log_level,
            },
            'file': {
                'class': 'logging.FileHandler',
                'formatter': 'standard',
                'filename': str(log_file),
                'level': log_level,
            },
        },
        'loggers': {
            '': {  # Root logger
                'handlers': ['console', 'file'],
                'level': log_level,
                'propagate': True,
            },
        },
    }

    logging.config.dictConfig(log_dict)
    logger = logging.getLogger(__name__)
    logger.debug("Logging erfolgreich konfiguriert.")
    return logger


def check_directories(directories: List[Path], logger: logging.Logger):
    missing_dirs = []
    for directory in directories:
        if not directory.exists():
            missing_dirs.append(directory)
            logger.error(f"Fehlendes Verzeichnis: {directory}")
        else:
            logger.debug(f"Verzeichnis vorhanden: {directory}")

    if missing_dirs:
        missing_paths = "\n".join(str(dir) for dir in missing_dirs)
        raise RuntimeError(f"Die folgenden Verzeichnisse fehlen und müssen manuell erstellt werden:\n{missing_paths}")


# Initialisierung der Konfiguration
try:
    settings = Settings()
except Exception as e:
    raise RuntimeError(f"Fehler beim Laden der Konfiguration: {e}")

# Einrichtung des Loggings
logger = setup_logging(settings.LOG_LEVEL, settings.LOGS_DIR / 'app.log')

# Vollständige Pfade zu spezifischen Dateien
TABOO_JSON_PATH = settings.JSON_DIR / settings.TABOO_JSON_FILE
COOKIES_SELECTOR_JSON_PATH = settings.JSON_DIR / settings.COOKIES_SELECTOR_JSON_FILE
EXCLUDE_SELECTORS_JSON_PATH = settings.JSON_DIR / settings.EXCLUDE_SELECTORS_JSON_FILE
URLS_JSON_PATH = settings.JSON_DIR / settings.URLS_JSON_FILE


def main():
    # Sicherstellen, dass alle wichtigen Verzeichnisse existieren
    important_dirs = [
        settings.BASE_DIR,
        settings.APP_DIR,
        settings.STATIC_DIR,
        settings.CSS_DIR,
        settings.IMG_DIR,
        settings.JS_DIR,
        settings.JSON_DIR,
        settings.TEMPLATES_DIR,
        settings.UTILS_DIR,
        settings.CACHE_DIR,
        settings.MAPPING_CACHE_DIR,
        settings.LOGS_DIR,
        settings.OUTPUT_PDFS_DIR,
    ]
    check_directories(important_dirs, logger)

    # Beispielhafte Nutzung der Konfiguration
    print(f"BASE_DIR: {settings.BASE_DIR}")
    print(f"APP_DIR: {settings.APP_DIR}")
    print(f"STATIC_DIR: {settings.STATIC_DIR}")
    print(f"CSS_DIR: {settings.CSS_DIR}")
    print(f"IMG_DIR: {settings.IMG_DIR}")
    print(f"JS_DIR: {settings.JS_DIR}")
    print(f"JSON_DIR: {settings.JSON_DIR}")
    print(f"TEMPLATES_DIR: {settings.TEMPLATES_DIR}")
    print(f"UTILS_DIR: {settings.UTILS_DIR}")
    print(f"CACHE_DIR: {settings.CACHE_DIR}")
    print(f"MAPPING_CACHE_DIR: {settings.MAPPING_CACHE_DIR}")
    print(f"LOGS_DIR: {settings.LOGS_DIR}")
    print(f"OUTPUT_PDFS_DIR: {settings.OUTPUT_PDFS_DIR}")
    print(f"TABOO_JSON_PATH: {TABOO_JSON_PATH}")
    print(f"COOKIES_SELECTOR_JSON_PATH: {COOKIES_SELECTOR_JSON_PATH}")
    print(f"EXCLUDE_SELECTORS_JSON_PATH: {EXCLUDE_SELECTORS_JSON_PATH}")
    print(f"URLS_JSON_PATH: {URLS_JSON_PATH}")
    print(f"MAX_WORKERS: {settings.MAX_WORKERS}")
    print(f"LOG_LEVEL: {settings.LOG_LEVEL}")

    logger.info("Konfiguration erfolgreich geladen:")
    logger.info(f"BASE_DIR: {settings.BASE_DIR}")
    logger.info(f"APP_DIR: {settings.APP_DIR}")
    logger.info(f"STATIC_DIR: {settings.STATIC_DIR}")
    logger.info(f"CSS_DIR: {settings.CSS_DIR}")
    logger.info(f"IMG_DIR: {settings.IMG_DIR}")
    logger.info(f"JS_DIR: {settings.JS_DIR}")
    logger.info(f"JSON_DIR: {settings.JSON_DIR}")
    logger.info(f"TEMPLATES_DIR: {settings.TEMPLATES_DIR}")
    logger.info(f"UTILS_DIR: {settings.UTILS_DIR}")
    logger.info(f"CACHE_DIR: {settings.CACHE_DIR}")
    logger.info(f"MAPPING_CACHE_DIR: {settings.MAPPING_CACHE_DIR}")
    logger.info(f"LOGS_DIR: {settings.LOGS_DIR}")
    logger.info(f"OUTPUT_PDFS_DIR: {settings.OUTPUT_PDFS_DIR}")
    logger.info(f"TABOO_JSON_PATH: {TABOO_JSON_PATH}")
    logger.info(f"COOKIES_SELECTOR_JSON_PATH: {COOKIES_SELECTOR_JSON_PATH}")
    logger.info(f"EXCLUDE_SELECTORS_JSON_PATH: {EXCLUDE_SELECTORS_JSON_PATH}")
    logger.info(f"URLS_JSON_PATH: {URLS_JSON_PATH}")
    logger.info(f"MAX_WORKERS: {settings.MAX_WORKERS}")
    logger.info(f"LOG_LEVEL: {settings.LOG_LEVEL}")


if __name__ == "__main__":
    main()
