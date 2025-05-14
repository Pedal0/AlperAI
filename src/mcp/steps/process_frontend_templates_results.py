# Copyright (C) 2025 Perey Alex
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>

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