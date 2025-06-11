"""
Démarre la prévisualisation de l'application générée.
"""
import time
import subprocess
import threading
import os
from src.preview.handler.detect_project_type import detect_project_type
from src.preview.handler.prepare_and_launch_project import prepare_and_launch_project_async as prepare_and_launch_project
from src.preview.steps.get_start_command import get_start_command
from src.preview.steps.get_app_url import get_app_url
from src.preview.steps.log_entry import log_entry
from src.preview.steps.improve_readme import improve_readme_for_preview
from src.utils.prompt_loader import get_agent_prompt

def start_preview(project_dir: str, session_id: str, running_processes=None, process_logs=None, session_ports=None, already_patched=False, ai_model=None, api_key=None):
    if running_processes is None or process_logs is None or session_ports is None:
        from src.preview.preview_manager import running_processes, process_logs, session_ports
    if session_id in running_processes:
        from src.preview.preview_manager import stop_preview
        stop_preview(session_id)
    try:
        process_logs[session_id] = []
        log_entry(session_id, "INFO", f"Démarrage de la prévisualisation pour le projet: {project_dir}")
        
        # Améliorer le README si nécessaire pour s'assurer qu'il contient des instructions détaillées
        from src.preview.steps.improve_readme import improve_readme_for_preview
        improve_readme_for_preview(project_dir)
        
        # When calling prepare_and_launch_project, pass ai_model and api_key
        success, message = prepare_and_launch_project(project_dir, ai_model=ai_model, api_key=api_key)
        log_entry(session_id, "INFO" if success else "ERROR", message)
        if not success:
            if already_patched:
                log_entry(session_id, "ERROR", "L'auto-correction IA a échoué. Impossible de démarrer l'application après correction automatique.")
                return False, "L'auto-correction IA a échoué. Impossible de démarrer l'application après correction automatique.", {"project_type": None}
            # --- AI PATCH SUGGESTION LOGIC ---
            import re, json
            from pathlib import Path
            from src.api.openrouter_api import get_openrouter_completion
            # Try to extract a filename from the error message
            file_match = re.search(r"([\w\-.]+\.(js|ts|py|json|jsx|tsx|css|html|conf|cfg|ini|sh|bat))", message)
            file_content = None
            file_path = None
            if file_match:
                file_path = Path(project_dir) / file_match.group(1)
                if file_path.exists():
                    try:
                        file_content = file_path.read_text(encoding="utf-8", errors="ignore")
                    except Exception:
                        file_content = None
            # Get project structure
            def get_project_structure(project_dir, max_depth=2, max_files_per_dir=10):
                structure = []
                for root, dirs, files in os.walk(project_dir):
                    depth = root.replace(str(project_dir), '').count(os.sep)
                    if depth > max_depth:
                        dirs[:] = []
                        continue
                    indent = "  " * depth
                    structure.append(f"{Path(root).name}/")
                    for i, f_name in enumerate(sorted(files)):
                        if i >= max_files_per_dir:
                            structure.append(f"{indent}  ... (and more files)")
                            break
                        structure.append(f"{indent}  {f_name}")
                return "\n".join(structure)
            structure_str = get_project_structure(project_dir)
            # Try to get the model used for generation from launch_commands.json
            model_name = None
            launch_config_path = Path(project_dir) / "launch_commands.json"
            if launch_config_path.exists():
                try:
                    with open(launch_config_path, "r", encoding="utf-8") as f:
                        launch_config = json.load(f)
                    if isinstance(launch_config, dict) and "model" in launch_config and launch_config["model"]:
                        model_name = launch_config["model"]
                except Exception:
                    pass            # Compose AI prompt using prompt loader
            file_content_section = ""
            if file_path and file_content:
                file_content_section = f"\nHere is the FULL content of the blocking file ({file_path.name}):\n---\n{file_content}\n---\n"
            
            ai_prompt = get_agent_prompt(
                'auto_patch_agent',
                'auto_patch_prompt',
                error_message=message,
                file_content_section=file_content_section,
                project_structure=structure_str
            )
            # Call the AI
            try:
                import asyncio
                ai_response = asyncio.run(get_openrouter_completion(ai_prompt, model_name=model_name))
                if ai_response:
                    log_entry(session_id, "AI", f"AI patch suggestion for error: {message}\n---\n{ai_response}")
                    # --- AUTO PATCH LOGIC ---
                    patched = False
                    new_content = None
                    # Always expect a code block (```) with the full file content
                    code_block = re.search(r"```[a-zA-Z0-9]*\n([\s\S]+?)```", ai_response)
                    if code_block and file_path:
                        new_content = code_block.group(1).strip()
                        try:
                            file_path.write_text(new_content, encoding="utf-8")
                            # Log structuré spécial pour le frontend
                            log_entry(session_id, "AI_PATCH_APPLIED", json.dumps({
                                "file": file_path.name,
                                "patch_excerpt": new_content[:500] + ("..." if len(new_content) > 500 else "")
                            }))
                            log_entry(session_id, "AI", f"Auto-patch applied to {file_path.name} (full rewrite). Relance de la prévisualisation...")
                            patched = True
                        except Exception as e:
                            log_entry(session_id, "ERROR", f"Failed to apply AI patch to {file_path.name}: {e}")
                    if patched:
                        # Relancer la preview automatiquement après patch (mais une seule fois)
                        retry_result = start_preview(project_dir, session_id, running_processes, process_logs, session_ports, already_patched=True, ai_model=ai_model, api_key=api_key)
                        if retry_result and retry_result[0]:
                            return retry_result
                        else:
                            log_entry(session_id, "ERROR", "L'auto-correction IA a échoué. Impossible de démarrer l'application après correction automatique.")
                            return False, "L'auto-correction IA a échoué. Impossible de démarrer l'application après correction automatique.", {"project_type": None}
            except Exception as e:
                log_entry(session_id, "ERROR", f"AI patch suggestion failed: {e}")
            return False, message, {"project_type": None}
        # Détecter le type de projet (pour Flask, React, etc.)
        detected = detect_project_type(project_dir)
        types = detected.get('types', [])
        # Choix du type de projet pour la commande de démarrage
        if 'flask' in types:
            project_type = 'flask'
        elif 'express' in types:
            project_type = 'express'
        elif 'php' in types:
            project_type = 'php'
        elif 'streamlit' in types:
            project_type = 'streamlit'
        elif 'react' in types:
            project_type = 'react'
        elif 'vue' in types:
            project_type = 'vue'
        elif 'angular' in types:
            project_type = 'angular'
        elif 'node' in types:
            project_type = 'express'
        elif 'static' in types:
            project_type = 'static'
        else:
            project_type = None        
        command, env = get_start_command(project_dir, project_type, session_id)
        log_entry(session_id, "INFO", f"Commande de démarrage: {' '.join(command)}")
        
        try:
            process = subprocess.Popen(
                command,
                cwd=project_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                bufsize=1,
                universal_newlines=True
            )
        except Exception as e:
            log_entry(session_id, "ERROR", f"Erreur lors du lancement du processus: {str(e)}")
            return False, f"Erreur lors du lancement du processus: {str(e)}", {"project_type": None}
        running_processes[session_id] = {
            "process": process,
            "project_dir": project_dir,
            "project_type": project_type,
            "command": command,
            "start_time": time.time()
        }
        def read_output(stream, log_type):
            try:
                while True:
                    # Use readline instead of iteration to better control the reading process
                    if stream.closed:
                        break
                    
                    try:
                        line = stream.readline()
                        if not line:  # Empty string indicates EOF
                            break
                        
                        log_entry(session_id, log_type, line.strip())
                    except (IOError, ValueError) as e:
                        # Handle read errors individually without breaking the loop
                        log_entry(session_id, "ERROR", f"Stream read error: {str(e)}")
                        break
            except Exception as e:
                log_entry(session_id, "ERROR", f"Stream processing error: {str(e)}")
            finally:
                # Always try to close in finally block to ensure it happens
                try:
                    if stream and not stream.closed:
                        stream.close()
                except Exception:
                    pass  # Ignore errors when closing
        stdout_thread = threading.Thread(target=read_output, args=(process.stdout, "INFO"))
        stderr_thread = threading.Thread(target=read_output, args=(process.stderr, "ERROR"))
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        stdout_thread.start()
        stderr_thread.start()
        # Wait for application startup depending on framework
        wait_time = 2
        if project_type in ('react', 'vue', 'angular'):
            wait_time = 10  # allow build/startup time for SPA frameworks
        elif project_type == 'flask':
            wait_time = 5  # extra time for Flask apps
        elif project_type == 'streamlit':
            wait_time = 5  # extra time for Streamlit
        elif project_type == 'express' or project_type == 'php':
            wait_time = 3
        time.sleep(wait_time)
        if process.poll() is not None:
            return_code = process.poll()
            log_entry(session_id, "ERROR", f"Le processus s'est terminé avec le code: {return_code}")
            
            # Safely read remaining stderr
            try:
                if process.stderr and not process.stderr.closed:
                    remaining_stderr = process.stderr.read()
                    if remaining_stderr:
                        log_entry(session_id, "ERROR", remaining_stderr)
            except Exception as e:
                log_entry(session_id, "ERROR", f"Error reading stderr: {str(e)}")
            
            if session_id in running_processes:
                del running_processes[session_id]
            
            return False, f"Échec du démarrage du processus (code {return_code})", {
                "project_type": None,
                "logs": process_logs.get(session_id, [])
            }
        app_url = get_app_url(None, session_id)
        return True, "Application démarrée avec succès", {
            "project_type": project_type,
            "url": app_url,
            "logs": process_logs.get(session_id, []),
            "pid": process.pid
        }
    except Exception as e:
        from src.preview.preview_manager import logger
        logger.error(f"Erreur lors du démarrage de la prévisualisation: {str(e)}")
        log_entry(session_id, "ERROR", f"Erreur: {str(e)}")
        return False, f"Erreur: {str(e)}", {
            "logs": process_logs.get(session_id, [])
        }