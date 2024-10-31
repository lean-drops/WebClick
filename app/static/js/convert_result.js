document.addEventListener('DOMContentLoaded', function () {
    // Modal-Funktionalität
    const modal = document.getElementById('pdf-modal');
    const modalContent = document.querySelector('.modal-content');
    const closeButton = document.querySelector('.close-button');
    const pdfPreview = document.getElementById('pdf-preview');
    const previewButtons = document.querySelectorAll('.preview-button');

    // Vorschau-Button Event Listener
    previewButtons.forEach(button => {
        button.addEventListener('click', function () {
            const pdfName = this.getAttribute('data-pdf');
            pdfPreview.src = `/get_pdf_preview/${pdfName}?task_id=${taskId}`;
            modal.style.display = 'block';
        });
    });

    // Modal schließen
    closeButton.addEventListener('click', function () {
        modal.style.display = 'none';
        pdfPreview.src = '';
    });

    window.addEventListener('click', function (event) {
        if (event.target == modal) {
            modal.style.display = 'none';
            pdfPreview.src = '';
        }
    });

    // Download-Button Funktionalität
    const downloadButton = document.getElementById('download-button');
    downloadButton.addEventListener('click', function () {
        // Sammle die PDFs, die nicht entfernt werden sollen
        const removeCheckboxes = document.querySelectorAll('.remove-checkbox');
        let pdfsToInclude = [];
        removeCheckboxes.forEach(checkbox => {
            if (!checkbox.checked) {
                pdfsToInclude.push(checkbox.getAttribute('data-pdf'));
            }
        });

        if (pdfsToInclude.length === 0) {
            alert('Sie müssen mindestens ein PDF auswählen, um es herunterzuladen.');
            return;
        }

        // Hole den Ordnernamen
        const folderNameInput = document.getElementById('folder-name');
        const folderName = folderNameInput.value.trim();
        if (!folderName) {
            alert('Bitte geben Sie einen Namen für den Ordner/die ZIP-Datei an.');
            return;
        }

        // Zeige einen Ladeindikator an
        downloadButton.disabled = true;
        downloadButton.textContent = 'Download läuft...';

        // Sende die Daten an den Server
        fetch('/finalize_pdfs', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                task_id: taskId,
                pdfs_to_include: pdfsToInclude,
                folder_name: folderName
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Weiterleitung zum Download-Link
                window.location.href = data.download_url;
            } else {
                alert('Es gab einen Fehler beim Erstellen des Downloads: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Fehler:', error);
            alert('Es gab einen Fehler beim Erstellen des Downloads.');
        })
        .finally(() => {
            // Ladeindikator zurücksetzen
            downloadButton.disabled = false;
            downloadButton.textContent = 'PDF herunterladen';
        });
    });
});
