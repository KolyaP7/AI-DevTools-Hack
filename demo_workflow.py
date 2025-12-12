#!/usr/bin/env python3
"""Демонстрационный скрипт для тестирования системы замены имен в видео."""

import asyncio
import sys
import os
from pathlib import Path

# Добавляем текущую директорию в sys.path для импортов
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from LLM.gigachat_llm import VideoNameReplacer

async def test_video_replacement():
    """Тестирует систему замены имен в видео."""
    
    print("🎬 ДЕМОНСТРАЦИЯ СИСТЕМЫ ЗАМЕНЫ ИМЕН В ВИДЕО")
    print("=" * 60)
    
    # Создаем экземпляр системы
    replacer = VideoNameReplacer()
    
    try:
        # Демо параметры
        video_file = "demo_video.mp4"
        target_name = "Шамиль"  # Имя для замены
        output_file = "demo_output.mp4"
        
        print(f"📁 Входной видеофайл: {video_file}")
        print(f"👤 Целевое имя: {target_name}")
        print(f"📤 Выходной файл: {output_file}")
        print()
        
        # Запускаем обработку
        print("🚀 Запуск обработки...")
        result = await replacer.process_video_replacement(
            video_file=video_file,
            target_name=target_name,
            output_file=output_file
        )
        
        print("\n" + "=" * 60)
        print("📊 РЕЗУЛЬТАТ:")
        print("=" * 60)
        
        # Выводим результат в удобном формате
        if result.get("status") == "success":
            print("✅ Статус: УСПЕШНО")
            print(f"📄 Выходной файл: {result.get('output_file')}")
            print(f"🔢 Обработано сегментов: {result.get('segments_processed')}")
            
            video_segments = result.get("video_segments", [])
            if video_segments:
                print(f"🎬 Создано видео сегментов: {len(video_segments)}")
                for i, segment in enumerate(video_segments, 1):
                    print(f"   {i}. {segment}")
            
            final_result = result.get("final_result", {})
            if final_result:
                print(f"🔧 Статус финальной обработки: {final_result.get('status', 'unknown')}")
                
        elif result.get("status") == "no_matching_names":
            print("⚠️  Статус: ИМЕНА НЕ НАЙДЕНЫ")
            print(f"📝 Сообщение: {result.get('message')}")
            
        elif result.get("status") == "error":
            print("❌ Статус: ОШИБКА")
            print(f"💥 Сообщение об ошибке: {result.get('message')}")
            
        else:
            print("❓ Статус: НЕИЗВЕСТНЫЙ")
            print(f"📋 Полный результат: {result}")
        
        print("\n" + "=" * 60)
        print("🎉 ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА")
        
    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Закрываем клиент
        await replacer.close()

def show_workflow_steps():
    """Показывает шаги workflow системы."""
    print("\n🔄 ШАГИ РАБОЧЕГО ПРОЦЕССА:")
    print("=" * 40)
    print("1️⃣  Получение текста из видео (get_text_from_video)")
    print("2️⃣  Поиск фраз с целевым именем")
    print("3️⃣  Для каждой найденной фразы:")
    print("    3.1 ✂️  Удаление имени (remove_name_from_phrase)")
    print("    3.2 🤖 Замена с помощью LLM (GigaChat)")
    print("    3.3 🔊 Генерация TTS аудио (generate_tts_audio)")
    print("    3.4 🔗 Объединение аудио (merge_audio)")
    print("    3.5 🎬 Синхронизация губ (lip_sync_video)")
    print("4️⃣  Объединение всех сегментов (combine_video_segments)")
    print("5️⃣  Финальное видео готово!")

def show_available_tools():
    """Показывает доступные MCP tools."""
    print("\n🛠️  ДОСТУПНЫЕ MCP TOOLS:")
    print("=" * 40)
    tools = [
        ("get_text_from_video", "Получение текста из видео с временными метками"),
        ("remove_name_from_phrase", "Удаление имени из фразы"),
        ("generate_tts_audio", "Генерация TTS аудио"),
        ("merge_audio", "Объединение оригинального и TTS аудио"),
        ("lip_sync_video", "Синхронизация губ с аудио"),
        ("combine_video_segments", "Объединение видео сегментов")
    ]
    
    for tool_name, description in tools:
        print(f"🔧 {tool_name}")
        print(f"   📝 {description}")
        print()

if __name__ == "__main__":
    print("🎯 СИСТЕМА ЗАМЕНЫ ИМЕН В ВИДЕО ПОЗДРАВЛЕНИЯХ")
    print("💡 Автоматическая обработка с помощью LLM и MCP tools")
    print()
    
    # Показываем информацию о системе
    show_workflow_steps()
    show_available_tools()
    
    # Спрашиваем пользователя, хочет ли он запустить демо
    try:
        response = input("\n❓ Запустить демонстрацию? (y/n): ").lower().strip()
        if response in ['y', 'yes', 'да', 'д']:
            print("\n🚀 Запуск демонстрации...")
            asyncio.run(test_video_replacement())
        else:
            print("👋 Демонстрация отменена пользователем.")
    except KeyboardInterrupt:
        print("\n👋 Демонстрация прервана пользователем.")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")