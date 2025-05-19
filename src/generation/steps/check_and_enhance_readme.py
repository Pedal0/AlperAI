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
Vérifie et corrige le contenu du README.md pour s'assurer qu'il contient des instructions détaillées
"""
import os
import re
import logging
from pathlib import Path
from ...api.openrouter_api import call_openrouter_api

logger = logging.getLogger(__name__)

def check_and_enhance_readme(project_dir, api_key=None, model_name=None):
    """
    Vérifie si le README contient des instructions détaillées ou simplement une référence aux scripts de démarrage.
    Si nécessaire, génère un README plus détaillé.
    
    Args:
        project_dir (str): Chemin du projet
        api_key (str, optional): Clé API OpenRouter
        model_name (str, optional): Modèle d'IA à utiliser
        
    Returns:
        bool: True si le README est correct ou a été corrigé, False sinon
    """
    project_dir = Path(project_dir)
    readme_path = project_dir / "README.md"
    
    if not readme_path.exists():
        logger.warning(f"No README.md found in {project_dir}")
        return False
    
    # Lire le contenu du README
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            readme_content = f.read()
        
        # Vérifier si le README contient des instructions détaillées
        if _is_readme_detailed(readme_content):
            logger.info(f"README.md in {project_dir} contains detailed instructions")
            return True
            
        # Si le README ne contient que des références aux scripts, le corriger
        if api_key and model_name:
            return _enhance_readme(project_dir, readme_path, readme_content, api_key, model_name)
        else:
            logger.warning(f"README.md in {project_dir} lacks detailed instructions, but no API key/model provided for enhancement")
            return False
    except Exception as e:
        logger.error(f"Error checking README.md: {e}")
        return False

def _is_readme_detailed(readme_content):
    """
    Vérifie si le README contient des instructions détaillées ou simplement une référence aux scripts de démarrage
    
    Args:
        readme_content (str): Contenu du README
        
    Returns:
        bool: True si le README contient des instructions détaillées
    """
    content_lower = readme_content.lower()
    
    # Vérifier si le README mentionne uniquement les scripts de démarrage
    script_mentions = [
        # Removed all references to start.bat and start.sh
        "launch the script",
        "launch script",
        "execute the scripts"
    ]
    
    only_script_references = any(mention in content_lower for mention in script_mentions)
    
    # Vérifier si le README contient des instructions détaillées
    detailed_instructions = [
        "pip install -r",
        "npm install",
        "python ",
        "node ",
        "flask run",
        "virtual environment",
        "virtualenv",
        "venv",
        "java -jar",
        "--port",
        "localhost:"
    ]
    
    has_detailed_instructions = any(instruction in content_lower for instruction in detailed_instructions)
    
    # Vérifier si le README contient des sections d'installation et d'exécution
    has_install_section = any(section in content_lower for section in [
        "## installation", 
        "## setup", 
        "## getting started",
        "## prerequisites",
        "### installation",
        "### setup"
    ])
    
    has_run_section = any(section in content_lower for section in [
        "## usage", 
        "## running", 
        "## exécution",
        "## run",
        "### usage",
        "### running"
    ])
    
    # Si le README a des sections d'installation et d'exécution ET des instructions détaillées
    # OU si le README contient des instructions détaillées sans mentionner les scripts
    return (has_install_section and has_run_section and has_detailed_instructions) or \
           (has_detailed_instructions and not only_script_references)

def _enhance_readme(project_dir, readme_path, original_content, api_key, model_name):
    """
    Améliore le README pour inclure des instructions détaillées
    
    Args:
        project_dir (Path): Chemin du projet
        readme_path (Path): Chemin du README
        original_content (str): Contenu original du README
        api_key (str): Clé API OpenRouter
        model_name (str): Modèle d'IA à utiliser
        
    Returns:
        bool: True si le README a été amélioré avec succès
    """
    try:
        # Collecter les informations sur le projet
        project_info = {}
        
        # Vérifier requirements.txt
        req_path = project_dir / "requirements.txt"
        if req_path.exists():
            with open(req_path, 'r', encoding='utf-8') as f:
                project_info['requirements.txt'] = f.read()
        
        # Vérifier package.json
        pkg_path = project_dir / "package.json"
        if pkg_path.exists():
            with open(pkg_path, 'r', encoding='utf-8') as f:
                project_info['package.json'] = f.read()
        
        # Vérifier la structure du projet
        project_files = []
        for root, dirs, files in os.walk(project_dir):
            for file in files:
                if file.endswith(('.py', '.js', '.php')):
                    rel_path = os.path.relpath(os.path.join(root, file), project_dir)
                    project_files.append(rel_path)
        
        project_info['files'] = project_files[:20]  # Limiter à 20 fichiers pour éviter un prompt trop long
        
        # Vérifier les scripts de démarrage
        start_bat = project_dir / "start.bat"
        start_sh = project_dir / "start.sh"
        
        if start_bat.exists():
            with open(start_bat, 'r', encoding='utf-8') as f:
                project_info['start.bat'] = f.read()
        
        if start_sh.exists():
            with open(start_sh, 'r', encoding='utf-8') as f:
                project_info['start.sh'] = f.read()
        
        # Construire le prompt
        prompt = f"""Le README.md suivant ne contient pas d'instructions détaillées pour installer et exécuter le projet. 
Il se contente de mentionner les scripts start.bat/start.sh sans expliquer les étapes manuelles.

README original:
```
{original_content}
```

Veuillez améliorer ce README pour inclure des instructions détaillées pas à pas sur comment:
1. Installer toutes les dépendances nécessaires
2. Configurer l'environnement si nécessaire
3. Exécuter l'application manuellement

Ne mentionnez pas simplement les scripts start.bat/start.sh, mais donnez les commandes exactes à exécuter.

Informations sur le projet:
"""

        # Ajouter les informations sur le projet au prompt
        for key, value in project_info.items():
            if key == 'files':
                prompt += f"\nFichiers principaux: {', '.join(value)}"
            else:
                prompt += f"\n\n{key}:\n```\n{value}\n```"
        
        # Appeler l'API
        response = call_openrouter_api(
            api_key, 
            model_name,
            [{"role": "user", "content": prompt}],
            temperature=0.3, 
            max_retries=2
        )
        
        if response and response.get('choices'):
            new_readme = response['choices'][0]['message']['content']
            
            # Sauvegarder l'ancien README par précaution
            backup_path = readme_path.with_suffix('.md.bak')
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
            
            # Écrire le nouveau README
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(new_readme)
            
            logger.info(f"README.md in {project_dir} has been enhanced with detailed instructions")
            return True
        else:
            logger.error("Failed to get response from API to enhance README")
            return False
    except Exception as e:
        logger.error(f"Error enhancing README.md: {e}")
        return False
