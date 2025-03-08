import os
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def detect_javascript_dependencies(app_path: str, project_context: Dict[str, Any]) -> List[str]:
    """Detect JavaScript dependencies from project content"""
    js_dependencies = []
    
    req_path = os.path.join(app_path, "requirements.txt")
    if os.path.exists(req_path):
        with open(req_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read().lower()
            if 'chart.js' in content or 'chartjs' in content:
                js_dependencies.append("chart.js")
            if 'react' in content:
                js_dependencies.append("react")
                js_dependencies.append("react-dom")
            if 'vue' in content:
                js_dependencies.append("vue")
            if 'angular' in content:
                js_dependencies.append("@angular/core")
    
    for root, dirs, files in os.walk(app_path):
        for file in files:
            if file.endswith(('.js', '.html', '.py')):
                try:
                    with open(os.path.join(root, file), 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read().lower()
                        if 'chart.js' in content or 'chartjs' in content:
                            js_dependencies.append("chart.js")
                        if 'import react' in content or 'from react' in content:
                            js_dependencies.append("react")
                            js_dependencies.append("react-dom")
                        if 'import vue' in content or 'from vue' in content:
                            js_dependencies.append("vue")
                        if 'import { component }' in content and 'angular' in content:
                            js_dependencies.append("@angular/core")
                except:
                    pass
    
    return list(set(js_dependencies))
