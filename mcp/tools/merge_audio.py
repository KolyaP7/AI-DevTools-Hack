"""Макет инструмента для объединения аудио."""

import os
from typing import Dict, Any

from fastmcp import Context
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field

from mcp_instance import mcp
from tools.utils import ToolResult
from globals import VIDEO_PATH

tracer = trace.get_tracer(__name__)

@mcp.tool(
    name="merge_audio",
    description="""🔊 Инструмент для объединения оригинального аудио с TTS аудио.
    """
)
async def merge_audio(
    original_audio_file: str = Field(
        ...,
        description="Оригинальный аудио файл сегмента"
    ),
    tts_audio_file: str = Field(
        ...,
        description="TTS аудио файл"
    ),
    name_start: float = Field(
        ...,
        description="Начало имени в секундах"
    ),
    name_end: float = Field(
        ...,
        description="Конец имени в секундах"
    ),
    output_file: str = Field(
        ...,
        description="Выходной файл"
    ),
    ctx: Context = None
) -> ToolResult:
    """
    Объединяет оригинальное аудио с TTS, заменяя часть с именем.

    Returns:
        ToolResult с output_file
    """
    with tracer.start_as_current_span("merge_audio") as span:
        span.set_attribute("original_audio_file", original_audio_file)
        span.set_attribute("tts_audio_file", tts_audio_file)
        span.set_attribute("output_file", output_file)

        await ctx.info("🚀 merge_audio started")

        try:
            output_path = os.path.join(VIDEO_PATH, output_file)

            # Mock: create dummy file
            with open(output_path, 'w') as f:
                f.write(f"# Merged audio: {original_audio_file} + {tts_audio_file}\n")

            result = {
                "output_file": output_file,
                "status": "merged"
            }

            return ToolResult(
                content=[TextContent(type="text", text=f"Audio merged: {output_file}")],
                structured_content=result,
                meta={"original_audio_file": original_audio_file, "tts_audio_file": tts_audio_file, "output_file": output_file}
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