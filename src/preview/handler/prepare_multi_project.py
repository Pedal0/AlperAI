"""
Gère les projets multi-services (front/back).
"""
from .prepare_node_project import prepare_node_project
from .prepare_python_project import prepare_python_project
from pathlib import Path

def prepare_multi_project(frontend_dir, backend_dir):
    """
    Lance le front (Node.js) et le back (Python) si détectés.
    Args:
        frontend_dir (str): Dossier du front
        backend_dir (str): Dossier du back
    Returns:
        tuple: (succès, message)
    """
    results = []
    if frontend_dir:
        ok, msg = prepare_node_project(frontend_dir)
        results.append(f"Frontend: {msg}")
    if backend_dir:
        ok, msg = prepare_python_project(backend_dir)
        results.append(f"Backend: {msg}")
    if results:
        return True, " | ".join(results)
    return False, "Aucun front/back détecté."