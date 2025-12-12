#!/usr/bin/env python3
"""LLM система для автоматической замены имен в видео поздравлениях."""

import os
import sys
import json
import httpx
from typing import Dict, Any, List
from openai import OpenAI
from pathlib import Path
from dotenv import load_dotenv

# Добавляем корневой каталог проекта в sys.path для импорта video_selector
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Импортируем систему выбора видео
try:
    from video_selector import VideoSelector
except ImportError as e:
    print(f"⚠️ Не удалось импортировать video_selector: {e}")
    print("💡 Убедитесь, что файл video_selector.py находится в корневом каталоге проекта")
    VideoSelector = None

# Загружаем переменные окружения
load_dotenv()

# Конфигурация LLM
api_key = os.getenv("GIGACHAT_API_KEY")
if not api_key:
    raise ValueError("GIGACHAT_API_KEY не найден в переменных окружения. Проверьте файл .env")

url = "https://foundation-models.api.cloud.ru/v1"
client = OpenAI(api_key=api_key, base_url=url)

# Импортируем MCP stdio клиент
try:
    from mcp_stdio_client import get_mcp_client, close_mcp_client
except ImportError:
    from LLM.mcp_stdio_client import get_mcp_client, close_mcp_client

class VideoNameReplacer:
    """Система замены имен в видео с помощью LLM и MCP tools."""

    def __init__(self):
        self.mcp_client = None
        
    async def ensure_mcp_client(self):
        """Убеждается, что MCP клиент инициализирован."""
        if self.mcp_client is None:
            self.mcp_client = await get_mcp_client()

    async def call_mcp_tool(self, tool_name: str, **params) -> Dict[str, Any]:
        """Вызывает MCP tool через stdio."""
        try:
            await self.ensure_mcp_client()
            return await self.mcp_client.call_tool(tool_name, **params)
        except Exception as e:
            print(f"Ошибка вызова {tool_name}: {e}")
            return {"error": str(e)}
    
    async def get_text_from_video(self, video_file: str) -> List[Dict[str, Any]]:
        """Получает текст из видео с временными метками."""
        result = await self.call_mcp_tool("get_text_from_video", fileName=video_file)
        if "error" in result:
            raise Exception(f"Ошибка получения текста: {result['error']}")

        # Извлекаем segments из structuredContent (с заглавной буквы)
        structured_content = result.get("structuredContent", {}).get("structured_content", {})
        if "segments" in structured_content:
            segments = structured_content["segments"]
            # Убеждаемся, что это список
            if isinstance(segments, list):
                return segments
            elif isinstance(segments, str):
                return json.loads(segments)

        # Fallback: извлекаем из content
        content = result.get("content", [])
        if content and len(content) > 0:
            text_content = content[0].get("text", "[]")
            try:
                return json.loads(text_content)
            except json.JSONDecodeError:
                return []
        return []
    
    def find_phrases_with_name(self, segments: List[Dict[str, Any]], target_name: str) -> List[Dict[str, Any]]:
        """Находит фразы, содержащие целевое имя."""
        matching_phrases = []
        target_lower = target_name.lower()
        
        for segment in segments:
            text = segment.get("text", "").lower()
            if target_lower in text:
                matching_phrases.append({
                    "text": segment.get("text"),
                    "start": segment.get("start"),
                    "end": segment.get("end"),
                    "original_text": segment.get("text")
                })
        
        return matching_phrases
    
    async def remove_name_from_phrase(self, phrase: str, name: str) -> Dict[str, Any]:
        """Удаляет имя из фразы."""
        result = await self.call_mcp_tool("remove_name_from_phrase", 
                                        phrase=phrase, name=name)
        return result
    
    async def generate_tts_audio(self, text: str, output_file: str) -> Dict[str, Any]:
        """Генерирует TTS аудио для текста."""
        result = await self.call_mcp_tool("generate_tts_audio",
                                        text=text, output_file=output_file)
        return result
    
    async def merge_audio(self, original_audio: str, tts_audio: str, 
                         name_start: float, name_end: float, output_file: str) -> Dict[str, Any]:
        """Объединяет оригинальное и TTS аудио."""
        result = await self.call_mcp_tool("merge_audio",
                                        original_audio_file=original_audio,
                                        tts_audio_file=tts_audio,
                                        name_start=name_start,
                                        name_end=name_end,
                                        output_file=output_file)
        return result
    
    async def lip_sync_video(self, video_file: str, audio_file: str, 
                           output_file: str, start_time: float, end_time: float) -> Dict[str, Any]:
        """Синхронизирует губы с аудио."""
        result = await self.call_mcp_tool("lip_sync_video",
                                        video_file=video_file,
                                        audio_file=audio_file,
                                        output_file=output_file,
                                        start_time=start_time,
                                        end_time=end_time)
        return result
    
    async def combine_video_segments(self, video_files: List[str], output_file: str) -> Dict[str, Any]:
        """Объединяет видео сегменты в один файл."""
        result = await self.call_mcp_tool("combine_video_segments",
                                        video_files=video_files,
                                        output_file=output_file)
        return result
    
    def use_llm_to_modify_text(self, text: str, original_name: str, new_name: str) -> str:
        """Использует LLM для замены имени в тексте с правильной падежной формой."""
        try:
            response = client.chat.completions.create(
                model="ai-sage/GigaChat3-10B-A1.8B",
                max_tokens=2500,
                temperature=0.5,
                presence_penalty=0,
                top_p=0.95,
                messages=[
                    {
                        "role": "user",
                        "content": f"Определи в следующем тексте имя того человека кому адресовано поздравление с Новым Годом. Это имя замени на имя {new_name}, поставив его в правильную падежную форму. Верни новый текст. \"{text}\""
                    }
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Ошибка LLM: {e}")
            return text  # Возвращаем исходный текст при ошибке
    
    async def select_video_interactive(self) -> str:
        """Интерактивный выбор видео файла пользователем.
        
        Returns:
            Путь к выбранному видео файлу
            
        Raises:
            Exception: Если пользователь отменил выбор или нет доступных файлов
        """
        if VideoSelector is None:
            raise Exception("Система выбора видео недоступна. Убедитесь, что файл video_selector.py находится в том же каталоге.")
        
        print("\n🎥 ВЫБОР ВИДЕО ФАЙЛА ДЛЯ ОБРАБОТКИ")
        print("=" * 50)
        
        selector = VideoSelector()
        selected = selector.interactive_selection()
        
        if not selected:
            raise Exception("Выбор видео файла отменен пользователем.")
        
        # Возвращаем только имя файла, так как VideoNameReplacer ожидает относительный путь
        return selected['name']
    
    async def get_available_videos(self) -> List[Dict[str, Any]]:
        """Получает список доступных видео файлов.
        
        Returns:
            Список информации о видео файлах
        """
        if VideoSelector is None:
            return []
        
        selector = VideoSelector()
        return selector.find_video_files()

    async def process_video_replacement(self, video_file: str = None, target_name: str = None,
                                      output_file: str = "final_output.mp4") -> Dict[str, Any]:
        """Основной процесс замены имен в видео с анализом всего текста."""
        # Интерактивный выбор видео файла
        if video_file is None:
            try:
                video_file = await self.select_video_interactive()
            except Exception as e:
                return {"status": "error", "message": f"Ошибка выбора видео: {e}"}

        # Интерактивный ввод имени для замены
        if target_name is None:
            try:
                print(f"\n👤 Выбран файл: {video_file}")
                target_name = input("📝 Введите имя для замены: ").strip()
                if not target_name:
                    return {"status": "error", "message": "Имя не может быть пустым"}
            except KeyboardInterrupt:
                return {"status": "error", "message": "Ввод прерван пользователем"}

        print(f"🎬 Начинаю обработку видео {video_file} для замены имени на '{target_name}'")

        try:
            # 0. Извлекаем оригинальное аудио из видео для voice cloning
            print("\n0️⃣ ИЗВЛЕЧЕНИЕ ОРИГИНАЛЬНОГО АУДИО")
            print("-" * 35)

            original_audio_filename = f"original_audio_{os.path.splitext(video_file)[0]}.wav"
            extract_result = await self.call_mcp_tool("extract_audio_from_video",
                                                    video_file=video_file,
                                                    output_file=original_audio_filename)

            if "error" in extract_result:
                print(f"   ❌ Ошибка извлечения аудио: {extract_result['error']}")
                return {"status": "error", "message": f"Ошибка извлечения аудио: {extract_result['error']}"}

            print(f"   ✅ Оригинальное аудио извлечено: {original_audio_filename}")

            # 1. Получаем текст из видео
            print("\n1️⃣ ПОЛУЧЕНИЕ ТЕКСТА ИЗ ВИДЕО")
            print("-" * 30)
            segments = await self.get_text_from_video(video_file)

            if not segments:
                return {"status": "error", "message": "Не удалось извлечь текст из видео"}

            print(f"   📝 Извлечено {len(segments)} сегментов текста")

            # 2. Объединяем весь текст в одну строку
            print("\n2️⃣ АНАЛИЗ ПОЛНОГО ТЕКСТА")
            print("-" * 25)
            full_text = " ".join([segment["text"] for segment in segments])
            print(f"   📄 Полный текст: '{full_text}'")

            # 3. Анализируем текст и заменяем имя через LLM
            print("\n3️⃣ ЗАМЕНА ИМЕНИ ВО ВСЕМ ТЕКСТЕ")
            print("-" * 30)
            print(f"   🤖 Отправляю запрос на замену имени '{target_name}'...")

            replace_result = await self.call_mcp_tool("analyze_and_replace_name",
                                                    full_text=full_text,
                                                    new_name=target_name)

            if "error" in replace_result:
                print(f"   ❌ Ошибка замены имени: {replace_result['error']}")
                return {"status": "error", "message": f"Ошибка замены имени: {replace_result['error']}"}

            # Извлекаем замененный текст
            replaced_text = None
            if "structuredContent" in replace_result:
                structured = replace_result["structuredContent"].get("structured_content", {})
                replaced_text = structured.get("replaced_text")
            elif "content" in replace_result and replace_result["content"]:
                replaced_text = replace_result["content"][0].get("text", "")

            if not replaced_text:
                return {"status": "error", "message": "Не удалось получить замененный текст"}

            print(f"   ✅ Замененный текст: '{replaced_text}'")

            # Выводим полный результат в терминал
            print("\n" + "="*60)
            print("🎬 ПОЛНЫЙ ТЕКСТ ВИДЕО ДО И ПОСЛЕ ЗАМЕНЫ:")
            print("="*60)
            print(f"📝 ДО:  {full_text}")
            print(f"🔄 ПОСЛЕ: {replaced_text}")
            print("="*60)

            # 4. Разбиваем замененный текст на предложения
            print("\n4️⃣ РАЗБИЕНИЕ НА ПРЕДЛОЖЕНИЯ")
            print("-" * 25)

            import re

            # Разбиваем текст на предложения
            # Используем регулярное выражение для разделения по точкам, восклицательным и вопросительным знакам
            sentence_pattern = r'(?<=[.!?])\s+'
            replaced_sentences = re.split(sentence_pattern, replaced_text.strip())

            # Очищаем предложения от лишних пробелов
            replaced_sentences = [s.strip() for s in replaced_sentences if s.strip()]

            print(f"   📝 Разбито на {len(replaced_sentences)} предложений")

            # Создаем сегменты на основе предложений
            replaced_segments = []

            # Распределяем предложения по временным сегментам оригинального видео
            total_duration = segments[-1]["end"] if segments else 0
            sentence_duration = total_duration / len(replaced_sentences) if replaced_sentences else 0

            current_time = 0.0
            for i, sentence in enumerate(replaced_sentences):
                start_time = current_time
                end_time = current_time + sentence_duration if i < len(replaced_sentences) - 1 else total_duration

                replaced_segments.append({
                    "text": sentence,
                    "start": start_time,
                    "end": end_time,
                    "sentence_id": i,
                    "original_text": ""  # Будет заполнено позже при сравнении
                })

                current_time = end_time
                print(f"   📝 Предложение {i+1}: '{sentence}' ({start_time:.1f}-{end_time:.1f}с)")

            # Теперь сравниваем с оригинальными сегментами, чтобы определить, какие предложения изменились
            print("\n4️⃣.1️⃣ АНАЛИЗ ИЗМЕНЕНИЙ")
            print("-" * 20)

            # Объединяем оригинальные сегменты в текст для сравнения
            original_full_text = " ".join([seg["text"] for seg in segments])
            original_sentences = re.split(sentence_pattern, original_full_text.strip())
            original_sentences = [s.strip() for s in original_sentences if s.strip()]

            # Сопоставляем предложения и проверяем изменения
            for i, segment in enumerate(replaced_segments):
                # Ищем соответствующее оригинальное предложение
                original_sentence = ""
                if i < len(original_sentences):
                    original_sentence = original_sentences[i]

                segment["original_text"] = original_sentence

                # Проверяем, изменилось ли предложение и содержит ли оно имя
                has_name = target_name.lower() in segment["text"].lower()
                changed = segment["text"] != original_sentence

                segment["has_name"] = has_name
                segment["changed"] = changed

                status = "🔄" if changed else "⏭️"
                name_status = "👤" if has_name else "📝"
                print(f"   {status} {name_status} '{segment['text']}'")
                if changed:
                    print(f"      Было: '{original_sentence}'")

            # 5. Генерация TTS для измененных сегментов
            print("\n5️⃣ ГЕНЕРАЦИЯ TTS ДЛЯ ИЗМЕНЕННЫХ СЕГМЕНТОВ")
            print("-" * 45)

            processed_segments = []
            tts_segments_dir = "tts_segments"
            synced_segments_dir = "synced_segments"

            for i, segment in enumerate(replaced_segments):
                # Проверяем, изменился ли текст сегмента И содержит ли он имя
                if segment.get("changed", False) and segment.get("has_name", False):
                    print(f"   🎵 Генерация TTS для предложения {i+1}: '{segment['text']}' (изменено + содержит имя)")

                    # Вычисляем длительность сегмента
                    duration = segment["end"] - segment["start"]

                    # Формируем имя файла для TTS
                    tts_filename = f"{tts_segments_dir}/tts_segment_{i:03d}_{segment['start']:.1f}s_{segment['end']:.1f}s.wav"

                    # Извлекаем оригинальное аудио из видео для voice cloning
                    original_audio_filename = f"original_audio_{os.path.splitext(video_file)[0]}.wav"

                    # Вызываем TTS генерацию через MCP с voice cloning
                    tts_result = await self.call_mcp_tool("generate_tts_audio",
                                                        text=segment["text"],
                                                        output_file=tts_filename,
                                                        original_audio_file=original_audio_filename,
                                                        start_time=segment["start"],
                                                        end_time=segment["end"],
                                                        duration=duration)  # Передаем длительность для контроля скорости речи

                    if "error" in tts_result:
                        print(f"   ❌ Ошибка генерации TTS для предложения {i+1}: {tts_result['error']}")
                        processed_segments.append({
                            "segment_id": i,
                            "text": segment["text"],
                            "original_text": segment["original_text"],
                            "audio_file": None,
                            "synced_video_file": None,
                            "start": segment["start"],
                            "end": segment["end"],
                            "duration": duration,
                            "changed": True,
                            "has_name": True,
                            "tts_error": str(tts_result['error'])
                        })
                        continue

                    print(f"   ✅ TTS сгенерирован: {tts_filename} (длительность: {duration:.1f}с)")

                    # Синхронизация губ с новым аудио
                    synced_video_filename = f"{synced_segments_dir}/synced_segment_{i:03d}_{segment['start']:.1f}s_{segment['end']:.1f}s.mp4"
                    print(f"   🎬 Синхронизация губ для предложения {i+1}...")

                    lip_sync_result = await self.call_mcp_tool("lip_sync_video",
                                                             video_file=video_file,
                                                             audio_file=tts_filename,
                                                             output_file=synced_video_filename,
                                                             start_time=segment["start"],
                                                             end_time=segment["end"])

                    if "error" in lip_sync_result:
                        print(f"   ❌ Ошибка синхронизации губ для предложения {i+1}: {lip_sync_result['error']}")
                        # Продолжаем без синхронизации
                        synced_video_filename = None

                    if synced_video_filename:
                        print(f"   ✅ Синхронизация губ завершена: {synced_video_filename}")

                    processed_segments.append({
                        "segment_id": i,
                        "text": segment["text"],
                        "original_text": segment["original_text"],
                        "audio_file": tts_filename,
                        "synced_video_file": synced_video_filename,
                        "start": segment["start"],
                        "end": segment["end"],
                        "duration": duration,
                        "changed": True,
                        "has_name": True
                    })
                elif segment.get("changed", False):
                    print(f"   ⏭️  Предложение {i+1} изменено, но не содержит имя, пропускаем: '{segment['text']}'")
                    processed_segments.append({
                        "segment_id": i,
                        "text": segment["text"],
                        "original_text": segment["original_text"],
                        "audio_file": None,
                        "synced_video_file": None,
                        "start": segment["start"],
                        "end": segment["end"],
                        "duration": segment["end"] - segment["start"],
                        "changed": True,
                        "has_name": False
                    })
                else:
                    print(f"   ⏭️  Предложение {i+1} не изменилось, пропускаем: '{segment['text']}'")
                    processed_segments.append({
                        "segment_id": i,
                        "text": segment["text"],
                        "original_text": segment["original_text"],
                        "audio_file": None,
                        "synced_video_file": None,
                        "start": segment["start"],
                        "end": segment["end"],
                        "duration": segment["end"] - segment["start"],
                        "changed": False,
                        "has_name": segment.get("has_name", False)
                    })

            # 6. Объединение видео сегментов в финальное видео
            print("\n6️⃣ ОБЪЕДИНЕНИЕ ВИДЕО СЕГМЕНТОВ")
            print("-" * 35)

            # Собираем сегменты для замены
            segments_to_replace = []
            for segment in processed_segments:
                if segment.get('synced_video_file'):
                    segments_to_replace.append({
                        "start": segment["start"],
                        "end": segment["end"],
                        "replacement_video": segment["synced_video_file"]
                    })

            # Сортируем сегменты по времени начала
            segments_to_replace.sort(key=lambda x: x["start"])

            if segments_to_replace:
                print(f"   🎬 Заменяем {len(segments_to_replace)} сегментов в оригинальном видео...")

                # Вызываем replace_video_segments
                replace_result = await self.call_mcp_tool("replace_video_segments",
                                                        original_video=video_file,
                                                        segments=segments_to_replace,
                                                        output_video=output_file)

                if "error" in replace_result:
                    print(f"   ❌ Ошибка объединения видео сегментов: {replace_result['error']}")
                    return {"status": "error", "message": f"Ошибка объединения видео сегментов: {replace_result['error']}"}

                print(f"   ✅ Финальное видео создано: {output_file}")
            else:
                print("   ⏭️  Нет сегментов для замены, копируем оригинальное видео")
                # Если нет замен, просто копируем оригинальное видео
                import shutil
                original_path = f"videos/{video_file}"
                output_path = f"videos/{output_file}"
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                shutil.copy2(original_path, output_path)
                print(f"   ✅ Оригинальное видео скопировано как: {output_file}")

            # 7. Создание финального результата
            print("\n7️⃣ СОЗДАНИЕ ФИНАЛЬНОГО РЕЗУЛЬТАТА")
            print("-" * 35)

            # Создаем подробный отчет
            result_text = f"🎬 РЕЗУЛЬТАТ ЗАМЕНЫ ИМЕНИ В ВИДЕО\n"
            result_text += f"📹 Видео файл: {video_file}\n"
            result_text += f"👤 Новое имя: {target_name}\n\n"

            result_text += f"📝 ИСХОДНЫЙ ТЕКСТ:\n{full_text}\n\n"
            result_text += f"🔄 ЗАМЕНЕННЫЙ ТЕКСТ:\n{replaced_text}\n\n"

            result_text += f"🎯 ОБРАБОТАННЫЕ ПРЕДЛОЖЕНИЯ:\n"
            tts_generated = 0
            lip_sync_done = 0
            changed_with_name = 0
            for i, segment in enumerate(processed_segments):
                status = "🔄" if segment.get('changed', False) else "⏭️"
                name_status = "👤" if segment.get('has_name', False) else "📝"
                audio_info = f" | TTS: {segment['audio_file']}" if segment.get('audio_file') else ""
                video_info = f" | Видео: {segment['synced_video_file']}" if segment.get('synced_video_file') else ""
                error_info = f" | Ошибка: {segment.get('tts_error', '')}" if segment.get('tts_error') else ""
                result_text += f"   {i+1}. {status} {name_status} '{segment['text']}' ({segment['start']:.1f}-{segment['end']:.1f}с){audio_info}{video_info}{error_info}\n"
                if segment.get('changed', False) and segment.get('has_name', False):
                    changed_with_name += 1
                if segment.get('audio_file'):
                    tts_generated += 1
                if segment.get('synced_video_file'):
                    lip_sync_done += 1

            result_text += f"\n📊 СТАТИСТИКА:\n"
            result_text += f"   📝 Всего предложений: {len(processed_segments)}\n"
            result_text += f"   🔄 Измененных предложений: {sum(1 for s in processed_segments if s.get('changed', False))}\n"
            result_text += f"   👤 Содержат имя: {sum(1 for s in processed_segments if s.get('has_name', False))}\n"
            result_text += f"   🎵 Сгенерировано TTS (изменено + имя): {tts_generated}\n"
            result_text += f"   🎬 Синхронизировано видео: {lip_sync_done}\n"

            # Сохраняем отчет в текстовый файл
            report_file = f"report_{os.path.splitext(output_file)[0]}.txt"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(result_text)

            print(f"✅ Отчет сохранен в файл: {report_file}")
            print(f"✅ Финальное видео: {output_file}")

            return {
                "status": "success",
                "output_video": output_file,
                "report_file": report_file,
                "original_text": full_text,
                "replaced_text": replaced_text,
                "sentences_processed": len(processed_segments),
                "processed_segments": processed_segments,
                "sentences_changed": sum(1 for s in processed_segments if s.get('changed', False)),
                "sentences_with_name": sum(1 for s in processed_segments if s.get('has_name', False)),
                "tts_generated": tts_generated,
                "lip_sync_done": lip_sync_done,
                "message": f"Успешно заменено имя на '{target_name}' в {tts_generated} предложениях. Синхронизировано видео: {lip_sync_done}"
            }

        except Exception as e:
            print(f"❌ Ошибка обработки: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}
    
    async def close(self):
        """Закрывает MCP клиент."""
        if self.mcp_client:
            await close_mcp_client()
            self.mcp_client = None

# Основная функция для тестирования
async def main():
    """Основная функция для запуска обработки с интерактивным выбором."""
    replacer = VideoNameReplacer()
    
    print("🎯 ИНТЕРАКТИВНАЯ СИСТЕМА ЗАМЕНЫ ИМЕН В ВИДЕО")
    print("=" * 50)
    print("💡 Система поможет вам выбрать видео файл и ввести имя для замены")
    print()
    
    try:
        # Запускаем обработку без параметров - пользователь будет выбирать интерактивно
        result = await replacer.process_video_replacement(
            # video_file=None,  # Будет запрошен интерактивно
            # target_name=None,  # Будет запрошен интерактивно
            output_file="personalized_video.mp4"
        )
        
        print("\n📊 ИТОГОВЫЙ РЕЗУЛЬТАТ:")
        print("=" * 30)
        
        if result.get("status") == "success":
            print("✅ Статус: УСПЕШНО")
            print(f"🎬 Финальное видео: {result.get('output_video')}")
            print(f"📄 Отчет: {result.get('report_file')}")
            print(f"📝 Обработано предложений: {result.get('sentences_processed')}")
            print(f"🔄 Измененных предложений: {result.get('sentences_changed', 0)}")
            print(f"👤 Содержат имя: {result.get('sentences_with_name', 0)}")
            print(f"🎵 Сгенерировано TTS: {result.get('tts_generated', 0)}")
            print(f"🎬 Синхронизировано видео: {result.get('lip_sync_done', 0)}")
                    
        elif result.get("status") == "no_matching_names":
            print("⚠️  Статус: ИМЕНА НЕ НАЙДЕНЫ")
            print(f"📝 Сообщение: {result.get('message')}")
            
        elif result.get("status") == "error":
            print("❌ Статус: ОШИБКА")
            print(f"💥 Сообщение об ошибке: {result.get('message')}")
            
        else:
            print("❓ Статус: НЕИЗВЕСТНЫЙ")
            print(f"📋 Полный результат: {result}")
        
        print("\n🎉 Обработка завершена!")
        
    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await replacer.close()

# Дополнительная функция для программного использования
async def process_specific_video(video_path: str, target_name: str, output_path: str = "result.mp4") -> Dict[str, Any]:
    """Функция для программной обработки конкретного видео.
    
    Args:
        video_path: Путь к видео файлу
        target_name: Имя для замены
        output_path: Выходной файл
        
    Returns:
        Результат обработки
    """
    replacer = VideoNameReplacer()
    
    try:
        result = await replacer.process_video_replacement(
            video_file=video_path,
            target_name=target_name,
            output_file=output_path
        )
        return result
    finally:
        await replacer.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
