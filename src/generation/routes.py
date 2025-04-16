from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, flash, send_file, current_app
import os
import uuid
import threading
import zipfile
import io
from pathlib import Path
from datetime import datetime
from src.generation.generation_flow import generate_application
from src.utils.model_utils import is_free_model
from src.api.openrouter_api import extract_files_from_response, generate_code_with_openrouter

# Blueprint pour la génération
bp_generation = Blueprint('generation', __name__)

generation_tasks = {}

# ...existing code for build_directory_structure if needed...

def generate_application_thread(task_id, api_key, model, prompt, target_dir, use_mcp, frontend_framework, include_animations, empty_files_check, app=None):
    # Correction : utiliser app.app_context() si app est fourni
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
            current_app.logger.info(f"[Task {task_id}] Génération terminée. {len(files_written)} fichiers créés, {len(files_still_empty)} fichiers toujours vides.")
        else:
            generation_tasks[task_id]['status'] = 'failed'
            if 'error' not in generation_tasks[task_id]:
                generation_tasks[task_id]['error'] = "Échec de la génération de l'application (raison inconnue)"
            generation_tasks[task_id]['result'] = {'success': False, 'used_tools': used_tools}
            current_app.logger.error(f"[Task {task_id}] Échec de la génération de l'application: {generation_tasks[task_id]['error']}")
    except Exception as e:
        import traceback
        current_app.logger.error(f"[Task {task_id}] Erreur PENDANT la génération: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        generation_tasks[task_id]['error'] = str(e)
        generation_tasks[task_id]['status'] = 'failed'
        used_tools_on_error = current_app.config.pop('used_tools_details', [])
        generation_tasks[task_id]['result'] = {'success': False, 'used_tools': used_tools_on_error}

def iterate_application_thread(task_id, api_key, model, reformulated_prompt, feedback, target_dir, regenerate_code=False):
    try:
        generation_tasks[task_id]['progress'] = 10
        generation_tasks[task_id]['current_step'] = "Analyse du code existant..."
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
            current_app.logger.error(f"Erreur lors de la lecture des fichiers existants: {str(e)}")
            generation_tasks[task_id]['error'] = f"Erreur lors de la lecture des fichiers: {str(e)}"
            generation_tasks[task_id]['status'] = 'failed'
            return
        generation_tasks[task_id]['progress'] = 30
        generation_tasks[task_id]['current_step'] = "Préparation de l'itération..."
        code_summary = "Structure du projet et aperçu du code existant:\n\n"
        for file_path, content in existing_files.items():
            code_summary += f"FILE: {file_path}\n"
            preview = content[:300] + "..." if len(content) > 300 else content
            code_summary += f"```\n{preview}\n```\n\n"
        system_prompt = """Vous êtes un expert en développement logiciel. Votre tâche est d'améliorer le code existant d'une application selon les instructions de l'utilisateur.\n\nNe générez que les fichiers qui doivent être modifiés ou ajoutés.\n\nPour chaque fichier à modifier ou ajouter, indiquez clairement:\n\n```\nFILE: <chemin/du/fichier>\n```\n\nSuivi du contenu complet du fichier après modifications.\nNe tronquez pas le code et fournissez des implémentations complètes.\nAssurez-vous d'être précis quant aux chemins des fichiers.\n"""
        user_prompt = f"""Voici la description originale du projet:\n\n{reformulated_prompt}\n\nVoici un aperçu du code existant:\n\n{code_summary}\n\nItération demandée par l'utilisateur:\n\n{feedback}\n\nVeuillez améliorer le code existant selon ces instructions. \nFournissez uniquement les fichiers qui doivent être modifiés ou ajoutés."""
        generation_tasks[task_id]['progress'] = 50
        generation_tasks[task_id]['current_step'] = "Génération des améliorations..."
        response = generate_code_with_openrouter(
            api_key=api_key,
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3
        )
        if not response or 'error' in response:
            error_message = response.get('error', "Erreur inconnue lors de l'appel à l'API pour l'itération")
            generation_tasks[task_id]['error'] = error_message
            generation_tasks[task_id]['status'] = 'failed'
            return
        generation_tasks[task_id]['progress'] = 70
        generation_tasks[task_id]['current_step'] = "Application des améliorations..."
        modified_files = extract_files_from_response(response)
        if not modified_files:
            current_app.logger.warning("Aucun fichier n'a été extrait de la réponse de l'API.")
            code_response_text = response.get('content', '')
            import re
            file_blocks = re.findall(r'FILE: (.+?)\n```[\w\+]*\n(.*?)```', code_response_text, re.DOTALL)
            for file_path, content in file_blocks:
                norm_path = os.path.normpath(file_path.strip())
                modified_files[norm_path] = content.strip()
            if not modified_files:
                current_app.logger.error("Échec de l'extraction des fichiers modifiés, même avec la méthode de secours.")
                generation_tasks[task_id]['error'] = "Impossible d'extraire les fichiers modifiés de la réponse de l'API"
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
                current_app.logger.info(f"Fichier modifié écrit: {full_path}")
            except Exception as e:
                current_app.logger.error(f"Erreur lors de l'écriture du fichier {file_path}: {str(e)}")
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
        current_app.logger.info(f"Itération terminée. {len(files_written)} fichiers modifiés.")
    except Exception as e:
        current_app.logger.error(f"Erreur lors de l'itération: {str(e)}")
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
                errors.append(f"Impossible de créer le répertoire '{target_dir}': {str(e)}")
        if errors:
            return jsonify({"status": "error", "errors": errors})
        session['prompt'] = prompt
        session['target_dir'] = target_dir
        session['model'] = model
        session['use_mcp'] = use_mcp
        session['frontend_framework'] = frontend_framework
        session['include_animations'] = include_animations
        task_id = str(uuid.uuid4())
        session['generation_task_id'] = task_id
        generation_tasks[task_id] = {
            'id': task_id,
            'status': 'in_progress',
            'progress': 0,
            'current_step': 'Initialisation...',
            'start_time': datetime.now(),
            'error': None,
            'result': None
        }
        # Correction : passer l'objet app au thread et utiliser app.app_context()
        app = current_app._get_current_object()
        thread = threading.Thread(
            target=generate_application_thread,
            args=(task_id, api_key, model, prompt, target_dir, use_mcp, frontend_framework, include_animations, empty_files_check, app)
        )
        thread.daemon = True
        thread.start()
        return jsonify({
            "status": "success",
            "message": "Génération démarrée",
            "task_id": task_id
        })
    except Exception as e:
        current_app.logger.error(f"Erreur lors de la génération: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"status": "error", "message": str(e)})
        else:
            flash(f"Erreur: {str(e)}", "danger")
            return redirect(url_for('ui.index'))

@bp_generation.route('/generation_progress', methods=['GET'])
def generation_progress():
    task_id = session.get('generation_task_id')
    if not task_id or task_id not in generation_tasks:
        return jsonify({
            "status": "error",
            "message": "Aucune tâche de génération trouvée"
        })
    task = generation_tasks[task_id]
    if task['status'] == 'completed' and task['result']:
        session['generation_result'] = task['result']
    # Ajout : liste ordonnée des étapes (steps)
    use_mcp = session.get('use_mcp', False)
    steps = [
        "Initialisation..."
    ]
    if use_mcp:
        steps.append("🔌 Outils MCP activés: Recherche web, documentation, et composants frontend disponibles.")
    steps += [
        "Extraction des URLs du prompt...",
        "Reformulation du prompt...",
        "Définition de la structure du projet...",
        "Création des dossiers et fichiers...",
        "Génération du code complet...",
        "Écriture du code dans les fichiers...",
        "Vérification des fichiers vides...",
        "🎉 Application générée avec succès!"
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
        flash("Aucun résultat de génération trouvé. Veuillez d'abord générer une application.", "warning")
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
        flash("Aucun résultat de génération trouvé. Veuillez d'abord générer une application.", "warning")
        return redirect(url_for('ui.index'))
    try:
        data = request.form
        api_key = data.get('api_key', '')
        model = data.get('model', session.get('model', 'google/gemini-2.5-pro-exp-03-25:free'))
        feedback = data.get('feedback', '')
        target_dir = session.get('target_dir', '')
        reformulated_prompt = session['generation_result'].get('reformulated_prompt', '')
        if not api_key:
            flash("Clé API requise", "danger")
            return redirect(url_for('generation.result'))
        if not feedback:
            flash("Veuillez fournir des instructions pour l'itération", "danger")
            return redirect(url_for('generation.result'))
        if not target_dir or not Path(target_dir).is_dir():
            flash("Répertoire cible introuvable", "danger")
            return redirect(url_for('generation.result'))
        task_id = str(uuid.uuid4())
        session['generation_task_id'] = task_id
        generation_tasks[task_id] = {
            'id': task_id,
            'status': 'in_progress',
            'progress': 0,
            'current_step': 'Initialisation de l\'itération...',
            'start_time': datetime.now(),
            'error': None,
            'result': None,
            'is_iteration': True,
            'previous_result': session['generation_result']
        }
        thread = threading.Thread(
            target=iterate_application_thread,
            args=(task_id, api_key, model, reformulated_prompt, feedback, target_dir)
        )
        thread.daemon = True
        thread.start()
        return jsonify({
            "status": "success",
            "message": "Itération démarrée",
            "task_id": task_id
        })
    except Exception as e:
        current_app.logger.error(f"Erreur lors de l'itération: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"status": "error", "message": str(e)})
        else:
            flash(f"Erreur: {str(e)}", "danger")
            return redirect(url_for('generation.result'))

@bp_generation.route('/continue_iteration', methods=['POST'])
def continue_iteration():
    if 'generation_result' not in session:
        flash("Aucun résultat de génération trouvé. Veuillez d'abord générer une application.", "warning")
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
            flash("Clé API requise", "danger")
            return redirect(url_for('generation.result'))
        if not feedback:
            flash("Veuillez fournir des instructions pour l'itération", "danger")
            return redirect(url_for('generation.result'))
        if not target_dir or not Path(target_dir).is_dir():
            flash("Répertoire cible introuvable", "danger")
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
            'current_step': 'Initialisation de l\'itération...',
            'start_time': datetime.now(),
            'error': None,
            'result': None,
            'is_iteration': True,
            'previous_result': session['generation_result']
        }
        thread = threading.Thread(
            target=iterate_application_thread,
            args=(task_id, api_key, model, reformulated_prompt, feedback, target_dir, regenerate_code)
        )
        thread.daemon = True
        thread.start()
        return jsonify({
            "status": "success",
            "message": "Itération démarrée",
            "task_id": task_id
        })
    except Exception as e:
        current_app.logger.error(f"Erreur lors de l'itération: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"status": "error", "message": str(e)})
        else:
            flash(f"Erreur: {str(e)}", "danger")
            return redirect(url_for('generation.result'))

@bp_generation.route('/download_zip', methods=['GET'])
def download_zip():
    if 'generation_result' not in session:
        flash("Aucun résultat de génération trouvé. Veuillez d'abord générer une application.", "warning")
        return redirect(url_for('ui.index'))
    target_dir = session['generation_result'].get('target_directory')
    if not target_dir or not Path(target_dir).is_dir():
        flash("Répertoire cible introuvable", "danger")
        return redirect(url_for('generation.result'))
    try:
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(target_dir):
                for file in files:
                    if file.startswith('.') or '__pycache__' in root:
                        continue
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, target_dir)
                    zipf.write(file_path, rel_path)
        memory_file.seek(0)
        dir_name = os.path.basename(os.path.normpath(target_dir))
        zip_filename = f"{dir_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
        return send_file(
            memory_file,
            as_attachment=True,
            download_name=zip_filename,
            mimetype='application/zip'
        )
    except Exception as e:
        current_app.logger.error(f"Erreur lors de la création du ZIP: {str(e)}")
        flash(f"Erreur lors de la création du fichier ZIP: {str(e)}", "danger")
        return redirect(url_for('generation.result'))
