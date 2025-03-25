"""
Centralized prompt definitions for AI completion requests.

This module contains all the prompts used throughout the application,
organized by category and purpose. Using centralized prompts ensures
consistency and makes it easier to modify prompts across the application.
"""

# System messages (instructions for the AI)
SYSTEM_MESSAGES = {
    "optimize_prompt": """
    You are an expert application design assistant. Your task is to take a user's application 
    description and enhance it by adding structure, clarifying ambiguities, and suggesting 
    relevant features. Maintain the original intent while making it as clear and detailed as possible.
    """,
    
    "project_structure": """
    You are an expert software architect. Your task is to design an appropriate project structure
    for the described application. Consider best practices for the technologies involved and create
    a logical file organization. You MUST return the structure as a valid JSON object.
    """,
    
    "element_dictionary": """
    You are an expert frontend developer. Your task is to create a comprehensive dictionary of 
    HTML elements, CSS classes and IDs based on application requirements. This dictionary will 
    ensure consistent naming across HTML, CSS, and JavaScript files.
    """,
    
    "html_generator": """
    You are an expert HTML developer. Your task is to generate clean, functional HTML for a {file_name} file.
    
    IMPORTANT INSTRUCTIONS:
    1. Do NOT include any CSS styles inside <style> tags. All styles must be in external CSS files.
    2. Do NOT include any JavaScript code inside <script> tags. All JS must be in external JS files.
    3. Use the following external CSS files (link them in the <head> section):
       {css_files}
    4. Use the following external JavaScript files (link them at the end of <body>):
       {js_files}
    5. Create proper HTML5 structure with <!DOCTYPE html>, <html>, <head>, and <body> tags.
    6. Include responsive viewport meta tag.
    7. VERY IMPORTANT: Use EXACTLY the element IDs and classes provided in the element dictionary for consistency across files.
    
    File description: {file_description}
    """,
    
    "css_generator": """
    You are an expert CSS developer. Your task is to generate clean, well-organized CSS for a {file_name} file.
    
    IMPORTANT INSTRUCTIONS:
    1. Create comprehensive styles for the associated HTML pages.
    2. Use CSS best practices with clear organization and comments.
    3. Include responsive design with appropriate media queries.
    4. Use modern CSS features when appropriate.
    5. Organize the CSS with logical sections.
    6. VERY IMPORTANT: Use EXACTLY the element IDs and classes provided in the element dictionary for consistency across files.
    
    File description: {file_description}
    """,
    
    "js_generator": """
    You are an expert JavaScript developer. Your task is to generate clean, functional JavaScript for a {file_name} file.
    
    IMPORTANT INSTRUCTIONS:
    1. Write modern, clean JavaScript following best practices.
    2. Create all necessary functionality described in the application requirements.
    3. Use appropriate event listeners for DOM interactions.
    4. Include proper error handling.
    5. Add helpful comments where necessary.
    6. VERY IMPORTANT: Use EXACTLY the element IDs and classes provided in the element dictionary for consistency across files.
    
    File description: {file_description}
    """,
    
    "default_file_generator": """
    You are an expert developer specializing in creating {file_ext} files. Your task
    is to generate clean, functional code for a {file_name} file that meets the application requirements.
    
    This file is of type: {file_type}
    Description: {file_description}
    
    Follow best practices for this file type. Generate complete, working code with proper imports and dependencies.
    Do not include example code markers like ```python or ```javascript - just write the actual file content.
    """,
    
    "readme_generator": """
    You are an expert technical writer. Your task is to create a comprehensive README.md file
    that clearly explains the application, its features, installation, usage, and structure.
    """
}

# Prompts (user instructions for the AI)
PROMPTS = {
    "optimize_prompt": """
    Please optimize and enhance the following application description by:
    1. Clarifying any ambiguous requirements
    2. Adding appropriate structure
    3. Suggesting relevant technologies and features
    4. Organizing the requirements in a logical manner

    Original Description:
    {user_prompt}
    
    Please provide the optimized description in a clear, structured format.
    """,
    
    "project_structure": """
    Based on the following application requirements, design a comprehensive project structure
    with appropriate directories and files. Consider separation of concerns, maintainability,
    and best practices for the technologies involved.

    Application Requirements:
    {optimized_prompt}
    
    Return a JSON structure representing the project directories and files. Use the following format:
    {{
        "directories": [
            {{
                "name": "directory_name",
                "path": "relative/path/to/directory",
                "description": "Brief description of the directory's purpose"
            }}
        ],
        "files": [
            {{
                "name": "filename.ext",
                "path": "relative/path/to/file",
                "description": "Brief description of the file's purpose",
                "type": "code|config|data|documentation|style|test"
            }}
        ]
    }}

    Make sure all paths are correct and consistent. Use proper file extensions based on the content.
    Don't include '│', '├──', '└──' or similar characters for tree visualization.
    
    IMPORTANT: For static websites, ALWAYS include an index.html file at the root level.
    """,
    
    "element_dictionary": """
    Based on the following application requirements, create a detailed dictionary of HTML elements, 
    CSS classes, and IDs that will be used consistently across HTML, CSS, and JavaScript files.
    
    Application Requirements:
    {optimized_prompt}
    
    Return a JSON object with the following structure:
    {{
        "page_structure": {{
            "main_container": "container",  // Main container class name
            "header": "site-header",        // Header class name
            "footer": "site-footer",        // Footer class name
            "navigation": "main-nav"        // Navigation class name
        }},
        "components": [
            {{
                "name": "login_form",       // Component name (descriptive)
                "element_type": "form",     // HTML element type
                "id": "login-form",         // ID attribute
                "classes": ["form", "login-form"],  // CSS classes
                "children": [               // Child elements (optional)
                    {{
                        "name": "username_input",
                        "element_type": "input",
                        "id": "username",
                        "classes": ["form-input", "username-field"]
                    }},
                    {{
                        "name": "login_button",
                        "element_type": "button",
                        "id": "login-btn",
                        "classes": ["btn", "btn-primary", "login-button"]
                    }}
                ]
            }}
        ],
        "styles": {{
            "color_scheme": {{
                "primary": "#4285F4",
                "secondary": "#34A853",
                "accent": "#FBBC05",
                "text": "#333333",
                "background": "#FFFFFF"
            }},
            "typography": {{
                "heading_font": "'Roboto', sans-serif",
                "body_font": "'Open Sans', sans-serif"
            }}
        }}
    }}

    Create a comprehensive and detailed dictionary that covers all major UI elements needed for this application.
    Be specific about naming conventions and maintain consistency (e.g., use either kebab-case or camelCase consistently).
    """,
    
    "html_file": """
    Generate an HTML file for '{file_name}' based on the following application requirements.
    
    Application Requirements:
    {optimized_prompt}
    
    File Information:
    Path: {file_path}
    Description: {file_description}
    
    External Resources:
    - CSS Files: {css_files}
    - JS Files: {js_files}
    
    Element Dictionary (USE THESE EXACT IDs AND CLASSES FOR CONSISTENCY):
    {element_dictionary}
    
    IMPORTANT REQUIREMENTS:
    1. NEVER include CSS styles within <style> tags - use only external CSS files referenced above.
    2. NEVER include JavaScript within <script> tags - use only external JS files referenced above.
    3. DO link to the external files using proper relative paths.
    4. Create semantic HTML5 structure.
    5. Use EXACTLY the element IDs and classes from the element dictionary to ensure consistency with CSS and JS files.
    6. If the element dictionary specifies components, implement them in the HTML structure.
    
    Create a complete HTML file without inline styles or scripts.
    """,
    
    "css_file": """
    Generate comprehensive CSS styles for '{file_name}' based on the following application requirements.
    
    Application Requirements:
    {optimized_prompt}
    
    File Information:
    Path: {file_path}
    Description: {file_description}
    
    Element Dictionary (USE THESE EXACT IDs AND CLASSES FOR CONSISTENCY):
    {element_dictionary}
    
    IMPORTANT REQUIREMENTS:
    1. Create styles specifically for the IDs and classes defined in the element dictionary.
    2. Include responsive design with media queries.
    3. Use the color scheme and typography settings from the element dictionary if available.
    4. Organize styles logically (e.g., reset, layout, components, utilities).
    5. Add helpful comments to indicate section purposes.
    6. ONLY style elements, classes and IDs that exist in the element dictionary to ensure consistency with HTML.
    
    Provide only the CSS code without any HTML or JS.
    """,
    
    "js_file": """
    Generate JavaScript code for '{file_name}' based on the following application requirements.
    
    Application Requirements:
    {optimized_prompt}
    
    File Information:
    Path: {file_path}
    Description: {file_description}
    
    Element Dictionary (USE THESE EXACT IDs AND CLASSES FOR CONSISTENCY):
    {element_dictionary}
    
    IMPORTANT REQUIREMENTS:
    1. Write clean, well-documented JavaScript.
    2. Use modern JS features (ES6+) where appropriate.
    3. Implement proper event handling and DOM manipulation using IDs and classes from the element dictionary.
    4. Add error handling for any async operations or potential issues.
    5. Implement all required functionality described in the requirements.
    6. ONLY target elements with IDs and classes that exist in the element dictionary to ensure consistency with HTML.
    
    Provide only the JavaScript code without any HTML or CSS.
    """,
    
    "default_file": """
    Generate the content for a file named '{file_name}' based on the following application
    requirements and project structure. The code should be clean, well-structured, and follow best practices.
    
    File Path: {file_path}
    File Description: {file_description}
    File Type: {file_type}
    
    Application Requirements:
    {optimized_prompt}
    
    File Structure Context:
    {structure_info}
    
    Please provide only the complete code for this specific file without any explanations or code block markers.
    """,
    
    "readme": """
    Create a comprehensive README.md file for a project named '{app_name}' based on the
    following requirements and structure. Include sections for description, features, installation,
    usage, project structure, and license.
    
    Application Requirements:
    {optimized_prompt}
    
    Project Structure:
    {project_structure}
    
    Please provide a complete, well-formatted markdown document.
    """
}

# Fallback responses (when something goes wrong)
FALLBACKS = {
    "project_structure": {
        "directories": [{"name": "src", "path": "src", "description": "Source code"}],
        "files": [
            {"name": "README.md", "path": "README.md", "description": "Documentation", "type": "documentation"},
            {"name": "index.html", "path": "index.html", "description": "Main entry point", "type": "code"}
        ]
    },
    
    "element_dictionary": {
        "page_structure": {
            "main_container": "container",
            "header": "header",
            "footer": "footer",
            "navigation": "nav"
        },
        "components": [
            {
                "name": "main_content",
                "element_type": "div",
                "id": "main-content",
                "classes": ["main", "content"]
            }
        ],
        "styles": {
            "color_scheme": {
                "primary": "#4CAF50",
                "secondary": "#2196F3",
                "text": "#333333",
                "background": "#FFFFFF"
            }
        }
    }
}
