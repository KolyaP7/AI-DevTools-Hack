import os

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

MCP_SERVER_NAME = os.getenv("MCP_SERVER_NAME", "mcp-server")


WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
VIDEO_PATH = os.getenv("VIDEO_PATH", "./videos")


WAV2LIB_PATH = os.getenv("WAV2LIB_PATH", "./wav2lip")