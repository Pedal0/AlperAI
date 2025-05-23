"""
Step: Génération de la documentation (README, docs, etc.) uniquement, selon la structure et le contexte.
"""
def generate_documentation_step(api_key, selected_model, reformulated_prompt, structure_lines, url_context, tool_results_text, url_reference, animation_instruction, use_mcp_tools, mcp_client, user_prompt, progress_callback=None, process_state=None):
    # Filtrer la structure pour ne garder que les fichiers de documentation
    doc_keywords = ["readme", "doc", "documentation", ".md", "guide", "manuel", "docs/"]
    doc_files = [f for f in structure_lines if any(k in f.lower() for k in doc_keywords)]
    if not doc_files:
        if progress_callback:
            progress_callback(4, "Aucun fichier de documentation détecté dans la structure.", 80)
        return None
    from .generate_code_step import generate_code_step
    return generate_code_step(
        api_key,
        selected_model,
        reformulated_prompt,
        doc_files,
        url_context,
        tool_results_text,
        url_reference,
        animation_instruction,
        use_mcp_tools,
        mcp_client,
        user_prompt,
        progress_callback=progress_callback,
        process_state=process_state
    )
