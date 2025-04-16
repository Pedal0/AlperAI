from src.config.frontend_resources import get_templates_by_type

"""
Traite les résultats des templates frontend MCP.
"""
def process_frontend_templates_results(template_results, template_type):
    """
    Process frontend template search results and add curated resources.
    
    Args:
        template_results (str): Raw template search results
        template_type (str): Type of template requested
        
    Returns:
        str: Processed template information with links to curated resources
    """
    processed_info = ["### Template Resources ###"]
    processed_info.append(template_results)
    
    # Add curated resources
    template_links = get_templates_by_type(template_type)
    if template_links:
        processed_info.append("\n### Curated Template Resources ###")
        processed_info.append(f"Template type: {template_type}")
        processed_info.append("Recommended resources:")
        for i, link in enumerate(template_links, 1):
            processed_info.append(f"{i}. {link}")
    
    return "\n".join(processed_info)

    pass