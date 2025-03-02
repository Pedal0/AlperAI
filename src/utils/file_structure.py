import os

def get_flat_file_list(structure, parent_path=""):
    """
    Convertit une structure hiérarchique en liste plate de chemins de fichiers.
    
    Args:
        structure (dict): La structure du projet
        parent_path (str): Le chemin parent pour la récursion
        
    Returns:
        list: Liste de tuples (chemin_fichier, description)
    """
    files = []
    
    for name, value in structure.items():
        current_path = os.path.join(parent_path, name)
        
        if isinstance(value, dict):
            files.extend(get_flat_file_list(value, current_path))
        else:
            files.append((current_path, value))
    
    return files
