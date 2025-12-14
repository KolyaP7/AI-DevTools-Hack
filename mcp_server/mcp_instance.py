"""Единый экземпляр FastMCP для всего приложения."""

# from fastmcp import FastMCP

from mcp.server.fastmcp import FastMCP



from globals import MCP_SERVER_NAME


# Создаем единый экземпляр FastMCP
mcp = FastMCP(MCP_SERVER_NAME)
