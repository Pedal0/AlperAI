import streamlit as st
import os
import json
import re
from src.generators import generate_project_structure, generate_project_files, verify_project_files
from src.utils import create_project_files, save_corrected_files

st.set_page_config(
    page_title="Générateur de projet",
    page_icon="🤖",
    layout="wide"
)

if 'popup_shown' not in st.session_state:
    st.session_state.popup_shown = False

if 'selected_corrections' not in st.session_state:
    st.session_state.selected_corrections = {}

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
Fournissez un descriptif de votre projet (fonctionnalités, langage, etc) et un chemin où sauvegarder les fichiers.
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
    st.session_state.verification_results = None

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
    files_content = generate_project_files(
        project_description, 
        st.session_state.project_structure,
        regenerate=False 
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Vérifier et corriger le code"):
            with st.spinner("Vérification et correction du code en cours..."):
                try:
                    verification_results = verify_project_files(
                        project_description,
                        st.session_state.project_structure,
                        files_content
                    )
                    st.session_state.verification_results = verification_results
                    
                    # Initialiser les sélections
                    st.session_state.selected_corrections = {
                        file_path: True for file_path in verification_results['modified_files'].keys()
                    }
                    
                except Exception as e:
                    st.error(f"Erreur lors de la vérification du code: {str(e)}")
    
    with col2:
        if st.session_state.get('verification_results'):
            if not st.session_state.verification_results['needs_correction']:
                st.success("✅ Le code est parfaitement fonctionnel. Aucune correction nécessaire.")
            else:
                num_files = len(st.session_state.verification_results['modified_files'])
                modified_count = len([f for f, status in st.session_state.verification_results['analysis_results'].items() 
                                   if status == "MODIFIÉ"])
                st.warning(f"⚠️ {modified_count} fichiers nécessitent des corrections pour assurer la compatibilité.")
                
                # Interface de sélection des corrections
                if modified_count > 0:
                    st.subheader("Sélectionner les corrections à appliquer")
                    
                    for file_path in st.session_state.verification_results['modified_files'].keys():
                        st.session_state.selected_corrections[file_path] = st.checkbox(
                            f"Appliquer les corrections pour: {file_path}",
                            value=True,
                            key=f"select_{file_path}"
                        )
                    
                    if st.button("Appliquer les corrections sélectionnées"):
                        with st.spinner("Application des corrections..."):
                            # Filtrer uniquement les fichiers sélectionnés
                            selected_files = {
                                file_path: content 
                                for file_path, content in st.session_state.verification_results['modified_files'].items()
                                if st.session_state.selected_corrections.get(file_path, False)
                            }
                            
                            if selected_files:
                                success = create_project_files(project_path, selected_files)
                                if success:
                                    st.success(f"✅ Corrections appliquées avec succès pour {len(selected_files)} fichiers!")
                                else:
                                    st.error("Erreur lors de l'application des corrections.")
                            else:
                                st.info("Aucune correction sélectionnée.")

    with st.expander("Voir le contenu des fichiers"):
        # Onglets pour choisir entre fichiers originaux et corrigés
        if st.session_state.get('verification_results') and st.session_state.verification_results['needs_correction']:
            tab1, tab2 = st.tabs(["Fichiers originaux", "Fichiers corrigés"])
            
            with tab1:
                for file_path, content in files_content.items():
                    language = "python" if file_path.endswith(".py") else ""
                    if file_path.endswith(".js"): language = "javascript"
                    if file_path.endswith(".html"): language = "html"
                    if file_path.endswith(".css"): language = "css"
                    
                    st.subheader(f"📄 {file_path}")
                    
                    # Afficher le statut d'analyse
                    if file_path in st.session_state.verification_results.get('analysis_results', {}):
                        analysis = st.session_state.verification_results['analysis_results'][file_path]
                        if analysis == "PARFAIT":
                            st.success("✓ Ce fichier est parfait, aucune correction nécessaire.")
                        elif analysis == "MODIFIÉ":
                            st.warning("⚠ Ce fichier nécessite des corrections.")
                    
                    st.code(content, language=language)
            
            with tab2:
                for file_path, content in files_content.items():
                    language = "python" if file_path.endswith(".py") else ""
                    if file_path.endswith(".js"): language = "javascript"
                    if file_path.endswith(".html"): language = "html"
                    if file_path.endswith(".css"): language = "css"
                    
                    st.subheader(f"📄 {file_path}")
                    
                    # Afficher le statut d'analyse
                    if file_path in st.session_state.verification_results.get('analysis_results', {}):
                        analysis = st.session_state.verification_results['analysis_results'][file_path]
                        if analysis == "PARFAIT":
                            st.success("✓ Ce fichier est parfait, aucune correction nécessaire.")
                            st.code(content, language=language)
                        elif analysis == "MODIFIÉ":
                            st.warning("⚠ Ce fichier a été corrigé.")
                            st.code(st.session_state.verification_results['modified_files'][file_path], language=language)
                            st.info(st.session_state.verification_results['suggestions'][file_path])
                        elif analysis == "ERREUR":
                            st.error("❌ Erreur lors de l'analyse de ce fichier.")
                            st.code(content, language=language)
                    else:
                        st.code(content, language=language)
        else:
            # Si pas de corrections, afficher simplement les fichiers
            for file_path, content in files_content.items():
                language = "python" if file_path.endswith(".py") else ""
                if file_path.endswith(".js"): language = "javascript"
                if file_path.endswith(".html"): language = "html"
                if file_path.endswith(".css"): language = "css"
                
                st.subheader(f"📄 {file_path}")
                st.code(content, language=language)
                if st.session_state.get('verification_results') and file_path in st.session_state.verification_results.get('suggestions', {}):
                    if file_path in st.session_state.verification_results.get('analysis_results', {}) and st.session_state.verification_results['analysis_results'][file_path] == "PARFAIT":
                        st.success(st.session_state.verification_results['suggestions'][file_path])
                    else:
                        st.info(st.session_state.verification_results['suggestions'][file_path])

st.markdown("---")