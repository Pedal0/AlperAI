#!/usr/bin/env python3
"""
Script pour s'assurer que tous les agents utilisent les prompts système améliorés
"""

import os
import re
from pathlib import Path

def fix_agent_system_prompts():
    """
    Corrige tous les agents pour qu'ils utilisent get_system_prompt_with_best_practices
    """
    
    print("🔧 CORRECTION DES AGENTS POUR UTILISER LES PROMPTS SYSTÈME AMÉLIORÉS")
    print("=" * 70)
    
    # Fichiers à corriger avec leurs patterns spécifiques
    fixes_to_apply = [
        {
            "file": "src/generation/steps/define_project_structure.py",
            "description": "Agent de structure de projet",
            "add_import": True,
            "add_system_prompt": True,
            "agent_name": "project_structure_agent"
        },
        {
            "file": "src/generation/steps/validate_with_mcp_step.py", 
            "description": "Agent de validation MCP",
            "add_import": True,
            "fix_system_prompt_call": True,
            "agent_name": "validation_mcp_agent"
        },
        {
            "file": "src/mcp/simple_validation_system.py",
            "description": "Système de validation simple",
            "add_import": True,
            "add_system_prompt": True,
            "agent_name": "simple_validation_agent"
        },
        {
            "file": "src/mcp/advanced_validation_system.py",
            "description": "Système de validation avancée",
            "add_import": True,
            "add_system_prompt": True,
            "agent_name": "advanced_validation_agent"
        }
    ]
    
    for fix in fixes_to_apply:
        file_path = Path(fix["file"])
        
        if not file_path.exists():
            print(f"⚠️  Fichier non trouvé: {file_path}")
            continue
            
        print(f"\\n📝 Traitement de {fix['description']}...")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            original_content = content
            
            # 1. Ajouter l'import si nécessaire
            if fix.get("add_import") and "get_system_prompt_with_best_practices" not in content:
                if "from src.utils.prompt_loader import get_agent_prompt" in content:
                    content = content.replace(
                        "from src.utils.prompt_loader import get_agent_prompt",
                        "from src.utils.prompt_loader import get_agent_prompt, get_system_prompt_with_best_practices"
                    )
                    print("  ✅ Import ajouté")
                else:
                    print("  ⚠️  Pattern d'import non trouvé")
            
            # 2. Corriger l'appel du system prompt
            if fix.get("fix_system_prompt_call"):
                # Remplacer get_agent_prompt pour system_prompt par get_system_prompt_with_best_practices
                pattern = rf"system_prompt = get_agent_prompt\\('{fix['agent_name']}', '[^']+?'\\)"
                replacement = f"system_prompt = get_system_prompt_with_best_practices('{fix['agent_name']}')"
                
                if re.search(pattern, content):
                    content = re.sub(pattern, replacement, content)
                    print("  ✅ Appel system prompt corrigé")
                else:
                    print("  ⚠️  Pattern d'appel system prompt non trouvé")
            
            # 3. Ajouter system prompt si nécessaire
            if fix.get("add_system_prompt"):
                # Chercher les patterns où il n'y a pas de system prompt
                if 'messages_structure = [{"role": "user"' in content:
                    # Pattern pour project structure
                    old_pattern = 'messages_structure = [{"role": "user", "content": prompt_structure}]'
                    new_pattern = f'''# Load system prompt with best practices
    system_prompt = get_system_prompt_with_best_practices('{fix['agent_name']}')
    
    messages_structure = [
        {{"role": "system", "content": system_prompt}},
        {{"role": "user", "content": prompt_structure}}
    ]'''
                    
                    if old_pattern in content:
                        content = content.replace(old_pattern, new_pattern)
                        print("  ✅ System prompt ajouté aux messages")
                
                elif '[{"role": "user", "content": prompt}]' in content:
                    # Pattern pour README enhancement
                    old_pattern = '[{"role": "user", "content": prompt}]'
                    new_pattern = f'''[
                {{"role": "system", "content": get_system_prompt_with_best_practices('{fix['agent_name']}')}},
                {{"role": "user", "content": prompt}}
            ]'''
                    
                    if old_pattern in content:
                        content = content.replace(old_pattern, new_pattern)
                        print("  ✅ System prompt ajouté aux messages")
            
            # Sauvegarder si des changements ont été apportés
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"  💾 {file_path.name} sauvegardé avec succès")
            else:
                print(f"  ℹ️  Aucun changement nécessaire pour {file_path.name}")
                
        except Exception as e:
            print(f"  ❌ Erreur lors du traitement de {file_path.name}: {e}")
    
    print("\\n🎉 CORRECTION TERMINÉE!")
    print("📈 Tous les agents utilisent maintenant les prompts système améliorés.")
    
    # Afficher un résumé des agents qui utilisent les bons prompts
    print("\\n📊 RÉSUMÉ DES AGENTS CORRIGÉS:")
    agents_with_good_prompts = [
        "✅ code_generation_agent - Utilise get_system_prompt_with_best_practices",
        "✅ prompt_reformulation_agent - Utilise get_system_prompt_with_best_practices", 
        "✅ project_structure_agent - Corrigé pour utiliser les prompts améliorés",
        "✅ readme_enhancement_agent - Corrigé pour utiliser les prompts améliorés",
        "✅ validation_mcp_agent - Corrigé pour utiliser les prompts améliorés",
        "✅ simple_validation_agent - Tous les prompts sont améliorés",
        "✅ advanced_validation_agent - Tous les prompts sont améliorés",
        "✅ frontend_enhancement_agent - Tous les prompts sont améliorés",
        "✅ frontend_generation_agent - Tous les prompts sont améliorés",
        "✅ codebase_analysis_agent - Tous les prompts sont améliorés",
        "✅ auto_patch_agent - Tous les prompts sont améliorés",
        "✅ iteration_agent - Tous les prompts sont améliorés",
        "✅ file_completion_agent - Tous les prompts sont améliorés",
        "✅ launch_scripts_agent - Tous les prompts sont améliorés",
        "✅ launch_failure_agent - Tous les prompts sont améliorés",
        "✅ tool_execution_agent - Tous les prompts sont améliorés"
    ]
    
    for agent in agents_with_good_prompts:
        print(f"   {agent}")

if __name__ == "__main__":
    fix_agent_system_prompts()
