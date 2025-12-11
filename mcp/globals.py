import os

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

MCP_SERVER_NAME = os.getenv("MCP_SERVER_NAME", "mcp-server")
