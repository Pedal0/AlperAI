import os
import sys
import subprocess
import logging
import json
import time
import webbrowser
from typing import Dict, Any, Optional, Tuple, List
from src.config import APP_FIXER_PROMPT, AGENT_TEAM_ENABLED

from .environment_setup import setup_environment
from .app_runner import try_start_application
from .dependency_detector import detect_javascript_dependencies
from .requirements_cleaner import create_clean_requirements_cmd
from .entry_point_finder import find_python_entry_point, find_js_entry_point
from .error_fixer import identify_error_file, fix_file_with_ai
from .agent_team_verifier import run_verification_team
from .functions.validate_app import validate_app as validate_app_function
from .functions.validate_static_website import _validate_static_website as validate_static_website_function
from .functions.fix_dependency_files import _fix_dependency_files as fix_dependency_files_function
from .functions.create_package_json import _create_package_json as create_package_json_function
from .functions.update_readme_with_js_dependencies import _update_readme_with_js_dependencies as update_readme_with_js_dependencies_function
from .functions.get_env_and_start_commands import _get_env_and_start_commands as get_env_and_start_commands_function
from .functions.attempt_fix_application import _attempt_fix_application as attempt_fix_application_function


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AppValidator:
    def __init__(self, api_client):
        self.api_client = api_client
        self.max_fix_attempts = 3

    def validate_app(self, app_path: str, project_context: Dict[str, Any], extended_dep_wait: bool = True):
        # Lancer l'équipe d'agents pour vérifier le projet
        if AGENT_TEAM_ENABLED:
            logger.info("Lancement de l'équipe d'agents de vérification...")
            run_verification_team(app_path, project_context)
            logger.info("Vérification par l'équipe d'agents terminée")
        
        # Continuer avec la validation standard
        return validate_app_function(self, app_path, project_context, extended_dep_wait) 
           
    def _validate_static_website(self, app_path: str) -> bool:
        return validate_static_website_function(self, app_path)

    def _fix_dependency_files(self, app_path: str, language: str, project_context: Dict[str, Any]) -> None:
        return fix_dependency_files_function(self, app_path, language, project_context)

    def _create_package_json(self, app_path: str, dependencies: List[str]) -> None:
        return create_package_json_function(self, app_path, dependencies)

    def _update_readme_with_js_dependencies(self, app_path: str, dependencies: List[str]) -> None:
        return update_readme_with_js_dependencies_function(self, app_path, dependencies)

    def _get_env_and_start_commands(self, app_path: str, language: str) -> Tuple[List[str], List[str]]:
        return get_env_and_start_commands_function(app_path, language)
    
    def _attempt_fix_application(self, app_path: str, error_info: Dict[str, Any], 
                               project_context: Dict[str, Any]) -> bool:
        return attempt_fix_application_function(self, app_path, error_info, project_context)
