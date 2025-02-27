import json
import re

def remove_json_comments(json_str):
    """
    Supprime les commentaires de style JavaScript (// ...) dans une chaîne JSON.
    """
    return re.sub(r'//.*?(?=\r?\n)', '', json_str)

def extract_json(text):
    """
    Extrait une chaîne de code valide depuis un texte qui peut contenir 
    du contenu autour, notamment dans un bloc markdown formaté.
    De plus, cette fonction supprime les commentaires éventuels.
    """
    # First try to extract from markdown code blocks
    match = re.search(r'```(?:[a-zA-Z]*)?(?:\n|\s)([\s\S]*?)\s*```', text, re.DOTALL)
    if match:
        return match.group(1)
    
    # If no code block, use the entire content
    return text.strip()

def normalize_structure(structure):
    """
    Normalise la structure JSON pour s'assurer qu'elle est bien formatée.
    
    - Si la structure est une liste, elle est convertie en dictionnaire avec chaque élément pour clé et une valeur vide.
    - Si c'est un dictionnaire, on normalise récursivement chaque valeur.
    - Si c'est une chaîne de caractères, on retourne la chaîne elle-même.
    """
    if isinstance(structure, list):
        return {item: "" for item in structure}
    elif isinstance(structure, dict):
        return {k: normalize_structure(v) for k, v in structure.items()}
    elif isinstance(structure, str):
        return structure
    return {}
