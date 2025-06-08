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
Given the project information below, provide SIMPLE and MINIMAL shell commands to set up and run this project.
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
- Keep commands SIMPLE and MINIMAL - prefer short, essential commands only
- NEVER use port 5000 (it's occupied) - use ports like 3000, 8000, 8080, or any other port
- The JSON object must contain two keys:
  1. "commands": A list of strings, where each string is a shell command to be executed in sequence. These commands should cover ONLY the essential steps: installing dependencies (if needed) and starting the application. Keep it to 2-3 commands maximum. Assume the commands will be run from the root of the project directory. If the project runs a server, the last command should be the one that starts the server and keeps running. For static HTML/CSS/JS projects, use simple servers like 'python -m http.server 8000' or 'npx serve -p 3000'. DO NOT create, write, or mention any batch (.bat), shell (.sh), or script files. DO NOT output any file content, only the JSON object as described. DO NOT output any command that creates or writes to a file. DO NOT include any 'cd ...' command, as the working directory is already set correctly.
  2. "env": An optional dictionary of environment variables (string key-value pairs) that might be needed for the commands. Keep this minimal - only include if absolutely necessary. If no specific environment variables are needed, this can be an empty dictionary or omitted.

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

def test_command_generation():
    """Test function for command generation system."""
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Create a dummy project structure for testing
    test_project_dir = Path("./test_project_ai_launch")
    test_project_dir.mkdir(exist_ok=True)
    (test_project_dir / "README.md").write_text("This is a test project.\n\nTo run: \n1. npm install\n2. npm start")
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
                logger.info(f"Contents of {config_file}:\n{f.read()}")
    else:
        logger.error("Test failed.")

    # Cleanup (optional)
    # import shutil
    # shutil.rmtree(test_project_dir)
    
    return success


# Example usage (if run directly, for testing):
if __name__ == '__main__':
    test_command_generation()