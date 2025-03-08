import os
import time
import logging
from typing import Dict, Any
from src.config import APP_FIXER_PROMPT

from ..environment_setup import setup_environment
from ..app_runner import try_start_application
from ..dependency_detector import detect_javascript_dependencies

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_app(self, app_path: str, project_context: Dict[str, Any], extended_dep_wait: bool = True) -> bool:
    language = project_context.get("architecture", {}).get("language", "python").lower()
    
    is_static_website = project_context.get("requirements", {}).get("is_static_website", False)
    
    logger.info(f"Validating {'static website' if is_static_website else language + ' application'} at {app_path}")
    
    if is_static_website:
        return self._validate_static_website(app_path)
    
    js_dependencies = detect_javascript_dependencies(app_path, project_context)
    if js_dependencies and not os.path.exists(os.path.join(app_path, "package.json")):
        self._create_package_json(app_path, js_dependencies)
    
    env_setup_cmds, start_cmd = self._get_env_and_start_commands(app_path, language)
    
    if not setup_environment(app_path, env_setup_cmds):
        logger.error("Failed to setup environment")
        self._fix_dependency_files(app_path, language, project_context)
        if not setup_environment(app_path, env_setup_cmds):
            return False
    
    if extended_dep_wait:
        logger.info("Adding extra delay after dependency installation to ensure completion")
        time.sleep(10)
        
    success, error_info = try_start_application(app_path, start_cmd)
    
    if success:
        logger.info("Application started successfully")
        return True
        
    return self._attempt_fix_application(app_path, error_info, project_context)
