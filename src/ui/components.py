import streamlit as st
import sys
from src.utils.config import save_api_key, load_api_key


def show_header():
    """Affiche l'en-tête de l'application"""
    st.title("AI Application Generator")
    st.markdown("""
    This tool uses AI to generate complete applications based on your description.
    Just provide a detailed description of what you want to build, set the output directory,
    and click "Generate Application".
    """)


def show_sidebar():
    """Affiche et gère la barre latérale de configuration"""
    st.sidebar.header("Configuration")

    # Initialisation de l'état API key
    if 'api_key' not in st.session_state:
        api_key = load_api_key()
        st.session_state.api_key = api_key

    # Champ de saisie de l'API key
    api_key_input = st.sidebar.text_input(
        "OpenAI API Key",
        value=st.session_state.api_key,
        type="password",
        help="Enter your OpenAI API key here. It will be used for all AI operations."
    )

    # Mise à jour de l'API key
    if api_key_input != st.session_state.api_key:
        st.session_state.api_key = api_key_input

    # Bouton de sauvegarde de l'API key
    if st.sidebar.button("Save API Key"):
        if st.session_state.api_key:
            if save_api_key(st.session_state.api_key):
                st.sidebar.success("API key saved successfully to .env file!")
            else:
                st.sidebar.error("Failed to save API key.")
        else:
            st.sidebar.error("Please enter an API key to save.")

    # Informations sur la plateforme
    st.sidebar.divider()
    st.sidebar.markdown("### Platform Info")
    st.sidebar.info(f"Running on: {sys.platform}")

    return st.session_state.api_key
