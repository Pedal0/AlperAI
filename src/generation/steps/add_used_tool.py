"""
Fonction utilitaire : ajout ou mise à jour d'un outil utilisé dans le process_state.
"""
def add_used_tool(process_state, name, details=None):
    existing_tool = next((tool for tool in process_state['used_tools_details'] if tool['name'] == name), None)
    if existing_tool:
        if details:
            if isinstance(existing_tool['details'], list) and isinstance(details, list):
                existing_tool['details'] = list(set(existing_tool['details'] + details))
            else:
                existing_tool['details'] = details
    else:
        process_state['used_tools_details'].append({'name': name, 'details': details if details is not None else []})
