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
        
    def _remove_svg_icons_from_structure(self):
        """
        Supprime toute référence aux dossiers d'icônes et fichiers SVG dans la structure du projet.
        Les icônes seront créées directement dans le code HTML/CSS/JS à la place.
        """
        try:
            # Vérifier que project_structure est chargé
            if not self.project_structure:
                return
                
            # Analyser la structure si c'est une chaîne JSON
            structure = json.loads(self.project_structure) if isinstance(self.project_structure, str) else self.project_structure
            
            # Filtrer les répertoires - supprimer 'assets/icons' et similaires
            if "directories" in structure:
                filtered_dirs = []
                for directory in structure["directories"]:
                    path = directory.get("path", "")
                    # Exclure tout répertoire contenant "icons" dans son chemin
                    if "icons" not in path.lower():
                        filtered_dirs.append(directory)
                    else:
                        self.update_status(f"Suppression du répertoire d'icônes '{path}' de la structure")
                
                structure["directories"] = filtered_dirs
            
            # Filtrer les fichiers - supprimer tous les .svg et les références aux icônes
            if "files" in structure:
                filtered_files = []
                for file in structure["files"]:
                    path = file.get("path", "")
                    # Exclure tout fichier .svg ou se trouvant dans un dossier d'icônes
                    if not path.lower().endswith(".svg") and "/icons/" not in path.lower() and "\\icons\\" not in path.lower():
                        filtered_files.append(file)
                    else:
                        self.update_status(f"Suppression du fichier SVG '{path}' de la structure")
                
                structure["files"] = filtered_files
            
            # Mettre à jour la structure
            if isinstance(self.project_structure, str):
                self.project_structure = json.dumps(structure)
            else:
                self.project_structure = structure
                
            self.update_status("Structure de projet modifiée: les références aux icônes SVG ont été supprimées")
            
        except Exception as e:
            self.update_status(f"Avertissement: Impossible de supprimer les références aux icônes: {str(e)}")
        
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
                
                # Modifier pour générer des CSS complets sans éléments TODO ou à remplir
                if file_path.lower().endswith('.css'):
                    file_content = self._generate_complete_css(
                        file_path, 
                        self.optimized_prompt, 
                        self.project_structure,
                        self.element_dictionary
                    )
                else:
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
            
    def _generate_complete_css(self, file_path, optimized_prompt, project_structure, element_dictionary):
        """
        Génère un fichier CSS complet et s'assure qu'il n'y a pas d'éléments manquants ou à compléter.
        
        Args:
            file_path: Chemin du fichier CSS
            optimized_prompt: Prompt optimisé
            project_structure: Structure du projet
            element_dictionary: Dictionnaire d'éléments
            
        Returns:
            str: Contenu CSS complet
        """
        self.update_status(f"Générant un CSS complet pour {file_path}")
        
        # D'abord, générer le contenu normal
        css_content = generate_file_content(file_path, optimized_prompt, project_structure, element_dictionary)
        
        # Vérifier s'il y a des TODOs ou des commentaires de remplissage
        todo_patterns = [
            r'/\*\s*TODO.*?\*/', 
            r'\/\/\s*TODO.*?$',
            r'/\*\s*À compléter.*?\*/',
            r'\/\/\s*À compléter.*?$',
            r'/\*\s*A remplir.*?\*/',
            r'\/\/\s*A remplir.*?$',
            r'\/\*\s*FILL ME.*?\*\/',
            r'\/\/\s*FILL ME.*?$'
        ]
        
        has_todos = any(re.search(pattern, css_content, re.IGNORECASE | re.MULTILINE) for pattern in todo_patterns)
        
        # S'il y a des TODOs, on régénère le CSS avec des instructions plus strictes
        if has_todos:
            self.update_status(f"Des éléments incomplets détectés dans le CSS, régénération...")
            
            # Créer un message système spécifique pour générer un CSS complet
            from src.api.openrouter import generate_text
            
            system_message = """
            Vous êtes un expert en CSS. Votre tâche est de générer un fichier CSS complet et fonctionnel.
            IMPORTANT: Ne laissez AUCUN élément "à compléter", "TODO", ou tout autre espace réservé.
            N'utilisez PAS de commentaires indiquant qu'un élément est "à remplir plus tard".
            Chaque règle CSS doit être complète, fonctionnelle et appropriée pour l'application.
            Fournissez TOUS les styles nécessaires pour un site web ou une application entièrement fonctionnel.
            """
            
            # Créer un prompt spécifique
            prompt = f"""
            Générez un fichier CSS COMPLET pour : {file_path}
            
            Description du projet: 
            {optimized_prompt}
            
            Ce fichier CSS doit:
            1. Être ENTIÈREMENT fonctionnel et complet sans aucun élément manquant
            2. Contenir toutes les règles CSS nécessaires pour styler l'application/site
            3. Ne PAS contenir de TODOs, commentaires "à compléter", ou espaces réservés
            4. Utiliser des valeurs concrètes pour tous les éléments (couleurs, tailles, etc.)
            5. Être prêt à l'utilisation immédiate sans modification
            
            Le fichier CSS précédemment généré contenait des éléments incomplets. 
            Veuillez générer un CSS complet qui répond à tous les besoins de l'application.
            """
            
            # Générer le CSS complet
            css_content = generate_text(prompt, temperature=0.4, system_message=system_message)
            
            # Nettoyer le contenu
            css_content = clean_generated_content(css_content)
            
            # Vérification finale pour retirer tout TODO restant
            for pattern in todo_patterns:
                css_content = re.sub(pattern, '/* */', css_content, flags=re.IGNORECASE | re.MULTILINE)
        
        return css_content
    
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
        """
        Désactive complètement la génération d'icônes SVG - aucun dictionnaire n'est préparé.
        Les icônes seront uniquement générées par le code frontend si nécessaire.
        """
        # Supprimer tout dossier d'icônes existant s'il existe déjà
        icons_dir = os.path.join(self.output_dir, "assets", "icons")
        if os.path.exists(icons_dir):
            try:
                shutil.rmtree(icons_dir)
                self.update_status("Dossier d'icônes supprimé - les SVG ne seront générés que par le code frontend")
            except Exception as e:
                self.update_status(f"Note: Impossible de supprimer le dossier d'icônes: {str(e)}")
        
        # Ne crée pas de dictionnaire d'icônes, ne parcours pas les fichiers pour chercher des références
        self.update_status("Aucun dictionnaire d'icônes préparé - les icônes seront gérées directement par le code frontend")
        
        return True

    def _identify_required_icons(self, icon_definitions):
        """
        Cette méthode est désactivée - aucun dictionnaire d'icônes n'est créé.
        Le code frontend est responsable de générer ses propres icônes.
        
        Args:
            icon_definitions: Ignoré
            
        Returns:
            dict: Dictionnaire vide
        """
        # Ne crée aucun dictionnaire - retourne un dictionnaire vide
        return {}

    def get_inline_svg(self, icon_name):
        """
        Génère une icône SVG à la demande, uniquement lorsqu'elle est explicitement demandée par le code frontend.
        
        Args:
            icon_name (str): Nom de l'icône à générer
            
        Returns:
            str: Contenu SVG inline
        """
        # Si le générateur SVG n'est pas initialisé, le créer
        if not hasattr(self, 'svg_generator'):
            from src.api.openrouter import OpenRouterAPI
            api_client = OpenRouterAPI()
            from src.generators.svg_generator import SVGIconGenerator
            self.svg_generator = SVGIconGenerator(api_client)
        
        # Génère l'icône à la demande sans utiliser de dictionnaire préétabli
        icon_description = f"{icon_name} icon"
        return self.svg_generator.get_inline_svg_content(icon_name, icon_description)

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
            
            # Supprimer les références aux icônes SVG dans la structure
            self._remove_svg_icons_from_structure()
            
            # Phase 2.5: Generate element dictionary for consistency
            if 'static website' in self.user_prompt.lower() or 'html' in self.user_prompt.lower():
                self.update_status("Creating element dictionary for consistent naming...")
                self.update_progress(0.2)
                self.element_dictionary = generate_element_dictionary(self.optimized_prompt)
                
                # Ajouter une instruction pour les icônes SVG inline
                try:
                    if isinstance(self.element_dictionary, str):
                        element_dict = json.loads(self.element_dictionary)
                        # Ajouter une instruction spéciale pour les icônes
                        if "instructions" not in element_dict:
                            element_dict["instructions"] = []
                        
                        element_dict["instructions"].append({
                            "type": "svg_icons",
                            "message": "Les icônes SVG doivent être intégrées directement dans le code HTML/CSS/JS en dur, sans utiliser de fichiers externes."
                        })
                        
                        # Remise en JSON
                        self.element_dictionary = json.dumps(element_dict)
                except Exception as e:
                    self.update_status(f"Note: Impossible d'ajouter l'instruction pour les icônes SVG: {str(e)}")
                
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