from TTS.api import TTS

# Инициализация модели
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to("cuda")

# Клонирование голоса
tts.tts_to_file(
    text="Привет, это клонированный голос!",
    speaker_wav="reference_audio.wav",
    language="ru",
    file_path="output.wav"
)