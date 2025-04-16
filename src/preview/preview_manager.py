"""
Module de gestion de la prévisualisation d'applications générées.
Contient les variables globales et importe les fonctions de steps/.
"""
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Variables globales pour stocker les processus en cours d'exécution
running_processes = {}
process_logs = {}
# Dictionnaire pour stocker les ports utilisés par session
session_ports = {}

from src.preview.steps.find_free_port import find_free_port
from src.preview.steps.detect_project_type import detect_project_type, ProjectType
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