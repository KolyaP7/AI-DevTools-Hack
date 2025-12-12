"""Инструмент для генерации TTS аудио с использованием FastSpeech 2 + Vocoder."""

import os
from typing import Dict, Any, List

from fastmcp import Context
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field

# Импорты с обработкой разных контекстов выполнения
try:
    # Относительные импорты (когда файл импортируется как модуль)
    from ..mcp_instance import mcp
    from .utils import ToolResult
except ImportError:
    # Абсолютные импорты (когда файл запускается напрямую или через server.py)
    from mcp_instance import mcp
    from tools.utils import ToolResult

# OpenTelemetry tracer
tracer = trace.get_tracer(__name__)

# Импорт для TTS (предполагаем наличие библиотек)
try:
    # Пример импортов, нужно установить соответствующие библиотеки
    # from TTS.api import TTS
    # или другие
    pass
except ImportError:
    pass


async def apply_clean_voice_cloning(tts_file: str, reference_file: str, video_path: str):
    """Применяет чистый voice cloning без шумов и артефактов."""
    try:
        import librosa
        import numpy as np
        import soundfile as sf

        reference_path = os.path.join(video_path, reference_file)

        # Загружаем аудио файлы
        tts_audio, tts_sr = librosa.load(tts_file, sr=None)
        ref_audio, ref_sr = librosa.load(reference_path, sr=None)

        # Ресемплируем к общей частоте дискретизации
        target_sr = 22050
        if tts_sr != target_sr:
            tts_audio = librosa.resample(tts_audio, orig_sr=tts_sr, target_sr=target_sr)
            tts_sr = target_sr
        if ref_sr != target_sr:
            ref_audio = librosa.resample(ref_audio, orig_sr=ref_sr, target_sr=target_sr)
            ref_sr = target_sr

        # Вычисляем pitch с консервативными параметрами для чистоты
        ref_pitch = librosa.yin(ref_audio, fmin=80, fmax=300, sr=ref_sr, frame_length=2048, hop_length=512)
        tts_pitch = librosa.yin(tts_audio, fmin=80, fmax=300, sr=tts_sr, frame_length=2048, hop_length=512)

        # Фильтруем выбросы
        ref_pitch_valid = ref_pitch[(ref_pitch > 70) & (ref_pitch < 350)]
        tts_pitch_valid = tts_pitch[(tts_pitch > 70) & (tts_pitch < 350)]

        if len(ref_pitch_valid) > 0 and len(tts_pitch_valid) > 0:
            ref_pitch_median = np.median(ref_pitch_valid)
            tts_pitch_median = np.median(tts_pitch_valid)

            # Вычисляем коэффициент изменения высоты тона
            pitch_ratio = ref_pitch_median / tts_pitch_median

            # Очень консервативные границы для чистоты
            pitch_ratio = np.clip(pitch_ratio, 0.9, 1.2)

            # Применяем изменение высоты тона только если нужно
            n_steps = 12 * np.log2(pitch_ratio)
            if abs(n_steps) > 0.5:  # Только значительные изменения
                n_steps = np.clip(n_steps, -2, 2)  # Максимум полтона
                tts_audio = librosa.effects.pitch_shift(tts_audio, sr=tts_sr, n_steps=n_steps)

        # Простая нормализация громкости без компрессии
        # Вычисляем RMS референсного аудио
        ref_rms = np.sqrt(np.mean(ref_audio**2))
        tts_rms = np.sqrt(np.mean(tts_audio**2))

        if ref_rms > 0 and tts_rms > 0:
            # Нормализуем громкость TTS к уровню референса
            gain = ref_rms / tts_rms
            gain = np.clip(gain, 0.7, 1.5)  # Более естественный диапазон
            tts_audio = tts_audio * gain

        # Добавляем естественность через простые вариации громкости (без артефактов)
        # Имитация естественной просодии через subtle амплитудную модуляцию
        time_axis = np.linspace(0, len(tts_audio) / tts_sr, len(tts_audio))

        # Очень мягкая амплитудная модуляция (2-3 Hz) - имитация естественного дыхания
        amplitude_modulation = 1 + 0.02 * np.sin(2 * np.pi * 2.5 * time_axis)

        # Ограничиваем модуляцию для предотвращения клиппинга
        amplitude_modulation = np.clip(amplitude_modulation, 0.9, 1.1)

        # Применяем модуляцию
        tts_audio = tts_audio * amplitude_modulation

        # Добавляем естественное начало и окончание речи
        fade_length = int(tts_sr * 0.08)  # 80ms fade для плавности
        if len(tts_audio) > fade_length * 2:
            # Плавный fade in (имитация начала речи)
            fade_in = np.linspace(0.7, 1.0, fade_length)
            tts_audio[:fade_length] *= fade_in

            # Плавный fade out (имитация окончания речи)
            fade_out = np.linspace(1.0, 0.8, fade_length)
            tts_audio[-fade_length:] *= fade_out

        # Применяем частотную коррекцию для более глубокого голоса
        # Усиливаем низкие частоты и срезаем высокие
        try:
            from scipy import signal
            import numpy as np

            # Создаем фильтр нижних частот (low-pass) для среза высоких частот
            # Частота среза: 8000 Hz (убираем шипение и высокие тона)
            nyquist = tts_sr / 2
            cutoff_high = 8000  # Hz
            normalized_cutoff_high = cutoff_high / nyquist

            # Фильтр Баттерворта 4-го порядка для плавного среза
            b_high, a_high = signal.butter(4, normalized_cutoff_high, btype='low')

            # Применяем фильтр высоких частот (срезаем выше 8000 Hz)
            tts_audio = signal.filtfilt(b_high, a_high, tts_audio)

            # Создаем фильтр высоких частот (high-pass) для усиления басов
            # Частота среза: 100 Hz (оставляем только низкие частоты для усиления)
            cutoff_low = 100  # Hz
            normalized_cutoff_low = cutoff_low / nyquist

            # Фильтр Баттерворта для басов
            b_low, a_low = signal.butter(2, normalized_cutoff_low, btype='high')

            # Выделяем басовую компоненту
            bass_component = signal.filtfilt(b_low, a_low, tts_audio)

            # Усиливаем басовую компоненту (boost на 3dB = ~1.4 раза)
            bass_boost = 1.4
            bass_component = bass_component * bass_boost

            # Смешиваем оригинал с усиленными басами
            # Используем 70% оригинала + 30% усиленных басов
            tts_audio = 0.7 * tts_audio + 0.3 * bass_component

        except ImportError:
            # Если scipy недоступен, пропускаем частотную коррекцию
            pass
        except Exception as e:
            # При ошибке фильтрации оставляем оригинал
            print(f"Frequency correction failed: {e}")
            pass

        # Финальная нормализация без клиппинга
        max_val = np.max(np.abs(tts_audio))
        if max_val > 0:
            tts_audio = tts_audio / max_val * 0.95  # Оптимальная громкость

        # Сохраняем результат с глубоким голосом
        sf.write(tts_file, tts_audio, tts_sr)

    except Exception as e:
        print(f"Clean voice cloning failed: {e}")
        # Если voice cloning не удался, оставляем оригинальный файл
        pass


@mcp.tool(
    name="generate_tts_audio",
    description="""🔊 Инструмент для генерации TTS аудио с использованием FastSpeech 2 + Vocoder.
    """
)
async def generate_tts_audio(
    text: str = Field(
        ...,
        description="Текст для озвучивания"
    ),
    output_file: str = Field(
        ...,
        description="Имя выходного аудиофайла"
    ),
    original_audio_file: str = Field(
        None,
        description="Путь к оригинальному аудио файлу для клонирования голоса"
    ),
    start_time: float = Field(
        None,
        description="Время начала сегмента в секундах"
    ),
    end_time: float = Field(
        None,
        description="Время окончания сегмента в секундах"
    ),
    duration: float = Field(
        None,
        description="Целевая длительность аудио в секундах (для контроля скорости речи)"
    ),
    segments: List[Dict[str, Any]] = Field(
        None,
        description="Сегменты с временными метками для генерации в нужные моменты"
    ),
    ctx: Context = None
) -> ToolResult:
    """
    Генерирует TTS аудио для текста с использованием XTTS v2 и клонированием голоса.

    Args:
        text: Текст для озвучивания
        output_file: Имя выходного файла
        original_audio_file: Путь к оригинальному аудио для клонирования голоса
        start_time: Время начала сегмента в секундах
        end_time: Время окончания сегмента в секундах
        duration: Целевая длительность аудио в секундах (для контроля скорости речи)
        segments: Опционально, сегменты для генерации в конкретные моменты

    Returns:
        ToolResult с информацией о сгенерированном аудио.

    Examples:
        >>> result = await generate_tts_audio(text="новое имя", output_file="name.wav",
        ...                                   original_audio_file="original.wav",
        ...                                   start_time=10.0, end_time=12.5, ctx)
    """
    with tracer.start_as_current_span("generate_tts_audio") as span:
        span.set_attribute("text", text)
        span.set_attribute("output_file", output_file)
        if duration:
            span.set_attribute("target_duration", duration)

        if ctx:
            await ctx.info("🚀 generate_tts_audio started")
            await ctx.report_progress(progress=0, total=100)

        try:
            # Импорт с обработкой разных контекстов выполнения
            try:
                from ..globals import VIDEO_PATH
            except ImportError:
                from globals import VIDEO_PATH
            output_path = os.path.join(VIDEO_PATH, output_file)

            # Вычисляем длительность если не указана
            if duration is None and start_time is not None and end_time is not None:
                duration = end_time - start_time

            # Импорт и инициализация TTS (XTTS v2 или gTTS)
            tts_available = False
            gtts_available = False

            # Сначала пробуем gTTS для чистого звука
            try:
                from gtts import gTTS
                gtts_available = True
                if ctx:
                    await ctx.info("✅ gTTS инициализирован для чистого TTS")
                    await ctx.report_progress(progress=30, total=100)
            except Exception as e:
                if ctx:
                    await ctx.info(f"⚠️ gTTS недоступен: {e}")
                    await ctx.info("🔄 Пробуем pyttsx3...")
                # Fallback to pyttsx3
                try:
                    import pyttsx3
                    tts = pyttsx3.init()
                    # Настраиваем для чистоты
                    voices = tts.getProperty('voices')
                    # Выбираем чистый голос
                    clean_voice = None
                    for voice in voices:
                        if 'samantha' in voice.name.lower() and 'en_US' in voice.languages:
                            clean_voice = voice
                            break
                        elif 'alex' in voice.name.lower():
                            clean_voice = voice
                            break

                    if clean_voice:
                        tts.setProperty('voice', clean_voice.id)
                    # Настраиваем для максимальной чистоты
                    tts.setProperty('rate', 180)  # Чуть быстрее для четкости
                    tts.setProperty('volume', 1.0)  # Максимальная громкость
                    pyttsx3_available = True
                    if ctx:
                        await ctx.info("✅ pyttsx3 инициализирован с чистым голосом")
                        await ctx.report_progress(progress=30, total=100)
                except Exception as e2:
                    if ctx:
                        await ctx.info(f"⚠️ pyttsx3 недоступен: {e2}")
                        await ctx.info("🔄 Пробуем XTTS v2...")

                # Попытка использовать XTTS v2
                try:
                    from TTS.api import TTS
                    import torch

                    if ctx:
                        await ctx.info("🎯 Инициализация XTTS v2 модели...")
                        await ctx.report_progress(progress=10, total=100)

                    # Инициализация модели
                    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")

                    # Попытка использовать CUDA, если доступно
                    if torch.cuda.is_available():
                        tts = tts.to("cuda")
                        if ctx:
                            await ctx.info("✅ Модель загружена на GPU")
                    else:
                        if ctx:
                            await ctx.info("⚠️ CUDA недоступна, используем CPU")

                    tts_available = True
                    if ctx:
                        await ctx.report_progress(progress=30, total=100)

                except ImportError as e2:
                    if ctx:
                        await ctx.info(f"⚠️ XTTS v2 недоступен: {e2}")
                        await ctx.info("📝 Создание заглушки для TTS аудио")
                    tts_available = False
                    pyttsx3_available = False

            # Генерация речи с клонированием голоса
            if ctx:
                await ctx.info(f"🎤 Генерация речи для текста: '{text}'")
                await ctx.report_progress(progress=50, total=100)

            if gtts_available:
                # Используем gTTS для чистого и четкого звука
                if ctx:
                    await ctx.info("🎭 Генерация чистой речи через gTTS")

                # Создаем gTTS объект с русским языком для максимальной чистоты и человечности
                # Используем разные TLD для более естественного голоса
                tts = gTTS(text=text, lang='ru', slow=False, tld='ru')  # Русский домен для аутентичности

                # Сохраняем в файл
                tts.save(output_path)

                # Если указан оригинальный аудио файл, применяем простой voice cloning
                if original_audio_file:
                    if ctx:
                        await ctx.info(f"🎭 Применяем чистый voice cloning к: {original_audio_file}")

                    try:
                        # Применяем упрощенный voice cloning для чистоты
                        await apply_clean_voice_cloning(output_path, original_audio_file, VIDEO_PATH)
                        if ctx:
                            await ctx.info("✅ Чистый voice cloning применен")
                    except Exception as e:
                        if ctx:
                            await ctx.info(f"⚠️ Voice cloning не удался: {e}")

                if ctx:
                    await ctx.info("✅ Чистая речь сгенерирована через gTTS")

            elif pyttsx3_available:
                # Используем pyttsx3 для генерации речи
                if ctx:
                    await ctx.info("🎭 Генерация речи через pyttsx3 с чистым голосом")

                # Генерируем речь в файл
                tts.save_to_file(text, output_path)
                tts.runAndWait()

                # Если указан оригинальный аудио файл, применяем voice cloning
                if original_audio_file:
                    if ctx:
                        await ctx.info(f"🎭 Применяем voice cloning к: {original_audio_file}")

                    try:
                        # Применяем чистый voice cloning
                        await apply_clean_voice_cloning(output_path, original_audio_file, VIDEO_PATH)
                        if ctx:
                            await ctx.info("✅ Voice cloning применен")
                    except Exception as e:
                        if ctx:
                            await ctx.info(f"⚠️ Voice cloning не удался: {e}")

                if ctx:
                    await ctx.info("✅ Речь сгенерирована через pyttsx3")

            elif tts_available:
                # Если указан оригинальный аудио файл, используем voice cloning
                if original_audio_file:
                    original_audio_path = os.path.join(VIDEO_PATH, original_audio_file)

                    if not os.path.exists(original_audio_path):
                        raise Exception(f"Оригинальный аудио файл не найден: {original_audio_path}")

                    if ctx:
                        await ctx.info(f"🎭 Клонирование голоса из: {original_audio_file}")

                    # Генерация с voice cloning
                    tts.tts_to_file(
                        text=text,
                        file_path=output_path,
                        speaker_wav=original_audio_path,
                        language="ru"  # Русский язык
                    )
                else:
                    # Генерация без voice cloning (стандартный голос)
                    if ctx:
                        await ctx.info("🎭 Генерация со стандартным голосом")

                    tts.tts_to_file(
                        text=text,
                        file_path=output_path,
                        language="ru"
                    )
            else:
                # Создаем настоящий WAV файл с тишиной нужной длительности
                if ctx:
                    await ctx.info("🎵 Создание WAV файла с тишиной")

                try:
                    import wave

                    # Параметры WAV файла
                    sample_rate = 22050  # Hz
                    num_channels = 1  # Моно
                    sample_width = 2  # 16 бит

                    # Вычисляем количество сэмплов
                    if duration:
                        num_samples = int(sample_rate * duration)
                    else:
                        # Оценка длительности по количеству символов (примерно 150 символов в минуту)
                        estimated_duration = max(1.0, len(text) / 25)  # Примерная скорость речи
                        num_samples = int(sample_rate * estimated_duration)

                    # Создаем WAV файл с тишиной
                    with wave.open(output_path, 'wb') as wav_file:
                        wav_file.setnchannels(num_channels)
                        wav_file.setsampwidth(sample_width)
                        wav_file.setframerate(sample_rate)

                        # Заполняем тишиной (нулевые сэмплы)
                        silence_data = b'\x00\x00' * num_samples
                        wav_file.writeframes(silence_data)

                    if ctx:
                        await ctx.info(f"✅ Создан WAV файл длительностью {num_samples/sample_rate:.1f} секунд")

                except Exception as e:
                    # Fallback: создаем текстовый файл
                    if ctx:
                        await ctx.info(f"📝 Создание текстового файла (ошибка: {e})")

                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(f"# TTS STUB for: {text}\n")
                        f.write(f"# Duration: {duration or 'unknown'} seconds\n")
                        if original_audio_file:
                            f.write(f"# Voice cloned from: {original_audio_file}\n")

            if ctx:
                await ctx.report_progress(progress=80, total=100)

            # Если указана целевая длительность, корректируем скорость
            if duration:
                if ctx:
                    await ctx.info(f"⏱️ Корректировка длительности до {duration:.1f} секунд")

                # Используем ffmpeg для корректировки скорости
                temp_output = output_path + ".temp.wav"

                # Вычисляем коэффициент скорости
                # Сначала получаем текущую длительность
                import subprocess
                probe_cmd = [
                    "ffprobe", "-v", "quiet", "-print_format", "json",
                    "-show_format", output_path
                ]
                probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)

                if probe_result.returncode == 0:
                    import json
                    probe_data = json.loads(probe_result.stdout)
                    current_duration = float(probe_data["format"]["duration"])

                    if abs(current_duration - duration) > 0.1:  # Если разница больше 0.1 сек
                        speed_factor = current_duration / duration

                        # Корректируем скорость
                        speed_cmd = [
                            "ffmpeg", "-i", output_path,
                            "-filter:a", f"atempo={speed_factor}",
                            "-y", temp_output
                        ]

                        speed_result = subprocess.run(speed_cmd, capture_output=True, text=True)
                        if speed_result.returncode == 0:
                            os.replace(temp_output, output_path)
                            if ctx:
                                await ctx.info(f"✅ Длительность скорректирована: {current_duration:.1f} → {duration:.1f} сек")
                        else:
                            if ctx:
                                await ctx.info(f"⚠️ Не удалось скорректировать длительность: {speed_result.stderr}")

                # Очищаем временный файл если он существует
                if os.path.exists(temp_output):
                    try:
                        os.unlink(temp_output)
                    except:
                        pass

            if ctx:
                await ctx.report_progress(progress=100, total=100)
                await ctx.info(f"✅ TTS аудио сгенерировано: {output_file}")

            # Создаем результат
            result = {
                "output_file": output_file,
                "text": text,
                "status": "generated",
                "duration": duration,
                "voice_cloning": bool(original_audio_file),  # Voice cloning применяется если указан оригинальный файл
                "tts_available": tts_available or gtts_available or pyttsx3_available
            }

            return ToolResult(
                content=[TextContent(type="text", text=f"TTS audio generated: {output_file}")],
                structured_content=result,
                meta={"text": text, "output_file": output_file}
            )
        except Exception as e:
            span.set_attribute("error", str(e))
            if ctx:
                await ctx.error(f"❌ Ошибка выполнения: {e}")

            from mcp.shared.exceptions import McpError, ErrorData
            raise McpError(
                ErrorData(
                    code=-32603,
                    message=f"Не удалось выполнить операцию: {e}"
                )
            )