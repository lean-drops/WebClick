// Modal-Funktionalität
function toggleModal(url = null) {
    const modal = document.getElementById("siteModal");
    const iframe = document.getElementById("siteIframe");

    console.log("toggleModal called, url:", url); // Log
    if (modal && modal.classList.contains("hidden") && url) {
        console.log("Opening modal and setting iframe src to:", url); // Log
        iframe.src = url;
        modal.classList.remove("hidden");
    } else if (modal) {
        console.log("Closing modal"); // Log
        modal.classList.add("hidden");
        iframe.src = ""; // Clear iframe
    }
}

// Form Handling und Scraping starten
document.addEventListener('DOMContentLoaded', function () {
    const scrapeForm = document.getElementById("scrapeForm");

    if (scrapeForm) {
        scrapeForm.onsubmit = async function (e) {
            e.preventDefault();
            const url = document.getElementById("url").value;
            console.log("Form submitted, scraping URL:", url); // Log

            try {
                const response = await fetch('/scrape_links', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url })
                });

                const data = await response.json();
                console.log("Scrape started, received task_id:", data.task_id); // Log

                if (data.task_id) {
                    checkScrapingStatus(data.task_id);
                } else {
                    console.error('Error: No task_id returned'); // Log
                    alert('Fehler beim Starten des Scrapings.');
                }
            } catch (err) {
                console.error("Error during scraping:", err); // Log
                alert('Fehler beim Starten des Scrapings.');
            }
        };
    }

    // Scraping-Status abfragen
    async function checkScrapingStatus(taskId) {
        console.log("Checking status for task_id:", taskId); // Log

        try {
            const statusResponse = await fetch(`/scrape/status/${taskId}`);
            const statusData = await statusResponse.json();
            console.log("Scraping status:", statusData.status); // Log

            if (statusData.status === 'completed') {
                const resultResponse = await fetch(`/scrape_result/${taskId}`);
                const resultHtml = await resultResponse.text();
                displayResults(resultHtml);
            } else if (statusData.status === 'running') {
                console.log("Scraping still running... retrying in 2 seconds"); // Log
                setTimeout(() => checkScrapingStatus(taskId), 2000);
            } else {
                console.error("Error in scraping status:", statusData); // Log
                alert('Fehler beim Scraping.');
            }
        } catch (err) {
            console.error("Error checking status:", err); // Log
            alert('Fehler beim Abfragen des Scraping-Status.');
        }
    }

    // Ergebnisse anzeigen
    function displayResults(resultHtml) {
        const resultsContainer = document.getElementById("resultsContainer");
        console.log("Displaying results..."); // Log

        if (resultsContainer) {
            resultsContainer.innerHTML = resultHtml;

            document.querySelectorAll('.link-checkbox').forEach(checkbox => {
                checkbox.addEventListener('change', function () {
                    console.log("Checkbox changed:", checkbox.dataset.url, checkbox.checked); // Log
                    updateSelectedLinks(checkbox.dataset.url, checkbox.checked);
                });
            });

            document.querySelectorAll('.link').forEach(link => {
                link.addEventListener('click', function (e) {
                    e.preventDefault();
                    console.log("Link clicked, opening in modal:", link.href); // Log
                    toggleModal(link.href);
                });
            });
        }
    }

    // Ausgewählte Links aktualisieren
    function updateSelectedLinks(url, isSelected) {
        const list = document.getElementById("selectedLinksList");
        console.log("Updating selected links:", url, isSelected); // Log

        if (list) {
            if (isSelected) {
                const li = document.createElement('li');
                li.textContent = url;
                li.dataset.url = url;
                list.appendChild(li);
                console.log("Added link to selected list:", url); // Log
            } else {
                const items = list.querySelectorAll('li');
                items.forEach(item => {
                    if (item.dataset.url === url) {
                        item.remove();
                        console.log("Removed link from selected list:", url); // Log
                    }
                });
            }
        }
    }
});
