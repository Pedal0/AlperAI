import os
import sys
import uuid
import json
import time
import secrets
import threading
import traceback
from pathlib import Path
from functools import wraps
from threading import Thread
from typing import Dict, List, Union, Optional, Any
import zipfile
import io

import requests
from flask import (
    Flask, render_template, request, jsonify, redirect, 
    url_for, session, flash, send_file, abort, Response
)
from werkzeug.utils import secure_filename

from datetime import datetime
import subprocess
import tempfile

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
        use_selected_path = request.form.get('use_selected_path', 'false') == 'true'
        file_path = request.form.get('file_path', '')
        directory_path = request.form.get('directory_path', '')
        
        if not directory_name:
            return jsonify({"error": "Nom de dossier manquant"}), 400
        
        # Si l'utilisateur demande explicitement d'utiliser le chemin sélectionné
        if use_selected_path:
            # Obtenir le chemin complet à partir du dossier parent du fichier sélectionné
            try:
                # Si un chemin de fichier ou de dossier a été fourni, l'utiliser pour construire le chemin complet
                if file_path:
                    # Pour les sélecteurs de fichiers traditionnels qui renvoient un chemin relatif
                    # Récupérer le dossier de l'utilisateur et ajouter le nom du dossier sélectionné
                    user_dir = os.path.expanduser("~")
                    # Vérifier si le chemin existe déjà, sinon le créer
                    target_path = os.path.join(user_dir, directory_name)
                    if not os.path.exists(target_path):
                        os.makedirs(target_path)
                    return jsonify({"path": target_path})
                
                # Si aucun chemin n'est fourni, utiliser le dossier de l'utilisateur mais laisser 
                # la possibilité à l'utilisateur de changer manuellement
                user_dir = os.path.expanduser("~")
                return jsonify({"path": os.path.join(user_dir, directory_name)})
            except Exception as e:
                app.logger.error(f"Erreur lors du traitement du chemin: {str(e)}")
                # Fallback en cas d'erreur
                user_dir = os.path.expanduser("~")
                return jsonify({"path": os.path.join(user_dir, directory_name)})
        
        # Si nous avons reçu le chemin du dossier directement de l'API File System Access
        elif directory_path:
            # Créer le dossier s'il n'existe pas encore
            full_path = os.path.dirname(directory_path)
            if not os.path.exists(full_path):
                os.makedirs(full_path)
            return jsonify({"path": full_path})
        
        # Méthode par défaut: permettre à l'utilisateur de créer ou choisir un dossier
        # au lieu d'imposer un chemin par défaut
        else:
            # Sur Windows, revenir au dossier Documents de l'utilisateur comme suggestion
            if os.name == 'nt':
                # Obtenir le chemin du dossier Documents
                import subprocess
                try:
                    # Essayer d'obtenir le dossier Documents avec PowerShell
                    docs_dir = subprocess.check_output(
                        ["powershell", "-command", "[Environment]::GetFolderPath('MyDocuments')"], 
                        universal_newlines=True
                    ).strip()
                    
                    # Si le répertoire Documents existe, renvoyer un chemin suggéré
                    if os.path.exists(docs_dir):
                        suggested_path = os.path.join(docs_dir, directory_name)
                        return jsonify({"path": suggested_path})
                    
                except Exception:
                    # En cas d'erreur, revenir au répertoire utilisateur
                    pass
            
            # Pour tous les systèmes d'exploitation, revenir au répertoire de l'utilisateur
            user_dir = os.path.expanduser("~")
            suggested_path = os.path.join(user_dir, directory_name)
            return jsonify({"path": suggested_path})
            
    except Exception as e:
        app.logger.error(f"Erreur lors de la récupération du chemin: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/validate_directory_path', methods=['POST'])
def validate_directory_path():
    """Valider et créer si nécessaire un chemin de répertoire complet"""
    try:
        full_path = request.form.get('full_path', '')
        create_if_missing = request.form.get('create_if_missing', 'false') == 'true'
        
        if not full_path:
            return jsonify({"valid": False, "error": "Chemin non spécifié"}), 400
        
        # Normaliser le chemin pour s'assurer qu'il est dans le bon format
        normalized_path = os.path.normpath(full_path)
        
        # Vérifier si le chemin existe déjà
        if os.path.exists(normalized_path):
            if os.path.isdir(normalized_path):
                # Le chemin existe et c'est un dossier
                return jsonify({"valid": True, "path": normalized_path})
            else:
                # Le chemin existe mais ce n'est pas un dossier
                return jsonify({"valid": False, "error": "Le chemin spécifié existe mais n'est pas un dossier"})
        elif create_if_missing:
            # Essayer de créer le dossier
            try:
                os.makedirs(normalized_path, exist_ok=True)
                return jsonify({"valid": True, "path": normalized_path})
            except Exception as e:
                return jsonify({"valid": False, "error": f"Impossible de créer le dossier: {str(e)}"})
        else:
            return jsonify({"valid": False, "error": "Le dossier spécifié n'existe pas"})
    except Exception as e:
        app.logger.error(f"Erreur lors de la validation du chemin: {str(e)}")
        return jsonify({"valid": False, "error": str(e)}), 500

@app.route('/list_files', methods=['GET'])
def list_files():
    """Liste les fichiers dans un répertoire spécifié"""
    directory = request.args.get('directory')
    if not directory or not os.path.isdir(directory):
        return jsonify({"status": "error", "message": "Répertoire invalide"}), 400
    
    try:
        # Lister les fichiers
        files = []
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path):
                files.append(file)
        
        return jsonify({
            "status": "success",
            "directory": directory,
            "files": files
        })
    except Exception as e:
        app.logger.error(f"Erreur lors de la lecture du répertoire {directory}: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/open_folder', methods=['POST'])
def open_folder():
    """Ouvre un dossier dans l'explorateur de fichiers du système d'exploitation"""
    try:
        data = request.json
        folder_path = data.get('folder_path')
        
        if not folder_path or not os.path.isdir(folder_path):
            return jsonify({"status": "error", "message": "Chemin de dossier invalide"}), 400
        
        # Ouvrir le dossier selon le système d'exploitation
        if os.name == 'nt':  # Windows
            # Sur Windows, on utilise explorer.exe avec le chemin absolu
            os.startfile(folder_path)
        elif os.name == 'posix':  # Linux/Mac
            try:
                # Pour macOS, on utilise 'open'
                if sys.platform == 'darwin':
                    subprocess.Popen(['open', folder_path])
                else:
                    # Pour Linux, on utilise xdg-open
                    subprocess.Popen(['xdg-open', folder_path])
            except Exception as e:
                return jsonify({"status": "error", "message": f"Erreur lors de l'ouverture du dossier: {str(e)}"}), 500
        
        return jsonify({"status": "success", "message": "Dossier ouvert avec succès"})
    except Exception as e:
        app.logger.error(f"Erreur lors de l'ouverture du dossier: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/open_folder_dialog', methods=['GET'])
def open_folder_dialog():
    """Ouvre un sélecteur de dossier natif Windows et renvoie le chemin sélectionné"""
    try:
        if os.name != 'nt':
            return jsonify({"status": "error", "message": "Cette fonctionnalité n'est disponible que sur Windows"}), 400
        
        import subprocess
        import tempfile
        
        # Script PowerShell pour ouvrir un sélecteur de dossier natif Windows
        ps_script = """
        Add-Type -AssemblyName System.Windows.Forms
        $folderBrowser = New-Object System.Windows.Forms.FolderBrowserDialog
        $folderBrowser.Description = "Sélectionnez le dossier où vous souhaitez générer votre application"
        $folderBrowser.RootFolder = [System.Environment+SpecialFolder]::Desktop
        $folderBrowser.ShowNewFolderButton = $true
        
        if ($folderBrowser.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
            $folderBrowser.SelectedPath
        } else {
            "CANCELED"
        }
        """
        
        # Écrire le script dans un fichier temporaire
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".ps1")
        temp_file_path = temp_file.name
        temp_file.write(ps_script.encode('utf-8'))
        temp_file.close()
        
        # Exécuter le script PowerShell
        result = subprocess.check_output(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", temp_file_path],
            universal_newlines=True
        ).strip()
        
        # Supprimer le fichier temporaire
        os.unlink(temp_file_path)
        
        if result == "CANCELED":
            return jsonify({"status": "canceled", "message": "Sélection annulée par l'utilisateur"})
        
        # Vérifier si le chemin existe
        if os.path.exists(result) and os.path.isdir(result):
            return jsonify({"status": "success", "path": result})
        else:
            return jsonify({"status": "error", "message": "Le chemin sélectionné n'est pas valide"})
            
    except Exception as e:
        app.logger.error(f"Erreur lors de l'ouverture du sélecteur de dossier: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_project_structure', methods=['POST'])
def get_project_structure():
    """Récupère la structure du projet généré"""
    if 'generation_result' not in session:
        return jsonify({"status": "error", "message": "Aucun résultat de génération trouvé"}), 400
    
    target_dir = session['generation_result'].get('target_directory')
    if not target_dir or not Path(target_dir).is_dir():
        return jsonify({"status": "error", "message": "Répertoire cible introuvable"}), 400
    
    # Fonction pour construire la structure de répertoire récursivement
    def build_directory_structure(directory_path):
        directory = Path(directory_path)
        result = []
        
        for item in sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if item.name.startswith('.') or '__pycache__' in str(item):
                continue  # Ignorer les fichiers/dossiers cachés et __pycache__
                
            node = {'name': item.name, 'isFolder': item.is_dir()}
            
            if item.is_dir():
                children = build_directory_structure(item)
                if children:  # Ne pas inclure les dossiers vides
                    node['children'] = children
                    
            result.append(node)
            
        return result
    
    try:
        structure = build_directory_structure(target_dir)
        return jsonify({"status": "success", "structure": structure})
    except Exception as e:
        app.logger.error(f"Erreur lors de la récupération de la structure: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

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
        
        # Correction de la récupération de l'état de la case à cocher pour les outils MCP
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
    """Affiche la page de prévisualisation de l'application générée"""
    if 'generation_result' not in session or not session['generation_result'].get('success'):
        flash("Aucune génération réussie trouvée. Veuillez d'abord générer une application.", "warning")
        return redirect(url_for('index'))
        
    target_dir = session['generation_result'].get('target_directory')
    if not target_dir or not Path(target_dir).is_dir():
        flash("Répertoire d'application généré introuvable.", "danger")
        return redirect(url_for('result'))
    
    # Récupérer ou générer un ID de session pour la prévisualisation
    if 'preview_session_id' not in session:
        session['preview_session_id'] = str(uuid.uuid4())
    
    # Pour l'affichage initial, nous ne démarrons pas encore l'application
    # Elle sera démarrée via une requête AJAX après le chargement de la page
    
    return render_template('preview.html', 
                          target_dir=target_dir,
                          preview_session_id=session['preview_session_id'],
                          prompt=session.get('prompt', ''))

@app.route('/preview/start', methods=['POST'])
def start_preview():
    """Démarre la prévisualisation de l'application"""
    # Débogage de la session
    app.logger.info(f"Contenu de la session: {dict(session)}")
    
    if 'generation_result' not in session:
        app.logger.error("Erreur: 'generation_result' n'est pas présent dans la session")
        return jsonify({"status": "error", "message": "Aucun résultat de génération trouvé"}), 400
    
    app.logger.info(f"generation_result dans la session: {session['generation_result']}")
    target_dir = session['generation_result'].get('target_directory')
    if not target_dir or not Path(target_dir).is_dir():
        app.logger.error(f"Erreur: Répertoire cible '{target_dir}' introuvable ou invalide")
        return jsonify({"status": "error", "message": "Répertoire cible introuvable"}), 400
    
    # Utiliser l'ID de session fourni ou celui de la session Flask
    preview_session_id = request.json.get('session_id') if request.json else session.get('preview_session_id')
    if not preview_session_id:
        preview_session_id = str(uuid.uuid4())
        session['preview_session_id'] = preview_session_id
    
    # Nettoyer les ports non utilisés avant de démarrer
    from src.preview.preview_manager import cleanup_unused_ports
    ports_cleaned = cleanup_unused_ports()
    if ports_cleaned > 0:
        app.logger.info(f"{ports_cleaned} ports libérés avant le démarrage")
    
    # Démarrer la prévisualisation avec le module preview_manager
    from src.preview.preview_manager import start_preview
    success, message, info = start_preview(target_dir, preview_session_id)
    
    if success:
        return jsonify({
            "status": "success", 
            "message": message,
            "url": info.get("url"),
            "project_type": info.get("project_type"),
            "logs": info.get("logs", [])
        })
    else:
        return jsonify({
            "status": "error", 
            "message": message,
            "logs": info.get("logs", [])
        }), 500

@app.route('/preview/status', methods=['GET'])
def preview_status():
    """Récupère le statut actuel de la prévisualisation"""
    preview_session_id = session.get('preview_session_id')
    if not preview_session_id:
        # Instead of returning an error, return a valid response with default values
        return jsonify({
            "status": "success", 
            "running": False,
            "url": None,
            "project_type": None,
            "logs": [],
            "message": "No preview session found. Please start a new preview."
        })
    
    # Récupérer le statut depuis le module preview_manager
    from src.preview.preview_manager import get_preview_status
    status_info = get_preview_status(preview_session_id)
    
    return jsonify({
        "status": "success",
        "running": status_info.get("running", False),
        "url": status_info.get("url"),
        "project_type": status_info.get("project_type"),
        "logs": status_info.get("logs", []),
        "duration": status_info.get("duration")
    })

@app.route('/preview/stop', methods=['POST'])
def stop_preview():
    """Arrête la prévisualisation de l'application"""
    preview_session_id = session.get('preview_session_id')
    if not preview_session_id:
        return jsonify({"status": "error", "message": "Aucune session de prévisualisation trouvée"}), 400
    
    # Arrêter la prévisualisation avec le module preview_manager
    from src.preview.preview_manager import stop_preview
    success, message = stop_preview(preview_session_id)
    
    if success:
        return jsonify({"status": "success", "message": message})
    else:
        return jsonify({"status": "error", "message": message}), 500

@app.route('/preview/restart', methods=['POST'])
def restart_preview():
    """Redémarre la prévisualisation de l'application"""
    preview_session_id = session.get('preview_session_id')
    if not preview_session_id:
        return jsonify({"status": "error", "message": "Aucune session de prévisualisation trouvée"})
    
    # Redémarrer la prévisualisation avec le module preview_manager
    from src.preview.preview_manager import restart_preview
    success, message, info = restart_preview(preview_session_id)
    
    if success:
        return jsonify({
            "status": "success", 
            "message": message,
            "url": info.get("url"),
            "project_type": info.get("project_type"),
            "logs": info.get("logs", [])
        })
    else:
        # Retourner un statut d'erreur mais toujours avec le code HTTP 200
        return jsonify({
            "status": "error", 
            "message": message,
            "logs": info.get("logs", [])
        })

@app.route('/preview/refresh', methods=['POST'])
def refresh_preview():
    """Endpoint pour rafraîchir manuellement la prévisualisation"""
    try:
        return jsonify({
            "status": "success",
            "message": "Rafraîchissement manuel demandé"
        })
    except Exception as e:
        app.logger.error(f"Erreur lors du rafraîchissement manuel: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": f"Erreur lors du rafraîchissement: {str(e)}"
        }), 500

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

@app.route('/download_zip', methods=['GET'])
def download_zip():
    """Créer et télécharger un fichier ZIP du projet généré"""
    if 'generation_result' not in session:
        flash("Aucun résultat de génération trouvé. Veuillez d'abord générer une application.", "warning")
        return redirect(url_for('index'))
    
    target_dir = session['generation_result'].get('target_directory')
    if not target_dir or not Path(target_dir).is_dir():
        flash("Répertoire cible introuvable", "danger")
        return redirect(url_for('result'))
    
    try:
        # Créer un buffer mémoire pour stocker le zip
        memory_file = io.BytesIO()
        
        # Créer l'archive ZIP en mémoire
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Parcourir le répertoire et ajouter tous les fichiers
            for root, dirs, files in os.walk(target_dir):
                for file in files:
                    # Ignorer les fichiers cachés et __pycache__
                    if file.startswith('.') or '__pycache__' in root:
                        continue
                    
                    # Chemin absolu du fichier
                    file_path = os.path.join(root, file)
                    
                    # Chemin relatif pour le zip (enlever le chemin de base)
                    rel_path = os.path.relpath(file_path, target_dir)
                    
                    # Ajout du fichier au zip
                    zipf.write(file_path, rel_path)
        
        # Revenir au début du fichier mémoire
        memory_file.seek(0)
        
        # Extraire le nom du dossier pour nommer le fichier zip
        dir_name = os.path.basename(os.path.normpath(target_dir))
        zip_filename = f"{dir_name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
        
        # Envoyer le fichier
        return send_file(
            memory_file,
            as_attachment=True,
            download_name=zip_filename,
            mimetype='application/zip'
        )
    
    except Exception as e:
        app.logger.error(f"Erreur lors de la création du ZIP: {str(e)}")
        flash(f"Erreur lors de la création du fichier ZIP: {str(e)}", "danger")
        return redirect(url_for('result'))

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