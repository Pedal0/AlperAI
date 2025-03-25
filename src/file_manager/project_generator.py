import os
import shutil
import zipfile
import tempfile
import json
import re
from datetime import datetime

from src.api.openrouter import (
    optimize_prompt,
    generate_project_structure,
    generate_file_content,
    generate_readme,
    clean_generated_content,
    extract_external_resources
)
from src.config.constants import DEFAULT_OUTPUT_DIR

class ProjectGenerator:
    def __init__(self, user_prompt, output_dir, update_progress=None, update_status=None):
        self.user_prompt = user_prompt
        self.output_dir = output_dir
        self.update_progress = update_progress or (lambda x: None)
        self.update_status = update_status or (lambda x: None)
        self.optimized_prompt = None
        self.project_structure = None
        self.app_name = None
        
    def extract_app_name(self):
        """Extract an app name from the prompt"""
        if not self.optimized_prompt:
            return "generated_app"
            
        # Try to extract a name from the prompt
        lines = self.optimized_prompt.split('\n')
        for line in lines:
            if ":" in line and ("app" in line.lower() or "application" in line.lower() or "project" in line.lower() or "name" in line.lower()):
                parts = line.split(":", 1)
                if len(parts) == 2 and parts[1].strip():
                    potential_name = parts[1].strip().replace(" ", "_")
                    # Take only the first 20 chars if it's too long
                    if len(potential_name) > 20:
                        potential_name = potential_name[:20]
                    return potential_name
                
        # If no name found, generate a default
        return f"app_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def create_directory_structure(self, structure_json):
        """Create the directory structure from JSON structure"""
        try:
            structure = json.loads(structure_json) if isinstance(structure_json, str) else structure_json
            
            # Create directories first
            for directory in structure.get("directories", []):
                dir_path = os.path.join(self.output_dir, directory["path"])
                os.makedirs(dir_path, exist_ok=True)
                self.update_status(f"Created directory: {directory['path']}")
            
            # Create empty files
            for file in structure.get("files", []):
                file_path = os.path.join(self.output_dir, file["path"])
                # Ensure the parent directory exists
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                # Create empty file
                with open(file_path, 'w', encoding='utf-8') as f:
                    pass
                
            return True
        except Exception as e:
            self.update_status(f"Error creating directory structure: {str(e)}")
            return False
                
    def populate_files(self, structure_json):
        """Populate files with generated content from JSON structure"""
        try:
            structure = json.loads(structure_json) if isinstance(structure_json, str) else structure_json
            
            # Get the total file count for progress calculation
            files = structure.get("files", [])
            total_files = len(files)
            
            # First process non-HTML files to ensure CSS and JS files are generated first
            html_files = []
            non_html_files = []
            
            for file in files:
                if file["path"].lower().endswith(".html"):
                    html_files.append(file)
                else:
                    non_html_files.append(file)
            
            # Process non-HTML files first
            for i, file in enumerate(non_html_files):
                file_path = file["path"]
                full_path = os.path.join(self.output_dir, file_path)
                
                # Update status with current file
                self.update_status(f"Generating content for {file_path}")
                
                # Generate content for the file
                file_content = generate_file_content(
                    file_path, 
                    self.optimized_prompt, 
                    self.project_structure
                )
                
                # Ensure the content doesn't have backticks or code block markers
                file_content = clean_generated_content(file_content)
                
                # Write the content to the file
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(file_content)
                
                # Update progress proportionally 
                progress = (i + 1) / total_files
                self.update_progress(progress * 0.3 + 0.3)  # Scale to 30%-60% of overall progress
            
            # Then process HTML files, which may reference the CSS and JS files
            for i, file in enumerate(html_files):
                file_path = file["path"]
                full_path = os.path.join(self.output_dir, file_path)
                
                # Update status with current file
                self.update_status(f"Generating content for {file_path}")
                
                # Generate content for the file
                file_content = generate_file_content(
                    file_path, 
                    self.optimized_prompt, 
                    self.project_structure
                )
                
                # Ensure the content doesn't have backticks or code block markers
                file_content = clean_generated_content(file_content)
                
                # Verify that HTML content doesn't contain inline styles or scripts when external files exist
                external_resources = extract_external_resources(self.project_structure)
                
                # Remove any remaining style tags if we have external CSS
                if external_resources['css'] and '<style' in file_content.lower():
                    self.update_status(f"Removing inline styles from {file_path}")
                    file_content = re.sub(r'<style[^>]*>.*?</style>', '', file_content, flags=re.DOTALL | re.IGNORECASE)
                
                # Remove any remaining script tags with content if we have external JS
                if external_resources['js']:
                    self.update_status(f"Removing inline scripts from {file_path}")
                    # Keep script tags that have src attribute (external scripts)
                    file_content = re.sub(r'<script(?![^>]*src)[^>]*>.*?</script>', '', file_content, flags=re.DOTALL | re.IGNORECASE)
                
                # Write the content to the file
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(file_content)
                
                # Update progress for HTML files
                progress = (i + 1) / len(html_files) if len(html_files) > 0 else 1
                self.update_progress(progress * 0.3 + 0.6)  # Scale to 60%-90% of overall progress
                
            return True
        except Exception as e:
            self.update_status(f"Error populating files: {str(e)}")
            return False
    
    def create_zip_file(self):
        """Create a zip file of the generated project"""
        zip_path = f"{self.output_dir}.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.output_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, os.path.dirname(self.output_dir))
                    zipf.write(file_path, rel_path)
                    
        return zip_path
    
    def generate_default_index_html(self):
        """Generate a default index.html file if it's missing"""
        default_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generated Website</title>
    <!-- Link to CSS files -->
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <header>
        <h1>Welcome to Your Generated Website</h1>
        <nav>
            <ul>
                <li><a href="index.html">Home</a></li>
                <li><a href="about.html">About</a></li>
                <li><a href="contact.html">Contact</a></li>
            </ul>
        </nav>
    </header>
    
    <main>
        <section>
            <h2>Main Content Section</h2>
            <p>This is a default index.html page created by the AI Application Generator.</p>
        </section>
    </main>
    
    <footer>
        <p>&copy; 2024 - Generated Website</p>
    </footer>
    
    <!-- Link to JS files -->
    <script src="js/main.js"></script>
</body>
</html>"""

        with open(os.path.join(self.output_dir, "index.html"), 'w', encoding='utf-8') as f:
            f.write(default_html)
    
    def generate(self):
        """Generate the project based on the user prompt"""
        try:
            # Phase 1: Optimize the prompt
            self.update_status("Optimizing prompt...")
            self.update_progress(0.1)
            self.optimized_prompt = optimize_prompt(self.user_prompt)
            
            # Extract app name
            self.app_name = self.extract_app_name()
            
            # Phase 2: Generate project structure as JSON
            self.update_status("Designing project structure...")
            self.update_progress(0.2)
            self.project_structure = generate_project_structure(self.optimized_prompt)
            
            # Phase 3: Create directory structure
            self.update_status("Creating directory structure...")
            self.update_progress(0.3)
            os.makedirs(self.output_dir, exist_ok=True)
            if not self.create_directory_structure(self.project_structure):
                return {
                    'error': True,
                    'message': 'Failed to create directory structure',
                    'output_dir': self.output_dir,
                    'app_name': self.app_name or 'generated_application',
                    'optimized_prompt': self.optimized_prompt
                }
            
            # Phase 4: Populate files
            self.update_status("Generating code for files...")
            self.update_progress(0.4)
            if not self.populate_files(self.project_structure):
                return {
                    'error': True,
                    'message': 'Failed to populate files',
                    'output_dir': self.output_dir,
                    'app_name': self.app_name or 'generated_application',
                    'optimized_prompt': self.optimized_prompt
                }
            
            # Check for essential files for static websites
            if 'static website' in self.user_prompt.lower() and not os.path.exists(os.path.join(self.output_dir, 'index.html')):
                self.update_status("Creating missing index.html...")
                self.generate_default_index_html()
            
            # Phase 5: Generate README
            self.update_status("Creating documentation...")
            self.update_progress(0.9)
            readme_content = generate_readme(self.app_name, self.optimized_prompt, self.project_structure)
            with open(os.path.join(self.output_dir, "README.md"), 'w', encoding='utf-8') as f:
                f.write(readme_content)
            
            # Phase 6: Create zip file
            self.update_status("Creating ZIP archive...")
            self.update_progress(0.95)
            zip_path = self.create_zip_file()
            
            # Complete
            self.update_status("Project generation complete!")
            self.update_progress(1.0)
            
            return {
                'output_dir': self.output_dir,
                'zip_path': zip_path,
                'app_name': self.app_name,
                'optimized_prompt': self.optimized_prompt
            }
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
            return {
                'error': True,
                'message': str(e),
                'output_dir': getattr(self, 'output_dir', DEFAULT_OUTPUT_DIR),
                'app_name': getattr(self, 'app_name', 'generated_application'),
                'optimized_prompt': getattr(self, 'optimized_prompt', self.user_prompt)
            }