"""
Retourne l'URL d'accès à l'application selon le type de projet et le port utilisé.
"""
def get_app_url(project_type: str, session_id: str = None):
    if project_type in ["static", "react", "express", "vue", "angular"]:
        if session_id:
            from src.preview.preview_manager import session_ports
            if session_id in session_ports:
                port = session_ports[session_id]
                return f"http://localhost:{port}"
        return "http://localhost:3000"
    else:
        return "http://localhost:5000"
