"""
Système de validation et correction automatique avancé utilisant l'analyse de codebase RepoMix.
"""
import os
import logging
from pathlib import Path
from src.api.openrouter_api import call_openrouter_api
from src.mcp.simple_codebase_client import create_simple_codebase_client
from src.utils.prompt_loader import get_agent_prompt

def validate_with_codebase_analysis(target_directory, api_key=None, model=None, user_prompt=None, reformulated_prompt=None, progress_callback=None):
    """
    Validation et correction automatique utilisant l'analyse complète de codebase avec RepoMix.
    
    Args:
        target_directory: Répertoire du projet généré
        api_key: Clé API OpenRouter
        model: Modèle à utiliser
        user_prompt: Prompt original de l'utilisateur
        reformulated_prompt: Prompt reformulé
        progress_callback: Fonction de callback pour le progrès
    
    Returns:
        tuple: (success, message)
    """
    try:
        if progress_callback:
            progress_callback(9, "🔍 Advanced codebase analysis and validation...", 95)
        
        if not api_key or not model:
            return False, "API key and model required for validation."
        
        # Créer le client d'analyse de codebase
        codebase_client = create_simple_codebase_client()
        
        if not codebase_client.repomix_available:
            return False, "RepoMix not available for codebase analysis"
        
        if progress_callback:
            progress_callback(9, "📊 Analyzing complete codebase structure...", 96)
        
        # Analyser la structure du projet
        project_structure = codebase_client.analyze_project_structure(target_directory)
          # Obtenir l'analyse complète de la codebase
        success, codebase_content = codebase_client.get_codebase_analysis(
            target_directory, 
            output_format="markdown", 
            include_summary=True
        )
        
        if not success:
            return False, f"Failed to analyze codebase: {codebase_content}"
        
        if progress_callback:
            progress_callback(9, "🧠 AI-powered comprehensive validation...", 97)
        
        # Load validation prompt template
        validation_prompt = get_agent_prompt(
            'advanced_validation_agent',
            'advanced_validation_prompt',
            target_directory=target_directory,
            user_prompt=user_prompt or 'Not specified',
            reformulated_prompt=reformulated_prompt or 'Not specified',
            total_files=project_structure.get('total_files', 0),
            total_size=project_structure.get('total_size', 0),
            file_types=str(project_structure.get('file_types', {})),
            directories_count=len(project_structure.get('directories', [])),
            repomix_output=codebase_content[:20000] + ("..." if len(codebase_content) > 20000 else "")
        )
        
        # Utiliser l'IA pour valider
        system_prompt = get_agent_prompt('advanced_validation_agent', 'advanced_validation_system_prompt')
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": validation_prompt}
        ]
        
        response = call_openrouter_api(api_key, model, messages, temperature=0.2, max_retries=2)
        
        if response and response.get("choices"):
            validation_result = response["choices"][0]["message"]["content"]
            
            if progress_callback:
                progress_callback(9, "🔧 Processing validation results...", 98)
            
            # Analyser les résultats et appliquer les corrections si nécessaire
            if "🔧" in validation_result or "ISSUES FOUND" in validation_result.upper():
                # SAFETY CHECK: Make sure we don't apply fixes if AI says no issues found
                if ("NO ISSUES FOUND" in validation_result.upper() or 
                    "ALL CODE VALIDATED" in validation_result.upper() or 
                    "VALIDATION COMPLETE - NO ISSUES" in validation_result.upper() or
                    "EVERYTHING IS GOOD" in validation_result.upper() or
                    "✅" in validation_result and ("NO ISSUES" in validation_result.upper() or "NO PROBLEMS" in validation_result.upper())):
                    summary = "✅ All code validated - no issues found (safety check prevented unnecessary fixes)"
                    logging.info("Advanced validation passed - safety check prevented fix application when no issues found")
                else:
                    if progress_callback:
                        progress_callback(9, "⚡ Applying automatic corrections...", 99)
                    
                    # Appliquer les corrections automatiques
                    fixes_applied = apply_advanced_fixes(
                        target_directory, 
                        validation_result, 
                        codebase_content,
                        api_key, 
                        model
                    )
                    
                    if fixes_applied > 0:
                        summary = f"✅ {fixes_applied} issues automatically corrected"
                        logging.info(f"Applied {fixes_applied} automatic corrections")
                    else:
                        summary = f"Issues detected but no automatic fixes applied: {validation_result[:200]}..."
                        logging.warning("Validation found issues but could not auto-fix")
            else:
                summary = "✅ All code validated - no issues found"
                logging.info("Advanced validation passed - no issues found")
            
            if progress_callback:
                progress_callback(10, f"✅ Advanced validation complete: {summary}", 100)
            
            return True, summary
        else:
            return False, "Failed to get validation response from AI"
            
    except Exception as e:
        logging.error(f"Error during advanced validation: {e}")
        return False, str(e)


def apply_advanced_fixes(target_directory, validation_result, codebase_content, api_key, model):
    """
    Applique des corrections automatiques avancées basées sur l'analyse de validation.
    
    Args:
        target_directory: Répertoire du projet
        validation_result: Résultats de la validation
        codebase_content: Contenu complet de la codebase
        api_key: Clé API
        model: Modèle à utiliser
    
    Returns:
        int: Nombre de corrections appliquées
    """
    try:
        fixes_applied = 0
        target_path = Path(target_directory)
        
        # SAFETY CHECK: Don't apply fixes if validation indicates no issues
        if ("NO ISSUES FOUND" in validation_result.upper() or 
            "ALL CODE VALIDATED" in validation_result.upper() or 
            "VALIDATION COMPLETE - NO ISSUES" in validation_result.upper() or
            "EVERYTHING IS GOOD" in validation_result.upper() or
            "✅" in validation_result and ("NO ISSUES" in validation_result.upper() or "NO PROBLEMS" in validation_result.upper())):
            logging.info("Skipping advanced fix application - validation indicates no issues found")
            return 0
          # Créer un prompt spécialisé pour générer des corrections automatiques
        fix_prompt = get_agent_prompt(
            'advanced_validation_agent',
            'auto_correction_prompt',
            validation_results=validation_result,
            codebase_content=codebase_content[:15000] + ("..." if len(codebase_content) > 15000 else "")
        )
        
        # Obtenir les corrections de l'IA
        auto_correction_system_prompt = get_agent_prompt('advanced_validation_agent', 'auto_correction_system_prompt')
        messages = [
            {"role": "system", "content": auto_correction_system_prompt},
            {"role": "user", "content": fix_prompt}
        ]
        
        response = call_openrouter_api(api_key, model, messages, temperature=0.1, max_retries=2)
        
        if response and response.get("choices"):
            fix_content = response["choices"][0]["message"]["content"]
            
            # SAFETY CHECK: Don't proceed if no proper fix patterns found
            import re
            fix_pattern = r'=== FIX_FILE: (.+?) ===(.*?)=== END_FIX ==='
            fixes = re.findall(fix_pattern, fix_content, re.DOTALL)
            
            if not fixes:
                if ("NO ISSUES" in fix_content.upper() or 
                    "EVERYTHING IS GOOD" in fix_content.upper() or
                    "ALL CODE VALIDATED" in fix_content.upper() or
                    "NO FIXES NEEDED" in fix_content.upper()):
                    logging.info("No advanced fixes applied - AI response indicates no issues to fix")
                    return 0
                else:
                    logging.warning(f"No valid FIX_FILE patterns found in advanced AI response: {fix_content[:200]}...")
                    return 0
            
            # Parser et appliquer les corrections
            # Trouver tous les fichiers à corriger
            for filename, file_content in fixes:
                filename = filename.strip()
                file_content = file_content.strip()
                
                try:
                    # Écrire le contenu corrigé
                    file_path = target_path / filename
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(file_content)
                    
                    fixes_applied += 1
                    logging.info(f"Applied advanced fix to: {filename}")
                    
                except Exception as e:
                    logging.error(f"Error applying fix to {filename}: {e}")
                    continue
        
        return fixes_applied
        
    except Exception as e:
        logging.error(f"Error applying advanced fixes: {e}")
        return 0