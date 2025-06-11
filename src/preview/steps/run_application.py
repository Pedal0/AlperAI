"""
Exécute l'application générée en utilisant une liste de commandes structurées fournies par l'IA.
"""
from pathlib import Path
import json
import re # Ensure re is imported
import asyncio
# import subprocess # No longer directly used for Popen, replaced by asyncio.subprocess
import platform # Added platform import
import os # Keep os import for environ, pathsep, etc.
import logging # Ensure logging is imported
import time # Keep for time.sleep if any remains, or remove if fully async

# Add this at the beginning of your script or relevant module
if platform.system() == "Windows":
    # ProactorEventLoop is required for subprocess pipes on Windows with asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from src.api.openrouter_api import get_openrouter_completion # Added import
from src.utils.prompt_loader import get_agent_prompt

logger = logging.getLogger(__name__)

# Regex for port detection
SERVE_OUTPUT_REGEX = re.compile(r"https?://[a-zA-Z0-9.-]+:(\d{4,5})")  # New regex for common server outputs

PORT_REGEX_1 = re.compile(
    r"""\b(?:port|address|listening on|host|server at|endpoint)\b\s*[:=]?\s*(?:(?:[a-zA-Z0-9.-]+|\[[^\]]+\]):)?(\d{4,5})\b""",  # Corrected word boundaries and bracket matching
    re.IGNORECASE
)
PORT_REGEX_2 = re.compile(
    r"""(?:https?://)?(?:[a-zA-Z0-9.-]+|\[[^\]]+\]):(\d{4,5})\b""",  # Corrected word boundaries and bracket matching
    re.IGNORECASE
)

def extract_port_from_line(line: str) -> int | None:
    """Extracts a port number from a log line using predefined regexes."""
    # Attempt to match common "serve" like output first
    # e.g., "INFO  Accepting connections at http://localhost:3000"
    # or "   Local: http://localhost:3000"
    match_serve = SERVE_OUTPUT_REGEX.search(line)
    if match_serve:
        port_str = match_serve.group(1)
        try:
            port = int(port_str)
            if 1024 <= port <= 65535:
                logger.info(f"Port {port} detected by SERVE_OUTPUT_REGEX from line: {line}")
                return port
        except ValueError:
            pass # Fall through if parsing fails

    # Then try existing regexes
    match1 = PORT_REGEX_1.search(line)
    port_str = None
    if match1:
        port_str = match1.group(1)
    else:
        match = PORT_REGEX_2.search(line)
        if match:
            port_str = match.group(1)
        else:
            return None
    
    if port_str:
        try:
            port = int(port_str)
            if 1024 <= port <= 65535: # Standard port range check
                return port
        except ValueError:
            pass
    return None

def extract_url_and_port_from_line(line: str):
    """
    Extracts a (url, port) tuple from a log line using regexes.
    Returns (url, port) if found, else (None, None).
    Converts IPv6 format to localhost for better browser compatibility.
    """
    # Try to match a URL with port, including IPv6 brackets
    match_serve = re.search(r"(https?://(?:[a-zA-Z0-9.-]+|\[[^\]]+\]):(\d{4,5}))", line)
    if match_serve:
        url = match_serve.group(1)
        port_str = match_serve.group(2)
        try:
            port = int(port_str)
            if 1024 <= port <= 65535:
                # Convert IPv6 format to localhost for better browser compatibility
                if "[::]" in url or "[::1]" in url or "0.0.0.0" in url:
                    url = f"http://localhost:{port}"
                    logger.info(f"Converted IPv6/wildcard URL to localhost format: {url} (port {port}) from line: {line}")
                else:
                    logger.info(f"URL {url} and port {port} detected from line: {line}")
                return url, port
        except ValueError:
            pass
    
    # Additional pattern for Python's http.server IPv6 format: "http://[::]:8000"
    ipv6_match = re.search(r"http://\[::\]:(\d{4,5})", line)
    if ipv6_match:
        port_str = ipv6_match.group(1)
        try:
            port = int(port_str)
            if 1024 <= port <= 65535:
                url = f"http://localhost:{port}"
                logger.info(f"Converted IPv6 URL to localhost format: {url} (port {port}) from line: {line}")
                return url, port
        except ValueError:
            pass
    # Fallback: try to extract just the port from 'port XXXX' or similar
    match_port = re.search(r"port[\s:=]+(\d{4,5})", line, re.IGNORECASE)
    if match_port:
        port_str = match_port.group(1)
        try:
            port = int(port_str)
            if 1024 <= port <= 65535:
                # Construct a default URL if possible
                url = f"http://localhost:{port}"
                logger.info(f"Port {port} detected from 'port' pattern in line: {line}")
                return url, port
        except ValueError:
            pass
    # Fallback: try to extract just the port with existing regexes
    match1 = PORT_REGEX_1.search(line)
    port_str = None
    if match1:
        port_str = match1.group(1)
    else:
        match = PORT_REGEX_2.search(line)
        if match:
            port_str = match.group(1)
        else:
            return None, None
    if port_str:
        try:
            port = int(port_str)
            if 1024 <= port <= 65535:
                return None, port
        except ValueError:
            pass
    return None, None

async def _read_stream_and_find_port(stream_reader: asyncio.StreamReader, log_callback, port_found_event: asyncio.Event, found_port_ref: list):
    """Helper to read a stream, log, and extract port."""
    while not stream_reader.at_eof():
        try:
            line_bytes = await stream_reader.readline()
            if not line_bytes:
                break
            line = line_bytes.decode(errors='ignore').strip()
            if line: # Avoid logging empty lines
                log_callback(line) # Log to PreviewManager via the provided callback
                if not port_found_event.is_set(): # Only search for port if not already found
                    port = extract_port_from_line(line)
                    if port:
                        logger.info(f"Port {port} detected in application logs: {line}")
                        if not found_port_ref: # Ensure list is empty before appending
                             found_port_ref.append(port)
                        port_found_event.set() # Signal that port is found
        except asyncio.CancelledError:
            logger.debug("Stream reading task cancelled.")
            break
        except Exception as e:
            logger.error(f"Error reading stream: {e}")
            break # Stop on error

async def _read_stream_and_find_url_and_port(stream_reader: asyncio.StreamReader, log_callback, url_found_event: asyncio.Event, found_url_ref: list):
    """Helper to read a stream, log, and extract url/port."""
    while not stream_reader.at_eof():
        try:
            line_bytes = await stream_reader.readline()
            if not line_bytes:
                break
            line = line_bytes.decode(errors='ignore').strip()
            if line:
                log_callback(line)
                if not url_found_event.is_set():
                    url, port = extract_url_and_port_from_line(line)
                    if url or port:
                        logger.info(f"Detected in logs: url={url}, port={port}, line={line}")
                        if not found_url_ref:
                            found_url_ref.append((url, port))
                        url_found_event.set()
        except asyncio.CancelledError:
            logger.debug("Stream reading task cancelled.")
            break
        except Exception as e:
            logger.error(f"Error reading stream: {e}")
            break

async def monitor_process_output_for_port(
    process: asyncio.subprocess.Process, # MODIFIED: Takes asyncio.subprocess.Process
    duration: int,
    log_callback # This callback should send logs to PreviewManager
) -> int | None:
    """
    Monitors the process's stdout and stderr for a specified duration,
    logs the output, and tries to extract a port number.
    Uses StreamReader objects from asyncio.subprocess.Process.
    """
    if process.stdout is None or process.stderr is None:
        logger.warning("Process stdout or stderr is None, cannot monitor for port.")
        return None

    port_found_event = asyncio.Event()
    found_port_ref = [] # Using a list to pass by reference

    # process.stdout and process.stderr are already StreamReader objects
    stdout_task = asyncio.create_task(_read_stream_and_find_port(process.stdout, log_callback, port_found_event, found_port_ref))
    stderr_task = asyncio.create_task(_read_stream_and_find_port(process.stderr, log_callback, port_found_event, found_port_ref))

    try:
        await asyncio.wait_for(port_found_event.wait(), timeout=duration)
        logger.info(f"Port detection: Port found event triggered within {duration}s.")
    except asyncio.TimeoutError:
        logger.info(f"Port detection: Timed out after {duration}s waiting for port event. Checking collected data.")
    except Exception as e:
        logger.error(f"Port detection: Error during wait: {e}")
    finally:
        if not stdout_task.done():
            stdout_task.cancel()
        if not stderr_task.done():
            stderr_task.cancel()
        
        await asyncio.gather(stdout_task, stderr_task, return_exceptions=True) # Wait for tasks to finish cancellation
        logger.debug("Port monitoring tasks finished.")

    if found_port_ref:
        return found_port_ref[0]
    return None

async def monitor_process_output_for_url_and_port(
    process: asyncio.subprocess.Process,
    duration: int,
    log_callback
) -> tuple[str|None, int|None]:
    """
    Monitors the process's stdout and stderr for a specified duration,
    logs the output, and tries to extract a url and/or port number.
    Returns (url, port) tuple.
    """
    if process.stdout is None or process.stderr is None:
        logger.warning("Process stdout or stderr is None, cannot monitor for url/port.")
        return None, None
    url_found_event = asyncio.Event()
    found_url_ref = []
    stdout_task = asyncio.create_task(_read_stream_and_find_url_and_port(process.stdout, log_callback, url_found_event, found_url_ref))
    stderr_task = asyncio.create_task(_read_stream_and_find_url_and_port(process.stderr, log_callback, url_found_event, found_url_ref))
    try:
        await asyncio.wait_for(url_found_event.wait(), timeout=duration)
        logger.info(f"URL/Port detection: Event triggered within {duration}s.")
    except asyncio.TimeoutError:
        logger.info(f"URL/Port detection: Timed out after {duration}s waiting for event. Checking collected data.")
    except Exception as e:
        logger.error(f"URL/Port detection: Error during wait: {e}")
    finally:
        if not stdout_task.done():
            stdout_task.cancel()
        if not stderr_task.done():
            stderr_task.cancel()
        await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)
        logger.debug("URL/Port monitoring tasks finished.")
    if found_url_ref:
        return found_url_ref[0]
    return None, None

async def get_ai_fix_for_launch_failure(project_dir: str, commands_data: dict, failed_command_index: int, stdout: str, stderr: str, log_callback=print, ai_model: str = None, api_key: str = None):
    """
    Asks AI for help with a failed launch command.
    Returns: {"fixed": bool, "new_commands_data": dict_or_none, "message_to_user": str, "file_patch": {"filename": ..., "content": ...} or None}
    """
    import re
    from pathlib import Path
    import os
    import json

    log_callback(f"AI assistance requested for command: {commands_data['commands'][failed_command_index]}")

    # 1. Tenter d'extraire le nom du fichier fautif depuis stderr
    file_match = re.search(r"([\w\-.]+\.(js|jsx|ts|tsx|py|json|yml|yaml|toml|cfg|ini|sh|bat|php|html|css|scss|md))(:\d+)?", stderr)
    file_content = None
    file_name = None
    if file_match:
        file_name = file_match.group(1)
        file_path = Path(project_dir) / file_name
        if file_path.exists():
            try:
                file_content = file_path.read_text(encoding="utf-8", errors="ignore")
                log_callback(f"Including content of file '{file_name}' in AI prompt for fix.")
            except Exception as e:
                log_callback(f"Could not read file '{file_name}': {e}")
                file_content = None

    # 2. Générer la structure du projet (arborescence)
    def get_project_structure(project_dir: Path, max_depth=2, max_files_per_dir=10):
        structure = []
        for root, dirs, files in os.walk(project_dir):
            depth = root.replace(str(project_dir), '').count(os.sep)
            if depth > max_depth:
                dirs[:] = []
                continue
            indent = "  " * depth
            structure.append(f"{indent}{Path(root).name}/")
            for i, f_name in enumerate(sorted(files)):
                if i >= max_files_per_dir:
                    structure.append(f"{indent}  ... (and more files)")
                    break
                structure.append(f"{indent}  {f_name}")
        return "\n".join(structure)
    structure_str = get_project_structure(Path(project_dir))    # 3. Construire le prompt enrichi avec le prompt loader
    file_content_section = ""
    fix_instructions = ""
    
    if file_name and file_content:
        file_content_section = get_agent_prompt(
            'launch_failure_agent',
            'file_content_section_with_file',
            file_name=file_name,
            file_content=file_content
        )
        fix_instructions = get_agent_prompt(
            'launch_failure_agent',
            'fix_instructions_with_file'
        )
    else:
        fix_instructions = get_agent_prompt(
            'launch_failure_agent',
            'fix_instructions_without_file'
        )
    
    prompt = get_agent_prompt(
        'launch_failure_agent',
        'launch_failure_fix_prompt',
        project_dir=project_dir,
        failed_command=commands_data['commands'][failed_command_index],
        stdout=stdout,
        stderr=stderr,
        project_structure=structure_str,
        file_content_section=file_content_section,
        fix_instructions=fix_instructions
    )

    ai_response_str = None
    try:
        log_callback("Attempting to call AI for a fix...")
        # Use the provided ai_model, fallback to a default if None
        model_to_use = ai_model if ai_model else "openai/gpt-4.1-nano"
        ai_response_str = await get_openrouter_completion(prompt, model_name=model_to_use, api_key=api_key)
        log_callback("AI call completed.")
    except Exception as e:
        log_callback(f"Error calling AI API: {e}")
        return {
            "fixed": False,
            "new_commands_data": None,
            "message_to_user": f"AI assistance failed due to an API error: {e}",
            "file_patch": None
        }

    if ai_response_str is None:
        return {
            "fixed": False,
            "new_commands_data": None,
            "message_to_user": "AI assistance failed: No response from AI.",
            "file_patch": None
        }

    try:
        ai_response = json.loads(ai_response_str)
        if not isinstance(ai_response, dict):
            raise ValueError("AI response is not a dictionary")
        return {
            "fixed": ai_response.get("fixed", False),
            "new_commands_data": ai_response.get("new_commands_data"),
            "message_to_user": ai_response.get("message_to_user", "AI response was not in the expected format."),
            "file_patch": ai_response.get("file_patch")
        }
    except json.JSONDecodeError:
        log_callback("Error decoding AI response.")
        return {
            "fixed": False,
            "new_commands_data": None,
            "message_to_user": "AI assistance failed due to an invalid response format from the AI.",
            "file_patch": None
        }
    except ValueError as e:
        log_callback(f"Error processing AI response: {e}")
        return {
            "fixed": False,
            "new_commands_data": None,
            "message_to_user": f"AI assistance failed due to an error processing the AI response: {e}",
            "file_patch": None
        }


# MODIFIED: Renamed and made async
async def _execute_single_command_async(command_str: str, project_dir: Path, env: dict, log_callback=print) -> asyncio.subprocess.Process:
    """Helper to execute a single command asynchronously and return an asyncio.subprocess.Process."""
    log_callback(f"Executing async: {command_str} in {project_dir}")
    # Use asyncio's subprocess handling
    process = await asyncio.create_subprocess_shell(
        command_str,
        cwd=project_dir,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    return process

# MODIFIED: Renamed to _async and made async
async def run_application_commands_internal_async(
    project_dir_str: str, 
    commands_data: dict, 
    venv_path_str: str = None, 
    log_callback=print, 
    attempt_ai_fix=False,
    ai_model: str = None, # Default is now None, not hardcoded
    api_key: str = None # Added for AI fix
):
    """
    Internal async function to execute a list of commands using asyncio.subprocess.
    commands_data: {"commands": ["cmd1", ...], "env": {"VAR": "val"}}
    Returns: {"success": bool, "message": str, "process": asyncio.subprocess.Process_or_None, "stdout": str, "stderr": str, "original_commands_data": dict}
    'process' is for the last command if it's a running server (asyncio.subprocess.Process).
    stdout/stderr are decoded strings for the failed command or last successful setup command.
    """
    project_dir = Path(project_dir_str)
    current_env = os.environ.copy()
    if 'env' in commands_data and isinstance(commands_data['env'], dict):
        current_env.update(commands_data['env'])

    current_commands_data = commands_data.copy() 

    # Activate virtual environment if venv_path_str is provided
    if venv_path_str:
        venv_path = Path(venv_path_str)
        if venv_path.is_dir():
            log_callback(f"Attempting to activate virtual environment: {venv_path_str}")
            current_env['VIRTUAL_ENV'] = str(venv_path)
            
            if os.name == 'nt': # Windows
                scripts_dir = venv_path / 'Scripts'
            else: # Linux/macOS
                scripts_dir = venv_path / 'bin'
            
            if scripts_dir.is_dir():
                original_path = current_env.get('PATH', '')
                current_env['PATH'] = f"{str(scripts_dir)}{os.pathsep}{original_path}"
                log_callback(f"Venv activated. Updated PATH: {current_env['PATH']}")
            else:
                log_callback(f"Warning: Scripts directory '{scripts_dir}' not found in venv '{venv_path_str}'. PATH not modified for venv activation.")
        else:
            log_callback(f"Warning: Provided venv path '{venv_path_str}' is not a valid directory. Venv not activated.")
    elif "VIRTUAL_ENV" in current_env: # If AI provided VIRTUAL_ENV, try to use it
        venv_path_str_from_ai = current_env["VIRTUAL_ENV"]
        venv_path_ai = Path(venv_path_str_from_ai)
        if venv_path_ai.is_dir():
            log_callback(f"Attempting to activate virtual environment from AI config: {venv_path_str_from_ai}")
            if os.name == 'nt': # Windows
                scripts_dir_ai = venv_path_ai / 'Scripts'
            else: # Linux/macOS
                scripts_dir_ai = venv_path_ai / 'bin'
            
            if scripts_dir_ai.is_dir():
                original_path = current_env.get('PATH', '')
                if str(scripts_dir_ai) not in original_path.split(os.pathsep):
                    current_env['PATH'] = f"{str(scripts_dir_ai)}{os.pathsep}{original_path}"
                    log_callback(f"Venv (from AI config) activated. Updated PATH: {current_env['PATH']}")
                else:
                    log_callback(f"Venv (from AI config) scripts directory already in PATH: {scripts_dir_ai}")
            else:
                log_callback(f"Warning: Scripts directory '{scripts_dir_ai}' not found in venv (from AI config) '{venv_path_str_from_ai}'.")
        else:
            log_callback(f"Warning: VIRTUAL_ENV path from AI ('{venv_path_str_from_ai}') is not a valid directory.")


    command_list = current_commands_data.get("commands", [])
    if not isinstance(command_list, list) or not command_list:
        log_callback("Error: No commands provided or commands format is invalid.")
        return {"success": False, "message": "No commands to execute or invalid format.", "process": None, "stdout": "", "stderr": "No commands provided or invalid format.", "original_commands_data": commands_data}

    if venv_path_str: # This log message can remain
        log_callback(f"Virtual environment path provided: {venv_path_str}. Ensure commands account for this.")

    last_stdout_str, last_stderr_str = "", ""
    ai_fix_attempted_for_command = -1 

    i = 0
    while i < len(command_list):
        command_str = command_list[i]
        if not isinstance(command_str, str):
            log_callback(f"Error: Command at index {i} is not a string.")
            return {"success": False, "message": f"Invalid command format at index {i}.", "process": None, "stdout": last_stdout_str, "stderr": f"Invalid command format at index {i}.", "original_commands_data": commands_data}

        # Add -u for unbuffered output for python http.server
        if command_str.startswith("python -m http.server") and "python -u -m" not in command_str:
            command_str = command_str.replace("python -m", "python -u -m", 1)
            log_callback(f"Modified command for unbuffered output: {command_str}")
        elif command_str.startswith("python3 -m http.server") and "python3 -u -m" not in command_str: # Also handle python3
            command_str = command_str.replace("python3 -m", "python3 -u -m", 1)
            log_callback(f"Modified command for unbuffered output: {command_str}")

        is_last_command = (i == len(command_list) - 1)
        
        process = None # Define process here for broader scope in try/except
        try:
            # Add detection for static project launchers (e.g., 'start', 'open', 'explorer', etc.)
            static_launchers = [
                'start ',  # Windows
                'explorer ',  # Windows
                'open ',  # macOS
                'xdg-open ',  # Linux
            ]
            if is_last_command and any(command_str.lower().startswith(launcher) for launcher in static_launchers):
                log_callback("Le projet est statique. Aucun serveur n'a été lancé, mais le fichier HTML a été ouvert dans le navigateur.")
                return {
                    "success": True,
                    "message": "Projet statique : aucun serveur n'a été lancé, mais le fichier HTML a été ouvert dans le navigateur. Pour la prévisualisation intégrée, lancez un serveur local (ex: 'python -m http.server').",
                    "process": None,
                    "stdout": "",
                    "stderr": "",
                    "original_commands_data": commands_data,
                    "url": None,
                    "port": None
                }
            process = await _execute_single_command_async(command_str, project_dir, current_env, log_callback)

            if not is_last_command: # Setup command, wait for it
                stdout_bytes, stderr_bytes = await process.communicate()
                stdout_str = stdout_bytes.decode(errors='ignore')
                stderr_str = stderr_bytes.decode(errors='ignore')
                last_stdout_str, last_stderr_str = stdout_str, stderr_str
                log_callback(f"STDOUT:\\n{stdout_str}")
                log_callback(f"STDERR:\\n{stderr_str}")

                if process.returncode != 0:
                    error_message = f"Setup command '{command_str}' failed (exit code {process.returncode})."
                    log_callback(error_message)
                    if attempt_ai_fix and ai_fix_attempted_for_command != i:
                        log_callback("Attempting AI fix for setup command...")
                        ai_fix_attempted_for_command = i 
                        ai_result = await get_ai_fix_for_launch_failure(
                            project_dir_str, current_commands_data, i, stdout_str, stderr_str, log_callback, ai_model=ai_model, api_key=api_key
                        )
                        if ai_result.get("fixed") and ai_result.get("new_commands_data"):
                            log_callback(f"AI provided a fix: {ai_result.get('message_to_user')}")
                            if ai_result.get("file_patch"):
                                patch = ai_result.get("file_patch")
                                try:
                                    patched_file_path = project_dir / patch["filename"]
                                    patched_file_path.write_text(patch["content"], encoding="utf-8")
                                    log_callback(f"AI_PATCH_APPLIED: File '{patch['filename']}' patched by AI.")
                                except Exception as e_patch:
                                    log_callback(f"Error applying AI file patch: {e_patch}")

                            current_commands_data = ai_result["new_commands_data"]
                            command_list = current_commands_data.get("commands", [])
                            i = 0 
                            last_stdout_str, last_stderr_str = "", "" 
                            ai_fix_attempted_for_command = -1 
                            continue 
                        else:
                            log_callback(f"AI could not fix the command: {ai_result.get('message_to_user')}")
                            return {"success": False, "message": f"{error_message} {ai_result.get('message_to_user')}", "process": None, "stdout": stdout_str, "stderr": stderr_str, "original_commands_data": commands_data}
                    return {"success": False, "message": error_message, "process": None, "stdout": stdout_str, "stderr": stderr_str, "original_commands_data": commands_data}
                log_callback(f"Setup command '{command_str}' succeeded.")
            else: # Last command (assumed to be the server/application)
                try:
                    # Wait for a short period to see if it fails fast
                    await asyncio.wait_for(process.wait(), timeout=3.0)
                    # If wait() completed, process has terminated
                    stdout_bytes, stderr_bytes = await process.communicate() # Should be quick as it already exited
                    stdout_str = stdout_bytes.decode(errors='ignore')
                    stderr_str = stderr_bytes.decode(errors='ignore')
                    last_stdout_str, last_stderr_str = stdout_str, stderr_str
                    log_callback(f"STDOUT:\\n{stdout_str}")
                    log_callback(f"STDERR:\\n{stderr_str}")
                    exit_code = process.returncode
                    error_message = f"Main command '{command_str}' terminated unexpectedly (exit code {exit_code})."
                    log_callback(error_message)
                    if attempt_ai_fix and ai_fix_attempted_for_command != i:
                        log_callback("Attempting AI fix for main command...")
                        ai_fix_attempted_for_command = i
                        ai_result = await get_ai_fix_for_launch_failure(
                            project_dir_str, current_commands_data, i, stdout_str, stderr_str, log_callback, ai_model=ai_model, api_key=api_key
                        )
                        if ai_result.get("fixed") and ai_result.get("new_commands_data"):
                            log_callback(f"AI provided a fix: {ai_result.get('message_to_user')}")
                            if ai_result.get("file_patch"):
                                patch = ai_result.get("file_patch")
                                try:
                                    patched_file_path = project_dir / patch["filename"]
                                    patched_file_path.write_text(patch["content"], encoding="utf-8")
                                    log_callback(f"AI_PATCH_APPLIED: File '{patch['filename']}' patched by AI.")
                                except Exception as e_patch:
                                    log_callback(f"Error applying AI file patch: {e_patch}")
                            current_commands_data = ai_result["new_commands_data"]
                            command_list = current_commands_data.get("commands", [])
                            i = 0 
                            last_stdout_str, last_stderr_str = "", ""
                            ai_fix_attempted_for_command = -1
                            continue
                        else:
                            log_callback(f"AI could not fix the command: {ai_result.get('message_to_user')}")
                            return {"success": False, "message": f"{error_message} {ai_result.get('message_to_user')}", "process": None, "stdout": stdout_str, "stderr": stderr_str, "original_commands_data": commands_data}
                    return {"success": False, "message": error_message, "process": None, "stdout": stdout_str, "stderr": stderr_str, "original_commands_data": commands_data}
                except asyncio.TimeoutError: # Process is still running after timeout
                    log_callback(f"Main command '{command_str}' is running as a background process.")
                    return {"success": True, "message": f"Main application command '{command_str}' started.", "process": process, "stdout": "", "stderr": "", "original_commands_data": commands_data}
        
        except FileNotFoundError:
            error_message = f"Error: File or command not found for '{command_str}'. Ensure it's installed and in PATH."
            log_callback(error_message)
            last_stderr_str = error_message # Use error_message as stderr for AI
            if attempt_ai_fix and ai_fix_attempted_for_command != i:
                log_callback("Attempting AI fix for FileNotFoundError...")
                ai_fix_attempted_for_command = i
                ai_result = await get_ai_fix_for_launch_failure(
                    project_dir_str, current_commands_data, i, last_stdout_str, last_stderr_str, log_callback, ai_model=ai_model, api_key=api_key
                )
                if ai_result.get("fixed") and ai_result.get("new_commands_data"):
                    log_callback(f"AI provided a fix: {ai_result.get('message_to_user')}")
                    if ai_result.get("file_patch"):
                        patch = ai_result.get("file_patch")
                        try:
                            patched_file_path = project_dir / patch["filename"]
                            patched_file_path.write_text(patch["content"], encoding="utf-8")
                            log_callback(f"AI_PATCH_APPLIED: File '{patch['filename']}' patched by AI.")
                        except Exception as e_patch:
                            log_callback(f"Error applying AI file patch: {e_patch}")
                    current_commands_data = ai_result["new_commands_data"]
                    command_list = current_commands_data.get("commands", [])
                    i = 0 
                    last_stdout_str, last_stderr_str = "", ""
                    ai_fix_attempted_for_command = -1
                    continue
                else:
                    log_callback(f"AI could not fix the command: {ai_result.get('message_to_user')}")
                    return {"success": False, "message": f"{error_message} {ai_result.get('message_to_user')}", "process": None, "stdout": last_stdout_str, "stderr": last_stderr_str, "original_commands_data": commands_data}
            return {"success": False, "message": error_message, "process": None, "stdout": last_stdout_str, "stderr": last_stderr_str, "original_commands_data": commands_data}
        except Exception as e:
            error_message = f"Exception while running command '{command_str}': {str(e)}"
            log_callback(error_message)
            # Try to kill the process if it was started and an error occurred
            if process and process.returncode is None: # Check if process exists and is running
                try:
                    process.kill()
                    await process.wait() # Wait for kill to complete
                except Exception as kill_exc:
                    log_callback(f"Exception during process kill: {kill_exc}")
            
            partial_stdout_str, partial_stderr_str = last_stdout_str, str(e)
            if attempt_ai_fix and ai_fix_attempted_for_command != i:
                log_callback("Attempting AI fix for general exception...")
                ai_fix_attempted_for_command = i
                ai_result = await get_ai_fix_for_launch_failure(
                    project_dir_str, current_commands_data, i, partial_stdout_str, partial_stderr_str, log_callback, ai_model=ai_model, api_key=api_key
                )
                if ai_result.get("fixed") and ai_result.get("new_commands_data"):
                    log_callback(f"AI provided a fix: {ai_result.get('message_to_user')}")
                    if ai_result.get("file_patch"):
                        patch = ai_result.get("file_patch")
                        try:
                            patched_file_path = project_dir / patch["filename"]
                            patched_file_path.write_text(patch["content"], encoding="utf-8")
                            log_callback(f"AI_PATCH_APPLIED: File '{patch['filename']}' patched by AI.")
                        except Exception as e_patch:
                            log_callback(f"Error applying AI file patch: {e_patch}")
                    current_commands_data = ai_result["new_commands_data"]
                    command_list = current_commands_data.get("commands", [])
                    i = 0 
                    last_stdout_str, last_stderr_str = "", ""
                    ai_fix_attempted_for_command = -1
                    continue
                else:
                    log_callback(f"AI could not fix the command: {ai_result.get('message_to_user')}")
                    return {"success": False, "message": f"{error_message} {ai_result.get('message_to_user')}", "process": None, "stdout": partial_stdout_str, "stderr": partial_stderr_str, "original_commands_data": commands_data}
            return {"success": False, "message": error_message, "process": None, "stdout": partial_stdout_str, "stderr": partial_stderr_str, "original_commands_data": commands_data}
        i += 1 # Move to the next command if successful

    log_callback("All commands processed.")
    if not command_list: # Should be caught earlier, but as a safeguard
        return {"success": False, "message": "No commands were executed.", "process": None, "stdout": last_stdout_str, "stderr": last_stderr_str, "original_commands_data": commands_data}
    
    # If loop finishes, it means all commands were setup commands and succeeded, or list was empty after AI fix.
    return {"success": True, "message": "All setup commands completed successfully (no main server command identified as last, or command list became empty).", "process": None, "stdout": last_stdout_str, "stderr": last_stderr_str, "original_commands_data": commands_data}

async def run_application_async_wrapper(
    project_dir_str: str, 
    commands_data_json: str, 
    venv_path_str: str = None, 
    log_callback=print, 
    attempt_ai_fix=True,
    ai_model: str = None, # Default is now None, not hardcoded
    api_key: str = None 
):
    """
    Asynchronous wrapper to handle AI fix attempts for run_application_commands_internal_async.
    Also monitors for url/port in logs if the application starts successfully.
    """
    effective_log_callback = log_callback if log_callback != print else logger.info

    try:
        initial_commands_data = json.loads(commands_data_json)
        if not isinstance(initial_commands_data, dict) or "commands" not in initial_commands_data:
            raise ValueError("Commands data must be a dict with a 'commands' key.")
    except json.JSONDecodeError as e:
        effective_log_callback(f"Error: Invalid JSON format for commands_data: {e}")
        return {"success": False, "message": f"Invalid JSON for commands: {e}", "process": None, "original_commands_data": None, "url": None, "port": None }
    except ValueError as e:
        effective_log_callback(f"Error: Invalid structure for commands_data: {e}")
        return {"success": False, "message": f"Invalid data structure for commands: {e}", "process": None, "original_commands_data": None, "url": None, "port": None}

    effective_log_callback(f"run_application_async_wrapper called for {project_dir_str}, AI fix: {attempt_ai_fix}")

    current_commands_data = initial_commands_data.copy()
    final_result = {} # To store the final outcome

    result = await run_application_commands_internal_async(
        project_dir_str,
        current_commands_data, # Start with initial/current
        venv_path_str,
        effective_log_callback,
        attempt_ai_fix=attempt_ai_fix, # Allow AI fixes
        ai_model=ai_model,
        api_key=api_key
    )

    final_result = result.copy() # Store the latest result

    app_process = result.get("process") # asyncio.subprocess.Process or None
    url_to_return = None
    port_to_return = None

    if result.get("success") and app_process:
        effective_log_callback(f"[{Path(project_dir_str).name}] Main application process started. Monitoring output for url/port for up to 10 seconds...")
        try:
            url, port = await monitor_process_output_for_url_and_port(app_process, 10, effective_log_callback)
            if url:
                effective_log_callback(f"[{Path(project_dir_str).name}] URL {url} detected from application logs.")
                url_to_return = url
            if port:
                effective_log_callback(f"[{Path(project_dir_str).name}] Port {port} detected from application logs.")
                port_to_return = port
            if not url and not port:
                effective_log_callback(f"[{Path(project_dir_str).name}] No specific url/port detected from application logs within monitoring period.")
            final_result["url"] = url_to_return
            final_result["port"] = port_to_return
        except Exception as e_monitor:
            effective_log_callback(f"Error during url/port monitoring: {e_monitor}")
            final_result["success"] = False
            final_result["message"] = f"{final_result.get('message', '')} Error during url/port monitoring: {e_monitor}"
            final_result["url"] = None
            final_result["port"] = None
            if app_process and app_process.returncode is None:
                app_process.kill()
                await app_process.wait()
            final_result["process"] = None
    elif not result.get("success"):
        effective_log_callback(f"[{Path(project_dir_str).name}] Application command execution failed: {result.get('message')}")
        final_result["process"] = None
        final_result["url"] = None
        final_result["port"] = None
    else:
        effective_log_callback(f"[{Path(project_dir_str).name}] Application commands completed, but no running server process returned.")
        final_result["process"] = None
        final_result["url"] = None
        final_result["port"] = None

    return {
        "success": final_result.get("success", False),
        "message": final_result.get("message", "An unknown error occurred."),
        "process": final_result.get("process"),
        "stdout": final_result.get("stdout", ""),
        "stderr": final_result.get("stderr", ""),
        "original_commands_data": initial_commands_data,
        "url": final_result.get("url"),
        "port": final_result.get("port")
    }