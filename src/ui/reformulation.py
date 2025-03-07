import streamlit as st
import os


def show_reformulation_section():
    """Affiche la section de reformulation"""
    st.subheader("Application Details")

    # Champ pour le nom de l'application
    app_name = st.text_input(
        "Application Name", value=st.session_state.app_name)

    # Mise à jour du nom et du répertoire de sortie si modifié
    if app_name != st.session_state.app_name:
        update_app_name(app_name)

    # Affichage et édition de la description reformulée
    st.info("""
    The AI has reformulated your description to make it more specific and comprehensive. 
    The placeholder **APP_NAME** will be replaced with the application name when generating the code.
    You can edit both the name and description if needed.
    """)

    reformulated_text = st.text_area(
        "Reformulated description",
        value=st.session_state.reformulated_prompt,
        height=200
    )
    st.session_state.reformulated_prompt = reformulated_text

    # Option pour revenir à la description originale
    if st.button("Use Original Description"):
        st.session_state.show_reformulation = False


def update_app_name(new_app_name):
    """Met à jour le nom de l'application et le répertoire de sortie"""
    st.session_state.app_name = new_app_name

    # Mise à jour du chemin de sortie
    base_dir = os.path.dirname(st.session_state.output_directory)
    if not base_dir or base_dir == st.session_state.output_directory:
        base_dir = os.path.expanduser('~')

    new_dir = os.path.join(base_dir, new_app_name.replace(" ", "_").lower())
    st.session_state.output_directory = new_dir
