import streamlit as st
from src.ui.interface import create_ui
from src.config.constants import APP_TITLE, APP_DESCRIPTION

def main():
    # Set page configuration
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Load and apply custom CSS
    try:
        with open("src/ui/styles.css", "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("CSS file not found. Using default styles.")
    
    # Display app header
    st.title(APP_TITLE)
    st.markdown(APP_DESCRIPTION)
    
    # Create the main UI
    create_ui()

if __name__ == "__main__":
    main()
