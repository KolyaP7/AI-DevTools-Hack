#!/usr/bin/env python3
"""Прямой запуск MCP сервера."""

import sys
import os
from pathlib import Path

# Добавляем текущую директорию в sys.path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Убираем mcp из sys.modules чтобы избежать конфликтов
if 'mcp' in sys.modules:
    del sys.modules['mcp']
if 'mcp.server' in sys.modules:
    del sys.modules['mcp.server']

# Загружаем переменные окружения
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

# Импортируем и запускаем сервер напрямую
sys.path.insert(0, str(project_root / 'mcp'))
import server
server.main()