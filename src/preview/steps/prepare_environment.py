"""
Prépare l'environnement du projet (Python venv, npm install, etc.) selon le type de projet.
"""
import subprocess
import platform
from pathlib import Path
from .detect_project_type import ProjectType

def prepare_environment(project_dir: str, project_type: str):
    project_dir = Path(project_dir)
    try:
        if project_type == ProjectType.FLASK:
            venv_dir = project_dir / "venv"
            if not venv_dir.exists():
                subprocess.check_call([platform.python_implementation().lower(), "-m", "venv", str(venv_dir)])
            if platform.system() == "Windows":
                pip_path = venv_dir / "Scripts" / "pip"
            else:
                pip_path = venv_dir / "bin" / "pip"
            requirements_file = project_dir / "requirements.txt"
            if requirements_file.exists():
                subprocess.check_call([str(pip_path), "install", "-r", str(requirements_file)])
            return True, "Environnement Python prêt."
        elif project_type in [ProjectType.EXPRESS, ProjectType.REACT, ProjectType.VUE, ProjectType.ANGULAR]:
            if (project_dir / "node_modules").exists():
                return True, "Les modules Node.js sont déjà installés."
            npm_process = subprocess.Popen([
                "npm", "install"], cwd=str(project_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = npm_process.communicate()
            if npm_process.returncode != 0:
                return False, f"Erreur lors de l'installation des dépendances Node.js: {stderr}"
            return True, "Dépendances Node.js installées."
        elif project_type == ProjectType.STATIC:
            if (project_dir / "package.json").exists():
                if (project_dir / "node_modules").exists():
                    return True, "Les modules Node.js sont déjà installés."
                npm_process = subprocess.Popen([
                    "npm", "install"], cwd=str(project_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = npm_process.communicate()
                if npm_process.returncode != 0:
                    return True, f"Site statique avec dépendances prêt (erreur npm: {stderr})"
                return True, "Site statique avec dépendances prêt."
            return True, "Site statique prêt."
        else:
            if (project_dir / "package.json").exists():
                if (project_dir / "node_modules").exists():
                    return True, "Les modules Node.js sont déjà installés."
                npm_process = subprocess.Popen([
                    "npm", "install"], cwd=str(project_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = npm_process.communicate()
                if npm_process.returncode != 0:
                    return False, f"Erreur lors de l'installation des dépendances Node.js: {stderr}"
                return True, "Dépendances Node.js installées pour projet de type inconnu."
            return True, "Aucune préparation nécessaire pour ce type de projet inconnu."
    except Exception as e:
        return False, f"Erreur: {str(e)}"
