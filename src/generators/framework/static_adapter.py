import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def adjust_for_static_website(frontend_files: List[Dict[str, Any]], 
                             backend_files: List[Dict[str, Any]], 
                             other_files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Adjust architecture for a static website with no backend"""
    new_files = other_files.copy()
    
    # Make sure we have essential files for a static website
    has_index = any(file.get('path', '').endswith('index.html') for file in frontend_files if isinstance(file, dict))
    
    # Convert all backend files to frontend files or remove server-side code
    for file in backend_files:
        if isinstance(file, dict):
            path = file.get('path', '')
            # Skip server-side files entirely
            if any(ext in path for ext in ['.py', '.php', '.rb', '.java']):
                continue
                
            # Move any remaining useful files to the root
            if path.startswith('backend/'):
                file['path'] = path.replace('backend/', '', 1)
                
            if not any(path.endswith(ext) for ext in ['.py', '.php', '.rb', '.java']):
                new_files.append(file)
    
    # Move all frontend files to the root level
    for file in frontend_files:
        if isinstance(file, dict):
            path = file.get('path', '')
            
            # Special handling for index.html - always move to root regardless of location
            if path.endswith('index.html'):
                file['path'] = 'index.html'
                new_files.append(file)
                continue
                
            # Remove any server-side directory paths
            if path.startswith(('frontend/', 'templates/', 'views/', 'src/')):
                file['path'] = path.split('/', 1)[1]
            
            # Ensure HTML files at root level
            if path.startswith('static/') and path.endswith('.html'):
                file['path'] = os.path.basename(path)
            
            # Additional check for any HTML files in directories
            elif path.endswith('.html') and '/' in path:
                file['path'] = os.path.basename(path)
                
            new_files.append(file)
        else:
            new_files.append(file)
    
    # Make sure we have an index.html file
    if not has_index:
        new_files.append({
            'path': 'index.html',
            'type': 'html',
            'purpose': 'Main entry page for the static website'
        })
    
    # Usually static sites have these directories
    return {
        "files": new_files,
        "directories": ['css', 'js', 'images', 'assets']
    }
