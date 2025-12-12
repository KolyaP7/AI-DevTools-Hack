"""Инструмент для извлечения аудио из видео файла."""

import os
import subprocess
from typing import Dict, Any

from fastmcp import Context
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field

from ..mcp_instance import mcp
from .utils import ToolResult
from ..globals import VIDEO_PATH

# OpenTelemetry tracer
tracer = trace.get_tracer(__name__)


@mcp.tool(
    name="extract_audio_from_video",
    description="""🎵 Инструмент для извлечения аудио дорожки из видео файла.
    """
)
async def extract_audio_from_video(
    video_file: str = Field(
        ...,
        description="Имя видео файла"
    ),
    output_file: str = Field(
        ...,
        description="Имя выходного аудио файла"
    ),
    ctx: Context = None
) -> ToolResult:
    """
    Извлекает аудио дорожку из видео файла.

    Args:
        video_file: Имя видео файла
        output_file: Имя выходного аудио файла

    Returns:
        ToolResult с информацией об извлеченном аудио.

    Raises:
        McpError: Если входные данные некорректны или произошла ошибка извлечения.
    """
    with tracer.start_as_current_span("extract_audio_from_video") as span:
        span.set_attribute("video_file", video_file)
        span.set_attribute("output_file", output_file)

        if ctx:
            await ctx.info("🚀 extract_audio_from_video started")
            await ctx.report_progress(progress=0, total=100)

        try:
            video_path = os.path.join(VIDEO_PATH, video_file)
            output_path = os.path.join(VIDEO_PATH, output_file)

            if not os.path.exists(video_path):
                raise Exception(f"Видео файл не найден: {video_path}")

            # Извлекаем аудио из видео
            extract_cmd = [
                "ffmpeg", "-i", video_path, "-vn", "-acodec", "pcm_s16le",
                "-ar", "22050", "-ac", "1", "-y", output_path
            ]

            result = subprocess.run(extract_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Ошибка извлечения аудио: {result.stderr}")

            if ctx:
                await ctx.report_progress(progress=100, total=100)
                await ctx.info(f"✅ Аудио извлечено: {output_file}")

            result_data = {
                "video_file": video_file,
                "output_file": output_file,
                "status": "extracted"
            }

            return ToolResult(
                content=[TextContent(type="text", text=f"Audio extracted: {output_file}")],
                structured_content=result_data,
                meta={"video_file": video_file, "output_file": output_file}
            )

        except Exception as e:
            span.set_attribute("error", str(e))
            if ctx:
                await ctx.error(f"❌ Ошибка выполнения: {e}")

            from mcp.shared.exceptions import McpError, ErrorData
            raise McpError(
                ErrorData(
                    code=-32603,
                    message=f"Не удалось выполнить операцию: {e}"
                )
            )