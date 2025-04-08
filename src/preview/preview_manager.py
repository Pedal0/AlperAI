"""
Module de gestion de l'état de prévisualisation.
Contient les fonctions pour gérer l'état de la prévisualisation.
"""
import streamlit as st

def toggle_preview_mode():
    """
    Bascule l'état du mode prévisualisation.
    Si un processus d'application est en cours d'exécution, il est arrêté.
    """
    st.session_state.preview_mode = not st.session_state.preview_mode
    
    # Si on désactive le mode prévisualisation, arrêter le processus en cours d'exécution
    if not st.session_state.preview_mode and st.session_state.app_preview_process:
        try:
            st.session_state.app_preview_process.terminate()
            st.session_state.app_preview_process = None
        except Exception as e:
            st.error(f"Erreur lors de l'arrêt du processus: {e}")

def initialize_preview_state():
    """
    Initialise les variables d'état nécessaires pour la prévisualisation.
    """
    if 'preview_mode' not in st.session_state:
        st.session_state.preview_mode = False
    if 'last_generated_app_path' not in st.session_state:
        st.session_state.last_generated_app_path = ""
    if 'app_preview_process' not in st.session_state:
        st.session_state.app_preview_process = None

def is_preview_mode():
    """
    Vérifie si l'application est en mode prévisualisation.
    
    Returns:
        bool: True si l'application est en mode prévisualisation, False sinon
    """
    return st.session_state.get('preview_mode', False) and st.session_state.get('last_generated_app_path', "")

def launch_preview_mode(project_dir):
    """
    Active le mode prévisualisation et définit le chemin du projet.
    
    Args:
        project_dir (str): Chemin vers le répertoire du projet à prévisualiser
    """
    initialize_preview_state()
    st.session_state.last_generated_app_path = project_dir
    st.session_state.preview_mode = True