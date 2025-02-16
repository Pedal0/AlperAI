import os
import json
import streamlit as st
from dotenv import load_dotenv
from src.llm_service import get_project_structure
from src.file_manager import create_project_files

load_dotenv()

def main():
    st.title("Structure Project Creator")
    
    project_path = st.text_input("Chemin absolu du projet")
    prompt = st.text_area("Décris ton projet")
    
    if st.button("Créer le projet"):
        if not os.path.exists(project_path):
            st.error("Chemin invalide.")
            return
        
        status_placeholder = st.empty()
        status_placeholder.info("Génération en cours... 🧠")
        
        structure = get_project_structure(prompt)
        
        if structure:
            create_project_files(project_path, structure)
            status_placeholder.empty()
            st.success("Projet créé avec succès ! 🚀")
        else:
            status_placeholder.empty()
            st.error("Erreur lors de la récupération de la structure du projet.")

if __name__ == "__main__":
    main()