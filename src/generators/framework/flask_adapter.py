import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def adjust_for_flask(frontend_files: List[Dict[str, Any]], 
                    backend_files: List[Dict[str, Any]], 
                    other_files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Adjust architecture for Flask framework"""
    templates_dir = "templates"
    static_dir = "static"
    
    templates_exists = False
    static_exists = False
    
    for file in backend_files:
        if isinstance(file, dict) and file.get('path', '').startswith(templates_dir + '/'):
            templates_exists = True
        if isinstance(file, dict) and file.get('path', '').startswith(static_dir + '/'):
            static_exists = True
    
    new_files = other_files
    
    for file in frontend_files:
        if isinstance(file, dict):
            path = file.get('path', '')
            file_name = os.path.basename(path)
            
            if path.startswith('frontend/'):
                path = path.replace('frontend/', '', 1)
                file_name = os.path.basename(path)
            
            if path.endswith('.html'):
                file['path'] = f"{templates_dir}/{file_name}"
                new_files.append(file)
            elif path.endswith(('.css', '.js')):
                file['path'] = f"{static_dir}/{file_name}"
                new_files.append(file)
            else:
                new_files.append(file)
        else:
            new_files.append(file)
    
    for file in backend_files:
        if isinstance(file, dict):
            path = file.get('path', '')
            
            if path.startswith('backend/'):
                parts = path.split('/')
                if len(parts) > 1:
                    new_path = '/'.join(parts[1:])
                    file['path'] = new_path
            
            new_files.append(file)
        else:
            new_files.append(file)
    
    directories = []
    
    if not templates_exists:
        directories.append(templates_dir)
    if not static_exists:
        directories.append(static_dir)
    
    return {
        "files": new_files,
        "directories": directories
    }
