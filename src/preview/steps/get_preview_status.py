"""
Récupère le statut actuel de la prévisualisation.
"""
import time
from src.preview.steps.get_app_url import get_app_url
from src.preview.steps.log_entry import log_entry

def get_preview_status(session_id: str, running_processes=None, process_logs=None) -> dict:
    if running_processes is None or process_logs is None:
        from src.preview.preview_manager import running_processes, process_logs
    if session_id not in running_processes:
        return {
            "running": False,
            "logs": process_logs.get(session_id, [])
        }
    process_info = running_processes[session_id]
    process = process_info["process"]
    is_running = process.poll() is None
    if not is_running:
        return_code = process.poll()
        log_entry(session_id, "INFO", f"Le processus s'est terminé avec le code: {return_code}")
        del running_processes[session_id]
        return {
            "running": False,
            "exit_code": return_code,
            "project_type": process_info["project_type"],
            "project_dir": process_info["project_dir"],
            "logs": process_logs.get(session_id, []),
            "duration": time.time() - process_info["start_time"]
        }
    return {
        "running": True,
        "project_type": process_info["project_type"],
        "project_dir": process_info["project_dir"],
        "url": get_app_url(process_info["project_type"], session_id),
        "logs": process_logs.get(session_id, []),
        "pid": process.pid,
        "duration": time.time() - process_info["start_time"]
    }