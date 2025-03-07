import re


def extract_app_name(text):
    """Extrait le nom de l'application à partir du texte de reformulation"""
    # Modèles pour trouver des noms d'application
    patterns = [
        r'(?:application|app) name:?\s*["\']?([a-zA-Z0-9_\-\s]+)["\']?',
        r'name:?\s*["\']?([a-zA-Z0-9_\-\s]+)["\']?',
        r'create\s+(?:an?|the)\s+([a-zA-Z0-9_\-\s]+)\s+(?:app|application)',
        r'develop\s+(?:an?|the)\s+([a-zA-Z0-9_\-\s]+)\s+(?:app|application)',
    ]

    # Recherche dans le texte
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            return name if len(name) > 2 else None

    # Génération à partir de la première phrase si aucun nom trouvé
    if text:
        first_line = text.split('.')[0].strip()
        words = first_line.split()
        if words:
            word_count = min(3, len(words))
            return ' '.join(words[:word_count]).strip()

    return "MyApp"  # Nom par défaut
