// dropdown.js
export function createLinkRow(page, isSubLink = false) {
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
    link.href = page.url;
    link.target = "_blank";
    link.textContent = page.title;

    link.addEventListener('dblclick', async (event) => {
        event.preventDefault();  // Prevent the link from opening
        const sublinks = await fetchSublinks(page.url);
        if (sublinks) {
            openModalWithLinks(sublinks);  // Open the modal with sublinks
        }
    });

    const toggleArrow = document.createElement('span');
    toggleArrow.textContent = '▶';
    toggleArrow.className = 'toggle-arrow';
    toggleArrow.addEventListener('click', async (event) => {
        event.stopPropagation();
        if (row.classList.contains('expanded')) {
            collapseSubLinks(row);
        } else {
            const sublinks = await fetchSublinks(page.url);
            if (sublinks) {
                expandSubLinks(row, sublinks);  // Pass the sublinks directly
            }
        }
    });

    cellLink.appendChild(toggleArrow);
    cellLink.appendChild(link);
    row.appendChild(cellSelect);
    row.appendChild(cellLink);
    return row;
}

// Ensure that the function is available globally or importable
window.createLinkRow = createLinkRow; // Optional for global use

// dropdown.js

// Funktion zum Erweitern der Sublinks
export async function expandSubLinks(row, url) {
    // Beispielsweise könnte man eine Funktion aufrufen, die die Sublinks für die gegebene URL abruft
    const subLinks = await fetchSubLinks(url); // Diese Funktion muss definiert sein

    subLinks.forEach(subLink => {
        const subLinkRow = createLinkRow(subLink, true);
        row.parentNode.insertBefore(subLinkRow, row.nextSibling);
    });

    row.classList.add('expanded');
}

// Funktion zum Kollabieren der Sublinks
export function collapseSubLinks(row) {
    let next = row.nextSibling;
    while (next && next.classList.contains('sub-link')) {
        let toRemove = next;
        next = next.nextSibling;
        toRemove.parentNode.removeChild(toRemove);
    }
    row.classList.remove('expanded');
}

