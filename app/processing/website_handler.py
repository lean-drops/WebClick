import asyncio
from playwright.async_api import Page

from config import logger


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