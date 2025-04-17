"""
Prépare et lance un projet Node.js (npm install, build, run).
"""
import subprocess
from pathlib import Path

def prepare_node_project(project_dir):
    """
    Installe les dépendances Node.js, build si besoin, puis lance le projet.
    Args:
        project_dir (str or Path): Dossier du projet
    Returns:
        tuple: (succès, message)
    """
    project_dir = Path(project_dir)
    try:
        subprocess.check_call(['npm', 'install'], cwd=str(project_dir))
        pkg = project_dir / 'package.json'
        import json
        with open(pkg, 'r', encoding='utf-8') as f:
            data = json.load(f)
        scripts = data.get('scripts', {})
        if 'build:css' in scripts:
            subprocess.check_call(['npm', 'run', 'build:css'], cwd=str(project_dir))
        if 'build' in scripts:
            subprocess.check_call(['npm', 'run', 'build'], cwd=str(project_dir))
        run_script = 'start' if 'start' in scripts else ('dev' if 'dev' in scripts else None)
        if run_script:
            proc = subprocess.Popen(['npm', 'run', run_script], cwd=str(project_dir))
            return True, f"Projet Node.js lancé (npm run {run_script}) sur PID {proc.pid}"
        return False, "Aucun script de lancement trouvé dans package.json."
    except Exception as e:
        return False, f"Erreur Node.js: {e}"
