import { showProgressBar, hideProgressBar } from './loadingbar.js';
import { createLinkRow, expandSubLinks, collapseSubLinks } from './dropdown.js';

document.addEventListener('DOMContentLoaded', function () {
    console.log("[DEBUG] DOMContentLoaded event fired.");

    const scrapeForm = document.getElementById('scrape-form');
    const linksTableBody = document.getElementById('links-table').querySelector('tbody');
    const notificationContainer = document.getElementById('notification-container');
    const archiveForm = document.getElementById('archive-form');
    const archiveButton = document.getElementById('archive-button');
    const modal = document.getElementById('modal');
    const modalCloseButton = modal.querySelector('.close');
    const archivedLinksList = document.getElementById('archived-links-list');
    const downloadButton = document.getElementById('download-button');

    console.log("[DEBUG] Elements loaded:", { scrapeForm, linksTableBody, notificationContainer, archiveForm, archiveButton, modal, modalCloseButton, archivedLinksList, downloadButton });

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

    async function scrapeWebsiteLinks(url) {
        try {
            const response = await fetch('/scrape_sub_links', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url }),
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Server error: ${errorText}`);
            }

            const data = await response.json();
            if (data.error) {
                showNotification(`Error: ${data.error}`, 'error');
                return [];
            }

            return data.links || [];
        } catch (error) {
            console.error("[ERROR] Error fetching website links:", error);
            showNotification(`Error fetching website links: ${error.message}`, 'error');
            return [];
        }
    }

    async function displayWebsiteLinks(url) {
        showProgressBar();
        linksTableBody.innerHTML = '';  // Clear previous results

        try {
            const links = await scrapeWebsiteLinks(url);

            links.forEach(link => {
                const row = createLinkRow(link);
                linksTableBody.appendChild(row);
            });

            showNotification('Links successfully retrieved.', 'success');
        } catch (error) {
            console.error("[ERROR] Error displaying website links:", error);
            showNotification('Failed to display website links.', 'error');
        } finally {
            hideProgressBar();
        }
    }

scrapeForm.addEventListener('submit', function (event) {
    event.preventDefault();
    const url = document.getElementById('url').value.trim(); // trim() entfernt Leerzeichen
    if (url) {
        // Weitere einfache Validierung, ob die URL korrekt formatiert ist
        try {
            new URL(url); // Versucht, die URL zu parsen
            displayWebsiteLinks(url);
        } catch (_) {
            showNotification('Please enter a valid URL.', 'error');
        }
    } else {
        showNotification('Please enter a valid URL.', 'error');
    }
});

    archiveForm.addEventListener('submit', async function (event) {
        event.preventDefault();

        const url = document.getElementById('url').value.trim();
        if (!url) {
            showNotification('Please enter a URL to archive.', 'error');
            return;
        }

        // Collect all selected links
        const selectedLinks = Array.from(linksTableBody.querySelectorAll('input[type="checkbox"]:checked'))
            .map(input => input.value);

        if (selectedLinks.length === 0) {
            showNotification('Please select at least one link to archive.', 'error');
            return;
        }

        archiveButton.disabled = true;
        showProgressBar();

        try {
            const savePath = prompt("Please enter the path where you want to save the archive:");
            if (!savePath) {
                showNotification('Save path was not provided.', 'error');
                return;
            }

            const response = await fetch('/archive', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url, save_path: savePath, urls: selectedLinks }),
            });

            const result = await response.json();
            if (response.ok) {
                showNotification('Archive created successfully.', 'success');
                modal.style.display = 'block';
                archivedLinksList.innerHTML = '';
                selectedLinks.forEach(link => {
                    const li = document.createElement('li');
                    li.textContent = link;
                    archivedLinksList.appendChild(li);
                });
                downloadButton.onclick = () => window.open(result.zip_path, '_blank');
            } else {
                showNotification(`Error: ${result.error}`, 'error');
            }
        } catch (error) {
            console.error("[ERROR] Error archiving links:", error);
            showNotification('An error occurred while archiving the links.', 'error');
        } finally {
            hideProgressBar();
            archiveButton.disabled = false;
        }
    });

    modalCloseButton.addEventListener('click', () => {
        modal.style.display = 'none';
    });

    window.addEventListener('click', (event) => {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });

    console.log("[DEBUG] Main script execution completed.");
});
