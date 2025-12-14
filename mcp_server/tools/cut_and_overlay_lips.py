"""Инструмент для вырезания сегментов из видео и наложения губ на каждый сегмент с использованием Wav2Lip."""

import os
import subprocess
import json
from typing import Dict, Any, List

from fastmcp import Context
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field

from ..globals import WAV2LIB_PATH, VIDEO_PATH
from ..mcp_instance import mcp
from .utils import ToolResult, _require_env_vars, format_api_error

from ..funcs.video import cut_video, get_audio_duration, change_video_speed
# OpenTelemetry tracer
tracer = trace.get_tracer(__name__)

import ffmpeg

def ensure_wav(audio_path: str) -> str:
    """Конвертирует любой аудио файл в WAV 16kHz, моно, для Wav2Lip"""
    base, _ = os.path.splitext(audio_path)
    wav_path = f"{base}.wav"
    if not os.path.exists(wav_path):
        (
            ffmpeg
            .input(audio_path)
            .output(wav_path, ar=16000, ac=1)
            .overwrite_output()
            .run(quiet=True)
        )
    return wav_path


@mcp.tool(
    name="cut_and_overlay_lips",
    description="""🎬 Инструмент для вырезания сегментов из видео и наложения губ (lip-sync) на каждый сегмент с использованием Wav2Lip.
    """
)
async def cut_and_overlay_lips(
    video_file: str = Field(...),
    segments: List[Dict[str, Any]] = Field(...),
    ctx: Context = None
) -> ToolResult:

    with tracer.start_as_current_span("cut_and_overlay_lips") as span:
        await ctx.info("🚀 cut_and_overlay_lips started")
        await ctx.report_progress(progress=0, total=100)

        try:
            video_path = os.path.join(VIDEO_PATH, video_file)
            checkpoint_path = os.path.join(WAV2LIB_PATH, "checkpoints", "wav2lip_gan.pth")

            output_files = []

            # Убеждаемся, что директория VIDEO_PATH существует
            os.makedirs(VIDEO_PATH, exist_ok=True)

            for i, seg in enumerate(segments):
                await ctx.info(f"▶ Segment {i}: {seg['start']}–{seg['end']}")

                start = seg["start"]
                end = seg["end"]
                audio_name = seg["audio_name"]

                raw_seg_path = os.path.join(VIDEO_PATH, f"{video_file}_segment_{i}.mp4")
                adjusted_seg_path = os.path.join(VIDEO_PATH, f"{video_file}_segment_{i}_adjusted.mp4")
                result_path = os.path.join(VIDEO_PATH, f"{video_file}_segment_{i}_result.mp4")
                audio_path = ensure_wav(os.path.join(VIDEO_PATH, audio_name))
                
                # Убеждаемся, что директория для result_path существует
                result_dir = os.path.dirname(result_path)
                if result_dir:
                    os.makedirs(result_dir, exist_ok=True)


                # --- 1. Вырезаем отрезок -------------------------------------
                cut_video(video_path, raw_seg_path, start, end)

                # --- 2. Синхронизируем длительность -------------------------
                audio_duration = get_audio_duration(audio_path)
                change_video_speed(
                    raw_seg_path,
                    adjusted_seg_path,
                    end - start,
                    audio_duration
                )

                # --- 3. Запускаем Wav2Lip на adjusted_seg_path --------------
                # Используем абсолютные пути для надежности
                abs_result_path = os.path.abspath(result_path)
                abs_adjusted_seg_path = os.path.abspath(adjusted_seg_path)
                abs_audio_path = os.path.abspath(audio_path)
                abs_checkpoint_path = os.path.abspath(checkpoint_path)
                
                wav2lip_cmd = [
                    "python",
                    f"{WAV2LIB_PATH}/inference.py",
                    "--checkpoint_path", abs_checkpoint_path,
                    "--face", abs_adjusted_seg_path,
                    "--audio", abs_audio_path,
                    "--outfile", abs_result_path,
                ]

                proc = subprocess.run(
                    wav2lip_cmd,
                    capture_output=True,
                    text=True,
                    cwd=WAV2LIB_PATH  # Запускаем из директории wav2lib для корректных относительных путей
                )

                if proc.returncode != 0:
                    raise RuntimeError(
                        f"Wav2Lip failed for segment {i}:\n"
                        f"STDOUT:\n{proc.stdout}\n"
                        f"STDERR:\n{proc.stderr}"
                    )

                # Проверяем, что файл действительно создан
                if not os.path.exists(abs_result_path):
                    raise RuntimeError(
                        f"Wav2Lip completed but output file not found: {abs_result_path}\n"
                        f"STDOUT:\n{proc.stdout}\n"
                        f"STDERR:\n{proc.stderr}"
                    )

                output_files.append(abs_result_path)

            await ctx.report_progress(progress=100, total=100)

            return ToolResult(
                content=[TextContent(type="text", text=f"Processed {len(output_files)} segments")],
                structured_content={"output_files": output_files},
            )

        except Exception as e:
            await ctx.error(f"❌ Ошибка выполнения: {e}")
            from mcp.shared.exceptions import McpError, ErrorData
            raise McpError(
                ErrorData(code=-32603, message=f"Не удалось выполнить операцию: {e}")
            )
