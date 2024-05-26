const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const AdblockerPlugin = require('puppeteer-extra-plugin-adblocker');
const fs = require('fs').promises;

// Verwende das Stealth-Plugin
puppeteer.use(StealthPlugin());

// Verwende das Adblocker-Plugin, das auch Cookie-Banner blockieren kann
puppeteer.use(AdblockerPlugin({ blockTrackers: true }));

// Funktion zum Laden der Cookie-Selektoren aus einer JSON-Datei
const loadCookieSelectors = async () => {
    try {
        const data = await fs.readFile('cookie_selectors.json', 'utf8');
        return JSON.parse(data);
    } catch (err) {
        console.error('Fehler beim Laden der Cookie-Selektoren:', err);
        return [];
    }
};

// Funktion zum automatischen Ablehnen von Cookie-Bannern
const autoRejectCookies = async (page, cookieSelectors) => {
    for (const selector of cookieSelectors) {
        try {
            const button = await page.$(selector);
            if (button) {
                await button.click();
                console.log(`Clicked cookie reject button with selector: ${selector}`);
                break;
            }
        } catch (err) {
            console.error(`Fehler beim Klicken auf den Selektor ${selector}:`, err);
        }
    }
};

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

    // Ensure URL has a protocol
    const fullUrl = url.startsWith('http://') || url.startsWith('https://') ? url : `https://${url}`;

    // Lade die Cookie-Selektoren
    const cookieSelectors = await loadCookieSelectors();

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
        console.log('Launching browser...');
        const browser = await puppeteer.launch({
            headless: true,
            args: ['--no-sandbox', '--disable-setuid-sandbox'],
            timeout: 120000 // Timeout auf 120 Sekunden setzen
        });

        console.log('Opening new page...');
        const page = await browser.newPage();
        await page.setViewport({
            width: 1920,
            height: 1080,
            deviceScaleFactor: 2
        });

        console.log(`Navigating to ${fullUrl}...`);
        await page.goto(fullUrl, { waitUntil: 'networkidle2', timeout: 120000 }); // Timeout auf 120 Sekunden setzen

        // Automatisches Ablehnen von Cookie-Bannern
        await autoRejectCookies(page, cookieSelectors);

        console.log('Waiting for 3 seconds...');
        await new Promise(resolve => setTimeout(resolve, 3000));

        console.log('Removing other banners...');
        await page.evaluate((selectors) => {
            selectors.forEach(selector => {
                const elements = document.querySelectorAll(selector);
                elements.forEach(element => element.remove());
            });
        }, otherBannerSelectors);

        console.log('Calculating full page height...');
        const fullHeight = await page.evaluate(() => {
            return document.body.scrollHeight;
        });

        console.log('Scrolling and waiting for the page to load completely...');
        let previousHeight;
        do {
            previousHeight = await page.evaluate('document.body.scrollHeight');
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)');
            console.log('Waiting for 1 second to allow for full load...');
            await new Promise(resolve => setTimeout(resolve, 1000)); // Warte 1 Sekunde
        } while ((await page.evaluate('document.body.scrollHeight')) !== previousHeight);

        await page.setViewport({
            width: 1920,
            height: Math.ceil(fullHeight),
            deviceScaleFactor: 2
        });

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
