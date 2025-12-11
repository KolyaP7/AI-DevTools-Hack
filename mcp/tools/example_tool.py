"""Пример инструмента для демонстрации стандарта MCP."""

import os
from typing import Dict, Any

import httpx
from fastmcp import Context
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field

try:
    from ..mcp_instance import mcp
    from .utils import ToolResult, _require_env_vars, format_api_error
except ImportError:
    from mcp_instance import mcp
    from tools.utils import ToolResult, _require_env_vars, format_api_error

# OpenTelemetry tracer
tracer = trace.get_tracer(__name__)


@mcp.tool(
    name="example_tool",
    description="""📝 Пример инструмента MCP сервера.

Этот инструмент демонстрирует стандартную структуру и использование всех
рекомендуемых практик: логирование через Context, прогресс-отчеты,
OpenTelemetry трейсинг и обработку ошибок.
"""
)
async def example_tool(
    query: str = Field(
        ..., 
        description="Поисковый запрос для обработки"
    ),
    limit: int = Field(
        default=10,
        description="Максимальное количество результатов"
    ),
    ctx: Context = None
) -> ToolResult:
    """
    📝 Выполняет примерную операцию с поисковым запросом.
    
    Args:
        query: Поисковый запрос пользователя
        limit: Максимальное количество результатов (по умолчанию: 10)
        ctx: Контекст для логирования и отслеживания прогресса
        
    Returns:
        ToolResult: Результат выполнения инструмента
        
    Raises:
        McpError: При ошибках выполнения
    """
    with tracer.start_as_current_span("example_tool") as span:
        # Настройка атрибутов спана
        span.set_attribute("query", query)
        span.set_attribute("limit", limit)
        
        # Логирование начала операции
        await ctx.info("🚀 Начинаем выполнение инструмента")
        await ctx.report_progress(progress=0, total=100)
        
        try:
            # Валидация переменных окружения (если нужны)
            # env = _require_env_vars(["API_KEY"])
            
            # Этап 1: Подготовка (0-25%)
            await ctx.info("🔧 Подготавливаем запрос")
            await ctx.report_progress(progress=25, total=100)
            
            # Этап 2: Симуляция API запроса (25-75%)
            await ctx.info("📡 Обрабатываем запрос")
            await ctx.report_progress(progress=50, total=100)
            
            # Пример обработки (в реальном инструменте здесь был бы API вызов)
            # async with httpx.AsyncClient(timeout=20.0) as client:
            #     response = await client.get(
            #         "https://api.example.com/search",
            #         params={"q": query, "limit": limit},
            #         headers={"Authorization": f"Bearer {api_key}"}
            #     )
            #     response.raise_for_status()
            #     result = response.json()
            
            # Симуляция результата
            result = {
                "query": query,
                "limit": limit,
                "items": [
                    {"id": i, "title": f"Результат {i} для запроса '{query}'"}
                    for i in range(1, min(limit, 5) + 1)
                ],
                "total": min(limit, 5)
            }
            
            await ctx.report_progress(progress=75, total=100)
            
            # Этап 3: Форматирование результатов (75-100%)
            await ctx.info("📄 Форматируем результаты")
            
            formatted_result = f"Найдено результатов: {result['total']}\n\n"
            formatted_result += "\n".join([
                f"- {item['title']}"
                for item in result["items"]
            ])
            
            await ctx.report_progress(progress=100, total=100)
            await ctx.info("✅ Операция завершена успешно")
            
            span.set_attribute("success", True)
            span.set_attribute("results_count", result["total"])
            
            return ToolResult(
                content=[TextContent(type="text", text=formatted_result)],
                structured_content=result,
                meta={"query": query, "limit": limit}
            )
            
        except Exception as e:
            span.set_attribute("error", str(e))
            await ctx.error(f"❌ Ошибка выполнения: {e}")
            
            from mcp.shared.exceptions import McpError, ErrorData
            raise McpError(
                ErrorData(
                    code=-32603,
                    message=f"Не удалось выполнить операцию: {e}"
                )
            )

