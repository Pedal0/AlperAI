"""
User needs analysis step to determine which generation steps to execute.
"""
import re

def analyze_user_needs(user_prompt: str) -> list:
    """
    Analyzes user prompt to determine necessary generation steps for the project.
    Returns a list of steps to execute (e.g., ["frontend", "backend", "tests", "documentation"])
    """
    steps = []
    prompt = user_prompt.lower()
      # Enhanced frontend detection
    frontend_indicators = [
        "interface", "web", "site", "frontend", "ui", "ux", "html", "css", "javascript", 
        "react", "vue", "angular", "svelte", "page", "form", "button", "menu",
        "responsive", "mobile", "design", "visual", "display", "navigation",
        # French variants
        "formulaire", "bouton", "visuel", "affichage",
        # Spanish variants
        "interfaz", "diseño", "visual", "botón", "formulario",
        # Other common variants
        "webpage", "website", "client-side", "user interface"
    ]
    if any(word in prompt for word in frontend_indicators):
        steps.append("frontend")
    
    # Enhanced backend detection
    backend_indicators = [
        "api", "backend", "server", "database", "sql", "sqlite", "mongodb", 
        "flask", "django", "express", "fastapi", "authentication", "login", 
        "session", "crud", "persistence", "data", "storage", "save", "store",
        # French variants
        "serveur", "base de données", "bdd", "authentification", "persistance", 
        "données", "stockage", "enregistrer", "sauvegarder",
        # Spanish variants
        "servidor", "base de datos", "autenticación", "persistencia", "datos",
        "almacenamiento", "guardar",
        # Other variants
        "server-side", "back-end", "endpoint", "rest api"
    ]
    if any(word in prompt for word in backend_indicators):
        steps.append("backend")
    
    # If user mentions data/persistence without explicit backend, add backend
    data_keywords = [
        "data", "save", "store", "persistent", "database", "storage",
        "données", "enregistrer", "sauvegarder", "stocker", "persistant", "base",
        "datos", "guardar", "almacenar", "persistente"
    ]
    if any(word in prompt for word in data_keywords) and "backend" not in steps:
        steps.append("backend")
    
    # Test detection
    test_indicators = [
        "test", "tests", "unit test", "pytest", "jest", "tdd", "coverage", "testing",
        "vérification", "prueba", "pruebas"
    ]
    if any(word in prompt for word in test_indicators):
        steps.append("tests")
    
    # Documentation detection
    doc_indicators = [
        "doc", "documentation", "readme", "manual", "guide", "instructions",
        "manuel", "guía", "documentación"
    ]
    if any(word in prompt for word in doc_indicators):
        steps.append("documentation")
    
    # Always generate minimal README if no specific documentation
    if "documentation" not in steps:
        steps.append("readme")
    
    # If no frontend/backend detected but web app mentioned, add both
    if not steps or (not any(s in steps for s in ["frontend", "backend"])):
        app_indicators = [
            "application", "app", "web", "site", "project", "system", "platform",
            "projet", "système", "plateforme", "aplicación", "proyecto", "sistema"
        ]
        if any(word in prompt for word in app_indicators):
            steps.extend(["frontend", "backend"])
    
    return list(set(steps))  # Remove duplicates