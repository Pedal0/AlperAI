"""
Code validator module.

This module provides functionality to validate and improve generated code using AI.
It can analyze individual files and suggest improvements while also considering the
overall project context.
"""

import os
import re
import json
from src.api import generate_text
from src.api.prompts import SYSTEM_MESSAGES, PROMPTS
from src.config.constants import PRECISE_TEMPERATURE
from src.api.agent_calls.large_file_handler import LargeFileHandler

class CodeValidator:
    def __init__(self, output_dir, project_structure=None, element_dictionary=None):
        """
        Initialize the code validator.
        
        Args:
            output_dir (str): Path to the generated project directory
            project_structure (dict/str): Project structure as JSON or dict
            element_dictionary (dict/str): Element dictionary as JSON or dict
        """
        self.output_dir = output_dir
        self.large_file_handler = LargeFileHandler()
        
        # Parse project structure if it's a string
        self.project_structure = project_structure
        if isinstance(project_structure, str):
            try:
                self.project_structure = json.loads(project_structure)
            except:
                self.project_structure = None
        
        # Parse element dictionary if it's a string
        self.element_dictionary = element_dictionary
        if isinstance(element_dictionary, str):
            try:
                self.element_dictionary = json.loads(element_dictionary)
            except:
                self.element_dictionary = None
    
    def get_file_info(self, file_path):
        """Get file information from project structure"""
        if not self.project_structure:
            return {"description": "Unknown file", "type": "code"}
        
        rel_path = os.path.relpath(file_path, self.output_dir)
        
        for file_info in self.project_structure.get("files", []):
            if file_info.get("path") == rel_path:
                return file_info
        
        return {"description": "Unknown file", "type": "code"}
    
    def validate_file(self, file_path):
        """
        Validate and improve a single file.
        
        Args:
            file_path (str): Path to the file to validate
            
        Returns:
            dict: Validation results including improved code if applicable
        """
        if not os.path.exists(file_path):
            return {
                "success": False,
                "message": f"File not found: {file_path}",
                "improvements": []
            }
        
        # Read the file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
        except Exception as e:
            return {
                "success": False,
                "message": f"Error reading file: {str(e)}",
                "improvements": []
            }
        
        # Get file extension and information
        file_ext = os.path.splitext(file_path)[1]
        file_info = self.get_file_info(file_path)
        file_description = file_info.get("description", "Generated file")
        
        # Check for incomplete files (especially large JS files)
        if file_ext.lower() == '.js' and len(file_content) > 10000:
            # For large JavaScript files, check if they might be incomplete
            if self.large_file_handler.is_incomplete_file(file_path, file_content):
                try:
                    # Handle the large JS file specially
                    self.large_file_handler.handle_large_js_file(
                        file_path, 
                        None,  # No optimized prompt needed here
                        self.project_structure,
                        self.element_dictionary
                    )
                    
                    # Reload the now-completed file content
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                    
                    # Mark this as an improved file
                    return {
                        "success": True,
                        "file_path": file_path,
                        "validation_results": "File was detected as incomplete and has been completed.",
                        "improved_code": file_content,  # Use the completed version
                        "has_improvements": True  # Mark as improved
                    }
                except Exception as e:
                    print(f"Error completing large JS file {file_path}: {str(e)}")
                    # Continue with regular validation
        
        # Check if any file appears to be incomplete
        elif self.large_file_handler.is_incomplete_file(file_path, file_content):
            try:
                # Try to complete the file
                completed_content = self.large_file_handler.complete_file(
                    file_path,
                    None,  # No optimized prompt needed
                    self.project_structure,
                    self.element_dictionary
                )
                
                if completed_content:
                    # File was successfully completed
                    return {
                        "success": True,
                        "file_path": file_path,
                        "validation_results": "File was detected as incomplete and has been completed.",
                        "improved_code": completed_content,
                        "has_improvements": True
                    }
            except Exception as e:
                print(f"Error completing file {file_path}: {str(e)}")
                # Continue with regular validation
        
        # Generate validation prompt
        system_message = SYSTEM_MESSAGES["code_validator"]
        prompt = PROMPTS["code_validator"].format(
            file_ext=file_ext,
            file_path=file_path,
            file_description=file_description,
            file_content=file_content
        )
        
        # Generate validation results
        try:
            validation_results = generate_text(
                prompt, 
                temperature=PRECISE_TEMPERATURE,
                system_message=system_message
            )
            
            # Extract the improved code section
            improved_code = self.extract_improved_code(validation_results)
            
            return {
                "success": True,
                "file_path": file_path,
                "validation_results": validation_results,
                "improved_code": improved_code,
                "has_improvements": improved_code != file_content
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error validating file: {str(e)}",
                "improvements": []
            }
    
    def extract_improved_code(self, validation_results):
        """Extract the improved code section from validation results"""
        # Look for a code block after "IMPROVED CODE:" or similar markers
        improved_code_pattern = re.compile(r'(?:IMPROVED CODE:|SUGGESTED CODE:|Here\'s the improved code:).*?```(?:\w+)?\s*([\s\S]*?)```', re.IGNORECASE)
        match = improved_code_pattern.search(validation_results)
        
        if match:
            return match.group(1).strip()
        return None
    
    def apply_improvements(self, file_path, improved_code):
        """Apply the improved code to the file"""
        if not improved_code:
            return False
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(improved_code)
            return True
        except Exception as e:
            print(f"Error applying improvements to {file_path}: {str(e)}")
            return False
    
    def validate_all_files(self, file_types=None, apply_improvements=True):
        """
        Validate all files in the project.
        
        Args:
            file_types (list): List of file extensions to validate (e.g., ['.html', '.css', '.js'])
            apply_improvements (bool): Whether to apply the improvements automatically
            
        Returns:
            dict: Summary of validation results
        """
        results = {
            "validated_files": 0,
            "improved_files": 0,
            "failed_validations": 0,
            "detailed_results": []
        }
        
        # Walk through all files in the output directory
        for root, _, files in os.walk(self.output_dir):
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = os.path.splitext(file)[1]
                
                # Skip files that don't match the requested types
                if file_types and file_ext not in file_types:
                    continue
                
                # Skip node_modules, .git, and other common directories to ignore
                if any(ignore in root for ignore in ['node_modules', '.git', '__pycache__']):
                    continue
                    
                # Validate the file
                validation_result = self.validate_file(file_path)
                results["detailed_results"].append(validation_result)
                
                if validation_result.get("success", False):
                    results["validated_files"] += 1
                    
                    # Apply improvements if requested and available
                    if (apply_improvements and 
                        validation_result.get("has_improvements", False) and 
                        validation_result.get("improved_code")):
                        
                        if self.apply_improvements(file_path, validation_result["improved_code"]):
                            results["improved_files"] += 1
                else:
                    results["failed_validations"] += 1
        
        return results

    def validate_frontend_files(self, apply_improvements=True):
        """Validate HTML, CSS, and JS files specifically"""
        return self.validate_all_files(
            file_types=['.html', '.css', '.js'],
            apply_improvements=apply_improvements
        )
    
    def check_for_incomplete_files(self):
        """
        Check for incomplete files specifically and try to complete them.
        This is a separate pass focused just on completing files rather than improving them.
        
        Returns:
            dict: Summary of completion results
        """
        results = {
            "checked_files": 0,
            "completed_files": 0,
            "failed_completions": 0
        }
        
        # Priority order - handle JS files first, then others
        priority_exts = ['.js', '.html', '.css', '.py']
        
        # Build a list of files to check
        files_to_check = []
        
        for root, _, files in os.walk(self.output_dir):
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = os.path.splitext(file)[1].lower()
                
                # Skip non-code files
                if file_ext not in priority_exts:
                    continue
                
                # Skip files in ignored directories
                if any(ignore in root for ignore in ['node_modules', '.git', '__pycache__']):
                    continue
                
                # Add to check list with priority
                priority = priority_exts.index(file_ext) if file_ext in priority_exts else len(priority_exts)
                files_to_check.append((priority, file_path))
        
        # Sort by priority
        files_to_check.sort()
        
        # Process files
        for _, file_path in files_to_check:
            results["checked_files"] += 1
            
            try:
                # Check if the file is incomplete
                if self.large_file_handler.is_incomplete_file(file_path):
                    file_ext = os.path.splitext(file_path)[1].lower()
                    
                    if file_ext == '.js':
                        # Use specialized handler for JS files
                        if self.large_file_handler.handle_large_js_file(
                            file_path, 
                            None,  # No optimized prompt needed
                            self.project_structure,
                            self.element_dictionary
                        ):
                            results["completed_files"] += 1
                        else:
                            results["failed_completions"] += 1
                    else:
                        # Use general completion for other files
                        if self.large_file_handler.complete_file(
                            file_path,
                            None,  # No optimized prompt needed 
                            self.project_structure,
                            self.element_dictionary
                        ):
                            results["completed_files"] += 1
                        else:
                            results["failed_completions"] += 1
            except Exception as e:
                print(f"Error checking/completing file {file_path}: {str(e)}")
                results["failed_completions"] += 1
        
        return results
