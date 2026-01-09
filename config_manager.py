import json
import os
from pathlib import Path
from path_utils import get_base_path


class ConfigManager:
    def __init__(self, config_path="app/config/app.json"):
        # Если путь относительный, делаем его абсолютным относительно базовой директории
        if not os.path.isabs(config_path):
            base_path = get_base_path()
            self.config_path = os.path.join(base_path, config_path)
        else:
            self.config_path = config_path
        self.default_settings = {
            'language': 'ru',
            'show_in_tray': True,
            'close_winws_on_exit': True,
            'start_minimized': False,
            'auto_start_last_strategy': False,
            'add_b_flag_on_update': False,
            'last_strategy': '',
            'auto_restart_strategy': False,
            'game_filter_enabled': False,
            'ipset_filter_mode': 'loaded'  # 'loaded', 'none', 'any'
        }
        self.ensure_config_file()
    
    def ensure_config_dir(self):
        """Создает папку конфигурации, если её нет"""
        config_dir = os.path.dirname(self.config_path)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
    
    def ensure_config_file(self):
        """Создает папку и файл конфигурации с настройками по умолчанию, если их нет"""
        self.ensure_config_dir()
        
        if not os.path.exists(self.config_path):
            # Создаем файл напрямую, без вызова save_settings, чтобы избежать рекурсии
            try:
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(self.default_settings, f, indent=4, ensure_ascii=False)
            except IOError as e:
                print(f"Ошибка при создании файла конфигурации: {e}")
    
    def load_settings(self):
        """Загружает настройки из JSON файла"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    # Объединяем с настройками по умолчанию на случай, если какие-то ключи отсутствуют
                    merged_settings = {**self.default_settings, **settings}
                    return merged_settings
            else:
                return self.default_settings.copy()
        except (json.JSONDecodeError, IOError) as e:
            print(f"Ошибка при загрузке настроек: {e}")
            return self.default_settings.copy()
    
    def save_settings(self, settings):
        """Сохраняет настройки в JSON файл"""
        try:
            # Убеждаемся, что папка существует
            self.ensure_config_dir()
            # Сохраняем настройки
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"Ошибка при сохранении настроек: {e}")
            return False
    
    def get_setting(self, key, default=None):
        """Получает значение настройки"""
        settings = self.load_settings()
        return settings.get(key, default)
    
    def set_setting(self, key, value):
        """Устанавливает значение настройки и сохраняет"""
        settings = self.load_settings()
        settings[key] = value
        self.save_settings(settings)
    
    def update_settings(self, updates):
        """Обновляет несколько настроек одновременно"""
        settings = self.load_settings()
        settings.update(updates)
        self.save_settings(settings)

