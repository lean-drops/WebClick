// dropdown.js

export function createLinkRow(page, isSubLink = false) {
    console.log("[DEBUG] createLinkRow called with page:", page, "isSubLink:", isSubLink);
    const row = document.createElement('tr');
    if (isSubLink) {
        console.log("[DEBUG] Adding sub-link class to row.");
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
        console.log("[DEBUG] Link double-clicked. Fetching sublinks for:", page.url);
        const sublinks = await fetchSublinks(page.url);
        if (sublinks) {
            console.log("[DEBUG] Sublinks fetched successfully:", sublinks);
            openModalWithLinks(sublinks);  // Open the modal with sublinks
        } else {
            console.log("[ERROR] No sublinks found or failed to fetch sublinks.");
        }
    });

    const toggleArrow = document.createElement('span');
    toggleArrow.textContent = '▶';
    toggleArrow.className = 'toggle-arrow';
    toggleArrow.addEventListener('click', async (event) => {
        event.stopPropagation();
        console.log("[DEBUG] Toggle arrow clicked for:", page.url);
        if (row.classList.contains('expanded')) {
            console.log("[DEBUG] Row is expanded. Collapsing sublinks.");
            collapseSubLinks(row);
        } else {
            console.log("[DEBUG] Row is collapsed. Fetching sublinks for expansion.");
            const sublinks = await fetchSublinks(page.url);
            if (sublinks) {
                console.log("[DEBUG] Sublinks fetched successfully:", sublinks);
                expandSubLinks(row, sublinks);  // Pass the sublinks directly
            } else {
                console.log("[ERROR] Failed to fetch sublinks for expansion.");
            }
        }
    });

    cellLink.appendChild(toggleArrow);
    cellLink.appendChild(link);
    row.appendChild(cellSelect);
    row.appendChild(cellLink);
    console.log("[DEBUG] Row created and populated:", row);
    return row;
}

// Function to expand sublinks
export async function expandSubLinks(row, subLinks) {
    console.log("[DEBUG] expandSubLinks called with row:", row, "subLinks:", subLinks);
    subLinks.forEach(subLink => {
        console.log("[DEBUG] Creating sub-link row for:", subLink);
        const subLinkRow = createLinkRow(subLink, true);
        row.parentNode.insertBefore(subLinkRow, row.nextSibling);
        console.log("[DEBUG] Sub-link row inserted:", subLinkRow);
    });
    row.classList.add('expanded');
    console.log("[DEBUG] Row marked as expanded.");
}

// Function to collapse sublinks
export function collapseSubLinks(row) {
    console.log("[DEBUG] collapseSubLinks called with row:", row);
    let next = row.nextSibling;
    while (next && next.classList.contains('sub-link')) {
        let toRemove = next;
        next = next.nextSibling;
        console.log("[DEBUG] Removing sub-link row:", toRemove);
        toRemove.parentNode.removeChild(toRemove);
    }
    row.classList.remove('expanded');
    console.log("[DEBUG] Row marked as collapsed.");
}

// Function to open a modal with the provided links
export function openModalWithLinks(links) {
    console.log("[DEBUG] openModalWithLinks called with links:", links);
    const modal = document.getElementById('modal');
    const linksList = modal.querySelector('#archived-links-list');
    linksList.innerHTML = '';  // Clear any existing content

    links.forEach(link => {
        console.log("[DEBUG] Adding link to modal:", link);
        const listItem = document.createElement('li');
        const linkElement = document.createElement('a');
        linkElement.href = link.url;
        linkElement.textContent = link.title;
        linkElement.target = "_blank";
        listItem.appendChild(linkElement);
        linksList.appendChild(listItem);
    });

    modal.style.display = 'block';
    console.log("[DEBUG] Modal displayed.");

    const closeModal = () => {
        modal.style.display = 'none';
        console.log("[DEBUG] Modal closed.");
    };

    modal.querySelector('.close').onclick = closeModal;
    window.onclick = function(event) {
        if (event.target == modal) {
            closeModal();
        }
    };
}

// Ensure that the functions are available globally or importable
window.createLinkRow = createLinkRow;
window.expandSubLinks = expandSubLinks;
window.collapseSubLinks = collapseSubLinks;
window.openModalWithLinks = openModalWithLinks;

console.log("[DEBUG] dropdown.js script execution completed.");
