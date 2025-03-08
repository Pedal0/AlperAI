import streamlit as st
import os

def initialize_session_state():
    """Initialize session state variables"""
    if 'generation_step' not in st.session_state:
        st.session_state.generation_step = 'initial'
    if 'reformulated_prompt' not in st.session_state:
        st.session_state.reformulated_prompt = ""
    if 'user_prompt' not in st.session_state:
        st.session_state.user_prompt = ""
    if 'output_path' not in st.session_state:
        st.session_state.output_path = os.path.join(os.getcwd(), "generated_app")
    if 'advanced_options' not in st.session_state:
        st.session_state.advanced_options = {
            'include_tests': False,
            'create_docker': False,
            'add_ci_cd': False,
            'use_sample_json': False,
            'extended_dep_wait': True,
            'is_static_website': False,
            'ai_generated_everything': True  # Option to force all files to be AI-generated
        }

def create_tabs():
    """Create and return the tabs for the application"""
    return st.tabs(["Initial Setup", "Review Requirements", "Generation Progress"])

def set_active_tab():
    """Set the active tab based on the current generation step"""
    if st.session_state.generation_step == "initial":
        st.session_state.active_tab = 0
    elif st.session_state.generation_step == "review":
        st.session_state.active_tab = 1
    elif st.session_state.generation_step == "generating":
        st.session_state.active_tab = 2