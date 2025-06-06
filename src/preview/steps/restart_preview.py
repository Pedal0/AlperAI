"""
Redémarre la prévisualisation d'une application.
"""
def restart_preview(session_id: str, running_processes=None):
    if running_processes is None:
        from src.preview.preview_manager import running_processes
    if session_id not in running_processes:
        return False, "Aucun processus en cours d'exécution pour cette session", {}
    project_dir = running_processes[session_id]["project_dir"]
    from src.preview.steps.stop_preview import stop_preview
    from src.preview.steps.start_preview import start_preview
    success, message = stop_preview(session_id)
    if not success:
        return False, message, {}
    return start_preview(project_dir, session_id)