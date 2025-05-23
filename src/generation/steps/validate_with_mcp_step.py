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
            "You are an expert full-stack code reviewer and auto-fixer. "
            "1. Check all files for syntax errors, missing or incorrect imports, and unused dependencies in package files (like package.json, requirements.txt, etc). "
            "2. For each API call or frontend-backend interaction, verify that the backend route exists and receives the correct parameters. "
            "3. If you find any mismatch (e.g., frontend sends data that backend does not expect, or vice versa), fix both sides so they match. "
            "4. Ensure all dependencies are declared and used correctly. "
            "5. Fix any small issues (naming, typos, missing files, etc). "
            "6. Summarize all corrections you made. If everything is correct, just reply 'All good'. "
            "You are allowed to directly edit the files to fix any detected issues."
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
