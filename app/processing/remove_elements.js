// app/processing/js/remove_elements.js

(function() {
    // Entferne das <div class="mdl-anchornav__container">
    const anchornavContainer = document.querySelector('.mdl-anchornav__container');
    if (anchornavContainer) {
        anchornavContainer.remove();
        console.log('Entfernt: .mdl-anchornav__container');
    } else {
        console.warn('.mdl-anchornav__container wurde nicht gefunden.');
    }

    // Optional: Weitere Elemente können hier hinzugefügt werden
    // Beispiel: Entferne ein weiteres Element
    /*
    const anotherElement = document.querySelector('.another-class');
    if (anotherElement) {
        anotherElement.remove();
        console.log('Entfernt: .another-class');
    }
    */
})();
