import streamlit as st
import os
import json
from src.generator import generate_project_structure, generate_project_files
from src.file_utils import create_project_files

st.set_page_config(
    page_title="Générateur de Site Web par IA",
    page_icon="🤖",
    layout="wide"
)

if 'popup_shown' not in st.session_state:
    st.session_state.popup_shown = False

st.title("Générateur de Site Web par IA")

if not st.session_state.popup_shown:
    popup_container = st.container()
    with popup_container:
        col1, col2, col3 = st.columns([1, 3, 1])
        with col2:
            st.warning("""
            ### Langages pris en charge
            Ce bot prend en charge avec une suite logique les langages suivants :
            - `py` : Python
            - `js`, `jsx` : JavaScript
            - `ts`, `tsx` : TypeScript 
            - `php` : PHP
            - `java` : Java
            - `cs` : C#
            - `rb` : Ruby
            - `go` : Go
            - `html` : HTML
            - `css` : CSS
            
            Si le langage que vous souhaitez n'est pas présent dans cette liste, vous pouvez quand même l'essayer, mais la cohérence n'est pas garantie.
            """)
            if st.button("Fermer"):
                st.session_state.popup_shown = True
                st.rerun()

st.markdown("""
Cette application vous permet de générer un site web ou une application à partir d'une simple description.
Fournissez un descriptif de votre projet et un chemin où sauvegarder les fichiers.
""")

project_path = st.text_input("Chemin du dossier projet", os.path.expanduser("~/mon_projet"))
project_description = st.text_area(
    "Description de votre projet", 
    height=200,
    placeholder="Exemple: Un site web de recettes de cuisine avec une page d'accueil, une page pour afficher les recettes, et un formulaire pour ajouter de nouvelles recettes..."
)

if 'project_structure' not in st.session_state:
    st.session_state.project_structure = None
    st.session_state.is_structure_generated = False
    st.session_state.is_files_generated = False

if st.button("Générer la structure du projet", disabled=not project_description):
    with st.spinner("Génération de la structure du projet en cours..."):
        try:
            st.session_state.project_structure = generate_project_structure(project_description)
            st.session_state.is_structure_generated = True
            st.session_state.is_files_generated = False
        except Exception as e:
            st.error(f"Erreur lors de la génération de la structure: {str(e)}")

if st.session_state.is_structure_generated and st.session_state.project_structure:
    st.subheader("Structure du projet")
    
    def format_structure(structure, indent=0):
        result = ""
        for key, value in structure.items():
            if isinstance(value, dict):
                result += "  " * indent + f"📁 {key}\n"
                result += format_structure(value, indent + 1)
            else:
                result += "  " * indent + f"📄 {key} - {value}\n"
        return result
    
    st.code(format_structure(st.session_state.project_structure), language="")
    
    if st.button("Générer les fichiers", disabled=not st.session_state.is_structure_generated):
        if not os.path.exists(project_path):
            st.warning(f"Le dossier {project_path} n'existe pas. Il sera créé.")
        
        with st.spinner("Génération des fichiers en cours..."):
            try:
                files_content = generate_project_files(
                    project_description, 
                    st.session_state.project_structure
                )
                
                success = create_project_files(project_path, files_content)
                
                if success:
                    st.session_state.is_files_generated = True
                    st.success(f"✅ Projet généré avec succès dans le dossier: {project_path}")
                else:
                    st.error("Une erreur est survenue lors de la création des fichiers.")
            except Exception as e:
                st.error(f"Erreur lors de la génération des fichiers: {str(e)}")

if st.session_state.is_files_generated:
    with st.expander("Voir le contenu des fichiers générés"):
        files_content = generate_project_files(
            project_description, 
            st.session_state.project_structure,
            regenerate=False 
        )
        
        for file_path, content in files_content.items():
            st.subheader(f"📄 {file_path}")
            st.code(content, language="python" if file_path.endswith(".py") else "")

st.markdown("---")