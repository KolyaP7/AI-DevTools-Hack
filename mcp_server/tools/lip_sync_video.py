"""Инструмент для синхронизации губ на видео с использованием Wav2Lip."""

import os
import subprocess
from typing import Dict, Any

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
    name="lip_sync_video",
    description="""🎬 Инструмент для синхронизации губ на видео с использованием Wav2Lip.
    """
)
async def lip_sync_video(
    video_file: str = Field(
        ...,
        description="Имя входного видеофайла"
    ),
    audio_file: str = Field(
        ...,
        description="Имя аудиофайла для синхронизации"
    ),
    output_file: str = Field(
        ...,
        description="Имя выходного видеофайла"
    ),
    start_time: float = Field(
        0.0,
        description="Время начала сегмента (секунды)"
    ),
    end_time: float = Field(
        None,
        description="Время окончания сегмента (секунды), если None - до конца"
    ),
    ctx: Context = None
) -> ToolResult:
    """
    Синхронизирует губы на видео с аудио с использованием Wav2Lip.

    Инструмент принимает видеофайл, аудиофайл и параметры сегмента,
    применяет Wav2Lip для синхронизации губ и сохраняет результат.

    Returns:
        ToolResult:
            Контейнер с результатами. Поле `structured_content`
            содержит информацию о обработанном файле.

    Raises:
        McpError: Если входные данные некорректны или произошла ошибка обработки.

    Examples:
        >>> result = await lip_sync_video(video_file="face.mp4", audio_file="speech.wav", output_file="synced.mp4", ctx)
        >>> print(result.structured_content)
        {"output_file": "synced.mp4", "status": "success"}
    """
    with tracer.start_as_current_span("lip_sync_video") as span:
        # Настройка атрибутов спана
        span.set_attribute("video_file", video_file)
        span.set_attribute("audio_file", audio_file)
        span.set_attribute("output_file", output_file)

        # Логирование начала операции
        await ctx.info("🚀 lip_sync_video started")
        await ctx.report_progress(progress=0, total=100)

        try:
            video_path = os.path.join(VIDEO_PATH, video_file)
            audio_path = os.path.join(VIDEO_PATH, audio_file)
            output_path = os.path.join(VIDEO_PATH, output_file)

            # Проверка существования файлов
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video file not found: {video_path}")
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")

            # Если указан сегмент, вырезать его
            temp_video = video_path
            if end_time is not None:
                temp_video = os.path.join(VIDEO_PATH, f"temp_{video_file}")
                # Вырезать сегмент видео
                cmd_cut = [
                    "ffmpeg", "-i", video_path, "-ss", str(start_time), "-t", str(end_time - start_time),
                    "-c", "copy", temp_video
                ]
                subprocess.run(cmd_cut, check=True)

            # Запуск Wav2Lip
            # Предполагаем, что Wav2Lip установлен и доступен
            cmd_wav2lip = [
                "python", "inference.py",  # Путь к inference.py Wav2Lip
                "--checkpoint_path", "wav2lip.pth",  # Путь к модели
                "--face", temp_video,
                "--audio", audio_path,
                "--outfile", output_path
            ]

            await ctx.report_progress(progress=50, total=100)
            subprocess.run(cmd_wav2lip, check=True, cwd="/path/to/wav2lip")  # Указать путь к Wav2Lip

            # Очистка временных файлов
            if temp_video != video_path:
                os.remove(temp_video)

            result = {
                "output_file": output_file,
                "status": "success",
                "segment": {"start": start_time, "end": end_time}
            }

            await ctx.report_progress(progress=100, total=100)

            return ToolResult(
                content=[TextContent(type="text", text=f"Lip sync completed: {output_file}")],
                structured_content=result,
                meta={"video_file": video_file, "audio_file": audio_file, "output_file": output_file}
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