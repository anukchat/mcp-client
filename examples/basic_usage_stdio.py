#!/usr/bin/env python3
# examples/basic_usage_stdio.py

"""
Basic Usage Example for MCP Client with stdio transport

This example demonstrates:
1. Loading client configuration from mcp.json
2. Using the client to interact with a stdio-based MCP server
3. Calling tools defined in the server

NOTE: This example uses async/await as the official MCP library is async-only.
"""

import asyncio
import logging
from mcpwire import MCPClient, MCPError

# Set up logging - helps trace what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Connect to a stdio MCP server and use its tools."""
    logger.info("\n=== Stdio MCP Server Example ===\n")
    try:
        # Load the client from the mcp.json config
        client = MCPClient.from_config(server_name="math_stdio")
        
        async with client as mcp:
            # List available tools
            tools = await mcp.list_tools()
            logger.info(f"Server provides {len(tools)} tools")
            for tool in tools:
                logger.info(f"Tool: {tool.name} - {tool.description}")
            
            # Call the hello tool
            try:
                result = await mcp.call_tool("hello", {"name": "World"})
                logger.info(f"Result of hello('World'): {result}")
            except Exception as e:
                logger.error(f"Error calling 'hello' tool: {e}")
            
            # Call the add tool
            try:
                result = await mcp.call_tool("add", {"a": 5, "b": 7})
                logger.info(f"Result of add(5, 7): {result}")
            except Exception as e:
                logger.error(f"Error calling 'add' tool: {e}")
                
            # Call the multiply tool
            try:
                result = await mcp.call_tool("multiply", {"a": 6, "b": 8})
                logger.info(f"Result of multiply(6, 8): {result}")
            except Exception as e:
                logger.error(f"Error calling 'multiply' tool: {e}")
    
    except MCPError as e:
        logger.error(f"MCP Client error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())