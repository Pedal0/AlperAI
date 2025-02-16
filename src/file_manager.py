import os

def create_project_files(base_dir, structure):
    """
    Crée les dossiers et fichiers spécifiés dans la structure du projet.
    
    - Pour chaque dossier (valeur dictionnaire), le dossier est créé et la fonction est appelée récursivement.
    - Pour chaque fichier (valeur chaîne de caractères), son contenu est écrit tel quel,
      permettant ainsi d'ajouter un commentaire en tête indiquant ce qu'il faudra coder.
    """
    for name, content in structure.items():
        path = os.path.join(base_dir, name)
        if isinstance(content, dict):
            os.makedirs(path, exist_ok=True)
            create_project_files(path, content)
        elif isinstance(content, str):
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            print(f"[AVERTISSEMENT] Type non supporté pour {name}: {type(content)}")
