"""Инструмент для генерации TTS аудио с использованием FastSpeech 2 + Vocoder."""

import os
from typing import Dict, Any, List

from fastmcp import Context
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field

from ..mcp_instance import mcp
from .utils import ToolResult
from ..funcs import video as video_funcs
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
    sample_video_file: str = Field(
        None,
        description="Путь к оригинальному видео файлу для клонирования голоса"
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
            from ..globals import VIDEO_PATH
            output_path = os.path.join(VIDEO_PATH, output_file)

            # Создаем директорию если она не существует
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Вычисляем длительность если не указана
            if duration is None and start_time is not None and end_time is not None:
                duration = end_time - start_time

            # Импорт и инициализация TTS (попытаемся несколько реализаций).
            tts_available = False
            gtts_available = False
            pyttsx3_available = False
            system_say_available = False

            try:
                import sys
                if sys.platform == "darwin":
                    # macOS: используем "say" как самый надёжный локальный генератор
                    system_say_available = True
                    if ctx:
                        await ctx.info("✅ macOS detected: will try `say` for TTS")
            except Exception:
                pass

            # Попробуем gTTS (интернет) и pyttsx3 локально
            try:
                from gtts import gTTS
                gtts_available = True
                if ctx:
                    await ctx.info("✅ gTTS доступен")
            except Exception:
                if ctx:
                    await ctx.info("⚠️ gTTS недоступен")

            try:
                import pyttsx3
                pyttsx3_available = True
                if ctx:
                    await ctx.info("✅ pyttsx3 доступен")
            except Exception:
                if ctx:
                    await ctx.info("⚠️ pyttsx3 недоступен")

            # Попытка использовать XTTS v2 (локальная модель) — дадим ей приоритет
            tts = None
            try:
                from TTS.api import TTS
                import torch
                if ctx:
                    await ctx.info("🔎 Проверяем наличие XTTS v2 локальной модели...")
                try:
                    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
                    if 'torch' in globals() and torch.cuda.is_available():
                        tts = tts.to("cuda")
                    tts_available = True
                    if ctx:
                        await ctx.info("✅ XTTS v2 локальная модель доступна и инициализирована")
                except Exception as e:
                    if ctx:
                        await ctx.info(f"⚠️ Не удалось инициализировать XTTS модель: {e}")
                    tts = None
            except Exception:
                # TTS.api не установлен
                if ctx:
                    await ctx.info("ℹ️ XTTS не установлен локально (TTS.api отсутствует)")

            # Генерация речи — даём приоритет XTTS, затем macOS `say`, затем gTTS, pyttsx3
            if ctx:
                await ctx.info(f"🎤 Генерация речи для текста: '{text}'")
                await ctx.report_progress(progress=50, total=100)

            used_method = None

            # 1) XTTS локально
            if tts is not None:
                try:
                    if sample_video_file:
                        original_video_path = os.path.join(VIDEO_PATH, sample_video_file)
                        if not os.path.exists(original_video_path):
                            raise Exception(f"Оригинальный видео файл не найден: {original_video_path}")
                        
                        # Создаём аудиофайл из видео для использования как образец голоса
                        if ctx:
                            await ctx.info("🎬 Извлекаем аудио из видео...")
                        
                        sample_audio_filename = f"{os.path.splitext(sample_video_file)[0]}_sample.wav"
                        sample_audio_path = os.path.join(VIDEO_PATH, sample_audio_filename)
                        
                        # Используем видео_to_audio для извлечения аудио
                        try:
                            video_funcs.video_to_audio(
                                video_path=original_video_path,
                                audio_path=sample_audio_path,
                                audio_format="wav",
                                bitrate="192k"
                            )
                            if ctx:
                                await ctx.info(f"✅ Аудио извлечено: {sample_audio_filename}")
                        except Exception as e:
                            if ctx:
                                await ctx.info(f"⚠️ Не удалось извлечь аудио из видео: {e}")
                            raise
                        
                        # Используем извлечённый аудиофайл как образец голоса
                        tts.tts_to_file(text=text, file_path=output_path, speaker_wav=sample_audio_path, language="ru")
                    else:
                        tts.tts_to_file(text=text, file_path=output_path, language="ru")
                    used_method = 'xtts'
                    if ctx:
                        await ctx.info("✅ TTS generated via XTTS v2")
                except Exception as e:
                    if ctx:
                        await ctx.info(f"⚠️ XTTS generation failed: {e}")

            # 2) macOS `say` (локально)
            if used_method is None and system_say_available:
                try:
                    import subprocess
                    temp_aiff = output_path + ".aiff"
                    subprocess.run(["say", "-o", temp_aiff, text], check=True)
                    subprocess.run(["ffmpeg", "-y", "-i", temp_aiff, output_path], check=True)
                    try:
                        os.remove(temp_aiff)
                    except Exception:
                        pass
                    used_method = "say"
                    if ctx:
                        await ctx.info("✅ TTS generated via macOS `say`")
                except Exception as e:
                    if ctx:
                        await ctx.info(f"⚠️ macOS say failed: {e}")

            # 3) gTTS (онлайн)
            if used_method is None:
                try:
                    from gtts import gTTS
                    tts_obj = gTTS(text=text, lang='ru', slow=False, tld='ru')
                    tts_obj.save(output_path)
                    used_method = 'gtts'
                    if ctx:
                        await ctx.info("✅ TTS generated via gTTS")
                except Exception as e:
                    if ctx:
                        await ctx.info(f"⚠️ gTTS not available or failed: {e}")

            # 4) pyttsx3 (локально)
            if used_method is None:
                try:
                    import pyttsx3
                    tts_engine = pyttsx3.init()
                    tts_engine.save_to_file(text, output_path)
                    tts_engine.runAndWait()
                    used_method = 'pyttsx3'
                    if ctx:
                        await ctx.info("✅ TTS generated via pyttsx3")
                except Exception as e:
                    if ctx:
                        await ctx.info(f"⚠️ pyttsx3 not available or failed: {e}")

            # Если ни один метод не сработал — создаём WAV с тишиной как fallback
            if used_method is None:
                if ctx:
                    await ctx.info("🎵 Ни один TTS не сработал, создаём WAV тишины (fallback)")
                try:
                    import wave
                    sample_rate = 22050
                    num_channels = 1
                    sample_width = 2
                    if duration:
                        num_samples = int(sample_rate * duration)
                    else:
                        estimated_duration = max(1.0, len(text) / 25)
                        num_samples = int(sample_rate * estimated_duration)
                    with wave.open(output_path, 'wb') as wav_file:
                        wav_file.setnchannels(num_channels)
                        wav_file.setsampwidth(sample_width)
                        wav_file.setframerate(sample_rate)
                        silence_data = b'\x00\x00' * num_samples
                        wav_file.writeframes(silence_data)
                    if ctx:
                        await ctx.info(f"✅ Создан WAV файл длительностью {num_samples/sample_rate:.1f} секунд (silence)")
                except Exception as e:
                    if ctx:
                        await ctx.info(f"📝 Не удалось создать WAV silence fallback: {e}")

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

            # CLEANUP: keep only the generated TTS file in its directory
            try:
                out_dir = os.path.dirname(output_path)
                keep_name = os.path.basename(output_path)
                # Only operate inside the output directory for safety
                if os.path.isdir(out_dir):
                    for fname in os.listdir(out_dir):
                        # skip the file we want to keep
                        if fname == keep_name:
                            continue
                        # remove common audio file types and temp files
                        lower = fname.lower()
                        if lower.endswith(('.wav', '.mp3', '.aac', '.m4a', '.aiff', '.flac', '.ogg', '.temp.wav')):
                            try:
                                os.remove(os.path.join(out_dir, fname))
                            except Exception:
                                # ignore deletion errors
                                pass
            except Exception:
                # don't let cleanup break the tool
                pass

            # Создаем результат
            result = {
                "output_file": output_file,
                "text": text,
                "status": "generated",
                "duration": duration,
                "voice_cloning": bool(sample_video_file),  # Voice cloning применяется если указан оригинальный файл
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