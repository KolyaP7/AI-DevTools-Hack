"""Инструмент для замены сегментов видео с использованием ffmpeg."""

import json
import os
import subprocess
from typing import Dict, Any, List

from fastmcp import Context
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field

# Импорты с обработкой разных контекстов выполнения
try:
    # Относительные импорты (когда файл импортируется как модуль)
    from ..mcp_instance import mcp
    from .utils import ToolResult
except ImportError:
    # Абсолютные импорты (когда файл запускается напрямую или через server.py)
    from mcp_instance import mcp
    from tools.utils import ToolResult
# OpenTelemetry tracer
tracer = trace.get_tracer(__name__)




def run_ffmpeg(cmd: List[str]):
    """Запуск FFmpeg и ожидание завершения."""
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode())




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
            # Импорт с обработкой разных контекстов выполнения
            try:
                from ..globals import VIDEO_PATH
            except ImportError:
                from globals import VIDEO_PATH
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
            concat_list: List[str] = []
            temp_files: List[str] = []

            def get_video_info(path: str) -> Dict[str, Any]:
                """Получает информацию о видео: разрешение, fps, наличие аудио."""
                probe_cmd = [
                    "ffprobe",
                    "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries", "stream=width,height,r_frame_rate",
                    "-of", "json",
                    path,
                ]
                result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
                video_info = json.loads(result.stdout)
                
                audio_cmd = [
                    "ffprobe",
                    "-v", "error",
                    "-select_streams", "a",
                    "-show_entries", "stream=codec_type",
                    "-of", "json",
                    path,
                ]
                audio_result = subprocess.run(audio_cmd, capture_output=True, text=True)
                has_audio = False
                if audio_result.returncode == 0:
                    audio_info = json.loads(audio_result.stdout)
                    has_audio = "streams" in audio_info and len(audio_info["streams"]) > 0
                
                streams = video_info.get("streams", [])
                if streams:
                    r_frame_rate = streams[0].get("r_frame_rate", "30/1")
                    num, den = map(int, r_frame_rate.split("/"))
                    fps = num / den if den > 0 else 30
                    width = streams[0].get("width", 1920)
                    height = streams[0].get("height", 1080)
                else:
                    fps = 30
                    width = 1920
                    height = 1080
                
                return {
                    "width": width,
                    "height": height,
                    "fps": fps,
                    "has_audio": has_audio
                }

            # Получаем параметры оригинального видео для нормализации
            orig_info = get_video_info(original_path)
            target_width = orig_info["width"]
            target_height = orig_info["height"]
            target_fps = orig_info["fps"]

            def transcode_segment(
                src: str,
                dst: str,
                start: float | None = None,
                duration: float | None = None,
            ) -> str:
                """
                Нормализует участок видео: одинаковое разрешение, fps, аудио параметры.
                Все сегменты приводятся к единым параметрам для корректной конкатенации.
                """
                # Проверяем наличие аудио в исходнике
                src_info = get_video_info(src)
                has_audio_src = src_info["has_audio"]
                
                # Используем seek до входа для устойчивости и скорости
                cmd = ["ffmpeg", "-y"]
                if start is not None:
                    cmd += ["-ss", str(start)]
                cmd += ["-i", src]
                if duration is not None:
                    cmd += ["-t", str(duration)]
                
                # Нормализуем видео: приводим к единому разрешению и fps
                video_filter = (
                    f"[0:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
                    f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2,"
                    f"fps={target_fps}[v]"
                )
                
                # Аудио: используем оригинальное, если есть, иначе добавляем тишину
                if has_audio_src:
                    audio_filter = "[0:a]aformat=sample_rates=48000:channel_layouts=stereo[a]"
                    filter_complex = f"{video_filter};{audio_filter}"
                    cmd += ["-filter_complex", filter_complex]
                    cmd += ["-map", "[v]", "-map", "[a]"]
                else:
                    # Добавляем синтезированный аудиопоток
                    cmd += [
                        "-f", "lavfi",
                        "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"
                    ]
                    cmd += ["-filter_complex", video_filter]
                    cmd += ["-map", "[v]", "-map", "1:a", "-shortest"]
                
                cmd += [
                    "-c:v", "libx264",
                    "-preset", "veryfast",
                    "-crf", "20",
                    "-pix_fmt", "yuv420p",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-ar", "48000",
                    "-ac", "2",
                    "-movflags", "+faststart",
                    "-fflags", "+genpts",
                    "-reset_timestamps", "1",
                    dst
                ]
                
                try:
                    subprocess.run(cmd, check=True, capture_output=True)
                except subprocess.CalledProcessError as e_cmd:
                    stderr = ""
                    try:
                        stderr = e_cmd.stderr.decode("utf-8", errors="replace") if e_cmd.stderr else ""
                    except Exception:
                        pass
                    detail = stderr.strip() or str(e_cmd)
                    raise RuntimeError(f"ffmpeg transcode_segment failed: {detail}") from e_cmd
                temp_files.append(dst)
                return dst

            # Валидация сегментов (отсортированы, без пересечений, с положительной длительностью)
            normalized_segments = sorted(segments, key=lambda x: x["start"])
            last_end = 0.0
            for seg in normalized_segments:
                start = float(seg["start"])
                end = float(seg["end"])
                if end <= start:
                    raise ValueError(f"Segment end must be > start: {seg}")
                if start < last_end:
                    raise ValueError(f"Segments overlap: {seg}")
                last_end = end

            from uuid import uuid4
            from funcs.video import change_video_speed, get_audio_duration as get_video_duration

            concat_list = []
            temp_files = []

            current_time = 0.0  # всегда по ОРИГИНАЛЬНОМУ таймлайну

            def tmpfile():
                return os.path.join(VIDEO_PATH, f"tmp_{uuid4().hex}.mp4")


            for idx, seg in enumerate(normalized_segments):
                start = float(seg["start"])
                end = float(seg["end"])
                repl = seg["replacement_video"]

                # 1) Вырезаем кусок оригинала ДО сегмента
                if start > current_time:
                    temp_before = tmpfile()
                    transcode_segment(
                        src=original_path,
                        dst=temp_before,
                        start=current_time,
                        duration=start - current_time,
                    )
                    concat_list.append(temp_before)

                # 2) Подготовка и подгонка replacement под длину сегмента
                repl_path = os.path.join(VIDEO_PATH, repl)

                original_seg_len = end - start
                repl_len = get_video_duration(repl_path)

                # если длина не совпадает — подгоняем
                if abs(repl_len - original_seg_len) > 0.01:
                    adjusted_repl = tmpfile()
                    change_video_speed(
                        input_file=repl_path,
                        output_file=adjusted_repl,
                        original_length=repl_len,
                        target_length=original_seg_len
                    )
                    repl_normalized = adjusted_repl
                else:
                    repl_normalized = repl_path

                # приводим заменённый участок к параметрам оригинального видео
                prepared_repl = tmpfile()
                transcode_segment(
                    src=repl_normalized,
                    dst=prepared_repl
                )
                concat_list.append(prepared_repl)

                current_time = end


            # 3) Вырезаем остаток оригинального видео
            duration_cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                original_path
            ]
            result = subprocess.run(duration_cmd, capture_output=True, text=True, check=True)
            total_duration = float(result.stdout.strip())

            if current_time < total_duration:
                temp_tail = tmpfile()
                transcode_segment(
                    src=original_path,
                    dst=temp_tail,
                    start=current_time,
                    duration=total_duration - current_time,
                )
                concat_list.append(temp_tail)
            # Остаток видео после последнего сегмента
            duration_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", original_path]
            result = subprocess.run(duration_cmd, capture_output=True, text=True, check=True)
            total_duration = float(result.stdout.strip())

            if current_time < total_duration:
                temp_end = os.path.join(VIDEO_PATH, f"temp_{current_time}_end.mp4")
                transcode_segment(
                    src=original_path,
                    dst=temp_end,
                    start=current_time,
                    duration=total_duration - current_time,
                )
                concat_list.append(temp_end)

            await ctx.report_progress(progress=60, total=100)

            # Создание файла со списком для конкатенации
            # Используем абсолютные пути для надежности
            concat_file = os.path.join(VIDEO_PATH, "concat_list.txt")
            with open(concat_file, 'w') as f:
                for vid in concat_list:
                    # Используем абсолютный путь и экранируем специальные символы
                    abs_path = os.path.abspath(vid)
                    f.write(f"file '{abs_path}'\n")

            # Конкатенация
            cmd_concat = [
                "ffmpeg",
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-c", "copy",
                "-movflags", "+faststart",
                output_path,
            ]
            subprocess.run(cmd_concat, check=True, capture_output=True)

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