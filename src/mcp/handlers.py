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

"""
Handlers for different MCP tools to process their results and integrate them into code generation.
"""
import re
import json
from src.config.frontend_resources import (
    get_component_sources,
    get_library_info,
    get_animation_resource,
    get_templates_by_type,
    UI_LIBRARIES,
    ANIMATION_RESOURCES,
    BEST_PRACTICES
)
from src.mcp.steps.process_web_search_results import process_web_search_results
from src.mcp.steps.process_documentation_results import process_documentation_results
from src.mcp.steps.process_frontend_component_results import process_frontend_component_results
from src.mcp.steps.process_frontend_templates_results import process_frontend_templates_results
from src.mcp.steps.process_animation_results import process_animation_results

def handle_tool_results(tool_name, tool_results, tool_args=None):
    """
    Process tool results based on the specific tool that was used.
    
    Args:
        tool_name (str): The name of the tool that was executed
        tool_results (str): The raw results from the tool
        tool_args (dict, optional): The arguments used for the tool call
        
    Returns:
        str: Processed and formatted tool results
    """
    if tool_name == "web_search":
        return process_web_search_results(tool_results)
    
    elif tool_name == "search_documentation":
        return process_documentation_results(tool_results)
    
    elif tool_name == "search_frontend_components":
        # If we have args, add curated resources
        if tool_args and 'component_type' in tool_args and 'framework' in tool_args:
            component_type = tool_args['component_type']
            framework = tool_args['framework']
            
            # Get curated sources for this component and framework
            sources = get_component_sources(component_type, framework)
            
            # Get framework info
            framework_info = get_library_info(framework)
            
            # Prepare additional information to append
            additional_info = ["\n### Curated Component Resources ###"]
            if framework_info:
                additional_info.append(f"\n{framework_info['name']} Documentation: {framework_info['docs']}")
                additional_info.append(f"CDN: {framework_info['cdn']}")
            
            if sources:
                additional_info.append("\nComponent-specific resources:")
                for i, src in enumerate(sources, 1):
                    additional_info.append(f"{i}. {src}")
            
            # Process tool results normally first
            processed = process_frontend_component_results(tool_results)
            
            # Append curated resources
            return processed + "\n" + "\n".join(additional_info)
        else:
            return process_frontend_component_results(tool_results)
    
    elif tool_name == "search_frontend_templates":
        if tool_args and 'template_type' in tool_args:
            return process_frontend_templates_results(tool_results, tool_args['template_type'])
        return process_frontend_templates_results(tool_results, "general")
    
    elif tool_name == "search_animation_resources":
        if tool_args and 'animation_type' in tool_args:
            return process_animation_results(tool_results, tool_args['animation_type'])
        return process_animation_results(tool_results, "general")
    
    else:
        # Generic handling for unknown tools
        return f"### Results from {tool_name} ###\n{tool_results}"