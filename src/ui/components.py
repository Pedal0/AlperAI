"""
UI components for the Streamlit application.
Contains functions for rendering different parts of the UI.
"""
import streamlit as st
from src.config.constants import DEFAULT_MODEL, RATE_LIMIT_DELAY_SECONDS

def setup_page_config():
    """Set up the Streamlit page configuration."""
    st.set_page_config(layout="wide", page_title="CodeGen App")
    st.title("✨ Générateur d'Application Web via IA ✨")
    st.markdown("Décrivez votre application, fournissez un chemin, et laissez l'IA générer le code !")

def render_sidebar():
    """
    Render the sidebar configuration UI.
    
    Returns:
        tuple: (api_key, selected_model)
    """
    with st.sidebar:
        st.header("⚙️ Configuration")
        api_key = st.text_input("Clé API OpenRouter", type="password", help="Votre clé API OpenRouter. Elle ne sera pas stockée.")
        selected_model = st.text_input("Modèle OpenRouter", value=DEFAULT_MODEL, help=f"Ex: {DEFAULT_MODEL}, meta-llama/llama-3-70b-instruct, etc.")
        st.caption(f"Utilise l'API OpenRouter. Délai de {RATE_LIMIT_DELAY_SECONDS}s appliqué si modèle ':free' ou Gemini Flash détecté.")
    
    return api_key, selected_model

def render_input_columns():
    """
    Render the main input columns for user prompt and target directory.
    
    Returns:
        tuple: (user_prompt, target_directory)
    """
    col1, col2 = st.columns(2)
    
    with col1:
        st.header("1. Décrivez votre application")
        user_prompt = st.text_area(
            "Prompt initial:",
            height=200,
            placeholder="Exemple: Crée une simple application de TODO list en Flask avec une base de données SQLite. L'utilisateur doit pouvoir ajouter, voir et supprimer des tâches."
        )
    
    with col2:
        st.header("2. Où générer le projet ?")
        target_directory = st.text_input(
            "Chemin du dossier de destination:",
            placeholder="Ex: C:\\Users\\VotreNom\\Projets\\MonAppGeneree",
            help="Le chemin absolu vers un dossier existant où le projet sera créé."
        )
        st.info("Assurez-vous que le dossier existe et que vous avez les permissions d'écriture.", icon="📁")
    
    return user_prompt, target_directory

def show_response_expander():
    """Show an expander with the last generated code (for debugging)."""
    if st.session_state.get('last_code_generation_response', ''):
        st.markdown("---")
        with st.expander("Voir le dernier code brut généré par l'IA (Étape 3)", expanded=False):
            st.code(st.session_state.last_code_generation_response, language='markdown')
