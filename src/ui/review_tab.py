import streamlit as st

def show_review_tab():
    """Display the review requirements tab"""
    if st.session_state.generation_step == "review":
        st.header("Review AI-Reformulated Requirements")
        st.markdown("Please review the AI-structured version of your request. You can make any necessary edits before proceeding with generation.")
        
        edited_prompt = st.text_area(
            "AI-Structured Requirements", 
            value=st.session_state.reformulated_prompt,
            height=300
        )
        
        # Update session state
        st.session_state.reformulated_prompt = edited_prompt
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("← Back to Setup"):
                st.session_state.generation_step = 'initial'
                st.rerun()
        with col2:
            if st.button("Proceed with Generation ►"):
                st.session_state.generation_step = 'generating'
                st.rerun()
    elif st.session_state.generation_step == "initial":
        st.info("Please complete the Initial Setup step first.")
    else:
        st.info("You've already completed this step. You can go to the Generation Progress tab.")