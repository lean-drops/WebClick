import aiohttp
import asyncio
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import hashlib
import json


def hash_url(url):
    """Generates a unique hash for a URL."""
    return hashlib.md5(url.encode()).hexdigest()


async def fetch(url, session, visited, prefix):
    """Asynchronously fetches a URL and extracts relevant links."""
    url_hash = hash_url(url)
    if url_hash in visited:
        return None  # URL bereits besucht

    visited.add(url_hash)
    try:
        async with session.get(url, timeout=10) as response:
            if response.status != 200:
                print(f"Skipping {url}, status code: {response.status}")
                return (url, [])

            text = await response.text()
            soup = BeautifulSoup(text, 'html.parser')
            page_links = set()

            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                full_url = urljoin(url, href)
                parsed_full_url = urlparse(full_url)._replace(fragment='', query='').geturl()

                if parsed_full_url.startswith(prefix):
                    full_url_hash = hash_url(parsed_full_url)
                    if full_url_hash not in visited:
                        page_links.add(parsed_full_url)

            return (url, list(page_links))
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return (url, [])


async def crawl(url, prefix, visited, session, semaphore):
    """Controls the asynchronous crawling of a single URL."""
    async with semaphore:
        return await fetch(url, session, visited, prefix)


async def crawl_all_links(start_url, prefix):
    """Orchestrates the recursive, asynchronous crawling of links using aiohttp and asyncio."""
    visited = set()
    links = []
    url_to_links = {}
    semaphore = asyncio.Semaphore(20)  # Erhöht die Parallelität bei Bedarf

    async with aiohttp.ClientSession() as session:
        tasks = set()
        # Erstelle die initiale Aufgabe
        initial_task = asyncio.create_task(crawl(start_url, prefix, visited, session, semaphore))
        tasks.add(initial_task)

        while tasks:
            # Warte auf die erste abgeschlossene Aufgabe
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

            for task in done:
                tasks.remove(task)
                result = await task
                if result is None:
                    continue
                url, sub_links = result
                url_to_links[url] = sub_links
                links.extend(sub_links)

                for sub_link in sub_links:
                    sub_link_hash = hash_url(sub_link)
                    if sub_link_hash not in visited:
                        new_task = asyncio.create_task(crawl(sub_link, prefix, visited, session, semaphore))
                        tasks.add(new_task)

        return links, url_to_links


def main():
    start_url = input("Enter the starting URL: ").strip()
    parsed_url = urlparse(start_url)
    base_path = parsed_url.path.rsplit('/', 1)[0] + '/'
    prefix = f"{parsed_url.scheme}://{parsed_url.netloc}{base_path}"
    print(f"Crawling links starting with prefix: {prefix}")

    links, url_map = asyncio.run(crawl_all_links(start_url, prefix))
    unique_links = sorted(set(links))
    output_file = 'links.json'

    # Save the mapping of URLs and their discovered links
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(url_map, f, indent=2, ensure_ascii=False)

    print(f"Collected {len(unique_links)} links. Saved to {output_file}")


if __name__ == "__main__":
    main()
