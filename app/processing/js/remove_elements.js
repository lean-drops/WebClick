// app/processing/js/remove_elements.js

function removeElements(config) {
    if (!config || !config.remove) {
        console.warn("Keine Konfiguration für removeElements gefunden.");
        return;
    }
    const selectorsToRemove = config.remove;
    selectorsToRemove.forEach(selector => {
        const elements = document.querySelectorAll(selector);
        elements.forEach(el => el.remove());
    });
}
