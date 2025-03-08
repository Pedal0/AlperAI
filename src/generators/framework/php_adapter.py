import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def adjust_for_php(frontend_files: List[Dict[str, Any]], 
                  backend_files: List[Dict[str, Any]], 
                  other_files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Adjust architecture for PHP framework"""
    html_to_php_map = {}
    
    for html_file in frontend_files:
        if isinstance(html_file, dict) and html_file.get('path', '').endswith('.html'):
            html_path = html_file.get('path', '')
            html_name = os.path.splitext(os.path.basename(html_path))[0]
            
            for php_file in backend_files:
                if isinstance(php_file, dict):
                    php_path = php_file.get('path', '')
                    php_name = os.path.splitext(os.path.basename(php_path))[0]
                    
                    if php_name == html_name or php_path.endswith(f"{html_name}.php"):
                        html_to_php_map[html_path] = php_path
                        break
    
    new_files = other_files
    
    for file in backend_files:
        new_files.append(file)
    
    for file in frontend_files:
        if isinstance(file, dict):
            path = file.get('path', '')
            
            if path in html_to_php_map:
                continue
                
            if path.endswith('.html'):
                new_path = path.replace('.html', '.php')
                file['path'] = new_path
                file['type'] = 'php'
                new_files.append(file)
            else:
                new_files.append(file)
        else:
            new_files.append(file)
    
    return {
        "files": new_files,
        "directories": []  
    }
