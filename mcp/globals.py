import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# Загружаем переменные окружения из .env
load_dotenv(find_dotenv())

# MCP Server Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
MCP_SERVER_NAME = os.getenv("MCP_SERVER_NAME", "mcp-server")

# OpenTelemetry Configuration
OTEL_ENDPOINT = os.getenv("OTEL_ENDPOINT", "")
OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "mcp-server")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Video Processing
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "tiny")
VIDEO_PATH = os.getenv("VIDEO_PATH", os.path.join(os.path.dirname(__file__), "..", "videos"))
WAV2LIB_PATH = os.getenv("WAV2LIB_PATH", os.path.join(os.path.dirname(__file__), "..", "wav2lib"))

# LLM Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://foundation-models.api.cloud.ru/v1")
GIGACHAT_MODEL = os.getenv("GIGACHAT_MODEL", "ai-sage/GigaChat3-10B-A1.8B")

