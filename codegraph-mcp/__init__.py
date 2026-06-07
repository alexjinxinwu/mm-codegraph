"""codegraph-mcp — MCP server with stdio transport.

This package contains only MCP-specific code:
- stdio transport adapter
- MCP protocol parsing
- FastMCP server with @mcp.tool() decorators

All query logic delegates to QueryEngine from codegraph-core.
"""

from .server import mcp

__all__ = ["mcp"]