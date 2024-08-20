import { createLinkRow, expandSubLinks, collapseSubLinks, openModalWithLinks } from './dropdown.js';
import { showProgressBar, hideProgressBar, updateProgressBar } from './loadingbar.js';

document.addEventListener('DOMContentLoaded', function() {
    console.log("[DEBUG] DOMContentLoaded event fired.");

    // Element References
    const scrapeForm = document.getElementById('scrape-form');
    const linksTableBody = document.getElementById('links-table').querySelector('tbody');
    const notificationContainer = document.getElementById('notification-container');
    let cache = {}; // Cache to store fetched links

    console.log("[DEBUG] Elements loaded:", { scrapeForm, linksTableBody, notificationContainer });

    // Utility Functions
    function showNotification(message, type = 'info') {
        const notificationDiv = document.createElement('div');
        notificationDiv.className = `notification ${type}`;
        notificationDiv.textContent = message;
        notificationContainer.appendChild(notificationDiv);
        setTimeout(() => notificationDiv.classList.add('fade-in'), 10);
        setTimeout(() => {
            notificationDiv.classList.remove('fade-in');
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

    // Fetch sublinks function defined within main.js
    async function fetchSublinks(url) {
        console.log("[DEBUG] fetchSublinks called with URL:", url);
        try {
            const response = await fetch('/fetch_sublinks', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: url }),
            });

            console.log("[DEBUG] fetchSublinks received response:", response);

            if (!response.ok) {
                console.error("[ERROR] Failed to fetch sublinks:", response.statusText);
                throw new Error('Failed to fetch sublinks');
            }

            const data = await response.json();
            console.log("[DEBUG] Sublinks data received:", data);
            return data.links || [];  // Return sublinks
        } catch (error) {
            console.error("[ERROR] Error fetching sublinks:", error);
            return [];
        }
    }

    // Function to recursively fetch links up to three levels deep
    async function fetchLinksRecursively(url, level = 0) {
        if (level > 2) return []; // Stop at third level
        console.log(`[DEBUG] Fetching links for ${url} at level ${level}`);

        if (cache[url]) {
            console.log("[DEBUG] Using cached data for:", url);
            return cache[url];
        }

        const sublinks = await fetchSublinks(url);
        cache[url] = sublinks; // Cache the results

        for (let link of sublinks) {
            const deeperLinks = await fetchLinksRecursively(link.url, level + 1);
            cache[link.url] = deeperLinks;
        }

        return sublinks;
    }

    // Event Listeners
    scrapeForm.addEventListener('submit', async function(event) {
        event.preventDefault();
        let url = document.getElementById('url').value.trim();
        url = normalizeURL(url);
        if (!url) return;

        showProgressBar();

        try {
            const links = await fetchLinksRecursively(url);
            console.log("[DEBUG] All links fetched:", links);

            linksTableBody.innerHTML = '';
            links.forEach(page => {
                const row = createLinkRow(page);
                linksTableBody.appendChild(row);
            });

            showNotification('Links erfolgreich abgerufen.', 'success');
        } catch (error) {
            console.error("[ERROR] Error fetching links:", error);
            showNotification('Ein Fehler ist beim Abrufen der Links aufgetreten.', 'error');
        } finally {
            hideProgressBar();
        }
    });

    console.log("[DEBUG] Main script execution completed.");
});
