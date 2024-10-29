import os


# Liste von Datei-Endungen, die in der Ausgabe berücksichtigt werden sollen
ALLOWED_EXTENSIONS = {".py", ".pdf", ".json", ".css", ".html", ".gif", ".png", ".jpg", ".jpeg", ".env"}

# Liste von Ordnern, die ignoriert werden sollen
IGNORED_FOLDERS = {"venv", "node_modules", "__pycache__", "dist", "build", "External Libraries", "Scratches and Consoles", ".venv(310)", "webvenv(310)",".git"}


def list_files_in_directory(directory, indent_level=0):
    # Erzeugt eine strukturierte Liste von Dateien und Ordnern
    structure = ""
    indent = "    " * indent_level  # Einrückung für die Ausgabe
    for root, dirs, files in os.walk(directory):
        # Ignoriere unerwünschte Ordner
        dirs[:] = [d for d in dirs if d not in IGNORED_FOLDERS]

        for file in sorted(files):
            # Zeigt nur Dateien mit erlaubten Endungen an
            if any(file.endswith(ext) for ext in ALLOWED_EXTENSIONS):
                relative_path = os.path.relpath(os.path.join(root, file), directory)
                structure += f"{indent}{relative_path}\n"
        for d in sorted(dirs):
            # Erzeugt eine hierarchische Struktur
            structure += f"{indent}{d}/\n"
            structure += list_files_in_directory(os.path.join(root, d), indent_level + 1)
        break  # stoppt die Schleife nach dem Verzeichnis

    return structure


# Hauptprogramm
if __name__ == "__main__":

    # Ordner-Auswahl
    folder_path = "/Users/python/Satelite 1 Python Projekte/Archiv/WebClick"

    # Wenn ein Ordner ausgewählt wurde, Struktur anzeigen
    if folder_path:
        structure = list_files_in_directory(folder_path)

        if structure:
            print("Projektstruktur:")
            print(structure)
        else:
            print("Keine relevanten Dateien gefunden.")
    else:
        print("Kein Verzeichnis ausgewählt.")
