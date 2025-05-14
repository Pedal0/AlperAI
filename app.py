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
import atexit

import requests
from flask import (
    Flask, render_template, request, jsonify, redirect, 
    url_for, session, flash, send_file, abort, Response, current_app
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
from src.generation.routes import bp_generation
from src.preview.routes import bp_preview
from src.ui.routes import bp_ui

# Create Flask app
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Generate a secure secret key
app.config['SESSION_TYPE'] = 'filesystem'
app.config['is_vercel_project'] = False  # Par défaut, pas un projet temporaire Vercel

# Register blueprints
app.register_blueprint(bp_generation)
app.register_blueprint(bp_preview)
app.register_blueprint(bp_ui)

# Dictionnaire global pour stocker l'état de progression des tâches de génération
generation_tasks = {}

# Load environment variables at startup
load_env_vars()

# Enregistrer la fonction de nettoyage des processus à l'arrêt de l'application
@atexit.register
def cleanup_on_exit():
    """Nettoie tous les processus et ressources à l'arrêt de l'application Flask"""
    app.logger.info("Arrêt de l'application, nettoyage des processus...")
    try:
        from src.preview.preview_manager import cleanup_all_processes
        cleanup_all_processes()
        app.logger.info("Nettoyage des processus terminé")
    except Exception as e:
        app.logger.error(f"Erreur lors du nettoyage des processus: {str(e)}")

# Modifier le contexte Jinja2 pour ajouter des fonctions utiles
@app.context_processor
def utility_processor():
    def now():
        return datetime.now()
    
    return dict(now=now)

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
    app.run(debug=False, use_reloader=False)