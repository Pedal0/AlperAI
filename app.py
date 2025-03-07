from src.ui.main_view import display_main_ui  # Modifié: ui -> src.ui
import streamlit as st
import sys
import os
from dotenv import load_dotenv
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configuration de base
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    # Chargement des variables d'environnement
    load_dotenv()

    # Configuration Streamlit
    st.set_page_config(page_title="AI Application Generator", layout="wide")

    # Affichage de l'interface utilisateur principale
    display_main_ui()


if __name__ == "__main__":
    main()
