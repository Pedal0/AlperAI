"""
Prépare et lance un projet PHP (serveur intégré).
"""
import subprocess
from pathlib import Path

def prepare_php_project(project_dir, port=8000):
    """
    Lance le serveur PHP intégré sur le dossier du projet.
    Args:
        project_dir (str or Path): Dossier du projet
        port (int): Port à utiliser
    Returns:
        tuple: (succès, message)
    """
    project_dir = Path(project_dir)
    try:
        proc = subprocess.Popen(['php', '-S', f'localhost:{port}', '-t', str(project_dir)], cwd=str(project_dir))
        return True, f"Serveur PHP lancé sur http://localhost:{port} (PID {proc.pid})"
    except Exception as e:
        return False, f"Erreur PHP: {e}"