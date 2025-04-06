# mcp-python-client/mcp_client/utils.py

"""
Utility functions for the MCP client.
"""

from urllib.parse import urljoin

def join_url_path(base_url: str, path: str) -> str:
    """
    Safely joins a base URL and a relative path segment.

    Ensures there's exactly one slash between the base URL's path component
    and the start of the relative path, handling potential trailing slashes
    in the base URL and leading slashes in the path.

    Args:
        base_url: The base URL (e.g., "http://localhost:8000", "http://api.example.com/v1").
        path: The relative path segment (e.g., "prompt", "/tools", "resources/res_123").

    Returns:
        The correctly joined full URL string.
    """
    # Ensure base_url ends with a slash if it has a path component or is just the domain
    if not base_url.endswith('/'):
        base_url += '/'

    # urljoin handles joining correctly, including removing leading slashes from the path if needed
    # e.g., urljoin("http://host.com/v1/", "/path") -> "http://host.com/path" (correct)
    # e.g., urljoin("http://host.com/v1/", "path") -> "http://host.com/v1/path" (correct)
    # Use lstrip('/') on the path to ensure urljoin behaves predictably even if base has no path
    return urljoin(base_url, path.lstrip('/'))

