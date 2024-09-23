import os
import tempfile
import pathlib

def test_file_creation(directory):
    try:
        # Teste das Erstellen einer Datei im angegebenen Verzeichnis
        test_file_path = pathlib.Path(directory) / "test_file.txt"
        test_file_path.write_text("Test content")
        print(f"Erstellen und Schreiben der Datei war erfolgreich: {test_file_path}")
        test_file_path.unlink()  # Datei nach dem Test löschen
    except PermissionError as e:
        print(f"PermissionError beim Erstellen/Schreiben der Datei: {e}")
    except Exception as e:
        print(f"Ein unerwarteter Fehler ist aufgetreten: {e}")

def test_directory_creation(base_directory):
    try:
        # Teste das Erstellen eines Unterverzeichnisses im angegebenen Basisverzeichnis
        test_dir_path = pathlib.Path(base_directory) / f"test_dir_{os.getpid()}"
        test_dir_path.mkdir(parents=True, exist_ok=True)
        print(f"Erstellen des Verzeichnisses war erfolgreich: {test_dir_path}")
        test_file_creation(test_dir_path)  # Teste das Erstellen einer Datei im neuen Verzeichnis
        test_dir_path.rmdir()  # Verzeichnis nach dem Test löschen
    except PermissionError as e:
        print(f"PermissionError beim Erstellen des Verzeichnisses: {e}")
    except Exception as e:
        print(f"Ein unerwarteter Fehler ist aufgetreten: {e}")

def test_tempfile_creation():
    try:
        # Teste das Erstellen eines temporären Verzeichnisses
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"Erstellen eines temporären Verzeichnisses war erfolgreich: {temp_dir}")
            test_file_creation(temp_dir)  # Teste das Erstellen einer Datei im temporären Verzeichnis
    except Exception as e:
        print(f"Ein unerwarteter Fehler ist im temporären Verzeichnis aufgetreten: {e}")

def analyze_permission_issues():
    # Teste verschiedene Verzeichnisse, um Berechtigungsprobleme zu diagnostizieren
    print("Teste das Benutzerverzeichnis:")
    test_directory_creation(pathlib.Path.home())

    print("\nTeste das aktuelle Arbeitsverzeichnis:")
    test_directory_creation(os.getcwd())

    print("\nTeste das Erstellen eines temporären Verzeichnisses:")
    test_tempfile_creation()

if __name__ == "__main__":
    analyze_permission_issues()
