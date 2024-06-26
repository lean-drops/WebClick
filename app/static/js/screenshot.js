const puppeteer = require('puppeteer');

(async () => {
    const url = process.argv[2];
    const screenshotPath = process.argv[3];
    const countdownSeconds = parseInt(process.argv[4], 10) || 0;

    if (!url || !screenshotPath) {
        console.error('URL oder Screenshot-Pfad nicht angegeben');
        process.exit(1);
    }

    if (url.startsWith('mailto:') || url.startsWith('tel:')) {
        console.error('Screenshot von einer Mailto- oder Tel-Link ist nicht möglich');
        process.exit(1);
    }

    const fullUrl = url.startsWith('http://') || url.startsWith('https://') ? url : `https://${url}`;

    const cookieSelectors = [
        '#onetrust-reject-all-handler',
        'button[title="Only essential cookies"]',
        'button[aria-label="Reject Cookies"]',
    ];

    const otherBannerSelectors = [
        '.ad-banner', '.newsletter-popup', '.modal-overlay',
        '.subscription-banner', '.promo-banner', '.gdpr-banner'
    ];

    try {
        console.log('Launching browser...');
        const browser = await puppeteer.launch({
            headless: true,
            args: ['--no-sandbox', '--disable-setuid-sandbox'],
            timeout: 120000
        });

        console.log('Opening new page...');
        const page = await browser.newPage();
        await page.setViewport({
            width: 1920,
            height: 1080,
            deviceScaleFactor: 2
        });

        console.log(`Navigating to ${fullUrl}...`);
        await page.goto(fullUrl, { waitUntil: 'networkidle2', timeout: 120000 });

        console.log('Checking for cookie banners...');
        for (const selector of cookieSelectors) {
            const button = await page.$(selector);
            if (button) {
                await button.click();
                console.log(`Clicked cookie reject button with selector: ${selector}`);
                break;
            }
        }

        console.log('Waiting for 3 seconds...');
        await new Promise(resolve => setTimeout(resolve, 3000));

        console.log('Removing other banners...');
        await page.evaluate((selectors) => {
            selectors.forEach(selector => {
                const elements = document.querySelectorAll(selector);
                elements.forEach(element => element.remove());
            });
        }, otherBannerSelectors);

        // Countdown-Timer
        console.log(`Countdown gestartet: ${countdownSeconds} Sekunden`);
        for (let i = countdownSeconds; i > 0; i--) {
            console.log(`Countdown: ${i} Sekunden`);
            await new Promise(resolve => setTimeout(resolve, 1000));
        }

        console.log('Taking screenshot...');
        await page.screenshot({ path: screenshotPath, fullPage: true });

        await browser.close();
        console.log('Screenshot gespeichert unter ' + screenshotPath);
    } catch (err) {
        console.error('Fehler beim Erstellen des Screenshots:', err);
        process.exit(1);
    }
})();
