import subprocess
import json
import os
def cut_video(input_file: str, output_file: str, start: float, end: float):
    """
    Вырезает фрагмент видео из input_file по времени [start, end]
    с точностью до 0.01 секунды.
    
    start и end — время в секундах (могут быть дробными).
    """
    duration = end - start
    if duration <= 0:
        raise ValueError("Конечное время должно быть больше начального")

    command = [
        "ffmpeg",
        "-y",                  # перезаписывать файл
        "-ss", f"{start:.2f}", # начало с точностью 0.01 сек
        "-i", input_file,
        "-t", f"{duration:.2f}", # длительность
        "-c", "copy",            # без перекодирования
        output_file
    ]

    subprocess.run(command, check=True)





def get_audio_duration(file_path: str) -> float:
    """
    Возвращает длительность аудиофайла в секундах (float).
    Требуется установленный ffprobe (идёт в составе FFmpeg).
    """
    command = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        file_path
    ]

    result = subprocess.run(command, capture_output=True, text=True)
    info = json.loads(result.stdout)
    duration = float(info["format"]["duration"])
    return duration




def change_video_speed(input_file: str, output_file: str,
                       original_length: float, target_length: float):
    """
    Меняет скорость видео так, чтобы его длительность стала target_length.
    
    original_length — текущая длительность видео (в секундах)
    target_length   — нужная длительность видео (в секундах)
    """
    if target_length <= 0:
        raise ValueError("Нужная длина должна быть > 0.")

    # коэффициент скорости
    speed = original_length / target_length

    # FFmpeg: 
    #   -vf "setpts=PTS/speed"     — ускорение/замедление видео 
    #   -filter:a "atempo=value"   — изменение аудио
    # atempo принимает значения от 0.5 до 2.0, поэтому если нужно больше —
    # выполняем в несколько шагов.
    atempo_filters = []
    remaining = speed
    while remaining > 2.0:
        atempo_filters.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        atempo_filters.append("atempo=0.5")
        remaining *= 2.0
    atempo_filters.append(f"atempo={remaining}")
    audio_filter = ",".join(atempo_filters)

    command = [
        "ffmpeg",
        "-y",
        "-i", input_file,
        "-vf", f"setpts={1/speed}*PTS",
        "-filter:a", audio_filter,
        output_file
    ]

    subprocess.run(command, check=True)




def video_to_audio(
    video_path: str,
    audio_path: str,
    audio_format: str = "mp3",
    bitrate: str = "192k"
):
    """
    Извлекает аудио из видеофайла с помощью ffmpeg.

    :param video_path: путь к входному видеофайлу
    :param audio_path: путь к выходному аудиофайлу (без расширения или с ним)
    :param audio_format: формат аудио (mp3, wav, aac и т.д.)
    :param bitrate: битрейт аудио (например 128k, 192k)
    """

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Файл не найден: {video_path}")

    if not audio_path.endswith(f".{audio_format}"):
        audio_path = f"{audio_path}.{audio_format}"

    command = [
        "ffmpeg",
        "-y",               # перезаписывать файл без вопроса
        "-i", video_path,   # входное видео
        "-vn",              # отключить видео
        "-ab", bitrate,     # битрейт аудио
        "-f", audio_format, # формат
        audio_path
    ]

    subprocess.run(command, check=True)
