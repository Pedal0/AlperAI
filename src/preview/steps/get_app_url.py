import logging  # Import logging

"""
Retourne l'URL d'accès à l'application selon le type de projet et le port utilisé.
Ne doit JAMAIS retourner le port 5000 (utilisé par l'app principale).
"""
def get_app_url(project_type: str, session_id: str = None):
    logging.info(f"get_app_url called with project_type='{project_type}', session_id='{session_id}'")

    # Port par défaut si non trouvé dans la session
    default_port = 3000
    port = default_port

    if session_id:
        try:
            from src.preview.preview_manager import session_ports
            if session_id in session_ports:
                port = session_ports[session_id]
                logging.info(f"Found port {port} in session_ports for session {session_id}")
            else:
                logging.warning(f"session_id '{session_id}' not found in session_ports. Defaulting to port {default_port}.")
                port = default_port # Assurer que port est bien default_port
        except Exception as e:
            logging.error(f"Error accessing session_ports: {e}. Defaulting to port {default_port}.")
            port = default_port # Assurer que port est bien default_port
    else:
        logging.warning(f"No session_id provided. Defaulting to port {default_port}.")
        port = default_port # Assurer que port est bien default_port

    # Construire l'URL avec le port déterminé (jamais 5000)
    url = f"http://localhost:{port}"
    logging.info(f"Returning URL for project type '{project_type}': {url}")
    return url
