# MCP Python Client

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) [![PyPI version](https://badge.fury.io/py/mcpwire.svg)](https://badge.fury.io/py/mcpwire) [![Python Version](https://img.shields.io/pypi/pyversions/mcpwire.svg)](https://pypi.org/project/mcpwire/) [![Tests](https://github.com/anukchat/mcpwire/actions/workflows/test.yml/badge.svg)](https://github.com/anukchat/mcpwire/actions/workflows/test.yml)
[![Publish](https://github.com/anukchat/mcpwire/actions/workflows/publish.yml/badge.svg)](https://github.com/anukchat/mcpwire/actions/workflows/publish.yml)
[![Coverage Status](https://codecov.io/gh/anukchat/mcpwire/branch/main/graph/badge.svg)](https://codecov.io/gh/anukchat/mcpwire)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PyPI Downloads](https://img.shields.io/pypi/dm/mcpwire.svg)](https://pypi.org/project/mcpwire/)
[![Documentation Status](https://readthedocs.org/projects/mcpwire/badge/?version=latest)](https://mcpwire.readthedocs.io/en/latest/?badge=latest)

A Python client library for interacting with servers implementing the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/). This library simplifies communication with AI models and agents that expose an MCP interface.

**Version:** 0.4.1

## Features

* **Official MCP Implementation:** Starting with version 0.4.1, this library uses the official MCP library and langchain-mcp-adapters.
* **Backward Compatibility:** Maintains the same API structure as before, but now uses async methods.
* **Send Prompts:** Easily send conversation history to get responses from MCP servers.
* **Tool Support:** Access tools provided by MCP servers and convert them to LangChain tools.
* **MultiServerMCPClient:** Connect to multiple MCP servers and access their tools.
* **Configuration File:** Load server connection details (`base_url`, `api_key`, `timeout`) from an `mcp.json` file.
* **Robust Error Handling:** Differentiates between connection errors, timeouts, API errors, and data validation errors.
* **Authentication:** Supports API Key authentication via the `Authorization: Bearer` header.
* **Context Manager:** Supports use as an async context manager.

## Installation

```bash
# From PyPI (once published)
pip install mcpwire

# Development dependencies
pip install mcpwire[dev]

# Or directly from GitHub
pip install git+https://github.com/anukchat/mcpwire.git

# Or for development
git clone https://github.com/anukchat/mcpwire.git
cd mcpwire
pip install -e .
```

## Configuration (mcp.json)

The client can be configured using an mcp.json file. This allows you to define multiple server environments and easily switch between them using `MCPClient.from_config()`.

The client searches for mcp.json in the following order:
1. An explicit path provided to `MCPClient.from_config(config_path=...)`.
2. mcp.json in the current working directory.
3. `.mcp.json` in your home directory (`~/.mcp.json`).
4. `.config/mcp/mcp.json` in your home directory (`~/.config/mcp/mcp.json`).

Example mcp.json:
```json
{
  "default_server": "local",
  "servers": {
    "local": {
      "base_url": "http://localhost:8000",
      "api_key": null,
      "timeout": 60,
      "transport": "sse",
      "description": "Local development server (e.g., fast-agent)",
      "resources": {
        "enabled": true,
        "auto_subscribe": ["file:///workspace/shared/*"],
        "default_templates": [
          {
            "uri_template": "file:///workspace/{path}",
            "name": "Workspace File",
            "description": "Access files in the workspace directory"
          },
          {
            "uri_template": "db://customers/{customer_id}",
            "name": "Customer Record",
            "description": "Access customer data from the database",
            "mime_type": "application/json"
          }
        ]
      }
    },
    "stdio_server": {
      "transport": "stdio",
      "command": "python",
      "args": ["-m", "mcp.server.cli"],
      "timeout": 60,
      "description": "Local stdio server",
      "resources": {
        "enabled": false
      }
    },
    "remote_dev": {
      "base_url": "https://dev-mcp.example.com",
      "api_key": "dev-secret-key-abc",
      "timeout": 90,
      "transport": "sse",
      "description": "Remote development/testing server",
      "resources": {
        "enabled": true,
        "auto_subscribe": ["screen://capture/*"],
        "default_templates": [
          {
            "uri_template": "screen://capture/{timestamp}",
            "name": "Screen Capture",
            "description": "Access screenshots captured during browsing",
            "mime_type": "image/png"
          }
        ]
      }
    },
    "production": {
      "base_url": "https://mcp.example.com",
      "api_key": "env:MCP_PROD_API_KEY",
      "timeout": 120,
      "transport": "sse",
      "description": "Production MCP server"
    }
  }
}
```

- `default_server`: (Optional) The key of the server to use if server_name is omitted in from_config().
- `servers`: Dictionary of named server configurations.
  - `base_url`: (Required for http/sse) Server URL.
  - `api_key`: (Optional) API key string, null, or "env:YOUR_ENV_VAR".
  - `timeout`: (Optional) Request timeout in seconds (defaults to 60).
  - `transport`: (Required) The transport protocol to use ("sse" or "stdio").
  - `command`: (Required for stdio) The command to execute.
  - `args`: (Required for stdio) Arguments for the command.
  - `description`: (Optional) Description.
  - `resources`: (Optional) Configuration for MCP resources.
    - `enabled`: (Required) Whether resources are enabled for this server.
    - `auto_subscribe`: (Optional) List of resource URI patterns to automatically subscribe to.
    - `default_templates`: (Optional) List of resource templates that define dynamic resources.
      - `uri_template`: (Required) URI template following RFC 6570.
      - `name`: (Required) Human-readable name for this resource type.
      - `description`: (Optional) Description of this resource type.
      - `mime_type`: (Optional) MIME type for all matching resources.

## Quickstart (Async)

```python
import asyncio
import logging
from mcpwire import (
    MCPClient,
    MultiServerMCPClient,
    StdioConnection,
    SSEConnection,
    MCPAPIError,
    MCPConnectionError,
    MCPDataError
)

logging.basicConfig(level=logging.INFO)

async def main():
    # --- Option 1: Initialize directly ---
    # Note: The official MCP library supports "sse" transport, not "http"
    client = MCPClient(base_url="http://localhost:8000", transport="sse")
    
    try:
        # Initialize and use the client
        async with client as mcp:
            # Get server metadata
            metadata = await mcp.get_server_metadata()
            logging.info(f"Connected to MCP server: {metadata.name} v{metadata.version}")
            
            # List available tools
            tools = await mcp.list_tools()
            for tool in tools:
                logging.info(f"Available tool: {tool.name}")
            
            # Get a prompt
            prompt_messages = await mcp.get_prompt("hello_world", {})
            for msg in prompt_messages:
                logging.info(f"[{msg.type}] {msg.content}")
                
            # Call a tool
            tool_result = await mcp.call_tool("search", {"query": "MCP protocol"})
            logging.info(f"Tool result: {tool_result}")
            
            # Working with resources
            # List available resources
            resources_result = await mcp.list_resources()
            logging.info(f"Found {len(resources_result.resources)} resources and {len(resources_result.templates)} templates")
            
            # Display available resources
            for resource in resources_result.resources:
                logging.info(f"Resource: {resource.name} (URI: {resource.uri})")
            
            # Read a resource content (if any resources available)
            if resources_result.resources:
                resource_uri = resources_result.resources[0].uri
                content = await mcp.read_resource(resource_uri)
                logging.info(f"Read resource content with URI: {resource_uri}")
                
                # Subscribe to resource updates
                await mcp.subscribe_to_resource(resource_uri)
                logging.info(f"Subscribed to resource: {resource_uri}")
                
                # Later, unsubscribe when no longer needed
                await mcp.unsubscribe_from_resource(resource_uri)
                logging.info(f"Unsubscribed from resource: {resource_uri}")
            
    except (MCPAPIError, MCPConnectionError, MCPDataError) as e:
        logging.error(f"MCP Error: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)

    # --- Option 2: Initialize from mcp.json ---
    try:
        # Load 'local' config from mcp.json
        client_from_config = MCPClient.from_config(server_name="local")
        
        async with client_from_config as mcp:
            logging.info(f"Using server configured as 'local'")
            tools = await mcp.list_tools()
            logging.info(f"Found {len(tools)} tools")
            
    except (FileNotFoundError, ValueError, KeyError, MCPDataError) as e:
        logging.error(f"Configuration Error: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        
    # --- Option 3: Use MultiServerMCPClient ---
    try:
        # Connect to multiple servers
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
            # Get tools from all servers
            all_tools = multi_client.get_tools()
            logging.info(f"Total tools from all servers: {len(all_tools)}")
            
            # Get a prompt from a specific server
            messages = await multi_client.get_prompt("math", "calculate", {"expression": "2+2"})
            for msg in messages:
                logging.info(f"Message: {msg.content}")
                
            # Working with resources from multiple servers
            # List resources from a specific server
            math_resources = await multi_client.list_resources("math")
            logging.info(f"Math server has {len(math_resources.resources)} resources")
            
            # Read a resource from a specific server (if any available)
            if math_resources.resources:
                math_resource_uri = math_resources.resources[0].uri
                math_content = await multi_client.read_resource("math", math_resource_uri)
                logging.info(f"Read math resource: {math_resource_uri}")
                
                # Subscribe and unsubscribe to resource updates
                await multi_client.subscribe_to_resource("math", math_resource_uri)
                await multi_client.unsubscribe_from_resource("math", math_resource_uri)
                
    except Exception as e:
        logging.error(f"MultiServerMCPClient error: {e}", exc_info=True)

# Run the async main function
if __name__ == "__main__":
    asyncio.run(main())
```

## Migration from v0.3.0 to v0.4.1

Version 0.4.1 introduces significant changes by migrating to the official MCP library and langchain-mcp-adapters. Key differences:

1. **Async API**: Methods are now async and require `await` and an async context manager.
2. **Transport Change**: The "http" transport is no longer supported; use "sse" instead.
3. **MultiServerMCPClient**: A new class for connecting to multiple MCP servers.
4. **LangChain Integration**: Tools are now LangChain tools.

## Development

- Clone: `git clone https://github.com/anukchat/mcpwire.git`
- Setup Env: Create and activate a virtual environment
- Install Dev Dependencies: `pip install -e ".[dev]"`

## Contributing

Contributions are welcome! Here's how you can contribute to the project:

1. **Fork the Repository**: Create your own fork of the project
2. **Create a Branch**: Create a branch for your changes
3. **Make Changes**: Implement your changes, following the coding style
4. **Run Tests**: Make sure the tests pass by running `pytest`
5. **Submit a Pull Request**: Open a PR with a clear description of your changes

### Testing

Run the tests using pytest:

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

### Continuous Integration

This project uses GitHub Actions for continuous integration:

- **Tests**: Automatically run on each push and pull request to main/master branches
- **Builds**: Package is built and validated to ensure it will install correctly
- **Publishing**: When a new version tag is pushed (e.g., v0.4.1), the package is automatically published to PyPI

### Creating a Release

To release a new version:

1. Update the version in `pyproject.toml` and `mcpwire/__init__.py`
2. Update the CHANGELOG.md file with the changes
3. Commit the changes and push to GitHub
4. Create and push a new tag that matches the version:

```bash
git tag -a v0.4.1 -m "Release v0.4.1"
git push origin v0.4.1
```

The GitHub Actions workflow will automatically build and publish the package to PyPI.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Troubleshooting Resources

When working with MCP resources, the following issues might occur:

### Resource Errors

1. **Server Not Found**: When using `MultiServerMCPClient`, ensure the server name exists before accessing resources.
   ```python
   # This will raise ValueError if "math_server" is not connected
   resources = await multi_client.list_resources("math_server")
   ```

2. **Resource Not Found**: Ensure the resource URI is valid and accessible.
   ```python
   try:
       resource = await client.read_resource("file:///nonexistent/file.txt")
   except MCPAPIError as e:
       print(f"Resource error: {e}")
   ```

3. **Binary Resource Handling**: When dealing with binary resources (images, PDFs, etc.):
   ```python
   import base64
   
   # Read a binary resource
   response = await client.read_resource("image:///logo.png")
   if response.contents[0].blob:
       # Decode base64 data
       binary_data = base64.b64decode(response.contents[0].blob)
       with open("logo.png", "wb") as f:
           f.write(binary_data)
   ```

4. **Template Parameters**: When using templates, ensure all required parameters are provided:
   ```python
   # For a template like "file:///workspace/{path}"
   file_uri = "file:///workspace/documents/report.pdf"  # Provide the complete URI
   ```

5. **Subscription Leaks**: Always unsubscribe from resources when no longer needed:
   ```python
   try:
       await client.subscribe_to_resource("screen://capture/latest")
       # Do work with the resource...
   finally:
       # Ensure unsubscribe happens even if errors occur
       await client.unsubscribe_from_resource("screen://capture/latest")
   ```

### Common Configuration Issues

1. **Missing Resource Configuration**: Ensure the server has resources enabled:
   ```json
   "resources": {
     "enabled": true
   }
   ```

2. **Invalid Template Format**: Resource templates must follow RFC 6570 URI template format:
   ```json
   "uri_template": "file:///workspace/{path}",  // Correct
   "uri_template": "file:///workspace/<path>",  // Incorrect
   ```

3. **Incorrect MIME Types**: Use standard MIME types for resources to ensure proper handling:
   ```json
   "mime_type": "application/json"      // For JSON data
   "mime_type": "text/plain"            // For text files
   "mime_type": "image/png"             // For PNG images
   "mime_type": "application/pdf"       // For PDF documents
   ```