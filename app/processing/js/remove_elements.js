// app/processing/js/remove_elements.js

(function() {
    document.addEventListener('DOMContentLoaded', () => {
        // Verzögerung hinzufügen, um sicherzustellen, dass dynamische Inhalte geladen sind
        setTimeout(() => {
            try {
                // Entferne das <div class="mdl-anchornav__container">
                const anchornavContainer = document.querySelector('.mdl-anchornav__container');
                if (anchornavContainer) {
                    anchornavContainer.remove();
                    console.log('Entfernt: .mdl-anchornav__container');
                } else {
                    console.warn('.mdl-anchornav__container wurde nicht gefunden.');
                }

                // Entferne ein weiteres Element (Beispiel)
                const anotherElement = document.querySelector('.another-class');
                if (anotherElement) {
                    anotherElement.remove();
                    console.log('Entfernt: .another-class');
                } else {
                    console.warn('.another-class wurde nicht gefunden.');
                }

                // Weitere Elemente können hier hinzugefügt werden
            } catch (error) {
                console.error('Fehler beim Entfernen der Elemente:', error);
            }
        }, 3000); // Warte 3 Sekunden
    });
})();
