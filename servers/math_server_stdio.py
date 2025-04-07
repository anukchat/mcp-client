#!/usr/bin/env python3
# servers/math_server_stdio.py
"""
Math Server Example using stdio transport

This demonstrates a simple MCP server using the FastMCP class 
with stdio transport for command-line usage.

Run this server indirectly through the MCPClient:
    client = MCPClient.from_config(server_name="math_stdio")
"""
from mcp.server import FastMCP

# Create an MCP server with a name
mcp = FastMCP("MathStdio")

# Track calculation history
calculation_history = []

@mcp.tool()
def hello(name: str) -> str:
    """Say hello to someone"""
    result = f"Hello, {name}!"
    calculation_history.append(f"Greeted {name}")
    return result

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    result = a + b
    calculation_history.append(f"{a} + {b} = {result}")
    return result

@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers"""
    result = a * b
    calculation_history.append(f"{a} * {b} = {result}")
    return result

@mcp.tool()
def get_history() -> str:
    """Get the history of calculations"""
    if not calculation_history:
        return "No calculations performed yet."
    return "\n".join(calculation_history)

# The default transport is 'stdio', so you could omit the parameter
if __name__ == "__main__":
    mcp.run(transport="stdio")