"""
Automatic code validation and self-correction using direct file analysis.
"""
import os
import logging
from pathlib import Path
from src.api.openrouter_api import call_openrouter_api

def validate_with_mcp_step(target_directory, api_key=None, model=None, user_prompt=None, reformulated_prompt=None, progress_callback=None):
    """Validate and auto-correct generated code by reading files directly and using AI analysis."""
    try:
        if progress_callback:
            progress_callback(9, "🔍 Automatic code validation and correction...", 97)
        
        if not api_key or not model:
            return False, "API key and model required for validation."
        
        # Read all project files and create a comprehensive context
        project_files = {}
        file_contents = ""
        
        # Scan the project directory
        target_path = Path(target_directory)
        if not target_path.exists():
            return False, f"Target directory does not exist: {target_directory}"
        
        # Define file extensions to analyze
        code_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.json', '.md', '.txt', '.yml', '.yaml'}
        
        for file_path in target_path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in code_extensions:
                # Skip large files and common ignore patterns
                if file_path.stat().st_size > 100000:  # Skip files larger than 100KB
                    continue
                if any(part.startswith('.') for part in file_path.parts):  # Skip hidden dirs
                    continue
                if any(part in ['node_modules', '__pycache__', '.git', 'venv', 'env'] for part in file_path.parts):
                    continue
                
                try:
                    relative_path = file_path.relative_to(target_path)
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        project_files[str(relative_path)] = content
                        file_contents += f"\n\n=== FILE: {relative_path} ===\n{content}"
                except Exception as e:
                    logging.warning(f"Could not read file {file_path}: {e}")
        
        if not project_files:
            return False, "No code files found in the project directory"
        
        # Create a comprehensive validation context
        project_context = f"""AUTOMATED CODE VALIDATION AND CORRECTION TASK

You are performing automatic validation on a freshly generated project located at: {target_directory}

ORIGINAL USER REQUEST: {user_prompt or 'Not specified'}

REFORMULATED REQUIREMENTS: {reformulated_prompt or 'Not specified'}

PROJECT FILES ANALYSIS:
{file_contents[:15000]}{"..." if len(file_contents) > 15000 else ""}

YOUR TASK:
1. ANALYZE the provided code files for issues
2. CHECK for syntax errors, import problems, dependency mismatches, API inconsistencies
3. IDENTIFY specific files and lines that need fixes
4. PROVIDE specific corrections needed

VALIDATION CHECKLIST:
- Syntax errors in all source files
- Missing or incorrect imports  
- Unused dependencies in package.json/requirements.txt/etc
- Frontend-backend API mismatches (routes, parameters, data formats)
- Missing dependency declarations
- File naming consistency
- Basic functionality verification

RESPONSE FORMAT:
If issues found, respond with:
"🔧 ISSUES FOUND AND FIXES NEEDED:
1. [Issue description] in [filename:line] - Fix: [specific solution]
2. [Issue description] in [filename:line] - Fix: [specific solution]
..."

If no issues found, respond with:
"✅ All code validated - no issues found"

IMPORTANT: Be specific about file names and line numbers. Focus on critical errors that would prevent the application from running.

Begin validation now:"""
        
        if progress_callback:
            progress_callback(9, "🧪 Analyzing project files with AI...", 98)
        
        # Use AI to validate the code
        messages = [
            {"role": "system", "content": "You are an expert code reviewer and validator. Analyze the provided code carefully and identify any issues that need to be fixed."},
            {"role": "user", "content": project_context}
        ]
        
        response = call_openrouter_api(api_key, model, messages, temperature=0.3, max_retries=2)
        
        if response and response.get("choices"):
            validation_result = response["choices"][0]["message"]["content"]
            
            # Check if fixes are needed
            if "🔧" in validation_result or "ISSUES FOUND" in validation_result.upper():
                summary = f"Issues detected: {validation_result[:200]}..."
                logging.info(f"Validation found issues: {validation_result}")
            else:
                summary = "All code validated - no issues found"
                logging.info("Validation passed - no issues found")
            
            if progress_callback:
                progress_callback(10, f"✅ Validation complete: {summary}", 100)
            
            return True, summary
        else:
            return False, "Failed to get validation response from AI"
            
    except Exception as e:
        logging.error(f"Error during validation: {e}")
        return False, str(e)
