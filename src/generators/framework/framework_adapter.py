import logging
from typing import Dict, Any, List

from .flask_adapter import adjust_for_flask
from .django_adapter import adjust_for_django
from .php_adapter import adjust_for_php
from .express_adapter import adjust_for_express
from .generic_adapter import adjust_for_generic
from .static_adapter import adjust_for_static_website

logger = logging.getLogger(__name__)

def adjust_architecture_for_framework(
    architecture: Dict[str, Any],
    requirements_spec: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Adjust architecture based on the detected framework
    """
    tech_stack = requirements_spec.get('technical_stack', {})
    language = tech_stack.get('language', '').lower() if isinstance(tech_stack, dict) else ''
    framework = tech_stack.get('framework', '').lower() if isinstance(tech_stack, dict) else ''
    app_name = requirements_spec.get('app_name', 'main')
    
    # Check if this is a static website
    is_static_website = requirements_spec.get('is_static_website', False)
    
    frontend_files = []
    backend_files = []
    other_files = []
    
    for file in architecture.get('files', []):
        if not isinstance(file, dict):
            other_files.append(file)
            continue
            
        file_path = file.get('path', '')
        file_type = file.get('type', '').lower()
        file_purpose = file.get('purpose', '').lower()
        
        if (file_path.endswith(('.html', '.css', '.js')) and not file_path.endswith('.min.js') and
            not '/static/' in file_path and not '/assets/' in file_path) or \
           'frontend' in file_path.lower() or \
           any(kw in file_purpose for kw in ['frontend', 'ui', 'interface', 'html', 'template']):
            frontend_files.append(file)
        elif (framework == 'flask' and 'flask' in file_purpose) or \
             (framework == 'django' and 'django' in file_purpose) or \
             (framework == 'php' and file_path.endswith('.php')) or \
             'backend' in file_path.lower() or \
             'api' in file_path.lower() or \
             'server' in file_path.lower():
            backend_files.append(file)
        else:
            other_files.append(file)
    
    adjustment = None
    
    if is_static_website or framework == 'static':
        logger.info("Applying static website adjustments")
        adjustment = adjust_for_static_website(frontend_files, backend_files, other_files)
    elif framework == 'flask' or (language == 'python' and 
                               any('flask' in str(dep).lower() for dep in architecture.get('dependencies', []))):
        logger.info("Applying Flask-specific adjustments")
        adjustment = adjust_for_flask(frontend_files, backend_files, other_files)
    elif framework == 'django' or (language == 'python' and 
                                  any('django' in str(dep).lower() for dep in architecture.get('dependencies', []))):
        logger.info("Applying Django-specific adjustments")
        adjustment = adjust_for_django(frontend_files, backend_files, other_files, app_name)
    elif language == 'php':
        logger.info("Applying PHP-specific adjustments")
        adjustment = adjust_for_php(frontend_files, backend_files, other_files)
    elif framework in ['express', 'ejs'] or (language == 'javascript' and 
                                           any('express' in str(dep).lower() for dep in architecture.get('dependencies', []))):
        logger.info("Applying Express.js-specific adjustments")
        adjustment = adjust_for_express(frontend_files, backend_files, other_files)
    else:
        logger.info("Applying generic adjustments")
        adjustment = adjust_for_generic(frontend_files, backend_files, other_files)
    
    if adjustment:
        architecture['files'] = adjustment['files']
        
        directories = architecture.get('directories', [])
        
        if 'frontend' in directories:
            directories.remove('frontend')
        if 'backend' in directories:
            directories.remove('backend')
        
        for directory in adjustment.get('directories', []):
            if directory and directory not in directories:
                directories.append(directory)
        
        architecture['directories'] = directories
    
    return architecture
