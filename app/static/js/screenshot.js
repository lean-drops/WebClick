try {
    const puppeteer = require('puppeteer');

    (async () => {
        const url = process.argv[2];
        const path = process.argv[3];
        const browser = await puppeteer.launch();
        const page = await browser.newPage();
        await page.goto(url, { waitUntil: 'networkidle2' });
        await page.screenshot({ path: path, fullPage: true });
        await browser.close();
        console.log(`Screenshot saved at ${path}`);
    })();
} catch (error) {
    console.error("Error loading Puppeteer module:", error);
    process.exit(1);
}
