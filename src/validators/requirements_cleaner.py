import os
import logging

logger = logging.getLogger(__name__)

def create_clean_requirements_cmd(app_path: str) -> str:
    """Clean requirements.txt of JavaScript dependencies and fix package casing"""
    try:
        req_path = os.path.join(app_path, "requirements.txt")
        
        with open(req_path, 'r', encoding='utf-8', errors='replace') as f:
            requirements = []
            for line in f:
                line = line.strip()
                if (not line or line.startswith('#') or line.startswith('```') or 
                    any(js_lib in line.lower() for js_lib in ['chart.js', 'react', 'vue', 'angular', '.js', 
                                                             'webpack', 'babel', 'jquery', 'npm', 'node'])):
                    continue
                
                if line.lower() == 'flask' or line.lower().startswith('flask=') or line.lower().startswith('flask=='):
                    line = line.replace('Flask', 'flask')
                
                requirements.append(line)
        
        with open(req_path, 'w', encoding='utf-8') as f:
            for req in requirements:
                f.write(f"{req}\n")
                
        return f"pip install -r requirements.txt"
    except Exception as e:
        logger.error(f"Failed to clean requirements.txt: {str(e)}")
        return "echo 'Failed to clean requirements.txt'"
