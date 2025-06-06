"""
Step: Backend code generation only, based on structure and context.
"""
def generate_backend_step(api_key, selected_model, reformulated_prompt, structure_lines, url_context, tool_results_text, url_reference, animation_instruction, use_mcp_tools, mcp_client, user_prompt, progress_callback=None, process_state=None):
    # Filtrer la structure pour ne garder que les fichiers/dossiers backend
    backend_keywords = ["backend", "api", "server", "app.py", "main.py", "manage.py", "routes.py", "controllers", "models", "services", "flask", "django", "express", "fastapi", ".py", ".go", ".rs", ".java", ".cs", "db/", "database", "sql", "mongodb"]
    backend_files = [f for f in structure_lines if any(k in f.lower() for k in backend_keywords)]
    if not backend_files:
        if progress_callback:
            progress_callback(4, "No backend files detected in structure.", 80)
        return None
    from .generate_code_step import generate_code_step
    return generate_code_step(
        api_key,
        selected_model,
        reformulated_prompt,
        backend_files,
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