# Copyright (C) 2025 Perey Alex
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>

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
