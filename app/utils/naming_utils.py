import re
import unicodedata
from urllib.parse import urlparse
import logging
from slugify import slugify  # Importiere die slugify-Funktion

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str) -> str:
    """
    Normalisiert den Dateinamen, entfernt nicht-ASCII-Zeichen und ersetzt Leerzeichen und Sonderzeichen.
    Nutzt die slugify-Bibliothek für eine verbesserte Lesbarkeit.

    Args:
        filename (str): Der zu sanitierende Dateiname.

    Returns:
        str: Der sanitierte Dateiname.
    """
    # Verwende slugify, um den Dateinamen zu normalisieren und lesbar zu machen
    sanitized = slugify(filename, separator='_', lowercase=False)
    logger.debug(f"Sanitized Filename: {filename} to {sanitized}")
    return sanitized


def format_filename(filename: str) -> str:
    """
    Formatiert den Dateinamen, indem unerwünschte Zeichen entfernt und Unterstriche durch Leerzeichen ersetzt werden.
    Nutzt die slugify-Bibliothek für eine verbesserte Lesbarkeit.

    Args:
        filename (str): Der zu formatierende Dateiname.

    Returns:
        str: Der formatierte Dateiname.
    """
    # Verwende slugify mit separator=' ' und preserve_case=True für bessere Lesbarkeit
    formatted = slugify(filename, separator=' ', lowercase=False, allow_unicode=True)
    # Entferne führende und folgende Leerzeichen
    formatted = formatted.strip()
    logger.debug(f"Formatted Filename: {filename} to {formatted}")
    return formatted


def shorten_url(url: str) -> str:
    """
    Kürzt die URL, um einen ordnerfreundlichen und lesbaren Namen zu erstellen.
    Nutzt die slugify-Bibliothek zur Verbesserung der Lesbarkeit.

    Args:
        url (str): Die zu kürzende URL.

    Returns:
        str: Eine gekürzte und lesbare Version der URL.
    """
    parsed_url = urlparse(url)
    netloc = parsed_url.netloc.replace('www.', '')
    path = parsed_url.path.strip('/').replace('/', '_')

    # Kombiniere Netloc und Pfad und erstelle einen lesbaren Namen
    combined = f"{netloc}_{path}" if path else netloc
    # Verwende slugify, um den kombinierten String zu kürzen und lesbar zu machen
    short_name = slugify(combined, separator=' ', lowercase=False, allow_unicode=True)

    # Optional: Kürze den Namen auf eine maximale Länge, z.B. 50 Zeichen
    max_length = 50
    if len(short_name) > max_length:
        short_name = short_name[:max_length].rstrip()

    logger.debug(f"Shortened URL: {url} to {short_name}")
    return short_name
