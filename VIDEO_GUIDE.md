# 📹 Как система работает с видео файлами

## 🎯 Текущая конфигурация

**Путь к видео файлам:** `./videos/` (относительно корня проекта)

## 📁 Структура каталогов

```
AI-DevTools-Hack/
├── videos/                    # Каталог с видео файлами
│   ├── demo_video.mp4        # Основной тестовый файл
│   ├── birthday_video.mp4    # Дополнительный тестовый файл
│   └── test_video.mp4        # Пример для разработки
```

## 🎬 Источники видео файлов

### 1. **Демо скрипт (`demo_workflow.py`)**
- Ищет файл: `demo_video.mp4`
- Использует имя: `"Шамиль"` для замены

### 2. **LLM тест (`gigachat_llm.py`)**
- Ищет файл: `test_video.mp4`
- Использует имя: `"Алексей"` для замены

### 3. **README примеры**
- Примеры используют: `video.mp4`, `birthday_video.mp4`

## 🚀 Как добавить тестовое видео

### Способ 1: Загрузить готовое видео
```bash
# Скопируйте любое видео в каталог videos/
cp /path/to/your/video.mp4 videos/demo_video.mp4
```

### Способ 2: Создать тестовое видео
```bash
# Создать тестовое видео с помощью ffmpeg
ffmpeg -f lavfi -i testsrc=duration=10:size=640x480:rate=30 -f lavfi -i sine=frequency=1000:duration=10 videos/demo_video.mp4
```

### Способ 3: Использовать онлайн ресурсы
- Скачать тестовое видео из интернета
- Разместить в каталоге `videos/` с соответствующим именем

## 📋 Требования к видео файлам

### Формат:
- **Поддерживаемые кодеки:** H.264, H.265, VP9
- **Контейнеры:** MP4, AVI, MOV, MKV
- **Длительность:** от 1 секунды до нескольких минут
- **Разрешение:** любое (рекомендуется 640x480 или выше)

### Содержание:
- **Речь на русском языке** для корректной работы Whisper
- **Четкое произношение** имен для замены
- **Качественный звук** для лучшего TTS

## 🔧 Настройка пути к видео

Если нужно изменить каталог с видео:

### Через переменную окружения:
```bash
export VIDEO_PATH="/path/to/your/videos"
python3 demo_workflow.py
```

### Через файл `.env`:
```bash
echo "VIDEO_PATH=/custom/path/to/videos" > .env
```

### Через глобальные настройки:
Изменить `mcp/globals.py`:
```python
VIDEO_PATH = os.getenv("VIDEO_PATH", "/your/custom/path")
```

## 🎯 Примеры использования

### 1. Простая замена имени:
```python
from LLM.gigachat_llm import VideoNameReplacer

replacer = VideoNameReplacer()
result = await replacer.process_video_replacement(
    video_file="demo_video.mp4",
    target_name="Мария",
    output_file="personalized_video.mp4"
)
```

### 2. Пакетная обработка:
```python
videos = ["video1.mp4", "video2.mp4", "video3.mp4"]
for video in videos:
    result = await replacer.process_video_replacement(
        video_file=video,
        target_name="Анна",
        output_file=f"anna_{video}"
    )
```

## ⚠️ Важные замечания

1. **Система создана для демонстрации** - некоторые MCP tools являются макетами
2. **Требуется реальная реализация** для полноценной работы
3. **Зависимости:** whisper, ffmpeg, другие аудио/видео библиотеки
4. **Производительность** зависит от размера и качества видео

## 🚀 Быстрый старт

1. Поместите видео файл в каталог `videos/`
2. Переименуйте его в `demo_video.mp4` или обновите имя в скрипте
3. Запустите демо: `python3 demo_workflow.py`
4. Следуйте инструкциям на экране