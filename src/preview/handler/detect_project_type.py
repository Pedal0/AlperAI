"""
Détecte le(s) type(s) de projet dans un dossier donné.
"""
import os
from pathlib import Path

def detect_project_type(project_dir):
    """
    Analyse le dossier pour déterminer le(s) type(s) de projet (python, node, php, static, multi...)
    Args:
        project_dir (str or Path): Chemin du projet
    Returns:
        dict: Dictionnaire avec les types détectés et infos associées
    """
    project_dir = Path(project_dir)
    types = []
    info = {}
    if (project_dir / 'requirements.txt').exists():
        types.append('python')
    if (project_dir / 'package.json').exists():
        types.append('node')
    if (project_dir / 'composer.json').exists() or any(f.suffix == '.php' for f in project_dir.rglob('*.php')):
        types.append('php')
    if any((project_dir / d / 'index.html').exists() for d in ('', 'public', 'src')):
        types.append('static')
    
    # Détection explicite Flask : requirements.txt contient 'flask' OU un fichier .py contient 'from flask' ou 'import flask'
    flask_detected = False
    req_path = project_dir / 'requirements.txt'
    if req_path.exists():
        try:
            with open(req_path, 'r', encoding='utf-8') as f:
                content = f.read().lower()
                if 'flask' in content:
                    flask_detected = True
        except Exception:
            pass
    if not flask_detected:
        for py_file in project_dir.glob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    py_content = f.read().lower()
                    if 'from flask' in py_content or 'import flask' in py_content:
                        flask_detected = True
                        break
            except Exception:
                pass
    if flask_detected and 'flask' not in types:
        types.append('flask')

    # Multi-projet: front/back détectés
    for sub in ['client', 'frontend', 'front']:
        if (project_dir / sub).exists():
            info['frontend'] = str(project_dir / sub)
    for sub in ['server', 'backend', 'back', 'api']:
        if (project_dir / sub).exists():
            info['backend'] = str(project_dir / sub)
    if 'frontend' in info and 'backend' in info:
        types.append('multi')
    return {'types': types, 'info': info}
