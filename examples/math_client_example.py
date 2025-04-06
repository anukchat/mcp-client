#!/usr/bin/env python3
# mcpwire/examples/math_client_example.py

"""
Math Server Example for MCP Client

This example demonstrates:
1. Connecting to the math_server.py MCP server
2. Using the client to interact with the math server tools
"""

import asyncio
import logging
from mcpwire import (
    MCPClient,
    MCPError,
    MCPConnectionError
)

# Set up logging - helps trace what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def use_math_server():
    """Connect to the math server and use its tools."""
    logger.info("\n=== Math Server Example ===\n")
    
    try:
        # Create a client connected to the math server
        client = MCPClient(
            base_url="http://localhost:8000/sse",
            transport="sse",
            timeout=30
        )
        
        async with client as mcp:
            # List available math tools
            tools = await mcp.list_tools()
            logger.info(f"Math server provides {len(tools)} tools:")
            for tool in tools:
                logger.info(f"  - {tool.name}: {tool.description}")
            
            # Call the add tool
            add_result = await mcp.call_tool("add", {"a": 5, "b": 7})
            logger.info(f"5 + 7 = {add_result.content[0].text}")
            
            # Call the multiply tool
            multiply_result = await mcp.call_tool("multiply", {"a": 6, "b": 8})
            logger.info(f"6 × 8 = {multiply_result.content[0].text}")
            
            # Try different numbers
            for i in range(1, 5):
                for j in range(1, 5):
                    add_result = await mcp.call_tool("add", {"a": i, "b": j})
                    multiply_result = await mcp.call_tool("multiply", {"a": i, "b": j})
                    logger.info(f"{i} + {j} = {add_result.content[0].text}, {i} × {j} = {multiply_result.content[0].text}")
    
    except MCPConnectionError as e:
        logger.error(f"Connection error: {e}")
        logger.info("Make sure the math_server.py is running with 'python servers/math_server.py'")
    except MCPError as e:
        logger.error(f"MCP Client error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)

if __name__ == "__main__":
    # Run the async example
    asyncio.run(use_math_server()) 