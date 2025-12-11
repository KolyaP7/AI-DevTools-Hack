 
Стандарт написания MCP серверов

Общие принципы
1.1 Единый экземпляр FastMCP
ВСЕГДА создавайте единый экземпляр FastMCP в отдельном файле mcp_instance.py:

"""Единый экземпляр FastMCP для всего приложения."""

from fastmcp import FastMCP

# Создаем единый экземпляр FastMCP
mcp = FastMCP("your-server-name")


Почему: Это позволяет импортировать mcp в любом модуле без циклических зависимостей и обеспечивает единую точку конфигурации.
1.2 Разделение инструментов по файлам
ВСЕГДА создавайте отдельный файл для каждого MCP инструмента в директории tools/:

 project/
├── mcp_instance.py          # Единый экземпляр FastMCP
├── server.py                # Главный файл запуска
├── tools/
│   ├── __init__.py
│   ├── tool_name.py         # Один инструмент = один файл
│   └── utils.py             # Общие утилиты



Почему: Упрощает поддержку, тестирование и понимание кода.
1.3 Асинхронность
ВСЕГДА используйте async def для всех MCP инструментов:

from fastmcp import Context
from pydantic import Field
from mcp.types import TextContent
from .utils import ToolResult

@mcp.tool()
async def my_tool(
    query: str = Field(
        ..., 
        description="Поисковый запрос пользователя"
    ),
    ctx: Context = None
) -> ToolResult:
    """Описание инструмента."""
    import httpx
    import os
    
    # Асинхронный API вызов
    api_key = os.getenv("API_KEY")
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(
            "https://api.example.com/search",
            params={"q": query},
            headers={"Authorization": f"Bearer {api_key}"}
        )
        response.raise_for_status()
        result = response.json()
    
    return ToolResult(
        content=[TextContent(type="text", text=str(result))],
        structured_content={"result": result},
        meta={"query": query}
    )




Структура проекта
2.1 Базовая структура
project/
├── mcp_instance.py              # Единый экземпляр FastMCP
├── server.py                    # Главный файл запуска
├── pyproject.toml               # Зависимости проекта
├── .env.example                 # Пример переменных окружения
├── env_options.json             # Описание переменных окружения
├── mcp-server-catalog.yaml      # Каталог MCP сервера
├── mcp_tools.json               # JSON описание инструментов MCP
├── README.md                    # Документация проекта
├── Dockerfile                   # Docker образ
├── docker-compose.yml           # Docker Compose конфигурация
├── tools/
│   ├── __init__.py
│   ├── tool_name.py            # Инструменты (один файл = один инструмент)
│   ├── utils.py                # Общие утилиты
│   └── models.py               # Pydantic модели (опционально)
├── middleware/
│   ├── __init__.py
│   └── custom_middleware.py    # Кастомные middleware (опционально)
├── test/
│   ├── __init__.py
│   ├── test_tools.py           # Unit тесты инструментов
│   └── test_integration.py     # Интеграционные тесты
└── metrics.py                   # Prometheus метрики (опционально)


Примечание: Все файлы .py содержат код на Python.
2.2 Файл server.py
Главный файл должен содержать:

"""MCP сервер для [описание сервера]."""

# Standard library
import os
from typing import Dict, Any

# Third-party
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())

from fastmcp import FastMCP, Context
from opentelemetry import trace

# Импортируем единый экземпляр FastMCP
from mcp_instance import mcp

# Константы
PORT = int(os.getenv("PORT", "8000"))

# OpenTelemetry tracer
tracer = trace.get_tracer(__name__)

# Инициализация трейсинга
def init_tracing():
    """Инициализация OpenTelemetry для трейсинга."""
    # ... код инициализации

init_tracing()

# Импортируем инструменты
from tools.tool_name import tool_name

# Добавляем промпты (опционально)
@mcp.prompt()
def my_prompt(query: str = "") -> str:
    """Описание промпта."""
    return f"Промпт для: {query}"

def main():
    """Запуск MCP сервера с HTTP транспортом."""
    print("=" * 60)
    print("🌐 ЗАПУСК MCP СЕРВЕРА")
    print("=" * 60)
    print(f"🚀 MCP Server: http://0.0.0.0:{PORT}/mcp")
    print("=" * 60)
    
    # Запускаем MCP сервер с streamable-http транспортом
    mcp.run(transport="streamable-http", host="0.0.0.0", port=PORT, stateless_http=True)

if __name__ == "__main__":
    main()



Транспорт и запуск
3.1 Использование streamable-http транспорта
ВСЕГДА используйте streamable-http транспорт:
 
 # ✅ ПРАВИЛЬНО
mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)

# ❌ НЕПРАВИЛЬНО - не используйте SSE
mcp.run(transport="sse", ...)
 

Почему: streamable-http - стандартный и рекомендуемый транспорт для MCP серверов.
3.2 Настройка порта и хоста
Используйте переменные окружения с дефолтными значениями:

PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")

mcp.run(transport="streamable-http", host=HOST, port=PORT)



Создание инструментов
4.1 Базовая структура инструмента
 
"""Описание модуля инструмента."""

import os
from typing import Dict, Any

from fastmcp import Context
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field

# Импортируем mcp из единого экземпляра
from mcp_instance import mcp

# Импортируем утилиты
from .utils import ToolResult, _require_env_vars

# OpenTelemetry tracer
tracer = trace.get_tracer(__name__)


@mcp.tool(
    name="tool_name",
    description="""📝 Подробное описание инструмента.

Что делает инструмент, какие проблемы решает, примеры использования.
"""
)
async def tool_name(
    param1: str = Field(
        ..., 
        description="Описание параметра 1"
    ),
    param2: int = Field(
        default=10,
        description="Описание параметра 2"
    ),
    ctx: Context = None
) -> ToolResult:
    """
    📝 Подробное описание функции инструмента.
    
    Args:
        param1: Описание параметра 1
        param2: Описание параметра 2
        ctx: Контекст для логирования и отслеживания прогресса
        
    Returns:
        ToolResult: Результат выполнения инструмента
        
    Raises:
        McpError: При ошибках выполнения
        
    Examples:
        >>> result = await tool_name("value", 10, ctx)
        >>> print(result.content)
    """
    with tracer.start_as_current_span("tool_name") as span:
        # Настройка атрибутов спана
        span.set_attribute("param1", param1)
        span.set_attribute("param2", param2)
        
        # Логирование начала операции
        await ctx.info("🚀 Начинаем выполнение инструмента")
        await ctx.report_progress(progress=0, total=100)
        
        try:
            # Основная логика
            result = await perform_operation(param1, param2)
            
            await ctx.report_progress(progress=100, total=100)
            await ctx.info("✅ Операция завершена успешно")
            
            span.set_attribute("success", True)
            
            return ToolResult(
                content=[TextContent(type="text", text=str(result))],
                structured_content={"result": result},
                meta={"operation": "tool_name"}
            )
            
        except Exception as e:
            span.set_attribute("error", str(e))
            await ctx.error(f"❌ Ошибка выполнения: {e}")
            raise


4.2 Параметры инструментов
ВСЕГДА используйте Pydantic Field для описания параметров:

from fastmcp import Context
from pydantic import Field
from mcp.types import TextContent
from .utils import ToolResult

@mcp.tool()
async def my_tool(
    required_param: str = Field(
        ..., 
        description="Обязательный параметр для выполнения операции"
    ),
    optional_param: int = Field(
        default=10, 
        description="Опциональный параметр с значением по умолчанию"
    ),
    ctx: Context = None
) -> ToolResult:
    """
    Пример инструмента с обязательными и опциональными параметрами.
    
    Args:
        required_param: Обязательный строковый параметр
        optional_param: Опциональный числовой параметр (по умолчанию: 10)
        ctx: Контекст для логирования
        
    Returns:
        ToolResult: Результат выполнения инструмента
    """
    import httpx
    import os
    
    await ctx.info(f"Обрабатываем параметры: {required_param}, {optional_param}")
    
    # Выполняем API запрос
    api_key = os.getenv("API_KEY")
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            "https://api.example.com/process",
            json={
                "param": required_param,
                "limit": optional_param
            },
            headers={"Authorization": f"Bearer {api_key}"}
        )
        response.raise_for_status()
        result = response.json()
    
    return ToolResult(
        content=[TextContent(type="text", text=str(result))],
        structured_content={
            "required_param": required_param,
            "optional_param": optional_param,
            "result": result
        },
        meta={}
    )



4.3 Возвращаемые значения
ВСЕГДА возвращайте ToolResult:

from mcp.types import TextContent
from .utils import ToolResult

return ToolResult(
    content=[TextContent(type="text", text="Человеко-читаемый текст")],
    structured_content={"key": "value"},  # Структурированные данные
    meta={"additional": "metadata"}        # Метаданные
)




Логирование и контекст
5.1 Использование Context
ВСЕГДА используйте параметр Context для логирования в инструментах:

from fastmcp import Context
from pydantic import Field
from mcp.types import TextContent
from .utils import ToolResult

@mcp.tool()
async def my_tool(
    search_query: str = Field(
        ..., 
        description="Поисковый запрос для обработки"
    ),
    ctx: Context = None
) -> ToolResult:
    # ✅ ПРАВИЛЬНО - используем ctx
    await ctx.debug("🔍 Детальная информация для отладки")
    await ctx.info("ℹ️ Информационное сообщение")
    await ctx.warning("⚠️ Предупреждение")
    await ctx.error("❌ Ошибка")
    
    # ❌ НЕПРАВИЛЬНО - не используйте logger напрямую
    # logger.info("Сообщение")
    
    return ToolResult(
        content=[TextContent(type="text", text="Результат")],
        structured_content={"query": search_query},
        meta={}
    )



5.2 Эмодзи в логах
ВСЕГДА используйте эмодзи для лучшей читаемости логов:

await ctx.info("🚀 Начинаем операцию")
await ctx.info("✅ Операция завершена")
await ctx.warning("⚠️ Предупреждение")
await ctx.error("❌ Ошибка")
await ctx.debug("🔍 Детальная информация")



5.3 Прогресс-отчеты
ВСЕГДА реализуйте прогресс-отчеты для длительных операций:
 
from fastmcp import Context
from pydantic import Field
from mcp.types import TextContent
from .utils import ToolResult

@mcp.tool()
async def long_operation(
    query: str = Field(
        ..., 
        description="Запрос для длительной операции"
    ),
    ctx: Context = None
) -> ToolResult:
    """
    Пример инструмента с прогресс-отчетами.
    
    Args:
        query: Запрос для обработки
        ctx: Контекст для логирования и прогресс-отчетов
        
    Returns:
        ToolResult: Результат выполнения операции
    """
    import httpx
    import os
    
    # Начало операции (0%)
    await ctx.info("🚀 Начинаем длительную операцию")
    await ctx.report_progress(progress=0, total=100)

    # Этап 1: Аутентификация (0-25%)
    await ctx.info("🔐 Этап 1: Выполняем аутентификацию")
    auth_url = os.getenv("AUTH_URL", "https://api.example.com/auth")
    async with httpx.AsyncClient(timeout=10.0) as client:
        auth_response = await client.post(
            auth_url,
            json={
                "keyId": os.getenv("API_KEY_ID"),
                "secret": os.getenv("API_KEY_SECRET")
            }
        )
        auth_response.raise_for_status()
        token = auth_response.json().get("access_token")
    
    await ctx.report_progress(progress=25, total=100)

    # Этап 2: Запрос к API (25-50%)
    await ctx.info("📡 Этап 2: Отправляем запрос к API")
    api_url = os.getenv("API_URL", "https://api.example.com/search")
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(
            api_url,
            params={"q": query},
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        api_data = response.json()
    
    await ctx.report_progress(progress=50, total=100)

    # Этап 3: Обработка результатов (50-75%)
    await ctx.info("📄 Этап 3: Обрабатываем полученные результаты")
    processed_data = {
        "items": api_data.get("items", []),
        "total": len(api_data.get("items", []))
    }
    await ctx.report_progress(progress=75, total=100)

    # Этап 4: Форматирование ответа (75-100%)
    await ctx.info("📝 Этап 4: Форматируем финальный ответ")
    formatted_result = f"Найдено результатов: {processed_data['total']}\n\n"
    formatted_result += "\n".join([
        f"- {item.get('title', 'Без названия')}"
        for item in processed_data["items"][:10]
    ])
    await ctx.report_progress(progress=100, total=100)

    # Завершение (100%)
    await ctx.info("🎉 Операция завершена успешно")
    
    return ToolResult(
        content=[TextContent(type="text", text=formatted_result)],
        structured_content={"result": processed_data},
        meta={"query": query}
    )


Рекомендуемые этапы:
0% - Начало процесса
25% - Первый этап (например, аутентификация)
50% - Второй этап (например, запрос к API)
75% - Третий этап (например, обработка результатов)
100% - Завершение

Трейсинг и мониторинг
6.1 OpenTelemetry трейсинг
ВСЕГДА создавайте спаны для основных операций:
Примечание: Все блоки кода в этом разделе написаны на Python.

from fastmcp import Context
from pydantic import Field
from mcp.types import TextContent
from opentelemetry import trace
from .utils import ToolResult

tracer = trace.get_tracer(__name__)

@mcp.tool()
async def my_tool(
    operation_param: str = Field(
        ..., 
        description="Параметр для выполнения операции"
    ),
    ctx: Context = None
) -> ToolResult:
    """
    Пример инструмента с OpenTelemetry трейсингом.
    
    Args:
        operation_param: Параметр операции
        ctx: Контекст для логирования
        
    Returns:
        ToolResult: Результат выполнения операции
    """
    with tracer.start_as_current_span("my_tool") as span:
        # Настройка атрибутов спана для трейсинга
        span.set_attribute("operation_param", operation_param)
        span.set_attribute("param_length", len(operation_param))
        
        await ctx.info(f"🚀 Начинаем операцию с параметром: {operation_param}")
        
        # Выполнение API запроса
        import httpx
        import os
        
        api_key = os.getenv("API_KEY")
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                "https://api.example.com/process",
                json={"param": operation_param},
                headers={"Authorization": f"Bearer {api_key}"}
            )
            response.raise_for_status()
            result = response.json()
        
        # Установка атрибутов результата в спан
        span.set_attribute("success", True)
        span.set_attribute("response_status", response.status_code)
        span.set_attribute("result_length", len(str(result)))
        
        await ctx.info("✅ Операция завершена успешно")
        
        return ToolResult(
            content=[TextContent(type="text", text=str(result))],
            structured_content={"result": result, "param": operation_param},
            meta={"operation": "my_tool"}
        )



6.2 Вложенные спаны
Для сложных операций создавайте вложенные спаны:

from opentelemetry import trace

tracer = trace.get_tracer(__name__)

# Пример создания вложенных спанов для сложных операций
with tracer.start_as_current_span("main_operation") as main_span:
    # Атрибуты основного спана
    main_span.set_attribute("operation", "main")
    main_span.set_attribute("operation_type", "complex")
    
    # Вложенный спан для подоперации (например, аутентификация)
    with tracer.start_as_current_span("sub_operation") as sub_span:
        sub_span.set_attribute("sub_operation", "auth")
        sub_span.set_attribute("sub_operation_type", "authentication")
        
        # Выполняем подоперацию
        result = await authenticate()
        
        # Устанавливаем результат в подспан
        sub_span.set_attribute("success", True)
        sub_span.set_attribute("auth_result", "success" if result else "failed")
    
    # Устанавливаем результат в основной спан
    main_span.set_attribute("success", True)
    main_span.set_attribute("sub_operations_count", 1)



6.4 OpenInference трейсинг (опционально)
РЕКОМЕНДУЕТСЯ использовать OpenInference стандарт для трейсинга LLM операций, если ваш MCP сервер использует языковые модели.
OpenInference - это стандарт атрибутов OpenTelemetry для трейсинга LLM операций, который позволяет лучше отслеживать работу с языковыми моделями. Используйте этот раздел только если ваш сервер действительно работает с LLM.
Установка пакета openinference
pip install openinference-semantic-conventions
Или добавьте в pyproject.toml:
[project]
dependencies = [
    "openinference-semantic-conventions>=1.0.0",
]
Использование атрибутов из пакета openinference
ВСЕГДА используйте константы из пакета openinference-semantic-conventions вместо строковых литералов:

from fastmcp import Context
from pydantic import Field
from mcp.types import TextContent
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from openinference_semantic_conventions import GEN_AI
from .utils import ToolResult

tracer = trace.get_tracer(__name__)

@mcp.tool()
async def search_api_tool(
    query: str = Field(
        ..., 
        description="Поисковый запрос для API"
    ),
    api_endpoint: str = Field(
        default="https://api.example.com/search",
        description="URL эндпоинта API для поиска"
    ),
    ctx: Context = None
) -> ToolResult:
    """
    Инструмент с API вызовом и OpenTelemetry трейсингом.
    
    Args:
        query: Поисковый запрос пользователя
        api_endpoint: URL эндпоинта API (по умолчанию: https://api.example.com/search)
        ctx: Контекст для логирования
        
    Returns:
        ToolResult: Результат выполнения API запроса
    """
    import httpx
    import os
    
    with tracer.start_as_current_span("search_api_operation") as span:
        # Атрибуты спана для трейсинга
        span.set_attribute("api_endpoint", api_endpoint)
        span.set_attribute("query", query)
        span.set_attribute("query_length", len(query))
        
        await ctx.info(f"🚀 Отправляем запрос к API: {api_endpoint}")
        
        try:
            # Получаем API ключ из переменных окружения
            api_key = os.getenv("API_KEY")
            if not api_key:
                raise ValueError("API_KEY не установлен в переменных окружения")
            
            # API вызов
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    api_endpoint,
                    params={"q": query},
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                
                response.raise_for_status()
                result = response.json()
            
            # Атрибуты ответа в спан
            span.set_attribute("response_status", response.status_code)
            span.set_attribute("results_count", len(result.get("items", [])))
            span.set_attribute("success", True)
            
            await ctx.info(f"✅ Получен ответ от API: {len(result.get('items', []))} результатов")
            
            span.set_status(Status(StatusCode.OK))
            
            # Форматируем результат
            formatted_results = "\n".join([
                f"- {item.get('title', 'Без названия')}: {item.get('description', '')}"
                for item in result.get("items", [])[:10]
            ])
            
            return ToolResult(
                content=[TextContent(
                    type="text", 
                    text=f"Найдено результатов: {len(result.get('items', []))}\n\n{formatted_results}"
                )],
                structured_content={
                    "query": query,
                    "endpoint": api_endpoint,
                    "results": result.get("items", []),
                    "total": len(result.get("items", []))
                },
                meta={"api_endpoint": api_endpoint, "query": query}
            )
            
        except httpx.HTTPStatusError as e:
            await ctx.error(f"❌ HTTP ошибка при вызове API: {e.response.status_code}")
            span.set_attribute("error", "http_status_error")
            span.set_attribute("status_code", e.response.status_code)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise
        except Exception as e:
            await ctx.error(f"❌ Ошибка при вызове API: {e}")
            span.set_attribute("error", str(e))
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise



Основные константы OpenInference
Основные константы из пакета openinference-semantic-conventions (доступны через GEN_AI):
GEN_AI.OPERATION_NAME - название операции (chat_completion, embedding, etc.)
GEN_AI.SYSTEM - система LLM (openai, anthropic, etc.)
GEN_AI.REQUEST_MODEL - модель запроса
GEN_AI.RESPONSE_MODEL - модель ответа
GEN_AI.RESPONSE_FINISH_REASON - причина завершения
GEN_AI.USAGE_PROMPT_TOKENS - токены промпта
GEN_AI.USAGE_COMPLETION_TOKENS - токены ответа
GEN_AI.USAGE_TOTAL_TOKENS - общее количество токенов
Почему использовать константы:
✅ Избегаем опечаток в именах атрибутов
✅ Автодополнение в IDE
✅ Проверка типов
✅ Единообразие с официальным стандартом
Переменные окружения для OpenInference
OpenInference использует те же переменные окружения, что и OpenTelemetry:
# OpenTelemetry endpoint для экспорта трейсов
OTEL_ENDPOINT=http://jaeger:4318/v1/traces
OTEL_SERVICE_NAME=mcp-server
Примечание: OpenInference - это стандарт атрибутов OpenTelemetry для LLM операций. Используйте пакет openinference-semantic-conventions для получения констант атрибутов через объект GEN_AI вместо ручного написания строковых литералов. Это обеспечивает типобезопасность и избегает опечаток.
6.5 Prometheus метрики
РЕКОМЕНДУЕТСЯ добавлять метрики для мониторинга:
# metrics.py
from prometheus_client import Counter

API_CALLS = Counter(
    "api_calls_total",
    "Total number of API calls",
    ["service", "endpoint", "status"]
)

AUTH_ATTEMPTS = Counter(
    "auth_attempts_total",
    "Total number of authentication attempts",
    ["status"]
)


# В инструменте
from fastmcp import Context
from pydantic import Field
from mcp.types import TextContent
from .utils import ToolResult
from metrics import API_CALLS

@mcp.tool()
async def my_tool(
    operation_param: str = Field(
        ..., 
        description="Параметр для выполнения операции"
    ),
    ctx: Context = None
) -> ToolResult:
    API_CALLS.labels(
        service="mcp",
        endpoint="my_tool",
        status="started"
    ).inc()
    
    try:
        result = await perform_operation(operation_param)
        API_CALLS.labels(
            service="mcp",
            endpoint="my_tool",
            status="success"
        ).inc()
        
        return ToolResult(
            content=[TextContent(type="text", text=str(result))],
            structured_content={"result": result},
            meta={"param": operation_param}
        )
    except Exception as e:
        API_CALLS.labels(
            service="mcp",
            endpoint="my_tool",
            status="error"
        ).inc()
        raise



Обработка ошибок
7.1 Использование McpError
ВСЕГДА используйте McpError для пользовательских ошибок:

from fastmcp import Context
from pydantic import Field
from mcp.types import TextContent
from mcp.shared.exceptions import McpError, ErrorData
from .utils import ToolResult
import httpx

@mcp.tool()
async def my_tool(
    api_endpoint: str = Field(
        ..., 
        description="URL эндпоинта для запроса"
    ),
    request_data: str = Field(
        default="",
        description="Данные для отправки в запросе"
    ),
    ctx: Context = None
) -> ToolResult:
    try:
        result = await perform_operation(api_endpoint, request_data)
        
        return ToolResult(
            content=[TextContent(type="text", text=str(result))],
            structured_content={"result": result},
            meta={"endpoint": api_endpoint}
        )
    except ValueError as e:
        await ctx.error(f"❌ Ошибка валидации: {e}")
        raise McpError(
            ErrorData(
                code=-32602,  # Invalid params
                message=f"Неверный параметр: {e}"
            )
        )
    except httpx.HTTPStatusError as e:
        await ctx.error(f"❌ HTTP ошибка: {e.response.status_code}")
        raise McpError(
            ErrorData(
                code=-32603,  # Internal error
                message=f"Ошибка при запросе к API: {e.response.status_code}"
            )
        )




7.2 Коды ошибок MCP
Используйте стандартные коды ошибок:
-32600 - Invalid Request
-32601 - Method not found
-32602 - Invalid params
-32603 - Internal error
-32700 - Parse error
7.3 Форматирование ошибок API
Создавайте понятные сообщения об ошибках:
def format_api_error(response_text: str, status_code: int) -> str:
    """
    Форматирует ошибку API в понятное сообщение.
    
    Args:
        response_text: Текст ответа от API
        status_code: HTTP статус код
        
    Returns:
        Отформатированное сообщение об ошибке
    """
    import json
    
    try:
        error_data = json.loads(response_text)
        code = error_data.get("code", "unknown")
        message = error_data.get("message", response_text)
        
        error_msg = f"Ошибка API (код {code}): {message}"
        
        # Специальная обработка для разных статус кодов
        if status_code == 401:
            error_msg = (
                "Ошибка аутентификации.\n\n"
                "Что можно сделать:\n"
                "- Проверьте учетные данные\n"
                f"Детали: {message}"
            )
        
        return error_msg
    except json.JSONDecodeError:
        return f"Ошибка API (статус {status_code}): {response_text}"



Конфигурация
8.1 Переменные окружения
ВСЕГДА читайте конфигурацию из переменных окружения:
import os
from dotenv import load_dotenv, find_dotenv

# Загрузка переменных окружения
load_dotenv(find_dotenv())

# Константы с дефолтными значениями
PORT = int(os.getenv("PORT", "8000"))
API_URL = os.getenv("API_URL", "https://api.example.com")
TIMEOUT = float(os.getenv("TIMEOUT", "30.0"))
8.2 Валидация переменных окружения
Создавайте утилиты для валидации:

# tools/utils.py
def _require_env_vars(names: list[str]) -> dict[str, str]:
    """
    Проверяет наличие обязательных переменных окружения.
    
    Args:
        names: Список имен переменных окружения
        
    Returns:
        Словарь с переменными окружения
        
    Raises:
        McpError: Если отсутствуют обязательные переменные
    """
    missing = [n for n in names if not os.getenv(n)]
    if missing:
        from mcp.shared.exceptions import McpError, ErrorData
        raise McpError(
            ErrorData(
                code=-32602,
                message="Отсутствуют обязательные переменные окружения: " + ", ".join(missing)
            )
        )
    return {n: os.getenv(n, "") for n in names}



8.3 Парсинг значений
Создавайте утилиты для парсинга:
def _parse_int(value: str | None, default: int, min_value: int = 1) -> int:
    """Парсит целое число из переменной окружения."""
    if value is None:
        return default
    try:
        parsed = int(value)
        if parsed < min_value:
            return default
        return parsed
    except (TypeError, ValueError):
        return default

def _parse_float(value: str | None, default: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    """Парсит вещественное число из переменной окружения."""
    if value is None:
        return default
    try:
        parsed = float(value)
        if parsed < min_value or parsed > max_value:
            return default
        return parsed
    except (TypeError, ValueError):
        return default
8.4 Файл .env.example
ВСЕГДА создавайте файл .env.example с описанием всех переменных:
# Обязательные переменные
API_KEY=your_api_key_here
PROJECT_ID=your_project_id

# Опциональные переменные
PORT=8000
TIMEOUT=30.0
LOG_LEVEL=INFO
8.5 Файл env_options.json
РЕКОМЕНДУЕТСЯ создавать файл env_options.json для автоматической генерации документации:
{
  "rawEnvs": {
    "KNOWLEDGE_BASE_ID": {
      "isRequired": true,
      "description": "ID базы знаний"
    },
    "RETRIEVAL_NUMBER_OF_RESULTS": {
      "isRequired": false,
      "description": "Количество чанков из поисковой выдачи (по умолчанию: 3)",
      "defaultValue": "3"
    },
    "PORT": {
      "isRequired": false,
      "description": "Порт MCP сервера",
      "defaultValue": "8000"
    }
  },
  "secretEnvs": {
    "API_KEY": {
      "isRequired": true,
      "description": "API ключ для доступа к сервису"
    },
    "EVOLUTION_SERVICE_ACCOUNT_KEY_SECRET": {
      "isRequired": true,
      "description": "Секрет сервисного аккаунта Evolution"
    }
  }
}
Структура файла:
rawEnvs (object, обязательное) - объект с обычными переменными окружения
Каждая переменная содержит:
isRequired (boolean, обязательное) - является ли переменная обязательной
description (string, обязательное) - описание переменной
defaultValue (string, опциональное) - значение по умолчанию
secretEnvs (object, обязательное) - объект с секретными переменными окружения
Структура такая же, как у rawEnvs
Используется для переменных, содержащих секреты (API ключи, пароли и т.д.)
Важно:
Обязательные переменные должны иметь "isRequired": true
Опциональные переменные должны иметь "isRequired": false
Секретные переменные всегда должны быть в secretEnvs, а не в rawEnvs


Документация
10.1 README.md
ВСЕГДА создавайте подробный README.md:

## MCP Server Name

Описание сервера и его возможностей.

### 🚀 Возможности

- Инструмент 1 - описание
- Инструмент 2 - описание

### 📋 Требования

- Python 3.12+
- Зависимости из pyproject.toml

### 🔧 Переменные окружения

#### Обязательные переменные

- `API_KEY` - API ключ для доступа

#### Необязательные переменные

- `PORT` - Порт сервера (по умолчанию: 8000)

### 🚀 Локальный запуск

1. Установите зависимости:
```bash
uv sync

Создайте файл .env:
cp .env.example .env
# Отредактируйте .env файл

Запустите сервер:
uv run python server.py




📖 Использование инструментов
tool_name - Описание
Используется для...
Параметры:
param1 (str) - Описание параметра
Возвращает: Описание возвращаемого значения
### 10.2 MCP Tools JSON **РЕКОМЕНДУЕТСЯ** создавать файл `mcp_tools.json` с JSON описанием всех инструментов:
```json
[
  {
    "name": "tool_name",
    "description": "📝 Подробное описание инструмента. Что делает, какие проблемы решает.",
    "args": [
      {
        "name": "param1",
        "type": "string",
        "description": "Описание параметра 1"
      },
      {
        "name": "param2",
        "type": "integer",
        "description": "Описание параметра 2"
      }
    ]
  },
  {
    "name": "another_tool",
    "description": "Описание другого инструмента",
    "args": [
      {
        "name": "query",
        "type": "string",
        "description": "Поисковый запрос"
      }
    ]
  }
]


Структура объекта инструмента:
name (string, обязательное) - имя инструмента (должно совпадать с именем функции)
description (string, обязательное) - подробное описание инструмента
args (array, обязательное) - массив параметров инструмента
name (string) - имя параметра
type (string) - тип параметра: string, integer, number, boolean, array, object
description (string) - описание параметра
Почему: mcp_tools.json используется для автоматической генерации документации, интеграции с внешними системами и валидации инструментов.
Важно: После добавления или изменения инструмента обновляйте mcp_tools.json синхронно с кодом.
10.3 MCP Server Catalog
ВСЕГДА создавайте файл mcp-server-catalog.yaml:

# Конфигурация MCP сервера
id: "unique-server-id"
name: "Server Name"
description: |
  "Подробное описание сервера и его возможностей"
tools:
  - name: "tool_name"
    description: "Описание инструмента"
    parameters:
      param1: "string - Описание параметра"
rawEnvs:
  PORT:
    isRequired: false
    description: "Порт сервера"
secretEnvs:
  API_KEY:
    isRequired: true
    description: "API ключ"
image_uri: ${IMAGE_URI}
license_url: "https://example.com/license"
tags: ["tag1", "tag2"]
category: "Category"
versions: ["1.0.0"]
exposed_ports:
  - port: 8000
    protocol: "HTTP"
status: "MCP_SERVER_PREDEFINED_STATUS_AVAILABLE"
type: "MCP_SERVER_PREDEFINED_TYPE_INTERNAL"



10.4 Docstrings
ВСЕГДА добавляйте docstrings в формате Google Style, они будут отображаться как описание тула и поможет лучше понять LLM как этим пользоваться, но не злоупотребляйте чтобы не захламлять контекст:

def function_name(param1: str, param2: int) -> str:
    """
    Краткое описание функции.
    
    Подробное описание функции, что она делает, какие проблемы решает.
    
    Args:
        param1: Описание параметра 1
        param2: Описание параметра 2
        
    Returns:
        Описание возвращаемого значения
        
    Raises:
        ValueError: Когда возникает ошибка валидации
        
    Examples:
        >>> result = function_name("value", 10)
        >>> print(result)
        "result"
    """
    pass




Чеклист перед коммитом
Перед передачей MCP-сервера убедитесь, что:
[ ] Все инструменты имеют docstrings
[ ] Все функции используют type hints
[ ] Используется Context для логирования
[ ] Реализованы прогресс-отчеты для длительных операций
[ ] Созданы OpenTelemetry спаны для основных операций
[ ] Добавлены OpenInference атрибуты для LLM операций (если используются LLM операции)
[ ] Обработка ошибок через McpError
[ ] Переменные окружения валидируются
[ ] Обновлен README.md
[ ] Обновлен mcp_tools.json
[ ] Обновлен mcp-server-catalog.yaml
[ ] Все тесты проходят
[ ] Код соответствует стилю проекта

Примеры
Полный пример инструмента
"""Инструмент для выполнения операции."""

import os
from typing import Dict, Any

import httpx
from fastmcp import Context
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field

from mcp_instance import mcp
from .utils import ToolResult, _require_env_vars, format_api_error
from metrics import API_CALLS

tracer = trace.get_tracer(__name__)


@mcp.tool(
    name="my_tool",
    description="""📝 Описание инструмента.

Что делает инструмент, какие проблемы решает.
"""
)
async def my_tool(
    query: str = Field(
        ..., 
        description="Поисковый запрос"
    ),
    ctx: Context = None
) -> ToolResult:
    """
    📝 Выполняет операцию.
    
    Args:
        query: Поисковый запрос
        ctx: Контекст для логирования
        
    Returns:
        ToolResult: Результат выполнения
        
    Raises:
        McpError: При ошибках выполнения
    """
    with tracer.start_as_current_span("my_tool") as span:
        span.set_attribute("query", query)
        
        await ctx.info("🚀 Начинаем выполнение инструмента")
        await ctx.report_progress(progress=0, total=100)
        
        API_CALLS.labels(
            service="mcp",
            endpoint="my_tool",
            status="started"
        ).inc()
        
        try:
            # Валидация переменных окружения
            env = _require_env_vars(["API_KEY"])
            
            # Этап 1: Подготовка (0-25%)
            await ctx.info("🔧 Подготавливаем запрос")
            await ctx.report_progress(progress=25, total=100)
            
            # Этап 2: Выполнение запроса (25-75%)
            await ctx.info("📡 Отправляем запрос к API")
            await ctx.report_progress(progress=50, total=100)
            
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    "https://api.example.com/endpoint",
                    json={"query": query},
                    headers={"Authorization": f"Bearer {env['API_KEY']}"}
                )
                
                response.raise_for_status()
                result = response.json()
            
            await ctx.report_progress(progress=75, total=100)
            
            # Этап 3: Обработка результатов (75-100%)
            await ctx.info("📄 Обрабатываем результаты")
            
            formatted_result = format_result(result)
            
            await ctx.report_progress(progress=100, total=100)
            await ctx.info("✅ Операция завершена успешно")
            
            span.set_attribute("success", True)
            span.set_attribute("results_count", len(result.get("items", [])))
            
            API_CALLS.labels(
                service="mcp",
                endpoint="my_tool",
                status="success"
            ).inc()
            
            return ToolResult(
                content=[TextContent(type="text", text=formatted_result)],
                structured_content=result,
                meta={"query": query}
            )
            
        except httpx.HTTPStatusError as e:
            span.set_attribute("error", "http_status_error")
            span.set_attribute("status_code", e.response.status_code)
            
            error_message = format_api_error(
                e.response.text if e.response else "",
                e.response.status_code if e.response else 0
            )
            
            await ctx.error(f"❌ HTTP ошибка: {error_message}")
            
            API_CALLS.labels(
                service="mcp",
                endpoint="my_tool",
                status="error"
            ).inc()
            
            from mcp.shared.exceptions import McpError, ErrorData
            raise McpError(
                ErrorData(
                    code=-32603,
                    message=f"Не удалось выполнить операцию.\n\n{error_message}"
                )
            )
        except Exception as e:
            span.set_attribute("error", str(e))
            await ctx.error(f"💥 Неожиданная ошибка: {e}")
            
            API_CALLS.labels(
                service="mcp",
                endpoint="my_tool",
                status="error"
            ).inc()
            
            from mcp.shared.exceptions import McpError, ErrorData
            raise McpError(
                ErrorData(
                    code=-32603,
                    message=f"Неожиданная ошибка: {e}"
                )
            )



Заключение
Этот стандарт обеспечивает:
✅ Единообразие кода во всех MCP серверах
✅ Легкость поддержки и развития
✅ Наблюдаемость и мониторинг
✅ Правильную обработку ошибок
✅ Полную документацию
Следуйте этому стандарту при создании новых MCP серверов и обновлении существующих.
 

