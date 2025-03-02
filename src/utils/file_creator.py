import os

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
