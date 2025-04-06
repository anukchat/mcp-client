#!/usr/bin/env python3
# mcpwire/examples/basic_usage.py

"""
Basic Usage Example for MCP Client (v0.4.0+ with official MCP library)

This example demonstrates:
1. Creating a client directly or loading from configuration file
2. Using the client to interact with an MCP server
3. Using the MultiServerMCPClient to interact with multiple MCP servers
4. Basic error handling

NOTE: This example uses async/await as the official MCP library is async-only.
"""

import os
import asyncio
import logging
from typing import Dict, Any, Optional

from mcpwire import (
    MCPClient,
    MultiServerMCPClient,
    StdioConnection,
    SSEConnection,
    MCPError,
    MCPAPIError,
    MCPConnectionError,
    MCPTimeoutError,
    MCPDataError
)

# Set up logging - helps trace what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Basic Client Usage Examples ---

async def example_direct_initialization():
    """Example: Creating a client directly."""
    logger.info("\n=== Example: Direct Initialization ===\n")
    try:
        # Create a client with direct initialization
        # Note: The official MCP library supports "sse" transport, not "http"
        client = MCPClient(
            base_url="http://localhost:8000/sse",
            transport="sse",
            timeout=30,
            api_key=None  # Optional API key
        )
        
        async with client as mcp:
            # List available tools
            tools = await mcp.list_tools()
            logger.info(f"Server provides {len(tools)} tools")
            for tool in tools:
                logger.info(f"Tool: {tool.name} - {tool.description}")
            
            # Call the add tool from math_server.py
            try:
                result = await mcp.call_tool("add", {"a": 5, "b": 7})
                logger.info(f"Result of add(5, 7): {result}")
            except Exception as e:
                logger.error(f"Error calling 'add' tool: {e}")
            
            # Call the multiply tool from math_server.py
            try:
                result = await mcp.call_tool("multiply", {"a": 6, "b": 8})
                logger.info(f"Result of multiply(6, 8): {result}")
            except Exception as e:
                logger.error(f"Error calling 'multiply' tool: {e}")
    
    except MCPConnectionError as e:
        logger.error(f"Connection error: {e}")
        logger.info("Make sure an MCP server is running at http://localhost:8000")
    except MCPError as e:
        logger.error(f"MCP Client error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)

async def example_config_file_initialization():
    """Example: Loading client config from mcp.json."""
    logger.info("\n=== Example: Config File Initialization ===\n")
    try:
        # Load configuration from mcp.json file
        # If server_name is not specified, uses the "default_server" from the config
        # or attempts to use a server named "default"
        client = MCPClient.from_config(server_name="local")
        
        async with client as mcp:
            # Get server metadata
            metadata = await mcp.get_server_metadata()
            logger.info(f"Connected to server from config: {metadata.name} v{metadata.version}")
            
            # List available tools
            tools = await mcp.list_tools()
            logger.info(f"Server provides {len(tools)} tools")
            
    except FileNotFoundError:
        logger.error("mcp.json file not found in standard locations.")
        logger.info("Create an mcp.json file in the current directory or ~/.mcp.json")
    except KeyError as e:
        logger.error(f"Server configuration not found: {e}")
    except MCPError as e:
        logger.error(f"MCP Client error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)

async def example_multi_server_client():
    """Example: Using MultiServerMCPClient to connect to multiple servers."""
    logger.info("\n=== Example: Multi-Server Client ===\n")
    try:
        # Define connections to multiple servers
        connections = {
            "math": {
                "transport": "stdio",
                "command": "python",
                "args": ["-m", "mcp.server.cli"],
            },
            "web": {
                "transport": "sse",
                "url": "http://localhost:8000/sse",
            }
        }
        
        async with MultiServerMCPClient(connections) as multi_client:
            # Get all tools from all servers
            all_tools = multi_client.get_tools()
            logger.info(f"Total tools from all servers: {len(all_tools)}")
            
            # Add a new server after initialization
            await multi_client.connect_to_server(
                "local",
                transport="stdio",
                command="python",
                args=["-m", "mcp.server.cli"],
            )
            
            # Get tools again to see the updated count
            all_tools = multi_client.get_tools()
            logger.info(f"Updated total tools from all servers: {len(all_tools)}")
            
            # Call a specific tool on a specific server
            try:
                # Get a prompt from a specific server
                messages = await multi_client.get_prompt(
                    server_name="math", 
                    prompt_name="calculate", 
                    arguments={"expression": "2+2"}
                )
                for msg in messages:
                    logger.info(f"Message: {msg.content}")
            except Exception as e:
                logger.error(f"Error getting prompt: {e}")
            
    except Exception as e:
        logger.error(f"MultiServerMCPClient error: {e}", exc_info=True)

async def example_error_handling():
    """Example: Demonstrating error handling."""
    logger.info("\n=== Example: Error Handling ===\n")
    
    # Try to connect to a non-existent server
    try:
        client = MCPClient(
            base_url="http://non-existent-server:8000",
            transport="sse",
            timeout=5  # Short timeout for faster error
        )
        
        async with client as mcp:
            await mcp.get_server_metadata()
            
    except MCPConnectionError as e:
        logger.info(f"✓ Successfully caught connection error: {e}")
    except MCPTimeoutError as e:
        logger.info(f"✓ Successfully caught timeout error: {e}")
    except MCPAPIError as e:
        logger.info(f"✓ Successfully caught API error (Status {e.status_code}): {e}")
    except MCPError as e:
        logger.info(f"✓ Successfully caught general MCP error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error type: {e}", exc_info=True)
        
    # Try loading from non-existent config file
    try:
        MCPClient.from_config(config_path="/non/existent/path/to/mcp.json")
    except FileNotFoundError as e:
        logger.info(f"✓ Successfully caught config file not found error: {e}")

async def run_all_examples():
    """Run all examples in sequence."""
    try:
        await example_direct_initialization()
        # await example_config_file_initialization()  
        # await example_multi_server_client()
        # await example_error_handling()
    except Exception as e:
        logger.error(f"Error running examples: {e}", exc_info=True)

if __name__ == "__main__":
    # Run the async examples
    asyncio.run(run_all_examples())

