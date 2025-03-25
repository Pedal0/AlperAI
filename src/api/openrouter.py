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
from src.api.prompts import SYSTEM_MESSAGES, PROMPTS, FALLBACKS

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
    system_message = SYSTEM_MESSAGES["optimize_prompt"]
    prompt = PROMPTS["optimize_prompt"].format(user_prompt=user_prompt)
    
    return generate_text(prompt, temperature=0.3, system_message=system_message)

def generate_project_structure(optimized_prompt):
    """Generate project structure based on the optimized prompt as JSON"""
    system_message = SYSTEM_MESSAGES["project_structure"]
    prompt = PROMPTS["project_structure"].format(optimized_prompt=optimized_prompt)
    
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
            return json.dumps(FALLBACKS["project_structure"])

def generate_element_dictionary(optimized_prompt):
    """
    Generate a dictionary of HTML elements, classes, and IDs to use consistently
    
    Args:
        optimized_prompt (str): The optimized prompt
        
    Returns:
        str: JSON string containing element dictionary
    """
    system_message = SYSTEM_MESSAGES["element_dictionary"]
    prompt = PROMPTS["element_dictionary"].format(optimized_prompt=optimized_prompt)
    
    try:
        elements_json = generate_text(prompt, temperature=0.3, system_message=system_message, json_mode=True)
        # Validate JSON
        json.loads(elements_json)
        return elements_json
    except:
        # Return a minimal dictionary if generation fails
        return json.dumps(FALLBACKS["element_dictionary"])

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

def generate_file_content(file_path, optimized_prompt, project_structure, element_dictionary=None):
    """Generate content for a specific file based on its path"""
    file_name = os.path.basename(file_path)
    file_ext = os.path.splitext(file_name)[1].lower()
    
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
    
    # Parse element dictionary if it's a JSON string
    element_dict_parsed = None
    try:
        if element_dictionary:
            element_dict_parsed = json.loads(element_dictionary) if isinstance(element_dictionary, str) else element_dictionary
    except:
        # Continue without element dictionary if parsing fails
        pass
        
    # Add specific context about the file's purpose if available
    file_description = structure_info.get("description", f"A {file_ext} file named {file_name}")
    file_type = structure_info.get("type", "code")
    
    # Special handling for HTML files
    if file_ext == '.html':
        # Extract external resource files from project structure
        external_resources = extract_external_resources(project_structure)
        css_files = ', '.join([f'"{css}"' for css in external_resources['css']]) if external_resources['css'] else 'None'
        js_files = ', '.join([f'"{js}"' for js in external_resources['js']]) if external_resources['js'] else 'None'
        
        system_message = SYSTEM_MESSAGES["html_generator"].format(
            file_name=file_name,
            file_description=file_description,
            css_files=css_files,
            js_files=js_files
        )
        
        prompt = PROMPTS["html_file"].format(
            file_name=file_name,
            optimized_prompt=optimized_prompt,
            file_path=file_path,
            file_description=file_description,
            css_files=css_files,
            js_files=js_files,
            element_dictionary=json.dumps(element_dict_parsed, indent=2) if element_dict_parsed else 'No element dictionary available, use semantic and consistent naming.'
        )
        
    # Special handling for CSS files
    elif file_ext == '.css':
        system_message = SYSTEM_MESSAGES["css_generator"].format(
            file_name=file_name,
            file_description=file_description
        )
        
        prompt = PROMPTS["css_file"].format(
            file_name=file_name,
            optimized_prompt=optimized_prompt,
            file_path=file_path,
            file_description=file_description,
            element_dictionary=json.dumps(element_dict_parsed, indent=2) if element_dict_parsed else 'No element dictionary available, use semantic and consistent naming.'
        )
        
    # Special handling for JS files
    elif file_ext == '.js':
        system_message = SYSTEM_MESSAGES["js_generator"].format(
            file_name=file_name,
            file_description=file_description
        )
        
        prompt = PROMPTS["js_file"].format(
            file_name=file_name,
            optimized_prompt=optimized_prompt,
            file_path=file_path,
            file_description=file_description,
            element_dictionary=json.dumps(element_dict_parsed, indent=2) if element_dict_parsed else 'No element dictionary available, use semantic and consistent naming.'
        )
        
    else:
        # Default handling for other file types
        system_message = SYSTEM_MESSAGES["default_file_generator"].format(
            file_ext=file_ext,
            file_name=file_name,
            file_type=file_type,
            file_description=file_description
        )
        
        prompt = PROMPTS["default_file"].format(
            file_name=file_name,
            file_path=file_path,
            file_description=file_description,
            file_type=file_type,
            optimized_prompt=optimized_prompt,
            structure_info=json.dumps(structure_info, indent=2) if structure_info else "No specific context available"
        )
    
    content = generate_text(prompt, temperature=0.5, system_message=system_message)
    return clean_generated_content(content)

def generate_readme(app_name, optimized_prompt, project_structure):
    """Generate a README.md file for the project"""
    system_message = SYSTEM_MESSAGES["readme_generator"]
    
    prompt = PROMPTS["readme"].format(
        app_name=app_name,
        optimized_prompt=optimized_prompt,
        project_structure=project_structure
    )
    
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
