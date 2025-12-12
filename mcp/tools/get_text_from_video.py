"""Инструмент для получения текста с временными метками из видео."""

import json
import sys
import subprocess
import tempfile
import re

import os
from typing import Dict, Any, List

import whisper

import httpx
from fastmcp import Context
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field


from ..mcp_instance import mcp
from .utils import ToolResult, _require_env_vars, format_api_error
from ..globals import WHISPER_MODEL, VIDEO_PATH
# OpenTelemetry tracer
tracer = trace.get_tracer(__name__)


def split_text_into_sentences(text: str) -> List[str]:
    """Разбивает текст на предложения."""
    # Регулярное выражение для разделения по знакам препинания с учетом русского языка
    # Разделяем по: . ! ? ... но не разрываем сокращения
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())

    # Фильтруем пустые строки и очищаем от лишних пробелов
    sentences = [s.strip() for s in sentences if s.strip()]

    return sentences


def map_sentences_to_time_segments(sentences: List[str], whisper_segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Сопоставляет предложения с временными сегментами."""
    result_segments = []

    # Объединяем все сегменты Whisper в один текст для поиска
    full_whisper_text = ""
    word_positions = []  # (word_text, start_time, end_time, char_start, char_end)

    current_char_pos = 0
    for segment in whisper_segments:
        segment_text = segment["text"].strip()
        if segment_text:
            full_whisper_text += segment_text + " "
            words = segment_text.split()
            char_start = current_char_pos

            # Распределяем время между словами в сегменте
            if words:
                time_per_word = (segment["end"] - segment["start"]) / len(words)
                word_start_time = segment["start"]

                for word in words:
                    word_end_time = word_start_time + time_per_word
                    word_positions.append({
                        "word": word,
                        "start": word_start_time,
                        "end": word_end_time,
                        "char_start": current_char_pos,
                        "char_end": current_char_pos + len(word)
                    })
                    current_char_pos += len(word) + 1  # +1 для пробела
                    word_start_time = word_end_time

    full_whisper_text = full_whisper_text.strip()

    # Теперь сопоставляем предложения с временными диапазонами
    current_pos = 0
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        # Ищем начало предложения в полном тексте
        sentence_start = full_whisper_text.find(sentence, current_pos)
        if sentence_start == -1:
            # Если точное совпадение не найдено, ищем приблизительное
            # Ищем первое слово предложения
            first_word = sentence.split()[0] if sentence.split() else ""
            if first_word:
                alt_start = full_whisper_text.find(first_word, current_pos)
                if alt_start != -1:
                    sentence_start = alt_start
                else:
                    continue

        sentence_end = sentence_start + len(sentence)

        # Находим временные границы на основе позиций слов
        start_time = None
        end_time = None

        for word_info in word_positions:
            if word_info["char_start"] >= sentence_start and word_info["char_end"] <= sentence_end:
                if start_time is None:
                    start_time = word_info["start"]
                end_time = word_info["end"]

        # Если не нашли точное соответствие, используем приблизительные границы
        if start_time is None or end_time is None:
            # Ищем ближайшие слова
            for word_info in word_positions:
                if word_info["char_start"] <= sentence_start <= word_info["char_end"]:
                    start_time = word_info["start"]
                if word_info["char_start"] <= sentence_end <= word_info["char_end"]:
                    end_time = word_info["end"]
                    break

        # Если все еще не нашли, используем границы всего текста
        if start_time is None:
            start_time = word_positions[0]["start"] if word_positions else 0.0
        if end_time is None:
            end_time = word_positions[-1]["end"] if word_positions else 1.0

        result_segments.append({
            "text": sentence,
            "start": start_time,
            "end": end_time
        })

        current_pos = sentence_end

    return result_segments


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
        if ctx:
            await ctx.info("🚀 get_text_from_video started")
            await ctx.report_progress(progress=0, total=100)
        else:
            print("🚀 get_text_from_video started", file=sys.stderr)
        
        try:
            video_path = os.path.join(VIDEO_PATH, fileName)
            if not os.path.exists(video_path):
                raise Exception(f"Видео файл не найден: {video_path}")

            print(f"🚀 Начинаем обработку видео: {fileName}", file=sys.stderr)

            # Создаем временные файлы
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_audio:
                temp_audio_path = temp_audio.name

            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_enhanced:
                temp_enhanced_path = temp_enhanced.name

            try:
                # Шаг 1: Извлекаем аудио из видео
                print("🎵 Извлекаю аудио из видео...", file=sys.stderr)
                extract_cmd = [
                    "ffmpeg", "-i", video_path, "-vn", "-acodec", "mp3",
                    "-ab", "128k", "-y", temp_audio_path
                ]

                result = subprocess.run(extract_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    raise Exception(f"Ошибка извлечения аудио: {result.stderr}")

                print("✅ Аудио извлечено", file=sys.stderr)

                # Шаг 2: Улучшаем характеристики аудио для транскрибации
                print("🎛️ Улучшаю характеристики аудио для распознавания...", file=sys.stderr)
                enhance_cmd = [
                    "ffmpeg", "-i", temp_audio_path,
                    "-af", "acompressor=threshold=-30dB:ratio=20:attack=1:release=100:makeup=12dB:knee=8:mix=1,loudnorm",
                    "-c:a", "mp3", "-b:a", "128k", "-y", temp_enhanced_path
                ]

                result = subprocess.run(enhance_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"⚠️ Не удалось улучшить аудио: {result.stderr}", file=sys.stderr)
                    print("🔄 Использую оригинальное аудио для транскрибации", file=sys.stderr)
                    audio_for_transcription = temp_audio_path
                else:
                    print("✅ Аудио улучшено для распознавания", file=sys.stderr)
                    audio_for_transcription = temp_enhanced_path

                # Шаг 3: Загружаем модель Whisper
                print("⏳ Загружаем модель Whisper...", file=sys.stderr)
                model = whisper.load_model(WHISPER_MODEL)
                print("✅ Модель загружена", file=sys.stderr)

                # Шаг 4: Выполняем транскрибацию улучшенного аудио
                print("🎙️ Выполняем транскрибацию...", file=sys.stderr)
                whisper_result = model.transcribe(audio_for_transcription)
                print("✅ Транскрибация завершена", file=sys.stderr)

            finally:
                # Очищаем временные файлы
                for temp_file in [temp_audio_path, temp_enhanced_path]:
                    try:
                        if os.path.exists(temp_file):
                            os.unlink(temp_file)
                    except Exception as e:
                        print(f"⚠️ Не удалось удалить временный файл {temp_file}: {e}", file=sys.stderr)

            # Получаем сегменты Whisper для точного позиционирования
            whisper_segments = []
            for segment in whisper_result["segments"]:
                whisper_segments.append({
                    "text": segment["text"].strip(),
                    "start": segment["start"],
                    "end": segment["end"]
                })

            # Объединяем весь текст
            full_text = " ".join([segment["text"] for segment in whisper_segments])
            print(f"📄 Полный распознанный текст видео: '{full_text}'", file=sys.stderr)

            # Разбиваем текст на предложения
            sentences = split_text_into_sentences(full_text)
            print(f"📝 Разбито на {len(sentences)} предложений", file=sys.stderr)

            # Сопоставляем предложения с временными сегментами
            result = map_sentences_to_time_segments(sentences, whisper_segments)

            print(f"🎯 Созданы сегменты по предложениям: {len(result)}", file=sys.stderr)
            for i, segment in enumerate(result):
                print(f"  {i+1}. '{segment['text']}' ({segment['start']:.1f}-{segment['end']:.1f}с)", file=sys.stderr)

            # Раскомментируйте для реальной обработки:
            # print("model loading...", end="")
            # model = whisper.load_model(WHISPER_MODEL)
            # print("done")
            # print("transcribing...", end="")
            # whisper_result = model.transcribe(os.path.join(VIDEO_PATH, fileName))
            # print("done")
            #
            # result = []
            # for i in whisper_result["segments"]:
            #     result.append({
            #         "text": i["text"],
            #         "start": i["start"],
            #         "end": i["end"]
            #     })
            #     print("text: ", i["text"], "start: ", i["start"], "end: ", i["end"])




            json_result = json.dumps(result)


            return ToolResult(
                content=[TextContent(type="text", text=json_result)],
                structured_content={"segments": result},
                meta={"fileName": fileName}
            )
        except Exception as e:
            span.set_attribute("error", str(e))
            if ctx:
                await ctx.error(f"❌ Ошибка выполнения: {e}")
            else:
                print(f"❌ Ошибка выполнения: {e}", file=sys.stderr)
            
            from mcp.shared.exceptions import McpError, ErrorData
            raise McpError(
                ErrorData(
                    code=-32603,
                    message=f"Не удалось выполнить операцию: {e}"
                )
            )

