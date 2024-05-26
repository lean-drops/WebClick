const puppeteer = require('puppeteer');

(async () => {
    try {
        const url = process.argv[2];
        const path = process.argv[3];
        if (!url || !path) {
            throw new Error('URL and path must be provided');
        }

        const browser = await puppeteer.launch();
        const page = await browser.newPage();
        await page.goto(url, { waitUntil: 'networkidle2' });
        await page.screenshot({ path: path, fullPage: true });
        await browser.close();
        console.log(`Screenshot saved at ${path}`);
    } catch (error) {
        console.error("Error capturing screenshot:", error);
        process.exit(1);
    }
})();
