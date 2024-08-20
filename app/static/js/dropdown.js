export function createLinkRow(page, level = 0) {
    const row = document.createElement('tr');
    const cell = document.createElement('td');

    cell.textContent = page.title || page.url;
    cell.style.paddingLeft = `${level * 20}px`;  // Indentation for hierarchy
    row.appendChild(cell);

    if (page.links && page.links.length > 0) {
        const toggleCell = document.createElement('td');
        const toggleButton = document.createElement('button');
        toggleButton.textContent = "+";
        toggleButton.classList.add('toggle-arrow', 'collapsed');

        toggleButton.addEventListener('click', function () {
            const isCollapsed = toggleButton.classList.contains('collapsed');
            if (isCollapsed) {
                toggleButton.textContent = "-";
                expandSubLinks(toggleButton, page.links, level + 1);
            } else {
                toggleButton.textContent = "+";
                collapseSubLinks(toggleButton);
            }
            toggleButton.classList.toggle('collapsed');
        });

        toggleCell.appendChild(toggleButton);
        row.appendChild(toggleCell);
    }

    console.log("[DEBUG] Row created and populated:", row);
    return row;
}

export function expandSubLinks(element, links, level) {
    console.log("[DEBUG] Expanding sublinks for element:", element);
    const parentRow = element.closest('tr');

    links.forEach(link => {
        const newRow = createLinkRow(link, level);
        newRow.classList.add('sublink-row'); // Class for identification
        parentRow.insertAdjacentElement('afterend', newRow);
    });
}

export function collapseSubLinks(element) {
    console.log("[DEBUG] Collapsing sublinks.");
    const parentRow = element.closest('tr');
    let nextRow = parentRow.nextElementSibling;
    while (nextRow && nextRow.classList.contains('sublink-row')) {
        const rowToRemove = nextRow;
        nextRow = nextRow.nextElementSibling;
        rowToRemove.remove();
    }
}
