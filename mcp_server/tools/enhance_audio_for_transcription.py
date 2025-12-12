"""Инструмент для улучшения характеристик аудио для лучшего распознавания речи."""

import os
import subprocess
import sys
from typing import Dict, Any

import httpx
from fastmcp import Context
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field

from ..mcp_instance import mcp
from .utils import ToolResult, _require_env_vars, format_api_error
from ..globals import VIDEO_PATH
# OpenTelemetry tracer
tracer = trace.get_tracer(__name__)


@mcp.tool(
    name="enhance_audio_for_transcription",
    description="""🎵 Инструмент для улучшения характеристик аудио перед распознаванием речи.

    Применяет аудиофильтры FFmpeg для улучшения качества звука:
    - Нормализация громкости
    - Компрессия динамического диапазона
    - Усиление тихих звуков

    Используется исключительно для улучшения распознавания текста,
    оригинальная аудиодорожка сохраняется для финального видео.
    """
)
async def enhance_audio_for_transcription(
    input_audio: str = Field(
        ...,
        description="Путь к входному аудиофайлу"
    ),
    output_audio: str = Field(
        ...,
        description="Путь к выходному аудиофайлу с улучшенными характеристиками"
    ),
    ctx: Context = None
) -> ToolResult:
    """
    Улучшает характеристики аудио для лучшего распознавания речи.

    Args:
        input_audio: Путь к входному аудиофайлу
        output_audio: Путь к выходному файлу
        ctx: Контекст для логирования

    Returns:
        ToolResult с информацией об обработке
    """
    with tracer.start_as_current_span("enhance_audio_for_transcription") as span:
        # Настройка атрибутов спана
        span.set_attribute("input_audio", input_audio)
        span.set_attribute("output_audio", output_audio)

        # Логирование начала операции
        if ctx:
            await ctx.info("🎵 Начинаю улучшение характеристик аудио...")
            await ctx.report_progress(progress=0, total=100)
        else:
            print("🎵 Начинаю улучшение характеристик аудио...", file=sys.stderr)

        try:
            input_path = os.path.join(VIDEO_PATH, input_audio)
            output_path = os.path.join(VIDEO_PATH, output_audio)

            if not os.path.exists(input_path):
                raise Exception(f"Входной аудиофайл не найден: {input_path}")

            # Создаем директорию для выходного файла если нужно
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            print(f"🔊 Обрабатываю аудио: {input_path}", file=sys.stderr)
            print(f"📤 Выходной файл: {output_path}", file=sys.stderr)

            # Оптимальная простая цепочка фильтров для улучшения распознавания речи
            # acompressor - адаптивный компрессор для усиления тихих звуков
            # loudnorm - нормализация громкости
            audio_filter = "acompressor=threshold=-30dB:ratio=20:attack=1:release=100:makeup=12dB:knee=8:mix=1,loudnorm"

            cmd = [
                "ffmpeg",
                "-i", input_path,
                "-af", audio_filter,
                "-c:a", "mp3",  # Выход в MP3 для совместимости
                "-b:a", "128k",  # Битрейт
                "-y",  # Перезаписать выходной файл
                output_path
            ]

            print(f"🎛️  Применяю фильтр: {audio_filter}", file=sys.stderr)

            if ctx:
                await ctx.info("🎛️ Применяю аудиофильтры...")
                await ctx.report_progress(progress=25, total=100)
            else:
                print("🎛️ Применяю аудиофильтры...", file=sys.stderr)

            # Запускаем FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=VIDEO_PATH
            )

            if result.returncode != 0:
                error_msg = f"Ошибка FFmpeg: {result.stderr}"
                print(f"❌ {error_msg}", file=sys.stderr)
                raise Exception(error_msg)

            print("✅ Аудио успешно обработано", file=sys.stderr)

            # Проверяем размер выходного файла
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"📊 Размер выходного файла: {file_size} байт", file=sys.stderr)

                if ctx:
                    await ctx.info("✅ Аудио обработано успешно")
                    await ctx.report_progress(progress=100, total=100)
                else:
                    print("✅ Аудио обработано успешно", file=sys.stderr)

                return ToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"Аудио успешно обработано для улучшения распознавания речи. Выходной файл: {output_audio}"
                    )],
                    structured_content={
                        "input_audio": input_audio,
                        "output_audio": output_audio,
                        "filter_applied": audio_filter,
                        "file_size": file_size
                    },
                    meta={
                        "input_audio": input_audio,
                        "output_audio": output_audio,
                        "processing_type": "audio_enhancement_for_transcription"
                    }
                )
            else:
                raise Exception("Выходной файл не был создан")

        except Exception as e:
            span.set_attribute("error", str(e))
            if ctx:
                await ctx.error(f"❌ Ошибка обработки аудио: {e}")
            else:
                print(f"❌ Ошибка обработки аудио: {e}", file=sys.stderr)

            from mcp.shared.exceptions import McpError, ErrorData
            raise McpError(
                ErrorData(
                    code=-32603,
                    message=f"Не удалось обработать аудио: {e}"
                )
            )