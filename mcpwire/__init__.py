# mcpwire/mcpwire/__init__.py

"""
MCP Client Package Initialization.

This file makes the core components of the mcpwire package easily importable
and defines the package version.

The implementation has been updated to use the official MCP library and
langchain-mcp-adapters.
"""

# Define the package version. Follow semantic versioning (major.minor.patch).
__version__ = "0.4.1" # Updated to reflect migration to official MCP library

# Import core classes and exceptions for easier access
from .client import MCPClient, MultiServerMCPClient, StdioConnection, SSEConnection
from .exceptions import (
    MCPError,
    MCPAPIError,
    MCPConnectionError,
    MCPTimeoutError,
    MCPDataError
)
from .models import (
    # Request Models
    PromptMessage,
    PromptRequest,
    ResourceRequest,
    ToolChoice,
    # Response Models
    PromptResponse,
    AssistantMessageResponse,
    ToolCall,
    PromptUsage,
    ListToolsResponse,
    ListResourcesResponse,
    ServerMetadata,
    # Core Objects
    ToolDefinition,
    Resource,
    ToolParameterSchema,
    ToolParameterProperty,
)

# Define __all__ to control what `from mcpwire import *` imports
# Note: Class methods like from_config are accessed via the class (MCPClient.from_config)
# and don't need to be in __all__.
__all__ = [
    # Client
    "MCPClient",
    "MultiServerMCPClient",
    "StdioConnection",
    "SSEConnection",

    # Exceptions
    "MCPError",
    "MCPAPIError",
    "MCPConnectionError",
    "MCPTimeoutError",
    "MCPDataError",

    # --- Pydantic Models ---
    # Request Models
    "PromptMessage",
    "PromptRequest",
    "ResourceRequest",
    "ToolChoice",

    # Response Models
    "PromptResponse",
    "AssistantMessageResponse",
    "ToolCall",
    "PromptUsage",
    "ListToolsResponse",
    "ListResourcesResponse",
    "ServerMetadata",

    # Core Objects
    "ToolDefinition",
    "Resource",
    "ToolParameterSchema",
    "ToolParameterProperty",

    # Package Version
    "__version__",
]

# Optional: Configure basic logging handler if none is set by the user application
# This prevents "No handler found" warnings if the user app doesn't configure logging.
import logging
logging.getLogger(__name__).addHandler(logging.NullHandler())
