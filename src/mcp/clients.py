"""
MCP client implementations for interacting with various MCP servers.
"""
import json
import asyncio
import streamlit as st
from contextlib import AsyncExitStack
from typing import Optional, Dict, Any, List

from src.mcp.tool_utils import get_default_tools
from src.config.frontend_resources import (
    get_component_sources,
    get_library_info,
    get_animation_resource,
    get_templates_by_type
)

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
        self.model = model
        self.messages = []
        self.tools = get_default_tools()
        self.tool_results_cache = {}  # Cache tool results to avoid duplicate calls
        
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
            st.info(f"Using cached results for {tool_name}")
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
                resource_info += f"\nRelevant resources for {component_type} in {framework}:\n"
                for src in sources:
                    resource_info += f"- {src}\n"
            
            if framework_info:
                resource_info += f"\nFramework information:\n"
                resource_info += f"- Documentation: {framework_info['docs']}\n"
                resource_info += f"- CDN: {framework_info['cdn']}\n"
                resource_info += f"- GitHub: {framework_info['github']}\n"
        
        elif tool_name == "search_frontend_templates" and "template_type" in tool_args:
            template_type = tool_args["template_type"]
            template_links = get_templates_by_type(template_type)
            
            if template_links:
                resource_info += f"\nRelevant {template_type} template resources:\n"
                for link in template_links:
                    resource_info += f"- {link}\n"
        
        elif tool_name == "search_animation_resources" and "animation_type" in tool_args:
            animation_type = tool_args["animation_type"]
            
            resource_info += f"\nRelevant animation resources for {animation_type}:\n"
            animation_resources = get_animation_resource(animation_type)
            if animation_resources:
                # get_animation_resource returns a single resource dict
                info = animation_resources
                resource_info += f"- {info['name']}: {info['url']} (CDN: {info.get('cdn', 'N/A')})\n"
        
        # Create a special prompt for the tool execution
        tool_prompt = f"""
        You are executing the tool '{tool_name}' with the following arguments:
        {json.dumps(tool_args, indent=2)}
        
        {resource_info}
        
        Please provide the requested information based on your knowledge and the resources provided.
        For a web_search tool, provide relevant search results.
        For a search_documentation tool, provide relevant documentation with code examples.
        For a search_frontend_components tool, describe and provide HTML/CSS/JS code snippets for relevant components.
        For a search_frontend_templates tool, describe templates and provide links to resources.
        For a search_animation_resources tool, provide animation code examples and usage instructions.
        
        Your response should be comprehensive and include practical, ready-to-use code where appropriate.
        Format code examples using markdown code blocks with the appropriate language tag.
        """
        
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
        
        # Create initial request with tools
        response = call_openrouter_api(
            self.api_key, 
            self.model, 
            self.messages, 
            temperature=0.4,
            tools=self.tools
        )
        
        final_text = []
        tool_calls_info = []
        
        if response and response.get("choices"):
            content = response["choices"][0]["message"]
            self.add_message("assistant", content.get("content", ""), )
            
            # Handle tool calls if any
            if content.get("tool_calls"):
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
                    self.model,
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
        
        result = {
            "text": "\n".join(final_text) if final_text else "Error processing query",
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
