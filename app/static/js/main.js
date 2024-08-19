import { showProgressBar, hideProgressBar, updateProgressBar } from './loadingbar.js';

document.addEventListener('DOMContentLoaded', function() {
    const scrapeForm = document.getElementById('scrape-form');
    const archiveForm = document.getElementById('archive-form');
    const linksTableBody = document.getElementById('links-table').querySelector('tbody');
    const archiveButton = document.getElementById('archive-button');
    const notificationContainer = document.getElementById('notification-container');

    function log(message, type = 'info') {
        if (type === 'error') {
            console.error(`[ERROR] ${message}`);
        } else if (type === 'warn') {
            console.warn(`[WARN] ${message}`);
        } else {
            console.log(`[INFO] ${message}`);
        }
    }

    function showNotification(message, type = 'info') {
        const notificationDiv = document.createElement('div');
        notificationDiv.className = `notification ${type}`;
        notificationDiv.textContent = message;
        notificationContainer.appendChild(notificationDiv);

        setTimeout(() => {
            notificationDiv.classList.add('fade-out');
            setTimeout(() => notificationDiv.remove(), 500);
        }, 3000);
    }

    function normalizeURL(url) {
        if (!/^https?:\/\//i.test(url)) {
            url = 'http://' + url;
        }
        try {
            new URL(url);
            return url;
        } catch (e) {
            showNotification('Ungültige URL. Bitte geben Sie eine gültige URL ein.', 'error');
            return null;
        }
    }

    scrapeForm.addEventListener('submit', function(event) {
        event.preventDefault();
        let url = document.getElementById('url').value.trim();

        if (!url) {
            showNotification('Bitte geben Sie eine gültige URL ein.', 'error');
            return;
        }

        url = normalizeURL(url);
        if (!url) return;

        showProgressBar();

        fetch('/scrape_sub_links', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: url }),
        })
        .then(response => response.json())
        .then(data => {
            hideProgressBar();
            if (data.error) {
                showNotification(data.error, 'error');
            } else {
                linksTableBody.innerHTML = '';
                data.links.forEach(page => {
                    const row = createLinkRow(page);
                    linksTableBody.appendChild(row);
                });
                showNotification('Links erfolgreich abgerufen.', 'success');
            }
        })
        .catch(error => {
            hideProgressBar();
            showNotification('Ein Fehler ist beim Abrufen der Links aufgetreten.', 'error');
            log(`Error fetching sub-links for URL: ${url} - ${error}`, 'error');
        });
    });

    archiveForm.addEventListener('submit', async function(event) {
        event.preventDefault();
        const checkboxes = linksTableBody.querySelectorAll('input[type="checkbox"]:checked');
        const urls = Array.from(checkboxes).map(checkbox => checkbox.value);

        const mainUrl = document.getElementById('url').value.trim();
        if (urls.length === 0) {
            urls.push(mainUrl);
        } else if (!urls.includes(mainUrl)) {
            urls.unshift(mainUrl);
        }

        archiveButton.textContent = 'Archivierung läuft...';
        archiveButton.classList.add('pulsing');

        showProgressBar();

        const eventSource = new EventSource('/archive');

        eventSource.onmessage = function(event) {
            const data = event.data;

            if (data === 'complete') {
                archiveButton.textContent = 'Website Downloaden';
                archiveButton.classList.remove('pulsing');
                archiveButton.onclick = () => {
                    const downloadUrl = event.lastEventId;  // lastEventId wird verwendet, um den Pfad zu speichern
                    const a = document.createElement('a');
                    a.href = `/download/${downloadUrl}`;
                    a.download = downloadUrl.split('/').pop();  // Dateiname aus dem Pfad extrahieren
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                };
                hideProgressBar();
                showNotification('Website erfolgreich archiviert!', 'success');
                eventSource.close();
            } else {
                updateProgressBar(parseInt(data));
            }
        };

        eventSource.onerror = function() {
            showNotification('Ein Fehler ist beim Archivieren der Website aufgetreten.', 'error');
            archiveButton.textContent = 'Website archivieren';
            archiveButton.classList.remove('pulsing');
            hideProgressBar();
            eventSource.close();
        };
    });
});
