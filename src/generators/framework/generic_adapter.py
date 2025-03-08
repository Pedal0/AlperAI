import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def adjust_for_generic(frontend_files: List[Dict[str, Any]], 
                      backend_files: List[Dict[str, Any]], 
                      other_files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Adjust architecture for generic framework - flatten structure"""
    new_files = other_files
    
    for file in frontend_files:
        if isinstance(file, dict):
            path = file.get('path', '')
            
            if path.startswith('frontend/'):
                file['path'] = path.replace('frontend/', '', 1)
            
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
        "directories": []
    }
