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
    extract_external_resources,
    generate_element_dictionary
)
from src.config.constants import DEFAULT_OUTPUT_DIR
from src.validators.code_validator import CodeValidator
from src.generators.svg_generator import SVGIconGenerator

class ProjectGenerator:
    def __init__(self, user_prompt, output_dir, update_progress=None, update_status=None):
        self.user_prompt = user_prompt
        self.output_dir = output_dir
        self.update_progress = update_progress or (lambda x: None)
        self.update_status = update_status or (lambda x: None)
        self.optimized_prompt = None
        self.project_structure = None
        self.element_dictionary = None
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
                    self.project_structure,
                    self.element_dictionary
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
                    self.project_structure,
                    self.element_dictionary
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
    
    def enhance_code_quality(self):
        """
        Validate and enhance the code quality of generated files
        
        Returns:
            bool: True if validation process completed, False otherwise
        """
        try:
            self.update_status("Validating and enhancing code quality...")
            
            # Initialize the code validator
            validator = CodeValidator(
                self.output_dir,
                self.project_structure,
                self.element_dictionary
            )
            
            # Validate frontend files (HTML, CSS, JS) first
            self.update_status("Enhancing frontend files...")
            frontend_results = validator.validate_frontend_files(apply_improvements=True)
            self.update_status(f"Enhanced {frontend_results['improved_files']} frontend files")
            
            # Update progress
            self.update_progress(0.95)
            
            # Write a summary of improvements
            improvements_summary = {
                "validated_files": frontend_results["validated_files"],
                "improved_files": frontend_results["improved_files"],
                "timestamp": datetime.now().isoformat()
            }
            
            with open(os.path.join(self.output_dir, "validation_summary.json"), 'w', encoding='utf-8') as f:
                json.dump(improvements_summary, f, indent=2)
            
            return True
        except Exception as e:
            self.update_status(f"Warning: Code quality enhancement failed: {str(e)}")
            # Continue with the process even if validation fails
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
    
    def generate_icons(self):
        """Generate SVG icons based on the element dictionary and application requirements"""
        try:
            if not self.element_dictionary:
                self.update_status("No element dictionary available, skipping icon generation")
                return False
                
            # Parse the element dictionary if it's a string
            if isinstance(self.element_dictionary, str):
                try:
                    element_dict = json.loads(self.element_dictionary)
                except json.JSONDecodeError:
                    # Extract JSON from the string if it's wrapped in text
                    import re
                    json_match = re.search(r'(\{.*\})', self.element_dictionary, re.DOTALL)
                    if json_match:
                        try:
                            element_dict = json.loads(json_match.group(1))
                        except:
                            self.update_status("Failed to parse element dictionary JSON, skipping icon generation")
                            return False
                    else:
                        self.update_status("Could not find JSON in element dictionary, skipping icon generation")
                        return False
            else:
                element_dict = self.element_dictionary
                
            # Extract icon definitions
            icon_definitions = element_dict.get("icons", [])
            
            if not icon_definitions:
                self.update_status("No icon definitions found in element dictionary")
                return False
                
            # Filter icons based on application requirements and usage in HTML/JS files
            required_icons = self._identify_required_icons(icon_definitions)
            
            if not required_icons:
                self.update_status("No specific icons required for this application")
                return False
                
            self.update_status(f"Identified {len(required_icons)} required icons for the application")
            
            # Create SVG generator
            from src.api.openrouter import OpenRouterAPI
            api_client = OpenRouterAPI()
            svg_generator = SVGIconGenerator(api_client)
            
            # Generate icons
            generated_icons = svg_generator.generate_icons_for_project(
                self.output_dir, 
                required_icons
            )
            
            # Validate the generated icons
            valid_icons = self._validate_generated_icons(generated_icons)
            
            self.update_status(f"Successfully generated {len(valid_icons)} SVG icons in assets/icons directory")
            return True
        except Exception as e:
            self.update_status(f"Error generating SVG icons: {str(e)}")
            return False

    def _identify_required_icons(self, icon_definitions):
        """
        Identify ONLY icons that are actually referenced in the code.
        Performs strict matching to ensure only exactly referenced icons are generated.
        """
        try:
            # First, extract all possible icons from the definitions for better matching
            all_possible_icons = {}  # Map icon names to their definitions
            for icon_def in icon_definitions:
                icon_name = icon_def.get("name", "").lower()
                if icon_name:
                    all_possible_icons[icon_name] = icon_def
                    
                    # Also store without "icon-" prefix if the file has it
                    icon_file = icon_def.get("file", "").lower()
                    if icon_file.startswith("icon-"):
                        base_name = icon_file[5:].replace(".svg", "")
                        all_possible_icons[base_name] = icon_def
            
            # Map to keep track of where each icon is referenced
            icon_references = {}
            
            # Map to track actual icon filenames found in the code
            exact_icon_filenames = set()
            
            self.update_status("Scanning files for exact icon references...")
            
            # Collect all HTML, CSS, JS files for scanning
            code_files = []
            for root, _, files in os.walk(self.output_dir):
                for file in files:
                    if file.endswith(('.html', '.js', '.css')):
                        code_files.append(os.path.join(root, file))
            
            # First pass: Look for exact SVG filenames
            for file_path in code_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        # Find all .svg references
                        svg_references = re.findall(r'([a-zA-Z0-9_-]+\.svg)', content)
                        
                        for svg_ref in svg_references:
                            svg_name = svg_ref.lower()
                            exact_icon_filenames.add(svg_name)
                            base_name = svg_name.replace('.svg', '')
                            # Also find without "icon-" prefix if present
                            if base_name.startswith('icon-'):
                                base_name = base_name[5:]
                            
                            # Check if this matches any defined icon
                            for icon_name, icon_def in all_possible_icons.items():
                                if base_name == icon_name or svg_name == icon_def.get("file", "").lower():
                                    if icon_name not in icon_references:
                                        icon_references[icon_name] = []
                                    icon_references[icon_name].append((file_path, svg_ref))
                except Exception as e:
                    self.update_status(f"Warning: Error scanning {os.path.basename(file_path)}: {e}")
            
            # Second pass: Look for specific patterns indicating icons
            icon_patterns = [
                # Common icon pattern formats
                r'<i[^>]*class="[^"]*(?:fa|icon)[^"]*(?:fa|icon)-([a-z0-9_-]+)[^"]*"[^>]*>',
                r'<img[^>]*src="[^"]*\/icons\/([^"]+\.svg)"[^>]*>',
                r'<img[^>]*src="[^"]*\/([^"]+\.svg)"[^>]*>',
                r'<svg[^>]*class="[^"]*(?:icon|svg)-([a-z0-9_-]+)[^"]*"[^>]*>',
                r'<use[^>]*xlink:href="[^"]*#icon-([a-z0-9_-]+)[^"]*"[^>]*>',
                r'"iconName":\s*"([a-z0-9_-]+)"',
                r'\.icon-([a-z0-9_-]+)\s*{',
                r'loadIcon\("([a-z0-9_-]+)"\)',
                r'getIcon\("([a-z0-9_-]+)"\)',
            ]
            
            for file_path in code_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        # Check all patterns
                        for pattern in icon_patterns:
                            matches = re.findall(pattern, content, re.IGNORECASE)
                            for match in matches:
                                match_lower = match.lower()
                                base_name = match_lower.replace('.svg', '')
                                
                                # Strip common prefixes that might be in the match
                                for prefix in ['icon-', 'fa-', 'svg-']:
                                    if base_name.startswith(prefix):
                                        base_name = base_name[len(prefix):]
                                
                                # Check if this matches any defined icon
                                for icon_name, icon_def in all_possible_icons.items():
                                    if base_name == icon_name:
                                        if icon_name not in icon_references:
                                            icon_references[icon_name] = []
                                        icon_references[icon_name].append((file_path, match))
                except Exception as e:
                    self.update_status(f"Warning: Error pattern scanning {os.path.basename(file_path)}: {e}")
            
            # Special case: Look for specific icon names in comments or text
            specific_icon_patterns = [
                # Look for patterns like "XXX.svg - Used for..." or "Uses XXX icon for..."
                r'([a-z0-9_-]+)\.svg\s*[-–—]\s*[uU]sed for',
                r'[uU]se(?:s|d)?\s+([a-z0-9_-]+)\s+icon\s+for',
                r'[uU]se(?:s|d)?\s+([a-z0-9_-]+)\.svg\s+for',
            ]
            
            for file_path in code_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        for pattern in specific_icon_patterns:
                            matches = re.findall(pattern, content, re.IGNORECASE)
                            for match in matches:
                                match_lower = match.lower()
                                base_name = match_lower.replace('.svg', '')
                                
                                # Check if this matches any defined icon
                                for icon_name, icon_def in all_possible_icons.items():
                                    if base_name == icon_name:
                                        if icon_name not in icon_references:
                                            icon_references[icon_name] = []
                                        icon_references[icon_name].append((file_path, f"{match}.svg (from comment)"))
                except Exception:
                    pass
            
            # Log findings
            if icon_references:
                required_icons = list(icon_references.keys())
                self.update_status(f"Found {len(required_icons)} specific icon references:")
                
                for icon_name in required_icons:
                    references = icon_references[icon_name]
                    file_refs = [f"{os.path.relpath(ref[0], self.output_dir)} ({ref[1]})" for ref in references]
                    self.update_status(f"  - {icon_name}: referenced in {', '.join(file_refs)}")
                    
                # Check for exact icon filenames that weren't matched to our definitions
                if exact_icon_filenames:
                    unmatched = [f for f in exact_icon_filenames if not any(f.replace('.svg', '') == name or f == all_possible_icons.get(name, {}).get('file', '').lower() for name in required_icons)]
                    if unmatched:
                        self.update_status(f"Found {len(unmatched)} SVG filenames with no matching definitions:")
                        for unmatch in unmatched:
                            self.update_status(f"  - {unmatch} (no matching definition)")
                        
                        # Try to find the closest match in our definitions
                        for unmatch in unmatched:
                            base_name = unmatch.replace('.svg', '')
                            
                            # Look for a similar icon in our definitions
                            best_match = None
                            best_score = 0
                            for name, def_obj in all_possible_icons.items():
                                # Simple similarity score (number of shared characters)
                                score = sum(1 for c in base_name if c in name)
                                if score > best_score:
                                    best_score = score
                                    best_match = name
                            
                            if best_match and best_score > len(base_name) / 2:  # At least half the characters match
                                self.update_status(f"  - Using {best_match} as closest match for {unmatch}")
                                if best_match not in required_icons:
                                    required_icons.append(best_match)
                            else:
                                # Create a custom icon definition for this filename
                                for icon_def in icon_definitions:
                                    if base_name == icon_def.get("name", "").lower():
                                        if base_name not in required_icons:
                                            required_icons.append(base_name)
                                        break
            else:
                self.update_status("No specific icon references found in code.")
                required_icons = []
            
            # Filter the icon definitions to only those that are actually used
            filtered_icons = []
            for icon_def in icon_definitions:
                icon_name = icon_def.get("name", "").lower()
                if icon_name in required_icons:
                    filtered_icons.append(icon_def)
            
            if filtered_icons:
                self.update_status(f"Will generate only the {len(filtered_icons)} icons actually used: {', '.join(icon_def.get('name', '') for icon_def in filtered_icons)}")
            else:
                self.update_status("No icons will be generated as none are referenced in the code.")
            
            return filtered_icons
        except Exception as e:
            self.update_status(f"Warning: Error identifying required icons: {e}")
            return []

    def _validate_generated_icons(self, generated_icons):
        """
        Validate the generated SVG icons to ensure they are properly formed and match the expected names
        """
        valid_icons = []
        
        for icon_path in generated_icons:
            try:
                icon_name = os.path.basename(icon_path)
                self.update_status(f"Validating icon: {icon_name}")
                
                with open(icon_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Basic validation checks
                if not content or len(content) < 30:
                    self.update_status(f"Warning: Icon {icon_name} is empty or too small, regenerating...")
                    # Here we could try to regenerate the icon
                    continue
                    
                if '<svg' not in content or '</svg>' not in content:
                    self.update_status(f"Warning: Icon {icon_name} is not a valid SVG, regenerating...")
                    # Here we could try to regenerate the icon
                    continue
                    
                # Check for common issues
                if 'width="0"' in content or 'height="0"' in content:
                    self.update_status(f"Warning: Icon {icon_name} has zero dimensions, fixing...")
                    content = content.replace('width="0"', 'width="24"')
                    content = content.replace('height="0"', 'height="24"')
                    with open(icon_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                        
                # Ensure viewBox is present
                if 'viewBox' not in content:
                    self.update_status(f"Adding missing viewBox to {icon_name}")
                    content = content.replace('<svg', '<svg viewBox="0 0 24 24"')
                    with open(icon_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                
                # Ensure we have either a fill or stroke for visibility
                if 'fill=' not in content and 'stroke=' not in content:
                    self.update_status(f"Adding missing fill to {icon_name}")
                    content = content.replace('<svg', '<svg fill="currentColor"')
                    with open(icon_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                        
                valid_icons.append(icon_path)
            except Exception as e:
                self.update_status(f"Warning: Failed to validate icon {os.path.basename(icon_path)}: {e}")
        
        return valid_icons

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
            self.update_progress(0.15)
            self.project_structure = generate_project_structure(self.optimized_prompt)
            
            # Phase 2.5: Generate element dictionary for consistency
            if 'static website' in self.user_prompt.lower() or 'html' in self.user_prompt.lower():
                self.update_status("Creating element dictionary for consistent naming...")
                self.update_progress(0.2)
                self.element_dictionary = generate_element_dictionary(self.optimized_prompt)
                os.makedirs(self.output_dir, exist_ok=True)
                # Save the element dictionary to the project
                with open(os.path.join(self.output_dir, "element-dictionary.json"), 'w', encoding='utf-8') as f:
                    f.write(self.element_dictionary)
            
            # Phase 3: Create directory structure
            self.update_status("Creating directory structure...")
            self.update_progress(0.25)
            os.makedirs(self.output_dir, exist_ok=True)
            if not self.create_directory_structure(self.project_structure):
                return {
                    'error': True,
                    'message': 'Failed to create directory structure',
                    'output_dir': self.output_dir,
                    'app_name': self.app_name or 'generated_application',
                    'optimized_prompt': self.optimized_prompt
                }
            
            # Phase 4: Populate files - NOUVEAU: Maintenant avant la génération des SVG
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
            
            # Phase 4.5: Generate SVG Icons APRÈS la génération des fichiers HTML
            if self.element_dictionary:
                self.update_status("Analyzing HTML files and generating required SVG icons...")
                self.update_progress(0.65)
                self.generate_icons()
            
            # Phase 5: Validate and enhance code
            self.update_status("Enhancing code quality...")
            self.update_progress(0.85)
            self.enhance_code_quality()
            
            # Phase 6: Generate README
            self.update_status("Creating documentation...")
            self.update_progress(0.9)
            readme_content = generate_readme(self.app_name, self.optimized_prompt, self.project_structure)
            with open(os.path.join(self.output_dir, "README.md"), 'w', encoding='utf-8') as f:
                f.write(readme_content)
            
            # Phase 7: Create zip file
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
                'optimized_prompt': self.optimized_prompt,
                'element_dictionary': self.element_dictionary
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