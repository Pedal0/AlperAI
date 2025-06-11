#!/usr/bin/env python3
"""
Script de vérification pour s'assurer que tous les prompts améliorés sont utilisés
"""

import json
from pathlib import Path
import re

def verify_prompt_usage():
    """
    Vérifie que tous les agents utilisent les prompts système améliorés
    """
    
    print("🔍 VÉRIFICATION DE L'UTILISATION DES PROMPTS AMÉLIORÉS")
    print("=" * 60)
    
    # 1. Vérifier que tous les fichiers JSON ont des system_prompt_with_best_practices
    prompts_dir = Path("src/config/prompts")
    json_files = list(prompts_dir.glob("*.json"))
    
    print(f"\\n📂 Analyse de {len(json_files)} fichiers de configuration d'agents:")
    
    agents_with_enhanced_prompts = 0
    agents_missing_enhanced_prompts = []
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            agent_name = json_file.stem
            
            # Vérifier system_prompt_with_best_practices
            has_enhanced_prompt = False
            
            if "system_prompt_with_best_practices" in data:
                prompt = data["system_prompt_with_best_practices"]
                if len(prompt) > 200 and ("expertise" in prompt.lower() or "mastery" in prompt.lower() or "advanced" in prompt.lower()):
                    has_enhanced_prompt = True
                    agents_with_enhanced_prompts += 1
                    print(f"   ✅ {agent_name} - Prompt amélioré trouvé ({len(prompt)} caractères)")
                else:
                    print(f"   ⚠️  {agent_name} - Prompt basique détecté")
                    agents_missing_enhanced_prompts.append(agent_name)
            
            elif "prompts" in data and "system_prompt_with_best_practices" in data["prompts"]:
                prompt = data["prompts"]["system_prompt_with_best_practices"]
                if len(prompt) > 200 and ("expertise" in prompt.lower() or "mastery" in prompt.lower() or "advanced" in prompt.lower()):
                    has_enhanced_prompt = True
                    agents_with_enhanced_prompts += 1
                    print(f"   ✅ {agent_name} - Prompt amélioré trouvé dans prompts ({len(prompt)} caractères)")
                else:
                    print(f"   ⚠️  {agent_name} - Prompt basique détecté dans prompts")
                    agents_missing_enhanced_prompts.append(agent_name)
            else:
                print(f"   ❌ {agent_name} - Aucun system_prompt_with_best_practices trouvé")
                agents_missing_enhanced_prompts.append(agent_name)
                
        except Exception as e:
            print(f"   ❌ Erreur lors de la lecture de {json_file.name}: {e}")
            agents_missing_enhanced_prompts.append(json_file.stem)
    
    # 2. Vérifier que les étapes utilisent get_system_prompt_with_best_practices
    print(f"\\n📝 Analyse de l'utilisation dans les étapes de génération:")
    
    steps_dir = Path("src/generation/steps")
    python_files = list(steps_dir.glob("*.py"))
    
    steps_using_enhanced = 0
    steps_not_using_enhanced = []
    
    for py_file in python_files:
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            step_name = py_file.stem
            
            # Vérifier si le fichier utilise call_openrouter_api (donc fait des appels IA)
            if "call_openrouter_api" in content:
                if "get_system_prompt_with_best_practices" in content:
                    steps_using_enhanced += 1
                    print(f"   ✅ {step_name} - Utilise get_system_prompt_with_best_practices")
                else:
                    print(f"   ⚠️  {step_name} - Fait des appels IA mais n'utilise pas get_system_prompt_with_best_practices")
                    steps_not_using_enhanced.append(step_name)
            else:
                print(f"   ℹ️  {step_name} - Ne fait pas d'appels IA directs")
                
        except Exception as e:
            print(f"   ❌ Erreur lors de la lecture de {py_file.name}: {e}")
    
    # 3. Vérifier les systèmes MCP
    print(f"\\n🔧 Analyse des systèmes MCP:")
    
    mcp_dir = Path("src/mcp")
    mcp_files = [f for f in mcp_dir.glob("*.py") if "validation" in f.name]
    
    for mcp_file in mcp_files:
        try:
            with open(mcp_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if "get_system_prompt_with_best_practices" in content:
                print(f"   ✅ {mcp_file.name} - Utilise get_system_prompt_with_best_practices")
            elif "call_openrouter_api" in content:
                print(f"   ⚠️  {mcp_file.name} - Fait des appels IA mais n'utilise pas get_system_prompt_with_best_practices")
            else:
                print(f"   ℹ️  {mcp_file.name} - Ne fait pas d'appels IA directs")
                
        except Exception as e:
            print(f"   ❌ Erreur lors de la lecture de {mcp_file.name}: {e}")
    
    # 4. Résumé final
    print(f"\\n📊 RÉSUMÉ DE LA VÉRIFICATION:")
    print(f"   📁 Agents avec prompts améliorés: {agents_with_enhanced_prompts}/{len(json_files)}")
    print(f"   🔧 Étapes utilisant prompts améliorés: {steps_using_enhanced}")
    
    if agents_missing_enhanced_prompts:
        print(f"\\n⚠️  Agents manquant de prompts améliorés:")
        for agent in agents_missing_enhanced_prompts:
            print(f"     - {agent}")
    
    if steps_not_using_enhanced:
        print(f"\\n⚠️  Étapes ne utilisant pas get_system_prompt_with_best_practices:")
        for step in steps_not_using_enhanced:
            print(f"     - {step}")
    
    # 5. Validation finale
    success_rate = (agents_with_enhanced_prompts / len(json_files)) * 100
    
    if success_rate >= 90:
        print(f"\\n🎉 EXCELLENT! {success_rate:.1f}% des agents utilisent des prompts améliorés!")
        print("✅ Vos agents sont maintenant équipés de prompts de qualité professionnelle.")
    elif success_rate >= 75:
        print(f"\\n👍 BIEN! {success_rate:.1f}% des agents utilisent des prompts améliorés.")
        print("⚠️  Quelques agents pourraient encore être améliorés.")
    else:
        print(f"\\n📈 EN COURS: {success_rate:.1f}% des agents utilisent des prompts améliorés.")
        print("🔧 Des améliorations supplémentaires sont recommandées.")
    
    return success_rate >= 90

if __name__ == "__main__":
    verify_prompt_usage()
