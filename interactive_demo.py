#!/usr/bin/env python3
"""
Финальная демонстрация интерактивной системы замены имен в видео.
Показывает полный workflow с выбором видео и вводом имени.
"""

import asyncio
import sys
from pathlib import Path

# Добавляем текущую директорию в sys.path для импортов
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from LLM.gigachat_llm import VideoNameReplacer
from video_selector import VideoSelector


async def interactive_demo():
    """Интерактивная демонстрация системы."""
    
    print("🎬" + "=" * 60)
    print("🎯 ИНТЕРАКТИВНАЯ СИСТЕМА ЗАМЕНЫ ИМЕН В ВИДЕО")
    print("💡 Автоматическая обработка с помощью LLM и MCP tools")
    print("🎬" + "=" * 60)
    
    # Проверяем доступные видео
    print("\n📁 ПРОВЕРКА ДОСТУПНЫХ ВИДЕО ФАЙЛОВ")
    print("-" * 40)
    
    selector = VideoSelector()
    videos = selector.find_video_files()
    
    if not videos:
        print("❌ В каталоге ./videos/ не найдено видео файлов!")
        print("\n💡 Для добавления видео:")
        print("   1. Скопируйте видео файл в каталог ./videos/")
        print("   2. Поддерживаемые форматы: MP4, AVI, MOV, MKV, WEBM, FLV, WMV")
        return
    
    print(f"✅ Найдено {len(videos)} видео файлов:")
    for i, video in enumerate(videos, 1):
        print(f"   {i}. 📹 {video['name']} ({video['size_mb']} МБ)")
    
    # Создаем экземпляр системы
    print("\n🚀 ИНИЦИАЛИЗАЦИЯ СИСТЕМЫ")
    print("-" * 30)
    
    try:
        replacer = VideoNameReplacer()
        print("✅ VideoNameReplacer успешно создан")
        
        # Запускаем интерактивную обработку
        print("\n🎯 ЗАПУСК ИНТЕРАКТИВНОЙ ОБРАБОТКИ")
        print("=" * 40)
        print("💡 Система предложит выбрать видео и ввести имя для замены")
        print()
        
        # Запускаем обработку без параметров - пользователь будет выбирать интерактивно
        result = await replacer.process_video_replacement(
            output_file="personalized_video.mp4"
        )
        
        # Показываем результат
        print("\n📊 РЕЗУЛЬТАТ ОБРАБОТКИ:")
        print("=" * 30)
        
        if result.get("status") == "success":
            print("✅ Статус: УСПЕШНО")
            print(f"📄 Выходной файл: {result.get('output_file')}")
            print(f"🔢 Обработано сегментов: {result.get('segments_processed')}")
            
            video_segments = result.get("video_segments", [])
            if video_segments:
                print(f"🎬 Создано видео сегментов: {len(video_segments)}")
                for i, segment in enumerate(video_segments, 1):
                    print(f"   {i}. {segment}")
                    
        elif result.get("status") == "no_matching_names":
            print("⚠️  Статус: ИМЕНА НЕ НАЙДЕНЫ")
            print(f"📝 Сообщение: {result.get('message')}")
            print("\n💡 Возможные причины:")
            print("   - В видео нет речи на русском языке")
            print("   - Имя не произнесено четко")
            print("   - Whisper не смог распознать речь")
            
        elif result.get("status") == "error":
            print("❌ Статус: ОШИБКА")
            print(f"💥 Сообщение: {result.get('message')}")
            print("\n🔧 Возможные решения:")
            print("   - Проверьте, что MCP сервер запущен")
            print("   - Убедитесь, что видео файл доступен")
            print("   - Проверьте настройки API")
            
        else:
            print("❓ Статус: НЕИЗВЕСТНЫЙ")
            print(f"📋 Полный результат: {result}")
        
        print("\n🎉 ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА!")
        
    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Закрываем клиент
        await replacer.close()
        print("🔌 Соединения закрыты")


def show_system_info():
    """Показывает информацию о системе."""
    
    print("\n🏗️  АРХИТЕКТУРА СИСТЕМЫ:")
    print("=" * 40)
    print("🤖 LLM (GigaChat) - Интеллектуальная замена имен")
    print("🛠️  MCP Server - Набор инструментов для обработки")
    print("🎬 Video Selector - Интерактивный выбор файлов")
    print("⚡ Workflow Manager - Управление процессом")
    
    print("\n🔄 WORKFLOW:")
    print("=" * 20)
    print("1️⃣  Интерактивный выбор видео")
    print("2️⃣  Ввод имени для замены")
    print("3️⃣  Извлечение текста (Whisper)")
    print("4️⃣  Поиск фраз с именем")
    print("5️⃣  Удаление имени из фразы")
    print("6️⃣  LLM замена с правильной падежной формой")
    print("7️⃣  Генерация TTS аудио")
    print("8️⃣  Объединение аудио")
    print("9️⃣  Синхронизация губ")
    print("🔟 Объединение сегментов")
    print("✅ Финальное персонализированное видео")
    
    print("\n🎯 ВОЗМОЖНОСТИ:")
    print("=" * 25)
    print("🎬 Поддержка MP4, AVI, MOV, MKV, WEBM, FLV, WMV")
    print("🤖 Интеллектуальная обработка русского текста")
    print("🔊 Качественная генерация речи")
    print("🎭 Синхронизация движений губ")
    print("⚡ Быстрая обработка видео сегментов")
    print("🖥️  Интуитивный интерфейс")


if __name__ == "__main__":
    print("🚀 ИНИЦИАЛИЗАЦИЯ ДЕМОНСТРАЦИИ")
    
    # Показываем информацию о системе
    show_system_info()
    
    try:
        # Запускаем интерактивную демонстрацию
        asyncio.run(interactive_demo())
        
    except KeyboardInterrupt:
        print("\n\n👋 Демонстрация прервана пользователем.")
    except Exception as e:
        print(f"\n❌ Ошибка запуска: {e}")