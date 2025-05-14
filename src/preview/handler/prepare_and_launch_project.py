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
Orchestrateur : détecte le type de projet et lance la préparation/lancement adapté.
"""
from .detect_project_type import detect_project_type
from .prepare_python_project import prepare_python_project
from .prepare_node_project import prepare_node_project
from .prepare_php_project import prepare_php_project
from .prepare_static_project import prepare_static_project
from .prepare_multi_project import prepare_multi_project

def prepare_and_launch_project(project_dir):
    """
    Détecte le type de projet et lance la préparation/lancement adapté.
    Args:
        project_dir (str): Dossier du projet
    Returns:
        tuple: (succès, message)
    """
    detection = detect_project_type(project_dir)
    types = detection['types']
    info = detection['info']
    # Flask apps run as Python projects
    if 'flask' in types:
        return prepare_python_project(project_dir)
    if 'multi' in types:
        return prepare_multi_project(info.get('frontend'), info.get('backend'))
    # Node-based projects (Express, React, Vue, Angular)
    if any(t in types for t in ['express', 'node', 'react', 'vue', 'angular']):
        return prepare_node_project(project_dir)
    # Python projects
    if 'python' in types:
        return prepare_python_project(project_dir)
    if 'php' in types:
        return prepare_php_project(project_dir)
    if 'static' in types:
        return prepare_static_project(project_dir)
    return False, "Type de projet non reconnu ou non supporté."
