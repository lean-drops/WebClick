# app/processing/utils.py

import os
import logging
from typing import List
from urllib.parse import urlparse
import hashlib

from app.utils.naming_utils import sanitize_filename

# ======================= Logging Konfiguration =======================
logger = logging.getLogger("utils_logger")
logger.setLevel(logging.DEBUG)

# Erstelle einen Console-Handler mit einem höheren Log-Level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# Erstelle einen Formatter und füge ihn dem Handler hinzu
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)

# Füge den Handler dem Logger hinzu, falls noch nicht vorhanden
if not logger.handlers:
    logger.addHandler(ch)

# ======================= Hilfsfunktionen =======================


def extract_domain(url: str) -> str:
    """Extrahiert den Domain-Namen ohne 'www' und TLD."""
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    if domain.startswith('www.'):
        domain = domain[4:]
    domain_main = domain.split('.')[0]
    logger.debug(f"Extracted Domain: {domain_main}")
    return domain_main


def get_url(json_daten=None, eigene_urls=None):
    """
    Wählt eine zufällige URL aus einer Liste von URLs aus.

    :param json_daten: Ein JSON-Objekt mit einem Schlüssel "links", der eine Liste von URLs enthält.
    :param eigene_urls: Eine eigene Liste von URLs, die verwendet werden soll.
    :return: Eine zufällige URL als String.
    """
    if eigene_urls:
        urls = eigene_urls
    elif json_daten and "links" in json_daten:
        urls = json_daten["links"]
    else:
        # Standard-URLs, falls keine Eingabe erfolgt
        urls = [
            "https://www.zh.ch/de/staatskanzlei/regierungskommunikation.html",
            "https://www.zh.ch/de/wirtschaft-arbeit/handelsregister.html",
            "https://www.zh.ch/de/arbeiten-beim-kanton.html"
        ]

    if not urls:
        raise ValueError("Die URL-Liste ist leer.")

    import random
    return random.choice(urls)
def setup_directories(OUTPUT_PDFS_DIR: str):
    """
    Richtet die erforderlichen Ausgabe-Verzeichnisse ein.
    """
    os.makedirs(OUTPUT_PDFS_DIR, exist_ok=True)
    individual_collapsed = os.path.join(OUTPUT_PDFS_DIR, 'individual_pdfs_collapsed')
    individual_expanded = os.path.join(OUTPUT_PDFS_DIR, 'individual_pdfs_expanded')
    os.makedirs(individual_collapsed, exist_ok=True)
    os.makedirs(individual_expanded, exist_ok=True)
    logger.info(f"Ausgabe-Verzeichnisse eingerichtet: {individual_collapsed}, {individual_expanded}")

def load_js_file(file_path: str) -> str:
    """
    Lädt den Inhalt eines JS-Files und gibt ihn als String zurück.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            js_content = file.read()
        logger.debug(f"JS-Datei erfolgreich geladen: {file_path}")
        return js_content
    except FileNotFoundError:
        logger.error(f"JS-Datei nicht gefunden: {file_path}")
        return ""
    except Exception as e:
        logger.error(f"Fehler beim Laden der JS-Datei {file_path}: {e}")
        return ""
# app/processing/prepare.py

import asyncio
import os
import logging
from typing import List

from playwright.async_api import async_playwright, Page

# ======================= Konfiguration =======================

# Ausgabe-Verzeichnis
OUTPUT_PDFS_DIR = os.getenv("OUTPUT_PDFS_DIR", "output_pdfs")
os.makedirs(OUTPUT_PDFS_DIR, exist_ok=True)

# Logging konfigurieren
logger = logging.getLogger("prepare_logger")
logger.setLevel(logging.DEBUG)  # Setze auf DEBUG für ausführliches Logging

# Erstelle einen Console-Handler mit einem höheren Log-Level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# Erstelle einen Formatter und füge ihn dem Handler hinzu
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)

# Füge den Handler dem Logger hinzu
logger.addHandler(ch)

# ======================= URL Liste =======================


# ======================= Erweiterungsfunktionen =======================

async def expand_hidden_elements(page: Page):
    """
    Erweitert alle versteckten Elemente wie Dropdowns, Akkordeons und Details-Tags,
    um sicherzustellen, dass alle Inhalte sichtbar sind.
    """
    logger.info("Erweitere alle versteckten Elemente auf der Seite.")
    try:
        await page.evaluate("""
            () => {
                // Öffne alle <details> Elemente
                const details = document.querySelectorAll('details');
                details.forEach(detail => detail.open = true);

                // Klicke auf alle Elemente, die Klassen wie 'collapsible', 'expandable', 'accordion', oder 'toggle' enthalten
                const expandableElements = document.querySelectorAll('*[class*="collapsible"], *[class*="expandable"], *[class*="accordion"], *[class*="toggle"], *[data-toggle], *[data-expand]');
                expandableElements.forEach(el => {
                    // Überprüfen, ob das Element bereits erweitert ist, um unnötige Klicks zu vermeiden
                    const isExpanded = el.getAttribute('aria-expanded') === 'true' || el.classList.contains('expanded');
                    if (!isExpanded) {
                        if (typeof el.click === 'function') {
                            el.click();
                        } else {
                            // Fallback: Dispatch ein Click-Event
                            el.dispatchEvent(new Event('click'));
                        }
                    }
                });

                // Entferne Animationen und Übergänge, um das Layout stabil zu halten
                const style = document.createElement('style');
                style.innerHTML = `
                    * {
                        transition: none !important;
                        animation: none !important;
                    }
                `;
                document.head.appendChild(style);
            }
        """)
        logger.debug("Versteckte Elemente erfolgreich erweitert.")
        await asyncio.sleep(1)  # Warte kurz, um sicherzustellen, dass alle Klicks verarbeitet wurden
    except Exception as e:
        logger.error(f"Fehler beim Erweitern versteckter Elemente: {e}")

# app/processing/utils.py

async def remove_unwanted_elements(page: Page, expanded: bool = False):
    """Removes unwanted elements from the page."""
    try:
        # Common selectors to remove
        selectors = [
            'script',
            'noscript',
            'style',
            'iframe',
            'footer',
            'div.ads',
            # Add any other common unwanted elements here
        ]

        if expanded:
            # Additional selectors to remove in expanded mode
            selectors.extend([
                'header',
                'nav',
                '.sidebar',
                '#navigation',
                '.mdl-anchornav',
                '#header',
                '.mdl-header',
                '#toc',
                '.mdl-footer',
                '#footer',
                # Add any other selectors specific to the navbar and sidebar
            ])

        for selector in selectors:
            await page.evaluate(f'''
                const elements = document.querySelectorAll('{selector}');
                elements.forEach(el => el.remove());
            ''')
        logger.debug(f"Removed unwanted elements: {selectors}")
    except Exception as e:
        logger.error(f"Error removing unwanted elements: {e}")

async def remove_navigation_and_sidebars(page: Page):
    """
    Entfernt die Navigationsleiste und alle Sidebars von der Seite.
    """
    logger.info("Entferne die Navigationsleiste und Sidebars.")
    try:
        await page.evaluate("""
            () => {
                // Entferne die Navigationsleiste
                const header = document.querySelector('header#header');
                if (header) {
                    header.style.display = 'none';
                }

                // Entferne alle Sidebars mit der Klasse 'mdl-anchornav'
                const sidebars = document.querySelectorAll('div.mdl-anchornav');
                sidebars.forEach(sidebar => {
                    sidebar.style.display = 'none';
                });
            }
        """)
        logger.debug("Navigationsleiste und Sidebars erfolgreich entfernt.")
    except Exception as e:
        logger.error(f"Fehler beim Entfernen der Navigationsleiste und Sidebars: {e}")

async def remove_fixed_elements(page: Page):
    """
    Entfernt alle fixierten Elemente auf der Seite, einschließlich solcher mit position: fixed oder position: sticky.
    """
    logger.info("Entferne alle fixierten Elemente auf der Seite.")
    try:
        await page.evaluate("""
            () => {
                const fixedElements = Array.from(document.querySelectorAll('*')).filter(el => {
                    const style = window.getComputedStyle(el);
                    return (style.position === 'fixed' || style.position === 'sticky') && (el.offsetWidth > 0 || el.offsetHeight > 0);
                });
                fixedElements.forEach(el => {
                    el.style.display = 'none';
                });
            }
        """)
        logger.debug("Fixierte Elemente erfolgreich entfernt.")
    except Exception as e:
        logger.error(f"Fehler beim Entfernen fixierter Elemente: {e}")

async def scroll_page(page: Page):
    """
    Scrollt die Seite nach unten, um Lazy-Loading von Inhalten zu ermöglichen.
    """
    logger.info("Scrolle die Seite, um alle Inhalte zu laden.")
    try:
        previous_height = await page.evaluate("document.body.scrollHeight")
        while True:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            await asyncio.sleep(2)  # Warte, bis neue Inhalte geladen sind
            new_height = await page.evaluate("document.body.scrollHeight")
            if new_height == previous_height:
                break
            previous_height = new_height
        logger.debug("Seite vollständig gescrollt.")
    except Exception as e:
        logger.error(f"Fehler beim Scrollen der Seite: {e}")

# app/processing/utils.py

async def inject_custom_css(page: Page, expanded: bool = False):
    """Inject custom CSS into the page."""
    try:
        if expanded:
            css = '''
                /* Hide navbar and sidebar */
                header, nav, .sidebar, #navigation, .mdl-anchornav, #header, .mdl-header, #toc, .mdl-footer, #footer {
                    display: none !important;
                }
                /* Adjust page width */
                body {
                    margin: 0 auto;
                    width: 100%;
                }
                /* Additional CSS to make the page look nice and clean */
                .lyt-wrapper {
                    max-width: 100% !important;
                    padding: 0 !important;
                }
            '''
            await page.add_style_tag(content=css)
            logger.debug(f"Injected custom CSS for expanded mode.")
        else:
            # Inject CSS for collapsed mode if needed
            pass
    except Exception as e:
        logger.error(f"Error injecting custom CSS: {e}")


# app/processing/utils.py

import os
import logging

logger = logging.getLogger("utils_logger")


# ======================= Haupttestfunktion =======================

async def main_test():
    """
    Hauptfunktion zum Testen der prepare.py Funktionen.
    """
    logger.info("Starte Haupttestfunktion für prepare.py.")

    # Vorbereitung: Einrichtung der Verzeichnisse
    setup_directories()

    # Lade die URLs
    urls = get_url()

    if not urls:
        logger.error("Keine URLs zum Verarbeiten gefunden. Test abgebrochen.")
        return

    # Initialisiere Playwright und öffne den Browser
    logger.info("Initialisiere Playwright und starte den Browser.")
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True, args=[
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-infobars',
                '--window-size=2560,1440',  # Größere Fenstergröße
            ])
            context = await browser.new_context(
                viewport={"width": 2560, "height": 1440},  # Größere Breite und Höhe
                device_scale_factor=2,
                locale='de-DE',
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/94.0.4606.81 Safari/537.36"
                )
            )

            for url in urls:
                logger.info(f"Verarbeite URL: {url}")
                try:
                    page = await context.new_page()
                    await page.goto(url, timeout=120000, wait_until='load')  # Warten bis die Seite vollständig geladen ist
                    logger.info(f"Seite {url} erfolgreich geladen.")

                    # Schritt 1: Erweitere versteckte Elemente
                    await expand_hidden_elements(page)

                    # Schritt 2: Entferne unerwünschte Elemente im normal-Modus
                    await remove_unwanted_elements(page, expanded=False)

                    # Schritt 3: Entferne fixierte Elemente im normal-Modus
                    await remove_fixed_elements(page)

                    # Schritt 4: Entferne die Navigationsleiste und Sidebars
                    await remove_navigation_and_sidebars(page)

                    # Schritt 5: Injezieren von benutzerdefiniertem CSS für den normal-Modus
                    await inject_custom_css(page, expanded=False)

                    # Optional: Screenshot zur Überprüfung der Änderungen im normal-Modus
                    screenshot_collapsed = sanitize_filename(url).replace('.pdf', '_collapsed.png')
                    screenshot_collapsed_path = os.path.join(OUTPUT_PDFS_DIR, 'individual_pdfs_collapsed', screenshot_collapsed)
                    await page.screenshot(path=screenshot_collapsed_path, full_page=True)
                    logger.info(f"Screenshot im normal-Modus gespeichert: {screenshot_collapsed_path}")

                    # Schritt 6: Wiederhole die Schritte für den expanded-Modus
                    logger.info(f"Starte erweiterte Verarbeitung für URL: {url}")

                    # Erweitere versteckte Elemente erneut (falls nötig)
                    await expand_hidden_elements(page)

                    # Entferne unerwünschte Elemente im expanded-Modus (keine zusätzlichen)
                    await remove_unwanted_elements(page, expanded=True)

                    # Entferne fixierte Elemente im expanded-Modus (falls notwendig)
                    # In diesem Fall nicht notwendig, da Navigation beibehalten werden soll

                    # Injezieren von benutzerdefiniertem CSS für den expanded-Modus
                    await inject_custom_css(page, expanded=True)

                    # Optional: Screenshot zur Überprüfung der Änderungen im expanded-Modus
                    screenshot_expanded = sanitize_filename(url).replace('.pdf', '_expanded.png')
                    screenshot_expanded_path = os.path.join(OUTPUT_PDFS_DIR, 'individual_pdfs_expanded', screenshot_expanded)
                    await page.screenshot(path=screenshot_expanded_path, full_page=True)
                    logger.info(f"Screenshot im expanded-Modus gespeichert: {screenshot_expanded_path}")

                    await page.close()
                except Exception as e:
                    logger.error(f"Fehler bei der Verarbeitung von {url}: {e}")

            # Schließe den Kontext und den Browser
            await context.close()
            await browser.close()
            logger.info("Browser geschlossen.")

    except Exception as e:
        logger.critical(f"Unbehandelter Fehler beim Initialisieren von Playwright: {e}")

    logger.info("Haupttestfunktion abgeschlossen.")

# ======================= Ausführung des Haupttests =======================

if __name__ == "__main__":
    try:
        asyncio.run(main_test())
    except Exception as e:
        logger.critical(f"Unbehandelter Fehler im Hauptblock: {e}")
