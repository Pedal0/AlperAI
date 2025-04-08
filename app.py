import streamlit as st
from pathlib import Path
import time

# Import from restructured modules
from src.config.constants import RATE_LIMIT_DELAY_SECONDS
from src.utils.env_utils import load_env_vars
from src.ui.components import setup_page_config, render_sidebar, render_input_columns, show_response_expander
from src.generation.generation_flow import generate_application
from src.preview.preview_manager import initialize_preview_state, is_preview_mode
from src.preview.preview_utils import display_preview

# Load environment variables at startup
load_env_vars()

# --- Interface Streamlit ---

# Setup page configuration
setup_page_config()

# Initialize session state variables
if 'last_api_call_time' not in st.session_state:
    st.session_state.last_api_call_time = 0
if 'last_code_generation_response' not in st.session_state:
    st.session_state.last_code_generation_response = ""
if 'reformulated_prompt' not in st.session_state:
    st.session_state.reformulated_prompt = ""
if 'project_structure' not in st.session_state:
    st.session_state.project_structure = []
if 'process_running' not in st.session_state:
    st.session_state.process_running = False
if 'mcp_client' not in st.session_state:
    st.session_state.mcp_client = None
if 'tool_results' not in st.session_state:
    st.session_state.tool_results = {}

# Initialize preview state
initialize_preview_state()

# Check if we're in preview mode
if is_preview_mode():
    # Display application preview
    display_preview(st.session_state.last_generated_app_path)
else:
    # Display normal application generation UI
    # Render the UI components
    api_key, selected_model = render_sidebar()
    user_prompt, target_directory = render_input_columns()

    # Add MCP Tools toggle in sidebar
    with st.sidebar:
        st.subheader("🛠️ Advanced Options")
        use_mcp_tools = st.checkbox("Enable MCP Tools for enhanced generation", value=True, 
                                help="Use Model Context Protocol tools for web search, documentation lookup, and frontend components")
        
        if use_mcp_tools:
            st.subheader("🎨 Frontend Resources")
            frontend_framework = st.selectbox(
                "Preferred UI Framework",
                options=["Auto-detect", "Bootstrap", "Tailwind CSS", "Bulma", "Material Design"],
                index=0,
                help="Select a preferred frontend framework, or let the AI choose"
            )
            
            include_animations = st.checkbox(
                "Include Animations",
                value=True,
                help="Add CSS animations and transitions to make the UI more engaging"
            )

    # Main generation button
    generate_button = st.button("🚀 Generate Application", type="primary", disabled=st.session_state.process_running)

    st.markdown("---") # Visual separator

    # --- Main Logic ---
    if generate_button and not st.session_state.process_running:
        valid_input = True
        if not api_key:
            st.error("Please enter your OpenRouter API key in the sidebar.")
            valid_input = False
        if not user_prompt:
            st.error("Please describe the application you want to generate.")
            valid_input = False
        if not target_directory:
            st.error("Please specify the destination folder path.")
            valid_input = False
        elif not Path(target_directory).is_dir(): # Check if the path is a valid folder
            st.error(f"The specified path '{target_directory}' is not a valid folder or does not exist.")
            valid_input = False

        if valid_input:
            # Generate the application
            generate_application(
                api_key=api_key,
                selected_model=selected_model,
                user_prompt=user_prompt,
                target_directory=target_directory,
                use_mcp_tools=use_mcp_tools,
                frontend_framework=frontend_framework if use_mcp_tools else "Auto-detect",
                include_animations=include_animations if use_mcp_tools else True
            )
            
            st.session_state.process_running = False # Re-enable button
        else: # Invalid input
            st.session_state.process_running = False # Re-enable button if input error

    # Show response expander for debugging
    show_response_expander()