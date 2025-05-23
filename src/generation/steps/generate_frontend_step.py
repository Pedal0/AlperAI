"""
Step: Frontend code generation only, based on structure and context.
"""
def generate_frontend_step(api_key, selected_model, reformulated_prompt, structure_lines, url_context, tool_results_text, url_reference, animation_instruction, use_mcp_tools, mcp_client, user_prompt, progress_callback=None, process_state=None):
    # Filtrer la structure pour ne garder que les fichiers/dossiers frontend
    frontend_keywords = ["frontend", "src/", "public/", "static/", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", "components", "assets", "ui/"]
    frontend_files = [f for f in structure_lines if any(k in f.lower() for k in frontend_keywords)]
    if not frontend_files:
        if progress_callback:
            progress_callback(4, "No frontend files detected in structure.", 80)
        return None
    
    # Enrichir le prompt avec des instructions spécifiques au frontend
    enhanced_prompt = f"""
{reformulated_prompt}

ADDITIONAL FRONTEND REQUIREMENTS:
- Create a modern, responsive design using CSS Grid/Flexbox
- Use a clean color palette (consider using CSS variables for consistency)
- Add subtle animations and hover effects for better UX
- Ensure mobile-first responsive design
- Use semantic HTML elements
- Add proper accessibility attributes (alt texts, ARIA labels)
- Include a professional-looking header/navigation if applicable
- Style forms with proper validation feedback
- Use modern CSS features (border-radius, box-shadow, gradients where appropriate)
"""
    
    # Call code generation but limiting structure and with enhanced prompt
    from .generate_code_step import generate_code_step
    return generate_code_step(
        api_key,
        selected_model,
        enhanced_prompt,  # Utilise le prompt enrichi
        frontend_files,
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
