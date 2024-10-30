// static/js/scrape_result.js

document.addEventListener('DOMContentLoaded', function () {
    const toggleButtons = document.querySelectorAll('.toggle-btn-label');
    const selectedLinksContainer = document.getElementById('selected-links');
    const checkboxes = document.querySelectorAll('input[name="selected_links"]');
    const listLinks = document.querySelectorAll('.toggle-link');

    let externalWindow = null;

    // Funktion zum Öffnen eines neuen Fensters rechts neben dem aktuellen Fenster
    function openExternalWindow(url) {
        // Berechne die Position und Größe des neuen Fensters
        const screenWidth = window.screen.width;
        const screenHeight = window.screen.height;
        const windowWidth = screenWidth / 2;
        const windowHeight = screenHeight;

        // Berechne die Position des neuen Fensters (rechts neben dem aktuellen Fenster)
        const windowLeft = window.screenX + window.outerWidth;
        const windowTop = window.screenY;

        // Öffne das neue Fenster
        externalWindow = window.open(
            url,
            'externalWindow',
            `width=${windowWidth},height=${windowHeight},left=${windowLeft},top=${windowTop}`
        );
    }

    // Event-Listener für den Hauptlink
    const mainLinkElement = document.getElementById('main-link');
    if (mainLinkElement) {
        mainLinkElement.addEventListener('click', function (e) {
            e.preventDefault();
            const mainLinkUrl = this.getAttribute('data-url');
            if (externalWindow && !externalWindow.closed) {
                externalWindow.location.href = mainLinkUrl;
                externalWindow.focus();
            } else {
                openExternalWindow(mainLinkUrl);
            }
        });
    }

    // Event-Listener für die List Links
    listLinks.forEach(link => {
        link.addEventListener('click', function (e) {
            e.preventDefault();
            const url = this.getAttribute('data-url');
            if (externalWindow && !externalWindow.closed) {
                externalWindow.location.href = url;
                externalWindow.focus();
            } else {
                openExternalWindow(url);
            }
        });
    });

    // Event-Listener für Toggle-Buttons
    toggleButtons.forEach(button => {
        button.addEventListener('click', function () {
            const pageId = this.getAttribute('data-page-id');
            toggleChildren(pageId, this);
        });
    });

    // Event-Listener für Checkboxen
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function () {
            const linkUrl = this.value;
            const linkTitle = this.dataset.title;
            const linkId = `selected-${hashCode(linkUrl)}`;

            if (this.checked) {
                // Link hinzufügen
                const linkDiv = document.createElement('div');
                linkDiv.classList.add('selected-link');
                linkDiv.id = linkId;

                const linkAnchor = document.createElement('a');
                linkAnchor.href = '#';
                linkAnchor.textContent = linkTitle || linkUrl;
                linkAnchor.addEventListener('click', function (e) {
                    e.preventDefault();
                    if (externalWindow && !externalWindow.closed) {
                        externalWindow.location.href = linkUrl;
                        externalWindow.focus();
                    } else {
                        openExternalWindow(linkUrl);
                    }
                });

                const removeButton = document.createElement('button');
                removeButton.classList.add('remove-link');
                removeButton.innerHTML = '&times;';
                removeButton.addEventListener('click', function () {
                    checkbox.checked = false; // Checkbox deaktivieren
                    selectedLinksContainer.removeChild(linkDiv);
                });

                linkDiv.appendChild(linkAnchor);
                linkDiv.appendChild(removeButton);
                selectedLinksContainer.appendChild(linkDiv);
            } else {
                // Link entfernen
                const linkDiv = document.getElementById(linkId);
                if (linkDiv) {
                    selectedLinksContainer.removeChild(linkDiv);
                }
            }
        });

        // Initialisiere die ausgewählten Links beim Laden der Seite
        if (checkbox.checked) {
            const event = new Event('change');
            checkbox.dispatchEvent(event);
        }
    });

    function toggleChildren(pageId, toggleElement) {
        const childRows = document.querySelectorAll('.child-of-' + pageId);
        const isExpanded = toggleElement.classList.toggle('expanded');
        toggleElement.setAttribute('aria-expanded', isExpanded);

        childRows.forEach(row => {
            row.style.display = isExpanded ? 'table-row' : 'none';
        });
    }

    // Funktion zur Generierung eines einfachen Hashcodes für eindeutige IDs
    function hashCode(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            hash = (hash << 5) - hash + str.charCodeAt(i);
            hash |= 0; // Convert to 32bit integer
        }
        return Math.abs(hash).toString();
    }

    // Funktion zum Starten der PDF-Konvertierung
    async function startPdfConversion() {
        const checkboxes = document.querySelectorAll('input[name="selected_links"]:checked');
        let selectedLinks = [];

        // Benutzergewählte Links hinzufügen
        checkboxes.forEach((checkbox) => {
            selectedLinks.push(checkbox.value);
        });

        // Hauptlink immer hinzufügen, falls nicht bereits enthalten
        const mainLinkUrl = document.getElementById('main-link').getAttribute('data-url');
        if (!selectedLinks.includes(mainLinkUrl)) {
            selectedLinks.push(mainLinkUrl);
        }

        if (selectedLinks.length === 0) {
            alert('Bitte wählen Sie mindestens einen Link aus.');
            return;
        }

        // Erfasse den ausgewählten Konvertierungsmodus
        const modeRadio = document.querySelector('input[name="conversion_mode"]:checked');
        const conversionMode = modeRadio ? modeRadio.value : 'collapsed';

        // Ladeanzeige einblenden
        const loadingIndicator = document.getElementById('loading-indicator');
        loadingIndicator.style.display = 'block';

        try {
            const response = await fetch('/start_pdf_task', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ selected_links: selectedLinks, conversion_mode: conversionMode }),
            });

            const data = await response.json();

            if (data.status === 'success' && data.task_id) {
                // Weiterleitung zur PDF-Statusseite mit der task_id
                const taskId = data.task_id;
                window.location.href = `/pdf_status/${taskId}`;
            } else {
                loadingIndicator.style.display = 'none';
                alert(data.message || 'Fehler beim Starten des PDF-Tasks.');
            }
        } catch (error) {
            loadingIndicator.style.display = 'none';
            console.error('Fehler beim Erstellen des PDF-Tasks:', error);
            alert('Es gab ein Problem beim Starten der PDF-Konvertierung.');
        }
    }

    // Event-Listener für den Konvertieren-Button hinzufügen
    const convertButton = document.getElementById('convert-button');
    if (convertButton) {
        convertButton.addEventListener('click', startPdfConversion);
    }

    // Verbesserte Suchfunktion
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('input', function () {
            const filter = this.value.toLowerCase();
            const table = document.querySelector('.list-container table');
            const rows = table.querySelectorAll('tbody tr');

            rows.forEach(row => {
                const linkCell = row.querySelector('td a.toggle-link');
                if (linkCell) {
                    const text = linkCell.textContent.toLowerCase();
                    if (text.includes(filter)) {
                        row.style.display = '';
                    } else {
                        row.style.display = 'none';
                    }
                }
            });
        });
    }
});
