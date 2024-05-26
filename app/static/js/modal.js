document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('modal');
    const closeModalButton = document.querySelector('.close');
    const downloadButton = document.getElementById('download-button');
    const archiveForm = document.getElementById('archive-form');
    const archivedLinksList = document.getElementById('archived-links-list');
    const archiveButton = document.getElementById('archive-button');
    const linksTableBody = document.getElementById('links-table').querySelector('tbody');

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

    // Modal schließen
    closeModalButton.onclick = () => {
        modal.style.display = 'none';
    };

    window.onclick = (event) => {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    };
});
