import json
import re

def extract_json(text):
    """
    Extrait un objet JSON valide d'une chaîne de texte.
    Si le texte contient des blocs de code, tente d'extraire le JSON de ces blocs.
    
    Args:
        text (str): Le texte contenant potentiellement un objet JSON
        
    Returns:
        str or None: Le JSON extrait ou None si aucun JSON valide n'est trouvé
    """
    code_blocks = re.findall(r'```(?:json)?\s*([\s\S]*?)```', text)
    
    if code_blocks:
        for block in code_blocks:
            try:
                json.loads(block.strip())
                return block.strip()
            except json.JSONDecodeError:
                continue
    
    try:
        start = text.find('{')
        end = text.rfind('}')
        
        if start != -1 and end != -1 and start < end:
            potential_json = text[start:end+1]
            json.loads(potential_json)
            return potential_json
    except json.JSONDecodeError:
        pass
    
    return None

def normalize_structure(structure):
    """
    Normalise la structure de fichiers pour s'assurer qu'elle est au format attendu.
    Vérifie que les dossiers sont des dictionnaires et les fichiers sont des chaînes.
    
    Args:
        structure (dict): La structure à normaliser
        
    Returns:
        dict: La structure normalisée
    """
    normalized = {}
    
    for key, value in structure.items():
        if isinstance(value, dict):
            normalized[key] = normalize_structure(value)
        elif isinstance(value, list):
            normalized[key] = {}
            for item in value:
                if isinstance(item, str):
                    normalized[key][item] = "Fichier généré automatiquement"
                elif isinstance(item, dict):
                    for file_key, file_desc in item.items():
                        normalized[key][file_key] = file_desc
        elif isinstance(value, str):
            normalized[key] = value
            
    return normalized