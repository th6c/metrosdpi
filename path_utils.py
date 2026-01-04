"""
Утилита для определения правильных путей к файлам и папкам приложения.
Работает как при обычном запуске, так и после компиляции (PyInstaller).
"""
import os
import sys


def get_base_path():
    """
    Возвращает базовую директорию приложения.
    
    Для PyInstaller (скомпилированное приложение):
    - sys._MEIPASS содержит временную папку с распакованными файлами
    - sys.executable содержит путь к .exe файлу
    - Базовая директория - это директория, где находится .exe файл
    
    Для обычного запуска:
    - Базовая директория - это директория, где находится main.py
    """
    if getattr(sys, 'frozen', False):
        # Приложение скомпилировано (PyInstaller)
        # Базовая директория - это директория, где находится .exe файл
        if hasattr(sys, '_MEIPASS'):
            # Для PyInstaller: sys.executable - это путь к .exe
            base_path = os.path.dirname(os.path.abspath(sys.executable))
        else:
            # Fallback
            base_path = os.path.dirname(os.path.abspath(sys.executable))
    else:
        # Обычный запуск скрипта
        # Базовая директория - это директория, где находится main.py
        # Получаем путь к текущему файлу и поднимаемся на уровень выше
        # (если path_utils.py находится в корне проекта)
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return base_path


def get_resource_path(relative_path):
    """
    Возвращает абсолютный путь к ресурсу.
    
    Для PyInstaller:
    - Ресурсы могут быть в sys._MEIPASS (временная папка) или рядом с .exe
    
    Args:
        relative_path: Относительный путь к ресурсу (например, "app/resources/assets/icon.ico")
    
    Returns:
        Абсолютный путь к ресурсу
    """
    base_path = get_base_path()
    
    # Сначала проверяем рядом с исполняемым файлом
    resource_path = os.path.join(base_path, relative_path)
    if os.path.exists(resource_path):
        return resource_path
    
    # Если не найдено, проверяем в sys._MEIPASS (для PyInstaller)
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        resource_path = os.path.join(sys._MEIPASS, relative_path)
        if os.path.exists(resource_path):
            return resource_path
    
    # Возвращаем путь относительно базовой директории в любом случае
    return os.path.join(base_path, relative_path)


def get_config_path(relative_path="app/config/app.json"):
    """
    Возвращает путь к файлу конфигурации.
    Конфигурация всегда должна быть рядом с исполняемым файлом, а не в sys._MEIPASS.
    
    Args:
        relative_path: Относительный путь к файлу конфигурации
    
    Returns:
        Абсолютный путь к файлу конфигурации
    """
    base_path = get_base_path()
    return os.path.join(base_path, relative_path)


def get_winws_path():
    """
    Возвращает путь к папке winws.
    Папка winws всегда должна быть рядом с исполняемым файлом.
    
    Returns:
        Абсолютный путь к папке winws
    """
    base_path = get_base_path()
    return os.path.join(base_path, "winws")


