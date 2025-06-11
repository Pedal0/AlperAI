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
MCP (Model Context Protocol) client implementations for interacting with AI tools.
Provides simplified clients that work with OpenRouter API without needing full MCP SDK.
"""

import json
import asyncio
from contextlib import AsyncExitStack
from typing import Optional, Dict, Any, List

from src.mcp.tool_utils import get_default_tools
from src.config.frontend_resources import (
    get_component_sources,
    get_library_info,
    get_animation_resource,
    get_templates_by_type
)
from src.utils.prompt_loader import get_agent_prompt
from src.utils.openrouter_model_utils import model_supports_tools, get_fallback_model_for_tools

class SimpleMCPClient:
    """
    A simplified MCP client that doesn't require the full MCP SDK.
    Uses OpenRouter directly with predefined tools.
    """
    
    def __init__(self, api_key, model):
        """
        Initialize the simple MCP client.
        
        Args:
            api_key (str): OpenRouter API key
            model (str): Model to use for generation
        """
        self.api_key = api_key
        self.original_model = model
        self.messages = []
        self.tool_results_cache = {}  # Cache tool results to avoid duplicate calls
        
        # Check if the model supports tools
        self.supports_tools = model_supports_tools(model)
        
        if self.supports_tools:
            self.model = model
            self.tools = get_default_tools()
            print(f"✅ Model {model} supports tools - MCP tools enabled")
        else:
            # Use a fallback model for tool calls, but keep original for regular generation
            self.tool_model = get_fallback_model_for_tools(model)
            self.model = model  # Keep original for non-tool calls
            self.tools = get_default_tools()
            print(f"⚠️ Model {model} doesn't support tools - using {self.tool_model} for MCP operations")
        
    def add_message(self, role, content, tool_call_id=None, name=None):
        """
        Add a message to the conversation history.
        
        Args:
            role (str): Message role ('user', 'assistant', 'tool')
            content (str): Message content
            tool_call_id (str, optional): Tool call ID for tool responses
            name (str, optional): Tool name for tool responses
        """
        message = {"role": role, "content": content}
        if role == "tool" and tool_call_id and name:
            message["tool_call_id"] = tool_call_id
            message["name"] = name
        self.messages.append(message)
    
    async def execute_tool(self, tool_name, tool_args):
        """
        Execute a tool call and return the result.
        
        Args:
            tool_name (str): The name of the tool to execute
            tool_args (dict): The arguments for the tool
            
        Returns:
            str: The result of the tool execution
        """
        from src.api.openrouter_api import call_openrouter_api
        
        # Check cache first to avoid duplicate calls
        cache_key = f"{tool_name}:{json.dumps(tool_args, sort_keys=True)}"
        if cache_key in self.tool_results_cache:
            print(f"Using cached results for {tool_name}")
            return self.tool_results_cache[cache_key]
        
        # Prepare resource information based on tool type
        resource_info = ""
        if tool_name == "search_frontend_components" and "component_type" in tool_args and "framework" in tool_args:
            component_type = tool_args["component_type"]
            framework = tool_args["framework"]
            
            # Get curated resources
            sources = get_component_sources(component_type, framework)
            framework_info = get_library_info(framework)
            
            if sources:
                resource_info += f"\\nRelevant resources for {component_type} in {framework}:\\n"
                for src in sources:
                    resource_info += f"- {src}\\n"
            
            if framework_info:
                resource_info += f"\\nFramework information:\\n"
                resource_info += f"- Documentation: {framework_info['docs']}\\n"
                resource_info += f"- CDN: {framework_info['cdn']}\\n"
                resource_info += f"- GitHub: {framework_info['github']}\\n"
        
        elif tool_name == "search_frontend_templates" and "template_type" in tool_args:
            template_type = tool_args["template_type"]
            template_links = get_templates_by_type(template_type)
            
            if template_links:
                resource_info += f"\\nRelevant {template_type} template resources:\\n"
                for link in template_links:
                    resource_info += f"- {link}\\n"
        
        elif tool_name == "search_animation_resources" and "animation_type" in tool_args:
            animation_type = tool_args["animation_type"]
            
            resource_info += f"\\nRelevant animation resources for {animation_type}:\\n"
            animation_resources = get_animation_resource(animation_type)
            if animation_resources:
                # get_animation_resource returns a single resource dict
                info = animation_resources
                resource_info += f"- {info['name']}: {info['url']} (CDN: {info.get('cdn', 'N/A')})\\n"
        
        # Create tool execution prompt using prompt loader
        tool_prompt = get_agent_prompt(
            'tool_execution_agent',
            'tool_execution_prompt',
            tool_name=tool_name,
            tool_args=json.dumps(tool_args, indent=2),
            resource_info=resource_info
        )
        
        # Make a separate API call to simulate the tool
        tool_messages = [{"role": "user", "content": tool_prompt}]
        response = call_openrouter_api(self.api_key, self.model, tool_messages, temperature=0.3)
        
        if response and response.get("choices"):
            tool_result = response["choices"][0]["message"]["content"]
            
            # Cache the result
            self.tool_results_cache[cache_key] = tool_result
            
            return tool_result
        
        return "Error: Unable to execute tool"
    
    async def process_query(self, query, additional_context=None):
        """
        Process a user query using tools.
        
        Args:
            query (str): User query to process
            additional_context (str, optional): Additional context for the query
            
        Returns:
            Dict: Processing results including final text and tool calls
        """
        from src.api.openrouter_api import call_openrouter_api
        
        # Add context if provided
        if additional_context:
            context_msg = {
                "role": "system", 
                "content": additional_context
            }
            if not self.messages or self.messages[0].get("role") != "system":
                self.messages.insert(0, context_msg)
        
        # Add user query
        self.add_message("user", query)
        
        # Determine which model to use and whether to include tools
        model_to_use = self.tool_model if hasattr(self, 'tool_model') and not self.supports_tools else self.model
        tools_to_use = self.tools if self.supports_tools else None
        
        # Create initial request with or without tools based on model support
        response = call_openrouter_api(
            self.api_key, 
            model_to_use, 
            self.messages, 
            temperature=0.4,
            tools=tools_to_use
        )
        
        final_text = []
        tool_calls_info = []
        
        if response and response.get("choices"):
            content = response["choices"][0]["message"]
            self.add_message("assistant", content.get("content", ""))
            
            # Handle tool calls if any and if model supports tools
            if self.supports_tools and content.get("tool_calls"):
                for tool_call in content["tool_calls"]:
                    function_info = tool_call.get("function", {})
                    tool_name = function_info.get("name")
                    tool_args_str = function_info.get("arguments", "{}")
                    
                    try:
                        tool_args = json.loads(tool_args_str) if tool_args_str else {}
                    except json.JSONDecodeError:
                        tool_args = {}
                    
                    tool_call_info = {
                        "tool": tool_name,
                        "args": tool_args
                    }
                    tool_calls_info.append(tool_call_info)
                    
                    # Execute the tool
                    result = await self.execute_tool(tool_name, tool_args)
                    
                    final_text.append(f"[Tool Call: {tool_name} with args {tool_args}]")
                    
                    # Add tool response to messages
                    self.add_message(
                        "tool", 
                        result,
                        tool_call_id=tool_call.get("id"),
                        name=tool_name
                    )
                
                # Final response after tool execution
                response = call_openrouter_api(
                    self.api_key,
                    model_to_use,
                    self.messages,
                    temperature=0.4
                )
                
                if response and response.get("choices"):
                    assistant_response = response["choices"][0]["message"]["content"]
                    final_text.append(assistant_response)
                    self.add_message("assistant", assistant_response)
            else:
                # No tool calls, just return the response
                final_text.append(content.get("content", ""))
                
        # If model doesn't support tools but query suggests tool usage, simulate basic search
        elif not self.supports_tools and any(keyword in query.lower() for keyword in ["search", "find", "documentation", "component", "template"]):
            # Simulate a basic search response without actual tools
            simulated_response = f"Based on your query about: {query}\\n\\nHere are some general recommendations and resources:\\n"
            
            if "search" in query.lower() or "find" in query.lower():
                simulated_response += "- For web development, consider using modern frameworks like React, Vue, or vanilla JavaScript\\n"
                simulated_response += "- Popular CSS frameworks include Bootstrap, Tailwind CSS, and Bulma\\n"
                simulated_response += "- For backend development, Flask, Django (Python), Express (Node.js) are good choices\\n"
            
            if "documentation" in query.lower():
                simulated_response += "- MDN Web Docs (developer.mozilla.org) for web standards\\n"
                simulated_response += "- Official framework documentation is always the best source\\n"
                simulated_response += "- GitHub repositories often have excellent README files\\n"
            
            if "component" in query.lower():
                simulated_response += "- Component libraries: Material-UI, Ant Design, Chakra UI\\n"
                simulated_response += "- CSS-only components: Pure CSS, Semantic UI\\n"
                simulated_response += "- Icon libraries: Font Awesome, Heroicons, Feather\\n"
            
            final_text.append(simulated_response)
            self.add_message("assistant", simulated_response)
        
        result = {
            "text": "\\n".join(final_text) if final_text else "Error processing query",
            "tool_calls": tool_calls_info
        }
        
        return result

# Advanced MCP client that could use the actual MCP SDK
# Commented out as it requires additional dependencies that would need to be installed
"""
class FullMCPClient:
    def __init__(self, api_key, model):
        self.api_key = api_key
        self.model = model
        self.session = None
        self.exit_stack = AsyncExitStack()
        self.messages = []
        
    async def connect_to_server(self, server_config):
        # This would require the MCP SDK
        # from mcp import ClientSession, StdioServerParameters
        # from mcp.client.stdio import stdio_client
        
        # Implementation would go here
        pass
        
    async def process_query(self, query):
        # Implementation would go here
        pass
"""
