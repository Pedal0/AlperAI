import os
import json
import logging
from typing import Dict, Any, List, Optional

from src.api.client import AIAppGeneratorAPI
from src.file_manager.file_manager import FileSystemManager
from src.generators.framework.framework_adapter import adjust_architecture_for_framework

logger = logging.getLogger(__name__)

class AppGenerator:
    def __init__(self, api_key):
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
            
            if ((language == 'python' and framework in ['flask', 'django']) or
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
        
        code = self._api_client.generate_code(file_spec, project_context)
        
        if not code:
            raise Exception(f"Failed to generate code for {file_spec.get('path')}")
            
        return code
        
    def generate_application(self, user_prompt, output_path, include_tests=False, create_docker=False, add_ci_cd=False, use_sample_json=False):
        """Generate a complete application based on user prompt"""
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
        print(f"Generating {len(files_to_generate)} files")
        
        generated_files = []
        file_counter = 0
        
        for file_spec in files_to_generate:
            file_counter += 1
            file_path = file_spec.get("path", "")
            if not file_path:
                continue
                
            print(f"Generating file: {file_path} ({file_counter}/{len(files_to_generate)})")
            file_code = self._generate_file_code(file_spec)
            absolute_path = self.file_manager.write_code_to_file(output_path, file_path, file_code)
            generated_files.append({
                "path": file_path,
                "absolute_path": absolute_path,
                "spec": file_spec
            })
        
        file_structure = []
        for root, dirs, files in os.walk(output_path):
            rel_root = os.path.relpath(root, output_path)
            if rel_root == ".":
                rel_root = ""
            for file in files:
                file_path = os.path.join(rel_root, file) if rel_root else file
                file_structure.append(file_path)
        
        print("Generating configuration and documentation files")
        
        tech_stack = self._requirements_spec.get('technical_stack', {})
        language = tech_stack.get('language', '').lower() if isinstance(tech_stack, dict) else ''
        
        if language not in ['javascript', 'typescript', 'node', 'react', 'vue', 'angular']:
            print("Generating requirements.txt")
            requirements_content = self._api_client.generate_project_file(
                'requirements.txt',
                self.project_context,
                file_structure
            )
            with open(os.path.join(output_path, "requirements.txt"), 'w', encoding='utf-8') as f:
                f.write(requirements_content)
        
        if language in ['javascript', 'typescript', 'node', 'react', 'vue', 'angular']:
            print("Generating package.json")
            package_json_content = self._api_client.generate_project_file(
                'package.json',
                self.project_context,
                file_structure
            )
            with open(os.path.join(output_path, "package.json"), 'w', encoding='utf-8') as f:
                f.write(package_json_content)
        
        print("Generating README.md")
        readme_content = self._api_client.generate_project_file(
            'README.md',
            self.project_context,
            file_structure
        )
        with open(os.path.join(output_path, "README.md"), 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        print("Extracting file signatures for comprehensive validation")
        all_file_contents = {}
        
        for file_info in generated_files:
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
                
                for file_path, fixed_content in results.items():
                    if fixed_content != "PARFAIT":
                        print(f"Fixing issues in {file_path}")
                        self.file_manager.write_code_to_file(output_path, file_path, fixed_content)
            except Exception as e:
                print(f"Warning: Cross-file validation failed: {str(e)}")
        
        print(f"Project successfully generated at {output_path}")
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
