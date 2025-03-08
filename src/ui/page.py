import streamlit as st

def setup_page():
    """Set up the main page configuration"""
    st.set_page_config(page_title="AI Application Generator", layout="wide")
    
    st.title("AI Application Generator")
    st.markdown("""
    This tool uses AI to generate complete applications based on your description.
    Just provide a detailed description of what you want to build, set the output directory,
    and click "Generate Application".
    """)

def show_how_it_works():
    """Display the how it works section at the bottom of the page"""
    st.divider()
    st.markdown("### How it works")
    st.markdown("""
    1. **Requirements Analysis**: The system analyzes your description to understand what you want to build.
    2. **Architecture Design**: It designs the overall structure of your application.
    3. **Database Schema**: It creates appropriate database schemas if needed.
    4. **API Design**: It designs API interfaces for the application components.
    5. **Code Generation**: It generates the actual code for the application.
    6. **Code Review**: It reviews the generated code and makes improvements if necessary.
    7. **Project Packaging**: It creates project files like requirements.txt and README.md.
    """)