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
        # Determine entrypoint: require either a start script or a main JS file
        if 'start' in scripts or 'dev' in scripts:
            return True, "Dépendances Node.js installées et build réalisé (si applicable)."
        # Fallback: check for main JS entrypoints
        for main_js in ['server.js', 'app.js', 'index.js', 'main.js']:
            if (project_dir / main_js).exists():
                return True, "Dépendances Node.js installées et build réalisé (si applicable)."
        return False, "Aucun point d'entrée JavaScript trouvé pour lancer le projet."
    except Exception as e:
        return False, f"Erreur Node.js: {e}"
