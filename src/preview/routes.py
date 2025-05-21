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

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, flash, current_app
import uuid
from pathlib import Path
from src.preview.preview_manager import cleanup_unused_ports, stop_preview, get_preview_status, restart_preview
from src.preview.handler.prepare_and_launch_project import prepare_and_launch_project_async
import asyncio

bp_preview = Blueprint('preview', __name__)

@bp_preview.route('/preview')
def preview():
    if 'generation_result' not in session or not session['generation_result'].get('success'):
        flash("No successful generation found. Please generate an application first.", "warning")
        return redirect(url_for('ui.index'))
    target_dir = session['generation_result'].get('target_directory')
    if not target_dir or not Path(target_dir).is_dir():
        flash("Generated application directory not found.", "danger")
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
        current_app.logger.error("Error: 'generation_result' not found in session")
        return jsonify({"status": "error", "message": "No generation result found"}), 400
    
    target_dir = session['generation_result'].get('target_directory')
    if not target_dir or not Path(target_dir).is_dir():
        current_app.logger.error(f"Error: Target directory '{target_dir}' not found or invalid")
        return jsonify({"status": "error", "message": "Target directory not found"}), 400
    
    project_name = Path(target_dir).name

    preview_session_id = request.json.get('session_id') if request.json else session.get('preview_session_id')
    if not preview_session_id:
        preview_session_id = str(uuid.uuid4())
        session['preview_session_id'] = preview_session_id
    
    # Extract AI model from session or request
    ai_model = None
    if request.json and 'model' in request.json:
        ai_model = request.json['model']
    elif 'model' in session:
        ai_model = session['model']
    
    ports_cleaned = cleanup_unused_ports()
    if ports_cleaned > 0:
        current_app.logger.info(f"{ports_cleaned} ports freed before starting")

    # Pass ai_model to prepare_and_launch_project_async
    result = asyncio.run(prepare_and_launch_project_async(project_name, target_dir, ai_model=ai_model))

    if result and result[0]:
        # result = (success, message, url/port)
        return jsonify({
            "status": "success", 
            "message": result[1] or "Preview started successfully.",
            "url": result[2] if len(result) > 2 else None
        })
    else:
        return jsonify({
            "status": "error", 
            "message": result[1] if result and len(result) > 1 else "Failed to start preview.",
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
        return jsonify({"status": "error", "message": "No preview session found"}), 400
    success, message = stop_preview(preview_session_id)
    if success:
        return jsonify({"status": "success", "message": message})
    else:
        return jsonify({"status": "error", "message": message}), 500

@bp_preview.route('/preview/restart', methods=['POST'])
def restart_preview_route():
    preview_session_id = session.get('preview_session_id')
    if not preview_session_id:
        return jsonify({"status": "error", "message": "No preview session found"})
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
            "message": "Manual refresh requested"
        })
    except Exception as e:
        current_app.logger.error(f"Error during manual refresh: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": f"Error during refresh: {str(e)}"
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
            current_app.logger.warning("Attempt to stop without session ID")
            return '', 204
        success, message = stop_preview(session_id)
        current_app.logger.info(f"Stopped application on page exit: {success}, {message}")
        return '', 204
    except Exception as e:
        current_app.logger.error(f"Error during stop on exit: {str(e)}")
        return '', 204

@bp_preview.route('/list_files', methods=['GET'])
def list_files_route():
    """List all files in the given directory, relative paths."""
    from flask import request
    import os
    dir_path = request.args.get('directory')
    if not dir_path or not Path(dir_path).is_dir():
        return jsonify(status="error", message="Invalid directory"), 400
    file_list = []
    for root, dirs, files in os.walk(dir_path):
        for fname in files:
            rel = os.path.relpath(os.path.join(root, fname), dir_path)
            file_list.append(rel.replace('\\', '/'))
    return jsonify(status="success", files=file_list)

@bp_preview.route('/preview/stop_all', methods=['POST'])
def stop_all_previews():
    try:
        from src.preview.steps.cleanup_all_processes import cleanup_all_processes
        cleanup_all_processes()
        current_app.logger.info("All preview processes cleaned up via /preview/stop_all")
        return '', 204
    except Exception as e:
        current_app.logger.error(f"Error during stop_all_previews: {str(e)}")
        return '', 204
