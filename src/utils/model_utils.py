"""
Utility functions related to model identification and handling.
"""

def is_free_model(model_name):
    """
    Verify if the model name indicates a free model requiring rate limiting.
    
    Args:
        model_name (str): The model name to check
        
    Returns:
        bool: True if it's a free model, False otherwise
    """
    if not model_name:
        return False
        
    name_lower = model_name.lower()
    return ":free" in name_lower or "google/gemini-flash" in name_lower
