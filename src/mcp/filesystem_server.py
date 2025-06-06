"""
MCP Filesystem server management for automatic code validation and correction.
"""
import subprocess
import platform
import os
import signal

# Dictionary to track MCP processes per folder
_mcp_processes = {}

def start_mcp_filesystem_server(target_directory):
    """Start the MCP Filesystem server on the target folder."""
    if is_mcp_server_running(target_directory):
        return _mcp_processes[target_directory], False
    if platform.system() == 'Windows':
        cmd = ['npx.cmd', '-y', '@modelcontextprotocol/server-filesystem', target_directory]
    else:
        cmd = ['npx', '-y', '@modelcontextprotocol/server-filesystem', target_directory]
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    _mcp_processes[target_directory] = process
    return process, True

def stop_mcp_filesystem_server(target_directory):
    """Stop the MCP Filesystem server for the target folder."""
    process = _mcp_processes.get(target_directory)
    if not process:
        return False
    if platform.system() == 'Windows':
        process.terminate()
    else:
        os.kill(process.pid, signal.SIGTERM)
    process.wait(timeout=5)
    del _mcp_processes[target_directory]
    return True

def is_mcp_server_running(target_directory):
    """Check if the MCP server is running for the target folder."""
    process = _mcp_processes.get(target_directory)
    return process is not None and process.poll() is None