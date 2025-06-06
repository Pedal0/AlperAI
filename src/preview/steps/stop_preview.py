"""
Arrête la prévisualisation d'une application.
"""
import time
import platform
import subprocess
from src.preview.steps.log_entry import log_entry

def stop_preview(session_id: str, running_processes=None, process_logs=None, session_ports=None, logger=None):
    if running_processes is None or process_logs is None or session_ports is None or logger is None:
        from src.preview.preview_manager import running_processes, process_logs, session_ports, logger
    if session_id not in running_processes:
        # Appel du nettoyage global si aucun process n'est trouvé (force le même comportement que lors de l'arrêt du serveur Flask)
        try:
            from src.preview.steps.cleanup_all_processes import cleanup_all_processes
            cleanup_all_processes()
        except Exception as e:
            if logger is not None:
                logger.error(f"Erreur lors du cleanup_all_processes: {str(e)}")
        return False, "Aucun processus en cours d'exécution pour cette session (nettoyage global forcé)"
    
    try:
        process_info = running_processes[session_id]
        process = process_info["process"]
        log_entry(session_id, "INFO", "Arrêt de l'application...")
        
        # Close the process streams before termination to avoid I/O errors
        try:
            if process.stdout and not process.stdout.closed:
                process.stdout.close()
        except:
            pass
            
        try:
            if process.stderr and not process.stderr.closed:
                process.stderr.close()
        except:
            pass
            
        # Terminate the process
        if platform.system() == "Windows":
            subprocess.call(['taskkill', '/F', '/T', '/PID', str(process.pid)])
        else:
            process.terminate()
            time.sleep(1)
            if process.poll() is None:
                process.kill()
                
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning(f"Process {process.pid} did not terminate within timeout")
            
        log_entry(session_id, "INFO", "Application arrêtée avec succès")
        del running_processes[session_id]
        if session_id in session_ports:
            logger.info(f"Libération du port pour la session {session_id}")
            del session_ports[session_id]
        return True, "Application arrêtée avec succès"
    except Exception as e:
        if logger is None:
            from src.preview.preview_manager import logger
        logger.error(f"Erreur lors de l'arrêt de la prévisualisation: {str(e)}")
        log_entry(session_id, "ERROR", f"Erreur lors de l'arrêt: {str(e)}")
        if session_id in running_processes:
            del running_processes[session_id]
        if session_id in session_ports:
            del session_ports[session_id]
        return False, f"Erreur: {str(e)}"