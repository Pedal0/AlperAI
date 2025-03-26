"""
Centralized prompt definitions for AI completion requests.

This module contains all the prompts used throughout the application,
organized by category and purpose. Using centralized prompts ensures
consistency and makes it easier to modify prompts across the application.
"""

# System messages (instructions for the AI)
SYSTEM_MESSAGES = {
    "optimize_prompt": """
    You are an expert application design assistant specializing in software architecture and requirements analysis. Your task is to take a user's application 
    description and transform it into a comprehensive project specification by:
    
    1. Identifying and clarifying ambiguous or incomplete requirements
    2. Adding appropriate technical and architectural structure
    3. Suggesting specific, relevant technologies, frameworks, and libraries that best suit the project
    4. Expanding feature descriptions with implementation details
    5. Organizing requirements into logical categories (e.g., frontend, backend, database, authentication)
    6. Identifying potential challenges and providing solutions
    7. Adding non-functional requirements like security, performance, and scalability considerations
    8. Suggesting appropriate design patterns where applicable
    9. Providing clear, actionable development guidelines
    
    Your response should maintain the original intent of the user's description while making it as clear, detailed, and implementation-ready as possible.
    Focus on being specific rather than generic, and practical rather than theoretical.
    """,
    
    "project_structure": """
    You are an expert software architect. Your task is to design an appropriate project structure
    for the described application. Consider best practices for the technologies involved and create
    a logical file organization. You MUST return the structure as a valid JSON object.
    
    For web applications, be sure to include an "assets/icons" directory to store SVG icons
    that will be used throughout the application. Common icons like navigation, social media,
    and UI controls should be included in the structure.
    """,
    
    "element_dictionary": """
    You are an expert frontend developer. Your task is to create a comprehensive dictionary of 
    HTML elements, CSS classes and IDs based on application requirements. This dictionary will 
    ensure consistent naming across HTML, CSS, and JavaScript files.
    
    Also include an "icons" section that lists all the SVG icons that should be generated for the application.
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
    8. For icons, use the SVG files in the assets/icons directory using <img> tags or include them inline when appropriate.
    
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
    7. DESIGN REQUIREMENTS:
       - Create an aesthetically pleasing design using modern principles
       - Include smooth transitions and animations where appropriate
       - Use CSS variables for consistent color themes
       - Implement hover effects for interactive elements
       - Use subtle shadows and rounded corners for depth
       - Create responsive layouts that work on mobile, tablet, and desktop
       - Include styling for icons (size, color, hover effects)
    
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
    7. ANIMATION AND INTERACTIVITY REQUIREMENTS:
       - Add smooth animations for state changes (using CSS transitions/animations or JS)
       - Implement elegant loading states where appropriate
       - Create interactive UI elements with appropriate feedback
       - Use modern animation libraries when needed (e.g., GSAP, anime.js)
       - Ensure animations enhance UX without being distracting
       - If needed, implement icon animations or transitions
    
    File description: {file_description}
    """,
    
    "svg_icon_generator": """
    You are an expert SVG icon designer. Your task is to create clean, scalable SVG icons
    for use in a web application. Each icon should be simple, professional, and optimized for web use.
    
    IMPORTANT REQUIREMENTS:
    1. Create clean, minimal SVG markup without unnecessary elements or attributes
    2. Ensure icons are designed on a consistent grid (e.g., 24x24)
    3. Use vector paths rather than raster elements
    4. Optimize for both visual clarity and file size
    5. Use currentColor for stroke/fill to allow styling via CSS
    6. Include appropriate viewBox attribute
    7. Design should be simple and recognizable at small sizes
    8. Do not include any script tags or external dependencies
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
    """,
    
    "code_validator": """
    You are an expert code reviewer and debugger. Your task is to analyze a single file of code,
    identify potential issues, and suggest improvements. Focus on:
    
    1. Syntax errors and bugs
    2. Logic flaws
    3. Best practices violations
    4. Performance optimizations
    5. Security concerns
    6. Accessibility issues (for frontend code)
    7. Consistency with provided architecture/requirements
    
    Provide specific, actionable feedback that can be used to improve the code quality.
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
    
    IMPORTANT REQUIREMENTS:
    1. For static websites, ALWAYS include an index.html file at the root level.
    2. For any web application or website, ALWAYS include an assets/icons directory with common SVG icons:
       - navigation icons (menu, home, back, forward)
       - action icons (add, delete, edit, save, download)
       - UI control icons (close, expand, collapse, search, settings)
       - status icons (success, error, warning, info)
       - social media icons if relevant to the application
    3. Each icon should be in its own SVG file with an appropriate name (e.g., icon-menu.svg, icon-home.svg).
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
        "icons": [
            {{
                "name": "menu",            // Icon name (without prefix or suffix)
                "file": "icon-menu.svg",   // Filename in assets/icons directory
                "description": "Hamburger menu icon"  // Brief description of the icon's purpose
            }},
            // Add more icons as needed for the application
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
            }},
            "animations": {{
                "transition_speed": "0.3s",
                "hover_effect": "transform: scale(1.05)",
                "page_transition": "fade-in 0.4s ease-out"
            }}
        }}
    }}

    Create a comprehensive and detailed dictionary that covers all major UI elements needed for this application.
    Be specific about naming conventions and maintain consistency (e.g., use either kebab-case or camelCase consistently).
    Include animations settings to encourage consistent animation effects across the site.
    
    For the icons section, include at least 8-12 commonly needed icons relevant to the application's functionality.
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
    7. Use modern HTML5 elements (header, nav, main, section, article, footer) appropriately.
    8. Include appropriate ARIA attributes for accessibility.
    9. Ensure the structure facilitates animations and transitions defined in CSS.
    10. For icons, use the SVG files specified in the element dictionary. Include them using either:
        - <img src="assets/icons/[icon-file]"> tags with appropriate alt text
        - Or as inline SVG when more styling control is needed
    
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
    7. MODERN DESIGN REQUIREMENTS:
       - Use CSS variables for theming (--primary-color, etc.)
       - Implement subtle animations and transitions for interactive elements
       - Create hover/focus states with smooth transitions 
       - Use box-shadow for depth and dimension
       - Implement responsive layouts using flexbox or grid
       - Add appropriate whitespace and typography scaling
       - Use modern CSS features like clamp(), calc(), etc.
       - Add micro-interactions (button hover effects, input focus states, etc.)
    8. ANIMATION REQUIREMENTS:
       - Include keyframe animations for complex effects
       - Use transitions for smooth state changes (0.3s ease is a good default)
       - Implement subtle entrance animations for important elements
       - Add hover/focus animation effects for interactive elements
       - Use transform properties for better performance
       - Consider reduced motion preferences with @media (prefers-reduced-motion)
    9. ICON STYLING:
       - Include styles for SVG icons (size, color, alignment)
       - Add hover effects for interactive icons
       - Ensure consistent sizing across similar types of icons
       - Use currentColor for SVG fill/stroke to inherit text color
       - Consider adding subtle animations for interactive icons
    
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
    7. ANIMATION & INTERACTIVITY REQUIREMENTS:
       - Implement smooth animations for UI state changes
       - Add entrance/exit animations for dynamic content
       - Include loading states with appropriate visual feedback
       - Create interactive components with proper event handling
       - Ensure animations enhance rather than hinder UX
       - Consider performance implications of animations
       - Implement scroll-based animations where appropriate
       - Add touch gesture support for mobile devices
    8. ICON FUNCTIONALITY (if applicable):
       - Implement any needed icon animations or transitions
       - Add functionality to toggle icon states (e.g., expand/collapse)
       - Ensure proper accessibility for interactive icons
    
    Provide only the JavaScript code without any HTML or CSS.
    """,
    
    "svg_icon": """
    Create an SVG icon for '{icon_name}' to be used in a {app_type} application.
    
    Description: {icon_description}
    
    REQUIREMENTS:
    1. Create a clean, minimal SVG with a viewBox attribute (typically 24x24 or similar)
    2. Use vector paths (no raster elements)
    3. Use currentColor for stroke/fill to allow styling via CSS
    4. Optimize the SVG by removing any unnecessary elements or attributes
    5. Make the icon simple but recognizable even at small sizes
    6. Create professional, modern looking icon suitable for the application context
    7. Do NOT include any xmlns attributes or other namespace declarations
    8. Return ONLY the SVG code, nothing else
    
    Include a brief comment at the top with the icon name and purpose.
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
    """,
    
    "code_validator": """
    Please analyze the following {file_ext} code for potential issues and provide suggestions for improvement.
    
    File path: {file_path}
    File description: {file_description}
    
    CODE TO REVIEW:
    {file_content}
    
    Provide your analysis in the following format:
    1. CRITICAL ISSUES: Any bugs, errors, or problems that would prevent the code from working
    2. IMPROVEMENT SUGGESTIONS: Ways to optimize, improve readability, or follow best practices
    3. DESIGN/UX RECOMMENDATIONS: (for HTML/CSS/JS only) Suggestions to enhance the user experience
    4. IMPROVED CODE: A version of the code with your suggested improvements
    
    Focus particularly on ensuring that the code follows modern best practices and delivers a high-quality user experience.
    """
}

# Fallback responses (when something goes wrong)
FALLBACKS = {
    "project_structure": {
        "directories": [
            {"name": "src", "path": "src", "description": "Source code"},
            {"name": "assets", "path": "assets", "description": "Static assets"},
            {"name": "assets/icons", "path": "assets/icons", "description": "SVG icons"}
        ],
        "files": [
            {"name": "README.md", "path": "README.md", "description": "Documentation", "type": "documentation"},
            {"name": "index.html", "path": "index.html", "description": "Main entry point", "type": "code"},
            {"name": "icon-menu.svg", "path": "assets/icons/icon-menu.svg", "description": "Menu icon", "type": "image"},
            {"name": "icon-home.svg", "path": "assets/icons/icon-home.svg", "description": "Home icon", "type": "image"}
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
        "icons": [
            {"name": "menu", "file": "icon-menu.svg", "description": "Hamburger menu icon"},
            {"name": "home", "file": "icon-home.svg", "description": "Home navigation icon"},
            {"name": "settings", "file": "icon-settings.svg", "description": "Settings or configuration icon"},
            {"name": "user", "file": "icon-user.svg", "description": "User profile icon"}
        ],
        "styles": {
            "color_scheme": {
                "primary": "#4CAF50",
                "secondary": "#2196F3",
                "text": "#333333",
                "background": "#FFFFFF"
            },
            "typography": {
                "heading_font": "'Roboto', sans-serif",
                "body_font": "'Open Sans', sans-serif"
            },
            "animations": {
                "transition_speed": "0.3s",
                "hover_effect": "transform: scale(1.02)",
                "page_transition": "fade-in 0.3s ease"
            }
        }
    }
}
