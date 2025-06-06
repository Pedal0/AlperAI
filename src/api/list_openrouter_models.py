import requests
from collections import defaultdict

def get_openrouter_models():
    """
    Récupère la liste des modèles OpenRouter, ajoute les tags (Free), (No Tools), etc.
    Trie les modèles par provider (openai, gemini, etc.), puis par Free/No Tools.
    Retourne une liste de sections (label, models) pour affichage groupé dans le select.
    """
    url = "https://openrouter.ai/api/v1/models"
    response = requests.get(url)
    data = response.json().get("data", [])
    # Préparation des groupes
    providers = defaultdict(list)
    for model in data:
        name = model.get("name", "")
        model_id = model.get("id", "")
        supported_parameters = model.get("supported_parameters", [])
        # Détection Free
        is_free = ":free" in model_id or "(free)" in name.lower()
        # Détection Tools
        has_tools = any("tool" in param for param in supported_parameters)
        # Construction du nom
        display_name = name
        if is_free:
            if not has_tools:
                display_name += " (Free No Tools)"
            else:
                display_name += " (Free)"
        else:
            if not has_tools:
                display_name += " (No Tools)"
        # Provider = 1er segment de l'id (avant le /)
        provider = model_id.split("/")[0] if "/" in model_id else "Other"
        providers[provider].append({
            "id": model_id,
            "name": display_name,
            "is_free": is_free,
            "has_tools": has_tools
        })
    # Tri des providers (OpenAI, Gemini, Anthropic, Qwen, Mistral, Meta, etc.)
    provider_order = [
        "openai", "google", "anthropic", "qwen", "mistralai", "meta-llama", "deepseek", "agentica-org", "nousresearch"
    ]
    # Ajout des autres providers à la fin
    all_providers = list(providers.keys())
    for p in all_providers:
        if p not in provider_order:
            provider_order.append(p)
    # Construction des sections triées
    sections = []
    for provider in provider_order:
        if provider not in providers:
            continue
        # Sous-groupes : Free, No Tools, Autres
        free = [m for m in providers[provider] if m["is_free"] and m["has_tools"]]
        free_no_tools = [m for m in providers[provider] if m["is_free"] and not m["has_tools"]]
        no_tools = [m for m in providers[provider] if not m["is_free"] and not m["has_tools"]]
        normal = [m for m in providers[provider] if not m["is_free"] and m["has_tools"]]
        if free:
            sections.append({"label": f"{provider.capitalize()} (Free)", "models": sorted(free, key=lambda x: x["name"])})
        if free_no_tools:
            sections.append({"label": f"{provider.capitalize()} (Free No Tools)", "models": sorted(free_no_tools, key=lambda x: x["name"])})
        if no_tools:
            sections.append({"label": f"{provider.capitalize()} (No Tools)", "models": sorted(no_tools, key=lambda x: x["name"])})
        if normal:
            sections.append({"label": f"{provider.capitalize()}", "models": sorted(normal, key=lambda x: x["name"])})
    return sections

if __name__ == "__main__":
    for section in get_openrouter_models():
        print(f"--- {section['label']} ---")
        for m in section['models']:
            print(f"{m['name']} (id: {m['id']})")