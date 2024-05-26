// Wartet darauf, dass der DOM vollständig geladen ist
document.addEventListener('DOMContentLoaded', function() {
    const scrapeForm = document.getElementById('scrape-form');
    const archiveForm = document.getElementById('archive-form');
    const linksContainer = document.getElementById('links-container');
    const linksTableBody = document.getElementById('links-table').querySelector('tbody');
    const progressBarContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar');

    // Funktion zur Anzeige einer Fehlermeldung
    function showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error';
        errorDiv.textContent = message;
        document.body.prepend(errorDiv);
        setTimeout(() => errorDiv.remove(), 5000);
    }

    // Funktion zur Anzeige einer Erfolgsmeldung
    function showSuccess(message) {
        const successDiv = document.createElement('div');
        successDiv.className = 'success';
        successDiv.textContent = message;
        document.body.prepend(successDiv);
        setTimeout(() => successDiv.remove(), 5000);
    }

    // Funktion zum Validieren und Anpassen der URL
    function normalizeURL(url) {
        if (!/^https?:\/\//i.test(url)) {
            url = 'http://' + url;
        }
        try {
            new URL(url);
            return url;
        } catch (e) {
            return null;
        }
    }

    // Funktion zum Erstellen eines neuen Fensters für Links
    function openInNewWindow(url, windowFeatures) {
        const newWindow = window.open(url, '_blank', windowFeatures);
        if (newWindow) {
            newWindow.focus();
        } else {
            showError('Failed to open the link in a new window.');
        }
    }

    // Funktion zum Erstellen einer Tabellenzeile für einen Link
    function createLinkRow(page) {
        const row = document.createElement('tr');
        const cellSelect = document.createElement('td');
        const cellLink = document.createElement('td');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.value = page.url;
        cellSelect.appendChild(checkbox);

        const link = document.createElement('a');
        link.href = '#';
        link.textContent = page.title;
        link.addEventListener('dblclick', (event) => {
            event.preventDefault();
            const windowFeatures = `width=${window.screen.width / 2},height=${window.screen.height / 4},left=${window.screen.width / 2},top=0,scrollbars=yes,resizable=yes`;
            openInNewWindow(page.url, windowFeatures);
        });
        cellLink.appendChild(link);

        row.appendChild(cellSelect);
        row.appendChild(cellLink);
        return row;
    }

    // Funktion zur Anpassung des Fensters der Haupt-GUI
    function adjustMainWindow() {
        if (window.screen.width > 1280) {
            window.moveTo(0, 0);
            window.resizeTo(window.screen.width / 2, window.screen.height);
        } else {
            showError('Your screen resolution is too low to adjust the window.');
        }
    }

    // Funktion zum Öffnen der Webseite auf der rechten Seite
    function openWebsiteOnRight(url) {
        const windowFeatures = `width=${window.screen.width / 2},height=${window.screen.height},left=${window.screen.width / 2},top=0,scrollbars=yes,resizable=yes`;
        openInNewWindow(url, windowFeatures);
    }

    // Funktion zum Anzeigen des Fortschrittsbalkens
    function showProgressBar() {
        progressBarContainer.style.display = 'block';
        progressBar.style.width = '0%';
        let width = 0;
        const interval = setInterval(() => {
            if (width >= 100) {
                clearInterval(interval);
            } else {
                width++;
                progressBar.style.width = width + '%';
            }
        }, 100); // Adjust the interval time as needed
    }

    // Funktion zum Verbergen des Fortschrittsbalkens
    function hideProgressBar() {
        progressBarContainer.style.display = 'none';
    }

    // Event-Listener für das Scrape-Formular
    scrapeForm.addEventListener('submit', function(event) {
        event.preventDefault();
        let url = document.getElementById('url').value.trim();

        if (!url) {
            showError('Please enter a valid URL.');
            return;
        }

        url = normalizeURL(url);
        if (!url) {
            showError('Invalid URL. Please enter a valid URL.');
            return;
        }

        adjustMainWindow();
        openWebsiteOnRight(url);

        // Zeige Fortschrittsbalken
        showProgressBar();

        // POST-Anfrage an die /scrape-Route senden
        fetch('/scrape', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: url }),
        })
        .then(response => response.json())
        .then(data => {
            // Verberge Fortschrittsbalken
            hideProgressBar();

            if (data.error) {
                showError(data.error);
            } else {
                // Links in der Tabelle anzeigen
                linksTableBody.innerHTML = '';
                data.pages.forEach(page => {
                    const row = createLinkRow(page);
                    linksTableBody.appendChild(row);
                });
                linksContainer.style.display = 'block';
                showSuccess('Links successfully fetched.');
            }
        })
        .catch(error => {
            // Verberge Fortschrittsbalken
            hideProgressBar();
            console.error('Error:', error);
            showError('An error occurred while fetching the links.');
        });
    });

    // Event-Listener für das Archiv-Formular
    archiveForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const checkboxes = linksTableBody.querySelectorAll('input[type="checkbox"]:checked');
        const urls = Array.from(checkboxes).map(checkbox => checkbox.value);

        // Überprüfen, ob keine URLs ausgewählt sind, und die Haupt-URL hinzufügen
        if (urls.length === 0) {
            urls.push(document.getElementById('url').value.trim());
        }

        // Zeige Fortschrittsbalken
        showProgressBar();

        // POST-Anfrage an die /archive-Route senden
        fetch('/archive', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: document.getElementById('url').value, urls: urls }),
        })
        .then(response => response.json())
        .then(data => {
            // Verberge Fortschrittsbalken
            hideProgressBar();

            if (data.error) {
                showError(data.error);
            } else {
                showSuccess('Website archived successfully!');
                // Link zum Herunterladen des ZIP-Archivs anzeigen
                const downloadLink = document.createElement('a');
                downloadLink.href = `/download/${data.zip_path}`;
                downloadLink.textContent = 'Download Archive';
                downloadLink.className = 'download-link';
                document.body.appendChild(downloadLink);
            }
        })
        .catch(error => {
            // Verberge Fortschrittsbalken
            hideProgressBar();
            console.error('Error:', error);
            showError('An error occurred while archiving the website.');
        });
    });
});
