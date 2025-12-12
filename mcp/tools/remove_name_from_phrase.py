"""Макет инструмента для удаления имени из фразы."""

from typing import Dict, Any

from fastmcp import Context
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field

from mcp_instance import mcp
from tools.utils import ToolResult

tracer = trace.get_tracer(__name__)

@mcp.tool(
    name="remove_name_from_phrase",
    description="""✂️ Инструмент для удаления имени из фразы поздравления.
    """
)
async def remove_name_from_phrase(
    phrase: str = Field(
        ...,
        description="Фраза, содержащая имя"
    ),
    name: str = Field(
        ...,
        description="Имя для удаления"
    ),
    ctx: Context = None
) -> ToolResult:
    """
    Удаляет имя из фразы и возвращает модифицированную фразу с позицией имени.

    Returns:
        ToolResult с modified_phrase, name_start, name_end
    """
    with tracer.start_as_current_span("remove_name_from_phrase") as span:
        span.set_attribute("phrase", phrase)
        span.set_attribute("name", name)

        await ctx.info("🚀 remove_name_from_phrase started")

        try:
            # Mock: find name in phrase
            lower_phrase = phrase.lower()
            lower_name = name.lower()
            start = lower_phrase.find(lower_name)
            if start == -1:
                modified_phrase = phrase
                name_start = -1
                name_end = -1
            else:
                name_end = start + len(name)
                modified_phrase = phrase[:start] + "[NAME]" + phrase[name_end:]

            result = {
                "modified_phrase": modified_phrase,
                "name_start": start,
                "name_end": name_end,
                "original_phrase": phrase
            }

            return ToolResult(
                content=[TextContent(type="text", text=f"Modified phrase: {modified_phrase}")],
                structured_content=result,
                meta={"phrase": phrase, "name": name}
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