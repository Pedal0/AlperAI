"""
Nettoie tous les processus en cours d'exécution (à appeler à l'arrêt de l'application).
"""
def cleanup_all_processes(running_processes=None, session_ports=None, logger=None):
    if running_processes is None or session_ports is None:
        from src.preview.preview_manager import running_processes, session_ports, logger
    for session_id in list(running_processes.keys()):
        try:
            from src.preview.preview_manager import stop_preview
            stop_preview(session_id)
        except:
            pass
    if session_ports:
        logger.info(f"Nettoyage final de {len(session_ports)} ports restants")
        session_ports.clear()
