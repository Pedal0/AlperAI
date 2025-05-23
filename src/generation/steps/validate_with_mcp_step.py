"""
Automatic code validation and self-correction using the MCP server.
"""
import time
import logging
from src.mcp.filesystem_server import start_mcp_filesystem_server, stop_mcp_filesystem_server, is_mcp_server_running
from src.mcp.clients import SimpleMCPClient
from src.generation.steps.run_mcp_query import run_mcp_query

def validate_with_mcp_step(target_directory, api_key=None, model=None, user_prompt=None, progress_callback=None):
    """Start the MCP server, validate and auto-correct generated code, then stop the server."""
    try:
        if progress_callback:
            progress_callback(9, "🔍 Automatic code validation and correction via MCP...", 100)
        process, started = start_mcp_filesystem_server(target_directory)
        if not is_mcp_server_running(target_directory):
            logging.warning("Could not start MCP server for validation.")
            return False, "MCP server not started"
        # --- Automatic validation and correction logic ---
        # 1. Create an MCP client
        if not api_key or not model:
            return False, "API key and model required for MCP validation."
        mcp_client = SimpleMCPClient(api_key, model)
        # 2. Ask the AI to check for errors and fix them
        import asyncio
        validation_prompt = (
            "You are an expert code reviewer. "
            "Check all files in this project for errors, bad imports, missing files, or incorrect calls. "
            "If you find any issues, fix them directly in the files. "
            "Summarize the corrections you made. "
            "If everything is correct, just reply 'All good'."
        )
        if user_prompt:
            validation_prompt += f"\nUser request: {user_prompt}"
        query = f"[MCP-AUTO-VALIDATE]\n{validation_prompt}"
        result = asyncio.run(run_mcp_query(mcp_client, query, context=target_directory))
        summary = result.get("text", "No response from MCP.")
        if progress_callback:
            progress_callback(10, f"✅ MCP validation/correction done: {summary}", 100)
        return True, summary
    except Exception as e:
        logging.error(f"Error during MCP validation: {e}")
        return False, str(e)
    finally:
        stop_mcp_filesystem_server(target_directory)
