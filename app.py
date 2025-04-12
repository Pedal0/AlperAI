import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, abort
from pathlib import Path
import time
import json
import secrets
import threading
from datetime import datetime
import subprocess
import tempfile
import uuid

# Import from restructured modules
from src.config.constants import RATE_LIMIT_DELAY_SECONDS
from src.utils.env_utils import load_env_vars, get_openrouter_api_key
from src.generation.generation_flow import generate_application, process_urls
from src.utils.prompt_utils import extract_urls_from_prompt, prompt_mentions_design
from src.mcp.tool_utils import get_default_tools
from src.api.openrouter_api import generate_code_with_openrouter

# Create Flask app
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Generate a secure secret key
app.config['SESSION_TYPE'] = 'filesystem'

# Dictionnaire global pour stocker l'état de progression des tâches de génération
generation_tasks = {}

# Load environment variables at startup
load_env_vars()

# Modifier le contexte Jinja2 pour ajouter des fonctions utiles
@app.context_processor
def utility_processor():
    def now():
        return datetime.now()
    
    return dict(now=now)

# Routes principales
@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html', api_key=get_openrouter_api_key())

@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')

@app.route('/get_directory_path', methods=['POST'])
def get_directory_path():
    """Récupérer le chemin complet d'un dossier à partir de son nom"""
    try:
        directory_name = request.form.get('directory_name', '')
        if not directory_name:
            return jsonify({"error": "Nom de dossier manquant"}), 400
        
        # Méthode Windows pour obtenir un chemin complet
        if os.name == 'nt':
            # Essayer d'obtenir l'emplacement des dossiers des utilisateurs avec PowerShell
            try:
                # Créer un répertoire temporaire pour l'utilisateur s'il n'existe pas déjà
                user_dir = os.path.expanduser("~")
                projects_dir = os.path.join(user_dir, "Projects")
                if not os.path.exists(projects_dir):
                    os.makedirs(projects_dir)
                
                target_path = os.path.join(projects_dir, directory_name)
                
                # Créer le dossier cible s'il n'existe pas
                if not os.path.exists(target_path):
                    os.makedirs(target_path)
                
                return jsonify({"path": target_path})
                
            except Exception as e:
                app.logger.error(f"Erreur lors de la récupération du chemin avec PowerShell: {str(e)}")
                # Fallback: utiliser un chemin par défaut
                user_dir = os.path.expanduser("~")
                return jsonify({"path": os.path.join(user_dir, "Projects", directory_name)})
        else:
            # Pour les systèmes Unix/Linux/Mac
            user_dir = os.path.expanduser("~")
            projects_dir = os.path.join(user_dir, "Projects")
            if not os.path.exists(projects_dir):
                os.makedirs(projects_dir)
                
            target_path = os.path.join(projects_dir, directory_name)
            
            # Créer le dossier cible s'il n'existe pas
            if not os.path.exists(target_path):
                os.makedirs(target_path)
            
            return jsonify({"path": target_path})
    except Exception as e:
        app.logger.error(f"Erreur lors de la récupération du chemin: {str(e)}")
        return jsonify({"error": str(e)}), 500

def generate_application_thread(task_id, api_key, model, prompt, target_dir, use_mcp, 
                              frontend_framework, include_animations, empty_files_check):
    """Fonction exécutée dans un thread pour générer l'application"""
    try:
        from src.generation.generation_flow import generate_application
        from src.utils.model_utils import is_free_model
        
        # Fonction de callback pour la mise à jour de la progression
        def update_progress_callback(step, message, progress=None):
            if progress is not None:
                generation_tasks[task_id]['progress'] = progress
            if message:
                generation_tasks[task_id]['current_step'] = message
            app.logger.info(f"[Étape {step}] {message}")
        
        # Appel à la fonction de génération avec le callback de progression
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
        
        # En fonction du résultat de la génération
        if success:
            from pathlib import Path
            
            # Récupérer la liste des fichiers créés
            files_written = []
            files_still_empty = []
            
            for root, dirs, files in os.walk(target_dir):
                for file in files:
                    rel_path = os.path.relpath(os.path.join(root, file), target_dir)
                    rel_path = os.path.normpath(rel_path)
                    files_written.append(rel_path)
                    if os.path.getsize(os.path.join(root, file)) == 0:
                        files_still_empty.append(rel_path)
            
            # Mettre à jour l'état de la tâche
            generation_tasks[task_id]['progress'] = 100
            generation_tasks[task_id]['status'] = 'completed'
            generation_tasks[task_id]['result'] = {
                'success': True,
                'target_directory': target_dir,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'files_created': len(files_written),
                'file_list': files_written,
                'files_still_empty': files_still_empty,
                'prompt': prompt,
                'reformulated_prompt': app.config.get('reformulated_prompt', '')
            }
            
            app.logger.info(f"Génération terminée. {len(files_written)} fichiers créés, {len(files_still_empty)} fichiers toujours vides.")
        else:
            generation_tasks[task_id]['status'] = 'failed'
            generation_tasks[task_id]['error'] = "Échec de la génération de l'application"
            app.logger.error("Échec de la génération de l'application")
            
    except Exception as e:
        import traceback
        app.logger.error(f"Erreur lors de la génération: {str(e)}")
        app.logger.error(traceback.format_exc())
        generation_tasks[task_id]['error'] = str(e)
        generation_tasks[task_id]['status'] = 'failed'

@app.route('/generate', methods=['POST'])
def generate():
    """Generate application based on user input"""
    try:
        data = request.form
        api_key = data.get('api_key', '')
        model = data.get('model', 'google/gemini-2.5-pro-exp-03-25:free')
        prompt = data.get('user_prompt', '')
        target_dir = data.get('target_directory', '')
        use_mcp = data.get('use_mcp_tools', 'on') == 'on'
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
        
        thread = threading.Thread(
            target=generate_application_thread,
            args=(task_id, api_key, model, prompt, target_dir, use_mcp, frontend_framework, include_animations, empty_files_check)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "status": "success",
            "message": "Génération démarrée",
            "task_id": task_id
        })
    
    except Exception as e:
        app.logger.error(f"Erreur lors de la génération: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"status": "error", "message": str(e)})
        else:
            flash(f"Erreur: {str(e)}", "danger")
            return redirect(url_for('index'))

@app.route('/generation_progress', methods=['GET'])
def generation_progress():
    """Récupérer l'état de progression de la génération"""
    task_id = session.get('generation_task_id')
    
    if not task_id or task_id not in generation_tasks:
        return jsonify({
            "status": "error",
            "message": "Aucune tâche de génération trouvée"
        })
    
    task = generation_tasks[task_id]
    
    if task['status'] == 'completed' and task['result']:
        session['generation_result'] = task['result']
    
    response = {
        "status": task['status'],
        "progress": task['progress'],
        "current_step": task['current_step']
    }
    
    if task['status'] == 'completed':
        response["redirect_url"] = url_for('result')
    elif task['status'] == 'failed':
        response["error"] = task['error']
    
    return jsonify(response)

@app.route('/result')
def result():
    """Show generation result"""
    if 'generation_result' not in session:
        flash("Aucun résultat de génération trouvé. Veuillez d'abord générer une application.", "warning")
        return redirect(url_for('index'))
        
    return render_template('result.html', 
                          result=session['generation_result'],
                          prompt=session.get('prompt', ''),
                          target_dir=session.get('target_dir', ''))

@app.route('/preview')
def preview():
    """Preview the generated application"""
    if 'generation_result' not in session or not session['generation_result'].get('success'):
        flash("Aucune génération réussie trouvée. Veuillez d'abord générer une application.", "warning")
        return redirect(url_for('index'))
        
    target_dir = session['generation_result'].get('target_directory')
    if not target_dir or not Path(target_dir).is_dir():
        flash("Répertoire d'application généré introuvable.", "danger")
        return redirect(url_for('result'))
        
    return render_template('preview.html', 
                          target_dir=target_dir,
                          prompt=session.get('prompt', ''))

@app.route('/iterate', methods=['POST'])
def iterate_generation():
    """Continue l'itération de la génération pour améliorer le code"""
    if 'generation_result' not in session:
        flash("Aucun résultat de génération trouvé. Veuillez d'abord générer une application.", "warning")
        return redirect(url_for('index'))
    
    try:
        data = request.form
        api_key = data.get('api_key', '')
        model = data.get('model', session.get('model', 'google/gemini-2.5-pro-exp-03-25:free'))
        feedback = data.get('feedback', '')
        target_dir = session.get('target_dir', '')
        reformulated_prompt = session['generation_result'].get('reformulated_prompt', '')
        
        if not api_key:
            flash("Clé API requise", "danger")
            return redirect(url_for('result'))
        if not feedback:
            flash("Veuillez fournir des instructions pour l'itération", "danger")
            return redirect(url_for('result'))
        if not target_dir or not Path(target_dir).is_dir():
            flash("Répertoire cible introuvable", "danger")
            return redirect(url_for('result'))
            
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
        app.logger.error(f"Erreur lors de l'itération: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"status": "error", "message": str(e)})
        else:
            flash(f"Erreur: {str(e)}", "danger")
            return redirect(url_for('result'))

@app.route('/continue_iteration', methods=['POST'])
def continue_iteration():
    """Continue l'itération de la génération avec des instructions supplémentaires"""
    if 'generation_result' not in session:
        flash("Aucun résultat de génération trouvé. Veuillez d'abord générer une application.", "warning")
        return redirect(url_for('index'))
    
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
            return redirect(url_for('result'))
        if not feedback:
            flash("Veuillez fournir des instructions pour l'itération", "danger")
            return redirect(url_for('result'))
        if not target_dir or not Path(target_dir).is_dir():
            flash("Répertoire cible introuvable", "danger")
            return redirect(url_for('result'))
            
        task_id = str(uuid.uuid4())
        session['generation_task_id'] = task_id
        
        # Sauvegarder l'historique des itérations
        if 'iteration_history' not in session:
            session['iteration_history'] = []
        
        # Ajouter l'itération actuelle à l'historique
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
        app.logger.error(f"Erreur lors de l'itération: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"status": "error", "message": str(e)})
        else:
            flash(f"Erreur: {str(e)}", "danger")
            return redirect(url_for('result'))

def iterate_application_thread(task_id, api_key, model, reformulated_prompt, feedback, target_dir):
    """Fonction exécutée dans un thread pour itérer sur l'application générée"""
    try:
        from src.api.openrouter_api import extract_files_from_response, generate_code_with_openrouter
        
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
            app.logger.error(f"Erreur lors de la lecture des fichiers existants: {str(e)}")
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
            
        system_prompt = """Vous êtes un expert en développement logiciel. Votre tâche est d'améliorer le code 
        existant d'une application selon les instructions de l'utilisateur.
        
        Ne générez que les fichiers qui doivent être modifiés ou ajoutés.
        
        Pour chaque fichier à modifier ou ajouter, indiquez clairement:
        
        ```
        FILE: <chemin/du/fichier>
        ```
        
        Suivi du contenu complet du fichier après modifications.
        Ne tronquez pas le code et fournissez des implémentations complètes.
        Assurez-vous d'être précis quant aux chemins des fichiers.
        """
        
        user_prompt = f"""Voici la description originale du projet:
        
        {reformulated_prompt}
        
        Voici un aperçu du code existant:
        
        {code_summary}
        
        Itération demandée par l'utilisateur:
        
        {feedback}
        
        Veuillez améliorer le code existant selon ces instructions. 
        Fournissez uniquement les fichiers qui doivent être modifiés ou ajoutés."""
        
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
            app.logger.warning("Aucun fichier n'a été extrait de la réponse de l'API.")
            code_response_text = response.get('content', '')
            import re
            file_blocks = re.findall(r'FILE: (.+?)\n```[\w\+]*\n(.*?)```', code_response_text, re.DOTALL)
            
            for file_path, content in file_blocks:
                norm_path = os.path.normpath(file_path.strip())
                modified_files[norm_path] = content.strip()
            
            if not modified_files:
                app.logger.error("Échec de l'extraction des fichiers modifiés, même avec la méthode de secours.")
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
                app.logger.info(f"Fichier modifié écrit: {full_path}")
                    
            except Exception as e:
                app.logger.error(f"Erreur lors de l'écriture du fichier {file_path}: {str(e)}")
        
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
        
        app.logger.info(f"Itération terminée. {len(files_written)} fichiers modifiés.")
            
    except Exception as e:
        app.logger.error(f"Erreur lors de l'itération: {str(e)}")
        generation_tasks[task_id]['error'] = str(e)
        generation_tasks[task_id]['status'] = 'failed'

# Gestion des erreurs
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', 
                           code=404, 
                           message="Page introuvable", 
                           description="La page que vous recherchez n'existe pas ou a été déplacée."), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', 
                           code=500, 
                           message="Erreur serveur", 
                           description="Une erreur interne s'est produite. Veuillez réessayer plus tard."), 500

@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', 
                           code=403, 
                           message="Accès interdit", 
                           description="Vous n'avez pas les permissions nécessaires pour accéder à cette ressource."), 403

# Route de test pour vérifier que le serveur fonctionne
@app.route('/ping')
def ping():
    return jsonify({"status": "ok", "message": "Le serveur fonctionne correctement!"})

if __name__ == '__main__':
    app.run(debug=True)

