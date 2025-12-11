"""Единый экземпляр FastMCP для всего приложения."""

from mcp.server.fastmcp import FastMCP


try:
    from globals import MCP_SERVER_NAME
except ImportError:
    from globals import MCP_SERVER_NAME

# Создаем единый экземпляр FastMCP
mcp = FastMCP(MCP_SERVER_NAME)
