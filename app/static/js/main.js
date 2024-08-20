import { createLinkRow } from './dropdown.js';
import { showProgressBar, hideProgressBar, updateProgressBar } from './loadingbar.js';

document.addEventListener('DOMContentLoaded', function() {
    console.log("[DEBUG] DOMContentLoaded event fired.");

    // Element References
    const scrapeForm = document.getElementById('scrape-form');
    const archiveForm = document.getElementById('archive-form');
    const linksTableBody = document.getElementById('links-table').querySelector('tbody');
    const archiveButton = document.getElementById('archive-button');
    const notificationContainer = document.getElementById('notification-container');

    console.log("[DEBUG] Elements loaded:", { scrapeForm, archiveForm, linksTableBody, archiveButton, notificationContainer });

    // Utility Functions
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
        console.log(`[DEBUG] showNotification called with message: "${message}" and type: "${type}"`);
        if (!notificationContainer) {
            log('Notification container is not found.', 'error');
            return;
        }

        const notificationDiv = document.createElement('div');
        notificationDiv.className = `notification ${type}`;
        notificationDiv.textContent = message;
        notificationContainer.appendChild(notificationDiv);
        console.log("[DEBUG] Notification element created and appended.");

        setTimeout(() => {
            notificationDiv.classList.add('fade-in');
            console.log("[DEBUG] Fade-in effect triggered.");
        }, 10);

        setTimeout(() => {
            notificationDiv.classList.remove('fade-in');
            notificationDiv.classList.add('fade-out');
            console.log("[DEBUG] Fade-out effect triggered.");
            setTimeout(() => {
                notificationDiv.remove();
                console.log("[DEBUG] Notification element removed.");
            }, 500);
        }, 3000);
    }

    function normalizeURL(url) {
        console.log("[DEBUG] normalizeURL called with url:", url);
        if (!/^https?:\/\//i.test(url)) {
            url = 'http://' + url;
            console.log("[DEBUG] URL normalized to:", url);
        }
        try {
            new URL(url);
            console.log("[DEBUG] URL is valid:", url);
            return url;
        } catch (e) {
            console.error("[ERROR] Invalid URL:", url);
            showNotification('Ungültige URL. Bitte geben Sie eine gültige URL ein.', 'error');
            return null;
        }
    }

    // Event Listeners
    scrapeForm.addEventListener('submit', function(event) {
        console.log("[DEBUG] scrapeForm submit event triggered.");
        event.preventDefault();
        let url = document.getElementById('url').value.trim();
        console.log("[DEBUG] URL input value:", url);

        if (!url) {
            log('URL is empty.', 'error');
            showNotification('Bitte geben Sie eine gültige URL ein.', 'error');
            return;
        }

        url = normalizeURL(url);
        if (!url) return;

        console.log("[DEBUG] Fetching sub-links for URL:", url);
        showProgressBar();

        fetch('/scrape_sub_links', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: url }),
        })
        .then(response => {
            console.log("[DEBUG] Response received:", response);
            return response.json();
        })
        .then(data => {
            console.log("[DEBUG] Data received from server:", data);
            hideProgressBar();
            if (data.error) {
                log(`Server returned error: ${data.error}`, 'error');
                showNotification(data.error, 'error');
            } else {
                console.log("[DEBUG] No error in server response. Clearing table body.");
                linksTableBody.innerHTML = '';
                data.links.forEach(page => {
                    console.log("[DEBUG] Processing link:", page);
                    const row = createLinkRow(page);
                    console.log("[DEBUG] Link row created:", row);
                    linksTableBody.appendChild(row);
                    console.log("[DEBUG] Link row appended to table body.");
                });
                showNotification('Links erfolgreich abgerufen.', 'success');
            }
        })
        .catch(error => {
            log(`Error fetching sub-links: ${error}`, 'error');
            hideProgressBar();
            showNotification('Ein Fehler ist beim Abrufen der Links aufgetreten.', 'error');
        });
    });

    archiveForm.addEventListener('submit', async function(event) {
        console.log("[DEBUG] archiveForm submit event triggered.");
        event.preventDefault();
        const checkboxes = linksTableBody.querySelectorAll('input[type="checkbox"]:checked');
        console.log("[DEBUG] Number of selected checkboxes:", checkboxes.length);

        const urls = Array.from(checkboxes).map(checkbox => checkbox.value);
        console.log("[DEBUG] URLs to be archived:", urls);

        if (urls.length === 0) {
            log('No links selected for archiving.', 'error');
            showNotification('Bitte wählen Sie mindestens einen Link zum Archivieren aus.', 'error');
            return;
        }

        archiveButton.textContent = 'Archivierung läuft...';
        archiveButton.classList.add('pulsing');
        console.log("[DEBUG] Archive button text and class updated.");

        showProgressBar();

        try {
            const response = await fetch('/archive', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: document.getElementById('url').value, urls: urls }),
            });

            console.log("[DEBUG] Archive response received:", response);
            if (!response.ok) {
                throw new Error('Archivierungsfehler');
            }

            const reader = response.body.getReader();
            const contentLength = +response.headers.get('Content-Length');
            console.log("[DEBUG] Content length of archive:", contentLength);

            let receivedLength = 0;
            let chunks = [];

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                chunks.push(value);
                receivedLength += value.length;
                const progress = (receivedLength / contentLength) * 100;
                updateProgressBar(progress);
                console.log("[DEBUG] Progress updated:", progress);
            }

            const blob = new Blob(chunks);
            const downloadUrl = URL.createObjectURL(blob);
            console.log("[DEBUG] Blob URL created:", downloadUrl);

            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = 'website_archive.zip';
            document.body.appendChild(a);
            a.click();
            console.log("[DEBUG] Download initiated.");

            archiveButton.textContent = 'Website Downloaden';
            archiveButton.classList.remove('pulsing');
            hideProgressBar();
            showNotification('Website erfolgreich archiviert!', 'success');
        } catch (error) {
            log(`Error during website archiving: ${error}`, 'error');
            archiveButton.textContent = 'Website archivieren';
            archiveButton.classList.remove('pulsing');
            hideProgressBar();
            showNotification('Ein Fehler ist beim Archivieren der Website aufgetreten.', 'error');
        }
    });

    console.log("[DEBUG] Main script execution completed.");
});
