document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('modal');
    const closeModalButton = document.querySelector('.close');
    const downloadButton = document.getElementById('download-button');
    const archiveForm = document.getElementById('archive-form');
    const archivedLinksList = document.getElementById('archived-links-list');
    const archiveButton = document.getElementById('archive-button');
    const linksTableBody = document.getElementById('links-table').querySelector('tbody');
    const progressBar = document.getElementById('progress-bar');
    const progressContainer = document.getElementById('progress-container');

    // Function to show a pop-up notification in the bottom-left corner
    function showNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        document.body.appendChild(notification);

        // Automatically remove the notification after 5 seconds
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => notification.remove(), 500);
        }, 5000);
    }

    // Show error or success messages using the notification
    function showError(message) {
        showNotification(message, 'error');
    }

    function showSuccess(message) {
        showNotification(message, 'success');
    }

    // URL normalizer
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

    // Create a table row for each scraped link
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
        link.addEventListener('click', (event) => {
            event.preventDefault();
        });

        cellLink.appendChild(link);
        row.appendChild(cellSelect);
        row.appendChild(cellLink);
        return row;
    }

    // Progress bar functions
    function showProgressBar() {
        progressContainer.style.display = 'block';
        progressBar.style.width = '0%';

        let width = 0;
        const interval = setInterval(() => {
            if (width >= 100) {
                clearInterval(interval);
            } else {
                width++;
                progressBar.style.width = width + '%';
            }
        }, 100); // Adjust the interval as needed
    }

    function hideProgressBar() {
        progressContainer.style.display = 'none';
    }

    // Scrape form submission handler
    document.getElementById('scrape-form').addEventListener('submit', async function(event) {
        event.preventDefault();
        let url = document.getElementById('url').value.trim();

        if (!url) {
            showError('Bitte geben Sie eine gültige URL ein.');
            return;
        }

        url = normalizeURL(url);
        if (!url) {
            showError('Ungültige URL. Bitte geben Sie eine gültige URL ein.');
            return;
        }

        showProgressBar();

        try {
            const response = await fetch('/scrape', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: url }),
            });

            const data = await response.json();
            hideProgressBar();

            if (data.error) {
                showError(data.error);
            } else {
                linksTableBody.innerHTML = '';
                data.pages.forEach(page => {
                    const row = createLinkRow(page);
                    linksTableBody.appendChild(row);
                });
                showSuccess('Links erfolgreich abgerufen.');
            }
        } catch (error) {
            hideProgressBar();
            console.error('Error:', error);
            showError('Ein Fehler ist beim Abrufen der Links aufgetreten.');
        }
    });

    // Archive form submission handler
    archiveForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const checkboxes = linksTableBody.querySelectorAll('input[type="checkbox"]:checked');
        const urls = Array.from(checkboxes).map(checkbox => checkbox.value);

        if (urls.length === 0) {
            showError('Bitte wählen Sie mindestens einen Link zum Archivieren aus.');
            return;
        }

        archiveButton.textContent = 'Archivierung läuft...';
        archiveButton.classList.add('pulsing');

        try {
            const response = await fetch('/archive', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: document.getElementById('url').value, urls: urls }),
            });

            const data = await response.json();
            archiveButton.classList.remove('pulsing');

            if (data.error) {
                showError(data.error);
                archiveButton.textContent = 'Website archivieren';
            } else {
                archiveButton.textContent = 'Website archivieren'; // Reset button text
                downloadButton.onclick = () => {
                    window.location.href = `/download/${data.zip_path}`;
                };
                showSuccess('Website erfolgreich archiviert!');

                // Liste der archivierten Links anzeigen
                archivedLinksList.innerHTML = '';
                urls.forEach(link => {
                    const li = document.createElement('li');
                    li.textContent = link;
                    archivedLinksList.appendChild(li);
                });

                // Modal anzeigen
                modal.style.display = 'block';
            }
        } catch (error) {
            archiveButton.classList.remove('pulsing');
            console.error('Error:', error);
            showError('Ein Fehler ist beim Archivieren der Website aufgetreten.');
            archiveButton.textContent = 'Website archivieren';
        }
    });

    // Modal closing logic
    closeModalButton.onclick = () => {
        modal.style.display = 'none';
    };

    window.onclick = (event) => {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    };
});
