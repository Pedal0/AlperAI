import os
import json
import time
import logging
from src.api.api_client import AIAppGeneratorAPI
from src.file_manager.file_manager import FileSystemManager
from src.config import FILE_SIGNATURE_EXTRACTOR_PROMPT, CROSS_FILE_REVIEWER_PROMPT, MAX_TOKENS_DEFAULT, MAX_TOKENS_LARGE

logging.basicConfig(level=logging.INFO)
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
        if not hasattr(self, '_requirements_spec') or self._requirements_spec is None:
            return {}

        return {
            "requirements": self._requirements_spec,
            "architecture": self._architecture,
            "database": self._database_schema,
            "api": self._api_spec
        }

    def _build_requirements_spec(self, user_prompt, include_tests=False, create_docker=False, add_ci_cd=False, app_name=None):
        """Analyze user prompt to build requirements specification"""
        print(f"Analyzing requirements from prompt: '{user_prompt[:50]}...'")

        requirements = self._api_client.analyze_requirements(user_prompt)

        if not requirements:
            raise Exception("Failed to analyze requirements")

        # Override app name if provided
        if app_name and isinstance(requirements, dict):
            requirements["app_name"] = app_name

        # Add generation options to requirements
        requirements["generate_tests"] = include_tests
        requirements["create_docker"] = create_docker
        requirements["add_ci_cd"] = add_ci_cd

        return requirements

    def _design_architecture(self):
        """Design the application architecture based on requirements"""
        if not self._requirements_spec:
            raise Exception("Requirements specification is missing")

        architecture = self._api_client.design_architecture(
            self._requirements_spec)

        if not architecture:
            raise Exception("Failed to design architecture")

        # Ensure architecture is a dictionary
        if not isinstance(architecture, dict):
            logger.error(
                f"Architecture design returned invalid format: {type(architecture)}")
            logger.error(f"Architecture content: {architecture[:200]}..." if isinstance(
                architecture, str) else str(architecture))
            raise Exception(
                "Architecture design returned invalid format (not a dict)")

        return architecture

    def _design_database(self):
        """Design database schema if required by the application"""
        if not self._requirements_spec or not self._architecture:
            raise Exception("Requirements or architecture is missing")

        database_schema = self._api_client.design_database(
            self._requirements_spec, self._architecture)

        if not database_schema:
            logger.warning(
                "Failed to design database schema, continuing without it")
            return {}

        return database_schema

    def _design_api(self):
        """Design API if required by the application"""
        if not self._requirements_spec or not self._architecture:
            raise Exception("Requirements or architecture is missing")

        api_spec = self._api_client.design_api(
            self._requirements_spec, self._architecture)

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
            "database": getattr(self, "_database_design", None),
            "api": getattr(self, "_api_design", None),
            "file": file_spec
        }

        code = self._api_client.generate_code(file_spec, project_context)

        if not code:
            raise Exception(
                f"Failed to generate code for {file_spec.get('path')}")

        return code

    def generate_application(self, user_prompt, output_path, include_tests=False, create_docker=False, add_ci_cd=False, app_name=None):
        """Generate a complete application based on user's description"""
        print(f"Starting application generation for: {output_path}")

        # Build requirements specification
        self._requirements_spec = self._build_requirements_spec(
            user_prompt,
            include_tests=include_tests,
            create_docker=create_docker,
            add_ci_cd=add_ci_cd,
            app_name=app_name  # Pass app_name to _build_requirements_spec
        )

        # Ensure requirements is a dictionary
        if not isinstance(self._requirements_spec, dict):
            logger.error(
                f"Requirements returned invalid format: {type(self._requirements_spec)}")
            raise Exception(
                "Requirements analysis returned invalid format (not a dict)")

        # Design architecture based on requirements
        app_name = self._requirements_spec.get('app_name', 'Unnamed App')
        print(f"Designing architecture for {app_name}")
        self._architecture = self._design_architecture()

        # Design database if required
        if isinstance(self._requirements_spec.get('components', []), list) and any('database' in comp.get('type', '')
                                                                                   for comp in self._requirements_spec.get('components', []) if isinstance(comp, dict)):
            print("Designing database schema")
            self._database_schema = self._design_database()
        else:
            self._database_schema = {}

        # Design API if required
        if isinstance(self._requirements_spec.get('components', []), list) and any('api' in comp.get('type', '')
                                                                                   for comp in self._requirements_spec.get('components', []) if isinstance(comp, dict)):
            print("Designing API interfaces")
            self._api_spec = self._design_api()
        else:
            self._api_spec = {}

        # Step 1: Generate project structure first
        print(f"Creating project structure at {output_path}")
        files_to_generate = self.file_manager.create_project_structure(
            output_path, self._architecture)
        print(f"Generating {len(files_to_generate)} files")

        # Step 2: Generate all files without validation first
        generated_files = []
        file_counter = 0

        for file_spec in files_to_generate:
            file_counter += 1
            file_path = file_spec.get("path", "")
            if not file_path:
                continue

            print(
                f"Generating file: {file_path} ({file_counter}/{len(files_to_generate)})")
            file_code = self._generate_file_code(file_spec)
            absolute_path = self.file_manager.write_code_to_file(
                output_path, file_path, file_code)
            generated_files.append({
                "path": file_path,
                "absolute_path": absolute_path,
                "spec": file_spec
            })

        # Step 3: Generate appropriate dependency files
        print("Generating appropriate dependency files based on technology stack")
        tech_stack = self._requirements_spec.get('technical_stack', {})
        language = tech_stack.get('language', '').lower(
        ) if isinstance(tech_stack, dict) else ''

        # Handle dependencies based on technology stack
        dependencies = self._architecture.get('dependencies', [])

        if language in ['javascript', 'typescript', 'node', 'react', 'vue', 'angular']:
            self._create_package_json(output_path, dependencies)
        else:
            filtered_deps = []
            for dep in dependencies:
                if isinstance(dep, dict):
                    if dep.get('type', '') != 'node':
                        dep_str = dep.get('name', '')
                        if dep.get('version'):
                            dep_str += f"=={dep.get('version')}"
                        filtered_deps.append(dep_str)
                else:
                    filtered_deps.append(dep)
            self.file_manager.create_requirements_file(
                output_path, filtered_deps)

        # Step 4: Create README with detailed instructions
        self.file_manager.create_readme(output_path, self._requirements_spec)

        # Step 5: Extract file signatures for cross-validation
        print("Extracting file signatures for comprehensive validation")
        file_signatures = {}
        all_file_contents = {}

        for file_info in generated_files:
            if file_info["path"].endswith(('.py', '.js', '.ts', '.jsx', '.tsx')):
                try:
                    with open(file_info["absolute_path"], 'r', encoding='utf-8') as f:
                        file_content = f.read()
                        all_file_contents[file_info["path"]] = file_content
                except Exception as e:
                    print(
                        f"Warning: Could not read {file_info['path']}: {str(e)}")

        # Step 6: Use the API client directly for cross-file validation
        if all_file_contents:
            print("Performing cross-file validation on all files")
            try:
                results = self._api_client.cross_file_code_reviewer(
                    all_file_contents, self.project_context)

                for file_path, fixed_content in results.items():
                    if fixed_content != "PARFAIT":
                        print(f"Fixing issues in {file_path}")
                        self.file_manager.write_code_to_file(
                            output_path, file_path, fixed_content)
            except Exception as e:
                print(f"Warning: Cross-file validation failed: {str(e)}")

        print(f"Project successfully generated at {output_path}")
        return output_path

    def _create_package_json(self, output_path, dependencies):
        """Create a package.json file for JavaScript/Node.js projects"""
        import json

        node_deps = {}

        for dep in dependencies:
            name = ""
            version = "latest"

            if isinstance(dep, str):
                if "@" in dep:
                    parts = dep.split("@")
                    name = parts[0]
                    version = parts[1]
                else:
                    name = dep
            elif isinstance(dep, dict):
                name = dep.get('name', '')
                version = dep.get('version', 'latest')

            if name and name not in ["python", "pip"] and not name.startswith("python-"):
                node_deps[name] = version

        package_json = {
            "name": self._requirements_spec.get('app_name', 'generated-app').lower().replace(' ', '-'),
            "version": "1.0.0",
            "description": self._requirements_spec.get('app_description', ''),
            "main": "index.js",
            "scripts": {
                "start": "node index.js"
            },
            "dependencies": node_deps,
            "devDependencies": {}
        }

        # Handle frontend frameworks specifically
        if any(fw.lower() in node_deps for fw in ['react', 'vue', 'angular']):
            if 'react' in node_deps:
                package_json["scripts"]["start"] = "react-scripts start"
                package_json["scripts"]["build"] = "react-scripts build"
                package_json["scripts"]["test"] = "react-scripts test"
            elif 'vue' in node_deps:
                package_json["scripts"]["serve"] = "vue-cli-service serve"
                package_json["scripts"]["build"] = "vue-cli-service build"
            elif 'angular' in node_deps:
                package_json["scripts"]["start"] = "ng serve"
                package_json["scripts"]["build"] = "ng build"
        else:
            # Look for entry files
            entry_files = []
            for f in self._architecture.get('files', []):
                if isinstance(f, dict) and f.get('path', '').endswith(('.js', '.ts')):
                    purpose = f.get('purpose', '').lower()
                    if 'entry' in purpose or 'main' in purpose:
                        entry_files.append(f.get('path', ''))

            if entry_files:
                package_json["scripts"]["start"] = f"node {entry_files[0]}"

        with open(os.path.join(output_path, "package.json"), 'w', encoding='utf-8') as f:
            json.dump(package_json, f, indent=2)
