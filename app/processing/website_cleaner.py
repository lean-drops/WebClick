from playwright.async_api import Page

from config import logger


async def remove_unwanted_elements(page: Page, expanded: bool = False):
    """Entfernt unerwünschte Elemente von der Seite."""
    try:
        # Gemeinsame Selektoren zum Entfernen
        selectors = [
            'script',
            'noscript',
            'style',
            'iframe',
            'footer',
            'div.ads',
            # Füge weitere unerwünschte Elemente hinzu
        ]

        if expanded:
            # Zusätzliche Selektoren zum Entfernen im expanded Modus
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
                # Füge weitere Selektoren spezifisch für Navbar und Sidebar hinzu
            ])

        for selector in selectors:
            await page.evaluate(f'''
                const elements = document.querySelectorAll('{selector}');
                elements.forEach(el => el.remove());
            ''')
        logger.debug(f"Unerwünschte Elemente entfernt: {selectors}")
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
                const headers = document.querySelectorAll('header, nav');
                headers.forEach(header => {
                    header.style.display = 'none';
                });

                // Entferne alle Sidebars mit der Klasse 'mdl-anchornav' oder ähnlichen Klassen
                const sidebars = document.querySelectorAll('div.mdl-anchornav, aside.sidebar, .sidebar');
                sidebars.forEach(sidebar => {
                    sidebar.style.display = 'none';
                });
            }
        """)
        logger.debug("Navigationsleiste und Sidebars erfolgreich entfernt.")
    except Exception as e:
        logger.error(f"Fehler beim Entfernen der Navigationsleiste und Sidebars: {e}")
    pass

async def remove_fixed_elements(page: Page):
    # """
    # Entfernt alle fixierten Elemente auf der Seite, einschließlich solcher mit position: fixed oder position: sticky.
    # """
    # logger.info("Entferne alle fixierten Elemente auf der Seite.")
    # try:
    #     await page.evaluate("""
    #         () => {
    #             const fixedElements = Array.from(document.querySelectorAll('*')).filter(el => {
    #                 const style = window.getComputedStyle(el);
    #                 return (style.position === 'fixed' || style.position === 'sticky') && (el.offsetWidth > 0 || el.offsetHeight > 0);
    #             });
    #             fixedElements.forEach(el => {
    #                 el.style.display = 'none';
    #             });
    #         }
    #     """)
    #     logger.debug("Fixierte Elemente erfolgreich entfernt.")
    # except Exception as e:
    #     logger.error(f"Fehler beim Entfernen fixierter Elemente: {e}")
    pass