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
Génère des scripts de démarrage (start.bat, start.sh) à partir du contenu du README.md
"""
import os
import json
import logging
from pathlib import Path
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
