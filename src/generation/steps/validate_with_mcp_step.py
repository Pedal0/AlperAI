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
Perform comprehensive validation and identify ALL issues that need to be fixed automatically.

CRITICAL VALIDATION CHECKLIST:
✓ SYNTAX ERRORS: Check Python, JavaScript, TypeScript, HTML, CSS syntax
✓ IMPORTS: Verify all import statements are valid and modules exist
✓ DEPENDENCIES: Check package.json, requirements.txt match actual usage
✓ API CONSISTENCY: Frontend calls match backend routes exactly
✓ FILE STRUCTURE: Proper file organization and naming
✓ FUNCTIONALITY: Basic logic flows work correctly
✓ DATABASE: Models, migrations, connections are properly configured
✓ ENVIRONMENT: Configuration files and variables are set up
✓ SECURITY: No obvious security vulnerabilities
✓ PERFORMANCE: No obvious performance issues

RESPONSE FORMAT:
If ANY issues found (even minor ones), respond with:
"🔧 ISSUES FOUND AND FIXES NEEDED:
1. [Issue description] in [filename:line] - Fix: [specific solution]
2. [Issue description] in [filename:line] - Fix: [specific solution]
..."

If NO issues found, respond with:
"✅ All code validated - no issues found"

IMPORTANT: 
- Be thorough and check EVERYTHING
- Focus on issues that could cause runtime errors or broken functionality
- Be specific about file names and exact problems
- Don't ignore small issues - fix them all automatically

Begin comprehensive validation now:"""
        
        if progress_callback:
            progress_callback(9, "🧪 Analyzing project files with AI...", 98)
        
        # Use AI to validate the code
        messages = [
            {"role": "system", "content": "You are an expert code reviewer and validator. Analyze the provided code carefully and identify any issues that need to be fixed."},
            {"role": "user", "content": project_context}        ]
        
        response = call_openrouter_api(api_key, model, messages, temperature=0.3, max_retries=2)
        
        if response and response.get("choices"):
            validation_result = response["choices"][0]["message"]["content"]
            
            # Check if fixes are needed and apply them automatically
            if "🔧" in validation_result or "ISSUES FOUND" in validation_result.upper():
                if progress_callback:
                    progress_callback(9, "🔧 Issues found - applying automatic fixes...", 98)
                
                # Apply automatic fixes
                fixes_applied = apply_automatic_fixes(target_directory, validation_result, project_files, api_key, model)
                
                if fixes_applied > 0:
                    summary = f"✅ {fixes_applied} issues automatically fixed"
                    logging.info(f"Applied {fixes_applied} automatic fixes to the project")
                else:
                    summary = f"Issues detected but no automatic fixes applied: {validation_result[:200]}..."
                    logging.info(f"Validation found issues but could not auto-fix: {validation_result}")
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


def apply_automatic_fixes(target_directory, validation_result, project_files, api_key, model):
    """Apply automatic fixes based on AI validation results."""
    try:
        fixes_applied = 0
        target_path = Path(target_directory)
        
        # Create a more focused prompt for generating specific fixes
        fix_request = f"""AUTOMATIC CODE FIXING TASK

VALIDATION RESULTS:
{validation_result}

PROJECT FILES TO FIX:
{chr(10).join([f"=== {filename} ==={chr(10)}{content[:1000]}{'...' if len(content) > 1000 else ''}{chr(10)}" for filename, content in project_files.items()])}

YOUR TASK:
Generate SPECIFIC file fixes based on the validation results above. For each issue found, provide the EXACT corrected file content.

RESPONSE FORMAT:
For each file that needs fixing, respond with:

=== FIX_FILE: filename ===
[complete corrected file content]
=== END_FIX ===

RULES:
- Only include files that actually need changes
- Provide complete file content, not just snippets
- Ensure all syntax errors are fixed
- Fix imports and dependencies
- Maintain existing functionality while fixing issues
- Keep the same file structure and naming

Begin generating fixes now:"""
        
        # Get specific fixes from AI
        messages = [
            {"role": "system", "content": "You are an expert code fixer. Generate complete corrected file contents based on the validation results."},
            {"role": "user", "content": fix_request}
        ]
        
        response = call_openrouter_api(api_key, model, messages, temperature=0.1, max_retries=2)
        
        if response and response.get("choices"):
            fix_content = response["choices"][0]["message"]["content"]
            
            # Parse the fixes and apply them
            import re
            
            # Find all file fixes using regex
            fix_pattern = r'=== FIX_FILE: (.+?) ===(.*?)=== END_FIX ==='
            fixes = re.findall(fix_pattern, fix_content, re.DOTALL)
            
            for filename, file_content in fixes:
                filename = filename.strip()
                file_content = file_content.strip()
                
                if filename in project_files:
                    try:
                        # Write the corrected content
                        file_path = target_path / filename
                        file_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(file_content)
                        
                        fixes_applied += 1
                        logging.info(f"Applied automatic fix to: {filename}")
                        
                    except Exception as e:
                        logging.error(f"Error applying fix to {filename}: {e}")
                        continue
                else:
                    logging.warning(f"File {filename} not found in project files, skipping fix")
        
        return fixes_applied
        
    except Exception as e:
        logging.error(f"Error applying automatic fixes: {e}")
        return 0
