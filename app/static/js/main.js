document.addEventListener('DOMContentLoaded', function() {
    const scrapeForm = document.getElementById('scrape-form');
    const archiveForm = document.getElementById('archive-form');
    const linksContainer = document.getElementById('links-container');
    const linksTableBody = document.getElementById('links-table').querySelector('tbody');
    const archiveButton = document.getElementById('archive-button');
    const progressBar = document.getElementById('progress-bar');
    const progressContainer = document.getElementById('progress-container');

    function showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error';
        errorDiv.textContent = message;
        document.body.prepend(errorDiv);
        setTimeout(() => errorDiv.remove(), 5000);
    }

    function showSuccess(message) {
        const successDiv = document.createElement('div');
        successDiv.className = 'success';
        successDiv.textContent = message;
        document.body.prepend(successDiv);
        setTimeout(() => successDiv.remove(), 5000);
    }

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

    function openInNewWindow(url, windowFeatures) {
        const newWindow = window.open(url, '_blank', windowFeatures);
        if (newWindow) {
            newWindow.focus();
        } else {
            showError('Failed to open the link in a new window.');
        }
    }

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
            const windowFeatures = `width=${window.screen.width / 2},height=${window.screen.height},left=${window.screen.width / 2},top=0,scrollbars=yes,resizable=yes`;
            openInNewWindow(page.url, windowFeatures);
        });
        cellLink.appendChild(link);

        row.appendChild(cellSelect);
        row.appendChild(cellLink);
        return row;
    }

    function adjustMainWindow() {
        if (window.screen.width > 1280) {
            window.moveTo(0, 0);
            window.resizeTo(window.screen.width / 2, window.screen.height);
        } else {
            showError('Your screen resolution is too low to adjust the window.');
        }
    }

    function openWebsiteOnRight(url) {
        const windowFeatures = `width=${window.screen.width / 2},height=${window.screen.height},left=${window.screen.width / 2},top=0,scrollbars=yes,resizable=yes`;
        openInNewWindow(url, windowFeatures);
    }

    scrapeForm.addEventListener('submit', function(event) {
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

        adjustMainWindow();
        openWebsiteOnRight(url);

        showProgressBar();

        fetch('/scrape', {
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
                showError(data.error);
            } else {
                linksTableBody.innerHTML = '';
                data.pages.forEach(page => {
                    const row = createLinkRow(page);
                    linksTableBody.appendChild(row);
                });
                linksContainer.classList.add('fade-in');
                linksContainer.style.display = 'block';
                showSuccess('Links erfolgreich abgerufen.');
            }
        })
        .catch(error => {
            hideProgressBar();
            console.error('Error:', error);
            showError('Ein Fehler ist beim Abrufen der Links aufgetreten.');
        });
    });

    archiveForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const checkboxes = linksTableBody.querySelectorAll('input[type="checkbox"]:checked');
        const urls = Array.from(checkboxes).map(checkbox => checkbox.value);

        if (urls.length === 0) {
            showError('Bitte wählen Sie mindestens einen Link zum Archivieren aus.');
            return;
        }

        archiveButton.textContent = 'Archivierung läuft...';
        archiveButton.classList.add('pulsing');

        fetch('/archive', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: document.getElementById('url').value, urls: urls }),
        })
        .then(response => response.json())
        .then(data => {
            archiveButton.classList.remove('pulsing');
            if (data.error) {
                showError(data.error);
                archiveButton.textContent = 'Website archivieren';
            } else {
                archiveButton.textContent = 'Website Downloaden';
                archiveButton.addEventListener('click', () => {
                    window.location.href = `/download/${data.zip_path}`;
                });
                showSuccess('Website erfolgreich archiviert!');
            }
        })
        .catch(error => {
            archiveButton.classList.remove('pulsing');
            console.error('Error:', error);
            showError('Ein Fehler ist beim Archivieren der Website aufgetreten.');
            archiveButton.textContent = 'Website archivieren';
        });
    });
});
