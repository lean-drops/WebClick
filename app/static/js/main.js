import { showProgressBar, hideProgressBar } from './loadingbar.js';
import { createLinkRow, expandSubLinks, collapseSubLinks } from './dropdown.js';

document.addEventListener('DOMContentLoaded', () => {
    console.log("[DEBUG] DOMContentLoaded event fired.");

    const elements = {
        scrapeForm: document.getElementById('scrape-form'),
        linksTableBody: document.getElementById('links-table')?.querySelector('tbody'),
        notificationContainer: document.getElementById('notification-container'),
        archiveForm: document.getElementById('archive-form'),
        archiveButton: document.getElementById('archive-button'),
        modal: document.getElementById('modal'),
        modalCloseButton: document.getElementById('modal')?.querySelector('.close'),
        archivedLinksList: document.getElementById('archived-links-list'),
        downloadButton: document.getElementById('download-button'),
        urlInput: document.getElementById('url')
    };

    console.log("[DEBUG] Elements loaded:", elements);

    const showNotification = (message, type = 'info') => {
        const notificationDiv = document.createElement('div');
        notificationDiv.className = `notification ${type}`;
        notificationDiv.textContent = message;

        elements.notificationContainer.appendChild(notificationDiv);
        setTimeout(() => notificationDiv.classList.add('fade-in'), 10);
        setTimeout(() => {
            notificationDiv.classList.remove('fade-in');
            notificationDiv.classList.add('fade-out');
            setTimeout(() => notificationDiv.remove(), 500);
        }, 3000);
    };

    const validateUrl = (url) => {
        try {
            new URL(url);
            return true;
        } catch {
            return false;
        }
    };

    const fetchData = async (endpoint, payload, options = {}) => {
        const {
            retries = 3,
            retryDelay = 1000,
            timeout = 5000,
        } = options;

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);

        try {
            for (let attempt = 1; attempt <= retries; attempt++) {
                try {
                    const response = await fetch(endpoint, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                            'Accept': 'application/json, text/plain, */*',
                            'Accept-Language': 'en-US,en;q=0.9',
                            'Referer': 'https://www.zh.ch/'
                        },
                        body: JSON.stringify(payload),
                        signal: controller.signal,
                    });

                    clearTimeout(timeoutId);

                    if (!response.ok) {
                        const errorText = await response.text();
                        console.error(`[ERROR] Server error (Attempt ${attempt} of ${retries}): ${errorText}`);
                        if (attempt === retries) {
                            throw new Error(`Server error: ${errorText}`);
                        }
                    } else {
                        const data = await response.json();

                        if (data.error) {
                            console.error(`[ERROR] API error (Attempt ${attempt} of ${retries}): ${data.error}`);
                            if (attempt === retries) {
                                throw new Error(`Error: ${data.error}`);
                            }
                        } else {
                            return data; // Return the data if everything is okay
                        }
                    }
                } catch (error) {
                    if (attempt === retries || error.name === 'AbortError') {
                        throw error; // Rethrow the error if it's the last attempt or a timeout
                    }
                    console.warn(`[WARN] Request failed (Attempt ${attempt} of ${retries}). Retrying in ${retryDelay}ms...`);
                    await new Promise(res => setTimeout(res, retryDelay)); // Wait before retrying
                }
            }
        } catch (error) {
            clearTimeout(timeoutId);
            console.error(`[ERROR] ${error.message}`, error);
            showNotification(`Error: ${error.message}`, 'error');
            return null;
        }
    };

    const scrapeWebsiteLinks = (url) => fetchData('/scrape_sub_links', { url });

    const archiveLinks = (url, savePath, selectedLinks) =>
        fetchData('/archive', { url, save_path: savePath, urls: selectedLinks });

    const clearLinksTable = () => {
        if (elements.linksTableBody) {
            elements.linksTableBody.innerHTML = ''; // Clear previous results
        }
    };

    const displayWebsiteLinks = async (url) => {
        try {
            showProgressBar();
            clearLinksTable();

            const links = await scrapeWebsiteLinks(url);
            if (links && links.links && links.links.length > 0) {
                const fragment = document.createDocumentFragment();
                links.links.forEach(link => {
                    const row = createLinkRow(link);
                    fragment.appendChild(row);
                });
                elements.linksTableBody?.appendChild(fragment);
                showNotification('Links successfully retrieved.', 'success');
            } else {
                showNotification('No links found or an error occurred.', 'error');
            }
        } catch (error) {
            console.error("[ERROR] Failed to display website links:", error);
            showNotification('An unexpected error occurred while displaying links.', 'error');
        } finally {
            hideProgressBar();
        }
    };

    const handleScrapeFormSubmit = async (event) => {
        event.preventDefault();
        const url = elements.urlInput?.value.trim();

        if (validateUrl(url)) {
            await displayWebsiteLinks(url);
        } else {
            showNotification('Please enter a valid URL.', 'error');
        }
    };

    const handleArchiveFormSubmit = async (event) => {
        event.preventDefault();

        const url = elements.urlInput?.value.trim();
        if (!validateUrl(url)) {
            showNotification('Please enter a valid URL to archive.', 'error');
            return;
        }

        const selectedLinks = Array.from(elements.linksTableBody.querySelectorAll('input[type="checkbox"]:checked'))
            .map(input => input.value);

        if (selectedLinks.length === 0) {
            showNotification('Please select at least one link to archive.', 'error');
            return;
        }

        elements.archiveButton.disabled = true;
        showProgressBar();

        try {
            const savePath = prompt("Please enter the path where you want to save the archive:");
            if (!savePath) {
                showNotification('Save path was not provided.', 'error');
                return;
            }

            const result = await archiveLinks(url, savePath, selectedLinks);
            if (result) {
                showNotification('Archive created successfully.', 'success');
                elements.modal.style.display = 'block';
                elements.archivedLinksList.innerHTML = selectedLinks.map(link => `<li>${link}</li>`).join('');
                elements.downloadButton.onclick = () => window.open(result.zip_path, '_blank');
            }
        } catch (error) {
            console.error("[ERROR] Failed to archive links:", error);
            showNotification('An unexpected error occurred while archiving links.', 'error');
        } finally {
            hideProgressBar();
            elements.archiveButton.disabled = false;
        }
    };

    const handleModalClose = () => {
        if (elements.modal) {
            elements.modal.style.display = 'none';
        }
    };

    const handleWindowClick = (event) => {
        if (event.target === elements.modal) {
            elements.modal.style.display = 'none';
        }
    };

    if (elements.scrapeForm) {
        elements.scrapeForm.addEventListener('submit', handleScrapeFormSubmit);
    }
    if (elements.archiveForm) {
        elements.archiveForm.addEventListener('submit', handleArchiveFormSubmit);
    }
    if (elements.modalCloseButton) {
        elements.modalCloseButton.addEventListener('click', handleModalClose);
    }
    window.addEventListener('click', handleWindowClick);

    console.log("[DEBUG] Main script execution completed.");
});
