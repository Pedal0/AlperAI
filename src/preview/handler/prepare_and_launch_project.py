"""
Orchestrateur : détecte le type de projet et lance la préparation/lancement adapté.
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
    if 'multi' in types:
        return prepare_multi_project(info.get('frontend'), info.get('backend'))
    if 'python' in types:
        return prepare_python_project(project_dir)
    if 'node' in types:
        return prepare_node_project(project_dir)
    if 'php' in types:
        return prepare_php_project(project_dir)
    if 'static' in types:
        return prepare_static_project(project_dir)
    return False, "Type de projet non reconnu ou non supporté."
