# Copyright (C) 2025 Perey Alex
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>

"""

Génère les instructions de démarrage à partir du contenu du README.md sous forme de commandes shell dans un objet JSON. Ne jamais créer, mentionner ou utiliser de scripts start.bat ou start.sh.

Génère des scripts de démarrage (start.bat, start.sh) à partir du contenu du README.md

"""
import os
import json
import logging
from pathlib import Path

from src.api.openrouter_api import get_openrouter_completion
import asyncio

logger = logging.getLogger(__name__)

async def get_launch_commands_from_ai(project_dir: Path, readme_content: str, project_structure: str, project_types: list, log_callback=print, api_key: str = None, model_name: str = "openrouter/anthropic/claude-3-haiku"):
    """
    Asks AI for a structured list of setup and run commands for the project.
    Returns: {"commands": ["cmd1", ...], "env": {"VAR": "val"}} or None if failed.
    """
    log_callback(f"Requesting launch commands from AI for project: {project_dir}")

    prompt = f"""
Given the project information below, please provide the necessary shell commands to set up and run this project.
Project Directory: {project_dir}
Project Types: {', '.join(project_types) if project_types else 'Unknown'}

README.md content:
---
{readme_content}
---

Project Structure:
---
{project_structure}
---

IMPORTANT: Your response MUST be a single valid JSON object, WITHOUT any code block markers (no triple backticks, no markdown, no explanations, just the JSON object itself).

STRICT REQUIREMENTS:
- The JSON object must contain two keys:
  1. "commands": A list of strings, where each string is a shell command to be executed in sequence. These commands should cover all necessary steps like installing dependencies and then starting the application. Assume the commands will be run from the root of the project directory. If the project runs a server, the last command should be the one that starts the server and keeps running. For static HTML/CSS/JS projects, ALWAYS provide a real command to launch a local server (for example: 'python -m http.server 8000' or 'npx serve' or 'npx http-server'), NEVER just an echo or instruction to open index.html manually. DO NOT create, write, or mention any batch (.bat), shell (.sh), or script files. DO NOT output any file content, only the JSON object as described. DO NOT output any command that creates or writes to a file (e.g., do not use 'echo ... > start.sh'). DO NOT include any 'cd ...' command, as the working directory is already set correctly. If you suggest a Python server, prefer 'python -m http.server 8000 --bind 127.0.0.1' to ensure local accessibility.
  2. "env": An optional dictionary of environment variables (string key-value pairs) that might be needed for the commands. Example: {{"PORT": "8080", "NODE_ENV": "development"}}. If no specific environment variables are needed, this can be an empty dictionary or omitted.

Example of a valid JSON response:
{{
  "commands": [
    "npm install",
    "npm run build",
    "npm start"
  ],
  "env": {{
    "PORT": "3000"
  }}
}}

If you cannot determine the commands, respond with:
{{
  "commands": [],
  "error": "Could not determine launch commands."
}}
"""

    log_callback(f"Attempting to get launch commands from AI model: {model_name}")
    ai_response_str = None
    try:
        ai_response_str = await get_openrouter_completion(
            prompt,
            model_name=model_name,
            api_key=api_key
        )
        if ai_response_str:
            log_callback(f"AI response received: {ai_response_str[:500]}{'...' if len(ai_response_str) > 500 else ''}") # Log snippet
        else:
            log_callback("AI call did not return a response.")
            ai_response_str = json.dumps({
                "commands": [],
                "error": "AI service failed to provide a response."
            })

    except Exception as e:
        log_callback(f"Error calling AI for launch commands: {e}")
        ai_response_str = json.dumps({
            "commands": [],
            "error": f"Exception during AI call: {str(e)}"
        })
    
    # log_callback(f"AI response: {ai_response_str}") # Full response might be too verbose

    # --- PATCH: Remove code block markers if present in AI response ---
    if ai_response_str and ai_response_str.strip().startswith('```'):
        import re as _re
        ai_response_str = _re.sub(r'^```[a-zA-Z0-9]*\n', '', ai_response_str.strip())
        ai_response_str = _re.sub(r'```$', '', ai_response_str.strip())
    # --- END PATCH ---
    try:
        parsed_response = json.loads(ai_response_str)
        if not isinstance(parsed_response, dict) or "commands" not in parsed_response:
            log_callback(f"Error: AI response is not in the expected format. Response: {ai_response_str}")
            return None
        if parsed_response.get("error"):
            log_callback(f"AI could not determine commands: {parsed_response['error']}")
            return None
        # Ensure env is a dict if present
        if "env" in parsed_response and not isinstance(parsed_response["env"], dict):
            log_callback(f"Warning: 'env' in AI response is not a dictionary. Ignoring. Response: {ai_response_str}")
            parsed_response["env"] = {}

        return parsed_response
    except json.JSONDecodeError as e:
        log_callback(f"Error decoding AI response for launch commands: {e}. Response was: {ai_response_str}")
        return None

def get_project_structure(project_dir: Path, max_depth=2, max_files_per_dir=10):
    """
    Generates a string representation of the project's directory structure.
    """
    structure = []
    for root, dirs, files in os.walk(project_dir):
        depth = root.replace(str(project_dir), '').count(os.sep)
        if depth > max_depth:
            dirs[:] = [] # Don't go deeper
            continue

        indent = "  " * depth
        structure.append(f"{indent}{Path(root).name}/")
        
        # Limit number of files shown per directory
        for i, f_name in enumerate(sorted(files)):
            if i >= max_files_per_dir:
                structure.append(f"{indent}  ... (and more files)")
                break
            structure.append(f"{indent}  {f_name}")
        
        # Limit number of directories shown at current level if too many (optional)
        # if len(dirs) > max_files_per_dir and depth < max_depth: # Example limit
        #     dirs_to_show = sorted(dirs)[:max_files_per_dir]
        #     structure.append(f"{indent}  ... (and more directories)")
        #     dirs[:] = dirs_to_show
            
    return "\\n".join(structure)

async def generate_launch_config_from_ai(project_dir_str: str, log_callback=print, api_key: str = None, model_name: str = None):
    """
    Generates a launch configuration (list of commands and env vars) for a project
    by querying an AI based on README.md and project structure.
    Saves the configuration to 'launch_commands.json' in the project directory.
    
    Args:
        project_dir_str (str): Path to the project directory.
        log_callback (function): Callback for logging.
    
    Returns:
        dict: The launch configuration from AI, or None if failed.
              Example: {"commands": ["cmd1"], "env": {"VAR": "val"}}
    """
    project_dir = Path(project_dir_str)
    readme_path = project_dir / "README.md"
    launch_config_path = project_dir / "launch_commands.json"

    readme_content = ""
    if readme_path.exists():
        try:
            readme_content = readme_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            log_callback(f"Warning: Could not read README.md: {e}")
    else:
        log_callback("No README.md found in the project directory.")

    # Basic project type detection (can be enhanced)
    # This is a simplified version of what detect_project_type might do.
    project_types = []
    if (project_dir / 'package.json').exists():
        project_types.append('node')
    if (project_dir / 'requirements.txt').exists() or (project_dir / 'Pipfile').exists() or list(project_dir.glob('*.py')):
        project_types.append('python')
    if list(project_dir.glob('*.html')) and not project_types: # If only HTML files, likely static
        project_types.append('static')
    
    # Get project structure
    structure_str = get_project_structure(project_dir)
    log_callback(f"Project structure for AI:\\n{structure_str}")

    # Get launch commands from AI
    # This needs to be called from an async context or run in an event loop.
    launch_config = await get_launch_commands_from_ai(
        project_dir, readme_content, structure_str, project_types, log_callback,
        api_key=api_key, model_name=model_name # Pass through api_key and model_name
    )

    if launch_config and launch_config.get("commands"):
        try:
            with open(launch_config_path, 'w', encoding='utf-8') as f:
                json.dump(launch_config, f, indent=2)
            log_callback(f"Launch configuration saved to {launch_config_path}")
            return launch_config
        except Exception as e:
            log_callback(f"Error saving launch configuration to {launch_config_path}: {e}")
            return None # Or return launch_config if saving is optional but commands were received
    else:
        log_callback("Failed to get valid launch commands from AI.")
        # Optionally, create an empty or error-indicating launch_commands.json
        error_config = {"commands": [], "env": {}, "error": "Failed to generate launch commands via AI."}
        try:
            with open(launch_config_path, 'w', encoding='utf-8') as f:
                json.dump(error_config, f, indent=2)
            log_callback(f"Empty/error launch configuration saved to {launch_config_path}")
        except Exception as e:
            log_callback(f"Error saving empty/error launch configuration: {e}")
        return None

# The old generate_start_scripts function is replaced.
# If you need a synchronous wrapper for generate_launch_config_from_ai:
def generate_start_scripts(project_dir, api_key=None, model_name="openrouter/anthropic/claude-3-haiku"): # api_key and model_name are used to configure the AI call
    """
    Synchronous wrapper to generate launch configuration from AI.
    This function will run the async part in a new event loop.
    """
    logger.info(f"Attempting to generate AI launch configuration for {project_dir}")
    try:
        loop = asyncio.get_running_loop()
        # If there's a running loop, we might be in an async context already.
        # However, calling loop.run_until_complete on a task that's part of the *current* loop's execution
        # can lead to issues. It's safer to create a new task if we are already in an async func.
        # For simplicity here, we assume this sync wrapper is called from a sync context.
        # If called from async, the caller should 'await generate_launch_config_from_ai(...)' directly.
        if loop.is_running(): # This check might be too simplistic for nested loops or different threads
             logger.warning("generate_start_scripts (sync) called from a running event loop. This might lead to issues. Consider awaiting generate_launch_config_from_ai directly.")
             # Fallback or error, as run_until_complete cannot be used this way easily.
             # One option is to schedule it and block, but that's complex.
             pass # Allow it to proceed, but it's a code smell.


    except RuntimeError: # No current event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    config = None
    try:
        # Pass api_key and model_name to the async function
        config = loop.run_until_complete(generate_launch_config_from_ai(project_dir, logger.info, api_key=api_key, model_name=model_name))
    finally:
        # If we created a new loop, we should close it.
        # If we got an existing loop, we should not close it here.
        # This logic is tricky. A common pattern is to ensure set_event_loop(None) if a new one was made.
        # For now, if a new loop was created and is not running, close it.
        # This might need more robust handling depending on the application structure.
        if not asyncio.get_event_loop().is_running() and 'loop' in locals() and loop is not asyncio.get_event_loop():
             # Check if 'loop' was the one we set and it's different from a potentially new global one.
             # This is still a bit fragile.
             pass # Avoid closing if unsure, could affect other parts of the app.


    if config and config.get("commands"):
        logger.info(f"AI Launch configuration generated successfully for {project_dir}")
        return True # Indicates success (config file was written or commands obtained)
    else:
        logger.error(f"Failed to generate AI launch configuration for {project_dir}")
        return False


# --- Removed old helper functions like _convert_to_batch, _add_default_setup_commands_sh, etc. ---
# --- as the AI is now responsible for generating the full command list. ---

# Example usage (if run directly, for testing):
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    # Create a dummy project structure for testing
    test_project_dir = Path("./test_project_ai_launch")
    test_project_dir.mkdir(exist_ok=True)
    (test_project_dir / "README.md").write_text("This is a test project.\\n\\nTo run: \\n1. npm install\\n2. npm start")
    (test_project_dir / "package.json").write_text('{ "name": "test", "scripts": { "start": "node index.js" } }')
    (test_project_dir / "index.js").write_text('console.log("Hello from test project!");')

    logger.info(f"Testing AI launch config generation for: {test_project_dir.resolve()}")
    
    # Since generate_launch_config_from_ai is async, we need an event loop to run it.
    # The generate_start_scripts function handles this.
    success = generate_start_scripts(str(test_project_dir.resolve()))

    if success:
        logger.info("Test completed. Check launch_commands.json in test_project_ai_launch directory.")
        # You can also load and print the json file here
        config_file = test_project_dir / "launch_commands.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                logger.info(f"Contents of {config_file}:\\n{f.read()}")
    else:
        logger.error("Test failed.")

    # Cleanup (optional)
    # import shutil
    # shutil.rmtree(test_project_dir)
from ..preview_utils import parse_readme_instructions
from ..handler.detect_project_type import detect_project_type

logger = logging.getLogger(__name__)

def generate_start_scripts(project_dir, api_key=None, model_name=None):
    """
    Génère des scripts de démarrage pour un projet en se basant sur le README.md
    
    Args:
        project_dir (str): Chemin du projet
        api_key (str, optional): Clé API pour l'IA si une génération avancée est nécessaire
        model_name (str, optional): Nom du modèle à utiliser si une génération avancée est nécessaire
    
    Returns:
        bool: True si les scripts ont été générés avec succès
    """
    project_dir = Path(project_dir)
    readme_path = project_dir / "README.md"
    
    # Scripts paths
    start_sh_path = project_dir / "start.sh"
    start_bat_path = project_dir / "start.bat"    # Always regenerate for static sites to ensure they work correctly
    project_info = detect_project_type(project_dir)
    project_types = project_info['types']
    
    # Force generation for static sites or if any of the scripts is missing/empty
    if 'static' in project_types or any(file.name.endswith('.html') for file in project_dir.glob('*.html')):
        logger.info(f"Static site detected in {project_dir}, generating optimized start scripts")
        # Continue with generation
    elif (start_sh_path.exists() and start_sh_path.stat().st_size > 50 and
          start_bat_path.exists() and start_bat_path.stat().st_size > 50):
        # Both scripts exist and have content - skip generation
        logger.info(f"Start scripts already exist and have content in {project_dir}")
        return True
    
    # Get project type information
    project_info = detect_project_type(project_dir)
    project_types = project_info['types']
    
    # Default scripts for common port 8080
    default_sh = '#!/bin/bash\n\n# Default server script generated for preview\nPORT="${1:-8080}"\n\n'
    default_bat = '@echo off\n\nrem Default server script generated for preview\nset PORT=%1\nif "%PORT%"=="" set PORT=8080\n\n'
    
    if readme_path.exists():
        # Parse README for instructions
        instructions = parse_readme_instructions(readme_path)
        setup_cmds = instructions.get('setup_commands', [])
        run_cmds = instructions.get('run_commands', [])
        
        # Create sh script
        with open(start_sh_path, 'w', encoding='utf-8') as f:
            f.write(default_sh)
            
            # Add setup commands from README
            if setup_cmds:
                f.write("# Setup commands from README\n")
                for cmd in setup_cmds:
                    f.write(f"{cmd}\n")
                f.write("\n")
            
            # Add run commands, with port configuration if possible
            if run_cmds:
                f.write("# Run commands from README\n")
                # Try to add port configuration if applicable
                has_port_cmd = False
                for cmd in run_cmds:
                    # Check if we can inject PORT parameter
                    modified_cmd = cmd
                    if 'python ' in cmd:
                        modified_cmd = f"{cmd} --port $PORT"
                    elif 'flask ' in cmd:
                        modified_cmd = f"{cmd} --port=$PORT"
                    elif 'node ' in cmd:
                        modified_cmd = f"PORT=$PORT {cmd}"
                    elif 'npm ' in cmd:
                        modified_cmd = f"PORT=$PORT {cmd}"
                    
                    f.write(f"{modified_cmd}\n")
                    has_port_cmd = True
                    # Only use first run command
                    break
                
                if not has_port_cmd:
                    # Default by project type
                    _add_default_run_commands_sh(f, project_types, project_dir)
            else:
                # No run commands found, use defaults by project type
                _add_default_run_commands_sh(f, project_types, project_dir)
        
        # Create bat script
        with open(start_bat_path, 'w', encoding='utf-8') as f:
            f.write(default_bat)
            
            # Add setup commands from README
            if setup_cmds:
                f.write("rem Setup commands from README\n")
                for cmd in setup_cmds:
                    # Convert bash commands to batch where possible
                    bat_cmd = _convert_to_batch(cmd)
                    f.write(f"{bat_cmd}\n")
                f.write("\n")
            
            # Add run commands, with port configuration if possible
            if run_cmds:
                f.write("rem Run commands from README\n")
                # Try to add port configuration if applicable
                has_port_cmd = False
                for cmd in run_cmds:
                    # Check if we can inject PORT parameter
                    bat_cmd = _convert_to_batch(cmd)
                    modified_cmd = bat_cmd
                    
                    if 'python ' in bat_cmd:
                        modified_cmd = f"{bat_cmd} --port %PORT%"
                    elif 'flask ' in bat_cmd:
                        modified_cmd = f"{bat_cmd} --port=%PORT%"
                    elif 'node ' in bat_cmd:
                        modified_cmd = f"set PORT=%PORT% && {bat_cmd}"
                    elif 'npm ' in bat_cmd:
                        modified_cmd = f"set PORT=%PORT% && {bat_cmd}"
                    
                    f.write(f"{modified_cmd}\n")
                    has_port_cmd = True
                    # Only use first run command
                    break
                
                if not has_port_cmd:
                    # Default by project type
                    _add_default_run_commands_bat(f, project_types, project_dir)
            else:
                # No run commands found, use defaults by project type
                _add_default_run_commands_bat(f, project_types, project_dir)
    else:
        # No README, generate scripts based on project type
        with open(start_sh_path, 'w', encoding='utf-8') as f:
            f.write(default_sh)
            _add_default_setup_commands_sh(f, project_types, project_dir)
            _add_default_run_commands_sh(f, project_types, project_dir)
        
        with open(start_bat_path, 'w', encoding='utf-8') as f:
            f.write(default_bat)
            _add_default_setup_commands_bat(f, project_types, project_dir)
            _add_default_run_commands_bat(f, project_types, project_dir)
    
    # Make shell script executable
    try:
        import stat
        st = os.stat(start_sh_path)
        os.chmod(start_sh_path, st.st_mode | stat.S_IEXEC)
    except Exception as e:
        logger.warning(f"Failed to make start.sh executable: {e}")
    
    logger.info(f"Start scripts generated successfully in {project_dir}")
    return True

def _convert_to_batch(bash_cmd):
    """Convert bash command to batch command"""
    cmd = bash_cmd
    
    # Common conversions
    if cmd.startswith('pip '):
        # pip commands are mostly the same
        return cmd
    elif cmd.startswith('python '):
        # python commands are mostly the same
        return cmd
    elif cmd.startswith('./'):
        # ./script.sh -> script.bat
        cmd = cmd[2:].replace('.sh', '.bat')
    elif 'export ' in cmd:
        # export VAR=value -> set VAR=value
        cmd = cmd.replace('export ', 'set ').replace('=', '=')
    
    return cmd

def _add_default_setup_commands_sh(file, project_types, project_dir):
    """Add default setup commands for bash script"""
    file.write("# Default setup commands\n")
    
    # Python projects
    if any(t in project_types for t in ['python', 'flask', 'streamlit']):
        if (project_dir / 'requirements.txt').exists():
            file.write("pip install -r requirements.txt\n")
        elif (project_dir / 'Pipfile').exists():
            file.write("pip install pipenv && pipenv install --system\n")
    
    # Node projects
    if any(t in project_types for t in ['node', 'express', 'react', 'vue', 'angular']):
        if (project_dir / 'package.json').exists():
            file.write("npm install\n")
    
    file.write("\n")

def _add_default_setup_commands_bat(file, project_types, project_dir):
    """Add default setup commands for batch script"""
    file.write("rem Default setup commands\n")
    
    # Python projects
    if any(t in project_types for t in ['python', 'flask', 'streamlit']):
        if (project_dir / 'requirements.txt').exists():
            file.write("pip install -r requirements.txt\n")
        elif (project_dir / 'Pipfile').exists():
            file.write("pip install pipenv && pipenv install --system\n")
    
    # Node projects
    if any(t in project_types for t in ['node', 'express', 'react', 'vue', 'angular']):
        if (project_dir / 'package.json').exists():
            file.write("npm install\n")
    
    file.write("\n")

def _add_default_run_commands_sh(file, project_types, project_dir):
    """Add default run commands for bash script"""
    file.write("# Default run command\n")
    
    # Flask apps
    if 'flask' in project_types:
        main_files = ["app.py", "main.py", "server.py", "run.py"]
        for fname in main_files:
            if (project_dir / fname).exists():
                file.write(f"python {fname} --port=$PORT\n")
                return
        file.write("python -m flask run --host=0.0.0.0 --port=$PORT\n")
    
    # Streamlit apps
    elif 'streamlit' in project_types:
        main_files = ["app.py", "main.py", "streamlit_app.py"]
        for fname in main_files:
            if (project_dir / fname).exists():
                file.write(f"streamlit run {fname} --server.port=$PORT\n")
                return
        file.write("streamlit run app.py --server.port=$PORT\n")
    
    # Node/Express apps
    elif any(t in project_types for t in ['node', 'express']):
        if (project_dir / 'package.json').exists():
            file.write("PORT=$PORT npm start\n")
        elif (project_dir / 'server.js').exists():
            file.write("PORT=$PORT node server.js\n")
        elif (project_dir / 'app.js').exists():
            file.write("PORT=$PORT node app.js\n")
        elif (project_dir / 'index.js').exists():
            file.write("PORT=$PORT node index.js\n")
        else:
            file.write("PORT=$PORT npm start\n")
    
    # React/Vue/Angular apps
    elif any(t in project_types for t in ['react', 'vue', 'angular']):
        file.write("PORT=$PORT npm start\n")
    
    # Python apps
    elif 'python' in project_types:
        main_files = ["app.py", "main.py", "server.py", "run.py"]
        for fname in main_files:
            if (project_dir / fname).exists():
                file.write(f"python {fname} --port=$PORT\n")
                return
        file.write("python app.py --port=$PORT\n")
    
    # Static sites - most common case for simple HTML projects
    elif 'static' in project_types or any(file.name.endswith('.html') for file in project_dir.glob('*.html')):
        # Use Python's built-in HTTP server for static sites
        file.write("cd \"$(dirname $0)\"\n")  # Make sure we're in the right directory
        file.write("python3 -m http.server $PORT 2>/dev/null || python -m http.server $PORT\n")
    
    # PHP sites
    elif 'php' in project_types:
        file.write("php -S 0.0.0.0:$PORT\n")
    
    # Default fallback
    else:
        # Fallback to Python's HTTP server as most versatile option
        file.write("cd \"$(dirname $0)\"\n")  # Make sure we're in the right directory
        file.write("echo \"Using default HTTP server on port $PORT\"\n")
        file.write("python3 -m http.server $PORT 2>/dev/null || python -m http.server $PORT\n")

def _add_default_run_commands_bat(file, project_types, project_dir):
    """Add default run commands for batch script"""
    file.write("rem Default run command\n")
    
    # Flask apps
    if 'flask' in project_types:
        main_files = ["app.py", "main.py", "server.py", "run.py"]
        for fname in main_files:
            if (project_dir / fname).exists():
                file.write(f"python {fname} --port=%PORT%\n")
                return
        file.write("python -m flask run --host=0.0.0.0 --port=%PORT%\n")
    
    # Streamlit apps
    elif 'streamlit' in project_types:
        main_files = ["app.py", "main.py", "streamlit_app.py"]
        for fname in main_files:
            if (project_dir / fname).exists():
                file.write(f"streamlit run {fname} --server.port=%PORT%\n")
                return
        file.write("streamlit run app.py --server.port=%PORT%\n")
    
    # Node/Express apps
    elif any(t in project_types for t in ['node', 'express']):
        if (project_dir / 'package.json').exists():
            file.write("set PORT=%PORT%\nnpm start\n")
        elif (project_dir / 'server.js').exists():
            file.write("set PORT=%PORT%\nnode server.js\n")
        elif (project_dir / 'app.js').exists():
            file.write("set PORT=%PORT%\nnode app.js\n")
        elif (project_dir / 'index.js').exists():
            file.write("set PORT=%PORT%\nnode index.js\n")
        else:
            file.write("set PORT=%PORT%\nnpm start\n")
    
    # React/Vue/Angular apps
    elif any(t in project_types for t in ['react', 'vue', 'angular']):
        file.write("set PORT=%PORT%\nnpm start\n")
    
    # Python apps
    elif 'python' in project_types:
        main_files = ["app.py", "main.py", "server.py", "run.py"]
        for fname in main_files:
            if (project_dir / fname).exists():
                file.write(f"python {fname} --port=%PORT%\n")
                return
        file.write("python app.py --port=%PORT%\n")
    
    # Static sites - most common case for simple HTML projects
    elif 'static' in project_types or any(file.name.endswith('.html') for file in project_dir.glob('*.html')):
        # Use current directory for Python's HTTP server
        file.write("cd %~dp0\n")  # Change to batch file directory
        file.write("python -m http.server %PORT%\n")
    
    # PHP sites
    elif 'php' in project_types:
        file.write("php -S 0.0.0.0:%PORT%\n")
    
    # Default fallback
    else:
        # Fallback to Python's HTTP server as most versatile option
        file.write("cd %~dp0\n")  # Change to batch file directory
        file.write("echo Using default HTTP server on port %PORT%\n")
        file.write("python -m http.server %PORT%\n")

