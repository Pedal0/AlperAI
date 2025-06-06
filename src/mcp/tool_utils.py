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
Utility functions for working with MCP tools and converting them to OpenRouter compatible format.
"""
import json

def convert_tool_format(tool):
    """
    Convert an MCP tool definition to OpenAI/OpenRouter compatible format.
    
    Args:
        tool: The MCP tool definition object
        
    Returns:
        dict: OpenAI-compatible tool definition
    """
    converted_tool = {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": {
                "type": "object",
                "properties": tool.inputSchema["properties"],
                "required": tool.inputSchema["required"]
            }
        }
    }
    return converted_tool

def get_web_search_tool():
    """
    Define a web search tool for OpenRouter.
    
    Returns:
        dict: Web search tool definition
    """
    return {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for information on a specific topic or query",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up online"
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Number of search results to return (default: 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    }

def get_documentation_search_tool():
    """
    Define a documentation search tool for OpenRouter.
    
    Returns:
        dict: Documentation search tool definition
    """
    return {
        "type": "function",
        "function": {
            "name": "search_documentation",
            "description": "Search for documentation on programming languages, libraries, or frameworks",
            "parameters": {
                "type": "object",
                "properties": {
                    "technology": {
                        "type": "string",
                        "description": "The technology to search documentation for (e.g., 'React', 'Flask', 'Python')"
                    },
                    "topic": {
                        "type": "string",
                        "description": "Specific topic or function to look up in the documentation"
                    }
                },
                "required": ["technology", "topic"]
            }
        }
    }

def get_frontend_component_tool():
    """
    Define a frontend component search tool for OpenRouter.
    
    Returns:
        dict: Frontend component search tool definition
    """
    return {
        "type": "function",
        "function": {
            "name": "search_frontend_components",
            "description": "Search for frontend UI components, templates, or design patterns",
            "parameters": {
                "type": "object",
                "properties": {
                    "framework": {
                        "type": "string",
                        "description": "The frontend framework (e.g., 'React', 'Vue', 'Bootstrap', 'Tailwind')"
                    },
                    "component_type": {
                        "type": "string",
                        "description": "The type of component to search for (e.g., 'Navbar', 'Card', 'Form', 'Button')"
                    },
                    "style": {
                        "type": "string",
                        "description": "Optional style or theme preference",
                        "default": "modern"
                    }
                },
                "required": ["framework", "component_type"]
            }
        }
    }

def get_frontend_templates_tool():
    """
    Define a frontend templates search tool for OpenRouter.
    
    Returns:
        dict: Frontend templates search tool definition
    """
    return {
        "type": "function",
        "function": {
            "name": "search_frontend_templates",
            "description": "Search for complete frontend templates and design inspiration",
            "parameters": {
                "type": "object",
                "properties": {
                    "template_type": {
                        "type": "string",
                        "description": "The type of template (e.g., 'portfolio', 'landing', 'dashboard', 'ecommerce')"
                    },
                    "style_preference": {
                        "type": "string",
                        "description": "Optional style preference (e.g., 'minimal', 'modern', 'corporate')",
                        "default": "modern"
                    }
                },
                "required": ["template_type"]
            }
        }
    }

def get_animation_resources_tool():
    """
    Define an animation resources search tool for OpenRouter.
    
    Returns:
        dict: Animation resources search tool definition
    """
    return {
        "type": "function",
        "function": {
            "name": "search_animation_resources",
            "description": "Search for CSS animations and transition effects",
            "parameters": {
                "type": "object",
                "properties": {
                    "animation_type": {
                        "type": "string",
                        "description": "The type of animation (e.g., 'hover', 'scroll', 'transition', 'loading')"
                    },
                    "element": {
                        "type": "string",
                        "description": "The HTML element to animate (e.g., 'button', 'card', 'navbar', 'image')"
                    }
                },
                "required": ["animation_type"]
            }
        }
    }

def get_default_tools():
    """
    Get the default set of tools for code generation.
    
    Returns:
        list: List of tool definitions
    """
    return [
        get_web_search_tool(),
        get_documentation_search_tool(),
        get_frontend_component_tool(),
        get_frontend_templates_tool(),
        get_animation_resources_tool()
    ]