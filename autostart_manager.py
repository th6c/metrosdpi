import os
import sys
import subprocess
from path_utils import get_base_path


class AutostartManager:
    """Управление автозапуском приложения в Windows через Task Scheduler
    
    Использует планировщик задач Windows для запуска приложения с правами администратора
    при входе пользователя в систему. Это стандартный способ, используемый крупными компаниями
    (FACEIT, Steam, Discord и т.д.).
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
        """Включает автозапуск через планировщик задач с правами администратора
        
        Использует стандартный подход крупных компаний:
        - Задача запускается при входе пользователя в систему
        - Запускается с наивысшими правами (администратор)
        - Настроена для работы в интерактивном режиме
        """
        try:
            # Сначала удаляем существующую задачу, если она есть
            self.disable()
            
            # Получаем путь к исполняемому файлу
            if getattr(sys, 'frozen', False):
                # Если приложение упаковано (например, PyInstaller)
                exe_path = sys.executable
                work_dir = os.path.dirname(os.path.abspath(sys.executable))
                # Для скомпилированного приложения: путь к exe + аргумент --autostart
                task_command = f'"{exe_path}" --autostart'
            else:
                # Если запускается как скрипт Python
                script_path = os.path.abspath(__file__)
                # Получаем путь к main.py
                main_py = os.path.join(os.path.dirname(script_path), 'main.py')
                python_exe = sys.executable
                work_dir = os.path.dirname(os.path.abspath(main_py))
                # Формируем команду с аргументами
                # Используем кавычки для путей с пробелами
                task_command = f'"{python_exe}" "{main_py}" --autostart'
            
            # Создаем задачу в планировщике задач
            # Используем стандартный подход крупных компаний:
            # /tn - имя задачи
            # /tr - программа для запуска (команда с аргументами)
            # /sc ONLOGON - запуск при входе пользователя в систему (как у FACEIT, Steam и т.д.)
            # /rl HIGHEST - запуск с наивысшими правами (администратор) - КЛЮЧЕВОЙ ПАРАМЕТР
            # /f - принудительное создание (перезапись существующей)
            # /it - интерактивная задача (может взаимодействовать с пользователем)
            # /ru SYSTEM - запуск от имени SYSTEM (опционально, можно использовать текущего пользователя)
            
            cmd = [
                'schtasks', '/create',
                '/tn', self.task_name,
                '/tr', task_command,
                '/sc', 'ONLOGON',  # При входе пользователя в систему
                '/rl', 'HIGHEST',   # С наивысшими правами (администратор)
                '/f',               # Принудительное создание
                '/it'               # Интерактивная задача
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
                # Дополнительно настраиваем задачу для надежности
                # Устанавливаем описание задачи
                try:
                    subprocess.run(
                        ['schtasks', '/change', '/tn', self.task_name, '/d', f'{self.app_name} Auto-start'],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                except Exception:
                    pass  # Не критично, если не удалось установить описание
                
                return True
            else:
                # Если не удалось создать задачу, выводим ошибку
                error_msg = result.stderr if result.stderr else result.stdout
                print(f"Ошибка при создании задачи планировщика: {error_msg}")
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
