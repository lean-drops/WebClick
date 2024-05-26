from app import create_app
import os
import socket

# Erstelle die Flask-Anwendung
app = create_app()

if __name__ == '__main__':
    # Setze Debug-Modus basierend auf einer Umgebungsvariablen
    debug_mode = os.environ.get('FLASK_DEBUG', 'True').lower() in ['true', '1', 't']

    # Finde einen freien Port, falls der Standardport 5000 belegt ist
    port = int(os.environ.get('PORT', 5000))
    if port == 5000:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        if result == 0:
            port = 5001  # Ändere den Port, wenn 5000 belegt ist
        sock.close()

    try:
        # Starte die Anwendung
        app.run(debug=debug_mode, port=port)
    except Exception as e:
        # Fange Ausnahmen ab und gib eine Fehlermeldung aus
        print(f"Ein Fehler ist aufgetreten: {e}")
