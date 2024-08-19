import asyncio
import logging
import os
import shutil
import aiohttp
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from scrapers.create_directory import create_directory
from scrapers.link_processor import create_zip_file
from utils.naming_utils import sanitize_filename

# Logger konfigurieren
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

executor = ThreadPoolExecutor(max_workers=20)


def clear_cache(cache_path):
    """Clears the cache by deleting the cache folder."""
    if os.path.exists(cache_path):
        shutil.rmtree(cache_path)
        logger.info(f"Cache cleared at {cache_path}")
    else:
        logger.info(f"No cache to clear at {cache_path}")


async def fetch_website_links(url, session):
    """Fetches only the links from a website."""
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            content = await response.text()
            soup = BeautifulSoup(content, 'lxml')  # Using lxml for better performance
            links = [(a.get('href'), a.text.strip()) for a in soup.find_all('a', href=True)]
            logger.info(f"Extracted {len(links)} links from {url}")
            return links
    except Exception as e:
        logger.error(f"Error fetching links from {url}: {e}")
        return []


async def cache_links(url, max_depth=1, session=None):
    """Scrapes the website and caches the links up to the specified depth."""
    logger.debug(f"Starting to scrape and cache links for website: {url}")
    try:
        links = await fetch_website_links(url, session)
        result = {
            'url': url,
            'links': links
        }
        logger.info(f"Successfully scraped and cached links for {url}")
        return result
    except Exception as e:
        logger.error(f"Unexpected error scraping website: {url}, Error: {e}")
        return {'error': str(e)}


async def scrape_selected_links(urls, max_depth=3, session=None):
    """Scrapes selected links recursively up to the specified depth."""
    tasks = [fetch_website_links(url, session) for url in urls]
    completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)

    all_links = []
    for result in completed_tasks:
        if isinstance(result, Exception):
            logger.warning(f"Error during scraping: {result}")
        else:
            all_links.append(result)

    return all_links


async def run_package_creator(base_url, urls, output_zip_path, countdown_seconds=0):
    """Main function to scrape, screenshot and create a zip package."""
    logger.info(f"Starting package creation for {base_url} with countdown {countdown_seconds} seconds.")
    sanitized_base_url = sanitize_filename(base_url)
    base_folder = os.path.join('../scrapers/outputs_directory', sanitized_base_url)

    # Clear cache before starting the process
    clear_cache(base_folder)

    create_directory(base_folder)

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=100)) as session:
        # Cache main page links without recursion
        result = await cache_links(base_url, max_depth=1, session=session)
        if 'error' in result:
            logger.error(f"Error caching links for {base_url}: {result['error']}")
            return None

        # Recursively scrape selected subpage links
        selected_links = await scrape_selected_links(urls, max_depth=3, session=session)

    # Example of creating a zip file with the scraped data
    create_zip_file(base_folder, output_zip_path)

    # Clear cache after the process is completed
    clear_cache(base_folder)

    logger.info(f"Package created at {output_zip_path}")
    return output_zip_path


# Example use case
if __name__ == "__main__":
    import asyncio


    async def main():
        test_url = "https://www.zh.ch/de/direktion-der-justiz-und-des-innern/staatsarchiv.html"
        urls = [test_url]  # Example list of URLs

        output_zip_path = os.path.join("../scrapers/outputs_directory", "website_archive.zip")

        await run_package_creator(test_url, urls, output_zip_path)


    asyncio.run(main())
