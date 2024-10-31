// static/js/scrape_result.js

document.addEventListener('DOMContentLoaded', () => {
    const toggleButtons = document.querySelectorAll('.toggle-btn-label');
    const selectedLinksContainer = document.getElementById('selected-links');
    const checkboxes = document.querySelectorAll('input[name="selected_links"]');
    const listLinks = document.querySelectorAll('.toggle-link');
    const mainLinkElement = document.getElementById('main-link');
    const convertButton = document.getElementById('convert-button');
    const searchInput = document.getElementById('search-input');
    const loadingOverlay = document.getElementById('loading-overlay');
    const loadingMessage = document.getElementById('loading-message');
    const progressBar = document.getElementById('progress-bar');

    let externalWindow = null;

    // Funktion zum Öffnen eines externen Fensters mit der angegebenen URL
    function openExternalWindow(url) {
        if (externalWindow && !externalWindow.closed) {
            externalWindow.location.href = url;
            externalWindow.focus();
        } else {
            externalWindow = window.open(url, '_blank');
        }
    }

    // Event-Listener für den Hauptlink
    if (mainLinkElement) {
        mainLinkElement.addEventListener('click', (e) => {
            e.preventDefault();
            const mainLinkUrl = mainLinkElement.getAttribute('data-url');
            openExternalWindow(mainLinkUrl);
        });
    }

    // Event-Listener für die Listenlinks
    listLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const url = link.getAttribute('data-url');
            openExternalWindow(url);
        });
    });

    // Event-Listener für die Umschaltknöpfe (Toggle-Buttons)
    toggleButtons.forEach(button => {
        button.addEventListener('click', () => {
            const pageId = button.getAttribute('data-page-id');
            toggleChildren(pageId, button);
        });
    });

    // Funktion zum Verarbeiten der Änderung des Kontrollkästchens
    function handleCheckboxChange(checkbox) {
        const linkUrl = checkbox.value;
        const linkTitle = checkbox.dataset.title || linkUrl;
        const linkId = `selected-${hashCode(linkUrl)}`;

        if (checkbox.checked) {
            addSelectedLink(linkId, linkTitle, linkUrl, checkbox);
        } else {
            removeSelectedLink(linkId);
        }
    }

    // Funktion zum Hinzufügen eines ausgewählten Links zur Liste
    function addSelectedLink(linkId, linkTitle, linkUrl, checkbox) {
        const linkDiv = document.createElement('div');
        linkDiv.classList.add('selected-link');
        linkDiv.id = linkId;

        const linkAnchor = document.createElement('a');
        linkAnchor.href = '#';
        linkAnchor.textContent = linkTitle;
        linkAnchor.addEventListener('click', (e) => {
            e.preventDefault();
            openExternalWindow(linkUrl);
        });

        const removeButton = document.createElement('button');
        removeButton.classList.add('remove-link');
        removeButton.innerHTML = '&times;';
        removeButton.addEventListener('click', () => {
            checkbox.checked = false;
            selectedLinksContainer.removeChild(linkDiv);
        });

        linkDiv.appendChild(linkAnchor);
        linkDiv.appendChild(removeButton);
        selectedLinksContainer.appendChild(linkDiv);
    }

    // Funktion zum Entfernen eines ausgewählten Links aus der Liste
    function removeSelectedLink(linkId) {
        const linkDiv = document.getElementById(linkId);
        if (linkDiv) {
            selectedLinksContainer.removeChild(linkDiv);
        }
    }

    // Event-Listener für die Kontrollkästchen
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', () => handleCheckboxChange(checkbox));

        // Initialisiere die ausgewählten Links beim Laden der Seite
        if (checkbox.checked) {
            handleCheckboxChange(checkbox);
        }
    });

    // Funktion zum Umschalten der Anzeige von Kindelementen
    function toggleChildren(pageId, toggleElement) {
        const childRows = document.querySelectorAll(`.child-of-${pageId}`);
        const isExpanded = toggleElement.classList.toggle('expanded');
        toggleElement.setAttribute('aria-expanded', isExpanded);

        childRows.forEach(row => {
            row.style.display = isExpanded ? '' : 'none';
        });
    }

    // Funktion zum Generieren eines Hashcodes für eindeutige IDs
    function hashCode(str) {
        let hash = 0;
        for (const char of str) {
            hash = ((hash << 5) - hash) + char.charCodeAt(0);
            hash |= 0; // Konvertiert zu einer 32-Bit-Ganzzahl
        }
        return Math.abs(hash).toString();
    }

    // Funktion zur Aktualisierung der Ladeanzeige-Nachricht
    function updateLoadingMessage(message) {
        if (loadingMessage) {
            loadingMessage.textContent = message;
        }
    }

    // Funktion zur Aktualisierung des Fortschrittsbalkens
    function updateProgressBar(progress) {
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }
    }

    // Funktion zum Starten der PDF-Konvertierung
    async function startPdfConversion() {
        const selectedCheckboxes = document.querySelectorAll('input[name="selected_links"]:checked');
        const selectedLinks = Array.from(selectedCheckboxes).map(checkbox => checkbox.value);

        // Hauptlink hinzufügen, falls nicht bereits enthalten
        if (mainLinkElement) {
            const mainLinkUrl = mainLinkElement.getAttribute('data-url');
            if (!selectedLinks.includes(mainLinkUrl)) {
                selectedLinks.push(mainLinkUrl);
            }
        }

        if (selectedLinks.length === 0) {
            alert('Bitte wählen Sie mindestens einen Link aus.');
            return;
        }

        const modeRadio = document.querySelector('input[name="conversion_mode"]:checked');
        const conversionMode = modeRadio ? modeRadio.value : 'collapsed';

        // Zeige die Ladeanzeige
        loadingOverlay.style.display = 'flex';
        updateLoadingMessage('PDF-Konvertierung läuft. Bitte warten...');
        updateProgressBar(0);

        try {
            const response = await fetch('/start_pdf_task', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ selected_links: selectedLinks, conversion_mode: conversionMode }),
            });

            const data = await response.json();

            if (data.status === 'success' && data.task_id) {
                // Starte das Polling für den Task-Status
                pollPdfStatus(data.task_id);
            } else {
                throw new Error(data.message || 'Fehler beim Starten des PDF-Tasks.');
            }
        } catch (error) {
            console.error('Fehler beim Starten des PDF-Tasks:', error);
            alert('Es gab ein Problem beim Starten der PDF-Konvertierung.');
            // Verstecke die Ladeanzeige
            loadingOverlay.style.display = 'none';
        }
    }

    // Funktion zum regelmäßigen Abfragen des PDF-Task-Status
    function pollPdfStatus(taskId) {
        const interval = setInterval(async () => {
            try {
                const response = await fetch(`/get_pdf_status/${taskId}`);
                const data = await response.json();

                if (data.status === 'completed') {
                    clearInterval(interval);
                    updateProgressBar(100);
                    updateLoadingMessage('PDF-Konvertierung abgeschlossen!');
                    setTimeout(() => {
                        window.location.href = `/pdf_result/${taskId}`;
                    }, 1000);
                } else if (data.status === 'failed') {
                    clearInterval(interval);
                    alert(data.error || 'Der PDF-Task ist fehlgeschlagen.');
                    loadingOverlay.style.display = 'none';
                } else if (data.status === 'running') {
                    // Aktualisiere die Ladeanzeige mit dem Fortschritt
                    if (data.progress !== undefined) {
                        updateProgressBar(data.progress);
                        updateLoadingMessage(`PDF-Konvertierung läuft... ${data.progress}% abgeschlossen`);
                    }
                }
            } catch (error) {
                console.error('Fehler beim Abrufen des PDF-Status:', error);
                alert('Es gab ein Problem beim Abrufen des PDF-Status.');
                clearInterval(interval);
                loadingOverlay.style.display = 'none';
            }
        }, 1000); // Polling-Intervall von 1 Sekunde
    }

    // Event-Listener für den "PDF-Konvertierung starten"-Button
    if (convertButton) {
        convertButton.addEventListener('click', startPdfConversion);
    }

    // Verbesserte Suchfunktion für die Linkliste
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            const filter = searchInput.value.toLowerCase();
            const tableRows = document.querySelectorAll('.list-container table tbody tr');

            tableRows.forEach(row => {
                const linkCell = row.querySelector('td a.toggle-link');
                if (linkCell) {
                    const text = linkCell.textContent.toLowerCase();
                    row.style.display = text.includes(filter) ? '' : 'none';
                }
            });
        });
    }
});
