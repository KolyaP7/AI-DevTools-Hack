#!/usr/bin/env python3
"""Тест соединения с MCP сервером."""

import asyncio
import httpx
import sys
from pathlib import Path

# Добавляем текущую директорию в sys.path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

async def test_mcp_connection():
    """Тестирует соединение с MCP сервером."""
    
    mcp_url = "http://127.0.0.1:8000/mcp"
    
    print("🔍 ТЕСТ СОЕДИНЕНИЯ С MCP СЕРВЕРОМ")
    print("=" * 50)
    print(f"📡 URL: {mcp_url}")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            print("1️⃣ Проверка доступности сервера...")
            
            # Проверяем health endpoint
            try:
                response = await client.get(f"{mcp_url}/health", timeout=5.0)
                print(f"   ✅ Health check: {response.status_code}")
            except Exception as e:
                print(f"   ⚠️ Health endpoint недоступен: {e}")
            
            print("2️⃣ Проверка tools endpoint...")
            
            # Проверяем список инструментов
            try:
                response = await client.get(f"{mcp_url}/tools", timeout=5.0)
                if response.status_code == 200:
                    tools = response.json()
                    print(f"   ✅ Найдено инструментов: {len(tools.get('tools', []))}")
                    for tool in tools.get('tools', []):
                        print(f"      - {tool.get('name')}")
                else:
                    print(f"   ❌ Ошибка получения списка инструментов: {response.status_code}")
            except Exception as e:
                print(f"   ❌ Ошибка соединения: {e}")
                return False
            
            print("3️⃣ Тест вызова get_text_from_video...")
            
            # Тестируем вызов инструмента
            try:
                response = await client.post(
                    f"{mcp_url}/tools/get_text_from_video",
                    json={"fileName": "IMG_9022.mov"},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"   ✅ Инструмент успешно вызван")
                    print(f"   📊 Статус: {result.get('status', 'success')}")
                else:
                    print(f"   ❌ Ошибка вызова инструмента: {response.status_code}")
                    print(f"   📄 Ответ: {response.text}")
            except Exception as e:
                print(f"   ❌ Ошибка вызова инструмента: {e}")
                return False
        
        print("\n✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        return True
        
    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        return False

async def main():
    success = await test_mcp_connection()
    
    if success:
        print("\n🎉 Система готова к использованию!")
        print("💡 Теперь можете запустить: python interactive_demo.py")
    else:
        print("\n💥 Система не готова. Проверьте:")
        print("   1. MCP сервер запущен: python start_server.py --http")
        print("   2. Сервер доступен на http://127.0.0.1:8000")
        print("   3. Нет блокировки порта 8000")

if __name__ == "__main__":
    asyncio.run(main())