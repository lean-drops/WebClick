const puppeteer = require('puppeteer');

(async () => {
    const url = process.argv[2];
    const screenshotPath = process.argv[3];
    const countdownSeconds = parseInt(process.argv[4], 10) || 0;

    if (!url || !screenshotPath) {
        console.error('URL oder Screenshot-Pfad nicht angegeben');
        process.exit(1);
    }

    if (url.startsWith('mailto:')) {
        console.error('Screenshot von einer Mailto-Link ist nicht möglich');
        process.exit(1);
    }

    const fullUrl = url.startsWith('http://') || url.startsWith('https://') ? url : `https://${url}`;

    try {
        console.log('Launching browser...');
        const browser = await puppeteer.launch({
            headless: true,
            args: ['--no-sandbox', '--disable-setuid-sandbox'],
            timeout: 60000 // Timeout auf 60 Sekunden setzen
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

        console.log('Waiting for the page to load completely...');
        await page.waitForTimeout(2000); // Warte 2 Sekunden, um sicherzustellen, dass die Seite vollständig geladen ist

        // Countdown-Timer
        console.log(`Countdown gestartet: ${countdownSeconds} Sekunden`);
        for (let i = countdownSeconds; i > 0; i--) {
            console.log(`Countdown: ${i} Sekunden`);
            await new Promise(resolve => setTimeout(resolve, 1000));
        }

        console.log('Taking screenshot...');
        const bodyHandle = await page.$('body');
        const { width, height } = await bodyHandle.boundingBox();
        await page.setViewport({ width: Math.ceil(width), height: Math.ceil(height) });
        await page.screenshot({ path: screenshotPath, fullPage: true });

        await browser.close();
        console.log('Screenshot gespeichert unter ' + screenshotPath);
    } catch (err) {
        console.error('Fehler beim Erstellen des Screenshots:', err);
        process.exit(1);
    }
})();
