#!/usr/bin/env python3
"""Тест MCP клиента с использованием официального SDK."""

import asyncio
import sys
from pathlib import Path

# Добавляем текущую директорию в sys.path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

async def test_mcp_client():
    """Тестирует MCP клиент через официальный SDK."""
    
    print("🔍 ТЕСТ MCP КЛИЕНТА")
    print("=" * 30)
    
    try:
        from mcp.client.stdio import stdio_client
        import subprocess
        
        print("1️⃣ Запуск MCP клиента...")
        
        # Запускаем MCP сервер как subprocess
        server_script = str(project_root / "start_server.py")
        
        # Создаем subprocess для stdio режима
        process = await asyncio.create_subprocess_exec(
            sys.executable, server_script, "--stdio",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        print("2️⃣ Подключение к серверу...")
        
        # Подключаемся через stdio
        async with stdio_client(process) as (read, write):
            print("   ✅ Соединение установлено")
            
            # Инициализируем клиент
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "test-client",
                        "version": "1.0.0"
                    }
                }
            }
            
            await write.send(init_request)
            response = await read.recv()
            print(f"   📊 Инициализация: {response}")
            
            # Получаем список инструментов
            tools_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list"
            }
            
            await write.send(tools_request)
            response = await read.recv()
            print(f"   📋 Список инструментов: {response}")
            
            # Пробуем вызвать инструмент
            call_request = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "get_text_from_video",
                    "arguments": {
                        "fileName": "IMG_9022.mov"
                    }
                }
            }
            
            await write.send(call_request)
            response = await read.recv()
            print(f"   🎯 Результат вызова: {response}")
        
        print("\n✅ ТЕСТ ЗАВЕРШЕН УСПЕШНО!")
        return True
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    success = await test_mcp_client()
    
    if success:
        print("\n🎉 MCP соединение работает!")
    else:
        print("\n💥 Есть проблемы с MCP соединением")

if __name__ == "__main__":
    asyncio.run(main())