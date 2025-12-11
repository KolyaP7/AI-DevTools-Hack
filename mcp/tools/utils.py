"""Общие утилиты для инструментов MCP."""

import os
from typing import Any, Dict, List

from mcp.types import TextContent
from mcp.shared.exceptions import McpError, ErrorData

from pydantic import BaseModel
from mcp.types import TextContent
from typing import Any, Dict, List, Optional

class ToolResult(BaseModel):
    """
    Результат инструмента MCP.
    """

    content: List[TextContent]
    structured_content: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None


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
        raise McpError(
            ErrorData(
                code=-32602,
                message="Отсутствуют обязательные переменные окружения: " + ", ".join(missing)
            )
        )
    return {n: os.getenv(n, "") for n in names}


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


def _parse_float(
    value: str | None, 
    default: float, 
    min_value: float = 0.0, 
    max_value: float = 1.0
) -> float:
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

