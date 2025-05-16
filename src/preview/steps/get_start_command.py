"""
Détermine la commande de démarrage à utiliser selon le type de projet.
"""
import sys
import json
import subprocess
from pathlib import Path
from .detect_project_type import ProjectType
from .find_free_port import find_free_port
from src.preview.steps.detect_project_type import ProjectType

# Determine Windows platform
is_windows = sys.platform.startswith("win")

def _win_fix(cmd):
    if is_windows and cmd and cmd[0] in ("npm", "npx"):
        cmd[0] = cmd[0] + ".cmd"
    return cmd

def get_start_command(project_dir: str, project_type: str, session_id: str = None):
    project_dir = Path(project_dir)
    env = None
    # Determine free port for the generated application
    # Use port >=8000 for static projects, else default starting at 3000
    if project_type == ProjectType.STATIC or (isinstance(project_type, str) and project_type.lower() == 'static'):
        port = find_free_port(start_port=8000)
    else:
        port = find_free_port()    
    if port == 5000:
        port = find_free_port(start_port=5001)
    if session_id:
        from src.preview.preview_manager import session_ports
        session_ports[session_id] = port
        
    # Generate start scripts if they don't exist, using the new function that focuses on README
    from ..handler.generate_start_scripts import generate_start_scripts
    generate_start_scripts(project_dir)
    
    # Custom launch script detection: start.sh for macOS/Linux, start.bat for Windows
    custom_sh = project_dir / 'start.sh'
    custom_bat = project_dir / 'start.bat'
    # On Windows prefer batch script, otherwise bash script
    if is_windows and custom_bat.exists():
        # Run batch file through cmd with port argument
        return ['cmd', '/c', str(custom_bat), str(port)], env
    if custom_sh.exists():
        # Run bash script with port argument
        return ['bash', str(custom_sh), str(port)], env
    if custom_bat.exists():
        return [str(custom_bat), str(port)], env

    if project_type == ProjectType.FLASK or (isinstance(project_type, str) and project_type.lower() == "flask"):
        # Run Flask via project venv Python on script (run.py or app.py)
        if session_id:
            from src.preview.preview_manager import session_ports
            session_ports[session_id] = port
        # Determine Python executable: use project venv if exists
        venv_py = project_dir / 'venv' / ('Scripts' if is_windows else 'bin') / ('python.exe' if is_windows else 'python')
        python_exec = str(venv_py) if venv_py.exists() else sys.executable
        # Locate entry script
        script = None
        for candidate in ['run.py', 'app.py', 'main.py', 'server.py']:
            if (project_dir / candidate).exists():
                script = str(project_dir / candidate)
                break
        if script:
            # Pass port as argument to script
            return [python_exec, script, str(port)], env
        # Fallback: use flask run with venv
        return [python_exec, '-m', 'flask', 'run', '--host', '0.0.0.0', '--port', str(port)], env
    # Streamlit projects: use 'streamlit run'
    elif project_type == "streamlit" or (isinstance(project_type, str) and project_type.lower() == "streamlit"):
        if session_id:
            from src.preview.preview_manager import session_ports
            session_ports[session_id] = port
        # find script
        script = None
        if (project_dir / "app.py").exists():
            script = str(project_dir / "app.py")
        else:
            pyfs = list(project_dir.glob("*.py"))
            if pyfs:
                script = str(pyfs[0])
        if script:
            cmd = ["streamlit", "run", script, "--server.port", str(port)]
            return _win_fix(cmd), env
        else:
            return [sys.executable, str(project_dir)], env
    elif project_type == ProjectType.EXPRESS:
        # Choose port and set environment
        if session_id:
            from src.preview.preview_manager import session_ports
            session_ports[session_id] = port
        import os
        env = os.environ.copy()
        env["PORT"] = str(port)
        # Direct node entrypoint if exists
        for main in ["server.js", "app.js", "index.js"]:
            if (project_dir / main).exists():
                return _win_fix(["node", str(project_dir / main)]), env
        # fallback on npm start if no entrypoint
        return _win_fix(["npm", "start"]), env
    # PHP projects: launch built-in server
    elif project_type == ProjectType.PHP or (isinstance(project_type, str) and project_type.lower() == "php"):
        if session_id is not None:
            from src.preview.preview_manager import session_ports
            session_ports[session_id] = port
        # Serve PHP built-in server
        return ["php", "-S", f"0.0.0.0:{port}", "-t", str(project_dir)], env
    elif project_type in [ProjectType.REACT, ProjectType.VUE, ProjectType.ANGULAR]:
        # Use free port for SPA frameworks
        if session_id:
            from src.preview.preview_manager import session_ports
            session_ports[session_id] = port
        import os
        env = os.environ.copy()
        env["PORT"] = str(port)
        if (project_dir / "package.json").exists():
            try:
                with open(project_dir / "package.json", "r", encoding="utf-8") as f:
                    package_json = json.load(f)
                    scripts = package_json.get("scripts", {})
                    if "start" in scripts:
                        return _win_fix(["npm", "start"]), env
                    elif "dev" in scripts:
                        return _win_fix(["npm", "run", "dev"]), env
                    elif "serve" in scripts:
                        return _win_fix(["npm", "run", "serve"]), env
            except:
                pass
        # Pass PORT env to npm scripts
        return _win_fix(["npm", "start"]), env
    elif project_type == ProjectType.STATIC:
        # Determine directory containing index.html
        serve_dir = project_dir
        for sub in ["public", "src"]:
            if (project_dir / sub / "index.html").exists():
                serve_dir = project_dir / sub
                break
        # If custom scripts available, use npm
        if (project_dir / "package.json").exists():
            try:
                with open(project_dir / "package.json", "r", encoding="utf-8") as f:
                    package_json = json.load(f)
                    scripts = package_json.get("scripts", {})
                    if "start" in scripts:
                        return _win_fix(["npm", "start"]), env
                    elif "dev" in scripts:
                        return _win_fix(["npm", "run", "dev"]), env
                    elif "serve" in scripts:
                        return _win_fix(["npm", "run", "serve"]), env
            except:
                pass
        # Serve via python http.server or npx serve
        if session_id is not None:
            from src.preview.preview_manager import session_ports
            session_ports[session_id] = port
        # Try python handler
        python_exec = sys.executable
        try:
            return [python_exec, "-m", "http.server", str(port), "--directory", str(serve_dir)], env
        except:
            return _win_fix(["npx", "serve", "-s", str(serve_dir), "-p", str(port)]), env
    else:
        if (project_dir / "package.json").exists():
            try:
                with open(project_dir / "package.json", "r", encoding="utf-8") as f:
                    package_json = json.load(f)
                    scripts = package_json.get("scripts", {})
                    if "start" in scripts:
                        return _win_fix(["npm", "start"]), env
                    elif "dev" in scripts:
                        return _win_fix(["npm", "run", "dev"]), env
                    elif "serve" in scripts:
                        return _win_fix(["npm", "run", "serve"]), env
            except Exception:
                return _win_fix(["npm", "start"]), env
        main_py_files = ["app.py", "main.py", "server.py", "run.py"]
        for file in main_py_files:
            if (project_dir / file).exists():
                return [sys.executable, str(project_dir / file)], env
        main_js_files = ["server.js", "app.js", "index.js", "main.js"]
        for file in main_js_files:
            if (project_dir / file).exists():
                return ["node", str(project_dir / file)], env
        if (project_dir / "index.html").exists() or (project_dir / "public" / "index.html").exists():
            return get_start_command(project_dir, ProjectType.STATIC, session_id)
        return _win_fix(["npm", "start"]), env
