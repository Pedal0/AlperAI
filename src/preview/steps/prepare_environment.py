"""
Prépare l'environnement du projet (Python venv, npm install, etc.) selon le type de projet.
"""
import subprocess
import platform
from pathlib import Path
from .detect_project_type import ProjectType
from src.preview.handler.prepare_and_launch_project import prepare_and_launch_project

def prepare_environment(project_dir: str, project_type: str):
    """
    Nouvelle version : utilise l'orchestrateur universel pour préparer et lancer le projet.
    """
    # On ignore project_type, la détection est automatique
    success, message = prepare_and_launch_project(project_dir)
    return success, message
