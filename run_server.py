#!/usr/bin/env python3
"""Скрипт запуска MCP сервера."""

import sys
from pathlib import Path

# Добавляем текущую директорию в sys.path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Запускаем сервер
if __name__ == "__main__":
    # Импортируем из локального файла server.py
    from mcp_server.server import main
    main()

