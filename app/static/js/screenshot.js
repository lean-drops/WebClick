const puppeteer = require('puppeteer');

(async () => {
    const url = process.argv[2];
    const screenshotPath = process.argv[3];
    const countdownSeconds = parseInt(process.argv[4], 10) || 0; // Countdown-Zeit in Sekunden

    if (!url || !screenshotPath) {
        console.error('URL oder Screenshot-Pfad nicht angegeben');
        process.exit(1);
    }

    if (url.startsWith('mailto:')) {
        console.error('Screenshot von einer Mailto-Link ist nicht möglich');
        process.exit(1);
    }

    const cookieSelectors = [
        '#onetrust-reject-all-handler',
        'button[title="Only essential cookies"]',
        'button[aria-label="Reject Cookies"]',
        'button[title="Reject Cookies"]',
        'button[data-testid="reject-all"]',
        '.cookie-consent-reject',
        '.cookie-banner-reject',
        'button.reject-cookies',
        'button#reject-all-cookies'
    ];

    const otherBannerSelectors = [
        '#age-gate',
        '.rating-popup',
        '.ad-banner',
        '.newsletter-popup',
        '.modal-overlay',
        '.subscription-banner',
        '#age-verification',
        '.survey-popup',
        '.feedback-popup',
        '.welcome-screen',
        '.promo-banner',
        '.gdpr-banner',
        '.cc-window',
        '.cookie-consent-banner',
        '.interstitial'
    ];

    try {
        const browser = await puppeteer.launch({
            headless: true,
            args: ['--no-sandbox', '--disable-setuid-sandbox'],
            timeout: 120000 // Timeout auf 120 Sekunden erhöhen
        });
        const page = await browser.newPage();
        await page.setViewport({
            width: 1920,
            height: 1080,
            deviceScaleFactor: 2
        });

        await page.goto(url, { waitUntil: 'networkidle2', timeout: 120000 }); // Timeout auf 120 Sekunden erhöhen

        for (const selector of cookieSelectors) {
            const button = await page.$(selector);
            if (button) {
                await button.click();
                console.log(`Clicked cookie reject button with selector: ${selector}`);
                break;
            }
        }

        await new Promise(resolve => setTimeout(resolve, 3000));

        await page.evaluate((selectors) => {
            selectors.forEach(selector => {
                const elements = document.querySelectorAll(selector);
                elements.forEach(element => element.remove());
            });
        }, otherBannerSelectors);

        const fullHeight = await page.evaluate(() => {
            return document.body.scrollHeight;
        });

        // Scrollen und warten, um sicherzustellen, dass die Seite vollständig geladen wird
        let previousHeight;
        do {
            previousHeight = await page.evaluate('document.body.scrollHeight');
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)');
            await new Promise(resolve => setTimeout(resolve, 2000)); // Warte 2 Sekunden
        } while ((await page.evaluate('document.body.scrollHeight')) !== previousHeight);

        await page.setViewport({
            width: 1920,
            height: Math.ceil(fullHeight),
            deviceScaleFactor: 2
        });

        // Countdown-Timer
        for (let i = countdownSeconds; i > 0; i--) {
            console.log(`Countdown: ${i} Sekunden`);
            await new Promise(resolve => setTimeout(resolve, 1000));
        }

        await page.screenshot({ path: screenshotPath, fullPage: true });

        await browser.close();
        console.log('Screenshot gespeichert unter ' + screenshotPath);
    } catch (err) {
        console.error('Fehler beim Erstellen des Screenshots:', err);
        process.exit(1);
    }
})();
