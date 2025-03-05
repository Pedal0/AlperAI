import os
import json
import time
import logging
from src.api.api_client import AIAppGeneratorAPI
from src.file_manager.file_manager import FileSystemManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AppGenerator:
    def __init__(self, api_key):
        self.api_client = AIAppGeneratorAPI(api_key)
        self.file_manager = FileSystemManager()
        
    def generate_application(self, user_prompt, output_path, include_tests=False, create_docker=False, add_ci_cd=False):
        print(f"Analyzing requirements from prompt: '{user_prompt[:50]}...'")
        requirements = self.api_client.analyze_requirements(user_prompt)
        if not requirements:
            print("Failed to analyze requirements. Aborting.")
            return False
            
        # Add configurations to requirements
        requirements["generate_tests"] = include_tests
        requirements["create_docker"] = create_docker
        requirements["add_ci_cd"] = add_ci_cd
        
        app_name = requirements.get('app_name', 'application')
        print(f"Designing architecture for {app_name}")
        architecture = self.api_client.design_architecture(requirements)
        if not architecture:
            print("Failed to design architecture. Aborting.")
            logger.error("Architecture design failed - check API response")
            return False
            
        print("Designing database schema")
        database = self.api_client.design_database(requirements, architecture)
        if not database:
            print("Warning: Failed to design database schema. Continuing with limited functionality.")
            database = {"database_type": "none", "schema": {}, "tables": []}
        
        print("Designing API interfaces")
        api_design = self.api_client.design_api(requirements, architecture)
        if not api_design:
            print("Warning: Failed to design API. Continuing with limited functionality.")
            api_design = {"api_type": "none", "endpoints": []}
        
        project_context = {
            "requirements": requirements,
            "architecture": architecture,
            "database": database,
            "api": api_design
        }
        
        os.makedirs(output_path, exist_ok=True)
        with open(os.path.join(output_path, "project_context.json"), "w") as f:
            json.dump(project_context, f, indent=2)
        
        print(f"Creating project structure at {output_path}")
        files_to_generate = self.file_manager.create_project_structure(output_path, architecture)
        
        if not files_to_generate:
            print("Warning: No files to generate based on architecture.")
            return False
            
        print(f"Generating {len(files_to_generate)} files")
        total_files = len(files_to_generate)
        generated_files = 0
        
        for file_spec in files_to_generate:
            file_path = file_spec.get("path", "")
            if not file_path:
                continue
                
            print(f"Generating file: {file_path} ({generated_files + 1}/{total_files})")
            code_content = self.api_client.generate_code(file_spec, project_context)
            
            if code_content:
                self.file_manager.write_code_to_file(output_path, file_path, code_content)
                
                review = self.api_client.code_reviewer(file_path, code_content, file_spec)
                if review and not review.get("pass", True):
                    print(f"Code review failed for {file_path}. Regenerating...")
                    code_content = self.api_client.generate_code(file_spec, project_context)
                    self.file_manager.write_code_to_file(output_path, file_path, code_content)
            else:
                print(f"Warning: Failed to generate content for {file_path}")
                    
            generated_files += 1
            
        dependencies = []
        for dependency in architecture.get("dependencies", []):
            if isinstance(dependency, str):
                dependencies.append(dependency)
            elif isinstance(dependency, dict):
                name = dependency.get("name", "")
                version = dependency.get("version", "")
                if name and version:
                    dependencies.append(f"{name}=={version}")
                elif name:
                    dependencies.append(name)
                    
        self.file_manager.create_requirements_file(output_path, dependencies)
        
        self.file_manager.create_readme(output_path, requirements)
        
        print(f"Application generation complete. Generated {generated_files} files.")
        return True