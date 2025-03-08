import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def find_python_entry_point(app_path: str) -> Optional[str]:
    """Find the main Python entry point for the application"""
    priority_files = [
        "app.py", "main.py", "server.py", "run.py", "manage.py",
        "wsgi.py", "asgi.py", "index.py", "application.py"
    ]
    
    for filename in priority_files:
        path = os.path.join(app_path, filename)
        if os.path.exists(path):
            return path
    
    backend_dirs = ["backend", "server", "api", "src"]
    for dirname in backend_dirs:
        subdir = os.path.join(app_path, dirname)
        if os.path.isdir(subdir):
            for filename in priority_files:
                path = os.path.join(subdir, filename)
                if os.path.exists(path):
                    return path
    
    for root, dirs, files in os.walk(app_path):
        dirs[:] = [d for d in dirs if d not in ["node_modules", ".venv", "venv", ".git", "__pycache__"]]
        
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read().lower()
                        if ("if __name__ == '__main__'" in content or 
                            "app.run(" in content or
                            "runserver" in content):
                            return path
                except:
                    pass
    
    return None

def find_js_entry_point(app_path: str) -> Optional[str]:
    """Find the main JavaScript entry point for the application"""
    priority_files = [
        "index.js", "server.js", "app.js", "main.js", "start.js"
    ]
    
    for filename in priority_files:
        path = os.path.join(app_path, filename)
        if os.path.exists(path):
            return path
            
    js_dirs = ["src", "server", "backend", "api"]
    for dirname in js_dirs:
        subdir = os.path.join(app_path, dirname)
        if os.path.isdir(subdir):
            for filename in priority_files:
                path = os.path.join(subdir, filename)
                if os.path.exists(path):
                    return path
    
    return None
