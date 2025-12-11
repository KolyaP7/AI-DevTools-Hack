"""Единый экземпляр FastMCP для всего приложения."""

from fastmcp import FastMCP

try:
    from globals import MCP_SERVER_NAME
except ImportError:
    from mcp.globals import MCP_SERVER_NAME

# Создаем единый экземпляр FastMCP
mcp = FastMCP(MCP_SERVER_NAME)
