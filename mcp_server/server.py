"""MCP сервер для демонстрации стандарта разработки."""

# Standard library
import os
import sys
from pathlib import Path
from typing import Dict, Any

# Добавляем корневой каталог проекта в sys.path для поддержки импорта

project_root = Path(__file__).parent.parent.resolve()

if str(project_root) not in sys.path:

    sys.path.insert(0, str(project_root))

# Устанавливаем __package__ для правильной работы относительных импортов

__package__ = 'mcp_server'

# Это нужно когда файл запускается как скрипт: python mcp/server.py

if __name__ == "__main__":

    pass

# Third-party
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())

from fastmcp import FastMCP, Context

from opentelemetry import trace

# Импортируем единый экземпляр FastMCP
from mcp_server.mcp_instance import mcp
from mcp_server.globals import HOST, PORT

# OpenTelemetry tracer
tracer = trace.get_tracer(__name__)

# Инициализация трейсинга
def init_tracing():
    """Инициализация OpenTelemetry для трейсинга."""
    # Здесь можно добавить настройку экспорта трейсов
    # Например, через OTEL_ENDPOINT переменную окружения
    pass

init_tracing()

# Импортируем инструменты
from mcp_server.tools.get_text_from_video import get_text_from_video
from mcp_server.tools.cut_and_overlay_lips import cut_and_overlay_lips
from mcp_server.tools.replace_video_segments import replace_video_segments
from mcp_server.tools.generate_tts_audio import generate_tts_audio



# Добавляем промпты (опционально)
@mcp.prompt()
def example_prompt(query: str = "") -> str:
    """Пример промпта для демонстрации."""
    return f"Пример промпта для запроса: {query}"


def main():
    """Запуск MCP сервера с HTTP транспортом."""
    # Определяем режим запуска: через fastmcp dev или напрямую
    # fastmcp dev использует stdio транспорт и передает данные через stdin/stdout
    # По умолчанию используем stdio для совместимости с fastmcp dev
    # Если явно указан --http, используем streamable-http
    
    use_stdio = "--stdio" in sys.argv or os.getenv("MCP_TRANSPORT") == "stdio"
    use_http = "--http" in sys.argv or os.getenv("MCP_TRANSPORT") == "http"

    # По умолчанию используем stdio для совместимости с MCP клиентами
    if not use_stdio and not use_http:
        use_stdio = True

    # Включаем HTTP транспорт по умолчанию для поддержки LLM системы только если не указан stdio
    if not use_stdio and not use_http and os.getenv("ENABLE_HTTP_FOR_LLM", "true").lower() != "false":
        use_http = True
    
    if use_stdio:
        # Режим stdio для MCP клиентов
        print("🔧 Режим stdio: использование stdio транспорта", file=sys.stderr)
        mcp.run(transport="stdio")
    elif use_http:
        # Прямой запуск с HTTP - используем streamable-http
        print("=" * 60)
        print("🌐 ЗАПУСК MCP СЕРВЕРА")
        print("=" * 60)
        print(f"🚀 MCP Server: http://{HOST}:{PORT}/mcp")
        print("=" * 60)

        # Запускаем MCP сервер с SSE транспортом
        mcp.run(transport="sse", host=HOST, port=PORT)
    else:
        # По умолчанию stdio
        print("🔧 Режим по умолчанию: использование stdio транспорта", file=sys.stderr)
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()


