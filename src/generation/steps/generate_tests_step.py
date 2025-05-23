"""
Step: Tests generation only, based on structure and context.
"""
def generate_tests_step(api_key, selected_model, reformulated_prompt, structure_lines, url_context, tool_results_text, url_reference, animation_instruction, use_mcp_tools, mcp_client, user_prompt, progress_callback=None, process_state=None):
    # Filtrer la structure pour ne garder que les fichiers/dossiers de tests
    test_keywords = ["test", "tests", "__tests__", "spec", "pytest", ".test.", ".spec.", "test_", "_test.", "tests/", "__tests__/", "jest"]
    test_files = [f for f in structure_lines if any(k in f.lower() for k in test_keywords)]
    if not test_files:
        if progress_callback:
            progress_callback(4, "No test files detected in structure.", 80)
        return None
    from .generate_code_step import generate_code_step
    return generate_code_step(
        api_key,
        selected_model,
        reformulated_prompt,
        test_files,
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
