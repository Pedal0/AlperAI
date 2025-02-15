import os

def create_project_files(base_path, structure):
    """Crée les fichiers et dossiers selon la structure générée."""
    for path, content in structure.items():
        full_path = os.path.join(base_path, path)
        if isinstance(content, dict): 
            os.makedirs(full_path, exist_ok=True)
            create_project_files(full_path, content)
        else:  
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content or "# TODO: Implement this file")
