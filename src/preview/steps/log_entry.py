"""
Ajoute une entrée de log pour une session de prévisualisation.
"""
import time

def log_entry(session_id: str, level: str, message: str, process_logs=None):
    if process_logs is None:
        from src.preview.preview_manager import process_logs
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log = {"timestamp": timestamp, "level": level, "message": message}
    if session_id not in process_logs:
        process_logs[session_id] = []
    process_logs[session_id].append(log)
