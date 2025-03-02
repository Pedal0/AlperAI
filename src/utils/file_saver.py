import os

def save_corrected_files(base_path, modified_files, selected_files=None):
    """
    Prépare les fichiers corrigés sans créer un nouveau dossier.
    
    Args:
        base_path (str): Chemin du dossier projet d'origine
        modified_files (dict): Dictionnaire des fichiers modifiés (chemin => contenu)
        selected_files (list, optional): Liste des chemins des fichiers à sauvegarder
        
    Returns:
        dict: Dictionnaire des fichiers à corriger
    """
    files_to_save = modified_files
    if selected_files is not None:
        files_to_save = {fp: modified_files[fp] for fp in selected_files if fp in modified_files}
    
    return files_to_save