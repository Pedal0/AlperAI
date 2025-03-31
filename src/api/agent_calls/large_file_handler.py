"""
Large file handler agent module.

This module provides specialized handling for large files that might exceed
token limits during generation or validation. It splits files into manageable chunks
and processes them incrementally.
"""

import os
import re
import json
from src.api.openrouter import generate_text, SYSTEM_MESSAGES
from src.config.constants import PRECISE_TEMPERATURE

class LargeFileHandler:
    """Handler for processing and validating large files in chunks."""
    
    def __init__(self, max_chunk_size=4000):
        """
        Initialize the large file handler.
        
        Args:
            max_chunk_size (int): Maximum size in characters for each chunk
        """
        self.max_chunk_size = max_chunk_size
    
    def is_incomplete_file(self, file_path, file_content=None):
        """
        Check if a file appears to be incomplete based on various indicators.
        
        Args:
            file_path (str): Path to the file
            file_content (str, optional): File content if already loaded
            
        Returns:
            bool: True if the file appears incomplete, False otherwise
        """
        if file_content is None:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
            except Exception as e:
                print(f"Error reading file: {str(e)}")
                return False
        
        # Get file extension
        ext = os.path.splitext(file_path)[1].lower()
        
        # Check for common incomplete file indicators
        incomplete_indicators = {
            '.js': [
                # Incomplete function/class definitions
                r'function\s+\w+\s*\([^)]*\)\s*{\s*$',
                r'class\s+\w+\s*{\s*$',
                # Missing closing brackets/braces
                r'{\s*$',
                # Unclosed multiline comments
                r'/\*(?![\s\S]*?\*/)',
                # Incomplete if/else blocks
                r'if\s*\([^)]*\)\s*{\s*$',
                r'else\s*{\s*$',
                # Incomplete try/catch blocks
                r'try\s*{\s*$',
                r'catch\s*\([^)]*\)\s*{\s*$',
                # Abrupt ending
                r'\/\/\s*TODO',
                r'\/\/\s*\.\.\.$'
            ],
            '.html': [
                # Unclosed tags
                r'<([a-z]+)[^>]*>(?![\s\S]*?</\1>)',
                # Missing closing body or html tags
                r'<body[^>]*>(?![\s\S]*?</body>)',
                r'<html[^>]*>(?![\s\S]*?</html>)',
                # Abrupt ending
                r'<!--\s*TODO',
                r'<!--\s*\.\.\.$'
            ],
            '.css': [
                # Unclosed CSS blocks
                r'{\s*$',
                # Unclosed media queries
                r'@media[^{]*{\s*$',
                # Abrupt ending
                r'/\*\s*TODO',
                r'/\*\s*\.\.\.$'
            ],
            '.py': [
                # Incomplete function/class definitions
                r'def\s+\w+\s*\([^)]*\):\s*$',
                r'class\s+\w+\s*:\s*$',
                # Incomplete if/else blocks
                r'if\s+.*:\s*$',
                r'else:\s*$',
                r'elif\s+.*:\s*$',
                # Incomplete try/except blocks
                r'try:\s*$',
                r'except.*:\s*$',
                # Abrupt ending
                r'#\s*TODO',
                r'#\s*\.\.\.$'
            ]
        }
        
        # Generic indicators for any file type
        generic_indicators = [
            # Truncated content
            r'\.{3,}\s*$',
            # TODO markers at the end
            r'TODO:?\s*$',
            # Explicitly marked as incomplete
            r'INCOMPLETE\s*$',
            r'NOT\s+FINISHED\s*$'
        ]
        
        # Check file size - suspiciously close to token limits (around 4096 tokens ~ 16K chars)
        if len(file_content) > 15000 and len(file_content) < 17000:
            # Files right at this boundary are suspicious
            print(f"File size suspicious for incompleteness: {file_path} ({len(file_content)} chars)")
            if ext in ['.js', '.html', '.css', '.py']:
                return True
        
        # Check file-specific indicators
        indicators = incomplete_indicators.get(ext, []) + generic_indicators
        
        for pattern in indicators:
            if re.search(pattern, file_content):
                print(f"Incomplete file detected: {file_path} (matched pattern: {pattern})")
                return True
                
        # Check for JavaScript specific issues
        if ext == '.js':
            # Check for balanced braces
            open_braces = file_content.count('{')
            close_braces = file_content.count('}')
            if open_braces > close_braces:
                print(f"Unbalanced braces in JavaScript file: {file_path} ({open_braces} opens vs {close_braces} closes)")
                return True
                
            # Check for unclosed quotes
            quote_chars = ["'", '"', '`']
            for quote in quote_chars:
                if file_content.count(quote) % 2 != 0:
                    print(f"Uneven number of {quote} quotes in JavaScript file: {file_path}")
                    return True
        
        return False
    
    def complete_file(self, file_path, optimized_prompt=None, project_structure=None, element_dictionary=None):
        """
        Complete an incomplete file by analyzing it and generating the missing parts.
        
        Args:
            file_path (str): Path to the incomplete file
            optimized_prompt (str, optional): The optimized prompt for context
            project_structure (dict/str, optional): Project structure for context
            element_dictionary (dict/str, optional): Element dictionary for frontend files
            
        Returns:
            str: The completed file content, or None if completion failed
        """
        try:
            print(f"Attempting to complete file: {file_path}")
            
            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
                
            # Get file info
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_name)[1].lower()
            
            # Prepare structure info
            structure_info = {}
            try:
                if isinstance(project_structure, str):
                    structure_data = json.loads(project_structure)
                else:
                    structure_data = project_structure or {}
                
                # Find file info in structure
                for file_info in structure_data.get("files", []):
                    if file_path.endswith(file_info.get("path", "")):
                        structure_info = file_info
                        break
            except:
                # Continue with empty structure info if parsing fails
                pass
                
            # Create prompts based on file type
            file_description = structure_info.get("description", f"A {file_ext} file that needs completion")
            
            # Create a specialized prompt for the file type
            system_message = f"""
            You are an expert code completer specialized in fixing incomplete {file_ext} files.
            Your task is to analyze an incomplete file and add the missing code to make it complete and functional.
            Focus only on adding the missing parts - do not rewrite working code that's already there.
            
            VERY IMPORTANT: Respect any patterns, coding style, and naming conventions in the existing code.
            Make sure to maintain consistency throughout the file.
            """
            
            prompt = f"""
            I have an incomplete {file_ext} file that needs to be completed. The file was cut off during generation.
            Analyze the file and complete it by adding the missing parts.
            
            File name: {file_name}
            File description: {file_description}
            
            INSTRUCTIONS:
            1. Analyze the provided code below and identify where it cuts off or what parts are missing
            2. Complete the file by adding the missing code to make it functional
            3. Maintain the same coding style, patterns, and naming conventions
            4. Return the COMPLETE file content (existing + new code)
            5. Make sure to close any unclosed structures (functions, classes, blocks, comments, etc.)
            6. Ensure the code is fully functional
            
            EXISTING CONTENT:
            ```
            {file_content}
            ```
            
            Please complete this file by adding the missing parts.
            """
            
            # Add context for frontend files
            if file_ext in ['.html', '.js', '.css']:
                if element_dictionary:
                    element_dict_str = element_dictionary
                    if not isinstance(element_dictionary, str):
                        element_dict_str = json.dumps(element_dictionary, indent=2)
                    prompt += f"\n\nElement Dictionary for consistency:\n{element_dict_str}"
            
            # Generate the completed file
            completed_content = generate_text(
                prompt=prompt,
                temperature=PRECISE_TEMPERATURE,
                system_message=system_message
            )
            
            # Extract just the code (remove any markdown code blocks or explanations)
            # Look for code blocks first
            code_pattern = r'```(?:\w+)?\s*([\s\S]+?)\s*```'
            code_match = re.search(code_pattern, completed_content)
            
            if code_match:
                completed_content = code_match.group(1).strip()
            else:
                # Try to remove explanation lines
                lines = completed_content.splitlines()
                code_lines = []
                capturing = False
                
                for line in lines:
                    line_lower = line.lower().strip()
                    # Skip explanation lines that often appear at the beginning
                    if not capturing and (line_lower.startswith('here') or line_lower.startswith('i ') or
                                         line_lower.startswith('the ') or line_lower.startswith('this ')):
                        continue
                    
                    # Start capturing when we likely hit code
                    if not capturing and (line.startswith('import ') or line.startswith('function ') or
                                         line.startswith('class ') or line.startswith('const ') or
                                         line.startswith('let ') or line.startswith('var ') or
                                         line.startswith('<!DOCTYPE') or line.startswith('<html') or
                                         line.startswith('/* ') or line.startswith('// ')):
                        capturing = True
                    
                    if capturing:
                        code_lines.append(line)
                
                if code_lines:
                    completed_content = '\n'.join(code_lines)
            
            # Write the completed content back to the file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(completed_content)
            
            print(f"Successfully completed file: {file_path}")
            return completed_content
            
        except Exception as e:
            print(f"Error completing file {file_path}: {str(e)}")
            return None

    def handle_large_js_file(self, file_path, optimized_prompt, project_structure=None, element_dictionary=None):
        """
        Special handler for large JavaScript files that might have been cut off during generation.
        Analyzes the file structure and completes it by generating any missing components.
        
        Args:
            file_path (str): Path to the JavaScript file
            optimized_prompt (str): The optimized prompt for context
            project_structure (dict/str, optional): Project structure for context
            element_dictionary (dict/str, optional): Element dictionary for frontend consistency
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print(f"Handling large JavaScript file: {file_path}")
            
            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
                
            # Check if it's truly incomplete
            if not self.is_incomplete_file(file_path, file_content):
                print(f"File seems complete, no need for special handling: {file_path}")
                return True
                
            # Get file details
            file_name = os.path.basename(file_path)
            
            # Create a specialized system message for JavaScript files
            system_message = """
            You are an expert JavaScript developer specializing in completing large JavaScript files.
            Your task is to analyze an incomplete JavaScript file and identify missing components,
            incomplete functions, or unfinished code blocks.
            """
            
            # Create a special prompt to analyze the file structure first
            analysis_prompt = f"""
            Analyze this potentially incomplete JavaScript file and identify:
            1. What components or sections appear to be missing or incomplete
            2. Any functions that start but don't finish
            3. Where the file appears to cut off
            4. What would be needed to make this file complete based on its purpose
            
            File name: {file_name}
            
            FILE CONTENT:
            ```javascript
            {file_content}
            ```
            
            Return your analysis in JSON format with these fields:
            - is_incomplete: boolean indicating if the file appears incomplete
            - missing_parts: array of missing components/sections
            - cutoff_point: line number or description of where the file cuts off
            - completion_strategy: how to approach completing this file
            """
            
            # Get the analysis result
            analysis_json = generate_text(
                prompt=analysis_prompt, 
                temperature=PRECISE_TEMPERATURE,
                system_message=system_message,
                json_mode=True
            )
            
            # Parse the analysis
            try:
                analysis = json.loads(analysis_json)
                print(f"Analysis results for {file_name}:")
                print(json.dumps(analysis, indent=2))
                
                # If the file is indeed incomplete, generate the missing parts
                if analysis.get("is_incomplete", False):
                    completion_prompt = f"""
                    Complete this incomplete JavaScript file by adding the missing parts identified in the analysis.
                    
                    File name: {file_name}
                    
                    ANALYSIS RESULTS:
                    {json.dumps(analysis, indent=2)}
                    
                    CURRENT CONTENT:
                    ```javascript
                    {file_content}
                    ```
                    
                    IMPORTANT:
                    1. Maintain the same coding style, patterns, and variable naming conventions
                    2. Complete all missing functions and components identified in the analysis
                    3. Make sure all open brackets, parentheses, and quotes are properly closed
                    4. Return the COMPLETE file with both existing and added code
                    5. The result should be a fully functional JavaScript file
                    """
                    
                    # If we have an element dictionary, include it for consistency
                    if element_dictionary:
                        element_dict_str = element_dictionary
                        if not isinstance(element_dictionary, str):
                            element_dict_str = json.dumps(element_dictionary, indent=2)
                        completion_prompt += f"\n\nElement Dictionary for consistency:\n{element_dict_str}"
                    
                    # Generate the completed file
                    completed_content = generate_text(
                        prompt=completion_prompt,
                        temperature=PRECISE_TEMPERATURE,
                        system_message=system_message
                    )
                    
                    # Extract just the code (remove any markdown code blocks or explanations)
                    code_pattern = r'```(?:javascript)?\s*([\s\S]+?)\s*```'
                    code_match = re.search(code_pattern, completed_content)
                    
                    if code_match:
                        completed_content = code_match.group(1).strip()
                    
                    # Write the completed content back to the file
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(completed_content)
                        
                    print(f"Successfully completed JavaScript file: {file_path}")
                    return True
                    
                else:
                    print(f"Analysis indicates the file is already complete: {file_path}")
                    return True
                    
            except json.JSONDecodeError:
                print(f"Failed to parse analysis results for {file_name}")
                # Fall back to the general completion method
                return self.complete_file(file_path, optimized_prompt, project_structure, element_dictionary) is not None
                
        except Exception as e:
            print(f"Error handling large JavaScript file {file_path}: {str(e)}")
            return False
