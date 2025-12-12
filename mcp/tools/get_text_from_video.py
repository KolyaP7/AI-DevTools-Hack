"""Инструмент для получения текста с временными меткамииз видео."""

import json

import os
import json
from typing import Dict, Any

import whisper

import httpx
from fastmcp import Context
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field


from mcp_instance import mcp
from tools.utils import ToolResult, _require_env_vars, format_api_error
from globals import WHISPER_MODEL, VIDEO_PATH
# OpenTelemetry tracer
tracer = trace.get_tracer(__name__)


@mcp.tool(
    name="get_text_from_video",
    description="""📝 Инструмент для получения текста с временными метками из видео.
"""
)
async def get_text_from_video(
    fileName: str = Field(
        ..., 
        description="Имя файла видео"
    ),
    ctx: Context = None
) -> ToolResult:
    """
    Получает текст с временными метками из видео.

    Инструмент принимает аудиофайл и возвращает текст с временными метками.

    Returns:
        ToolResult:
            Контейнер с результатами. Поле `structured_content`
            содержит массив слов в формате:

            [
                {
                    "text": str,    # Слово
                    "start": float, # Время начала (секунды)
                    "end": float    # Время окончания (секунды)
                }
            ]

    Raises:
        McpError: Если входные данные некорректны или произошла ошибка анализа.

    Examples:
        >>> result = await get_text_from_video(fileName="...", ctx)
        >>> print(result.structured_content)
        [
            {"text": "я", "start": 1.00, "end": 1.10},
            {"text": "поздравляю", "start": 1.10, "end": 1.80}
        ]
    """
    with tracer.start_as_current_span("get_text_from_video") as span:
        # Настройка атрибутов спана
        span.set_attribute("fileName", fileName)
        
        # Логирование начала операции
        await ctx.info("🚀 get_text_from_video started")
        await ctx.report_progress(progress=0, total=100)
        
        try:
            print("model loading...", end="")
            model = whisper.load_model(WHISPER_MODEL)
            print("done")
            print("transcribing...", end="")
            transcribe_result = model.transcribe(os.path.join(VIDEO_PATH, fileName))
            print("done")

            result = []
            for i in transcribe_result["segments"]:
                result.append({
                    "text": i["text"],
                    "start": i["start"],
                    "end": i["end"]
                })
                print("text: ", i["text"], "start: ", i["start"], "end: ", i["end"])




            json_result = json.dumps(result)


            return ToolResult(
                content=[TextContent(type="text", text=json_result)],
                structured_content={"result":result},
                meta={"fileName": fileName}
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

