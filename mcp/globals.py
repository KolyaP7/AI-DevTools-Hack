import os

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

MCP_SERVER_NAME = os.getenv("MCP_SERVER_NAME", "mcp-server")


WHISPER_MODEL = os.getenv("WHISPER_MODEL", "tiny")
VIDEO_PATH = os.getenv("VIDEO_PATH", os.path.join(os.path.dirname(__file__), "..", "videos"))


WAV2LIB_PATH=os.getenv("WAV2LIB_PATH", os.path.join(os.path.dirname(__file__), "..", "wav2lib"))

