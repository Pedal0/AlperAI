import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def adjust_for_express(frontend_files: List[Dict[str, Any]], 
                      backend_files: List[Dict[str, Any]], 
                      other_files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Adjust architecture for Express.js framework with views"""
    views_dir = "views"
    public_dir = "public"
    
    new_files = other_files
    
    for file in frontend_files:
        if isinstance(file, dict):
            path = file.get('path', '')
            file_name = os.path.basename(path)
            
            if path.endswith(('.html', '.ejs', '.pug', '.hbs', '.jade')):
                file['path'] = f"{views_dir}/{file_name}"
                new_files.append(file)
            elif path.endswith(('.css', '.js', '.jpg', '.png', '.gif', '.svg')):
                file['path'] = f"{public_dir}/{file_name}"
                new_files.append(file)
            else:
                new_files.append(file)
        else:
            new_files.append(file)
    
    for file in backend_files:
        if isinstance(file, dict):
            path = file.get('path', '')
            
            if path.startswith('backend/'):
                file['path'] = path.replace('backend/', '', 1)
            
            new_files.append(file)
        else:
            new_files.append(file)
    
    return {
        "files": new_files,
        "directories": [views_dir, public_dir]
    }
