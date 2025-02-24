import os
from src.llm_file_coder import get_file_code

def create_project_files(base_dir, structure, user_prompt, previous_codes=None):
    """
    Crée les dossiers et fichiers spécifiés dans la structure du projet.
    Pour chaque fichier, le code est généré en fournissant:
      - le prompt utilisateur,
      - le nom du fichier,
      - et les codes déjà générés pour que le LLM fasse des liens.
    """
    if previous_codes is None:
        previous_codes = {}
    
    for name, content in structure.items():
        path = os.path.join(base_dir, name)
        print(f"Traitement de : {path}")
        
        if isinstance(content, dict):
            os.makedirs(path, exist_ok=True)
            create_project_files(path, content, user_prompt, previous_codes)
        elif isinstance(content, str):
            code = get_file_code(user_prompt, name, previous_codes)
            if code:
                previous_codes[name] = code
                with open(path, "w", encoding="utf-8") as f:
                    f.write(code)
            else:
                print(f"[ERREUR] Code non généré pour le fichier : {name}")
        else:
            print(f"[AVERTISSEMENT] Type non supporté pour {name}: {type(content)}")