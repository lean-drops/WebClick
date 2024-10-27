urls = [
    "https://www.zh.ch/de/sicherheit-justiz/strafvollzug-und-strafrechtliche-massnahmen/jahresbericht-2023.html",
        "https://www.zh.ch/de/wirtschaft-arbeit/handelsregister/stiftung.html",
"https://www.zh.ch/de/direktion-der-justiz-und-des-innern/statistisches-amt.html"
]
selectors = [
]
selectors_safe = [
        'div[class*="banner"]',
        'div[class*="cookie"]',
        'div[class*="popup"]',
        'div[class*="subscribe"]',
        'div[id*="banner"]',
        'div[id*="cookie"]',
        'div[id*="popup"]',
        'div[id*="subscribe"]',

        '.advertisement',
        '.adsbygoogle',
        '.modal',
        '.overlay',
        '.subscribe-modal',
        '.cookie-consent',
        'button[class*="close"]',
        'button[class*="dismiss"]',
        'button[class*="agree"]',
        'button[id*="close"]',
        'button[id*="dismiss"]',
        'button[id*="agree"]',

        # Hinzugefügter Selektor für den Seitenbanner (falls bekannt)
        '.side-banner',  # Beispiel: Ersetze dies durch den tatsächlichen Selektor
        '#side-index',   # Beispiel: Weitere spezifische Selektoren
    ]