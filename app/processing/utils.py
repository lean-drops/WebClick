# app/processing/utils.py

import os
import logging
from typing import List
from urllib.parse import urlparse
import hashlib

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

def sanitize_filename(url: str) -> str:
    """Erstellt einen sicheren und eindeutigen Dateinamen aus einer URL."""
    parsed_url = urlparse(url)
    path = parsed_url.path.replace('/', '_').strip('_') or 'root'
    hash_digest = hashlib.sha256(url.encode()).hexdigest()[:10]  # Kurzer Hash zur Einzigartigkeit
    filename = f"{parsed_url.netloc}_{path}_{hash_digest}.pdf"
    logger.debug(f"Sanitized Filename: {filename}")
    return filename

def extract_domain(url: str) -> str:
    """Extrahiert den Domain-Namen ohne 'www' und TLD."""
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    if domain.startswith('www.'):
        domain = domain[4:]
    domain_main = domain.split('.')[0]
    logger.debug(f"Extracted Domain: {domain_main}")
    return domain_main

def get_urls() -> List[str]:
    """
    Gibt die Liste der URLs zurück, die konvertiert werden sollen.
    """
    try:
        from app.listen import urls  # Stelle sicher, dass listen.py die URLs enthält
        logger.info(f"{len(urls)} URLs für die Verarbeitung bereitgestellt.")
        return urls
    except ImportError as e:
        logger.error(f"Fehler beim Importieren von URLs: {e}")
        return []

def setup_directories(output_directory: str):
    """
    Richtet die erforderlichen Ausgabe-Verzeichnisse ein.
    """
    os.makedirs(output_directory, exist_ok=True)
    individual_collapsed = os.path.join(output_directory, 'individual_pdfs_collapsed')
    individual_expanded = os.path.join(output_directory, 'individual_pdfs_expanded')
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
OUTPUT_DIRECTORY = os.getenv("OUTPUT_DIRECTORY", "output_pdfs")
os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)

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

async def remove_unwanted_elements(page: Page, expanded: bool = False):
    """
    Entfernt unerwünschte Elemente wie Banner, Pop-ups und Cookie-Banner,
    ohne das Layout der Seite zu beeinträchtigen. Im expanded-Modus werden bestimmte Elemente beibehalten.
    """
    logger.info("Entferne unerwünschte Elemente wie Banner und Pop-ups.")
    try:
        from app.processing.listen import selectors  # Stelle sicher, dass listen.py die Selektoren enthält

        # Basis-Selektoren, die immer entfernt werden sollen
        base_selectors = [
            'div[class*="cookie"]',
            'div[class*="popup"]',
            'div[class*="subscribe"]',
            'div[id*="cookie"]',
            'div[id*="popup"]',
            'div[id*="subscribe"]',

            '.advertisement',
            '.adsbygoogle',
            '.modal',
            '.overlay',
            '.subscribe-modal',
            '.cookie-consent',
            'button[class*="close"]',
            'button[class*="dismiss"]',
            'button[class*="agree"]',
            'button[id*="close"]',
            'button[id*="dismiss"]',
            'button[id*="agree"]',
        ]

        # Zusätzliche Selektoren, die nur im normal-Modus entfernt werden sollen
        conditional_selectors = []
        if not expanded:
            conditional_selectors.extend([
                'div[class*="banner"]',
                'div[class*="anchornav__content"]',
                '.side-banner',
                '#side-index',
                '.fixed-sidebar',
                '#navigation-bar',
                'div.cell.tiny-12.xsmall-12.small-10.medium-10.large-2.xlarge-2',
                'div.mdl-anchornav',  # Gezieltes Entfernen aller mdl-anchornav Elemente
                '#toc',                # Gezieltes Entfernen des toc ID
            ])

        # Kombiniere die Selektoren
        all_selectors = base_selectors + selectors + conditional_selectors

        # Entferne die ausgewählten Elemente, indem ihre Anzeige auf 'none' gesetzt wird
        if all_selectors:
            await page.evaluate(f"""
                () => {{
                    const selectors = {all_selectors};
                    selectors.forEach(selector => {{
                        const elements = document.querySelectorAll(selector);
                        elements.forEach(el => {{
                            el.style.display = 'none';
                        }});
                    }});
                }}
            """)
            logger.debug(f"Entfernte Elemente: {all_selectors}")
        else:
            logger.warning("Keine Selektoren zum Entfernen gefunden.")
    except ImportError:
        logger.error("Fehler beim Importieren von Selektoren aus listen.py.")
    except Exception as e:
        logger.error(f"Fehler beim Entfernen unerwünschter Elemente: {e}")

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

async def inject_custom_css(page: Page, expanded: bool = False):
    """
    Injezieren von benutzerdefinierten CSS-Regeln, um die Darstellung der Seite zu optimieren.
    """
    logger.info("Injezieren von benutzerdefiniertem CSS.")
    try:
        if not expanded:
            await page.add_style_tag(content="""
                /* Entferne alle mdl-anchornav Navigationsmenüs */
                .mdl-anchornav {
                    display: none !important;
                }

                /* Entferne die Navigationsleiste */
                header#header {
                    display: none !important;
                }

                /* Anpassungen für den normalen Modus */
                body {
                    max-width: none !important;
                    width: 100% !important;
                }

                /* Anpassung der Schriftgröße für atm-heading im Normal-Modus */
                h3.atm-heading {
                    font-size: 1.2em !important;
                    line-height: 1.4 !important;
                }
                h2.atm-heading {
                    font-size: 1.8em !important;
                    line-height: 1.5 !important;
                }

                @media print {
                    /* Standardmäßig den Header ausblenden */
                    header#header {
                        display: none !important;
                    }

                    /* Nur auf der ersten Seite den Header anzeigen */
                    @page :first {
                        header#header {
                            display: block !important;
                            position: fixed;
                            top: 0;
                            width: 100%;
                            /* Weitere Stile nach Bedarf */
                        }
                    }

                    /* Platzhalter schaffen, damit der Inhalt nicht vom Header verdeckt wird */
                    body {
                        margin-top: 100px; /* Höhe des Headers anpassen */
                    }
                }
            """)
            logger.debug("CSS für den normal-Modus erfolgreich injiziert.")
        else:
            await page.add_style_tag(content="""
                /* Optimiere das Layout für den expanded-Modus */
                body {
                    max-width: none !important;
                    width: 100% !important;
                }

                .mdl-anchornav {
                    display: block !important;
                    position: fixed !important;
                    top: 0 !important;
                    left: 0 !important;
                    width: 300px !important;
                    height: 100% !important;
                    overflow: auto !important;
                    background-color: white !important;
                    box-shadow: 2px 0 5px rgba(0,0,0,0.1) !important;
                    z-index: 1000 !important;
                }

                /* Stelle sicher, dass der Hauptinhalt nicht von der Navigation überlappt wird */
                .main-content {
                    margin-left: 320px !important;
                }

                /* Anpassung der Schriftgröße für atm-heading im Expanded-Modus */
                h3.atm-heading {
                    font-size: 1.0em !important;
                    line-height: 1.3 !important;
                }
                h2.atm-heading {
                    font-size: 1.6em !important;
                    line-height: 1.4 !important;
                }
            """)
            logger.debug("CSS für den expanded-Modus erfolgreich injiziert.")
    except Exception as e:
        logger.error(f"Fehler beim Injizieren von CSS: {e}")


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
    urls = get_urls()

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
                    screenshot_collapsed_path = os.path.join(OUTPUT_DIRECTORY, 'individual_pdfs_collapsed', screenshot_collapsed)
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
                    screenshot_expanded_path = os.path.join(OUTPUT_DIRECTORY, 'individual_pdfs_expanded', screenshot_expanded)
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