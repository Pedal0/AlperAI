import os
import logging
from typing import List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _update_readme_with_js_dependencies(self, app_path: str, dependencies: List[str]) -> None:
    """Update README.md with JavaScript dependencies installation instructions"""
    readme_path = os.path.join(app_path, "README.md")
    
    if not os.path.exists(readme_path):
        return
    
    try:
        with open(readme_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
        if "npm install" in content:
            return
        
        js_section = "\n## JavaScript Dependencies\n\n"
        js_section += "This application uses JavaScript libraries that need to be installed separately:\n\n"
        js_section += "```bash\n"
        js_section += "# Install JavaScript dependencies\n"
        js_section += "npm install\n"
        js_section += "```\n\n"
        
        if "chart.js" in dependencies:
            js_section += "This will install Chart.js for data visualization.\n\n"
        
        if "## Usage" in content:
            content = content.replace("## Usage", js_section + "## Usage")
        elif "## Installation" in content:
            content = content.replace("## Installation", "## Installation" + js_section)
        else:
            content += js_section
        
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    except Exception as e:
        logger.error(f"Failed to update README with JS dependencies: {str(e)}")
