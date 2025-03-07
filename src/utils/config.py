import os
import logging
import streamlit as st  # Ajout de cette importation
from dotenv import set_key

logger = logging.getLogger(__name__)


def save_api_key(api_key):
    """Sauvegarde l'API key dans le fichier .env"""
    try:
        env_path = os.path.join(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))), '.env')
        set_key(env_path, "OPENAI_API_KEY", api_key)
        return True
    except Exception as e:
        logger.error(f"Failed to save API key: {e}")
        return False


def load_api_key():
    """Charge l'API key depuis le fichier .env"""
    return os.getenv("OPENAI_API_KEY", "")


def get_api_key():
    """Récupère l'API key depuis l'état de session"""
    if 'api_key' in st.session_state:
        return st.session_state.api_key
    return load_api_key()
