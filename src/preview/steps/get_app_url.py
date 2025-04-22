import logging  # Import logging

"""
Retourne l'URL d'accès à l'application selon le type de projet et le port utilisé.
Ne doit JAMAIS retourner le port 5000 (utilisé par l'app principale).
"""
def get_app_url(project_type: str, session_id: str = None):
    logging.info(f"get_app_url called with project_type='{project_type}', session_id='{session_id}'")

    # Port par défaut si non trouvé dans la session
    default_port = 8000  # assume generated apps run on port 8000
    port = default_port

    if session_id:
        try:
            from src.preview.preview_manager import session_ports, running_processes
            if session_id in session_ports:
                port = session_ports[session_id]
            elif session_id in running_processes:
                # Try to extract port from the command args
                cmd_args = running_processes[session_id].get('command', [])
                if cmd_args and isinstance(cmd_args[-1], (str,)) and cmd_args[-1].isdigit():
                    port = int(cmd_args[-1])
                else:
                    port = default_port
            else:
                logging.warning(f"session_id '{session_id}' not found in session_ports or running_processes. Defaulting to port {default_port}.")
                port = default_port
        except Exception as e:
            logging.error(f"Error accessing session data: {e}. Defaulting to port {default_port}.")
            port = default_port
    else:
        logging.warning(f"No session_id provided. Defaulting to port {default_port}.")
        port = default_port

    # Construire l'URL avec le port déterminé (jamais 5000)
    url = f"http://localhost:{port}"
    logging.info(f"Returning URL for project type '{project_type}': {url}")
    return url
