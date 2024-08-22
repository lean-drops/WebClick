document.addEventListener('DOMContentLoaded', function() {
    const scrapeForm = document.getElementById('scrape-form');
    const archiveForm = document.getElementById('archive-form');
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
            // Optionally, add code here to handle clicks (e.g., expanding sub-links)
        });

        cellLink.appendChild(link);
        row.appendChild(cellSelect);
        row.appendChild(cellLink);
        return row;
    }

    function showProgressBar() {
        progressContainer.style.display = 'block';
        progressBar.style.width = '0%';
    }

    function hideProgressBar() {
        progressContainer.style.display = 'none';
    }

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
                showSuccess('Links successfully retrieved.');
            }
        })
        .catch(error => {
            hideProgressBar();
            console.error('Error:', error);
            showError('An error occurred while retrieving the links.');
        });
    });

    archiveForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const checkboxes = linksTableBody.querySelectorAll('input[type="checkbox"]:checked');
        const urls = Array.from(checkboxes).map(checkbox => checkbox.value);

        if (urls.length === 0) {
            showError('Please select at least one link to archive.');
            return;
        }

        archiveButton.textContent = 'Archiving...';
        archiveButton.disabled = true;

        fetch('/archive', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: document.getElementById('url').value, urls: urls }),
        })
        .then(response => response.json())
        .then(data => {
            archiveButton.disabled = false;
            if (data.error) {
                showError(data.error);
                archiveButton.textContent = 'Archive Website';
            } else {
                archiveButton.textContent = 'Download Archive';
                archiveButton.addEventListener('click', () => {
                    window.location.href = `/download/${data.zip_path}`;
                });
                showSuccess('Website successfully archived!');
            }
        })
        .catch(error => {
            archiveButton.disabled = false;
            console.error('Error:', error);
            showError('An error occurred during archiving.');
            archiveButton.textContent = 'Archive Website';
        });
    });
});
