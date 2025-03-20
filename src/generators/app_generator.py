import os
import json
import logging
from typing import Dict, Any, List, Optional

from src.api.client import AIAppGeneratorAPI
from src.file_manager.file_manager import FileSystemManager
from src.generators.framework.framework_adapter import adjust_architecture_for_framework
from src.config.prompts import CSS_DESIGNER_PROMPT  
from src.config.constants import AGENT_TEAM_ENABLED, USE_OPENROUTER
from src.config import constants
from src.generators.context_enricher import ContextEnricher

logger = logging.getLogger(__name__)

from ..api.agent_calls.multi_file_generation import generate_multiple_files, write_multiple_files

class AppGenerator:
    def __init__(self, api_key):
        # Update USE_OPENROUTER from session state if available
        try:
            import streamlit as st
            if 'advanced_options' in st.session_state and 'use_openrouter' in st.session_state.advanced_options:
                constants.USE_OPENROUTER = st.session_state.advanced_options['use_openrouter']
                logging.info(f"OpenRouter usage set to: {constants.USE_OPENROUTER}")
        except ImportError:
            pass  # Streamlit not available
            
        self._api_client = AIAppGeneratorAPI(api_key)
        self.file_manager = FileSystemManager()
        self._requirements_spec = None
        self._architecture = None
        self._database_schema = None
        self._api_spec = None
        
    @property
    def api_client(self):
        return self._api_client
    
    @property
    def project_context(self):
        """Get the full project context for API calls"""
        if not hasattr(self, '_requirements_spec') or self._requirements_spec is None:
            return {}
            
        return {
            "requirements": self._requirements_spec,
            "architecture": self._architecture,
            "database": self._database_schema,
            "api": self._api_spec
        }
    
    def _build_requirements_spec(self, user_prompt, include_tests=False, create_docker=False, add_ci_cd=False):
        """Analyze user prompt to build requirements specification"""
        print(f"Analyzing requirements from prompt: '{user_prompt[:50]}...'")
        
        requirements = self._api_client.analyze_requirements(user_prompt)
        
        if not requirements:
            raise Exception("Failed to analyze requirements")
            
        requirements["generate_tests"] = include_tests
        requirements["create_docker"] = create_docker
        requirements["add_ci_cd"] = add_ci_cd
        
        tech_stack = requirements.get('technical_stack', {})
        if isinstance(tech_stack, dict):
            language = tech_stack.get('language', '').lower()
            framework = tech_stack.get('framework', '').lower()
            
            # Detect static website (HTML/CSS/JS without a backend framework)
            if (language in ['html', 'javascript'] and not framework) or framework == 'static':
                requirements["is_static_website"] = True
                requirements["technical_stack"]["framework"] = "static"
                print("Detected static website (HTML/CSS/JS without backend)")
            elif ((language == 'python' and framework in ['flask', 'django']) or
                (language == 'php') or
                (language == 'javascript' and framework in ['express', 'next', 'nuxt']) or
                (framework in ['laravel', 'symfony', 'rails', 'asp.net'])):
                
                requirements["unified_frontend_backend"] = True
                print(f"Detected {framework if framework else language} as a unified frontend/backend framework")
        
        return requirements
    
    def _design_architecture(self):
        """Design the application architecture based on requirements"""
        if not self._requirements_spec:
            raise Exception("Requirements specification is missing")
            
        architecture = self._api_client.design_architecture(self._requirements_spec)
        
        if not architecture:
            raise Exception("Failed to design architecture")
            
        if not isinstance(architecture, dict):
            logger.error(f"Architecture design returned invalid format: {type(architecture)}")
            logger.error(f"Architecture content: {architecture[:200]}..." if isinstance(architecture, str) else str(architecture))
            raise Exception("Architecture design returned invalid format (not a dict)")
            
        return architecture
    
    def _design_database(self):
        """Design database schema if required by the application"""
        if not self._requirements_spec or not self._architecture:
            raise Exception("Requirements or architecture is missing")
            
        database_schema = self._api_client.design_database(self._requirements_spec, self._architecture)
        
        if not database_schema:
            logger.warning("Failed to design database schema, continuing without it")
            return {}
            
        return database_schema
    
    def _design_api(self):
        """Design API if required by the application"""
        if not self._requirements_spec or not self._architecture:
            raise Exception("Requirements or architecture is missing")
            
        api_spec = self._api_client.design_api(self._requirements_spec, self._architecture)
        
        if not api_spec:
            logger.warning("Failed to design API, continuing without it")
            return {}
            
        return api_spec
    
    def _generate_file_code(self, file_spec):
        """Generate code for a specific file"""
        if not file_spec:
            raise Exception("File specification is missing")
            
        project_context = {
            "requirements": self._requirements_spec,
            "architecture": self._architecture,
            "database": self._database_schema,
            "api": self._api_spec,
            "file": file_spec
        }
        
        file_path = file_spec.get('path', '')
        if file_path.endswith('.css'):
            print(f"Using specialized CSS Designer for {file_path}")
            code = self._api_client.call_agent(
                CSS_DESIGNER_PROMPT,
                json.dumps(project_context),
                max_tokens=4000
            )
        else:
            code = self._api_client.generate_code(file_spec, project_context)
        
        if not code:
            raise Exception(f"Failed to generate code for {file_spec.get('path')}")
            
        return code
        
    def generate_application(self, user_prompt, output_path, include_tests=False, create_docker=False, add_ci_cd=False, use_sample_json=False, ai_generated_everything=True):
        """Generate a complete application based on user prompt"""
        # Ensure the user is informed that all files will be AI-generated
        if ai_generated_everything:
            print("Using AI to generate ALL project files (no templates)")
        
        self._requirements_spec = self._build_requirements_spec(
            user_prompt, include_tests, create_docker, add_ci_cd
        )
        
        if not isinstance(self._requirements_spec, dict):
            logger.error(f"Requirements returned invalid format: {type(self._requirements_spec)}")
            raise Exception("Requirements analysis returned invalid format (not a dict)")
            
        app_name = self._requirements_spec.get('app_name', 'Unnamed App')
        print(f"Designing architecture for {app_name}")
        
        # Inject sample JSON preference in the requirements
        if use_sample_json:
            if not self._requirements_spec.get("data_requirements"):
                self._requirements_spec["data_requirements"] = {}
            elif isinstance(self._requirements_spec["data_requirements"], str):
                # Convert string to dictionary if necessary
                self._requirements_spec["data_requirements"] = {"description": self._requirements_spec["data_requirements"]}
                
            if isinstance(self._requirements_spec["data_requirements"], dict):
                self._requirements_spec["data_requirements"]["use_json_files"] = True
                self._requirements_spec["data_requirements"]["use_sample_data"] = True
                print("Using JSON files with sample data instead of database")
            else:
                logger.warning(f"Could not set JSON data preferences, data_requirements has unexpected type: {type(self._requirements_spec['data_requirements'])}")
        
        # Add flag to ensure we generate all necessary configuration files
        if ai_generated_everything and not self._requirements_spec.get("generate_all_files"):
            self._requirements_spec["generate_all_files"] = True
            self._requirements_spec["include_config_files"] = True
            print("Ensuring all configuration files are included in the generated architecture")
        
        self._architecture = self._design_architecture()
        
        self._architecture = adjust_architecture_for_framework(self._architecture, self._requirements_spec)
        
        if isinstance(self._requirements_spec.get('components', []), list) and any(
            'database' in comp.get('type', '') for comp in self._requirements_spec.get('components', []) 
            if isinstance(comp, dict)
        ) and not use_sample_json:
            print("Designing database schema")
            self._database_schema = self._design_database()
        else:
            if use_sample_json:
                print("Creating sample JSON data structures instead of database schema")
                self._database_schema = self._design_json_data()
            else:
                self._database_schema = {}
        
        if isinstance(self._requirements_spec.get('components', []), list) and any(
            'api' in comp.get('type', '') for comp in self._requirements_spec.get('components', []) 
            if isinstance(comp, dict)
        ):
            print("Designing API interfaces")
            self._api_spec = self._design_api()
        else:
            self._api_spec = {}
            
        print(f"Creating project structure at {output_path}")
        files_to_generate = self.file_manager.create_project_structure(output_path, self._architecture)
        print(f"Preparing to generate {len(files_to_generate)} files")
        
        # Classifier les fichiers par type pour la génération par lots
        frontend_files = []
        backend_files = []
        config_files = []
        
        for file_spec in files_to_generate:
            file_path = file_spec.get("path", "")
            file_type = file_spec.get("type", "").lower()
            file_purpose = file_spec.get("purpose", "").lower()
            
            if not file_path:
                continue
                
            if file_path.endswith(("package.json", "requirements.txt", ".env", "Dockerfile", "docker-compose.yml", 
                                  "README.md", ".gitignore")):
                config_files.append(file_spec)
            elif file_path.endswith((".html", ".css", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte")) or \
                 "frontend" in file_path.lower() or "ui" in file_purpose or "client" in file_purpose:
                frontend_files.append(file_spec)
            else:
                backend_files.append(file_spec)
        
        generated_files = []
        
        # Enrichir le contexte du projet
        enriched_context = ContextEnricher.enrich_generation_context(
            self.project_context, 
            output_path
        )
        enriched_context['output_dir'] = output_path
        
        # Générer les fichiers de configuration individuellement
        for file_spec in config_files:
            try:
                file_path = file_spec.get("path", "")
                print(f"Generating file: {file_path}")
                
                if file_path.endswith("package.json") or file_path.endswith("requirements.txt"):
                    file_type = "package.json" if file_path.endswith("package.json") else "requirements.txt"
                    file_structure = ContextEnricher._get_project_structure(output_path)
                    file_content = self._api_client.generate_project_file(
                        file_type,
                        enriched_context,
                        file_structure
                    )
                else:
                    file_content = self._api_client.generate_code(
                        file_spec, 
                        enriched_context
                    )
                
                absolute_path = self.file_manager.write_code_to_file(output_path, file_path, file_content)
                generated_files.append({
                    "path": file_path,
                    "absolute_path": absolute_path,
                    "spec": file_spec
                })
            except Exception as e:
                print(f"Error generating config file {file_path}: {str(e)}")
        
        # Générer les fichiers frontend en lot (si > 1 fichier)
        if len(frontend_files) > 1:
            print(f"Generating {len(frontend_files)} frontend files in batch...")
            try:
                frontend_files_content = generate_multiple_files(
                    self._api_client,
                    frontend_files,
                    enriched_context,
                    "frontend"
                )
                
                if frontend_files_content:
                    written_files = write_multiple_files(output_path, frontend_files_content)
                    print(f"Successfully generated {len(written_files)} frontend files in batch")
                    
                    # Ajouter les fichiers générés à la liste
                    for file_path in written_files:
                        rel_path = os.path.relpath(file_path, output_path)
                        matching_spec = next((spec for spec in frontend_files if spec.get("path") == rel_path), {})
                        generated_files.append({
                            "path": rel_path,
                            "absolute_path": file_path,
                            "spec": matching_spec
                        })
                else:
                    # Fallback à la génération individuelle
                    print("Batch frontend generation failed, falling back to individual generation")
                    self._generate_files_individually(frontend_files, generated_files, output_path, enriched_context)
            except Exception as e:
                print(f"Error in batch frontend generation: {str(e)}")
                print("Falling back to individual generation for frontend files")
                self._generate_files_individually(frontend_files, generated_files, output_path, enriched_context)
        else:
            # Si un seul fichier frontend, générer individuellement
            self._generate_files_individually(frontend_files, generated_files, output_path, enriched_context)
        
        # Générer les fichiers backend en lot (si > 1 fichier)
        if len(backend_files) > 1:
            print(f"Generating {len(backend_files)} backend files in batch...")
            try:
                backend_files_content = generate_multiple_files(
                    self._api_client,
                    backend_files,
                    enriched_context,
                    "backend"
                )
                
                if backend_files_content:
                    written_files = write_multiple_files(output_path, backend_files_content)
                    print(f"Successfully generated {len(written_files)} backend files in batch")
                    
                    # Ajouter les fichiers générés à la liste
                    for file_path in written_files:
                        rel_path = os.path.relpath(file_path, output_path)
                        matching_spec = next((spec for spec in backend_files if spec.get("path") == rel_path), {})
                        generated_files.append({
                            "path": rel_path,
                            "absolute_path": file_path,
                            "spec": matching_spec
                        })
                else:
                    # Fallback à la génération individuelle
                    print("Batch backend generation failed, falling back to individual generation")
                    self._generate_files_individually(backend_files, generated_files, output_path, enriched_context)
            except Exception as e:
                print(f"Error in batch backend generation: {str(e)}")
                print("Falling back to individual generation for backend files")
                self._generate_files_individually(backend_files, generated_files, output_path, enriched_context)
        else:
            # Si un seul fichier backend, générer individuellement
            self._generate_files_individually(backend_files, generated_files, output_path, enriched_context)

        print("Extracting file signatures for comprehensive validation")
        all_file_contents = {}
        
        is_static_website = self._requirements_spec.get('is_static_website', False)
        if isinstance(self._requirements_spec.get('technical_stack', {}), dict):
            if self._requirements_spec.get('technical_stack', {}).get('framework', '') == 'static':
                is_static_website = True
        
        for file_info in generated_files:
            if is_static_website:
                if file_info["path"].endswith(('.js')):
                    try:
                        with open(file_info["absolute_path"], 'r', encoding='utf-8') as f:
                            file_content = f.read()
                            all_file_contents[file_info["path"]] = file_content
                    except Exception as e:
                        print(f"Warning: Could not read {file_info['path']}: {str(e)}")
            else:
                if file_info["path"].endswith(('.py', '.js', '.ts', '.jsx', '.tsx')):
                    try:
                        with open(file_info["absolute_path"], 'r', encoding='utf-8') as f:
                            file_content = f.read()
                            all_file_contents[file_info["path"]] = file_content
                    except Exception as e:
                        print(f"Warning: Could not read {file_info['path']}: {str(e)}")
        
        if all_file_contents:
            print("Performing cross-file validation on all files")
            try:
                results = self._api_client.cross_file_code_reviewer(all_file_contents, self.project_context)
                
                if results and isinstance(results, dict):
                    for file_path, fixed_content in results.items():
                        if fixed_content != "PARFAIT":
                            print(f"Fixing issues in {file_path}")
                            self.file_manager.write_code_to_file(output_path, file_path, fixed_content)
                else:
                    logger.warning("Cross-file validation returned non-dictionary result")
            except Exception as e:
                print(f"Warning: Cross-file validation failed: {str(e)}")
                logger.exception("Cross-file validation error")  # Add this line to log the full traceback
        
        file_structure = []
        for root, dirs, files in os.walk(output_path):
            rel_root = os.path.relpath(root, output_path)
            if rel_root == ".":
                rel_root = ""
            for file in files:
                file_path = os.path.join(rel_root, file) if rel_root else file
                file_structure.append(file_path)
        
        print("Generating comprehensive README.md")
        readme_content = self._api_client.generate_project_file(
            'README.md',
            self.project_context,
            file_structure  # This now contains the final list of all files
        )
        with open(os.path.join(output_path, "README.md"), 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        # Convertir tous les .env.example en .env
        env_example_path = os.path.join(output_path, '.env.example')
        env_path = os.path.join(output_path, '.env')
        
        if os.path.exists(env_example_path):
            try:
                # Si un .env existe déjà, ne pas l'écraser
                if not os.path.exists(env_path):
                    with open(env_example_path, 'r', encoding='utf-8') as example_file:
                        env_content = example_file.read()
                    
                    with open(env_path, 'w', encoding='utf-8') as env_file:
                        env_file.write(env_content)
                    
                    print("Converted .env.example to .env")
                    
                    # Supprimer le .env.example après la conversion
                    os.remove(env_example_path)
            except Exception as e:
                logger.warning(f"Could not convert .env.example to .env: {str(e)}")
        
        try:
            print(f"Project successfully generated at {output_path}")
            return output_path
        except Exception as e:
            logger.exception("Error in final project processing")
            # Still return the path since the project was successfully generated
            print(f"Project was successfully generated despite an error in final processing: {str(e)}")
            return output_path

    def _design_json_data(self):
        """Design JSON data structures with sample data instead of a database schema"""
        if not self._requirements_spec or not self._architecture:
            raise Exception("Requirements or architecture is missing")
            
        context = {
            "requirements": self._requirements_spec,
            "architecture": self._architecture,
            "instructions": "Create sample JSON data structures instead of database schema. "
                           "The data must be valid JSON, not Python code. Include realistic sample "
                           "data that matches the application domain."
        }
        
        json_data = self._api_client.call_agent(
            "You are a JSON Data Structure Designer. Create sample JSON data files with realistic test data "
            "based on the application requirements. The JSON data must be valid and contain no Python code. "
            "Include multiple sample records for each entity type. Return only valid JSON structures.", 
            json.dumps(context),
            max_tokens=4000
        )
        
        try:
            sample_data = json.loads(json_data)
            return {"json_data_structures": sample_data}
        except json.JSONDecodeError:
            import re
            json_matches = re.findall(r'```(?:json)?\s*([\s\S]*?)\s*```', json_data)
            if json_matches:
                try:
                    sample_data = json.loads(json_matches[0])
                    return {"json_data_structures": sample_data}
                except json.JSONDecodeError:
                    pass
                    
            logger.warning("Failed to parse JSON data structures, returning empty schema")
            return {"json_data_structures": {}}

    def validate_generated_project(self, output_dir):
        """Validate the generated project"""
        logger.info("Starting project validation...")
        
        # Vérifier si la validation par l'équipe d'agents est activée
        if AGENT_TEAM_ENABLED:
            logger.info("Starting agent team verification...")
            from src.validators.agent_team_verifier import run_verification_team
            try:
                run_verification_team(output_dir, self.project_context)
                logger.info("Agent team verification completed successfully")
                
                # Créer un fichier de vérification complète pour l'interface utilisateur
                verification_file = os.path.join(output_dir, "verification_complete.txt")
                with open(verification_file, 'w') as f:
                    f.write("Project successfully verified and improved by the AI agent team")
                    
            except Exception as e:
                logger.error(f"Error during agent team verification: {str(e)}")
                logger.exception("Agent verification exception")
        else:
            logger.info("Agent team verification skipped - disabled by user")
        
        logger.info("Project validation completed")
    
    def _generate_code(self, output_path: str, architecture: Dict[str, Any]) -> None:
        """Generate application code based on architecture"""
        logger.info("Starting code generation...")
        
        file_manager = FileSystemManager()
        files_to_generate = file_manager.create_project_structure(output_path, architecture)
        
        # Créer un répertoire pour JavaScript si aucun fichier JS n'est prévu
        js_dir = os.path.join(output_path, 'js')
        if not os.path.exists(js_dir):
            os.makedirs(js_dir, exist_ok=True)
            # Ajouter un fichier JS vide pour les animations
            files_to_generate.append({
                "path": "js/animations.js",
                "type": "javascript",
                "purpose": "JavaScript animations for UI enhancement"
            })
        
        total_files = len(files_to_generate)
        logger.info(f"Generating {total_files} files...")
        
        for index, file_spec in enumerate(files_to_generate):
            try:
                file_path = file_spec.get("path", "")
                file_purpose = file_spec.get("purpose", "")
                file_content = ""
                
                if not file_path:
                    continue
                
                # Enrichir le contexte du projet avec la structure des fichiers
                enriched_context = ContextEnricher.enrich_generation_context(
                    self.project_context, 
                    output_path
                )
                
                logger.info(f"Generating file {index+1}/{total_files}: {file_path}")
                
                # Génération basée sur le type de fichier
                if file_path.endswith((".py", ".js", ".html", ".css")):
                    file_content = self._api_client.generate_code(
                        file_spec, 
                        enriched_context
                    )
                # ...existing code...
            except Exception as e:
                logger.error(f"Error generating file {file_path}: {str(e)}")
                logger.exception("File generation exception")
    
    def generate(self, output_path: str) -> bool:
        """Generate the complete application"""
        logger.info(f"Starting generation in {output_path}...")
        self._output_path = output_path  # Stocker le chemin de sortie
        
        try:
            self._parse_user_prompt()
            logger.info("User prompt parsed successfully")
            
            self._architecture = self._design_architecture()
            logger.info("Architecture designed successfully")
            
            if self._requirements_spec.get('is_sample_json', False):
                self._database_schema = self._design_json_data()
            else:
                self._database_schema = self._design_database_schema()
            logger.info("Database schema designed successfully")
            
            self._api_spec = self._design_api()
            logger.info("API designed successfully")
            
            # Ajouter le répertoire de sortie au contexte du projet
            self._project_context_with_output = self.project_context.copy()
            self._project_context_with_output['output_dir'] = output_path
            
            # Adapter l'architecture au framework
            self._architecture = adjust_architecture_for_framework(
                self._architecture,
                self._requirements_spec
            )
            
            self._generate_code(output_path, self._architecture)
            logger.info("Code generation completed successfully")
            
            self.validate_generated_project(output_path)
            logger.info("Project validation completed")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during generation: {str(e)}")
            logger.exception("Generation exception")
            return False

    def _generate_code_batch(self, output_path: str, architecture: Dict[str, Any]) -> None:
        """Generate application code in batches based on architecture"""
        logger.info("Starting batch code generation...")
        
        file_manager = FileSystemManager()
        files_to_generate = file_manager.create_project_structure(output_path, architecture)
        
        # Créer un répertoire pour JavaScript si aucun fichier JS n'est prévu
        js_dir = os.path.join(output_path, 'js')
        if not os.path.exists(js_dir):
            os.makedirs(js_dir, exist_ok=True)
            # Ajouter un fichier JS vide pour les animations
            files_to_generate.append({
                "path": "js/animations.js",
                "type": "javascript",
                "purpose": "JavaScript animations for UI enhancement"
            })
        
        total_files = len(files_to_generate)
        logger.info(f"Preparing to generate {total_files} files in batches...")
        
        # Enrichir le contexte du projet avec la structure des fichiers
        enriched_context = ContextEnricher.enrich_generation_context(
            self.project_context, 
            output_path
        )
        
        # Classifier les fichiers par type
        backend_files = []
        frontend_files = []
        config_files = []
        
        for file_spec in files_to_generate:
            file_path = file_spec.get("path", "")
            file_type = file_spec.get("type", "").lower()
            file_purpose = file_spec.get("purpose", "").lower()
            
            if not file_path:
                continue
                
            if file_path.endswith(("package.json", "requirements.txt", ".env", "Dockerfile", "docker-compose.yml", 
                                  "README.md", ".gitignore")):
                config_files.append(file_spec)
            elif file_path.endswith((".html", ".css", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte")) or \
                 "frontend" in file_path.lower() or "ui" in file_purpose or "client" in file_purpose:
                frontend_files.append(file_spec)
            else:
                backend_files.append(file_spec)
        
        # Générer les fichiers de configuration individuellement
        for file_spec in config_files:
            try:
                file_path = file_spec.get("path", "")
                logger.info(f"Generating config file: {file_path}")
                
                if file_path.endswith("package.json") or file_path.endswith("requirements.txt"):
                    file_type = "package.json" if file_path.endswith("package.json") else "requirements.txt"
                    file_structure = ContextEnricher._get_project_structure(output_path)
                    file_content = self._api_client.generate_project_file(
                        file_type,
                        enriched_context,
                        file_structure
                    )
                else:
                    file_content = self._api_client.generate_code(
                        file_spec, 
                        enriched_context
                    )
                
                file_manager.write_code_to_file(output_path, file_path, file_content)
            except Exception as e:
                logger.error(f"Error generating config file {file_path}: {str(e)}")
        
        # Générer les fichiers backend en une seule requête
        if backend_files:
            logger.info(f"Generating {len(backend_files)} backend files in a single request...")
            try:
                backend_files_content = generate_multiple_files(
                    self._api_client,
                    backend_files,
                    enriched_context,
                    "backend"
                )
                
                if backend_files_content:
                    written_files = write_multiple_files(output_path, backend_files_content)
                    logger.info(f"Successfully generated {len(written_files)} backend files")
                else:
                    logger.warning("No backend files were generated in batch mode, falling back to individual generation")
                    self._generate_files_individually(output_path, backend_files, enriched_context)
            except Exception as e:
                logger.error(f"Error in batch backend generation: {str(e)}")
                logger.info("Falling back to individual generation for backend files")
                self._generate_files_individually(output_path, backend_files, enriched_context)
        
        # Générer les fichiers frontend en une seule requête
        if frontend_files:
            logger.info(f"Generating {len(frontend_files)} frontend files in a single request...")
            try:
                frontend_files_content = generate_multiple_files(
                    self._api_client,
                    frontend_files,
                    enriched_context,
                    "frontend"
                )
                
                if frontend_files_content:
                    written_files = write_multiple_files(output_path, frontend_files_content)
                    logger.info(f"Successfully generated {len(written_files)} frontend files")
                else:
                    logger.warning("No frontend files were generated in batch mode, falling back to individual generation")
                    self._generate_files_individually(output_path, frontend_files, enriched_context)
            except Exception as e:
                logger.error(f"Error in batch frontend generation: {str(e)}")
                logger.info("Falling back to individual generation for frontend files")
                self._generate_files_individually(output_path, frontend_files, enriched_context)
    
    def _generate_files_individually(self, files_to_generate, generated_files, output_path, enriched_context):
        """Générer les fichiers un par un"""
        file_manager = FileSystemManager()
        total_files = len(files_to_generate)
        
        logger.info(f"Generating {total_files} files individually...")
        
        for index, file_spec in enumerate(files_to_generate):
            try:
                file_path = file_spec.get("path", "")
                
                if not file_path:
                    continue
                
                logger.info(f"Generating file {index+1}/{total_files}: {file_path}")
                
                if file_path.endswith('.css'):
                    print(f"Using specialized CSS Designer for {file_path}")
                    file_content = self._api_client.call_agent(
                        CSS_DESIGNER_PROMPT,
                        json.dumps({
                            "file": file_spec,
                            "project_context": enriched_context
                        }),
                        max_tokens=4000
                    )
                else:
                    file_content = self._api_client.generate_code(file_spec, enriched_context)
                
                absolute_path = self.file_manager.write_code_to_file(output_path, file_path, file_content)
                generated_files.append({
                    "path": file_path,
                    "absolute_path": absolute_path,
                    "spec": file_spec
                })
            except Exception as e:
                print(f"Error generating file {file_path}: {str(e)}")
    
    def generate_app(self, output_path: str) -> str:
        """Generate a complete application based on requirements"""
        # ...existing code...
        
        # Remplacer l'appel à _generate_code par _generate_code_batch
        self._generate_code_batch(output_path, self._architecture)
        
        # ...existing code...
