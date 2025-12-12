#!/usr/bin/env python3
"""Тест генерации TTS аудио."""

import asyncio
import sys
from pathlib import Path

# Добавляем корневой каталог проекта в sys.path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from LLM.mcp_stdio_client import get_mcp_client, close_mcp_client

async def test_tts_generation():
    """Тестируем генерацию TTS с voice cloning."""
    print("🎤 Тестирование генерации TTS с клонированием голоса")

    try:
        client = await get_mcp_client()

        # 1. Извлекаем аудио из видео для voice cloning
        print("🎵 Извлечение аудио из видео IMG_9022.mov...")
        extract_result = await client.call_tool("extract_audio_from_video",
                                              video_file="IMG_9022.mov",
                                              output_file="original_audio.wav")

        if "error" in extract_result:
            print(f"❌ Ошибка извлечения аудио: {extract_result['error']}")
            return

        print("✅ Оригинальное аудио извлечено")

        # 2. Генерируем TTS с voice cloning
        print("🎭 Генерация TTS с клонированием голоса...")
        result = await client.call_tool("generate_tts_audio",
                                      text="Привет, Максим! С днем рождения!",
                                      output_file="voice_cloned_tts.wav",
                                      original_audio_file="original_audio.wav",
                                      duration=3.0)

        print(f"✅ Результат TTS: {result}")

        # Проверяем файл
        import os
        output_path = "videos/voice_cloned_tts.wav"
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"✅ Файл создан, размер: {file_size} байт")

            # Определяем тип файла
            import subprocess
            try:
                file_result = subprocess.run(["file", output_path],
                                           capture_output=True, text=True)
                print(f"📁 Тип файла: {file_result.stdout.strip()}")

                # Получаем длительность
                probe_result = subprocess.run([
                    "ffprobe", "-v", "quiet", "-print_format", "json",
                    "-show_format", output_path
                ], capture_output=True, text=True)

                if probe_result.returncode == 0:
                    import json
                    probe_data = json.loads(probe_result.stdout)
                    duration = float(probe_data["format"]["duration"])
                    print(f"⏱️ Длительность: {duration:.2f} секунд")

            except Exception as e:
                print(f"⚠️ Ошибка анализа файла: {e}")
        else:
            print("❌ Файл не создан")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await close_mcp_client()

if __name__ == "__main__":
    asyncio.run(test_tts_generation())