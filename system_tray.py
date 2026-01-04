from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QObject
from translator import tr
from path_utils import get_resource_path


class SystemTray(QSystemTrayIcon):
    def __init__(self, parent_window):
        super().__init__()
        self.parent_window = parent_window
        self.init_ui()
    
    def init_ui(self):
        # Сначала пытаемся получить иконку из главного окна (она уже установлена там)
        icon = None
        if self.parent_window:
            icon = self.parent_window.windowIcon()
        
        # Если иконка не установлена в окне или пустая, пробуем загрузить по пути
        if not icon or icon.isNull():
            icon_path = get_resource_path("app/resources/assets/icon.ico")
            icon = QIcon(icon_path)
        
        # Если все еще пустая, используем системную
        if icon.isNull():
            icon = QIcon.fromTheme('application-x-executable')
            if icon.isNull():
                icon = QIcon()
        
        self.setIcon(icon)
        
        # Создаем контекстное меню
        self.menu = QMenu()
        
        # Действие для показа/скрытия окна (будет обновляться динамически)
        self.toggle_window_action = QAction('', self)
        self.toggle_window_action.triggered.connect(self.toggle_window)
        self.menu.addAction(self.toggle_window_action)
        
        self.menu.addSeparator()
        
        # Действие "Выход"
        self.quit_action = QAction('', self)
        self.quit_action.triggered.connect(self.quit_application)
        self.menu.addAction(self.quit_action)
        
        self.setContextMenu(self.menu)
        
        # Обработка клика по иконке
        self.activated.connect(self.tray_icon_activated)
        
        # Применяем переводы и обновляем меню
        lang = 'ru'
        if self.parent_window and hasattr(self.parent_window, 'settings'):
            lang = self.parent_window.settings.get('language', 'ru')
        self.update_menu()
    
    def tray_icon_activated(self, reason):
        """Обработка активации иконки в трее"""
        # Обрабатываем как одиночный клик, так и двойной клик
        if reason == QSystemTrayIcon.ActivationReason.Trigger or reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_window()
    
    def toggle_window(self):
        """Переключает видимость окна"""
        if self.parent_window:
            if self.parent_window.isVisible():
                self.hide_window()
            else:
                self.show_window()
            # Обновляем меню после изменения состояния
            self.update_menu()
    
    def show_window(self):
        """Показывает главное окно"""
        if self.parent_window:
            self.parent_window.show()
            self.parent_window.raise_()
            self.parent_window.activateWindow()
            # Обновляем меню после показа
            self.update_menu()
    
    def hide_window(self):
        """Скрывает главное окно"""
        if self.parent_window:
            self.parent_window.hide()
            # Обновляем меню после скрытия
            self.update_menu()
    
    def quit_application(self):
        """Закрывает приложение"""
        QApplication.quit()
    
    def show_message(self, title, message, duration=2000):
        """Показывает уведомление в трее"""
        self.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, duration)
    
    def update_menu(self):
        """Обновляет меню в зависимости от состояния окна"""
        lang = 'ru'
        if self.parent_window and hasattr(self.parent_window, 'settings'):
            lang = self.parent_window.settings.get('language', 'ru')
        
        if self.parent_window and self.parent_window.isVisible():
            # Если окно видимо, показываем "Свернуть"
            if hasattr(self, 'toggle_window_action'):
                self.toggle_window_action.setText(tr('tray_minimize', lang))
        else:
            # Если окно скрыто, показываем "Показать"
            if hasattr(self, 'toggle_window_action'):
                self.toggle_window_action.setText(tr('tray_show', lang))
        
        if hasattr(self, 'quit_action'):
            self.quit_action.setText(tr('tray_quit', lang))
    
    def retranslate_ui(self, lang='ru'):
        """Обновляет тексты меню трея в соответствии с языком"""
        self.update_menu()

