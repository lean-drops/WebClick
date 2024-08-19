document.addEventListener('DOMContentLoaded', function() {
    function createLinkRow(page, isSubLink = false) {
        const row = document.createElement('tr');
        if (isSubLink) {
            row.classList.add('sub-link');
        }

        const cellSelect = document.createElement('td');
        const cellLink = document.createElement('td');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.value = page.url;
        cellSelect.appendChild(checkbox);

        const link = document.createElement('a');
        link.href = '#';
        link.textContent = page.title;

        const toggleArrow = document.createElement('span');
        toggleArrow.textContent = '▶';
        toggleArrow.className = 'toggle-arrow';
        toggleArrow.addEventListener('click', async (event) => {
            event.stopPropagation();
            if (row.classList.contains('expanded')) {
                collapseSubLinks(row);
            } else {
                await expandSubLinks(row, page.url);
            }
        });

        link.addEventListener('dblclick', (event) => {
            event.preventDefault();
            const windowFeatures = `width=${window.screen.width / 2},height=${window.screen.height},left=${window.screen.width / 2},top=0,scrollbars=yes,resizable=yes`;
            openInNewWindow(page.url, windowFeatures);
        });

        cellLink.appendChild(toggleArrow);
        cellLink.appendChild(link);
        row.appendChild(cellSelect);
        row.appendChild(cellLink);
        return row;
    }

    async function expandSubLinks(parentRow, url) {
        const response = await fetch('/scrape_sub_links', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url: url }),
        });

        const data = await response.json();
        if (data.error) {
            showError(data.error);
            return;
        }

        const uniqueLinks = filterUniqueLinks(data.links); // Filter duplizierte Links
        uniqueLinks.forEach(subLink => {
            const subLinkRow = createLinkRow(subLink, true);
            parentRow.after(subLinkRow);
        });

        parentRow.classList.add('expanded');
    }

    function collapseSubLinks(parentRow) {
        let nextSibling = parentRow.nextSibling;
        while (nextSibling && nextSibling.classList.contains('sub-link')) {
            nextSibling.remove();
            nextSibling = parentRow.nextSibling;
        }
        parentRow.classList.remove('expanded');
    }

    function filterUniqueLinks(links) {
        const seen = new Set();
        return links.filter(link => {
            const duplicate = seen.has(link.url);
            seen.add(link.url);
            return !duplicate;
        });
    }
});
