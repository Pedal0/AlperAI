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
Orchestrateur : Génère la configuration de lancement via IA et exécute le projet.
"""
import json
import logging
from pathlib import Path
import asyncio

# Import des nouvelles fonctions et des gestionnaires nécessaires
from .generate_start_scripts import generate_launch_config_from_ai
from src.preview.steps.run_application import run_application_async_wrapper
# from src.preview.preview_manager import get_preview_manager # This was causing the circular import

logger = logging.getLogger(__name__)

async def prepare_and_launch_project_async(project_name: str, project_dir_str: str, ai_model: str = None, api_key: str = None):
    """
    Prépare et lance un projet en utilisant la configuration de lancement générée par l'IA.
    Args:
        project_name (str): Nom du projet (pour le gestionnaire de preview).
        project_dir_str (str): Chemin du dossier du projet.
        ai_model (str): Nom du modèle IA à utiliser (par défaut OpenAI nano).
        api_key (str): Clé API à utiliser pour l'appel IA (optionnel).
    Returns:
        tuple: (succès, message, port_optionnel)
    """
    project_dir = Path(project_dir_str)
    
    # Import get_preview_manager here to avoid circular import at module level
    from src.preview.preview_manager import get_preview_manager
    preview_manager = get_preview_manager()

    # Utiliser une fonction de log qui est spécifique au projet via le preview_manager
    # Ceci permet de voir les logs dans l'interface utilisateur pour ce projet spécifique.
    def log_callback(message):
        logger.info(f"[{project_name}] {message}") # Log global
        preview_manager.add_log_entry_project_specific(project_name, message) # Log pour l'UI

    log_callback(f"Starting preparation and launch for project '{project_name}' at {project_dir}")
    preview_manager.update_project_status(project_name, "initializing", "Preparing project...")

    # 1. Try to load launch_commands.json if it exists and is valid
    launch_config_path = project_dir / "launch_commands.json"
    launch_config = None
    if launch_config_path.exists():
        try:
            with open(launch_config_path, "r", encoding="utf-8") as f:
                launch_config = json.load(f)
            if not (isinstance(launch_config, dict) and launch_config.get("commands") and isinstance(launch_config["commands"], list) and len(launch_config["commands"]) > 0):
                log_callback("launch_commands.json found but invalid or empty, will re-generate via AI.")
                launch_config = None
            else:
                log_callback("Using cached launch_commands.json (AI will not be called).")
        except Exception as e:
            log_callback(f"Error reading launch_commands.json: {e}. Will re-generate via AI.")
            launch_config = None
    
    # 2. If not valid, generate via AI (with correct model)
    if not launch_config:
        log_callback(f"Attempting to generate AI launch configuration using model: {ai_model}")
        launch_config = await generate_launch_config_from_ai(project_dir_str, log_callback=log_callback, api_key=api_key, model_name=ai_model)

    if not launch_config or not launch_config.get("commands"):
        message = "Failed to generate or retrieve valid launch commands from AI."
        log_callback(message)
        preview_manager.update_project_status(project_name, "error", message)
        return False, message, None

    log_callback(f"Launch configuration to be used: {json.dumps(launch_config)}")

    # La configuration est déjà un dict, nous la convertissons en chaîne JSON pour run_application_async_wrapper
    commands_data_json = json.dumps(launch_config)

    # Venv path: pour l'instant, on suppose que les commandes de l'IA gèrent l'activation du venv si nécessaire.
    # Ou que l'environnement d'exécution global est configuré correctement.
    venv_path_str = None 
    # Si vous avez un moyen de déterminer le chemin du venv (par ex. s'il est toujours nommé 'venv'):
    # potential_venv_path = project_dir / "venv"
    # if potential_venv_path.is_dir():
    #     venv_path_str = str(potential_venv_path)
    #     log_callback(f"Virtual environment path identified (but not activated by this script): {venv_path_str}")

    # 3. Run the application using the AI-generated commands
    log_callback("Executing launch commands...")
    preview_manager.update_project_status(project_name, "starting", "Executing launch commands...")
    
    run_result = await run_application_async_wrapper(
        project_dir_str=project_dir_str,
        commands_data_json=commands_data_json,
        venv_path_str=venv_path_str, # Passé ici, mais run_application gère son utilisation
        log_callback=log_callback,
        attempt_ai_fix=True, # Activer la boucle de correction par IA
        ai_model=ai_model,
        api_key=api_key
    )

    if run_result["success"]:
        process_info = run_result.get("process") # Objet Popen du processus principal (serveur)
        message = f"Application '{project_name}' seems to have started successfully."
        log_callback(message)

        # Prefer detected url/port from run_result
        app_url = run_result.get("url")
        port = run_result.get("port")
        if not app_url and port:
            app_url = f"http://localhost:{port}"
        if not port:
            # Try to get from config as fallback
            port = launch_config.get("env", {}).get("PORT")
            if port:
                try:
                    port = int(port)
                    if not app_url:
                        app_url = f"http://localhost:{port}"
                except ValueError:
                    log_callback(f"Warning: Port '{port}' from config is not a valid integer. URL cannot be determined.")
                    port = None
        if not app_url:
            log_callback("Port/URL not specified in config or detected. Manual URL check might be needed.")

        preview_manager.update_project_status(project_name, "running", message, process_info=process_info, app_url=app_url, port=port)
        return True, message, app_url
    else:
        error_detail = run_result['message']
        message = f"Failed to start application '{project_name}': {error_detail}"
        log_callback(message)
        # Log stdout/stderr si présents dans le résultat de l'échec
        if run_result.get('stdout'):
            log_callback(f"STDOUT from failed execution:\n{run_result.get('stdout')}")
        if run_result.get('stderr'):
            log_callback(f"STDERR from failed execution:\n{run_result.get('stderr')}")
        
        preview_manager.update_project_status(project_name, "error", message)
        return False, message, None

# For backward compatibility, you may want to keep the old function name:
prepare_and_launch_project = prepare_and_launch_project_async
Orchestrateur : détecte le type de projet et lance la préparation/lancement adapté.
"""
from .detect_project_type import detect_project_type
from .prepare_python_project import prepare_python_project
from .prepare_node_project import prepare_node_project
from .prepare_php_project import prepare_php_project
from .prepare_static_project import prepare_static_project
from .prepare_multi_project import prepare_multi_project
from .generate_start_scripts import generate_start_scripts

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
    
    # Generate or ensure start scripts exist first
    generate_start_scripts(project_dir)
    
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

