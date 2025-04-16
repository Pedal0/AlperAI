import re
"""
Traite les résultats de la recherche de documentation MCP.
"""
def process_documentation_results(doc_results):
    """
    Process documentation search results into code-relevant information.
    
    Args:
        doc_results (str): Raw documentation search results
        
    Returns:
        str: Processed documentation information useful for coding
    """
    # Extract code examples if present
    code_pattern = r'```(?:\w+)?\n(.*?)\n```'
    code_blocks = re.findall(code_pattern, doc_results, re.DOTALL)
    
    processed_info = ["### Documentation Information ###"]
    processed_info.append(doc_results)
    
    if code_blocks:
        processed_info.append("\n### Extracted Code Examples ###")
        for i, code in enumerate(code_blocks, 1):
            processed_info.append(f"Example {i}:\n{code}")
    
    return "\n".join(processed_info)
    pass



