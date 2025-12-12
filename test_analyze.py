#!/usr/bin/env python3
"""Тест инструмента analyze_and_replace_name."""

import asyncio
import sys
from pathlib import Path

# Добавляем корневой каталог проекта в sys.path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from LLM.mcp_stdio_client import get_mcp_client, close_mcp_client

async def test_analyze():
    """Тестируем замену имени."""
    print("🔍 ТЕСТИРОВАНИЕ ЗАМЕНЫ ИМЕНИ")

    try:
        client = await get_mcp_client()

        # Текст из видео
        full_text = "Доброго новогоднего дня, друзья! Привет, Максим! Я скоро приду же тебя поздравлять! Ты стешочек-то подготовил? Приду проверю! Я же подарю, это просто так не вручаю! Поэтому ты стешочек-то повтори! И мне его лично уже расскажешь! А я стешочек-то послушаю! И подарочек-то тебе вручу! Будь умненьким! Скоро же тебе приду! Поздравлю!"

        new_name = "Алексей"

        print(f"📝 Исходный текст: {full_text}")
        print(f"👤 Новое имя: {new_name}")

        result = await client.call_tool("analyze_and_replace_name",
                                      full_text=full_text,
                                      new_name=new_name)

        print("✅ Результат получен")

        if "structuredContent" in result:
            structured = result["structuredContent"].get("structured_content", {})
            replaced_text = structured.get("replaced_text")
            if replaced_text:
                print(f"🔄 Замененный текст: {replaced_text}")
            else:
                print("❌ Замененный текст не найден")
        else:
            print(f"📋 Полный результат: {result}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await close_mcp_client()

if __name__ == "__main__":
    asyncio.run(test_analyze())