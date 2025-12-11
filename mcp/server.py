"""MCP сервер для демонстрации стандарта разработки."""

# Standard library
import os
import sys
from pathlib import Path
from typing import Dict, Any

# Добавляем корневую директорию проекта в sys.path для поддержки прямого запуска
# Это нужно когда файл запускается как скрипт: python mcp/server.py
if __name__ == "__main__":
    # Определяем корневую директорию проекта (на уровень выше mcp/)
    project_root = Path(__file__).parent.parent.resolve()
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

# Third-party
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())

from mcp.server.fastmcp import FastMCP, Context

from opentelemetry import trace

# Импортируем единый экземпляр FastMCP
try:
    # Попытка относительного импорта (когда запускается как модуль)
    from mcp_instance import mcp
    from globals import HOST, PORT
except ImportError:
    # Абсолютный импорт (когда запускается как скрипт)
    from mcp_instance import mcp
    from globals import HOST, PORT

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
try:
    from tools.example_tool import example_tool
    from tools.get_text_from_video import get_text_from_video
except ImportError:
    from tools.example_tool import example_tool
    from tools.get_text_from_video import get_text_from_video

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
    
    use_http = "--http" in sys.argv or os.getenv("MCP_TRANSPORT") == "http"
    
    if use_http:
        # Прямой запуск с HTTP - используем streamable-http
        print("=" * 60)
        print("🌐 ЗАПУСК MCP СЕРВЕРА")
        print("=" * 60)
        print(f"🚀 MCP Server: http://{HOST}:{PORT}/mcp")
        print("=" * 60)
        
        # Запускаем MCP сервер с streamable-http транспортом
        mcp.run(transport="streamable-http", host=HOST, port=PORT, stateless_http=True)
    else:
        # Режим разработки через fastmcp dev - используем stdio
        # Вывод в stderr, чтобы не мешать stdio потоку
        print("🔧 Режим разработки: использование stdio транспорта", file=sys.stderr)
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()


