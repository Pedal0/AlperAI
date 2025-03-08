import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def adjust_for_django(frontend_files: List[Dict[str, Any]], 
                     backend_files: List[Dict[str, Any]], 
                     other_files: List[Dict[str, Any]],
                     app_name: str = "main") -> Dict[str, Any]:
    """Adjust architecture for Django framework"""
    app_name = app_name.lower().replace(' ', '_')
    
    templates_dir = f"{app_name}/templates/{app_name}"
    static_dir = f"{app_name}/static/{app_name}"
    
    new_files = backend_files + other_files
    
    for file in frontend_files:
        if isinstance(file, dict):
            path = file.get('path', '')
            file_name = os.path.basename(path)
            
            if path.endswith('.html'):
                file['path'] = f"{templates_dir}/{file_name}"
                new_files.append(file)
            elif path.endswith(('.css', '.js', '.jpg', '.jpeg', '.png', '.gif')):
                file['path'] = f"{static_dir}/{file_name}"
                new_files.append(file)
            else:
                new_files.append(file)
        else:
            new_files.append(file)
    
    directories = []
    for dir_path in [templates_dir, static_dir]:
        parts = dir_path.split('/')
        current_path = ""
        for part in parts:
            current_path = current_path + part if current_path == "" else f"{current_path}/{part}"
            if current_path not in directories:
                directories.append(current_path)
    
    return {
        "files": new_files,
        "directories": directories
    }
