import streamlit as st
import os
from src.config import USE_OPENROUTER

def initialize_session_state():
    """Initialize session state variables"""
    if 'user_prompt' not in st.session_state:
        st.session_state.user_prompt = ""
    
    if 'reformulated_prompt' not in st.session_state:
        st.session_state.reformulated_prompt = ""
    
    if 'output_path' not in st.session_state:
        st.session_state.output_path = "C:\\Users\\Public\\bot_generated_project"
    
    if 'generation_step' not in st.session_state:
        st.session_state.generation_step = "initial"
    
    if 'advanced_options' not in st.session_state:
        st.session_state.advanced_options = {
            'use_openrouter': USE_OPENROUTER,
            'include_tests': False,
            'create_docker': False,
            'add_ci_cd': False,
            'use_sample_json': False,
            'extended_dep_wait': True,
            'is_static_website': False,
            'ai_generated_everything': True,
            'enable_agent_team': False
        }
        
    if 'generation_logs' not in st.session_state:
        st.session_state.generation_logs = []
        
    if 'app_path' not in st.session_state:
        st.session_state.app_path = None

    if 'generation_complete' not in st.session_state:
        st.session_state.generation_complete = False
    
    if 'generation_error' not in st.session_state:
        st.session_state.generation_error = False
    
    if 'generation_error_message' not in st.session_state:
        st.session_state.generation_error_message = ""

def create_tabs(tab_names):
    """Create tabs with given names"""
    return st.tabs(tab_names)

def set_active_tab():
    """Set the active tab based on the current generation step"""
    js = ""
    if st.session_state.generation_step == "initial":
        js = """<script>
                document.querySelectorAll('.stTabs button[aria-selected="true"]')[0].style.backgroundColor = "#e6f3ff";
                document.querySelectorAll('.stTabs button')[0].click();
                </script>"""
    elif st.session_state.generation_step == "review":
        js = """<script>
                document.querySelectorAll('.stTabs button[aria-selected="true"]')[0].style.backgroundColor = "#e6f3ff";
                document.querySelectorAll('.stTabs button')[1].click();
                </script>"""
    elif st.session_state.generation_step in ["generating", "complete"]:
        js = """<script>
                document.querySelectorAll('.stTabs button[aria-selected="true"]')[0].style.backgroundColor = "#e6f3ff";
                document.querySelectorAll('.stTabs button')[2].click();
                </script>"""
    
    if js:
        st.components.v1.html(js)