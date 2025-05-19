# Copyright (C) 2025 Perey Alex
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>

"""
Vérifie et améliore le README pour la prévisualisation.
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def improve_readme_for_preview(project_dir):
    """
    Vérifie que le README contient des instructions détaillées et pas seulement une référence à des scripts de démarrage. N'utilise jamais start.bat/start.sh.
    Améliore les instructions si nécessaire.
    
    Args:
        project_dir (str): Chemin du projet
        
    Returns:
        bool: True si le README est adéquat ou a été amélioré
    """
    project_dir = Path(project_dir)
    readme_path = project_dir / "README.md"
    
    if not readme_path.exists():
        logger.warning(f"No README.md found in {project_dir}")
        return False
    
    try:
        # Lire le README
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Vérifier si le README mentionne uniquement des scripts de démarrage
        inadequate_content = _check_readme_inadequacy(content)
        
        if not inadequate_content:
            logger.info(f"README.md in {project_dir} has adequate instructions")
            return True
        
        # Ajouter des informations complémentaires au README
        _append_detailed_instructions(readme_path, project_dir)
        return True
    except Exception as e:
        logger.error(f"Error processing README.md: {e}")
        return False

def _check_readme_inadequacy(content):
    """
    Vérifie si le README est inadéquat (ne mentionne que des scripts de démarrage)
    
    Args:
        content (str): Contenu du README
        
    Returns:
        bool: True si le README est inadéquat
    """
    # Recherche de mentions de scripts sans instructions détaillées
    script_mentions = [
        # Removed all references to start.bat and start.sh
    ]
    
    content_lower = content.lower()
    
    # Si le README mentionne des scripts mais ne contient pas d'instructions détaillées
    if any(mention in content_lower for mention in script_mentions):
        # Vérifier s'il y a des instructions détaillées
        detailed_instructions = [
            "pip install",
            "npm install",
            "python ",
            "node ",
            "php -S",
            "--port",
            "localhost:"
        ]
        
        # Si aucune instruction détaillée n'est trouvée, le README est inadéquat
        if not any(instruction in content_lower for instruction in detailed_instructions):
            return True
    
    return False

def _append_detailed_instructions(readme_path, project_dir):
    """
    Ajoute des instructions détaillées au README
    
    Args:
        readme_path (Path): Chemin vers le README
        project_dir (Path): Chemin vers le projet
    """
    try:
        # Lire le README existant
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Déterminer le type de projet et les commandes à exécuter
        additional_instructions = "\n\n## Instructions détaillées d'installation et d'exécution\n\n"
        
        # Extraire les commandes d'installation
        additional_instructions += "Installation des dépendances:\n```bash\n"
        if "pip install" in content:
            additional_instructions += "pip install -r requirements.txt\n"
        if "npm install" in content:
            additional_instructions += "npm install\n"
        additional_instructions += "```\n\n"
        
        # Extraire les commandes d'exécution
        additional_instructions += "Lancement de l'application:\n```bash\n"
        run_commands = []
        
        if "python " in content:
            for line in content.split('\n'):
                if "python " in line and not line.strip().startswith('#'):
                    # Remplacer $PORT par 8080 dans la commande
                    clean_cmd = line.strip().replace("$PORT", "8080")
                    run_commands.append(clean_cmd)
        elif "node " in content:
            for line in content.split('\n'):
                if "node " in line and not line.strip().startswith('#'):
                    clean_cmd = line.strip().replace("PORT=$PORT", "PORT=8080")
                    run_commands.append(clean_cmd)
        elif "npm " in content:
            for line in content.split('\n'):
                if "npm start" in line and not line.strip().startswith('#'):
                    clean_cmd = line.strip().replace("PORT=$PORT", "PORT=8080")
                    run_commands.append(clean_cmd)
        
        if run_commands:
            additional_instructions += "\n".join(run_commands) + "\n"
        else:
            additional_instructions += "# Consultez la documentation pour les commandes spécifiques\n"
        
        additional_instructions += "```\n\n"
        
        additional_instructions += "L'application sera accessible à l'adresse: http://localhost:8080\n"
        
        # Écrire le README mis à jour
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(content + additional_instructions)
        
        logger.info(f"README.md in {project_dir} has been enhanced with detailed instructions")
    except Exception as e:
        logger.error(f"Error enhancing README.md: {e}")
