"""
Fonction utilitaire : exécution asynchrone d'une requête MCP.
"""
async def run_mcp_query(client, query, context=None):
    result = await client.process_query(query, context)
    return result
