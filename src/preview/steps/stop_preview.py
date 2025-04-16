"""
Arrête la prévisualisation d'une application.
"""
import time
import platform
import subprocess
from src.preview.steps.log_entry import log_entry

def stop_preview(session_id: str, running_processes=None, process_logs=None, session_ports=None, logger=None):
    if running_processes is None or process_logs is None or session_ports is None or logger is None:
        from src.preview.preview_manager import running_processes, process_logs, session_ports, logger
    if session_id not in running_processes:
        return False, "Aucun processus en cours d'exécution pour cette session"
    try:
        process_info = running_processes[session_id]
        process = process_info["process"]
        log_entry(session_id, "INFO", "Arrêt de l'application...")
        if platform.system() == "Windows":
            subprocess.call(['taskkill', '/F', '/T', '/PID', str(process.pid)])
        else:
            process.terminate()
            time.sleep(1)
            if process.poll() is None:
                process.kill()
        process.wait(timeout=5)
        log_entry(session_id, "INFO", "Application arrêtée avec succès")
        del running_processes[session_id]
        if session_id in session_ports:
            logger.info(f"Libération du port pour la session {session_id}")
            del session_ports[session_id]
        return True, "Application arrêtée avec succès"
    except Exception as e:
        if logger is None:
            from src.preview.preview_manager import logger
        logger.error(f"Erreur lors de l'arrêt de la prévisualisation: {str(e)}")
        log_entry(session_id, "ERROR", f"Erreur lors de l'arrêt: {str(e)}")
        if session_id in running_processes:
            del running_processes[session_id]
        if session_id in session_ports:
            del session_ports[session_id]
        return False, f"Erreur: {str(e)}"
