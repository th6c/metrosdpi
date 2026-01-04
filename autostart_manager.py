import os
import sys
import subprocess
from path_utils import get_base_path


class AutostartManager:
    """Управление автозапуском приложения в Windows через Task Scheduler
    
    Использует планировщик задач Windows для запуска приложения с правами администратора
    при входе пользователя в систему.
    """
    
    def __init__(self, app_name="MetrosDPI"):
        self.app_name = app_name
        self.task_name = f"\\{app_name}"  # Имя задачи в планировщике (с обратным слэшем)
    
    def is_enabled(self):
        """Проверяет, включен ли автозапуск (задача существует в планировщике)"""
        try:
            # Проверяем существование задачи через schtasks
            result = subprocess.run(
                ['schtasks', '/query', '/tn', self.task_name],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def enable(self):
        """Включает автозапуск через планировщик задач с правами администратора"""
        try:
            # Сначала удаляем существующую задачу, если она есть
            self.disable()
            
            # Получаем путь к исполняемому файлу
            if getattr(sys, 'frozen', False):
                # Если приложение упаковано (например, PyInstaller)
                exe_path = sys.executable
                work_dir = os.path.dirname(os.path.abspath(sys.executable))
            else:
                # Если запускается как скрипт Python
                script_path = os.path.abspath(__file__)
                # Получаем путь к main.py
                main_py = os.path.join(os.path.dirname(script_path), 'main.py')
                python_exe = sys.executable
                work_dir = os.path.dirname(os.path.abspath(main_py))
                # Формируем команду с аргументами
                exe_path = f'"{python_exe}" "{main_py}" --autostart'
            
            # Создаем задачу в планировщике задач
            # /tn - имя задачи
            # /tr - программа для запуска
            # /sc ONLOGON - запуск при входе пользователя в систему
            # /rl HIGHEST - запуск с наивысшими правами (администратор)
            # /f - принудительное создание (перезапись существующей)
            # /it - интерактивная задача (может взаимодействовать с пользователем)
            
            # Формируем команду для создания задачи
            # Для schtasks /tr должен содержать команду с аргументами в одной строке
            if getattr(sys, 'frozen', False):
                # Для скомпилированного приложения: путь к exe + аргумент --autostart
                task_command = f'"{exe_path}" --autostart'
            else:
                # Для скрипта Python: уже содержит python.exe, main.py и --autostart
                task_command = exe_path
            
            cmd = [
                'schtasks', '/create',
                '/tn', self.task_name,
                '/tr', task_command,
                '/sc', 'ONLOGON',
                '/rl', 'HIGHEST',
                '/f',
                '/it'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW,
                cwd=work_dir
            )
            
            if result.returncode == 0:
                return True
            else:
                print(f"Ошибка при создании задачи: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"Ошибка при включении автозапуска: {e}")
            return False
    
    def disable(self):
        """Выключает автозапуск (удаляет задачу из планировщика)"""
        try:
            # Удаляем задачу из планировщика
            result = subprocess.run(
                ['schtasks', '/delete', '/tn', self.task_name, '/f'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            # Возвращаем True даже если задача не существовала
            return True
        except Exception as e:
            print(f"Ошибка при выключении автозапуска: {e}")
            return False
    
    def toggle(self):
        """Переключает состояние автозапуска"""
        if self.is_enabled():
            return self.disable()
        else:
            return self.enable()

