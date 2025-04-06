# mcpwire/mcpwire/exceptions.py

"""
Custom exception classes for the MCP client.
"""

class MCPError(Exception):
    """Base exception class for all MCP client errors."""
    pass

class MCPConnectionError(MCPError):
    """
    Raised when the client encounters a network issue trying to connect
    to the MCP server (e.g., DNS resolution failure, refused connection).
    """
    pass

class MCPAPIError(MCPError):
    """
    Raised when the MCP server returns an HTTP error status code (>= 400)
    or provides a response that doesn't conform to the expected format.
    """
    def __init__(self, status_code: int, error_details: dict | str | None = None):
        """
        Initializes the MCPAPIError.

        Args:
            status_code: The HTTP status code received from the server.
            error_details: Optional dictionary or string containing details
                           parsed from the server's error response body.
        """
        self.status_code = status_code
        self.error_details = error_details
        message = f"MCP Server responded with error status {status_code}"
        if error_details:
            # Limit detail length in basic message for readability
            details_str = str(error_details)
            if len(details_str) > 200:
                details_str = details_str[:200] + "..."
            message += f". Details: {details_str}"
        super().__init__(message)

class MCPTimeoutError(MCPConnectionError):
    """
    Raised specifically when a request to the MCP server times out.
    Inherits from MCPConnectionError as it's a type of connection issue.
    """
    pass

class MCPDataError(MCPError):
    """
    Raised when there's an issue with data validation or processing,
    such as failing to parse the server's response according to Pydantic models
    or issues with the configuration file format.
    """
    pass

# You might add more specific exceptions later if needed,
# e.g., MCPAuthenticationError, MCPRateLimitError

