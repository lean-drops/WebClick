import asyncio
from playwright.async_api import async_playwright

async def test_playwright():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        async with browser.new_context() as context:
            page = await context.new_page()
            await page.goto('https://www.example.com')
            title = await page.title()
            print(f"Seitentitel: {title}")
            await page.screenshot(path='example.png')
        await browser.close()

asyncio.run(test_playwright())
