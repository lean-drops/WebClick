const puppeteer = require('puppeteer');

(async () => {
    const url = process.argv[2];
    const screenshotPath = process.argv[3];

    if (!url || !screenshotPath) {
        console.error('URL or screenshot path not provided');
        process.exit(1);
    }

    const cookieSelectors = [
        '#onetrust-reject-all-handler', // Beispiel: OneTrust Banner
        'button[title="Only essential cookies"]',
        'button[aria-label="Reject Cookies"]',
        'button[title="Reject Cookies"]',
        'button[data-testid="reject-all"]',
        '.cookie-consent-reject', // Beispiel: Weitere allgemeine Selektoren hinzufügen
        '.cookie-banner-reject',
        'button.reject-cookies',
        'button#reject-all-cookies'
    ];

    try {
        const browser = await puppeteer.launch({
            headless: true,
            args: ['--no-sandbox', '--disable-setuid-sandbox'], // Zusätzliche Argumente für Stabilität
            timeout: 60000 // Timeout auf 60 Sekunden erhöhen
        });
        const page = await browser.newPage();
        await page.setViewport({
            width: 1920,
            height: 1080,
            deviceScaleFactor: 2 // Höhere Auflösung
        });

        await page.goto(url, { waitUntil: 'networkidle2', timeout: 60000 });

        // Versuchen Sie, die Cookie-Banner abzulehnen, indem Sie die angegebenen Selektoren durchgehen
        for (const selector of cookieSelectors) {
            const button = await page.$(selector);
            if (button) {
                await button.click();
                console.log(`Clicked cookie reject button with selector: ${selector}`);
                break; // Stoppt die Schleife, wenn ein Button gefunden und geklickt wurde
            }
        }

        // Warte 3 Sekunden, um sicherzustellen, dass die Seite geladen ist
        await new Promise(resolve => setTimeout(resolve, 3000));

        await page.screenshot({ path: screenshotPath, fullPage: true });

        await browser.close();
        console.log('Screenshot saved at ' + screenshotPath);
        process.exit(0);
    } catch (err) {
        console.error('Error taking screenshot:', err);
        process.exit(1);
    }
})();
