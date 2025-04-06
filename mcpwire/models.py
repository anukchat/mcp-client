# mcpwire/mcpwire/models.py

"""
Pydantic models for validating and representing MCP request and response data structures.
These models should align with the MCP specification.
Adjust fields as necessary based on the specific MCP server implementation or version.
"""

from pydantic import BaseModel, Field, Json
from typing import List, Dict, Any, Optional, Union

# --- Core MCP Objects ---

class ToolParameterProperty(BaseModel):
    """Describes a single property within a tool's parameter schema (OpenAPI style)."""
    type: str
    description: Optional[str] = None
    enum: Optional[List[str]] = None # For parameters with fixed possible values

class ToolParameterSchema(BaseModel):
    """Defines the schema for a tool's parameters, typically following OpenAPI Schema Object."""
    type: str = "object"
    properties: Dict[str, ToolParameterProperty]
    required: Optional[List[str]] = None

class ToolDefinition(BaseModel):
    """Describes an available tool that the model can call."""
    name: str = Field(..., description="The name of the function/tool to be called.")
    description: Optional[str] = Field(None, description="A description of what the tool does.")
    parameters: Optional[ToolParameterSchema] = Field(None, description="The parameters the tool accepts, described as an OpenAPI Schema Object.")

class Resource(BaseModel):
    """Represents a resource managed by the MCP server (e.g., files, session state)."""
    id: str = Field(..., description="Unique identifier for the resource.")
    name: Optional[str] = Field(None, description="A user-friendly name for the resource.")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Arbitrary metadata associated with the resource.")
    # Add other common resource fields based on MCP spec (e.g., content_type, size, created_at)

# --- Request Models ---

class PromptMessage(BaseModel):
    """A single message within a prompt conversation."""
    role: str = Field(..., description="The role of the message author (e.g., 'user', 'assistant', 'system', 'tool').")
    content: Union[str, List[Dict[str, Any]]] = Field(..., description="The content of the message. Can be text or structured content (e.g., for tool results).")
    tool_call_id: Optional[str] = Field(None, description="Required if role is 'tool', identifies the tool call being responded to.")
    # Add optional 'name' field if needed for specific tool roles, etc.

class ToolChoice(BaseModel):
    """Specifies how the model should use tools (if supported by the server)."""
    type: str = "function" # Currently only 'function' is typical
    function: Dict[str, str] # e.g., {"name": "my_tool_name"}

class PromptRequest(BaseModel):
    """Request body for sending a prompt to the MCP server's /prompt endpoint."""
    messages: List[PromptMessage] = Field(..., description="A list of messages comprising the conversation history.")
    session_id: Optional[str] = Field(None, description="Optional identifier for the session context.")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Model-specific parameters (e.g., temperature, max_tokens).")
    tools: Optional[List[ToolDefinition]] = Field(None, description="A list of tools the model may call.")
    tool_choice: Optional[Union[str, ToolChoice]] = Field(None, description="Controls which tool is called by the model (e.g., 'none', 'auto', or specific tool).")
    stream: Optional[bool] = Field(None, description="Whether to stream the response (if supported). Client needs modification to handle streaming.")

class ResourceRequest(BaseModel):
    """Request body for creating or updating a resource."""
    name: Optional[str] = Field(None, description="Name for the resource.")
    content: Optional[Any] = Field(None, description="The actual content of the resource (structure depends on server).")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata for the resource.")
    # Add other relevant fields like 'content_type' if applicable

# --- Response Models ---

class ToolCall(BaseModel):
    """Represents a request from the model to call a specific tool."""
    id: str = Field(..., description="Unique identifier for this specific tool call.")
    type: str = Field(default="function", description="The type of tool call, typically 'function'.")
    function: str = Field(..., alias="name", description="The name of the function/tool to call.") # MCP uses 'name' here
    arguments: Json[Dict[str, Any]] = Field(..., description="The arguments to pass to the function, as a JSON string that needs parsing.")

    class Config:
        populate_by_name = True # Allow using 'name' in input data for 'function' field

class AssistantMessageResponse(BaseModel):
    """Response message from the assistant, potentially including tool calls."""
    role: str = Field(default="assistant", description="Role is always 'assistant'.")
    content: Optional[str] = Field(None, description="Text content of the assistant's response.")
    tool_calls: Optional[List[ToolCall]] = Field(None, description="List of tool calls requested by the assistant.")

class PromptUsage(BaseModel):
    """Token usage information for a prompt request (if provided by the server)."""
    prompt_tokens: Optional[int] = Field(None, description="Number of tokens in the prompt.")
    completion_tokens: Optional[int] = Field(None, description="Number of tokens in the generated completion.")
    total_tokens: Optional[int] = Field(None, description="Total number of tokens used.")

class PromptResponse(BaseModel):
    """Response body received from the MCP server's /prompt endpoint."""
    message: AssistantMessageResponse = Field(..., description="The assistant's response message.")
    session_id: Optional[str] = Field(None, description="Session identifier associated with the response.")
    usage: Optional[PromptUsage] = Field(None, description="Token usage information for the request.")

class ServerMetadata(BaseModel):
    """Information about the MCP server capabilities and version."""
    mcp_version: Optional[str] = Field(None, alias="mcpVersion", description="The version of the MCP specification supported.")
    # Add other potential metadata fields (e.g., supported_features, model_info)
    class Config:
        populate_by_name = True # Allow using 'mcpVersion' in input data

class ListToolsResponse(BaseModel):
    """Response body for the GET /tools endpoint."""
    tools: List[ToolDefinition]

class ListResourcesResponse(BaseModel):
    """Response body for the GET /resources endpoint."""
    resources: List[Resource]

