"""Инструмент для вырезания сегментов из видео и наложения губ на каждый сегмент с использованием Wav2Lip."""

import os
import subprocess
from typing import Dict, Any, List

from fastmcp import Context
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field

from mcp_instance import mcp
from tools.utils import ToolResult, _require_env_vars, format_api_error
from globals import VIDEO_PATH
# OpenTelemetry tracer
tracer = trace.get_tracer(__name__)


@mcp.tool(
    name="cut_and_overlay_lips",
    description="""🎬 Инструмент для вырезания сегментов из видео и наложения губ (lip-sync) на каждый сегмент с использованием Wav2Lip.
    """
)
async def cut_and_overlay_lips(
    video_file: str = Field(
        ...,
        description="Имя входного видеофайла"
    ),
    audio_file: str = Field(
        ...,
        description="Имя аудиофайла для синхронизации"
    ),
    segments: List[Dict[str, Any]] = Field(
        ...,
        description="Список сегментов: [{'start': float, 'end': float, 'output_name': str}]"
    ),
    ctx: Context = None
) -> ToolResult:
    """
    Вырезает сегменты из видео и применяет lip-sync к каждому сегменту.

    Использует ffmpeg для вырезания сегментов и Wav2Lip для синхронизации губ.

    Args:
        video_file: Входной видеофайл
        audio_file: Аудиофайл для синхронизации
        segments: Список сегментов с start, end, output_name

    Returns:
        ToolResult с информацией о обработанных сегментах.

    Examples:
        >>> segments = [{"start": 0, "end": 5, "output_name": "synced_0_5.mp4"}]
        >>> result = await cut_and_overlay_lips(video_file="input.mp4", audio_file="speech.wav", segments=segments, ctx)
    """
    with tracer.start_as_current_span("cut_and_overlay_lips") as span:
        span.set_attribute("video_file", video_file)
        span.set_attribute("audio_file", audio_file)

        await ctx.info("🚀 cut_and_overlay_lips started")
        await ctx.report_progress(progress=0, total=100)

        try:
            video_path = os.path.join(VIDEO_PATH, video_file)
            audio_path = os.path.join(VIDEO_PATH, audio_file)

            # Проверка существования файлов
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video file not found: {video_path}")
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")

            synced_segments = []

            total_segments = len(segments)
            for i, seg in enumerate(segments):
                start = seg["start"]
                end = seg["end"]
                output_name = seg.get("output_name", f"synced_{start}_{end}.mp4")
                output_path = os.path.join(VIDEO_PATH, output_name)

                # Вырезать сегмент видео
                temp_video = os.path.join(VIDEO_PATH, f"temp_segment_{i}.mp4")
                cmd_cut = [
                    "ffmpeg", "-i", video_path, "-ss", str(start), "-t", str(end - start),
                    "-c", "copy", temp_video
                ]
                subprocess.run(cmd_cut, check=True)

                # Вырезать соответствующий сегмент аудио
                temp_audio = os.path.join(VIDEO_PATH, f"temp_audio_{i}.wav")
                cmd_cut_audio = [
                    "ffmpeg", "-i", audio_path, "-ss", str(start), "-t", str(end - start),
                    "-acodec", "pcm_s16le", "-ar", "16000", temp_audio
                ]
                subprocess.run(cmd_cut_audio, check=True)

                # Запуск Wav2Lip
                cmd_wav2lip = [
                    "python", "inference.py",  # Путь к inference.py Wav2Lip
                    "--checkpoint_path", "wav2lip.pth",  # Путь к модели
                    "--face", temp_video,
                    "--audio", temp_audio,
                    "--outfile", output_path
                ]

                subprocess.run(cmd_wav2lip, check=True, cwd="/path/to/wav2lip")  # Указать путь к Wav2Lip

                # Очистка временных файлов
                os.remove(temp_video)
                os.remove(temp_audio)

                synced_segments.append({
                    "start": start,
                    "end": end,
                    "output_file": output_name
                })

                progress = int((i + 1) / total_segments * 100)
                await ctx.report_progress(progress=progress, total=100)

            result = {
                "video_file": video_file,
                "audio_file": audio_file,
                "synced_segments": synced_segments,
                "total_segments": len(synced_segments),
                "status": "success"
            }

            return ToolResult(
                content=[TextContent(type="text", text=f"Cut and overlaid lips on {len(synced_segments)} segments")],
                structured_content=result,
                meta={"video_file": video_file, "audio_file": audio_file}
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