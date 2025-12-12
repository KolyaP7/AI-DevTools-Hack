"""Инструмент для замены сегментов видео с использованием ffmpeg."""

import os
import subprocess
from typing import Dict, Any, List

from fastmcp import Context
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field

from ..mcp_instance import mcp
from .utils import ToolResult
# OpenTelemetry tracer
tracer = trace.get_tracer(__name__)


@mcp.tool(
    name="replace_video_segments",
    description="""🎬 Инструмент для замены сегментов в видео на отредактированные куски с использованием ffmpeg.
    """
)
async def replace_video_segments(
    original_video: str = Field(
        ...,
        description="Имя оригинального видеофайла"
    ),
    segments: List[Dict[str, Any]] = Field(
        ...,
        description="Список сегментов для замены: [{'start': float, 'end': float, 'replacement_video': str}]"
    ),
    output_video: str = Field(
        ...,
        description="Имя выходного видеофайла"
    ),
    ctx: Context = None
) -> ToolResult:
    """
    Заменяет сегменты в оригинальном видео на отредактированные куски.

    Использует ffmpeg для конкатенации видео с замененными сегментами.

    Args:
        original_video: Оригинальный видеофайл
        segments: Список сегментов с start, end, replacement_video
        output_video: Выходной файл

    Returns:
        ToolResult с информацией о замене.

    Examples:
        >>> segments = [{"start": 10, "end": 15, "replacement_video": "synced.mp4"}]
        >>> result = await replace_video_segments(original_video="input.mp4", segments=segments, output_video="output.mp4", ctx)
    """
    with tracer.start_as_current_span("replace_video_segments") as span:
        span.set_attribute("original_video", original_video)
        span.set_attribute("output_video", output_video)

        await ctx.info("🚀 replace_video_segments started")
        await ctx.report_progress(progress=0, total=100)

        try:
            from ..globals import VIDEO_PATH
            original_path = os.path.join(VIDEO_PATH, original_video)
            output_path = os.path.join(VIDEO_PATH, output_video)

            # Проверка существования файлов
            if not os.path.exists(original_path):
                raise FileNotFoundError(f"Original video not found: {original_path}")

            for seg in segments:
                repl_path = os.path.join(VIDEO_PATH, seg["replacement_video"])
                if not os.path.exists(repl_path):
                    raise FileNotFoundError(f"Replacement video not found: {repl_path}")

            await ctx.report_progress(progress=20, total=100)

            # Создание списка для конкатенации
            concat_list = []

            # Начало видео (до первого сегмента)
            current_time = 0.0
            for seg in sorted(segments, key=lambda x: x["start"]):
                start = seg["start"]
                end = seg["end"]
                repl = seg["replacement_video"]

                if start > current_time:
                    # Вырезать часть оригинала
                    temp_part = os.path.join(VIDEO_PATH, f"temp_{current_time}_{start}.mp4")
                    cmd_cut = [
                        "ffmpeg", "-i", original_path, "-ss", str(current_time), "-t", str(start - current_time),
                        "-c", "copy", temp_part
                    ]
                    subprocess.run(cmd_cut, check=True)
                    concat_list.append(temp_part)

                # Добавить замененный сегмент
                repl_path = os.path.join(VIDEO_PATH, repl)
                concat_list.append(repl_path)

                current_time = end

            # Остаток видео после последнего сегмента
            duration_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", original_path]
            result = subprocess.run(duration_cmd, capture_output=True, text=True, check=True)
            total_duration = float(result.stdout.strip())

            if current_time < total_duration:
                temp_end = os.path.join(VIDEO_PATH, f"temp_{current_time}_end.mp4")
                cmd_cut_end = [
                    "ffmpeg", "-i", original_path, "-ss", str(current_time), "-t", str(total_duration - current_time),
                    "-c", "copy", temp_end
                ]
                subprocess.run(cmd_cut_end, check=True)
                concat_list.append(temp_end)

            await ctx.report_progress(progress=60, total=100)

            # Создание файла со списком для конкатенации
            concat_file = os.path.join(VIDEO_PATH, "concat_list.txt")
            with open(concat_file, 'w') as f:
                for vid in concat_list:
                    f.write(f"file '{vid}'\n")

            # Конкатенация
            cmd_concat = [
                "ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_file, "-c", "copy", output_path
            ]
            subprocess.run(cmd_concat, check=True)

            # Очистка временных файлов
            os.remove(concat_file)
            for temp_file in concat_list:
                if temp_file.startswith(os.path.join(VIDEO_PATH, "temp_")):
                    os.remove(temp_file)

            result = {
                "output_video": output_video,
                "segments_replaced": len(segments),
                "status": "success"
            }

            await ctx.report_progress(progress=100, total=100)

            return ToolResult(
                content=[TextContent(type="text", text=f"Video segments replaced: {output_video}")],
                structured_content=result,
                meta={"original_video": original_video, "output_video": output_video}
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