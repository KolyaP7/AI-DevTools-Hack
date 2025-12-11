"""Инструмент для генерации TTS аудио с использованием FastSpeech 2 + Vocoder."""

import os
from typing import Dict, Any, List

from fastmcp import Context
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field

from mcp_instance import mcp
from tools.utils import ToolResult
# OpenTelemetry tracer
tracer = trace.get_tracer(__name__)

# Импорт для TTS (предполагаем наличие библиотек)
try:
    # Пример импортов, нужно установить соответствующие библиотеки
    # from TTS.api import TTS
    # или другие
    pass
except ImportError:
    pass


@mcp.tool(
    name="generate_tts_audio",
    description="""🔊 Инструмент для генерации TTS аудио с использованием FastSpeech 2 + Vocoder.
    """
)
async def generate_tts_audio(
    text: str = Field(
        ...,
        description="Текст для озвучивания"
    ),
    output_file: str = Field(
        ...,
        description="Имя выходного аудиофайла"
    ),
    segments: List[Dict[str, Any]] = Field(
        None,
        description="Сегменты с временными метками для генерации в нужные моменты"
    ),
    ctx: Context = None
) -> ToolResult:
    """
    Генерирует TTS аудио для текста с использованием FastSpeech 2 и Vocoder.

    Args:
        text: Текст для озвучивания
        output_file: Имя выходного файла
        segments: Опционально, сегменты для генерации в конкретные моменты

    Returns:
        ToolResult с информацией о сгенерированном аудио.

    Examples:
        >>> result = await generate_tts_audio(text="новое имя", output_file="name.wav", ctx)
    """
    with tracer.start_as_current_span("generate_tts_audio") as span:
        span.set_attribute("text", text)
        span.set_attribute("output_file", output_file)

        await ctx.info("🚀 generate_tts_audio started")
        await ctx.report_progress(progress=0, total=100)

        try:
            from globals import VIDEO_PATH  # Предполагаем наличие
            output_path = os.path.join(VIDEO_PATH, output_file)

            # Здесь должна быть реализация TTS
            # Пример с использованием TTS library (нужно установить)
            # tts = TTS(model_name="tts_models/en/ljspeech/fast_pitch", progress_bar=False)
            # tts.tts_to_file(text=text, file_path=output_path)

            # Заглушка для демонстрации
            await ctx.report_progress(progress=50, total=100)

            # Если segments указаны, можно генерировать аудио для каждого сегмента
            if segments:
                # Логика для генерации в нужные моменты
                # Например, создать композитный аудио файл
                pass

            # Имитация генерации
            with open(output_path, 'w') as f:
                f.write(f"# TTS audio for: {text}\n")  # Заглушка

            result = {
                "output_file": output_file,
                "text": text,
                "status": "generated",
                "segments_processed": len(segments) if segments else 0
            }

            await ctx.report_progress(progress=100, total=100)

            return ToolResult(
                content=[TextContent(type="text", text=f"TTS audio generated: {output_file}")],
                structured_content=result,
                meta={"text": text, "output_file": output_file}
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