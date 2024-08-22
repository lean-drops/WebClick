document.addEventListener('DOMContentLoaded', function() {
    const scrapeForm = document.getElementById('scrape-form');
    const linksContainer = document.getElementById('links-container');
    const linksTableBody = document.getElementById('links-table').querySelector('tbody');
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

    async function fetchLinksFromBackend(url) {
        const response = await fetch('/scrape_sub_links', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: url })
        });

        if (!response.ok) {
            throw new Error('Failed to fetch links from backend');
        }

        const result = await response.json();
        return result.links;  // Assuming the backend returns the links in this structure
    }

    scrapeForm.addEventListener('submit', async function(event) {
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
            const links = await fetchLinksFromBackend(url);
            hideProgressBar();
            linksTableBody.innerHTML = '';
            links.forEach(link => {
                const row = createLinkRow(link);
                linksTableBody.appendChild(row);
            });
            linksContainer.classList.add('fade-in');
            linksContainer.style.display = 'block';
            showSuccess('Links erfolgreich abgerufen.');
        } catch (error) {
            hideProgressBar();
            console.error('Error:', error);
            showError('Ein Fehler ist beim Abrufen der Links aufgetreten.');
        }
    });

    function showProgressBar() {
        progressContainer.style.display = 'block';
        progressBar.style.width = '100%';
    }

    function hideProgressBar() {
        progressContainer.style.display = 'none';
    }

    function createLinkRow(link) {
        const row = document.createElement('tr');

        const cellSelect = document.createElement('td');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.value = link.url;
        cellSelect.appendChild(checkbox);

        const cellLink = document.createElement('td');
        const linkElement = document.createElement('a');
        linkElement.href = '#';
        linkElement.textContent = link.title || link.url; // Falls kein Titel vorhanden ist, URL anzeigen
        linkElement.addEventListener('click', (event) => {
            event.preventDefault();
            window.open(link.url, '_blank');
        });

        cellLink.appendChild(linkElement);
        row.appendChild(cellSelect);
        row.appendChild(cellLink);
        return row;
    }
});
