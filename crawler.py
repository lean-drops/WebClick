import os
import re
import shutil
import subprocess
import sys
import logging
import argparse
from pathlib import Path
from typing import Set, Optional

try:
    from config import BASE_DIR
except ImportError:
    BASE_DIR = Path.cwd()

# Konfiguration des Loggings
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("setup.log", encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Einstellungen
ALLOWED_EXTENSIONS = {".py"}
IGNORED_FOLDERS = {
    "venv", "node_modules", "__pycache__", "dist", "build",
    "External Libraries", "Scratches and Consoles", ".venv(310)", ".git", "webvenv(310)"
}

def find_imports_in_file(file_path: Path) -> Set[str]:
    """
    Extrahiert alle Imports aus einer Datei.
    """
    imports = set()
    try:
        with file_path.open('r', encoding='utf-8') as file:
            for line in file:
                match = re.match(r'^\s*(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_\.]*)', line)
                if match:
                    # Extrahiere das Hauptmodul (z.B. aus 'package.module' wird 'package')
                    main_module = match.group(1).split('.')[0]
                    imports.add(main_module)
    except (UnicodeDecodeError, FileNotFoundError) as e:
        logger.error(f"Fehler beim Lesen der Datei {file_path}: {e}")
    return imports

def find_imports_in_directory(directory: Path) -> Set[str]:
    """
    Geht alle Python-Dateien durch und sammelt alle Imports.
    """
    all_imports = set()
    for root, dirs, files in os.walk(directory):
        # Ignoriere unerwünschte Ordner
        dirs[:] = [d for d in dirs if d not in IGNORED_FOLDERS]
        for file in files:
            if Path(file).suffix in ALLOWED_EXTENSIONS:
                file_path = Path(root) / file
                file_imports = find_imports_in_file(file_path)
                if file_imports:
                    logger.debug(f"Gefundene Importe in {file_path}: {file_imports}")
                all_imports.update(file_imports)
    return all_imports

def check_pipreqs_installed() -> bool:
    """
    Überprüft, ob pipreqs installiert ist.
    """
    if shutil.which("pipreqs") is None:
        logger.error("pipreqs ist nicht installiert. Bitte installieren Sie es mit `pip install pipreqs`.")
        return False
    return True

def create_requirements_file(imports: Set[str], directory: Path) -> bool:
    """
    Erstellt ein requirements.txt basierend auf den gefundenen Imports mithilfe von pipreqs.
    """
    if not check_pipreqs_installed():
        return False

    temp_folder = directory / "temp_imports"
    temp_folder.mkdir(exist_ok=True)
    temp_file_path = temp_folder / "temp_script.py"

    # Schreibe alle Imports in ein temporäres Python-File
    try:
        with temp_file_path.open('w', encoding='utf-8') as temp_file:
            for imp in imports:
                temp_file.write(f"import {imp}\n")
        logger.info(f"Temporäre Datei für pipreqs erstellt unter {temp_file_path}")
    except Exception as e:
        logger.error(f"Fehler beim Schreiben der temporären Datei: {e}")
        shutil.rmtree(temp_folder, ignore_errors=True)
        return False

    # Führe pipreqs aus, um requirements.txt zu erstellen
    try:
        logger.info("Führe pipreqs aus, um requirements.txt zu erstellen...")
        result = subprocess.run(
            ["pipreqs", str(temp_folder), "--force"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logger.debug(result.stdout)
        logger.debug(result.stderr)
    except subprocess.CalledProcessError as e:
        logger.error(f"Fehler beim Ausführen von pipreqs: {e.stderr.strip()}")
        shutil.rmtree(temp_folder, ignore_errors=True)
        return False

    # Verschiebe die generierte requirements.txt in das Projektverzeichnis
    requirements_src = temp_folder / "requirements.txt"
    requirements_dst = directory / "requirements.txt"
    if requirements_src.exists():
        try:
            shutil.move(str(requirements_src), str(requirements_dst))
            logger.info(f"requirements.txt erfolgreich erstellt unter {requirements_dst}")
        except Exception as e:
            logger.error(f"Fehler beim Verschieben der requirements.txt: {e}")
            shutil.rmtree(temp_folder, ignore_errors=True)
            return False
    else:
        logger.error("pipreqs konnte keine requirements.txt erstellen.")
        shutil.rmtree(temp_folder, ignore_errors=True)
        return False

    # Bereinige das temporäre Verzeichnis
    shutil.rmtree(temp_folder, ignore_errors=True)
    return True

def create_virtualenv(directory: Path, project_name: str, python_version: str = "3.10") -> Optional[Path]:
    """
    Erstellt eine virtuelle Umgebung mit dem Namen {projektname}-venv.
    """
    venv_name = f"{project_name}-venv"
    venv_path = directory / venv_name

    python_executable = shutil.which(f"python{python_version}") or shutil.which("python3")
    if not python_executable:
        logger.error(f"Python {python_version} ist nicht installiert oder nicht im PATH verfügbar.")
        return None

    if not venv_path.exists():
        logger.info(f"Erstelle virtuelle Umgebung '{venv_name}' mit Python {python_version}...")
        try:
            subprocess.run([python_executable, "-m", "venv", str(venv_path)], check=True)
            logger.info(f"Virtuelle Umgebung '{venv_name}' erfolgreich erstellt unter {venv_path}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Fehler beim Erstellen der virtuellen Umgebung: {e}")
            return None
    else:
        logger.info(f"Virtuelle Umgebung '{venv_name}' existiert bereits unter {venv_path}")

    return venv_path

def install_dependencies(venv_path: Path, requirements_file: Path) -> bool:
    """
    Installiert die Abhängigkeiten aus requirements.txt in der angegebenen virtuellen Umgebung.
    """
    if os.name == 'nt':
        # Windows
        pip_executable = venv_path / "Scripts" / "pip.exe"
    else:
        # Unix/Linux/Mac
        pip_executable = venv_path / "bin" / "pip"

    if not pip_executable.exists():
        logger.error(f"pip wurde in der virtuellen Umgebung nicht gefunden: {pip_executable}")
        return False

    logger.info(f"Installiere Abhängigkeiten aus {requirements_file} in der virtuellen Umgebung...")
    try:
        result = subprocess.run(
            [str(pip_executable), "install", "-r", str(requirements_file)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logger.debug(result.stdout)
        logger.debug(result.stderr)
        logger.info("Alle Abhängigkeiten wurden erfolgreich installiert.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Fehler beim Installieren der Abhängigkeiten: {e.stderr.strip()}")
        return False

    return True

def parse_arguments() -> argparse.Namespace:
    """
    Parst die Kommandozeilenargumente.
    """
    parser = argparse.ArgumentParser(
        description="Automatisiert die Einrichtung einer Python-Projektumgebung."
    )
    parser.add_argument(
        "--base-dir",
        type=str,
        default=str(BASE_DIR),
        help="Das Basisverzeichnis des Projekts."
    )
    parser.add_argument(
        "--python-version",
        type=str,
        default="3.10",
        help="Die Python-Version für die virtuelle Umgebung (z.B. 3.8, 3.9, 3.10)."
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Aktiviere detailliertes Logging."
    )
    return parser.parse_args()

def main():
    args = parse_arguments()

    # Anpassung des Log-Levels
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose-Modus aktiviert.")

    base_dir = Path(args.base_dir).resolve()
    if not base_dir.exists():
        logger.error(f"Das angegebene Basisverzeichnis existiert nicht: {base_dir}")
        sys.exit(1)

    # Bestimme den Projektnamen aus BASE_DIR
    project_name = base_dir.name
    logger.info(f"Projektname: {project_name}")

    # Suche nach Imports
    logger.info("Suche nach Imports im Projektverzeichnis...")
    imports = find_imports_in_directory(base_dir)
    if not imports:
        logger.warning("Keine Importe gefunden. Das requirements.txt wird nicht erstellt.")
        sys.exit(0)

    logger.debug(f"Alle gefundenen Importe: {imports}")

    # Erstelle requirements.txt
    logger.info("Erstelle requirements.txt basierend auf den gefundenen Imports...")
    if not create_requirements_file(imports, base_dir):
        logger.error("Fehler beim Erstellen der requirements.txt. Vorgang abgebrochen.")
        sys.exit(1)

    # Erstelle virtuelle Umgebung
    logger.info("Richte die virtuelle Umgebung ein...")
    venv_path = create_virtualenv(base_dir, project_name, args.python_version)
    if not venv_path:
        logger.error("Fehler beim Einrichten der virtuellen Umgebung. Vorgang abgebrochen.")
        sys.exit(1)

    # Installiere Abhängigkeiten in der virtuellen Umgebung
    requirements_file = base_dir / "requirements.txt"
    if not install_dependencies(venv_path, requirements_file):
        logger.error("Fehler beim Installieren der Abhängigkeiten. Überprüfe die requirements.txt und die Netzwerkverbindung.")
        sys.exit(1)

    # Abschließende Hinweise
    logger.info("\nSetup abgeschlossen!")
    logger.info(f"Die virtuelle Umgebung wurde erstellt unter: {venv_path}")
    logger.info("Um die virtuelle Umgebung zu aktivieren, verwende folgenden Befehl in deinem Terminal:")
    if os.name == 'nt':
        activation_command = f"{venv_path}\\Scripts\\activate"
    else:
        activation_command = f"source {venv_path}/bin/activate"
    logger.info(f"```shell\n{activation_command}\n```")
    logger.info("\nAuf PythonAnywhere kannst du die virtuelle Umgebung wie folgt aktivieren und die Abhängigkeiten nutzen:")
    logger.info("1. Öffne eine Bash-Konsole.")
    logger.info(f"2. Aktiviere die virtuelle Umgebung mit: source {venv_path}/bin/activate")
    logger.info("3. Stelle sicher, dass deine Web-App auf diese virtuelle Umgebung zeigt.")
    logger.info("4. Falls Änderungen an den Abhängigkeiten vorgenommen wurden, führe erneut `pip install -r requirements.txt` in der aktivierten venv aus.")

if __name__ == "__main__":
    main()
