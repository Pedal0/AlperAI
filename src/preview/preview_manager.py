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
Module de gestion de la prévisualisation d'applications générées.
Contient les variables globales et importe les fonctions de steps/.
"""
import logging
import datetime # Added import
import subprocess # Added import

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Variables globales pour stocker les processus en cours d'exécution
running_processes = {}
process_logs = {}
# Dictionnaire pour stocker les ports utilisés par session
session_ports = {}

from src.preview.steps.find_free_port import find_free_port
from src.preview.handler.detect_project_type import detect_project_type
from src.preview.steps.detect_project_type import ProjectType
from src.preview.steps.prepare_environment import prepare_environment
from src.preview.steps.get_start_command import get_start_command
from src.preview.steps.log_entry import log_entry
from src.preview.steps.get_app_url import get_app_url
from src.preview.steps.cleanup_all_processes import cleanup_all_processes
from src.preview.steps.cleanup_unused_ports import cleanup_unused_ports
from src.preview.steps.start_preview import start_preview
from src.preview.steps.stop_preview import stop_preview
from src.preview.steps.get_preview_status import get_preview_status
from src.preview.steps.restart_preview import restart_preview
from src.preview.steps.improve_readme import improve_readme_for_preview

# New PreviewManager class and getter function
class PreviewManager:
    def __init__(self):
        self.projects_status = {}  # Stores status, logs, process info, etc. per project_name
        self.running_processes = {}  # project_name: process_object
        # Note: self.session_ports is distinct from the global session_ports for now
        self.managed_session_ports = {} 

    def update_project_status(self, project_name: str, status: str, message: str = None, process_info=None, app_url: str = None, port: int = None):
        if project_name not in self.projects_status:
            self.projects_status[project_name] = {"logs": []}
        
        self.projects_status[project_name]["status"] = status
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry_msg = f"[{current_time}] Status: {status}"

        if message:
            self.projects_status[project_name]["message"] = message
            log_entry_msg += f" - {message}"
        
        self.add_log_entry_project_specific(project_name, log_entry_msg, add_status_prefix=False)

        if process_info:
            self.running_processes[project_name] = process_info
            self.projects_status[project_name]["process_pid"] = process_info.pid
        if app_url:
            self.projects_status[project_name]["app_url"] = app_url
        if port:
            self.projects_status[project_name]["port"] = port
            self.managed_session_ports[project_name] = port # Using project_name as key

        logger.info(f"Project '{project_name}' status updated to '{status}'. URL: {app_url}, Port: {port}")

    def add_log_entry_project_specific(self, project_name: str, log_message: str, add_status_prefix=True):
        if project_name not in self.projects_status:
            self.projects_status[project_name] = {"logs": []}
        elif "logs" not in self.projects_status[project_name]:
             self.projects_status[project_name]["logs"] = []
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if add_status_prefix: # Avoid double "Status:" if already included
            full_log_message = f"[{timestamp}] {log_message}"
        else:
            full_log_message = log_message # Message already formatted

        self.projects_status[project_name]["logs"].append(full_log_message)
        # Optionally, limit log size
        # MAX_LOGS = 200
        # self.projects_status[project_name]["logs"] = self.projects_status[project_name]["logs"][-MAX_LOGS:]

    def get_project_status_info(self, project_name: str): # Renamed to avoid conflict if a step is named get_project_status
        # This method provides data for the new manager.
        # The existing get_preview_status (from steps) is still used by routes.py for now.
        return self.projects_status.get(project_name, {
            "status": "unknown", 
            "message": "Project not found or not initialized in new manager.",
            "logs": []
        })

    def stop_managed_project(self, project_name: str): # Renamed to avoid conflict
        process = self.running_processes.pop(project_name, None)
        log_msg = ""
        stopped_successfully = False
        if process:
            try:
                process.terminate()
                process.wait(timeout=5) # Wait for graceful termination
                log_msg = f"Managed process for project '{project_name}' (PID: {process.pid}) terminated."
                stopped_successfully = True
            except subprocess.TimeoutExpired:
                process.kill()
                log_msg = f"Managed process for project '{project_name}' (PID: {process.pid}) forcefully killed."
                stopped_successfully = True
            except Exception as e:
                log_msg = f"Error stopping managed process for project '{project_name}': {e}"
            
            self.update_project_status(project_name, "stopped", log_msg)
            logger.info(log_msg)
            if project_name in self.managed_session_ports:
                del self.managed_session_ports[project_name]
            return stopped_successfully, log_msg
        return False, f"No running managed process found for project '{project_name}'."

_preview_manager_instance = None

def get_preview_manager():
    global _preview_manager_instance
    if _preview_manager_instance is None:
        _preview_manager_instance = PreviewManager()
    return _preview_manager_instance

# Existing global variables and re-exported functions from 'steps/' remain for now.
# Future refactoring could integrate them with the PreviewManager instance.