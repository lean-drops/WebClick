// main.js

// Event listener für das Scrape-Formular
document.getElementById('scrape-form').addEventListener('submit', async function (event) {
    event.preventDefault(); // Verhindert die Standardformularübermittlung

    const urlInput = document.getElementById('url');
    const url = urlInput.value;

    // Überprüfen, ob die URL eingegeben wurde
    if (!url) {
        alert('Bitte geben Sie eine gültige URL ein.');
        return;
    }

    // Fortschrittsanzeige initialisieren
    const progressBar = document.getElementById('progress-bar');
    progressBar.style.width = '0%';
    progressBar.setAttribute('aria-valuenow', 0);

  try {
    console.log('Sending POST request to /scrape_sub_links with URL:', url);

    const response = await fetch('/scrape_sub_links', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ url: url })
    });

    const result = await response.json();

    if (response.ok) {
        console.log('Received response from /scrape_sub_links:', result);
        populateLinksTable(result); // Füllt die Tabelle mit den gescrapten Links
    } else {
        console.error('Error response from /scrape_sub_links:', result);
        alert('Fehler beim Scrapen der Links: ' + result.error);
    }
} catch (error) {
    console.error('Fehler beim Senden der Anfrage:', error);
    alert('Ein unerwarteter Fehler ist aufgetreten.');
}

});

// Funktion zum Füllen der Tabelle mit den gescrapten Links
function populateLinksTable(links) {
    const linksTableBody = document.querySelector('#links-table tbody');
    linksTableBody.innerHTML = ''; // Löscht vorherige Einträge

    links.forEach((link, index) => {
        const row = document.createElement('tr');

        const selectCell = document.createElement('td');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.name = 'selectedLinks';
        checkbox.value = link;
        selectCell.appendChild(checkbox);

        const linkCell = document.createElement('td');
        linkCell.textContent = link;

        row.appendChild(selectCell);
        row.appendChild(linkCell);

        linksTableBody.appendChild(row);
    });
}

// Event listener für das Archivierungsformular
document.getElementById('archive-form').addEventListener('submit', async function (event) {
    event.preventDefault(); // Verhindert die Standardformularübermittlung

    const selectedLinks = Array.from(document.querySelectorAll('input[name="selectedLinks"]:checked'))
        .map(input => input.value);

    const mainUrl = document.getElementById('url').value;
    const savePath = prompt('Bitte geben Sie den Speicherpfad an:', 'C:\\Benutzer\\Benutzername\\Speicherort');

    if (!savePath) {
        alert('Bitte geben Sie einen gültigen Speicherpfad ein.');
        return;
    }

    if (selectedLinks.length === 0) {
        alert('Bitte wählen Sie mindestens einen Link aus.');
        return;
    }

    try {
        // API-Aufruf zur Archivierung der ausgewählten Links
        const response = await fetch('/archive', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                urls: selectedLinks,
                url: mainUrl,
                save_path: savePath
            })
        });

        const result = await response.json();

        if (response.ok) {
            showModal(result.zip_path); // Zeigt das Modalfenster an
        } else {
            alert('Fehler bei der Archivierung: ' + result.error);
        }
    } catch (error) {
        console.error('Fehler beim Senden der Anfrage:', error);
        alert('Ein unerwarteter Fehler ist aufgetreten.');
    }
});

// Funktion zum Anzeigen des Modalfensters
function showModal(zipPath) {
    const modal = document.getElementById('modal');
    const modalContent = modal.querySelector('.modal-content');
    const archivedLinksList = modalContent.querySelector('#archived-links-list');

    archivedLinksList.innerHTML = '';

    // Archivierte Links anzeigen
    const listItem = document.createElement('li');
    listItem.textContent = zipPath;
    archivedLinksList.appendChild(listItem);

    // Download-Button konfigurieren
    const downloadButton = modalContent.querySelector('#download-button');
    downloadButton.addEventListener('click', function () {
        window.location.href = zipPath; // Download-Link
    });

    modal.style.display = 'block';

    // Schließen-Button für das Modalfenster
    modal.querySelector('.close').addEventListener('click', function () {
        modal.style.display = 'none';
    });
}

// Fortschrittsbalken-Funktionalität aktualisieren
function updateProgressBar(percent) {
    const progressBar = document.getElementById('progress-bar');
    progressBar.style.width = `${percent}%`;
    progressBar.setAttribute('aria-valuenow', percent);
}
