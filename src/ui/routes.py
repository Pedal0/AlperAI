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

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, flash, current_app, send_file
import os
import sys
import subprocess
import tempfile
from pathlib import Path

bp_ui = Blueprint('ui', __name__)

@bp_ui.route('/')
def index():
    from src.utils.env_utils import get_openrouter_api_key, is_vercel_environment
    from src.api.list_openrouter_models import get_openrouter_models
    is_vercel = is_vercel_environment()
    models = get_openrouter_models()
    return render_template('index.html', api_key=get_openrouter_api_key(), is_vercel=is_vercel, models=models)

@bp_ui.route('/about')
def about():
    return render_template('about.html')

@bp_ui.route('/get_directory_path', methods=['POST'])
def get_directory_path():
    try:
        directory_name = request.form.get('directory_name', '')
        use_selected_path = request.form.get('use_selected_path', 'false') == 'true'
        file_path = request.form.get('file_path', '')
        directory_path = request.form.get('directory_path', '')
        if not directory_name:
            return jsonify({"error": "Nom de dossier manquant"}), 400
        if use_selected_path:
            try:
                if file_path:
                    user_dir = os.path.expanduser("~")
                    target_path = os.path.join(user_dir, directory_name)
                    if not os.path.exists(target_path):
                        os.makedirs(target_path)
                    return jsonify({"path": target_path})
                user_dir = os.path.expanduser("~")
                return jsonify({"path": os.path.join(user_dir, directory_name)})
            except Exception as e:
                current_app.logger.error(f"Erreur lors du traitement du chemin: {str(e)}")
                user_dir = os.path.expanduser("~")
                return jsonify({"path": os.path.join(user_dir, directory_name)})
        elif directory_path:
            full_path = os.path.dirname(directory_path)
            if not os.path.exists(full_path):
                os.makedirs(full_path)
            return jsonify({"path": full_path})
        else:
            if os.name == 'nt':
                try:
                    docs_dir = subprocess.check_output(
                        ["powershell", "-command", "[Environment]::GetFolderPath('MyDocuments')"],
                        universal_newlines=True
                    ).strip()
                    if os.path.exists(docs_dir):
                        suggested_path = os.path.join(docs_dir, directory_name)
                        return jsonify({"path": suggested_path})
                except Exception:
                    pass
            user_dir = os.path.expanduser("~")
            suggested_path = os.path.join(user_dir, directory_name)
            return jsonify({"path": suggested_path})
    except Exception as e:
        current_app.logger.error(f"Erreur lors de la récupération du chemin: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp_ui.route('/validate_directory_path', methods=['POST'])
def validate_directory_path():
    try:
        full_path = request.form.get('full_path', '')
        create_if_missing = request.form.get('create_if_missing', 'false') == 'true'
        if not full_path:
            return jsonify({"valid": False, "error": "Chemin non spécifié"}), 400
        normalized_path = os.path.normpath(full_path)
        if os.path.exists(normalized_path):
            if os.path.isdir(normalized_path):
                return jsonify({"valid": True, "path": normalized_path})
            else:
                return jsonify({"valid": False, "error": "Le chemin spécifié existe mais n'est pas un dossier"})
        elif create_if_missing:
            try:
                os.makedirs(normalized_path, exist_ok=True)
                return jsonify({"valid": True, "path": normalized_path})
            except Exception as e:
                return jsonify({"valid": False, "error": f"Impossible de créer le dossier: {str(e)}"})
        else:
            return jsonify({"valid": False, "error": "Le dossier spécifié n'existe pas"})
    except Exception as e:
        current_app.logger.error(f"Erreur lors de la validation du chemin: {str(e)}")
        return jsonify({"valid": False, "error": str(e)}), 500

@bp_ui.route('/list_files', methods=['GET'])
def list_files():
    directory = request.args.get('directory')
    if not directory or not os.path.isdir(directory):
        return jsonify({"status": "error", "message": "Répertoire invalide"}), 400
    try:
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
        current_app.logger.error(f"Erreur lors de la lecture du répertoire {directory}: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@bp_ui.route('/open_folder', methods=['POST'])
def open_folder():
    try:
        data = request.json
        folder_path = data.get('folder_path')
        if not folder_path or not os.path.isdir(folder_path):
            return jsonify({"status": "error", "message": "Chemin de dossier invalide"}), 400
        if os.name == 'nt':
            os.startfile(folder_path)
        elif os.name == 'posix':
            try:
                if sys.platform == 'darwin':
                    subprocess.Popen(['open', folder_path])
                else:
                    subprocess.Popen(['xdg-open', folder_path])
            except Exception as e:
                return jsonify({"status": "error", "message": f"Erreur lors de l'ouverture du dossier: {str(e)}"}), 500
        return jsonify({"status": "success", "message": "Dossier ouvert avec succès"})
    except Exception as e:
        current_app.logger.error(f"Erreur lors de l'ouverture du dossier: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@bp_ui.route('/open_folder_dialog', methods=['GET'])
def open_folder_dialog():
    try:
        if os.name != 'nt':
            return jsonify({"status": "error", "message": "Cette fonctionnalité n'est disponible que sur Windows"}), 400
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
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".ps1")
        temp_file_path = temp_file.name
        temp_file.write(ps_script.encode('utf-8'))
        temp_file.close()
        result = subprocess.check_output(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", temp_file_path],
            universal_newlines=True
        ).strip()
        os.unlink(temp_file_path)
        if result == "CANCELED":
            return jsonify({"status": "canceled", "message": "Sélection annulée par l'utilisateur"})
        if os.path.exists(result) and os.path.isdir(result):
            return jsonify({"status": "success", "path": result})
        else:
            return jsonify({"status": "error", "message": "Le chemin sélectionné n'est pas valide"})
    except Exception as e:
        current_app.logger.error(f"Erreur lors de l'ouverture du sélecteur de dossier: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@bp_ui.route('/get_project_structure', methods=['POST'])
def get_project_structure():
    if 'generation_result' not in session:
        return jsonify({"status": "error", "message": "Aucun résultat de génération trouvé"}), 400
    target_dir = session['generation_result'].get('target_directory')
    if not target_dir or not Path(target_dir).is_dir():
        return jsonify({"status": "error", "message": "Répertoire cible introuvable"}), 400
    def build_directory_structure(directory_path):
        directory = Path(directory_path)
        result = []
        items_sorted = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        for item in items_sorted:
            if item.name.startswith('.') or item.name == '__pycache__':
                continue
            node = {'name': item.name, 'type': 'folder' if item.is_dir() else 'file'}
            if item.is_dir():
                children = build_directory_structure(item)
                node['children'] = children
            result.append(node)
        return result
    try:
        structure = build_directory_structure(target_dir)
        return jsonify({"status": "success", "structure": structure})
    except Exception as e:
        current_app.logger.error(f"Erreur lors de la récupération de la structure: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@bp_ui.route('/ping')
def ping():
    return jsonify({"status": "ok", "message": "Le serveur fonctionne correctement!"})
