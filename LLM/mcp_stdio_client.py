#!/usr/bin/env python3
"""MCP клиент для общения с сервером через stdio."""

import asyncio
import json
import sys
from typing import Dict, Any, Optional
import subprocess
from pathlib import Path


class MCPStdioClient:
    """MCP клиент, использующий stdio транспорт."""

    def __init__(self, server_script: str = "run_server.py"):
        self.server_script = server_script
        self.process: Optional[subprocess.Popen] = None
        self.next_id = 1

    async def start_server(self):
        """Запускает MCP сервер в stdio режиме."""
        try:
            # Определяем путь к скрипту
            script_path = Path(__file__).parent.parent / self.server_script

            # Запускаем сервер
            self.process = subprocess.Popen(
                [sys.executable, str(script_path), "--stdio"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=None,  # Наследуем stderr для отображения ошибок
                text=True,
                bufsize=1,
                cwd=Path(__file__).parent.parent
            )

            print("✅ MCP сервер запущен в stdio режиме")

            # Даем серверу время на инициализацию
            await asyncio.sleep(1)

            # Инициализируем соединение
            await self.initialize()

        except Exception as e:
            print(f"❌ Ошибка запуска MCP сервера: {e}")
            raise

    async def stop_server(self):
        """Останавливает MCP сервер."""
        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
                print("✅ MCP сервер остановлен")
            except Exception as e:
                print(f"⚠️ Ошибка остановки сервера: {e}")
                self.process.kill()

    async def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Отправляет JSON-RPC запрос и получает ответ."""
        if not self.process:
            raise Exception("MCP сервер не запущен")

        request_id = self.next_id
        self.next_id += 1

        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }

        # Отправляем запрос
        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json)
        self.process.stdin.flush()

        # Читаем ответ
        while True:
            line = self.process.stdout.readline()
            if not line:
                raise Exception("MCP сервер закрыл соединение")

            try:
                response = json.loads(line.strip())
                if response.get("id") == request_id:
                    if "error" in response:
                        raise Exception(f"MCP ошибка: {response['error']}")
                    return response.get("result", {})
            except json.JSONDecodeError:
                continue  # Пропускаем не-JSON строки

    async def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None):
        """Отправляет JSON-RPC уведомление (без id)."""
        if not self.process:
            raise Exception("MCP сервер не запущен")

        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }

        # Отправляем уведомление
        notification_json = json.dumps(notification) + "\n"
        self.process.stdin.write(notification_json)
        self.process.stdin.flush()

    async def initialize(self):
        """Инициализирует соединение с MCP сервером."""
        try:
            result = await self.send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "llm-client",
                    "version": "1.0.0"
                }
            })

            print("✅ MCP соединение инициализировано")

            # Отправляем initialized как уведомление
            await self.send_notification("initialized")

        except Exception as e:
            print(f"❌ Ошибка инициализации MCP: {e}")
            raise

    async def list_tools(self) -> Dict[str, Any]:
        """Получает список доступных инструментов."""
        return await self.send_request("tools/list")

    async def call_tool(self, tool_name: str, **params) -> Dict[str, Any]:
        """Вызывает MCP инструмент."""
        return await self.send_request("tools/call", {
            "name": tool_name,
            "arguments": params
        })

    async def get_text_from_video(self, fileName: str) -> Dict[str, Any]:
        """Вызывает инструмент get_text_from_video."""
        return await self.call_tool("get_text_from_video", fileName=fileName)

    async def remove_name_from_phrase(self, phrase: str, name: str) -> Dict[str, Any]:
        """Вызывает инструмент remove_name_from_phrase."""
        return await self.call_tool("remove_name_from_phrase", phrase=phrase, name=name)

    async def generate_tts_audio(self, text: str, output_file: str, **kwargs) -> Dict[str, Any]:
        """Вызывает инструмент generate_tts_audio."""
        params = {"text": text, "output_file": output_file}
        params.update(kwargs)
        return await self.call_tool("generate_tts_audio", **params)

    async def merge_audio(self, original_audio_file: str, tts_audio_file: str,
                         name_start: float, name_end: float, output_file: str) -> Dict[str, Any]:
        """Вызывает инструмент merge_audio."""
        return await self.call_tool("merge_audio",
                                   original_audio_file=original_audio_file,
                                   tts_audio_file=tts_audio_file,
                                   name_start=name_start,
                                   name_end=name_end,
                                   output_file=output_file)

    async def lip_sync_video(self, video_file: str, audio_file: str,
                           output_file: str, start_time: float, end_time: float) -> Dict[str, Any]:
        """Вызывает инструмент lip_sync_video."""
        return await self.call_tool("lip_sync_video",
                                   video_file=video_file,
                                   audio_file=audio_file,
                                   output_file=output_file,
                                   start_time=start_time,
                                   end_time=end_time)

    async def combine_video_segments(self, video_files: list, output_file: str) -> Dict[str, Any]:
        """Вызывает инструмент combine_video_segments."""
        return await self.call_tool("combine_video_segments",
                                   video_files=video_files,
                                   output_file=output_file)


# Глобальный экземпляр клиента
_mcp_client: Optional[MCPStdioClient] = None


async def get_mcp_client() -> MCPStdioClient:
    """Получает глобальный экземпляр MCP клиента."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPStdioClient()
        await _mcp_client.start_server()
    return _mcp_client


async def close_mcp_client():
    """Закрывает глобальный экземпляр MCP клиента."""
    global _mcp_client
    if _mcp_client:
        await _mcp_client.stop_server()
        _mcp_client = None


# Тестовая функция
async def test_mcp_client():
    """Тестирует MCP клиент."""
    print("🔍 ТЕСТИРОВАНИЕ MCP STDIO КЛИЕНТА")
    print("=" * 40)

    try:
        client = await get_mcp_client()

        # Тестируем список инструментов
        print("1️⃣ Получение списка инструментов...")
        tools = await client.list_tools()
        print(f"   ✅ Найдено инструментов: {len(tools.get('tools', []))}")

        # Тестируем вызов get_text_from_video
        print("2️⃣ Вызов get_text_from_video...")
        result = await client.get_text_from_video("IMG_9022.mov")
        print(f"   ✅ Результат: {result}")

        print("\n✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")

    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await close_mcp_client()


if __name__ == "__main__":
    asyncio.run(test_mcp_client())