from playwright.async_api import Page

from config import logger


async def remove_unwanted_elements(page: Page, expanded: bool = False):
    """Removes unwanted elements from the page."""
    try:
        selectors = [
            'script',
            'noscript',
            'style',
            'iframe',
            'footer',
            'div.ads',
            # Add more unwanted elements
        ]

        if expanded:
            selectors.extend([
                # Removed 'header' from here
                'nav',
                '.sidebar',
                '#navigation',
                '.mdl-anchornav',
                '#header',
                '.mdl-header',
                '#toc',
                '.mdl-footer',
                '#footer',
                # Add more selectors specific for Navbar and Sidebar
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
    Removes the navigation bar and all sidebars from the page, but keeps the header.
    """
    logger.info("Removing the navigation bar and sidebars.")
    try:
        await page.evaluate("""
            // Remove navigation bars (excluding header)
            const navs = document.querySelectorAll('nav');
            navs.forEach(nav => {
                nav.style.display = 'none';
            });

            // Remove all sidebars with the class 'mdl-anchornav' or similar classes
            const sidebars = document.querySelectorAll('div.mdl-anchornav, aside.sidebar, .sidebar');
            sidebars.forEach(sidebar => {
                sidebar.style.display = 'none';
            });
        """)
        logger.debug("Navigation bar and sidebars successfully removed.")
    except Exception as e:
        logger.error(f"Error removing navigation bar and sidebars: {e}")

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