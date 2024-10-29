import os
import re
import shutil
import subprocess
from config import BASE_DIR

# Einstellungen
ALLOWED_EXTENSIONS = {".py"}
IGNORED_FOLDERS = {
    "venv", "node_modules", "__pycache__", "dist", "build",
    "External Libraries", "Scratches and Consoles", ".venv(310)", ".git", "webvenv(310)"
}

def find_imports_in_file(file_path):
    """
    Extrahiert alle Imports aus einer Datei.
    """
    imports = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                match = re.match(r'^\s*(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_]*)', line)
                if match:
                    imports.add(match.group(1))
    except (UnicodeDecodeError, FileNotFoundError) as e:
        print(f"Fehler beim Lesen der Datei {file_path}: {e}")
    return imports

def find_imports_in_directory(directory):
    """
    Geht alle Python-Dateien durch und sammelt alle Imports.
    """
    all_imports = set()
    for root, dirs, files in os.walk(directory):
        # Ignoriere unerwünschte Ordner
        dirs[:] = [d for d in dirs if d not in IGNORED_FOLDERS]
        for file in files:
            if file.endswith(tuple(ALLOWED_EXTENSIONS)):
                file_path = os.path.join(root, file)
                file_imports = find_imports_in_file(file_path)
                if file_imports:
                    print(f"Gefundene Importe in {file_path}: {file_imports}")
                all_imports.update(file_imports)
    return all_imports

def create_requirements_file(imports, directory):
    """
    Erstellt ein requirements.txt basierend auf den gefundenen Imports mithilfe von pipreqs.
    """
    temp_folder = os.path.join(directory, "temp_imports")
    os.makedirs(temp_folder, exist_ok=True)
    temp_file_path = os.path.join(temp_folder, "temp_script.py")

    # Schreibe alle Imports in ein temporäres Python-File
    with open(temp_file_path, 'w', encoding='utf-8') as temp_file:
        for imp in imports:
            temp_file.write(f"import {imp}\n")

    # Führe pipreqs aus, um requirements.txt zu erstellen
    try:
        print("Führe pipreqs aus, um requirements.txt zu erstellen...")
        subprocess.run(["pipreqs", temp_folder, "--force"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"Fehler beim Ausführen von pipreqs: {e.stderr.decode().strip()}")
        shutil.rmtree(temp_folder)
        return False

    # Verschiebe die generierte requirements.txt in das Projektverzeichnis
    requirements_src = os.path.join(temp_folder, "requirements.txt")
    requirements_dst = os.path.join(directory, "requirements.txt")
    if os.path.exists(requirements_src):
        os.replace(requirements_src, requirements_dst)
        print(f"requirements.txt erfolgreich erstellt unter {requirements_dst}")
    else:
        print("pipreqs konnte keine requirements.txt erstellen.")
        shutil.rmtree(temp_folder)
        return False

    # Bereinige das temporäre Verzeichnis
    shutil.rmtree(temp_folder)
    return True

def create_virtualenv(directory, project_name, python_version="3.10"):
    """
    Erstellt eine virtuelle Umgebung mit dem Namen {projektname}-venv.
    """
    venv_name = f"{project_name}-venv"
    venv_path = os.path.join(directory, venv_name)

    if not os.path.exists(venv_path):
        print(f"Erstelle virtuelle Umgebung '{venv_name}' mit Python {python_version}...")
        try:
            subprocess.run(["python3.10", "-m", "venv", venv_path], check=True)
            print(f"Virtuelle Umgebung '{venv_name}' erfolgreich erstellt unter {venv_path}")
        except subprocess.CalledProcessError as e:
            print(f"Fehler beim Erstellen der virtuellen Umgebung: {e}")
            return None
    else:
        print(f"Virtuelle Umgebung '{venv_name}' existiert bereits unter {venv_path}")

    return venv_path

def install_dependencies(venv_path, requirements_file):
    """
    Installiert die Abhängigkeiten aus requirements.txt in der angegebenen virtuellen Umgebung.
    """
    if os.name == 'nt':
        # Windows
        pip_executable = os.path.join(venv_path, "Scripts", "pip.exe")
    else:
        # Unix/Linux/Mac
        pip_executable = os.path.join(venv_path, "bin", "pip")

    if not os.path.exists(pip_executable):
        print(f"pip wurde in der virtuellen Umgebung nicht gefunden: {pip_executable}")
        return False

    print(f"Installiere Abhängigkeiten aus {requirements_file} in der virtuellen Umgebung...")
    try:
        subprocess.run([pip_executable, "install", "-r", requirements_file], check=True)
        print("Alle Abhängigkeiten wurden erfolgreich installiert.")
    except subprocess.CalledProcessError as e:
        print(f"Fehler beim Installieren der Abhängigkeiten: {e}")
        return False

    return True

def main():
    # Bestimme den Projektnamen aus BASE_DIR
    project_name = os.path.basename(os.path.normpath(BASE_DIR))
    print(f"Projektname: {project_name}")

    # Suche nach Imports
    print("Suche nach Imports im Projektverzeichnis...")
    imports = find_imports_in_directory(BASE_DIR)
    if not imports:
        print("Keine Importe gefunden. Das requirements.txt wird nicht erstellt.")
        return

    # Erstelle requirements.txt
    print("Erstelle requirements.txt basierend auf den gefundenen Imports...")
    if not create_requirements_file(imports, BASE_DIR):
        print("Fehler beim Erstellen der requirements.txt. Vorgang abgebrochen.")
        return

    # Erstelle virtuelle Umgebung
    print("Richte die virtuelle Umgebung ein...")
    venv_path = create_virtualenv(BASE_DIR, project_name)
    if not venv_path:
        print("Fehler beim Einrichten der virtuellen Umgebung. Vorgang abgebrochen.")
        return

    # Installiere Abhängigkeiten in der virtuellen Umgebung
    requirements_file = os.path.join(BASE_DIR, "requirements.txt")
    if not install_dependencies(venv_path, requirements_file):
        print("Fehler beim Installieren der Abhängigkeiten. Überprüfe die requirements.txt und die Netzwerkverbindung.")
        return

    # Abschließende Hinweise
    print("\nSetup abgeschlossen!")
    print(f"Die virtuelle Umgebung wurde erstellt unter: {venv_path}")
    print("Um die virtuelle Umgebung zu aktivieren, verwende folgenden Befehl in deinem Terminal:")
    if os.name == 'nt':
        print(f"```shell\n{venv_path}\\Scripts\\activate\n```")
    else:
        print(f"```shell\nsource {venv_path}/bin/activate\n```")
    print("\nAuf PythonAnywhere kannst du die virtuelle Umgebung wie folgt aktivieren und die Abhängigkeiten nutzen:")
    print("1. Öffne eine Bash-Konsole.")
    print(f"2. Aktiviere die virtuelle Umgebung mit: source {venv_path}/bin/activate")
    print("3. Stelle sicher, dass deine Web-App auf diese virtuelle Umgebung zeigt.")
    print("4. Falls Änderungen an den Abhängigkeiten vorgenommen wurden, führe erneut `pip install -r requirements.txt` in der aktivierten venv aus.")

if __name__ == "__main__":
    main()
