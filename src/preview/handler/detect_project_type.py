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
Détecte le(s) type(s) de projet dans un dossier donné.
"""
import os
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

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
    pkg_path = project_dir / 'package.json'

    # À la place de la simple détection 'node', faites :
    if pkg_path.exists():
        try:
            pkg = json.loads(pkg_path.read_text(encoding='utf-8'))
            deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
            if 'react' in deps:
                types.append('react')
            elif 'vue' in deps:
                types.append('vue')
            elif '@angular/core' in deps or (project_dir / 'angular.json').exists():
                types.append('angular')
            elif 'express' in deps:
                types.append('express')
            else:
                types.append('node')
        except Exception:
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

    # Streamlit detection: check requirements or imports
    streamlit_detected = False
    if req_path.exists():
        try:
            with open(req_path, 'r', encoding='utf-8') as f:
                if 'streamlit' in f.read().lower():
                    streamlit_detected = True
        except:
            pass
    if not streamlit_detected:
        for py_file in project_dir.glob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                    if 'import streamlit' in content:
                        streamlit_detected = True
                        break
            except:
                pass
    if streamlit_detected and 'streamlit' not in types:
        types.append('streamlit')

    # After explicit detections (Flask, Streamlit, PHP, Node, React, Vue, Angular, Static)
    # Fallback Python detection: pure Python if nothing else
    req_file = project_dir / 'requirements.txt'
    if not types and req_file.exists() and any(project_dir.glob('*.py')):
        types.append('python')

    # Multi-projet: front/back détectés
    for sub in ['client', 'frontend', 'front']:
        if (project_dir / sub).exists():
            info['frontend'] = str(project_dir / sub)
    for sub in ['server', 'backend', 'back', 'api']:
        if (project_dir / sub).exists():
            info['backend'] = str(project_dir / sub)
    if 'frontend' in info and 'backend' in info:
        types.append('multi')
    
    logger.debug(f"detect_project_type: project_dir={project_dir}, types={types}, info={info}")
    return {'types': types, 'info': info}