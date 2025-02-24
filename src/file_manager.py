import os
import re
from src.llm_file_coder import get_file_comments

def create_project_files(base_dir, structure, user_prompt, project_structure, previous_comments=None):
    """
    Crée les dossiers et fichiers spécifiés dans la structure du projet.
    Pour chaque fichier, il génère le code à inclure dans le fichier en passant :
      - le prompt utilisateur,
      - le nom du fichier,
      - et la structure JSON complète du projet.
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
            code = get_file_comments(user_prompt, name, project_structure)
            if code:
                match = re.search(r"```(?:[a-zA-Z]*)\n(.*?)\n```", code, re.DOTALL)
                if match:
                    code = match.group(1).strip()
                else:
                    if re.match(r"^(import|def|class|from)", code.strip()):
                        code = code.strip()
                    else:
                        print(f"[ERREUR] Réponse non conforme pour le fichier : {name}")
                        code = None
                if code:
                    previous_comments[name] = code
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(code)
            else:
                print(f"[ERREUR] Code non généré pour le fichier : {name}")
        else:
            print(f"[AVERTISSEMENT] Type non supporté pour {name}: {type(content)}")