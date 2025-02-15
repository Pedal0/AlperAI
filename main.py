import os
import json
from dotenv import load_dotenv
from src.llm_service import get_project_structure
from src.file_manager import create_project_files

load_dotenv()

def main():
    """Exécution principale du script."""
    project_path = input("Où créer le projet ? (chemin absolu) : ")
    if not os.path.exists(project_path):
        print("Chemin invalide.")
        return
    
    prompt = input("Décris ton projet : ")
    print("Génération en cours... 🧠")
    structure = get_project_structure(prompt)
    
    if structure:
        print("Structure reçue :", json.dumps(structure, indent=2))
        create_project_files(project_path, structure)
        print("Projet créé avec succès ! 🚀")
    else:
        print("Erreur lors de la récupération de la structure du projet.")

if __name__ == "__main__":
    main()
