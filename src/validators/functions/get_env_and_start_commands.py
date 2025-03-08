import os
import sys
import logging
import json
from typing import Tuple, List

from ..requirements_cleaner import create_clean_requirements_cmd
from ..entry_point_finder import find_python_entry_point, find_js_entry_point

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _get_env_and_start_commands(self, app_path: str, language: str) -> Tuple[List[str], List[str]]:
    """Get environment setup and application start commands based on language"""
    if language == "python":
        env_cmds = [
            f"{'python -m venv' if sys.platform != 'win32' else 'python -m venv'} .venv",
            f"{'source .venv/bin/activate' if sys.platform != 'win32' else '.venv\\Scripts\\activate'}"
        ]
        
        if os.path.exists(os.path.join(app_path, "requirements.txt")):
            env_cmds.append(create_clean_requirements_cmd(app_path))
        
        entry_point = find_python_entry_point(app_path)
        
        if entry_point:
            rel_path = os.path.relpath(entry_point, app_path)
            start_cmd = ["python", rel_path]
            logger.info(f"Found Python entry point: {rel_path}")
        else:
            logger.warning("No Python entry point found.")
            start_cmd = ["cmd", "/c", "echo", "No Python entry point found"]
            
    elif language in ["node", "javascript", "typescript"]:
        env_cmds = [
            "npm install"
        ]
        
        if os.path.exists(os.path.join(app_path, "package.json")):
            with open(os.path.join(app_path, "package.json")) as f:
                try:
                    pkg_json = json.load(f)
                    if "scripts" in pkg_json and "start" in pkg_json["scripts"]:
                        start_cmd = ["npm", "start"]
                        logger.info("Using 'npm start' from package.json")
                    else:
                        entry_point = find_js_entry_point(app_path)
                        if entry_point:
                            rel_path = os.path.relpath(entry_point, app_path)
                            start_cmd = ["node", rel_path]
                            logger.info(f"Found JS entry point: {rel_path}")
                        else:
                            start_cmd = ["cmd", "/c", "echo", "No JS entry point found"]
                except:
                    start_cmd = ["cmd", "/c", "echo", "Invalid package.json"]
        else:
            entry_point = find_js_entry_point(app_path)
            if entry_point:
                rel_path = os.path.relpath(entry_point, app_path)
                start_cmd = ["node", rel_path]
                logger.info(f"Found JS entry point: {rel_path}")
            else:
                start_cmd = ["cmd", "/c", "echo", "No JS entry point found"]
    elif language in ["html", "css"]:
        # For static websites
        env_cmds = []
        start_cmd = ["cmd", "/c", "echo", "Static website - open index.html in browser"]
    else:
        env_cmds = []
        start_cmd = ["cmd", "/c", "echo", f"Validation not supported for {language}"]
        
    return env_cmds, start_cmd
