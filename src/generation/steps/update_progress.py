"""
Fonction utilitaire : mise à jour de la progression (callback + log).
"""
import logging

def update_progress(step, message, progress=None, progress_callback=None):
    if progress_callback:
        progress_callback(step, message, progress)
    logging.info(f"[Étape {step}] {message}")
