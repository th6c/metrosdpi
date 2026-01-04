import sys
import ctypes
import os
from PyQt6.QtWidgets import QApplication, QMessageBox
from main_window import MainWindow
from path_utils import get_resource_path
 


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
            QMessageBox.critical(
                None,
                "Ошибка",
                f"Не удалось запросить права администратора:\n{str(e)}\n\n"
                "Пожалуйста, запустите программу от имени администратора вручную."
            )
            return False


def main():
    # Проверяем права администратора перед запуском приложения
    if not is_admin():
        # Показываем сообщение о необходимости прав администратора
        app = QApplication(sys.argv)
        reply = QMessageBox.question(
            None,
            "Требуются права администратора",
            "Для работы программы требуются права администратора.\n\n"
            "Перезапустить программу с правами администратора?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if not run_as_admin():
                sys.exit(0)
            else:
                sys.exit(0)
        else:
            sys.exit(0)
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
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

