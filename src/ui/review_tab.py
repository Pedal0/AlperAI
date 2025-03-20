import streamlit as st
import os
import logging
from src.config import constants
from src.generators.app_generator import AppGenerator

logger = logging.getLogger(__name__)

def show_review_tab(api_key):
    """Display the review tab with reformulated requirements and generation button"""
    if st.session_state.generation_step == "review":
        st.header("Review & Customize Requirements")
        
        # Afficher le prompt reformulé dans une zone de texte éditable
        reformulated_prompt = st.text_area(
            "Reformulated Requirements (you can modify this)",
            value=st.session_state.reformulated_prompt,
            height=400
        )
        
        # Mettre à jour le prompt reformulé dans l'état de session
        st.session_state.reformulated_prompt = reformulated_prompt
        
        # Ajouter une séparation visuelle
        st.markdown("---")
        
        # Ajouter un expander pour afficher les détails de la génération
        with st.expander("Generation details", expanded=True):
            st.markdown(f"**Output directory:** `{st.session_state.output_path}`")
            
            # Afficher les options avancées sélectionnées
            st.markdown("**Advanced options:**")
            options_text = []
            for option, value in st.session_state.advanced_options.items():
                if value == True:
                    options_text.append(f"- {option.replace('_', ' ').title()}")
            
            if options_text:
                st.markdown("\n".join(options_text))
            else:
                st.markdown("No advanced options selected")
                
            # Indication de vérification par équipe d'agents
            if st.session_state.advanced_options.get("enable_agent_team", False):
                st.info("AI agent team verification is enabled. The team will check and improve your code after generation.")
        
        # Bouton pour lancer la génération
        if st.button("Generate Application Now"):
            # Mettre à jour la configuration de l'équipe d'agents
            constants.AGENT_TEAM_ENABLED = st.session_state.advanced_options.get("enable_agent_team", False)
            
            # Réinitialiser les indicateurs d'erreurs précédentes
            if 'generation_error' in st.session_state:
                del st.session_state.generation_error
            if 'generation_error_message' in st.session_state:
                del st.session_state.generation_error_message
            
            # Passer à l'étape de génération
            st.session_state.generation_step = "generating"
            
            # Sauvegarder le prompt reformulé pour le contexte de génération
            st.session_state.final_prompt = reformulated_prompt
            
            # Stocker les options pour la génération
            st.session_state.generate_options = {
                "api_key": api_key,
                "user_prompt": st.session_state.final_prompt,
                "output_path": st.session_state.output_path,
                "include_tests": st.session_state.advanced_options.get("include_tests", False),
                "create_docker": st.session_state.advanced_options.get("create_docker", False),
                "add_ci_cd": st.session_state.advanced_options.get("add_ci_cd", False),
                "use_sample_json": st.session_state.advanced_options.get("use_sample_json", False),
                "ai_generated_everything": st.session_state.advanced_options.get("ai_generated_everything", True)
            }
            
            # Initialiser les logs de génération
            st.session_state.generation_logs = ["Generation started"]
            
            # Rediriger vers l'onglet de génération
            st.rerun()
    elif st.session_state.generation_step == "generating" or st.session_state.generation_step == "complete":
        # Afficher un message si on revient à cet onglet pendant ou après la génération
        if st.session_state.generation_step == "generating":
            st.info("Generation is in progress. Please see the Generation tab.")
        else:
            st.success("Generation is complete. Please see the Generation tab.")
            
        # Bouton pour recommencer
        if st.button("Start a new project"):
            st.session_state.generation_step = 'initial'
            st.session_state.reformulated_prompt = ""
            st.session_state.user_prompt = ""
            if 'generation_logs' in st.session_state:
                st.session_state.generation_logs = []
            if 'generation_started' in st.session_state:
                del st.session_state.generation_started
            if 'generation_complete' in st.session_state:
                del st.session_state.generation_complete
            if 'generation_error' in st.session_state:
                del st.session_state.generation_error
            st.rerun()
    else:
        st.info("Please first define your application in the 'Definition' tab.")