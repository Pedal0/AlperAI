"""
Libère les ports non utilisés (nettoyage des ports orphelins).
"""
def cleanup_unused_ports(session_ports=None, running_processes=None, logger=None):
    if session_ports is None or running_processes is None:
        from src.preview.preview_manager import session_ports, running_processes, logger
    to_remove = []
    for session_id, port in session_ports.items():
        if session_id not in running_processes:
            to_remove.append(session_id)
    for session_id in to_remove:
        logger.info(f"Libération du port orphelin pour la session {session_id}")
        del session_ports[session_id]
    return len(to_remove)
