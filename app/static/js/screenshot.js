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

    // Ensure URL has a protocol
    const fullUrl = url.startsWith('http://') || url.startsWith('https://') ? url : `https://${url}`;

const cookieSelectors = [
    // Englisch
    '#onetrust-reject-all-handler',
    'button[title="Only essential cookies"]',
    'button[aria-label="Reject Cookies"]',
    'button[title="Reject Cookies"]',
    'button[data-testid="reject-all"]',
    '.cookie-consent-reject',
    '.cookie-banner-reject',
    'button.reject-cookies',
    'button#reject-all-cookies',
    '#cookie-reject',
    '.cc-reject',
    'button.cookie-reject',
    'button[title="Decline"]',
    'button[aria-label="Decline"]',
    'button[data-testid="decline"]',
    '.cookie-decline',
    '.cookie-settings-decline',
    'button.decline-cookies',
    'button#decline-all-cookies',
    'button[title="Dismiss"]',
    'button[aria-label="Dismiss"]',
    'button[data-testid="dismiss"]',
    '.cookie-dismiss',
    '.cookie-banner-dismiss',
    'button.dismiss-cookies',
    'button#dismiss-all-cookies',
    'button[title="Reject all"]',
    'button[aria-label="Reject all"]',
    'button[data-testid="reject-all-cookies"]',
    '.cookie-reject-all',
    '.cookie-banner-reject-all',
    'button.reject-all-cookies',
    'button#reject-all-cookies-button',
    'button[title="Deny"]',
    'button[aria-label="Deny"]',
    'button[data-testid="deny"]',
    '.cookie-deny',
    '.cookie-banner-deny',
    'button.deny-cookies',
    'button#deny-all-cookies',
    'button[title="Opt out"]',
    'button[aria-label="Opt out"]',
    'button[data-testid="opt-out"]',
    '.cookie-optout',
    '.cookie-banner-optout',
    'button.optout-cookies',
    'button#opt-out-cookies',
    'button[title="No"]',
    'button[aria-label="No"]',
    'button[data-testid="no"]',
    '.cookie-no',
    '.cookie-banner-no',
    'button.no-cookies',
    'button#no-all-cookies',
    '.cookie-consent-deny',
    '.cookie-consent-no',
    '.cookie-consent-opt-out',
    '.cookie-settings-reject',
    'button.cookie-settings-reject',
    'button[data-cookie-action="reject"]',
    'button[data-cookie-action="deny"]',
    'button[data-cookie-action="opt-out"]',

    // Deutsch
    'button[title="Nur essenzielle Cookies"]',
    'button[aria-label="Cookies ablehnen"]',
    'button[title="Cookies ablehnen"]',
    'button[data-testid="alle ablehnen"]',
    '.cookie-zustimmung-ablehnen',
    '.cookie-banner-ablehnen',
    'button.cookies-ablehnen',
    'button#alle-cookies-ablehnen',
    '#cookies-ablehnen',
    '.cc-ablehnen',
    'button.cookie-ablehnen',
    'button[title="Ablehnen"]',
    'button[aria-label="Ablehnen"]',
    'button[data-testid="ablehnen"]',
    '.cookie-ablehnen',
    '.cookie-einstellungen-ablehnen',
    'button.einstellungen-ablehnen',
    'button[title="Ablehnen"]',
    'button[aria-label="Alle ablehnen"]',
    'button[data-testid="alle-ablehnen"]',
    '.cookie-alle-ablehnen',
    '.cookie-banner-alle-ablehnen',
    'button.alle-ablehnen',
    'button#alle-ablehnen-button',
    'button[title="Verweigern"]',
    'button[aria-label="Verweigern"]',
    'button[data-testid="verweigern"]',
    '.cookie-verweigern',
    '.cookie-banner-verweigern',
    'button.verweigern-cookies',
    'button#verweigern-alle-cookies',
    'button[title="Abmelden"]',
    'button[aria-label="Abmelden"]',
    'button[data-testid="abmelden"]',
    '.cookie-abmelden',
    '.cookie-banner-abmelden',
    'button.abmelden-cookies',
    'button#abmelden-alle-cookies',
    '.cookie-zustimmung-verweigern',
    '.cookie-zustimmung-nein',
    '.cookie-zustimmung-opt-out',
    '.cookie-einstellungen-verweigern',
    'button.cookie-einstellungen-verweigern',
    'button[data-cookie-aktion="verweigern"]',
    'button[data-cookie-aktion="nein"]',

    // Spanisch
    'button[title="Solo cookies esenciales"]',
    'button[aria-label="Rechazar cookies"]',
    'button[title="Rechazar cookies"]',
    'button[data-testid="rechazar todo"]',
    '.consentimiento-cookies-rechazar',
    '.banner-cookies-rechazar',
    'button.rechazar-cookies',
    'button#rechazar-todas-las-cookies',
    '#rechazar-cookies',
    '.cc-rechazar',
    'button.cookie-rechazar',
    'button[title="Rechazar"]',
    'button[aria-label="Rechazar"]',
    'button[data-testid="rechazar"]',
    '.cookie-rechazar',
    '.ajustes-cookies-rechazar',
    'button.ajustes-rechazar',
    'button[title="Rechazar todo"]',
    'button[aria-label="Rechazar todo"]',
    'button[data-testid="rechazar-todas"]',
    '.cookie-rechazar-todo',
    '.banner-cookies-rechazar-todo',
    'button.rechazar-todo',
    'button#rechazar-todo-boton',
    'button[title="Denegar"]',
    'button[aria-label="Denegar"]',
    'button[data-testid="denegar"]',
    '.cookie-denegar',
    '.banner-cookies-denegar',
    'button.denegar-cookies',
    'button#denegar-todas-las-cookies',
    'button[title="Optar por no participar"]',
    'button[aria-label="Optar por no participar"]',
    'button[data-testid="optar-no-participar"]',
    '.cookie-optar-no-participar',
    '.banner-cookies-optar-no-participar',
    'button.optar-no-participar-cookies',
    'button#optar-no-participar-cookies',
    'button[title="No"]',
    'button[aria-label="No"]',
    'button[data-testid="no"]',
    '.cookie-no',
    '.banner-cookies-no',
    'button.no-cookies',
    'button#no-todas-las-cookies',
    '.consentimiento-cookies-denegar',
    '.consentimiento-cookies-no',
    '.consentimiento-cookies-optar-no',
    '.ajustes-cookies-rechazar',
    'button.ajustes-cookies-rechazar',
    'button[data-cookie-accion="rechazar"]',
    'button[data-cookie-accion="denegar"]',
    'button[data-cookie-accion="optar-no"]',

    // Französisch
    'button[title="Cookies essentiels uniquement"]',
    'button[aria-label="Refuser les cookies"]',
    'button[title="Refuser les cookies"]',
    'button[data-testid="tout refuser"]',
    '.consentement-cookies-refuser',
    '.banniere-cookies-refuser',
    'button.refuser-cookies',
    'button#refuser-tous-les-cookies',
    '#refuser-cookies',
    '.cc-refuser',
    'button.cookie-refuser',
    'button[title="Refuser"]',
    'button[aria-label="Refuser"]',
    'button[data-testid="refuser"]',
    '.cookie-refuser',
    '.parametres-cookies-refuser',
    'button.parametres-refuser',
    'button[title="Refuser tout"]',
    'button[aria-label="Refuser tout"]',
    'button[data-testid="refuser-tous"]',
    '.cookie-refuser-tout',
    '.banniere-cookies-refuser-tout',
    'button.refuser-tout',
    'button#refuser-tout-bouton',
    'button[title="Refuser"]',
    'button[aria-label="Refuser"]',
    'button[data-testid="refuser"]',
    '.cookie-refuser',
    '.banniere-cookies-refuser',
    'button.refuser-cookies',
    'button#refuser-tous-les-cookies',
    'button[title="Se désinscrire"]',
    'button[aria-label="Se désinscrire"]',
    'button[data-testid="se-desinscrire"]',
    '.cookie-se-desinscrire',
    '.banniere-cookies-se-desinscrire',
    'button.se-desinscrire-cookies',
    'button#se-desinscrire-tous-les-cookies',
    'button[title="Non"]',
    'button[aria-label="Non"]',
    'button[data-testid="non"]',
    '.cookie-non',
    '.banniere-cookies-non',
    'button.non-cookies',
    'button#non-tous-les-cookies',
    '.consentement-cookies-refuser',
    '.consentement-cookies-non',
    '.consentement-cookies-opt-out',
    '.parametres-cookies-refuser',
    'button.parametres-cookies-refuser',
    'button[data-cookie-action="refuser"]',
    'button[data-cookie-action="non"]'
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
