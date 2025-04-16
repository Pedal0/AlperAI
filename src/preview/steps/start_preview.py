"""
Démarre la prévisualisation de l'application générée.
"""
import time
import subprocess
import threading
from src.preview.steps.detect_project_type import detect_project_type
from src.preview.steps.prepare_environment import prepare_environment
from src.preview.steps.get_start_command import get_start_command
from src.preview.steps.get_app_url import get_app_url
from src.preview.steps.log_entry import log_entry

def start_preview(project_dir: str, session_id: str, running_processes=None, process_logs=None, session_ports=None):
    if running_processes is None or process_logs is None or session_ports is None:
        from src.preview.preview_manager import running_processes, process_logs, session_ports
    if session_id in running_processes:
        from src.preview.preview_manager import stop_preview
        stop_preview(session_id)
    try:
        process_logs[session_id] = []
        log_entry(session_id, "INFO", f"Démarrage de la prévisualisation pour le projet: {project_dir}")
        project_type = detect_project_type(project_dir)
        log_entry(session_id, "INFO", f"Type de projet détecté: {project_type}")
        success, message = prepare_environment(project_dir, project_type)
        log_entry(session_id, "INFO" if success else "ERROR", message)
        if not success:
            return False, message, {"project_type": project_type}
        command, env = get_start_command(project_dir, project_type, session_id)
        log_entry(session_id, "INFO", f"Commande de démarrage: {' '.join(command)}")
        process = subprocess.Popen(
            command,
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            bufsize=1,
            universal_newlines=True
        )
        running_processes[session_id] = {
            "process": process,
            "project_dir": project_dir,
            "project_type": project_type,
            "command": command,
            "start_time": time.time()
        }
        def read_output(stream, log_type):
            for line in stream:
                log_entry(session_id, log_type, line.strip())
            if log_type == "ERROR" and not stream.closed:
                stream.close()
        stdout_thread = threading.Thread(target=read_output, args=(process.stdout, "INFO"))
        stderr_thread = threading.Thread(target=read_output, args=(process.stderr, "ERROR"))
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        stdout_thread.start()
        stderr_thread.start()
        time.sleep(2)
        if process.poll() is not None:
            return_code = process.poll()
            log_entry(session_id, "ERROR", f"Le processus s'est terminé avec le code: {return_code}")
            remaining_stderr = process.stderr.read()
            if remaining_stderr:
                log_entry(session_id, "ERROR", remaining_stderr)
            del running_processes[session_id]
            return False, f"Échec du démarrage du processus (code {return_code})", {
                "project_type": project_type,
                "logs": process_logs.get(session_id, [])
            }
        app_url = get_app_url(project_type, session_id)
        return True, "Application démarrée avec succès", {
            "project_type": project_type,
            "url": app_url,
            "logs": process_logs.get(session_id, []),
            "pid": process.pid
        }
    except Exception as e:
        from src.preview.preview_manager import logger
        logger.error(f"Erreur lors du démarrage de la prévisualisation: {str(e)}")
        log_entry(session_id, "ERROR", f"Erreur: {str(e)}")
        return False, f"Erreur: {str(e)}", {
            "logs": process_logs.get(session_id, [])
        }
