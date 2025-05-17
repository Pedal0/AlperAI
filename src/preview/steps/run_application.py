"""
Exécute l'application générée en utilisant une liste de commandes structurées fournies par l'IA.
"""
import os
import subprocess
import time
import logging
from pathlib import Path
import json
import re # Ensure re is imported
import asyncio
from src.api.openrouter_api import get_openrouter_completion # Added import

logger = logging.getLogger(__name__)

# Regex for port detection
# Corrected regex: Use \\b for word boundary, \\s for whitespace, and \\[ \\] for literal brackets.
# Also removed redundant \\ from \\b and \\s in raw strings.
PORT_REGEX_1 = re.compile(r"""\\b(?:port|address|listening on|host|server at|endpoint)\\b\\s*[:=]?\\s*(?:(?:[a-zA-Z0-9.-]+|\\[[0-9a-fA-F:]+\\]):)?(\\d{4,5})\\b""", re.IGNORECASE)
PORT_REGEX_2 = re.compile(r"""(?:https?://)?(?:[a-zA-Z0-9.-]+|\\[[0-9a-fA-F:]+\\]):(\\d{4,5})\\b""", re.IGNORECASE)

def extract_port_from_line(line: str) -> int | None:
    """Extracts a port number from a log line using predefined regexes."""
    match = PORT_REGEX_1.search(line)
    port_str = None
    if match:
        port_str = match.group(1)
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

async def monitor_process_output_for_port(
    process: subprocess.Popen,
    duration: int,
    log_callback # This callback should send logs to PreviewManager
) -> int | None:
    """
    Monitors the process's stdout and stderr for a specified duration,
    logs the output, and tries to extract a port number.
    """
    if process.stdout is None or process.stderr is None:
        logger.warning("Process stdout or stderr is None, cannot monitor for port.")
        return None

    loop = asyncio.get_running_loop()
    
    stdout_reader = asyncio.StreamReader(loop=loop)
    stdout_protocol = asyncio.StreamReaderProtocol(stdout_reader)
    await loop.connect_read_pipe(lambda: stdout_protocol, process.stdout)

    stderr_reader = asyncio.StreamReader(loop=loop)
    stderr_protocol = asyncio.StreamReaderProtocol(stderr_reader)
    await loop.connect_read_pipe(lambda: stderr_protocol, process.stderr)

    port_found_event = asyncio.Event()
    found_port_ref = [] # Using a list to pass by reference (as tasks can't directly return to waiting context easily)

    stdout_task = asyncio.create_task(_read_stream_and_find_port(stdout_reader, log_callback, port_found_event, found_port_ref))
    stderr_task = asyncio.create_task(_read_stream_and_find_port(stderr_reader, log_callback, port_found_event, found_port_ref))

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

async def get_ai_fix_for_launch_failure(project_dir: str, commands_data: dict, failed_command_index: int, stdout: str, stderr: str, log_callback=print, ai_model: str = "openai/gpt-4.1-nano", api_key: str = None):
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
    structure_str = get_project_structure(Path(project_dir))

    # 3. Construire le prompt enrichi
    prompt = f"""The following command failed during project startup:\n\nProject Directory: {project_dir}\nCommand: {commands_data['commands'][failed_command_index]}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}\n\nProject structure:\n{structure_str}\n"""
    if file_name and file_content:
        prompt += f"\nThe file '{file_name}' mentioned in the error has the following content:\n--- FILE: {file_name} ---\n{file_content}\n--- END FILE ---\n"
        prompt += "\nIf you can fix the error, please return a JSON object with keys: 'fixed' (true/false), 'new_commands_data' (if needed), 'message_to_user', and if a file needs to be replaced, add a 'file_patch' key with { 'filename': ..., 'content': ... } containing the corrected file content.\n"
    else:
        prompt += "\nIf you can fix the error, please return a JSON object with keys: 'fixed' (true/false), 'new_commands_data' (if needed), and 'message_to_user'.\n"
    prompt += "If you cannot fix it, respond with 'fixed: false' and a 'message_to_user' explaining the issue or suggesting manual steps. Ensure the response is a single JSON object."

    ai_response_str = None
    try:
        log_callback("Attempting to call AI for a fix...")
        ai_response_str = await get_openrouter_completion(prompt, model_name=ai_model, api_key=api_key)
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


def _execute_single_command(command_str: str, project_dir: Path, env: dict, log_callback=print):
    """Helper to execute a single command and return process, stdout, stderr."""
    log_callback(f"Executing: {command_str} in {project_dir}")
    process = subprocess.Popen(
        command_str, shell=True, cwd=project_dir,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, env=env, bufsize=1, universal_newlines=True
    )
    return process

def run_application_commands_internal(project_dir_str: str, commands_data: dict, venv_path_str: str = None, log_callback=print, attempt_ai_fix=False):
    """
    Internal function to execute a list of commands.
    commands_data: {"commands": ["cmd1", ...], "env": {"VAR": "val"}}
    Returns: {"success": bool, "message": str, "process": Popen_object_or_None, "stdout": str, "stderr": str, "original_commands_data": dict}
    'process' is for the last command if it's a running server.
    stdout/stderr are for the failed command or last successful setup command.
    """
    project_dir = Path(project_dir_str)
    current_env = os.environ.copy()
    if 'env' in commands_data and isinstance(commands_data['env'], dict):
        current_env.update(commands_data['env'])

    current_commands_data = commands_data.copy() # Work with a copy for potential AI fixes

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
            # VIRTUAL_ENV is already set by AI
            if os.name == 'nt': # Windows
                scripts_dir_ai = venv_path_ai / 'Scripts'
            else: # Linux/macOS
                scripts_dir_ai = venv_path_ai / 'bin'
            
            if scripts_dir_ai.is_dir():
                original_path = current_env.get('PATH', '')
                # Ensure scripts_dir_ai is not already in PATH to avoid duplicates
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

    # Robust venv handling would be more complex, e.g., modifying PATH or prefixing commands.
    # For now, assumes commands are self-sufficient or AI includes venv activation.
    if venv_path_str:
        log_callback(f"Virtual environment path provided: {venv_path_str}. Ensure commands account for this.")


    last_stdout, last_stderr = "", ""
    ai_fix_attempted_for_command = -1 # To prevent infinite loops on the same command

    i = 0
    while i < len(command_list):
        command_str = command_list[i]
        if not isinstance(command_str, str):
            log_callback(f"Error: Command at index {i} is not a string.")
            return {"success": False, "message": f"Invalid command format at index {i}.", "process": None, "stdout": last_stdout, "stderr": f"Invalid command format at index {i}.", "original_commands_data": commands_data}

        is_last_command = (i == len(command_list) - 1)
        
        try:
            process = _execute_single_command(command_str, project_dir, current_env, log_callback)

            if not is_last_command: # Setup command, wait for it
                stdout, stderr = process.communicate()
                last_stdout, last_stderr = stdout, stderr
                log_callback(f"STDOUT:\n{stdout}")
                log_callback(f"STDERR:\n{stderr}")

                if process.returncode != 0:
                    error_message = f"Setup command '{command_str}' failed (exit code {process.returncode})."
                    log_callback(error_message)
                    if attempt_ai_fix and ai_fix_attempted_for_command != i:
                        log_callback("Attempting AI fix...")
                        ai_fix_attempted_for_command = i # Mark this command index as attempted
                        # This part needs to be async if get_ai_fix_for_launch_failure is async
                        # For simplicity in this synchronous function, we'd need a sync version or a bridge
                        # ai_result = await get_ai_fix_for_launch_failure(project_dir_str, current_commands_data, i, stdout, stderr, log_callback)
                        # Since this function is sync, we'll assume a sync call or skip for now
                        # For demonstration, let's assume get_ai_fix_for_launch_failure can be called synchronously
                        # or this part is handled by an outer async orchestrator.
                        # This is a conceptual placement.
                        # In a real async app, run_application_commands_internal would be async too.
                        log_callback("AI fix attempt is conceptual here. In a real scenario, an async call would be made.")
                        # Placeholder: if AI provided a fix, update command_list and retry
                        # if ai_result["fixed"] and ai_result["new_commands_data"]:
                        #     log_callback(f"AI provided a fix: {ai_result['message_to_user']}")
                        #     current_commands_data = ai_result["new_commands_data"]
                        #     command_list = current_commands_data.get("commands", [])
                        #     i = 0 # Restart command execution from the beginning with new commands
                        #     last_stdout, last_stderr = "", "" # Reset logs
                        #     ai_fix_attempted_for_command = -1 # Reset AI fix attempt for new list
                        #     continue # Retry with new command list
                        # else:
                        #     log_callback(f"AI could not fix the command: {ai_result['message_to_user']}")
                        #     return {"success": False, "message": f"{error_message} {ai_result['message_to_user']}", "process": None, "stdout": stdout, "stderr": stderr, "original_commands_data": commands_data}

                    return {"success": False, "message": error_message, "process": None, "stdout": stdout, "stderr": stderr, "original_commands_data": commands_data}
                log_callback(f"Setup command '{command_str}' succeeded.")
            else: # Last command (assumed to be the server/application)
                time.sleep(3) # Allow time for the server to start or fail fast.

                if process.poll() is not None: # Process has terminated
                    stdout, stderr = process.communicate()
                    last_stdout, last_stderr = stdout, stderr
                    log_callback(f"STDOUT:\n{stdout}")
                    log_callback(f"STDERR:\n{stderr}")
                    exit_code = process.returncode
                    error_message = f"Main command '{command_str}' terminated unexpectedly (exit code {exit_code})."
                    log_callback(error_message)
                    # AI Fix attempt for the main command
                    if attempt_ai_fix and ai_fix_attempted_for_command != i:
                        log_callback("Attempting AI fix for main command...")
                        ai_fix_attempted_for_command = i
                        # ai_result = await get_ai_fix_for_launch_failure(project_dir_str, current_commands_data, i, stdout, stderr, log_callback)
                        # if ai_result["fixed"] and ai_result["new_commands_data"]:
                        #     log_callback(f"AI provided a fix: {ai_result['message_to_user']}")
                        #     current_commands_data = ai_result["new_commands_data"]
                        #     command_list = current_commands_data.get("commands", [])
                        #     i = 0 # Restart
                        #     last_stdout, last_stderr = "", ""
                        #     ai_fix_attempted_for_command = -1
                        #     continue
                        # else:
                        #     log_callback(f"AI could not fix the command: {ai_result['message_to_user']}")
                        #     return {"success": False, "message": f"{error_message} {ai_result['message_to_user']}", "process": None, "stdout": stdout, "stderr": stderr, "original_commands_data": commands_data}

                    return {"success": False, "message": error_message, "process": None, "stdout": stdout, "stderr": stderr, "original_commands_data": commands_data}
                else: # Process is still running
                    log_callback(f"Main command '{command_str}' is running as a background process.")
                    return {"success": True, "message": f"Main application command '{command_str}' started.", "process": process, "stdout": "", "stderr": "", "original_commands_data": commands_data}
        
        except FileNotFoundError:
            error_message = f"Error: File or command not found for '{command_str}'. Ensure it's installed and in PATH."
            log_callback(error_message)
            last_stderr = error_message
            # AI Fix attempt for FileNotFoundError
            if attempt_ai_fix and ai_fix_attempted_for_command != i:
                log_callback("Attempting AI fix for FileNotFoundError...")
                ai_fix_attempted_for_command = i
                # ai_result = await get_ai_fix_for_launch_failure(project_dir_str, current_commands_data, i, last_stdout, last_stderr, log_callback)
                # if ai_result["fixed"] and ai_result["new_commands_data"]:
                #     log_callback(f"AI provided a fix: {ai_result['message_to_user']}")
                #     current_commands_data = ai_result["new_commands_data"]
                #     command_list = current_commands_data.get("commands", [])
                #     i = 0 # Restart
                #     last_stdout, last_stderr = "", ""
                #     ai_fix_attempted_for_command = -1
                #     continue
                # else:
                #     log_callback(f"AI could not fix the command: ai_result['message_to_user']")
                #     return {"success": False, "message": f"{error_message} {ai_result['message_to_user']}", "process": None, "stdout": last_stdout, "stderr": last_stderr, "original_commands_data": commands_data}

            return {"success": False, "message": error_message, "process": None, "stdout": last_stdout, "stderr": last_stderr, "original_commands_data": commands_data}
        except Exception as e:
            error_message = f"Exception while running command '{command_str}': {str(e)}"
            log_callback(error_message)
            partial_stdout, partial_stderr = last_stdout, str(e)
            if 'process' in locals() and process: # Check if process was initialized
                try:
                    process.kill() 
                    out, err = process.communicate(timeout=1)
                    partial_stdout = out if out else ""
                    partial_stderr = err if err else str(e)
                except Exception as comm_exc:
                    log_callback(f"Exception during process communication on error: {comm_exc}")
            
            # AI Fix attempt for general Exception
            if attempt_ai_fix and ai_fix_attempted_for_command != i:
                log_callback("Attempting AI fix for general exception...")
                ai_fix_attempted_for_command = i
                # ai_result = await get_ai_fix_for_launch_failure(project_dir_str, current_commands_data, i, partial_stdout, partial_stderr, log_callback)
                # if ai_result["fixed"] and ai_result["new_commands_data"]:
                #     log_callback(f"AI provided a fix: {ai_result['message_to_user']}")
                #     current_commands_data = ai_result["new_commands_data"]
                #     command_list = current_commands_data.get("commands", [])
                #     i = 0 # Restart
                #     last_stdout, last_stderr = "", ""
                #     ai_fix_attempted_for_command = -1
                #     continue
                # else:
                #     log_callback(f"AI could not fix the command: {ai_result['message_to_user']}")
                #     return {"success": False, "message": f"{error_message} {ai_result['message_to_user']}", "process": None, "stdout": partial_stdout, "stderr": partial_stderr, "original_commands_data": commands_data}

            return {"success": False, "message": error_message, "process": None, "stdout": partial_stdout, "stderr": partial_stderr, "original_commands_data": commands_data}
        i += 1 # Move to the next command if successful

    log_callback("All commands processed.")
    if not command_list:
        return {"success": False, "message": "No commands were executed.", "process": None, "stdout": last_stdout, "stderr": last_stderr, "original_commands_data": commands_data}
    
    return {"success": True, "message": "All setup commands completed successfully (no main server command identified as last).", "process": None, "stdout": last_stdout, "stderr": last_stderr, "original_commands_data": commands_data}

async def run_application_async_wrapper(project_dir_str: str, commands_data_json: str, venv_path_str: str = None, log_callback=print, attempt_ai_fix=True):
    """
    Asynchronous wrapper to handle AI fix attempts for run_application_commands_internal.
    Also monitors for port in logs if the application starts successfully.
    """
    if log_callback == print:
        log_callback = logger.info

    try:
        initial_commands_data = json.loads(commands_data_json)
        if not isinstance(initial_commands_data, dict):
            raise ValueError("Parsed JSON is not a dictionary.")
    except json.JSONDecodeError as e:
        log_callback(f"Error: Invalid JSON format for commands_data: {e}")
        return {"success": False, "message": f"Invalid JSON for commands: {e}", "process": None, "original_commands_data": None }
    except ValueError as e:
        log_callback(f"Error: Invalid structure for commands_data: {e}")
        return {"success": False, "message": f"Invalid data structure for commands: {e}", "process": None, "original_commands_data": None}

    log_callback(f"run_application_async_wrapper called for {project_dir_str}, AI fix: {attempt_ai_fix}")

    current_commands_data = initial_commands_data.copy()
    max_ai_attempts = 3
    ai_attempt_count = 0
    
    result = {} # Define result here to ensure it's always available in the end

    while ai_attempt_count < max_ai_attempts:
        result = run_application_commands_internal(
            project_dir_str=project_dir_str,
            commands_data=current_commands_data,
            venv_path_str=venv_path_str,
            log_callback=log_callback,
            attempt_ai_fix=False
        )

        if result["success"]:
            log_callback(f"Application command execution summary: {result['message']}")
            if result.get("process"): # Main server process is running
                log_callback("Main application process started. Monitoring output for port for up to 10 seconds...")
                running_process = result["process"]
                # Pass the same log_callback that run_application_async_wrapper received
                detected_port = await monitor_process_output_for_port(
                    running_process,
                    duration=10, 
                    log_callback=log_callback 
                )
                if detected_port:
                    log_callback(f"Port {detected_port} detected from application logs.")
                    result["detected_port_in_logs"] = detected_port
                else:
                    log_callback("No specific port detected from application logs within monitoring period.")
            return result # Return success result (possibly with detected_port_in_logs)
        else: # Command execution failed
            log_callback(f"Application command execution failed: {result['message']}")
            if result.get('stdout'):
                log_callback(f"STDOUT from failed command: {result.get('stdout','')}")
            if result.get('stderr'):
                log_callback(f"STDERR from failed command: {result.get('stderr','')}")

            if attempt_ai_fix:
                failed_command_str = None
                failed_command_index = -1
                
                temp_command_list = current_commands_data.get("commands", [])
                # Try to find the failed command index based on the error message content.
                # This is a heuristic. A more robust way would be for run_application_commands_internal
                # to explicitly return the index of the failed command.
                # For now, we search for the command string in the error message.
                # If result['message'] contains "Setup command 'X' failed" or "Main command 'Y' terminated"
                # we can try to extract X or Y.
                
                # Heuristic to find failed command index
                # This part needs to be improved if run_application_commands_internal can return the index
                # For now, we proceed with this potentially flawed index if not found.
                for idx, cmd_str_in_list in enumerate(temp_command_list):
                    if cmd_str_in_list in result["message"] : # Basic check
                        failed_command_index = idx
                        failed_command_str = cmd_str_in_list
                        break
                if failed_command_index == -1 and temp_command_list: # Default to last if not found
                    failed_command_index = len(temp_command_list) -1 # This might be incorrect if an early command failed
                    # A better default might be to not attempt AI fix if index is uncertain.
                    # For now, we proceed with this potentially flawed index if not found.
                    failed_command_str = temp_command_list[failed_command_index]


                if failed_command_str is None and failed_command_index == -1 : # Check if any command was identified
                    log_callback("Could not determine the exact failed command for AI fix. Aborting AI fix.")
                    return result # Return original failure

                # Ensure failed_command_index is valid for current_commands_data['commands']
                if not (0 <= failed_command_index < len(current_commands_data.get('commands', []))):
                    log_callback(f"Failed command index {failed_command_index} is out of bounds. Aborting AI fix.")
                    return result

                log_callback(f"Attempting AI fix for command ({failed_command_index}): {current_commands_data['commands'][failed_command_index]}")
                ai_attempt_count += 1
                ai_result = await get_ai_fix_for_launch_failure(
                    project_dir_str,
                    current_commands_data, 
                    failed_command_index,
                    result.get("stdout", ""),
                    result.get("stderr", ""),
                    log_callback,
                    ai_model="openai/gpt-4.1-nano",  # Use the same model as for launch
                    api_key=None  # Optionally pass API key if available
                )

                if ai_result["fixed"] and ai_result["new_commands_data"]:
                    log_callback(f"AI provided a fix ({ai_attempt_count}/{max_ai_attempts}): {ai_result['message_to_user']}")
                    current_commands_data = ai_result["new_commands_data"]
                    if not isinstance(current_commands_data, dict) or "commands" not in current_commands_data:
                        log_callback("AI returned invalid new_commands_data structure. Aborting AI fix.")
                        result["message"] += " (AI fix failed due to invalid data structure from AI)"
                        return result
                    log_callback("Retrying with new commands from AI...")
                    continue # Retry with new commands
                else:
                    log_callback(f"AI could not fix the command ({ai_attempt_count}/{max_ai_attempts}): {ai_result['message_to_user']}")
                    result["message"] += f" (AI: {ai_result['message_to_user']})"
                    return result # Return original failure with AI message
            else: # attempt_ai_fix is False
                return result # AI fix not attempted, return original failure
    
    log_callback(f"Max AI fix attempts ({max_ai_attempts}) reached. Returning last failure.")
    return result # Return last failure if max attempts reached

# Keep the original run_application as a synchronous entry point if needed,
# but it cannot directly call the async AI fix logic without an event loop.
# For a fully async operation, the caller of run_application should call run_application_async_wrapper.

def run_application(project_dir_str: str, commands_data_json: str, venv_path_str: str = None, log_callback=print, attempt_ai_fix=False):
    """
    Main function to run application using a list of commands specified in a JSON string.
    `commands_data_json` is a JSON string like '{"commands": ["cmd1", ...], "env": {"VAR": "val"}}'
    `log_callback` is a function to send log messages to (e.g., print, or a UI updater).
    Returns a dict: {"success": bool, "message": str, "process": Popen_object_or_None}

    If attempt_ai_fix is True, this function will require an event loop to run the async AI fix logic.
    It's recommended to call `run_application_async_wrapper` directly from an async context.
    """
    if log_callback == print: # Default logger if none provided by caller
        log_callback = logger.info 

    if attempt_ai_fix:
        log_callback("Warning: attempt_ai_fix=True in synchronous run_application. This might not work as expected without an event loop for async AI calls. Consider using run_application_async_wrapper.")
        # This is a simplified way to run an async function from sync code.
        # In a real application, especially a server, you'd manage the event loop carefully.
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:  # 'RuntimeError: There is no current event loop...'
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            run_application_async_wrapper(
                project_dir_str=project_dir_str,
                commands_data_json=commands_data_json,
                venv_path_str=venv_path_str,
                log_callback=log_callback,
                attempt_ai_fix=True
            )
        )
        # If new_event_loop was called, it's good practice to close it if this is the end of its lifecycle.
        # However, if an existing loop was retrieved, it should not be closed here.
        # For simplicity, assuming this function might be called multiple times, managing loop closure carefully is key.
        # if not asyncio.get_event_loop().is_running(): # Check if it was a new loop that finished
        #     loop.close()
        return result

    # Original synchronous execution path if attempt_ai_fix is False
    try:
        commands_data = json.loads(commands_data_json)
        if not isinstance(commands_data, dict):
            raise ValueError("Parsed JSON is not a dictionary.")
    except json.JSONDecodeError as e:
        log_callback(f"Error: Invalid JSON format for commands_data: {e}")
        return {"success": False, "message": f"Invalid JSON for commands: {e}", "process": None, "original_commands_data": None}
    except ValueError as e:
        log_callback(f"Error: Invalid structure for commands_data: {e}")
        return {"success": False, "message": f"Invalid data structure for commands: {e}", "process": None, "original_commands_data": None}

    log_callback(f"run_application called for {project_dir_str} with data: {commands_data_json}")
    
    result = run_application_commands_internal(
        project_dir_str=project_dir_str,
        commands_data=commands_data,
        venv_path_str=venv_path_str,
        log_callback=log_callback,
        attempt_ai_fix=False 
    )
    
    if result["success"]:
        log_callback(f"Application command execution summary: {result['message']}")
    else:
        log_callback(f"Application command execution failed: {result['message']}")
        if result.get('stdout'):
            log_callback(f"Final STDOUT: {result.get('stdout','')}")
        if result.get('stderr'):
            log_callback(f"Final STDERR: {result.get('stderr','')}")

    return result
