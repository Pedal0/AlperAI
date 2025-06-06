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

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, flash, send_file, current_app
import os
import uuid
import threading
import zipfile
import io
from pathlib import Path
from datetime import datetime
import traceback # Ensure traceback is imported
from src.generation.generation_flow import generate_application
from src.utils.model_utils import is_free_model
from src.api.openrouter_api import extract_files_from_response, generate_code_with_openrouter

# Blueprint for generation
bp_generation = Blueprint('generation', __name__)

generation_tasks = {}

# ...existing code for build_directory_structure if needed...

def generate_application_thread(task_id, api_key, model, prompt, target_dir, use_mcp, frontend_framework, include_animations, empty_files_check, app=None):
    # Fix: use app.app_context() if app is provided
    if app is not None:
        with app.app_context():
            _generate_application_thread_body(task_id, api_key, model, prompt, target_dir, use_mcp, frontend_framework, include_animations, empty_files_check)
    else:
        with current_app.app_context():
            _generate_application_thread_body(task_id, api_key, model, prompt, target_dir, use_mcp, frontend_framework, include_animations, empty_files_check)

def _generate_application_thread_body(task_id, api_key, model, prompt, target_dir, use_mcp, frontend_framework, include_animations, empty_files_check):
    try:
        def update_progress_callback(step, message, progress=None):
            if progress is not None:
                generation_tasks[task_id]['progress'] = progress
            if message:
                generation_tasks[task_id]['current_step'] = message
            current_app.logger.info(f"[Task {task_id} - Step {step}] {message}")
        success = generate_application(
            api_key=api_key,
            selected_model=model,
            user_prompt=prompt,
            target_directory=target_dir,
            use_mcp_tools=use_mcp,
            frontend_framework=frontend_framework,
            include_animations=include_animations,
            progress_callback=update_progress_callback
        )
        used_tools = current_app.config.pop('used_tools_details', [])
        if success:
            files_written = []
            files_still_empty = []
            for root, dirs, files in os.walk(target_dir):
                if '__pycache__' in dirs:
                    dirs.remove('__pycache__')
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                files[:] = [f for f in files if not f.startswith('.')]
                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), target_dir)
                    rel_path = os.path.normpath(rel_path).replace(os.sep, '/')
                    files_written.append(rel_path)
                    try:
                        if os.path.getsize(os.path.join(root, file)) == 0:
                            files_still_empty.append(rel_path)
                    except OSError:
                        pass
            generation_tasks[task_id]['progress'] = 100
            generation_tasks[task_id]['status'] = 'completed'
            generation_tasks[task_id]['result'] = {
                'success': True,
                'target_directory': target_dir,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'files_created': len(files_written),
                'file_list': sorted(files_written),
                'files_still_empty': sorted(files_still_empty),
                'prompt': prompt,
                'reformulated_prompt': current_app.config.pop('reformulated_prompt', ''),
                'used_tools': used_tools
            }
            current_app.logger.info(f"[Task {task_id}] Generation completed. {len(files_written)} files created, {len(files_still_empty)} empty files.")
        else:
            generation_tasks[task_id]['status'] = 'failed'
            if 'error' not in generation_tasks[task_id]:
                generation_tasks[task_id]['error'] = "Application generation failed (unknown reason)"
            generation_tasks[task_id]['result'] = {'success': False, 'used_tools': used_tools}
            current_app.logger.error(f"[Task {task_id}] Generation failed: {generation_tasks[task_id]['error']}")
    except Exception as e:
        import traceback
        current_app.logger.error(f"[Task {task_id}] Error during generation: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        generation_tasks[task_id]['error'] = str(e)
        generation_tasks[task_id]['status'] = 'failed'
        used_tools_on_error = current_app.config.pop('used_tools_details', [])
        generation_tasks[task_id]['result'] = {'success': False, 'used_tools': used_tools_on_error}

def iterate_application_thread(task_id, api_key, model, reformulated_prompt, feedback, target_dir, regenerate_code=False, flask_app=None):
    app_ctx = flask_app or current_app._get_current_object()
    with app_ctx.app_context():
        try:
            generation_tasks[task_id]['progress'] = 10
            generation_tasks[task_id]['current_step'] = "Analyzing existing code..."
            existing_files = {}
            try:
                for root, dirs, files in os.walk(target_dir):
                    for file in files:
                        rel_path = os.path.relpath(os.path.join(root, file), target_dir)
                        if os.path.getsize(os.path.join(root, file)) > 0:
                            with open(os.path.join(root, file), 'r', encoding='utf-8', errors='ignore') as f:
                                try:
                                    existing_files[rel_path] = f.read()
                                except:
                                    pass
            except Exception as e:
                app_ctx.logger.error(f"Error reading existing files: {str(e)}")
                generation_tasks[task_id]['error'] = f"Error reading files: {str(e)}"
                generation_tasks[task_id]['status'] = 'failed'
                return
            generation_tasks[task_id]['progress'] = 30
            generation_tasks[task_id]['current_step'] = "Preparing iteration..."
            # Only send list of file paths to minimize tokens
            file_list = sorted(existing_files.keys())
            # Provide list of files
            code_summary = "List of existing files:\n" + "\n".join(file_list) + "\n"
            # Include brief previews of key HTML/CSS files to preserve style context
            detailed_context = ""
            for path in file_list:
                if path.lower().endswith(('.html', '.css')):
                    content = existing_files.get(path, '')
                    preview = content[:1000] + ('...' if len(content) > 1000 else '')
                    detailed_context += f"FILE: {path}\n```\n{preview}\n```\n\n"
            if detailed_context:
                code_summary += "\nDetailed file previews for style context:\n" + detailed_context
            # Nouveau prompt système renforcé pour l'itération IA
            system_prompt = '''You are a senior software engineer AI assistant. Your task is to improve the existing application code according to the user's instructions.

STRICT RULES:
- DO NOT modify any file, code, style, or structure unless it is EXPLICITLY requested by the user feedback.
- PRESERVE all existing styles, layouts, and logic unless the user asks for a change.
- If the user asks for a change, ONLY modify the minimal code required to achieve the request.
- DO NOT refactor, optimize, or reformat code unless the user asks for it.
- DO NOT change the structure, class names, CSS selectors, or HTML tags unless the user asks for it.
- If you need to add code, do it in a way that does not break or alter the existing design and logic.
- If the user feedback is ambiguous, DO NOT make assumptions: do the minimal change or ask for clarification.
- If you detect a risk of breaking the style or structure, warn in a comment at the top of the file.

EXAMPLES:
Good:
- User: "Add a button to the navbar" → Only add the button in the navbar, do not touch other parts.
- User: "Change the background color to black" → Only change the background property, do not touch other CSS or HTML.
Bad:
- Changing unrelated styles, deleting or renaming classes, or reformatting the whole file.

OUTPUT FORMAT:
For each file to modify or add, clearly indicate:
FILE: <file/path>
Followed by the complete content of the file after modifications. Do not truncate code and provide full implementations. Ensure accuracy in file paths.

FINAL CHECK:
- Double check that you did NOT change anything except what the user requested.
- If you made any change not strictly required, revert it.
'''
            # --- Détection automatique des fichiers concernés par l'itération ---
            import re
            feedback_lower = feedback.lower()
            # Heuristique simple : cherche des mots-clés de fichiers ou d'éléments
            file_keywords = []
            if 'navbar' in feedback_lower or 'menu' in feedback_lower:
                file_keywords += ['navbar', 'menu', 'header']
            if 'footer' in feedback_lower:
                file_keywords += ['footer']
            if 'button' in feedback_lower or 'bouton' in feedback_lower:
                file_keywords += ['button', 'btn']
            if 'background' in feedback_lower or 'fond' in feedback_lower:
                file_keywords += ['style', 'background', 'css']
            if 'color' in feedback_lower or 'couleur' in feedback_lower:
                file_keywords += ['style', 'color', 'css']
            if 'page' in feedback_lower:
                file_keywords += ['index', 'page', 'main']
            # Ajoute d'autres heuristiques selon besoin...

            # Recherche les fichiers concernés
            targeted_files = []
            for path in file_list:
                for kw in file_keywords:
                    if kw in path.lower():
                        targeted_files.append(path)
                        break
            # Si rien trouvé, fallback sur tous les fichiers HTML/CSS
            if not targeted_files:
                targeted_files = [p for p in file_list if p.lower().endswith(('.html', '.css'))]
            # Extraction des extraits pertinents
            detailed_context = ""
            for path in targeted_files:
                content = existing_files.get(path, '')
                preview = content[:2000] + ('...' if len(content) > 2000 else '')
                detailed_context += f"FILE: {path}\n```\n{preview}\n```\n\n"
            # Résumé du style global (extraction des variables CSS principales)
            style_summary = ""
            for path in file_list:
                if path.lower().endswith('.css'):
                    css_content = existing_files.get(path, '')
                    # Extrait les variables CSS et couleurs principales
                    vars_found = re.findall(r'--[\w-]+:\s*[^;]+;', css_content)
                    colors_found = re.findall(r'#[0-9a-fA-F]{3,6}|rgb\([^\)]+\)', css_content)
                    if vars_found or colors_found:
                        style_summary += f"\nDans {path}:\nVariables CSS: {', '.join(vars_found[:10])}\nCouleurs: {', '.join(colors_found[:10])}\n"
            if style_summary:
                detailed_context += f"\nRésumé du style global :\n{style_summary}\n"
            code_summary = "Liste des fichiers concernés :\n" + "\n".join(targeted_files) + "\n\nExtraits pertinents :\n" + detailed_context
            user_prompt = f"""Here is the original project description:\n\n{reformulated_prompt}\n\nHere is an overview of the existing code:\n\n{code_summary}\n\nUser requested iteration with the following feedback:\n\n{feedback}\n\nPlease improve the existing code according to these instructions. Provide only the files that need to be modified or added."""
            generation_tasks[task_id]['progress'] = 50
            generation_tasks[task_id]['current_step'] = "Generating improvements..."
            # Debug: log prompt sizes to estimate token usage
            app_ctx.logger.info(f"Iteration prompts size: system_prompt {len(system_prompt)} chars, user_prompt {len(user_prompt)} chars, file_list entries {len(file_list)}")
            response = generate_code_with_openrouter(
                api_key=api_key,
                model=model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3
            )
            if not response or 'error' in response:
                error_message = response.get('error', "Unknown error during API call for iteration")
                generation_tasks[task_id]['error'] = error_message
                generation_tasks[task_id]['status'] = 'failed'
                return
            generation_tasks[task_id]['progress'] = 70
            generation_tasks[task_id]['current_step'] = "Applying improvements..."
            modified_files = extract_files_from_response(response)
            if not modified_files:
                app_ctx.logger.warning("No files were extracted from the API response.")
                code_response_text = response.get('content', '')
                import re
                file_blocks = re.findall(r'FILE: (.+?)\n```[\w\+]*\n(.*?)```', code_response_text, re.DOTALL)
                for file_path, content in file_blocks:
                    norm_path = os.path.normpath(file_path.strip())
                    modified_files[norm_path] = content.strip()
                if not modified_files:
                    app_ctx.logger.error("Failed to extract modified files, even with fallback method.")
                    generation_tasks[task_id]['error'] = "Unable to extract modified files from API response"
                    generation_tasks[task_id]['status'] = 'failed'
                    return
            files_written = []
            for file_path, content in modified_files.items():
                try:
                    norm_path = os.path.normpath(file_path)
                    full_path = os.path.join(target_dir, norm_path)
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    files_written.append(norm_path)
                    app_ctx.logger.info(f"Modified file written: {full_path}")
                except Exception as e:
                    app_ctx.logger.error(f"Error writing file {file_path}: {str(e)}")
            generation_tasks[task_id]['progress'] = 100
            generation_tasks[task_id]['status'] = 'completed'
            generation_tasks[task_id]['result'] = {
                'success': True,
                'target_directory': target_dir,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'files_modified': len(files_written),
                'file_list': files_written,
                'prompt': feedback,
                'reformulated_prompt': reformulated_prompt,
                'iteration': True
            }
            app_ctx.logger.info(f"Iteration completed. {len(files_written)} files modified.")
        except Exception as e:
            app_ctx.logger.error(f"Error during iteration: {str(e)}")
            generation_tasks[task_id]['error'] = str(e)
            generation_tasks[task_id]['status'] = 'failed'

@bp_generation.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.form
        api_key = data.get('api_key', '')
        model = data.get('model', 'google/gemini-2.5-pro-exp-03-25:free')
        prompt = data.get('user_prompt', '')
        target_dir = data.get('target_directory', '')
        use_mcp = 'use_mcp_tools' in data
        frontend_framework = data.get('frontend_framework', 'Auto-detect')
        include_animations = data.get('include_animations', 'on') == 'on'
        empty_files_check = data.get('empty_files_check', 'on') == 'on'
        errors = []
        if not api_key:
            errors.append("API key is required")
        if not prompt:
            errors.append("Application description is required")
        if not target_dir:
            errors.append("Target directory is required")
        elif not Path(target_dir).is_dir():
            try:
                Path(target_dir).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Unable to create directory '{target_dir}': {str(e)}")
        if errors:
            return jsonify({"status": "error", "errors": errors})
        session['prompt'] = prompt
        session['target_dir'] = target_dir
        session['model'] = model
        session['api_key'] = api_key  # Store API key in session
        session['use_mcp'] = use_mcp
        session['frontend_framework'] = frontend_framework
        session['include_animations'] = include_animations
        task_id = str(uuid.uuid4())
        session['generation_task_id'] = task_id
        generation_tasks[task_id] = {
            'id': task_id,
            'status': 'in_progress',
            'progress': 0,
            'current_step': 'Initialization...',
            'start_time': datetime.now(),
            'error': None,
            'result': None
        }
        app = current_app._get_current_object()
        thread = threading.Thread(
            target=generate_application_thread,
            args=(task_id, api_key, model, prompt, target_dir, use_mcp, frontend_framework, include_animations, empty_files_check, app)
        )
        thread.daemon = True
        thread.start()
        return jsonify({
            "status": "success",
            "message": "Generation started",
            "task_id": task_id
        })
    except Exception as e:
        current_app.logger.error(f"Error during generation: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"status": "error", "message": str(e)})
        else:
            flash(f"Error: {str(e)}", "danger")
            return redirect(url_for('ui.index'))

@bp_generation.route('/generation_progress', methods=['GET'])
def generation_progress():
    task_id = session.get('generation_task_id')
    if not task_id or task_id not in generation_tasks:
        return jsonify({
            "status": "error",
            "message": "No generation task found"
        })
    task = generation_tasks[task_id]
    if task['status'] == 'completed' and task['result']:
        session['generation_result'] = task['result']
    # Added: ordered list of steps
    use_mcp = session.get('use_mcp', False)
    steps = [
        "Initialization..."
    ]
    if use_mcp:
        steps.append("🔌 MCP tools enabled: web search, documentation, and frontend components available.")
    steps += [
        "Extracting URLs from prompt...",
        "Reformulating prompt...",
        "Defining project structure...",
        "Creating folders and files...",
        "Generating complete code...",
        "Writing code to files...",
        "Checking for empty files...",
        "🎉 Application generated successfully!"
    ]
    response = {
        "status": task['status'],
        "progress": task['progress'],
        "current_step": task['current_step'],
        "steps": steps
    }
    if task['status'] == 'completed':
        response["redirect_url"] = url_for('generation.result')
    elif task['status'] == 'failed':
        response["error"] = task['error']
    return jsonify(response)

@bp_generation.route('/result')
def result():
    if 'generation_result' not in session:
        flash("No generation result found. Please generate an application first.", "warning")
        return redirect(url_for('ui.index'))
    generation_result = session['generation_result']
    used_tools = generation_result.get('used_tools', [])
    return render_template('result.html',
                          result=generation_result,
                          prompt=session.get('prompt', ''),
                          target_dir=session.get('target_dir', ''),
                          used_tools=used_tools)

@bp_generation.route('/iterate', methods=['POST'])
def iterate_generation():
    if 'generation_result' not in session:
        flash("No generation result found. Please generate an application first.", "warning")
        return redirect(url_for('ui.index'))
    try:
        data = request.form
        api_key = data.get('api_key', '')
        model = data.get('model', session.get('model', 'google/gemini-2.5-pro-exp-03-25:free'))
        feedback = data.get('feedback', '')
        target_dir = session.get('target_dir', '')
        reformulated_prompt = session['generation_result'].get('reformulated_prompt', '')
        if not api_key:
            flash("API key required", "danger")
            return redirect(url_for('generation.result'))
        if not feedback:
            flash("Please provide iteration instructions", "danger")
            return redirect(url_for('generation.result'))
        if not target_dir or not Path(target_dir).is_dir():
            flash("Target directory not found", "danger")
            return redirect(url_for('generation.result'))
        task_id = str(uuid.uuid4())
        session['generation_task_id'] = task_id
        generation_tasks[task_id] = {
            'id': task_id,
            'status': 'in_progress',
            'progress': 0,
            'current_step': 'Initializing iteration...',
            'start_time': datetime.now(),
            'error': None,
            'result': None,
            'is_iteration': True,
            'previous_result': session['generation_result']
        }
        app = current_app._get_current_object()
        thread = threading.Thread(
            target=iterate_application_thread,
            args=(task_id, api_key, model, reformulated_prompt, feedback, target_dir, False, app)
        )
        thread.daemon = True
        thread.start()
        return jsonify({
            "status": "success",
            "message": "Iteration started",
            "task_id": task_id
        })
    except Exception as e:
        current_app.logger.error(f"Error during iteration: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"status": "error", "message": str(e)})
        else:
            flash(f"Error: {str(e)}", "danger")
            return redirect(url_for('generation.result'))

@bp_generation.route('/continue_iteration', methods=['POST'])
def continue_iteration():
    if 'generation_result' not in session:
        flash("No generation result found. Please generate an application first.", "warning")
        return redirect(url_for('ui.index'))
    try:
        data = request.form
        api_key = data.get('api_key', '')
        model = data.get('model', session.get('model', 'google/gemini-2.5-pro-exp-03-25:free'))
        feedback = data.get('feedback', '')
        regenerate_code = data.get('regenerate_code', 'off') == 'on'
        target_dir = session.get('target_dir', '')
        original_prompt = session.get('prompt', '')
        reformulated_prompt = session['generation_result'].get('reformulated_prompt', '')
        if not api_key:
            flash("API key required", "danger")
            return redirect(url_for('generation.result'))
        if not feedback:
            flash("Please provide iteration instructions", "danger")
            return redirect(url_for('generation.result'))
        if not target_dir or not Path(target_dir).is_dir():
            flash("Target directory not found", "danger")
            return redirect(url_for('generation.result'))
        task_id = str(uuid.uuid4())
        session['generation_task_id'] = task_id
        if 'iteration_history' not in session:
            session['iteration_history'] = []
        iteration_entry = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'feedback': feedback,
            'regenerate_code': regenerate_code
        }
        session['iteration_history'].append(iteration_entry)
        generation_tasks[task_id] = {
            'id': task_id,
            'status': 'in_progress',
            'progress': 0,
            'current_step': 'Initializing iteration...',
            'start_time': datetime.now(),
            'error': None,
            'result': None,
            'is_iteration': True,
            'previous_result': session['generation_result']
        }
        app = current_app._get_current_object()
        thread = threading.Thread(
            target=iterate_application_thread,
            args=(task_id, api_key, model, reformulated_prompt, feedback, target_dir, regenerate_code, app)
        )
        thread.daemon = True
        thread.start()
        return jsonify({
            "status": "success",
            "message": "Iteration started",
            "task_id": task_id
        })
    except Exception as e:
        current_app.logger.error(f"Error during iteration: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"status": "error", "message": str(e)})
        else:
            flash(f"Error: {str(e)}", "danger")
            return redirect(url_for('generation.result'))

@bp_generation.route('/download_zip', methods=['GET'])
def download_zip():
    # Log entry point of the function
    current_app.logger.debug("Entered download_zip route.")
    
    try:
        # Log session content at the beginning to check its state
        current_app.logger.debug(f"Session data at download_zip start: {{key: type(value) for key, value in session.items()}}")
        # Log specific session keys expected
        current_app.logger.debug(f"session.get('generation_result') type: {type(session.get('generation_result'))}")
        current_app.logger.debug(f"session.get('target_dir') from generation_result: {session.get('generation_result', {}).get('target_directory')}")


        from src.utils.env_utils import is_vercel_environment
        from src.utils.file_utils import cleanup_vercel_project
        current_app.logger.debug("Successfully imported env_utils and file_utils in download_zip.")

        if 'generation_result' not in session:
            current_app.logger.error("'generation_result' not found in session for download_zip.")
            flash("No generation result found. Please generate an application first.", "warning")
            return redirect(url_for('ui.index'))
        
        generation_result_data = session['generation_result']
        target_dir = generation_result_data.get('target_directory')
        current_app.logger.info(f"Target directory for ZIP: {target_dir}")

        if not target_dir or not Path(target_dir).is_dir():
            current_app.logger.error(f"Target directory '{target_dir}' not found or is not a directory.")
            flash("Target directory not found", "danger")
            return redirect(url_for('generation.result'))
        
        is_vercel = is_vercel_environment()
        # Make sure 'is_vercel_project' is accessed safely if it might not exist
        is_vercel_project = current_app.config.get('is_vercel_project', False)
        current_app.logger.debug(f"Vercel check: is_vercel={is_vercel}, is_vercel_project={is_vercel_project}")
        
        current_app.logger.info(f"Attempting to create ZIP for directory: {target_dir}")
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(target_dir):
                # Exclude hidden files/dirs and __pycache__
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
                files[:] = [f for f in files if not f.startswith('.')] # Corrected this line
                
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, target_dir)
                    current_app.logger.debug(f"Adding to ZIP: {file_path} as {rel_path}")
                    zipf.write(file_path, rel_path)
        memory_file.seek(0)
        
        dir_name = os.path.basename(os.path.normpath(target_dir))
        zip_filename = f"{dir_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
        current_app.logger.info(f"ZIP file '{zip_filename}' created in memory. Size: {memory_file.getbuffer().nbytes} bytes.")

        def cleanup_after_send():
            try: # Added try-except for cleanup
                if is_vercel and is_vercel_project:
                    current_app.logger.info(f"Vercel cleanup: Attempting to remove {target_dir}")
                    cleanup_vercel_project(Path(target_dir))
                    current_app.logger.info(f"Vercel cleanup: Project directory {target_dir} cleaned up.")
            except Exception as e_cleanup:
                 current_app.logger.error(f"Exception in Vercel cleanup: {str(e_cleanup)}\\nTraceback:\\n{traceback.format_exc()}")

        
        response = send_file(
            memory_file,
            as_attachment=True, 
            download_name=zip_filename,
            mimetype='application/zip'
        )
        current_app.logger.info(f"Prepared send_file response for {zip_filename}.")
        
        if is_vercel and is_vercel_project:
            current_app.logger.info("Scheduling Vercel cleanup after send.")
            threading.Timer(5.0, cleanup_after_send).start() 
        
        current_app.logger.debug("download_zip route processing complete, returning response.")
        return response
        
    except Exception as e:
        tb_str = traceback.format_exc()
        current_app.logger.error(f"Exception in download_zip: {str(e)}\\nTraceback:\\n{tb_str}")
        flash(f"Error creating ZIP file: {str(e)}", "danger")
        return redirect(url_for('generation.result'))