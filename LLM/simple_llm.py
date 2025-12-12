#!/usr/bin/env python3
"""Упрощенная LLM система для демонстрации."""

import os
import sys
import json
import asyncio
from typing import Dict, Any, List
from pathlib import Path
from dotenv import load_dotenv

# Добавляем корневой каталог проекта в sys.path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Загружаем переменные окружения
load_dotenv()

# Импортируем систему выбора видео
try:
    from video_selector import VideoSelector
except ImportError as e:
    print(f"⚠️ Не удалось импортировать video_selector: {e}")
    VideoSelector = None

# LLM конфигурация
api_key = os.getenv("GIGACHAT_API_KEY")
url = "https://foundation-models.api.cloud.ru/v1"

try:
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=url) if api_key else None
except ImportError:
    print("⚠️ OpenAI клиент недоступен, будет использован мок")
    client = None

class SimpleVideoNameReplacer:
    """Упрощенная система замены имен без зависимостей."""
    
    def __init__(self):
        print("✅ SimpleVideoNameReplacer инициализирован")
        
    async def get_text_from_video(self, video_file: str) -> List[Dict[str, Any]]:
        """Симулирует получение текста из видео."""
        print(f"🎬 Обрабатываю видео: {video_file}")
        
        # Симулируем задержку обработки
        await asyncio.sleep(1)
        
        # Возвращаем мок-данные для демонстрации
        mock_segments = [
            {"text": "С новым годом, Иван!", "start": 1.0, "end": 3.0},
            {"text": "Желаю тебе счастья, здоровья", "start": 3.5, "end": 6.0},
            {"text": "И пусть все мечты сбываются, Иван", "start": 6.5, "end": 9.0},
        ]
        
        print(f"✅ Извлечен текст: {len(mock_segments)} сегментов")
        return mock_segments
    
    def find_phrases_with_name(self, segments: List[Dict[str, Any]], target_name: str) -> List[Dict[str, Any]]:
        """Находит фразы, содержащие целевое имя."""
        matching_phrases = []
        target_lower = target_name.lower()
        
        print(f"🔍 Ищу фразы с именем '{target_name}'...")
        
        for segment in segments:
            text = segment.get("text", "").lower()
            if target_lower in text:
                matching_phrases.append({
                    "text": segment.get("text"),
                    "start": segment.get("start"),
                    "end": segment.get("end"),
                    "original_text": segment.get("text")
                })
                print(f"   ✅ Найдено: '{segment.get('text')}'")
        
        return matching_phrases
    
    def use_llm_to_modify_text(self, text: str, original_name: str, new_name: str) -> str:
        """Использует LLM для замены имени в тексте."""
        if client is None:
            print("🤖 LLM недоступен, использую простую замену")
            return text.replace(original_name, new_name)
            
        try:
            print(f"🤖 Вызываю LLM для замены '{original_name}' на '{new_name}' в тексте: '{text}'")
            
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
            
            result = response.choices[0].message.content
            print(f"   📝 Результат LLM: '{result}'")
            return result
            
        except Exception as e:
            print(f"⚠️ Ошибка LLM: {e}, использую простую замену")
            return text.replace(original_name, new_name)
    
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
        print(f"🎬 Начинаю обработку видео {video_file} для замены имени на '{target_name}'")
        
        try:
            # 1. Получаем текст из видео
            print("\n1️⃣ ПОЛУЧЕНИЕ ТЕКСТА ИЗ ВИДЕО")
            print("-" * 30)
            segments = await self.get_text_from_video(video_file)
            
            if not segments:
                return {"status": "error", "message": "Не удалось извлечь текст из видео"}
            
            # 2. Находим фразы с целевым именем
            print("\n2️⃣ ПОИСК ФРАЗ С ЦЕЛЕВЫМ ИМЕНЕМ")
            print("-" * 30)
            matching_phrases = self.find_phrases_with_name(segments, target_name)
            
            if not matching_phrases:
                return {"status": "no_matching_names", "message": f"Имя '{target_name}' не найдено в видео"}
            
            # 3. Показываем найденные фразы
            print("\n3️⃣ НАЙДЕННЫЕ ФРАЗЫ ДЛЯ ОБРАБОТКИ")
            print("-" * 30)
            for i, phrase in enumerate(matching_phrases):
                print(f"   {i+1}. '{phrase['text']}' ({phrase['start']}-{phrase['end']}с)")
            
            # 4. Обрабатываем каждую фразу
            print("\n4️⃣ ОБРАБОТКА ФРАЗ")
            print("-" * 20)
            processed_phrases = []
            
            for i, phrase_info in enumerate(matching_phrases):
                print(f"\n4.{i+1}️⃣ Обрабатываю фразу {i+1}: '{phrase_info['text']}'")
                
                # 4.1. Заменяем имя с помощью LLM
                print("   4.1. Заменяю имя с помощью LLM...")
                new_phrase = self.use_llm_to_modify_text(
                    phrase_info["text"], target_name, target_name
                )
                
                processed_phrases.append({
                    "original": phrase_info["text"],
                    "modified": new_phrase,
                    "start": phrase_info["start"],
                    "end": phrase_info["end"]
                })
                
                print(f"   📝 Результат: '{new_phrase}'")
            
            # 5. Создаем выходной файл
            print("\n5️⃣ СОЗДАНИЕ ФИНАЛЬНОГО ФАЙЛА")
            print("-" * 25)
            
            # Создаем простой текстовый файл с результатом
            result_text = f"Результат замены имени в видео {video_file}:\n\n"
            result_text += f"Исходное имя: {target_name}\n"
            result_text += f"Новое имя: {target_name}\n\n"
            
            for i, phrase in enumerate(processed_phrases):
                result_text += f"Фраза {i+1}:\n"
                result_text += f"  Исходная: '{phrase['original']}'\n"
                result_text += f"  Измененная: '{phrase['modified']}'\n"
                result_text += f"  Время: {phrase['start']}-{phrase['end']}с\n\n"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result_text)
            
            print(f"✅ Результат сохранен в файл: {output_file}")
            
            return {
                "status": "success",
                "output_file": output_file,
                "segments_processed": len(matching_phrases),
                "phrases_found": [p["text"] for p in matching_phrases],
                "phrases_modified": [p["modified"] for p in processed_phrases],
                "video_segments": [f"segment_{i}.mp4" for i in range(len(matching_phrases))],
                "message": f"Успешно обработано {len(matching_phrases)} фраз с именем '{target_name}'"
            }
            
        except Exception as e:
            print(f"❌ Ошибка обработки: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}

# Основная функция для тестирования
async def main():
    """Тестирование упрощенного LLM."""
    replacer = SimpleVideoNameReplacer()
    
    print("🎯 УПРОЩЕННАЯ СИСТЕМА ЗАМЕНЫ ИМЕН В ВИДЕО")
    print("=" * 50)
    print("💡 Демонстрация работы без сложных зависимостей")
    
    try:
        # Запрашиваем имя у пользователя
        if len(sys.argv) > 1:
            target_name = sys.argv[1]
        else:
            target_name = input("\n👤 Введите имя для замены: ").strip()
            if not target_name:
                target_name = "Иван"  # Значение по умолчанию
        
        result = await replacer.process_video_replacement(
            video_file="IMG_9022.mov",
            target_name=target_name,
            output_file="result.txt"
        )
        
        print(f"\n📊 ИТОГОВЫЙ РЕЗУЛЬТАТ:")
        print("=" * 30)
        
        if result.get("status") == "success":
            print("✅ Статус: УСПЕШНО")
            print(f"📄 Выходной файл: {result.get('output_file')}")
            print(f"🔢 Обработано сегментов: {result.get('segments_processed')}")
            print(f"📝 Сообщение: {result.get('message')}")
            
            # Показываем изменения
            original_phrases = result.get("phrases_found", [])
            modified_phrases = result.get("phrases_modified", [])
            
            print(f"\n🔄 ИЗМЕНЕНИЯ:")
            for i, (orig, mod) in enumerate(zip(original_phrases, modified_phrases)):
                print(f"   {i+1}. '{orig}' → '{mod}'")
                    
        elif result.get("status") == "no_matching_names":
            print("⚠️  Статус: ИМЕНА НЕ НАЙДЕНЫ")
            print(f"📝 Сообщение: {result.get('message')}")
            
        elif result.get("status") == "error":
            print("❌ Статус: ОШИБКА")
            print(f"💥 Сообщение: {result.get('message')}")
            
        else:
            print("❓ Статус: НЕИЗВЕСТНЫЙ")
            print(f"📋 Полный результат: {result}")
        
        print("\n🎉 ОБРАБОТКА ЗАВЕРШЕНА!")
        
    except KeyboardInterrupt:
        print("\n\n👋 Обработка прервана пользователем.")
    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())