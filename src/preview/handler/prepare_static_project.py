"""
Sert un dossier statique (index.html dans racine, public ou src).
"""
import subprocess
import sys
from pathlib import Path
import platform

def find_free_port(start=8080, end=9000):
    import socket
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("localhost", port))
                return port
            except OSError:
                continue
    return 8080  # fallback

def prepare_static_project(project_dir, port=None):
    """
    Sert le dossier contenant index.html avec npx serve ou python -m http.server en fallback.
    Args:
        project_dir (str or Path): Dossier du projet
        port (int): Port à utiliser
    Returns:
        tuple: (succès, message)
    """
    project_dir = Path(project_dir)
    for sub in ['', 'public', 'src']:
        index = project_dir / sub / 'index.html' if sub else project_dir / 'index.html'
        if index.exists():
            serve_dir = index.parent
            # Choisir dynamiquement un port libre si non fourni
            if port is None:
                port = find_free_port()
            # Essayer d'abord npx serve
            try:
                proc = subprocess.Popen(['npx', 'serve', '-l', str(port), str(serve_dir)], cwd=str(project_dir))
                return True, f"Site statique servi sur http://localhost:{port} (PID {proc.pid}) via npx serve"
            except Exception as e:
                # Fallback sys.executable puis python
                py_cmds = [sys.executable]
                if platform.system() == 'Windows':
                    py_cmds.append('python')
                for py_cmd in py_cmds:
                    try:
                        proc = subprocess.Popen([py_cmd, '-m', 'http.server', str(port)], cwd=str(serve_dir))
                        return True, f"Site statique servi sur http://localhost:{port} (PID {proc.pid}) via {py_cmd} http.server"
                    except Exception as e2:
                        last_error = e2
                return False, f"Erreur static: npx serve: {e} | python http.server: {last_error}"
    return False, "Aucun index.html trouvé dans racine, public ou src."
