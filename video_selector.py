#!/usr/bin/env python3
"""
Интерактивная система выбора видео файлов для обработки.
"""

import os
import glob
from pathlib import Path
from typing import List, Dict, Any, Optional


class VideoSelector:
    """Класс для интерактивного выбора видео файлов."""
    
    def __init__(self, video_directory: str = "./videos"):
        """
        Инициализация селектора видео.
        
        Args:
            video_directory: Каталог с видео файлами
        """
        self.video_directory = Path(video_directory)
        self.supported_formats = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv'}
    
    def find_video_files(self) -> List[Dict[str, Any]]:
        """
        Находит все видео файлы в указанном каталоге.
        
        Returns:
            Список словарей с информацией о видео файлах
        """
        video_files = []
        
        if not self.video_directory.exists():
            print(f"❌ Каталог {self.video_directory} не существует!")
            return video_files
        
        # Ищем файлы всех поддерживаемых форматов (нечувствительно к регистру)
        for item in self.video_directory.iterdir():
            if item.is_file():
                file_ext = item.suffix.lower()
                if file_ext in self.supported_formats:
                    file_info = self._get_file_info(str(item))
                    if file_info:
                        video_files.append(file_info)
        
        # Сортируем по имени файла
        video_files.sort(key=lambda x: x['name'].lower())
        return video_files
    
    def _get_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о видео файле.
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Словарь с информацией о файле или None
        """
        try:
            path = Path(file_path)
            stat = path.stat()
            
            # Получаем размер файла в МБ
            size_mb = stat.st_size / (1024 * 1024)
            
            return {
                'name': path.name,
                'full_path': str(path.absolute()),
                'size_mb': round(size_mb, 2),
                'extension': path.suffix.lower(),
                'modified': stat.st_mtime
            }
        except Exception as e:
            print(f"⚠️ Ошибка при получении информации о файле {file_path}: {e}")
            return None
    
    def display_video_list(self, video_files: List[Dict[str, Any]]) -> None:
        """
        Отображает список доступных видео файлов.
        
        Args:
            video_files: Список видео файлов
        """
        print("\n🎬 ДОСТУПНЫЕ ВИДЕО ФАЙЛЫ:")
        print("=" * 60)
        
        if not video_files:
            print("📁 В каталоге ./videos/ не найдено видео файлов!")
            print("\n💡 Для добавления видео:")
            print("   1. Скопируйте видео файл в каталог ./videos/")
            print("   2. Поддерживаемые форматы: MP4, AVI, MOV, MKV, WEBM, FLV, WMV")
            return
        
        print(f"📁 Каталог: {self.video_directory.absolute()}")
        print(f"🎯 Найдено файлов: {len(video_files)}")
        print()
        
        for i, video in enumerate(video_files, 1):
            print(f"{i:2d}. 📹 {video['name']}")
            print(f"    📊 Размер: {video['size_mb']} МБ")
            print(f"    🏷️  Формат: {video['extension'].upper()}")
            print(f"    📍 Путь: {video['full_path']}")
            print()
    
    def get_user_selection(self, video_files: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Получает выбор пользователя.
        
        Args:
            video_files: Список доступных видео файлов
            
        Returns:
            Выбранный файл или None
        """
        if not video_files:
            return None
        
        while True:
            try:
                print("❓ Выберите видео файл для обработки (введите номер) или 'q' для выхода:")
                user_input = input("👉 Ваш выбор: ").strip().lower()
                
                if user_input in ['q', 'quit', 'exit', 'выход']:
                    print("👋 Выбор отменен пользователем.")
                    return None
                
                # Пытаемся преобразовать в число
                try:
                    index = int(user_input) - 1  # Пользователь вводит с 1, мы используем 0-based
                    if 0 <= index < len(video_files):
                        selected = video_files[index]
                        print(f"\n✅ Выбран файл: {selected['name']}")
                        print(f"📊 Размер: {selected['size_mb']} МБ")
                        print(f"🏷️  Формат: {selected['extension'].upper()}")
                        return selected
                    else:
                        print(f"❌ Неверный номер! Введите число от 1 до {len(video_files)}")
                except ValueError:
                    print("❌ Введите корректный номер или 'q' для выхода")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Выбор прерван пользователем.")
                return None
            except Exception as e:
                print(f"❌ Ошибка при обработке ввода: {e}")
    
    def interactive_selection(self) -> Optional[Dict[str, Any]]:
        """
        Интерактивный процесс выбора видео файла.
        
        Returns:
            Выбранный файл или None
        """
        print("🎯 ИНТЕРАКТИВНЫЙ ВЫБОР ВИДЕО ФАЙЛА")
        print("=" * 50)
        
        # Находим видео файлы
        video_files = self.find_video_files()
        
        # Отображаем список
        self.display_video_list(video_files)
        
        # Получаем выбор пользователя
        selected = self.get_user_selection(video_files)
        
        return selected
    
    def get_video_by_name(self, video_name: str) -> Optional[Dict[str, Any]]:
        """
        Получает видео файл по имени.
        
        Args:
            video_name: Имя файла для поиска
            
        Returns:
            Информация о файле или None
        """
        video_files = self.find_video_files()
        
        for video in video_files:
            if video['name'].lower() == video_name.lower():
                return video
        
        return None


# Функция для интеграции с LLM системой
def prompt_video_selection() -> Optional[str]:
    """
    Функция для интеграции с основной системой.
    Возвращает путь к выбранному видео файлу.
    
    Returns:
        Путь к выбранному видео файлу или None
    """
    selector = VideoSelector()
    selected = selector.interactive_selection()
    
    if selected:
        return selected['full_path']
    return None


# Демонстрация использования
if __name__ == "__main__":
    # Тестирование селектора
    selector = VideoSelector()
    
    print("🎬 ТЕСТ СИСТЕМЫ ВЫБОРА ВИДЕО")
    print("=" * 40)
    
    # Находим файлы
    videos = selector.find_video_files()
    
    # Отображаем список
    selector.display_video_list(videos)
    
    if videos:
        # Интерактивный выбор
        selected = selector.get_user_selection(videos)
        
        if selected:
            print(f"\n🎉 ФИНАЛЬНЫЙ ВЫБОР:")
            print(f"📹 Файл: {selected['name']}")
            print(f"📊 Размер: {selected['size_mb']} МБ")
            print(f"📍 Путь: {selected['full_path']}")
    else:
        print("💡 Добавьте видео файлы в каталог ./videos/ для тестирования")