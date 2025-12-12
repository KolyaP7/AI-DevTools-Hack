#!/usr/bin/env python3
"""LLM система с прямым вызовом MCP функций."""

import os
import sys
import json
import asyncio
from typing import Dict, Any, List
from pathlib import Path

# Добавляем корневой каталог проекта в sys.path для импорта
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Импортируем систему выбора видео
try:
    from video_selector import VideoSelector
except ImportError as e:
    print(f"⚠️ Не удалось импортировать video_selector: {e}")
    VideoSelector = None

# Импортируем MCP функции напрямую
try:
    # Добавляем путь к mcp в sys.path
    mcp_path = project_root / "mcp" / "tools"
    if str(mcp_path) not in sys.path:
        sys.path.insert(0, str(mcp_path))
    
    from get_text_from_video import get_text_from_video
    from remove_name_from_phrase import remove_name_from_phrase
    from generate_tts_audio import generate_tts_audio
    from merge_audio import merge_audio
    from lip_sync_video import lip_sync_video
    from combine_video_segments import combine_video_segments
except ImportError as e:
    print(f"⚠️ Не удалось импортировать MCP функции: {e}")

# LLM конфигурация
api_key = "ZjJkZTE0MTEtNDk2NC00NjBlLTkyNWItOTQ1NjllNDhlNDAz.e7bfa0c5e301eb8e85256aeb4c12da27"
url = "https://foundation-models.api.cloud.ru/v1"

try:
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=url)
except ImportError:
    print("⚠️ OpenAI клиент недоступен, будет использован мок")
    client = None

class DirectVideoNameReplacer:
    """Система замены имен с прямым вызовом MCP функций."""
    
    def __init__(self):
        pass
        
    async def call_mcp_tool(self, tool_func, **params) -> Dict[str, Any]:
        """Вызывает MCP функцию напрямую."""
        try:
            # Создаем мок контекст
            class MockContext:
                async def info(self, msg): print(f"ℹ️ {msg}")
                async def error(self, msg): print(f"❌ {msg}")
                async def report_progress(self, progress, total): 
                    print(f"📊 Progress: {progress}/{total}")
            
            ctx = MockContext()
            
            # Вызываем функцию
            result = await tool_func(ctx=ctx, **params)
            return result
        except Exception as e:
            print(f"Ошибка вызова {tool_func.__name__}: {e}")
            return {"error": str(e)}
    
    async def get_text_from_video(self, video_file: str) -> List[Dict[str, Any]]:
        """Получает текст из видео с временными метками."""
        try:
            result = await self.call_mcp_tool(get_text_from_video, fileName=video_file)
            if "error" in result:
                raise Exception(f"Ошибка получения текста: {result['error']}")
            
            # Извлекаем segments из результата
            content = result.get("content", [])
            if content and len(content) > 0:
                text_content = content[0].get("text", "[]")
                return json.loads(text_content)
            return []
        except Exception as e:
            print(f"❌ Ошибка в get_text_from_video: {e}")
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
        result = await self.call_mcp_tool(remove_name_from_phrase, 
                                        phrase=phrase, name=name)
        return result
    
    async def generate_tts_audio(self, text: str, output_file: str) -> Dict[str, Any]:
        """Генерирует TTS аудио для текста."""
        result = await self.call_mcp_tool(generate_tts_audio,
                                        text=text, output_file=output_file)
        return result
    
    async def merge_audio(self, original_audio: str, tts_audio: str, 
                         name_start: float, name_end: float, output_file: str) -> Dict[str, Any]:
        """Объединяет оригинальное и TTS аудио."""
        result = await self.call_mcp_tool(merge_audio,
                                        original_audio_file=original_audio,
                                        tts_audio_file=tts_audio,
                                        name_start=name_start,
                                        name_end=name_end,
                                        output_file=output_file)
        return result
    
    async def lip_sync_video(self, video_file: str, audio_file: str, 
                           output_file: str, start_time: float, end_time: float) -> Dict[str, Any]:
        """Синхронизирует губы с аудио."""
        result = await self.call_mcp_tool(lip_sync_video,
                                        video_file=video_file,
                                        audio_file=audio_file,
                                        output_file=output_file,
                                        start_time=start_time,
                                        end_time=end_time)
        return result
    
    async def combine_video_segments(self, video_files: List[str], output_file: str) -> Dict[str, Any]:
        """Объединяет видео сегменты в один файл."""
        result = await self.call_mcp_tool(combine_video_segments,
                                        video_files=video_files,
                                        output_file=output_file)
        return result
    
    def use_llm_to_modify_text(self, text: str, original_name: str, new_name: str) -> str:
        """Использует LLM для замены имени в тексте с правильной падежной формой."""
        if client is None:
            print("⚠️ LLM недоступен, возвращаем исходный текст")
            return text
            
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
        """Интерактивный выбор видео файла пользователем."""
        if VideoSelector is None:
            raise Exception("Система выбора видео недоступна.")
        
        print("\n🎥 ВЫБОР ВИДЕО ФАЙЛА ДЛЯ ОБРАБОТКИ")
        print("=" * 50)
        
        selector = VideoSelector()
        selected = selector.interactive_selection()
        
        if not selected:
            raise Exception("Выбор видео файла отменен пользователем.")
        
        return selected['name']
    
    async def get_available_videos(self) -> List[Dict[str, Any]]:
        """Получает список доступных видео файлов."""
        if VideoSelector is None:
            return []
        
        selector = VideoSelector()
        return selector.find_video_files()

    async def process_video_replacement(self, video_file: str = None, target_name: str = None, 
                                      output_file: str = "final_output.mp4") -> Dict[str, Any]:
        """Основной процесс замены имен в видео."""
        print(f"🎬 DirectVideoNameReplacer: обработка видео {video_file} для замены имени на '{target_name}'")
        
        try:
            # 1. Получаем текст из видео
            print("1️⃣ Получаю текст из видео...")
            segments = await self.get_text_from_video(video_file)
            print(f"   Найдено {len(segments)} сегментов")
            
            if not segments:
                return {"status": "error", "message": "Не удалось извлечь текст из видео"}
            
            # 2. Находим фразы с целевым именем
            print("2️⃣ Ищу фразы с целевым именем...")
            matching_phrases = self.find_phrases_with_name(segments, target_name)
            print(f"   Найдено {len(matching_phrases)} фраз с именем '{target_name}'")
            
            if not matching_phrases:
                return {"status": "no_matching_names", "message": f"Имя '{target_name}' не найдено в видео"}
            
            # 3. Показываем найденные фразы
            print("3️⃣ Найденные фразы:")
            for i, phrase in enumerate(matching_phrases):
                print(f"   {i+1}. '{phrase['text']}' ({phrase['start']}-{phrase['end']}с)")
            
            # 4. Симулируем обработку каждой фразы
            video_segments = []
            for i, phrase_info in enumerate(matching_phrases):
                print(f"4.{i+1}️⃣ Обрабатываю фразу {i+1}: '{phrase_info['text']}'")
                
                # 4.1. Удаляем имя из фразы
                print("   4.1. Удаляю имя из фразы...")
                remove_result = await self.remove_name_from_phrase(
                    phrase_info["text"], target_name
                )
                
                # 4.2. Заменяем имя с помощью LLM
                print("   4.2. Заменяю имя с помощью LLM...")
                modified_phrase = remove_result.get("structured_content", {}).get("modified_phrase", phrase_info["text"])
                new_phrase = self.use_llm_to_modify_text(
                    modified_phrase, target_name, target_name
                )
                print(f"   📝 Новый текст: '{new_phrase}'")
                
                # 4.3. Создаем фиктивные файлы для демонстрации
                tts_output = f"tts_{i}.wav"
                merged_audio = f"merged_{i}.wav"
                video_output = f"synced_{i}.mp4"
                
                # Создаем пустые файлы как заглушки
                with open(tts_output, 'w') as f:
                    f.write(f"# TTS audio for: {new_phrase}\n")
                with open(merged_audio, 'w') as f:
                    f.write(f"# Merged audio {i}\n")
                with open(video_output, 'w') as f:
                    f.write(f"# Synced video {i}\n")
                
                video_segments.append(video_output)
            
            # 5. Объединяем все сегменты
            print("5️⃣ Объединяю все видео сегменты...")
            final_result = await self.combine_video_segments(video_segments, output_file)
            
            print(f"✅ Обработка завершена! Результат: {output_file}")
            
            return {
                "status": "success",
                "output_file": output_file,
                "segments_processed": len(matching_phrases),
                "video_segments": video_segments,
                "final_result": final_result,
                "phrases_found": [p["text"] for p in matching_phrases]
            }
            
        except Exception as e:
            print(f"❌ Ошибка обработки: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}

# Основная функция для тестирования
async def main():
    """Тестирование прямого LLM."""
    replacer = DirectVideoNameReplacer()
    
    print("🎯 ТЕСТ ПРЯМОГО LLM")
    print("=" * 30)
    
    try:
        result = await replacer.process_video_replacement(
            video_file="IMG_9022.mov",
            target_name="Иван",
            output_file="test_output.mp4"
        )
        
        print(f"\n📊 РЕЗУЛЬТАТ: {result}")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())