"""
Système de validation et correction automatique avancé utilisant l'analyse de codebase RepoMix.
"""
import os
import logging
from pathlib import Path
from src.api.openrouter_api import call_openrouter_api
from src.mcp.simple_codebase_client import create_simple_codebase_client

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
        
        # Créer un prompt de validation ultra-complet
        validation_prompt = f"""ADVANCED CODEBASE VALIDATION AND AUTO-CORRECTION

You are performing comprehensive validation on a freshly generated project.

ORIGINAL USER REQUEST: {user_prompt or 'Not specified'}
REFORMULATED REQUIREMENTS: {reformulated_prompt or 'Not specified'}

PROJECT STRUCTURE ANALYSIS:
- Total files: {project_structure.get('total_files', 0)}
- Total size: {project_structure.get('total_size', 0)} bytes
- File types: {project_structure.get('file_types', {})}
- Directories: {len(project_structure.get('directories', []))}

COMPLETE CODEBASE ANALYSIS:
{codebase_content[:20000]}{"..." if len(codebase_content) > 20000 else ""}

COMPREHENSIVE VALIDATION REQUIREMENTS:

🔍 CRITICAL ANALYSIS AREAS:
1. SYNTAX & COMPILATION: Check all code files for syntax errors, compilation issues
2. DEPENDENCIES: Verify package.json, requirements.txt, imports, missing libraries
3. API CONSISTENCY: Frontend-backend route matching, parameter alignment, data formats
4. DATABASE INTEGRITY: Models, migrations, connections, schema consistency
5. CONFIGURATION: Environment variables, config files, deployment readiness
6. SECURITY: Authentication, authorization, input validation, XSS/CSRF protection
7. PERFORMANCE: Inefficient queries, memory leaks, optimization opportunities
8. FUNCTIONALITY: Core business logic implementation, edge cases, error handling
9. FILE STRUCTURE: Proper organization, naming conventions, best practices
10. TESTING: Test coverage, test quality, missing test cases

📋 VALIDATION CHECKLIST:
✓ All imports resolve correctly
✓ No undefined variables or functions
✓ API endpoints match between frontend and backend
✓ Database models are properly defined and used
✓ Environment configuration is complete
✓ Error handling is implemented
✓ Security best practices are followed
✓ Code follows language-specific conventions
✓ Dependencies are properly declared
✓ File structure is logical and maintainable

RESPONSE FORMAT:
If ANY issues found (even minor ones), respond with:
"🔧 VALIDATION RESULTS - ISSUES FOUND:

CRITICAL ISSUES:
1. [Issue] in [file:line] - Impact: [severity] - Fix: [solution]

MODERATE ISSUES:
2. [Issue] in [file:line] - Impact: [severity] - Fix: [solution]

MINOR IMPROVEMENTS:
3. [Issue] in [file:line] - Impact: [severity] - Fix: [solution]

SUMMARY: [total issues] issues found requiring automatic correction."

If NO issues found, respond with:
"✅ VALIDATION COMPLETE - NO ISSUES FOUND
All code meets quality standards and requirements."

IMPORTANT:
- Be extremely thorough - check EVERY aspect
- Provide specific file names and line references when possible
- Focus on issues that could cause runtime failures or security problems
- Suggest specific, actionable fixes
- Don't ignore small issues - they should all be fixed automatically

Begin comprehensive validation:"""
        
        # Utiliser l'IA pour valider
        messages = [
            {"role": "system", "content": "You are an expert code reviewer and validator with deep knowledge of software development best practices, security, and architecture. Perform the most thorough code analysis possible."},
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
        fix_prompt = f"""AUTOMATIC CODE CORRECTION SYSTEM

VALIDATION RESULTS:
{validation_result}

COMPLETE CODEBASE CONTEXT:
{codebase_content[:15000]}{"..." if len(codebase_content) > 15000 else ""}

TASK: Generate specific file corrections for ALL issues identified in the validation results.

CORRECTION RULES:
1. Fix ALL syntax errors, import problems, dependency issues
2. Ensure API consistency between frontend and backend
3. Implement proper error handling and security measures
4. Optimize performance and follow best practices
5. Maintain existing functionality while fixing issues
6. Generate complete file contents, not just snippets

RESPONSE FORMAT:
For each file needing corrections, provide:

=== FIX_FILE: [relative_file_path] ===
[complete corrected file content with all issues fixed]
=== END_FIX ===

CRITICAL REQUIREMENTS:
- Provide COMPLETE file content, not partial fixes
- Fix ALL issues mentioned in the validation results
- Ensure the fixes don't break existing functionality
- Follow language-specific best practices and conventions
- Include proper imports, dependencies, and configurations

Begin generating comprehensive fixes:"""
        
        # Obtenir les corrections de l'IA
        messages = [
            {"role": "system", "content": "You are an expert code fixer capable of automatically correcting any software issues. Generate complete, working file contents that fix all identified problems."},
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