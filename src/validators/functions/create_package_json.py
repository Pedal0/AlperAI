import os
import json
from typing import List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _create_package_json(self, app_path: str, dependencies: List[str]) -> None:
    """Create a package.json file with the detected dependencies"""
    logger.info(f"Creating package.json with dependencies: {dependencies}")
    
    package = {
        "name": os.path.basename(app_path),
        "version": "1.0.0",
        "description": "Generated application",
        "scripts": {
            "start": "node index.js"
        },
        "dependencies": {}
    }
    
    for dep in dependencies:
        package["dependencies"][dep] = "latest"
    
    if "chart.js" in dependencies:
        package["dependencies"]["chart.js"] = "^4.0.0"
    
    if "react" in dependencies:
        package["dependencies"]["react-scripts"] = "5.0.1"
        package["scripts"]["start"] = "react-scripts start"
    
    if "vue" in dependencies:
        package["dependencies"]["vue-cli-service"] = "^5.0.0"
        package["scripts"]["start"] = "vue-cli-service serve"
    
    package_path = os.path.join(app_path, "package.json")
    with open(package_path, 'w', encoding='utf-8') as f:
        json.dump(package, f, indent=2)
    
    self._update_readme_with_js_dependencies(app_path, dependencies)

