"""
Utility functions for prompt handling and detection.
"""

def prompt_mentions_design(prompt_text):
    """
    Check if the user prompt mentions design-related terms.
    
    Args:
        prompt_text (str): The prompt text to analyze
        
    Returns:
        bool: True if design terms are mentioned, False otherwise
    """
    if not prompt_text:
        return False
        
    keywords = [
        "design", "style", "css", "layout", "look", "feel", "appearance",
        "minimalist", "modern", "bootstrap", "tailwind", "material",
        "theme", "color", "font", "ui", "ux", "interface", "visual",
        "animation", "transition"
    ]
    prompt_lower = prompt_text.lower()
    for keyword in keywords:
        if keyword in prompt_lower:
            return True
    return False
