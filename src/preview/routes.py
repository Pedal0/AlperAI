from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, flash, current_app
import uuid
from pathlib import Path
from src.preview.preview_manager import cleanup_unused_ports, start_preview, stop_preview, get_preview_status, restart_preview

bp_preview = Blueprint('preview', __name__)

@bp_preview.route('/preview')
def preview():
    if 'generation_result' not in session or not session['generation_result'].get('success'):
        flash("Aucune génération réussie trouvée. Veuillez d'abord générer une application.", "warning")
        return redirect(url_for('ui.index'))
    target_dir = session['generation_result'].get('target_directory')
    if not target_dir or not Path(target_dir).is_dir():
        flash("Répertoire d'application généré introuvable.", "danger")
        return redirect(url_for('generation.result', _external=True))
    if 'preview_session_id' not in session:
        session['preview_session_id'] = str(uuid.uuid4())
    return render_template('preview.html', 
                          target_dir=target_dir,
                          preview_session_id=session['preview_session_id'],
                          prompt=session.get('prompt', ''))

@bp_preview.route('/preview/start', methods=['POST'])
def start_preview_route():
    if 'generation_result' not in session:
        current_app.logger.error("Erreur: 'generation_result' n'est pas présent dans la session")
        return jsonify({"status": "error", "message": "Aucun résultat de génération trouvé"}), 400
    target_dir = session['generation_result'].get('target_directory')
    if not target_dir or not Path(target_dir).is_dir():
        current_app.logger.error(f"Erreur: Répertoire cible '{target_dir}' introuvable ou invalide")
        return jsonify({"status": "error", "message": "Répertoire cible introuvable"}), 400
    preview_session_id = request.json.get('session_id') if request.json else session.get('preview_session_id')
    if not preview_session_id:
        preview_session_id = str(uuid.uuid4())
        session['preview_session_id'] = preview_session_id
    ports_cleaned = cleanup_unused_ports()
    if ports_cleaned > 0:
        current_app.logger.info(f"{ports_cleaned} ports libérés avant le démarrage")
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

@bp_preview.route('/preview/status', methods=['GET'])
def preview_status():
    preview_session_id = session.get('preview_session_id')
    if not preview_session_id:
        return jsonify({
            "status": "success", 
            "running": False,
            "url": None,
            "project_type": None,
            "logs": [],
            "message": "No preview session found. Please start a new preview."
        })
    status_info = get_preview_status(preview_session_id)
    return jsonify({
        "status": "success",
        "running": status_info.get("running", False),
        "url": status_info.get("url"),
        "project_type": status_info.get("project_type"),
        "logs": status_info.get("logs", []),
        "duration": status_info.get("duration")
    })

@bp_preview.route('/preview/stop', methods=['POST'])
def stop_preview_route():
    preview_session_id = session.get('preview_session_id')
    if not preview_session_id:
        return jsonify({"status": "error", "message": "Aucune session de prévisualisation trouvée"}), 400
    success, message = stop_preview(preview_session_id)
    if success:
        return jsonify({"status": "success", "message": message})
    else:
        return jsonify({"status": "error", "message": message}), 500

@bp_preview.route('/preview/restart', methods=['POST'])
def restart_preview_route():
    preview_session_id = session.get('preview_session_id')
    if not preview_session_id:
        return jsonify({"status": "error", "message": "Aucune session de prévisualisation trouvée"})
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
        return jsonify({
            "status": "error", 
            "message": message,
            "logs": info.get("logs", [])
        })

@bp_preview.route('/preview/refresh', methods=['POST'])
def refresh_preview():
    try:
        return jsonify({
            "status": "success",
            "message": "Rafraîchissement manuel demandé"
        })
    except Exception as e:
        current_app.logger.error(f"Erreur lors du rafraîchissement manuel: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": f"Erreur lors du rafraîchissement: {str(e)}"
        }), 500

@bp_preview.route('/preview/stop_on_exit', methods=['POST'])
def stop_preview_on_exit():
    try:
        if request.data:
            try:
                data = request.data
                import json as _json
                data = _json.loads(data)
                session_id = data.get('session_id')
            except:
                session_id = None
        else:
            session_id = request.json.get('session_id') if request.json else None
        if not session_id:
            session_id = session.get('preview_session_id')
        if not session_id:
            current_app.logger.warning("Tentative d'arrêt sans ID de session")
            return '', 204
        success, message = stop_preview(session_id)
        current_app.logger.info(f"Arrêt d'application sur sortie de page: {success}, {message}")
        return '', 204
    except Exception as e:
        current_app.logger.error(f"Erreur lors de l'arrêt sur sortie: {str(e)}")
        return '', 204
