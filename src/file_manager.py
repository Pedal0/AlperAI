import os
from src.llm_file_coder import get_file_comments

def create_project_files(base_dir, structure, user_prompt, project_structure, previous_comments=None):
    """
    Crée les dossiers et fichiers spécifiés dans la structure du projet.
    Pour chaque fichier, il génère une petite liste de commentaires (précédée d'un '#')
    indiquant ce qu'il faudra inclure dans le fichier, en passant :
      - le prompt utilisateur,
      - le nom du fichier,
      - et la structure JSON complète du projet.
    Seules les lignes débutant par '#' seront écrites dans le fichier.
    """
    if previous_comments is None:
        previous_comments = {}
    
    for name, content in structure.items():
        path = os.path.join(base_dir, name)
        print(f"Traitement de : {path}")
        
        if isinstance(content, dict):
            os.makedirs(path, exist_ok=True)
            create_project_files(path, content, user_prompt, project_structure, previous_comments)
        elif isinstance(content, str):
            comments = get_file_comments(user_prompt, name, project_structure)
            if comments:
                previous_comments[name] = comments
                filtered_lines = "\n".join(
                    [line for line in comments.splitlines() if line.strip().startswith("#")]
                )
                with open(path, "w", encoding="utf-8") as f:
                    f.write(filtered_lines)
            else:
                print(f"[ERREUR] Commentaires non générés pour le fichier : {name}")
        else:
            print(f"[AVERTISSEMENT] Type non supporté pour {name}: {type(content)}")