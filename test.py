
import whisperx
import torch
import json

AUDIO_FILE = "audio.mp3"
WHISPER_MODEL = "small"  # или tiny, base, small, medium

# Загружаем модель Whisper
device = "cuda" if torch.cuda.is_available() else "cpu"
model = whisperx.load_model(WHISPER_MODEL, device)

# Транскрибируем аудио
result = model.transcribe(AUDIO_FILE)

# Загружаем модель для forced alignment (точные таймкоды для слов)
align_model, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
result_aligned = whisperx.align(result["segments"], align_model, metadata, AUDIO_FILE, device)

# result_aligned["word_segments"] содержит слова с таймкодами
words_with_timestamps = []
for word_info in result_aligned["word_segments"]:
    words_with_timestamps.append({
        "word": word_info["word"],
        "start": word_info["start"],
        "end": word_info["end"]
    })

# Сохраняем в JSON
json_result = json.dumps(words_with_timestamps, ensure_ascii=False, indent=2)
print(json_result)
