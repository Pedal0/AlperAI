import os
import json
import re
from openai import OpenAI
from src.config.constants import (
    OPENROUTER_BASE_URL, 
    OPENROUTER_API_KEY, 
    OPENAI_API_KEY,
    OPENROUTER_SITE_URL, 
    OPENROUTER_SITE_NAME,
    OPENROUTER_MODEL,
    OPENAI_MODEL,
    USE_OPENROUTER,
    DEFAULT_TEMPERATURE
)

def get_client():
    """Return the appropriate client based on configuration"""
    if USE_OPENROUTER and OPENROUTER_API_KEY:
        return OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=OPENROUTER_API_KEY,
        )
    else:
        # Fallback to OpenAI
        return OpenAI(api_key=OPENAI_API_KEY)

def get_model_name():
    """Return the appropriate model name based on configuration"""
    if USE_OPENROUTER and OPENROUTER_API_KEY:
        return OPENROUTER_MODEL
    else:
        return OPENAI_MODEL

def clean_generated_content(content):
    """
    Clean the generated content by removing code block markers
    
    Args:
        content (str): The content to clean
        
    Returns:
        str: The cleaned content
    """
    # Remove markdown code block markers (```language and ```)
    content = re.sub(r'^```[\w-]*\n', '', content)
    content = re.sub(r'\n```$', '', content)
    
    # Remove triple backticks anywhere in the content
    content = re.sub(r'```', '', content)
    
    return content

def generate_text(prompt, temperature=DEFAULT_TEMPERATURE, system_message=None, json_mode=False):
    """
    Generate text using the configured AI model
    
    Args:
        prompt (str): The user prompt
        temperature (float): The temperature for generation
        system_message (str): Optional system message
        json_mode (bool): Whether to request JSON output
        
    Returns:
        str: The generated response
    """
    client = get_client()
    model = get_model_name()
    
    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    
    messages.append({"role": "user", "content": prompt})
    
    extra_args = {}
    if USE_OPENROUTER and OPENROUTER_API_KEY:
        extra_args = {
            "extra_headers": {
                "HTTP-Referer": OPENROUTER_SITE_URL,
                "X-Title": OPENROUTER_SITE_NAME,
            }
        }
    
    if json_mode:
        extra_args["response_format"] = {"type": "json_object"}
    
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        **extra_args
    )
    
    return clean_generated_content(completion.choices[0].message.content)

def optimize_prompt(user_prompt):
    """Optimize user prompt for better results"""
    system_message = """
    You are an expert application design assistant. Your task is to take a user's application 
    description and enhance it by adding structure, clarifying ambiguities, and suggesting 
    relevant features. Maintain the original intent while making it as clear and detailed as possible.
    """
    
    prompt = f"""
    Please optimize and enhance the following application description by:
    1. Clarifying any ambiguous requirements
    2. Adding appropriate structure
    3. Suggesting relevant technologies and features
    4. Organizing the requirements in a logical manner

    Original Description:
    {user_prompt}
    
    Please provide the optimized description in a clear, structured format.
    """
    
    return generate_text(prompt, temperature=0.3, system_message=system_message)

def generate_project_structure(optimized_prompt):
    """Generate project structure based on the optimized prompt as JSON"""
    system_message = """
    You are an expert software architect. Your task is to design an appropriate project structure
    for the described application. Consider best practices for the technologies involved and create
    a logical file organization. You MUST return the structure as a valid JSON object.
    """
    
    prompt = f"""
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
    """
    
    try:
        structure_json = generate_text(prompt, temperature=0.4, system_message=system_message, json_mode=True)
        # Validate that it's proper JSON before returning
        json_data = json.loads(structure_json)
        
        # If this is a static website, ensure there's an index.html
        if 'This should be a static website' in optimized_prompt:
            has_index_html = False
            for file in json_data.get("files", []):
                if file.get("name") == "index.html" or file.get("path").endswith("/index.html"):
                    has_index_html = True
                    break
            
            if not has_index_html:
                json_data["files"].append({
                    "name": "index.html",
                    "path": "index.html",
                    "description": "Main entry point for the website",
                    "type": "code"
                })
                # Re-serialize with the added file
                structure_json = json.dumps(json_data)
        
        return structure_json
    except json.JSONDecodeError:
        # Fallback: retry with more explicit instructions
        prompt += "\nIMPORTANT: You MUST return valid JSON. Check that your response can be parsed by json.loads()."
        try:
            structure_json = generate_text(prompt, temperature=0.2, system_message=system_message, json_mode=True)
            return structure_json
        except:
            # Return a minimal valid structure if everything fails
            return json.dumps({
                "directories": [{"name": "src", "path": "src", "description": "Source code"}],
                "files": [
                    {"name": "README.md", "path": "README.md", "description": "Documentation", "type": "documentation"},
                    {"name": "index.html", "path": "index.html", "description": "Main entry point", "type": "code"}
                ]
            })

def generate_frontend_code(optimized_prompt, project_structure):
    """Generate frontend code based on the optimized prompt and project structure"""
    system_message = """
    You are an expert frontend developer specializing in Streamlit applications. Your task
    is to generate clean, functional Streamlit code that meets the application requirements.
    """
    
    prompt = f"""
    Generate the frontend code for a Streamlit application based on the following requirements
    and project structure. The code should be clean, well-structured, and follow best practices.
    
    Application Requirements:
    {optimized_prompt}
    
    Project Structure:
    {project_structure}
    
    Please provide the complete Python code for the main Streamlit file and any supporting 
    frontend modules. Include appropriate UI elements, layout, and styling.
    """
    
    return generate_text(prompt, temperature=0.5, system_message=system_message)

def generate_backend_code(optimized_prompt, project_structure):
    """Generate backend code based on the optimized prompt and project structure"""
    system_message = """
    You are an expert backend developer specializing in Python applications. Your task
    is to generate clean, functional Python backend code that meets the application requirements.
    """
    
    prompt = f"""
    Generate the backend code for a Python application based on the following requirements
    and project structure. The code should be clean, well-structured, and follow best practices.
    
    Application Requirements:
    {optimized_prompt}
    
    Project Structure:
    {project_structure}
    
    Please provide the complete Python code for all backend modules, including data processing,
    API integration, and business logic. Ensure proper separation of concerns and modularization.
    """
    
    return generate_text(prompt, temperature=0.5, system_message=system_message)

def generate_file_content(file_path, optimized_prompt, project_structure):
    """Generate content for a specific file based on its path"""
    file_name = os.path.basename(file_path)
    file_ext = os.path.splitext(file_name)[1]
    
    # Parse project structure if it's a JSON string
    structure_info = {}
    try:
        if isinstance(project_structure, str):
            structure_data = json.loads(project_structure)
            
            # Find current file in the structure to get its description and purpose
            for file_info in structure_data.get("files", []):
                if file_path.endswith(file_info["path"]):
                    structure_info = file_info
                    break
    except:
        # If JSON parsing fails, continue without the additional context
        pass
    
    # Add specific context about the file's purpose if available
    file_description = structure_info.get("description", f"A {file_ext} file named {file_name}")
    file_type = structure_info.get("type", "code")
    
    system_message = f"""
    You are an expert developer specializing in creating {file_ext} files. Your task
    is to generate clean, functional code for a {file_name} file that meets the application requirements.
    
    This file is of type: {file_type}
    Description: {file_description}
    
    Follow best practices for this file type. Generate complete, working code with proper imports and dependencies.
    Do not include example code markers like ```python or ```javascript - just write the actual file content.
    """
    
    prompt = f"""
    Generate the content for a file named '{file_name}' based on the following application
    requirements and project structure. The code should be clean, well-structured, and follow best practices.
    
    File Path: {file_path}
    File Description: {file_description}
    File Type: {file_type}
    
    Application Requirements:
    {optimized_prompt}
    
    File Structure Context:
    {json.dumps(structure_info, indent=2) if structure_info else "No specific context available"}
    
    Please provide only the complete code for this specific file without any explanations or code block markers.
    """
    
    return generate_text(prompt, temperature=0.5, system_message=system_message)

def generate_readme(app_name, optimized_prompt, project_structure):
    """Generate a README.md file for the project"""
    system_message = """
    You are an expert technical writer. Your task is to create a comprehensive README.md file
    that clearly explains the application, its features, installation, usage, and structure.
    """
    
    prompt = f"""
    Create a comprehensive README.md file for a project named '{app_name}' based on the
    following requirements and structure. Include sections for description, features, installation,
    usage, project structure, and license.
    
    Application Requirements:
    {optimized_prompt}
    
    Project Structure:
    {project_structure}
    
    Please provide a complete, well-formatted markdown document.
    """
    
    return generate_text(prompt, temperature=0.6, system_message=system_message)

def extract_external_resources(content):
    """
    Extract external resources (e.g., URLs) from the generated content
    
    Args:
        content (str): The content to extract resources from
        
    Returns:
        list: A list of extracted URLs
    """
    urls = re.findall(r'(https?://\S+)', content)
    return urls

def extract_external_resources(project_structure):
    """
    Analyze project structure to identify external CSS and JS files
    
    Args:
        project_structure (str or dict): Project structure as JSON string or dict
    
    Returns:
        dict: Dictionary with 'css' and 'js' lists containing file paths
    """
    resources = {
        'css': [],
        'js': []
    }
    
    try:
        # Parse structure to dict if it's a string
        structure = json.loads(project_structure) if isinstance(project_structure, str) else project_structure
        
        # Look for CSS and JS files
        for file in structure.get("files", []):
            file_path = file.get("path", "")
            if file_path.endswith('.css'):
                resources['css'].append(file_path)
            elif file_path.endswith('.js'):
                resources['js'].append(file_path)
    except:
        # Return empty lists on error
        pass
    
    return resources
