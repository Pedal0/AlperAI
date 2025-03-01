import os
import json

def create_project_files(root_path, files_content):
    """
    Crée les fichiers et dossiers du projet à partir du dictionnaire de contenu.
    
    Args:
        root_path (str): Chemin racine où créer le projet
        files_content (dict): Dictionnaire avec les chemins relatifs et contenus des fichiers
        
    Returns:
        bool: True si tous les fichiers ont été créés avec succès, False sinon
    """
    try:
        if not os.path.exists(root_path):
            os.makedirs(root_path)
        
        for file_path, content in files_content.items():
            full_path = os.path.join(root_path, file_path)
            
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return True
    except Exception as e:
        print(f"Erreur lors de la création des fichiers: {str(e)}")
        return False

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

def save_corrected_files(base_path, modified_files, selected_files=None):
    """
    Sauvegarde les fichiers corrigés dans un dossier spécifique.
    
    Args:
        base_path (str): Chemin du dossier projet d'origine
        modified_files (dict): Dictionnaire des fichiers modifiés (chemin => contenu)
        selected_files (list, optional): Liste des chemins des fichiers à sauvegarder
        
    Returns:
        str: Chemin du dossier contenant les fichiers corrigés
    """
    corrected_dir = os.path.join(os.path.dirname(base_path), os.path.basename(base_path) + "_corrected")
    
    try:
        os.makedirs(corrected_dir, exist_ok=True)
        
        files_to_save = modified_files
        if selected_files is not None:
            files_to_save = {fp: modified_files[fp] for fp in selected_files if fp in modified_files}
        
        for file_path, content in files_to_save.items():
            full_path = os.path.join(corrected_dir, file_path)
            
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return corrected_dir
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des fichiers corrigés: {str(e)}")
        return None