import logging  # Import logging
import socket

"""
Retourne l'URL d'accès à l'application selon le type de projet et le port utilisé.
Ne doit JAMAIS retourner le port 5000 (utilisé par l'app principale).
"""
def get_app_url(project_type: str, session_id: str = None):
    logging.info(f"get_app_url called with project_type='{project_type}', session_id='{session_id}'")

    # Port par défaut si non trouvé dans la session
    default_port = 8000  # assume generated apps run on port 8000
    port = default_port
    found = False

    if session_id:
        try:
            from src.preview.preview_manager import session_ports, running_processes
            if session_id in session_ports:
                port = session_ports[session_id]
                found = True
            elif session_id in running_processes:
                # Try to extract port from the command args
                cmd_args = running_processes[session_id].get('command', [])
                if cmd_args and isinstance(cmd_args[-1], (str,)) and cmd_args[-1].isdigit():
                    port = int(cmd_args[-1])
                    found = True
        except Exception as e:
            logging.error(f"Error accessing session data: {e}. Defaulting to port {default_port}.")
            port = default_port
    
    # Si aucun port trouvé, essayer les ports classiques (hors 5000)
    if not found:
        common_ports = [3000, 8000, 8080, 5173, 8501, 4200, 1234]
        for p in common_ports:
            if p == 5000:
                continue
            try:
                with socket.create_connection(("localhost", p), timeout=0.5):
                    port = p
                    found = True
                    logging.info(f"Port auto-detecté par scan: {port}")
                    break
            except Exception:
                continue
    # Si toujours rien, fallback
    if not found:
        logging.warning(f"Aucun port détecté, fallback sur {default_port}")
        port = default_port

    # Construire l'URL avec le port déterminé (jamais 5000)
    url = f"http://localhost:{port}"
    logging.info(f"Returning URL for project type '{project_type}': {url}")
    return url