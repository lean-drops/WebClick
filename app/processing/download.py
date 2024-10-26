# download.py

import os
import asyncio
import logging
from playwright.async_api import async_playwright
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
OUTPUT_DIRECTORY = "output_directory"
os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)

# Semaphore to limit concurrent tasks
SEM = asyncio.Semaphore(5)  # Adjust as needed

def sanitize_filename(url: str) -> str:
    """Create a safe filename from a URL."""
    return "".join(c if c.isalnum() else "_" for c in url)

async def render_page(url: str) -> dict:
    """Render the web page and create a PDF with Playwright."""
    async with SEM:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, timeout=60000)  # Increase timeout to 60 seconds

                # Optionally expand collapsible elements
                await page.evaluate("""
                    const elements = document.querySelectorAll('details');
                    elements.forEach(el => {
                        el.setAttribute('open', '');
                    });
                """)

                # Wait until the page is fully loaded
                await page.wait_for_load_state('networkidle')

                # Create PDF
                filename = sanitize_filename(url)
                pdf_path = os.path.join(OUTPUT_DIRECTORY, f"{filename}.pdf")
                await page.pdf(path=pdf_path, format='A4', print_background=True)

                await browser.close()
                logger.info(f"PDF created: {pdf_path}")
                return {"url": url, "status": "success", "path": pdf_path}

        except Exception as e:
            logger.error(f"Error rendering page {url}: {e}")
            return {"url": url, "status": "error", "error": str(e)}
