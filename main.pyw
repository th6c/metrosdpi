import sys
import ctypes
import os
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon
from main_window import MainWindow
from path_utils import get_resource_path, get_config_path
from translator import tr
from config_manager import ConfigManager
 


def is_admin():
    """Проверяет, запущена ли программа от имени администратора"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def run_as_admin():
    """Перезапускает программу с правами администратора"""
    if is_admin():
        return True
    else:
        # Перезапускаем с правами администратора
        try:
            # Получаем путь к исполняемому файлу Python и скрипту
            script = os.path.abspath(sys.argv[0])
            params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
            
            # Запускаем с правами администратора
            ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",  # Запрашиваем права администратора
                sys.executable,  # Путь к Python
                f'"{script}" {params}',  # Аргументы
                None,
                1  # SW_SHOWNORMAL
            )
            return False
        except Exception as e:
            # Если не удалось перезапустить, показываем сообщение
            app = QApplication(sys.argv)
            
            # Загружаем настройки для определения языка
            config_path = get_config_path("app/config/app.json")
            config = ConfigManager(config_path)
            settings = config.load_settings()
            lang = settings.get('language', 'ru')
            
            # Загружаем иконку приложения
            icon_path = get_resource_path("app/resources/assets/icon.ico")
            icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
            
            # Создаем диалоговое окно с иконкой
            msg_box = QMessageBox()
            msg_box.setWindowIcon(icon)
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle(tr('admin_error_title', lang))
            msg_box.setText(tr('admin_error_text', lang).format(str(e)))
            msg_box.exec()
            return False


def main():
    # Проверяем права администратора перед запуском приложения
    if not is_admin():
        # Показываем сообщение о необходимости прав администратора
        app = QApplication(sys.argv)
        
        # Загружаем настройки для определения языка
        config_path = get_config_path("app/config/app.json")
        config = ConfigManager(config_path)
        settings = config.load_settings()
        lang = settings.get('language', 'ru')
        
        # Загружаем иконку приложения
        icon_path = get_resource_path("app/resources/assets/icon.ico")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
        
        # Создаем диалоговое окно с иконкой
        msg_box = QMessageBox()
        msg_box.setWindowIcon(icon)
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setWindowTitle(tr('admin_required_title', lang))
        msg_box.setText(tr('admin_required_text', lang))
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)
        
        reply = msg_box.exec()
        
        if reply == QMessageBox.StandardButton.Yes:
            if not run_as_admin():
                sys.exit(0)
            else:
                sys.exit(0)
        else:
            sys.exit(0)
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setApplicationName('MetrosDPI')
    app.setOrganizationName('Metros Software')

    
    # Загружаем стили из QSS файла
    try:
        qss_path = get_resource_path("app/resources/styles/app.qss")
        if os.path.exists(qss_path):
            with open(qss_path, 'r', encoding='utf-8') as f:
                app.setStyleSheet(f.read())
    except Exception as e:
        # Если не удалось загрузить стили, продолжаем без них
        print(f"Не удалось загрузить стили: {e}")
 
    # Предотвращаем закрытие приложения при закрытии окна
    app.setQuitOnLastWindowClosed(False)
    
    window = MainWindow()
    
    # MainWindow сам решает, показывать окно или нет в зависимости от настроек
    # (в методе __init__ вызывается self.show() или self.hide())
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

