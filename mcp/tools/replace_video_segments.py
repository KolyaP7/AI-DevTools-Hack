"""Ускоренный инструмент для замены сегментов видео."""

import os
import subprocess
import json
import tempfile
from typing import Dict, Any, List

from fastmcp import Context
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field

from mcp_instance import mcp
from tools.utils import ToolResult
from globals import VIDEO_PATH

tracer = trace.get_tracer(__name__)


@mcp.tool(
    name="replace_video_segments",
    description="""🎬 Инструмент для замены сегментов в видео на отредактированные куски с использованием ffmpeg.
    Принимает оригинальное видео и список сегментов для замены, создает новое видео с замененными сегментами путем конкатенации частей.
    """
)
async def replace_video_segments(
    original_video: str = Field(
        ...,
        description="Имя оригинального видеофайла"
    ),
    segments: List[Dict[str, Any]] = Field(
        ...,
        description="Список сегментов для замены в формате: [{'start': float, 'end': float, 'replacement_video': str}]"
    ),
    ctx: Context = None
) -> ToolResult:
    """
    Заменяет указанные сегменты в видео на другие видеофайлы.
    
    Args:
        original_video: Имя оригинального видеофайла
        segments: Список сегментов для замены, каждый содержит:
            - start: время начала сегмента (float, секунды)
            - end: время окончания сегмента (float, секунды)
            - replacement_video: имя видеофайла для замены
        ctx: Контекст для логирования и отслеживания прогресса
        
    Returns:
        ToolResult: Результат выполнения инструмента
        
    Raises:
        McpError: При ошибках выполнения
    """
    with tracer.start_as_current_span("replace_video_segments") as span:
        span.set_attribute("original_video", original_video)
        span.set_attribute("segments_count", len(segments))
        
        await ctx.info("🚀 replace_video_segments started")
        await ctx.report_progress(progress=0, total=100)
        
        try:
            original_path = os.path.join(VIDEO_PATH, original_video)
            
            # Генерируем имя выходного файла
            base_name, ext = os.path.splitext(original_video)
            output_file = f"{base_name}_replaced{ext}"
            output_path = os.path.join(VIDEO_PATH, output_file)
            
            span.set_attribute("output_file", output_file)
            
            # Проверка существования оригинального видео
            if not os.path.exists(original_path):
                raise FileNotFoundError(f"Original video file not found: {original_path}")
            
            # Получение длительности оригинального видео
            await ctx.info("📹 Определение длительности оригинального видео")
            cmd_duration = [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", original_path
            ]
            result = subprocess.run(cmd_duration, capture_output=True, text=True, check=True)
            video_duration = float(result.stdout.strip())
            
            await ctx.report_progress(progress=10, total=100)
            
            # Валидация и сортировка сегментов
            await ctx.info("🔍 Валидация и сортировка сегментов")
            validated_segments = []
            for i, seg in enumerate(segments):
                if not all(k in seg for k in ['start', 'end', 'replacement_video']):
                    raise ValueError(f"Сегмент {i} должен содержать поля: start, end, replacement_video")
                
                start = float(seg['start'])
                end = float(seg['end'])
                replacement_video = seg['replacement_video']
                replacement_path = os.path.join(VIDEO_PATH, replacement_video)
                
                if not os.path.exists(replacement_path):
                    raise FileNotFoundError(f"Replacement video file not found: {replacement_path}")
                
                if start < 0 or end <= start:
                    raise ValueError(f"Неверные временные метки в сегменте {i}: start={start}, end={end}")
                
                if start > video_duration:
                    raise ValueError(f"Начало сегмента {i} ({start}) превышает длительность видео ({video_duration})")
                
                validated_segments.append({
                    'start': start,
                    'end': min(end, video_duration),  # Обрезаем если выходит за границы
                    'replacement_video': replacement_path
                })
            
            # Сортировка по времени начала
            validated_segments.sort(key=lambda x: x['start'])
            
            # Проверка на перекрытия
            for i in range(len(validated_segments) - 1):
                if validated_segments[i]['end'] > validated_segments[i + 1]['start']:
                    await ctx.info(f"⚠️ Предупреждение: сегменты {i} и {i+1} перекрываются")
                    # Обрезаем первый сегмент до начала второго
                    validated_segments[i]['end'] = validated_segments[i + 1]['start']
            
            await ctx.report_progress(progress=20, total=100)
            
            # Создание списка частей для конкатенации
            parts = []
            temp_files = []
            
            current_time = 0.0
            
            for i, seg in enumerate(validated_segments):
                start = seg['start']
                end = seg['end']
                replacement_path = seg['replacement_video']
                
                # Добавляем часть до сегмента (если есть)
                if current_time < start:
                    temp_before = os.path.join(VIDEO_PATH, f"temp_before_{i}.mp4")
                    cmd_before = [
                        "ffmpeg", "-y", "-i", original_path,
                        "-ss", str(current_time),
                        "-t", str(start - current_time),
                        "-c", "copy", temp_before
                    ]
                    await ctx.info(f"Вырезаем часть до сегмента {i}: {current_time:.2f} - {start:.2f}")
                    subprocess.run(cmd_before, check=True, capture_output=True)
                    parts.append(temp_before)
                    temp_files.append(temp_before)
                
                # Добавляем заменяющее видео
                await ctx.info(f"Добавляем заменяющее видео для сегмента {i}: {replacement_path}")
                parts.append(replacement_path)
                
                current_time = end
                await ctx.report_progress(progress=20 + int((i + 1) / len(validated_segments) * 60), total=100)
            
            # Добавляем оставшуюся часть после последнего сегмента
            if current_time < video_duration:
                temp_after = os.path.join(VIDEO_PATH, f"temp_after_final.mp4")
                cmd_after = [
                    "ffmpeg", "-y", "-i", original_path,
                    "-ss", str(current_time),
                    "-c", "copy", temp_after
                ]
                await ctx.info(f"Вырезаем часть после последнего сегмента: {current_time:.2f} - {video_duration:.2f}")
                subprocess.run(cmd_after, check=True, capture_output=True)
                parts.append(temp_after)
                temp_files.append(temp_after)
            
            # Если нет сегментов, просто копируем оригинал
            if not validated_segments:
                parts = [original_path]
            
            await ctx.report_progress(progress=80, total=100)
            
            # Конкатенация всех частей
            await ctx.info("🔗 Конкатенация всех частей видео")
            
            # Создаем файл списка для concat demuxer
            concat_list_file = os.path.join(VIDEO_PATH, "concat_list.txt")
            with open(concat_list_file, 'w') as f:
                for part in parts:
                    # Используем абсолютные пути и экранируем специальные символы
                    abs_part = os.path.abspath(part)
                    f.write(f"file '{abs_part}'\n")
            
            # Конкатенация с использованием concat demuxer
            cmd_concat = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", concat_list_file,
                "-c", "copy", output_path
            ]
            
            subprocess.run(cmd_concat, check=True, capture_output=True)
            
            # Удаление временных файлов
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            
            if os.path.exists(concat_list_file):
                os.remove(concat_list_file)
            
            await ctx.report_progress(progress=100, total=100)
            await ctx.info("✅ Замена сегментов завершена успешно")
            
            result = {
                "output_file": output_file,
                "status": "success",
                "segments_processed": len(validated_segments),
                "original_video": original_video
            }
            
            span.set_attribute("success", True)
            
            return ToolResult(
                content=[TextContent(type="text", text=f"Замена сегментов завершена: {output_file}")],
                structured_content=result,
                meta={
                    "original_video": original_video,
                    "output_file": output_file,
                    "segments_count": len(validated_segments)
                }
            )
            
        except Exception as e:
            span.set_attribute("error", str(e))
            await ctx.error(f"❌ Ошибка выполнения: {e}")
            
            from mcp.shared.exceptions import McpError, ErrorData
            raise McpError(
                ErrorData(
                    code=-32603,
                    message=f"Не удалось выполнить замену сегментов: {e}"
                )
            )

