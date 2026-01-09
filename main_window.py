from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtGui import QDesktopServices
from system_tray import SystemTray
from config_manager import ConfigManager
from translator import tr
from autostart_manager import AutostartManager
from zapret_updater import ZapretUpdater
from test_window import TestWindow
from path_utils import get_base_path, get_resource_path, get_config_path, get_winws_path
import os
import subprocess
import psutil
import winreg


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.bat_process = None  # Процесс запущенного .bat файла
        self.running_strategy = None  # Название запущенной стратегии для перезапуска
        self.is_restarting = False  # Флаг для предотвращения множественных перезапусков
        self.user_stopped = False  # Флаг явной остановки пользователем (чтобы не запускать автоперезапуск)
        self.bat_start_time = None  # Время запуска .bat файла (для проверки появления winws.exe)
        self.process_monitor_timer = QTimer(self)  # Таймер для отслеживания процесса
        self.process_monitor_timer.timeout.connect(self.check_winws_process)
        # Инициализация менеджера конфигурации
        config_path = get_config_path("app/config/app.json")
        self.config = ConfigManager(config_path)
        # Загружаем настройки из файла
        self.settings = self.config.load_settings()
        # Инициализация менеджера автозапуска
        self.autostart_manager = AutostartManager()
        # Инициализация менеджера обновлений zapret
        self.zapret_updater = ZapretUpdater()
        self.init_ui()
        self.init_menu_bar()
        self.init_tray()
        self.center_window()
        # Применяем переводы после инициализации всех компонентов
        self.retranslate_ui()
        
        # Обновляем статусы фильтров после инициализации меню
        if hasattr(self, 'game_filter_action'):
            self.update_filter_statuses()
        
        # Если включена настройка start_minimized, сворачиваем в трей при запуске
        if self.settings.get('start_minimized', False):
            # Скрываем окно в трей, если включена настройка
            self.hide()
        else:
            # Показываем окно, если настройка выключена
            self.show()
        
        # Запускаем мониторинг процесса (проверка каждые 1 секунду)
        self.process_monitor_timer.start(1000)
        
        # Если включен автозапуск последней стратегии, запускаем её
        if self.settings.get('auto_start_last_strategy', False):
            # Небольшая задержка, чтобы окно успело полностью инициализироваться
            QTimer.singleShot(1000, lambda: self.auto_start_last_strategy())
    
    def _is_autostart(self):
        """Проверяет, запущено ли приложение через автозапуск"""
        # Проверяем аргумент командной строки --autostart
        import sys
        if '--autostart' in sys.argv:
            return True
        
        # Проверяем, включен ли автозапуск (через Task Scheduler)
        if self.autostart_manager.is_enabled():
            # Дополнительная проверка: если родительский процесс - explorer.exe, winlogon.exe или userinit.exe,
            # и автозапуск включен, то вероятно это автозапуск
            try:
                current_process = psutil.Process()
                parent = current_process.parent()
                if parent:
                    parent_name = parent.name().lower()
                    # Если родитель - explorer.exe и автозапуск включен, это может быть автозапуск
                    # Но explorer.exe также может быть родителем при обычном запуске
                    # Поэтому проверяем только winlogon.exe и userinit.exe как более надежные индикаторы
                    if parent_name in ['winlogon.exe', 'userinit.exe']:
                        return True
                    # Для explorer.exe используем дополнительную проверку - время запуска
                    # При автозапуске процесс обычно запускается сразу после входа в систему
                    if parent_name == 'explorer.exe':
                        # Проверяем, что процесс запущен недавно (в течение последних 30 секунд)
                        # Это может указывать на автозапуск
                        import time
                        process_create_time = current_process.create_time()
                        current_time = time.time()
                        if current_time - process_create_time < 30:
                            return True
            except Exception:
                pass
        
        return False
    
    def init_ui(self):
        self.setWindowTitle('MetrosDPI')
        # Фиксированный размер окна
        self.setFixedSize(640, 480)
        # Убираем кнопки минимизации и максимизации, оставляем только закрытие
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint)
        icon_path = get_resource_path("app/resources/assets/icon.ico")
        self.setWindowIcon(QIcon(icon_path))
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной layout
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 10)
        central_widget.setLayout(layout)
        
        # Добавляем растягивающий элемент сверху, чтобы элементы были по центру
        layout.addStretch()
        
        # ComboBox
        self.combo_box = QComboBox()
        self.load_bat_files()
        # Восстанавливаем последнюю выбранную стратегию
        self.restore_last_strategy()
        # Сохраняем стратегию при изменении
        self.combo_box.currentTextChanged.connect(self.on_strategy_changed)
        self.combo_box.setMinimumHeight(35)
        self.combo_box.setMinimumWidth(300)
        # Выравниваем ComboBox по центру
        combo_layout = QHBoxLayout()
        combo_layout.addStretch()
        combo_layout.addWidget(self.combo_box)
        combo_layout.addStretch()
        layout.addLayout(combo_layout)
        
        # Кнопка Запустить/Остановить
        self.action_button = QPushButton('')
        self.action_button.setMinimumHeight(40)
        self.action_button.setMinimumWidth(300)  # Та же ширина, что и у ComboBox
        self.action_button.clicked.connect(self.toggle_action)
        # Выравниваем кнопку по центру
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.action_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Добавляем растягивающий элемент, чтобы версия была внизу
        layout.addStretch()
        
        # Виджет с информацией о версии и MD5
        self.version_label = QLabel()
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.version_label.setStyleSheet("color: gray; font-size: 10px;")
        self.load_version_info()
        layout.addWidget(self.version_label)
        
        # Сохраняем ссылки на меню для обновления переводов
        self.menubar = None
        self.settings_menu = None
        self.update_menu = None
        self.language_menu = None
        self.check_updates_action = None
        self.manual_update_action = None
    
    def init_menu_bar(self):
        """Создает меню бар"""
        self.menubar = self.menuBar()
        
        # Меню "Tools"
        self.tools_menu = self.menubar.addMenu('')
        
        # Запуск теста
        self.run_test_action = QAction('', self)
        self.run_test_action.triggered.connect(self.show_test_window)
        self.tools_menu.addAction(self.run_test_action)
        
        # Run Diagnostics
        self.run_diagnostics_action = QAction('', self)
        self.run_diagnostics_action.triggered.connect(self.run_diagnostics)
        self.tools_menu.addAction(self.run_diagnostics_action)
        
        # Меню "Настройки"
        self.settings_menu = self.menubar.addMenu('')
        
        # Параметры программы
        self.open_settings_action = QAction('', self)
        self.open_settings_action.triggered.connect(self.show_settings_dialog)
        self.settings_menu.addAction(self.open_settings_action)
        
        self.settings_menu.addSeparator()
        
        # Game Filter
        self.game_filter_action = QAction('', self)
        self.game_filter_action.setCheckable(True)
        self.game_filter_action.triggered.connect(self.toggle_game_filter)
        self.settings_menu.addAction(self.game_filter_action)
        
        # IPSet Filter
        self.ipset_filter_action = QAction('', self)
        self.ipset_filter_action.setCheckable(True)
        self.ipset_filter_action.triggered.connect(self.toggle_ipset_filter)
        self.settings_menu.addAction(self.ipset_filter_action)
        
        # Обновляем статусы
        self.update_filter_statuses()
        
        # Сохраняем ссылки на действия для обновления в диалоге настроек
        # (они больше не в меню, но нужны для синхронизации)
        self.show_tray_action = None
        self.start_minimized_action = None
        self.close_winws_action = None
        self.autostart_action = None
        self.auto_start_action = None
        self.auto_restart_action = None
        self.language_menu = None
        
        # Меню "Обновление"
        self.update_menu = self.menubar.addMenu('')
        
        # Проверить наличие обновление стратегий zapret
        self.check_updates_action = QAction('', self)
        self.check_updates_action.triggered.connect(self.check_zapret_updates)
        self.update_menu.addAction(self.check_updates_action)
        
        # Обновить стратегии в ручную
        self.manual_update_action = QAction('', self)
        self.manual_update_action.triggered.connect(self.manual_update_strategies)
        self.update_menu.addAction(self.manual_update_action)
        
        self.update_menu.addSeparator()
        
        # Update IPSet List
        self.update_ipset_action = QAction('', self)
        self.update_ipset_action.triggered.connect(self.update_ipset_list)
        self.update_menu.addAction(self.update_ipset_action)
        
        # Update Hosts File
        self.update_hosts_action = QAction('', self)
        self.update_hosts_action.triggered.connect(self.update_hosts_file)
        self.update_menu.addAction(self.update_hosts_action)
        
        # Меню "Справка"
        self.help_menu = self.menubar.addMenu('')
        
        # Открыть страницу Github
        self.open_github_action = QAction('', self)
        self.open_github_action.triggered.connect(self.open_github)
        self.help_menu.addAction(self.open_github_action)
        
        # Открыть справку программы
        self.open_help_action = QAction('', self)
        self.open_help_action.triggered.connect(self.open_help)
        self.help_menu.addAction(self.open_help_action)
        
        # Открыть Github Flowseal zapret
        self.open_github_zapret_action = QAction('', self)
        self.open_github_zapret_action.triggered.connect(self.open_github_zapret)
        self.help_menu.addAction(self.open_github_zapret_action)
    
    def update_strategies_menu(self, menu):
        """Обновляет меню со списком стратегий"""
        menu.clear()
        winws_folder = get_winws_path()
        
        # Добавляем пункт "Открыть папку winws"
        lang = self.settings.get('language', 'ru')
        open_folder_action = QAction(tr('strategies_open_winws_folder', lang), self)
        open_folder_action.triggered.connect(self.open_winws_folder)
        menu.addAction(open_folder_action)
        
        # Добавляем разделитель
        menu.addSeparator()
        
        if os.path.exists(winws_folder):
            bat_files = []
            for filename in os.listdir(winws_folder):
                if filename.endswith('.bat') and os.path.isfile(os.path.join(winws_folder, filename)):
                    name_without_ext = filename[:-4]
                    bat_files.append((name_without_ext, filename))
            
            bat_files.sort(key=lambda x: x[0])
            
            for name, filename in bat_files:
                action = QAction(name, self)
                action.triggered.connect(lambda checked, f=filename: self.select_strategy(f))
                menu.addAction(action)
        else:
            action = QAction(tr('msg_winws_not_found', lang), self)
            action.setEnabled(False)
            menu.addAction(action)
    
    def select_strategy(self, filename):
        """Выбирает стратегию из меню"""
        name_without_ext = filename[:-4]
        index = self.combo_box.findText(name_without_ext)
        if index >= 0:
            self.combo_box.setCurrentIndex(index)
            # Сохраняем последнюю выбранную стратегию
            self.config.set_setting('last_strategy', name_without_ext)
            self.settings['last_strategy'] = name_without_ext
    
    def retranslate_ui(self):
        """Обновляет все тексты интерфейса в соответствии с текущим языком"""
        lang = self.settings.get('language', 'ru')
        
        # Обновляем меню
        if hasattr(self, 'tools_menu') and self.tools_menu:
            self.tools_menu.setTitle(tr('menu_tools', lang))
        if hasattr(self, 'run_test_action') and self.run_test_action:
            self.run_test_action.setText(tr('menu_run_test', lang))
        if hasattr(self, 'run_diagnostics_action') and self.run_diagnostics_action:
            self.run_diagnostics_action.setText(tr('menu_run_diagnostics', lang))
        
        if self.settings_menu:
            self.settings_menu.setTitle(tr('menu_settings', lang))
        if hasattr(self, 'open_settings_action') and self.open_settings_action:
            self.open_settings_action.setText('Параметры программы' if lang == 'ru' else 'Program Parameters')
        if hasattr(self, 'game_filter_action') and self.game_filter_action:
            self.game_filter_action.setText(tr('settings_game_filter', lang))
        if hasattr(self, 'ipset_filter_action') and self.ipset_filter_action:
            self.ipset_filter_action.setText(tr('settings_ipset_filter', lang))
        
        if self.update_menu:
            self.update_menu.setTitle(tr('menu_update', lang))
        if self.check_updates_action:
            self.check_updates_action.setText(tr('update_check_zapret', lang))
        if self.manual_update_action:
            self.manual_update_action.setText(tr('update_manual', lang))
        if hasattr(self, 'update_ipset_action') and self.update_ipset_action:
            self.update_ipset_action.setText(tr('update_ipset_list', lang))
        if hasattr(self, 'update_hosts_action') and self.update_hosts_action:
            self.update_hosts_action.setText(tr('update_hosts_file', lang))
        
        # Обновляем меню "Справка"
        if hasattr(self, 'help_menu') and self.help_menu:
            self.help_menu.setTitle(tr('menu_help', lang))
        if hasattr(self, 'open_github_action') and self.open_github_action:
            self.open_github_action.setText(tr('help_open_github', lang))
        if hasattr(self, 'open_help_action') and self.open_help_action:
            self.open_help_action.setText(tr('help_open_help', lang))
        if hasattr(self, 'open_github_zapret_action') and self.open_github_zapret_action:
            self.open_github_zapret_action.setText(tr('help_open_github_zapret', lang))
        
        # Обновляем кнопку
        if self.action_button:
            if self.is_running:
                self.action_button.setText(tr('button_stop', lang))
            else:
                self.action_button.setText(tr('button_start', lang))
        
        # Обновляем трей меню
        if hasattr(self, 'tray') and self.tray:
            self.tray.update_menu()
    
    def set_language(self, lang):
        """Устанавливает язык и обновляет интерфейс"""
        self.settings['language'] = lang
        self.config.set_setting('language', lang)
        self.retranslate_ui()
    
    def toggle_show_in_tray(self):
        """Переключает отображение в трее"""
        value = self.show_tray_action.isChecked()
        # Сохраняем настройку
        self.settings['show_in_tray'] = value
        self.config.set_setting('show_in_tray', value)
        # Применяем настройку
        if value:
            if hasattr(self, 'tray') and self.tray:
                self.tray.show()
        else:
            if hasattr(self, 'tray') and self.tray:
                self.tray.hide()
    
    def toggle_close_winws(self):
        """Переключает настройку закрытия winws при выходе"""
        value = self.close_winws_action.isChecked()
        self.settings['close_winws_on_exit'] = value
        self.config.set_setting('close_winws_on_exit', value)
    
    def toggle_start_minimized(self):
        """Переключает настройку запуска свернутым"""
        value = self.start_minimized_action.isChecked()
        self.settings['start_minimized'] = value
        self.config.set_setting('start_minimized', value)
    
    def toggle_auto_start(self):
        """Переключает автозапуск последней стратегии"""
        value = self.auto_start_action.isChecked()
        self.settings['auto_start_last_strategy'] = value
        self.config.set_setting('auto_start_last_strategy', value)
    
    def toggle_auto_restart(self):
        """Переключает автоперезапуск стратегии"""
        value = self.auto_restart_action.isChecked()
        self.settings['auto_restart_strategy'] = value
        self.config.set_setting('auto_restart_strategy', value)
    
    def toggle_autostart(self):
        """Переключает автозапуск приложения с Windows"""
        if self.autostart_action.isChecked():
            if self.autostart_manager.enable():
                self.settings['autostart_enabled'] = True
                self.config.set_setting('autostart_enabled', True)
            else:
                # Если не удалось включить, снимаем галочку
                self.autostart_action.setChecked(False)
                lang = self.settings.get('language', 'ru')
                msg = QMessageBox(self)
                msg.setWindowTitle('Ошибка')
                msg.setText('Не удалось включить автозапуск')
                msg.setIcon(QMessageBox.Icon.Warning)
                msg.exec()
        else:
            if self.autostart_manager.disable():
                self.settings['autostart_enabled'] = False
                self.config.set_setting('autostart_enabled', False)
    
    def show_settings_dialog(self):
        """Открывает диалоговое окно с настройками"""
        lang = self.settings.get('language', 'ru')
        
        dialog = QDialog(self)
        dialog.setWindowTitle(tr('menu_open_settings', lang))
        dialog.setMinimumSize(600, 500)
        
        # Основной горизонтальный layout
        main_layout = QHBoxLayout()
        
        # QListWidget слева для категорий
        categories_list = QListWidget()
        categories_list.setMaximumWidth(200)
        categories_list.setCurrentRow(0)
        
        # Добавляем категории
        categories = [
            tr('menu_change_language', lang),
            'Трей' if lang == 'ru' else 'Tray',
            'Поведение при выходе' if lang == 'ru' else 'Exit Behavior',
            'Автозапуск' if lang == 'ru' else 'Autostart',
            tr('menu_add_b_flag_submenu', lang),
            'Обновление' if lang == 'ru' else 'Update'
        ]
        for category in categories:
            categories_list.addItem(category)
        
        # QStackedWidget справа для страниц настроек
        stacked_widget = QStackedWidget()
        
        # Страница 1: Язык
        language_page = QWidget()
        language_layout = QVBoxLayout()
        language_layout.setContentsMargins(20, 20, 20, 20)
        
        language_label = QLabel(tr('menu_change_language', lang) + ':')
        language_layout.addWidget(language_label)
        
        self.dialog_language_combo = QComboBox()
        self.dialog_language_combo.addItems(['Russian (Русский)', 'English (Английский)'])
        self.dialog_language_combo.setCurrentIndex(0 if self.settings.get('language', 'ru') == 'ru' else 1)
        self.dialog_language_combo.currentIndexChanged.connect(lambda: self._update_language_help(language_help_label, lang))
        language_layout.addWidget(self.dialog_language_combo)
        
        language_layout.addStretch()
        
        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        language_layout.addWidget(separator)
        
        # Справка
        language_help_label = QLabel()
        language_help_label.setWordWrap(True)
        language_help_label.setStyleSheet("  padding: 10px; border-radius: 5px;")
        self._update_language_help(language_help_label, lang)
        language_layout.addWidget(language_help_label)
        
        language_page.setLayout(language_layout)
        stacked_widget.addWidget(language_page)
        
        # Страница 2: Трей
        tray_page = QWidget()
        tray_layout = QVBoxLayout()
        tray_layout.setContentsMargins(20, 20, 20, 20)
        
        # Отображать в трее
        show_tray_label = QLabel(tr('settings_show_tray', lang) + ':')
        tray_layout.addWidget(show_tray_label)
        self.dialog_show_tray = QComboBox()
        self.dialog_show_tray.addItems(['Да' if lang == 'ru' else 'Yes', 'Нет' if lang == 'ru' else 'No'])
        self.dialog_show_tray.setCurrentIndex(0 if self.settings.get('show_in_tray', True) else 1)
        self.dialog_show_tray.currentIndexChanged.connect(lambda: self._update_tray_help(tray_help_label, lang))
        tray_layout.addWidget(self.dialog_show_tray)
        
        tray_layout.addSpacing(15)
        
        # Запускать свернутым
        start_minimized_label = QLabel(tr('settings_start_minimized', lang) + ':')
        tray_layout.addWidget(start_minimized_label)
        self.dialog_start_minimized = QComboBox()
        self.dialog_start_minimized.addItems(['Да' if lang == 'ru' else 'Yes', 'Нет' if lang == 'ru' else 'No'])
        self.dialog_start_minimized.setCurrentIndex(0 if self.settings.get('start_minimized', False) else 1)
        self.dialog_start_minimized.currentIndexChanged.connect(lambda: self._update_tray_help(tray_help_label, lang))
        tray_layout.addWidget(self.dialog_start_minimized)
        
        # Функция для показа/скрытия пункта "Запускать свернутым"
        def toggle_start_minimized_visibility():
            show_tray = self.dialog_show_tray.currentIndex() == 0
            start_minimized_label.setVisible(show_tray)
            self.dialog_start_minimized.setVisible(show_tray)
        
        # Подключаем обработчик изменения "Отображать в трее"
        self.dialog_show_tray.currentIndexChanged.connect(toggle_start_minimized_visibility)
        
        # Устанавливаем начальную видимость
        toggle_start_minimized_visibility()
        
        tray_layout.addStretch()
        
        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        tray_layout.addWidget(separator)
        
        # Справка
        tray_help_label = QLabel()
        tray_help_label.setWordWrap(True)
        tray_help_label.setStyleSheet(" padding: 10px; border-radius: 5px;")
        self._update_tray_help(tray_help_label, lang)
        tray_layout.addWidget(tray_help_label)
        
        tray_page.setLayout(tray_layout)
        stacked_widget.addWidget(tray_page)
        
        # Страница 3: Поведение при выходе
        exit_page = QWidget()
        exit_layout = QVBoxLayout()
        exit_layout.setContentsMargins(20, 20, 20, 20)
        
        close_winws_label = QLabel(tr('settings_close_winws', lang) + ':')
        exit_layout.addWidget(close_winws_label)
        self.dialog_close_winws = QComboBox()
        self.dialog_close_winws.addItems(['Да' if lang == 'ru' else 'Yes', 'Нет' if lang == 'ru' else 'No'])
        self.dialog_close_winws.setCurrentIndex(0 if self.settings.get('close_winws_on_exit', True) else 1)
        self.dialog_close_winws.currentIndexChanged.connect(lambda: self._update_exit_help(exit_help_label, lang))
        exit_layout.addWidget(self.dialog_close_winws)
        
        exit_layout.addStretch()
        
        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        exit_layout.addWidget(separator)
        
        # Справка
        exit_help_label = QLabel()
        exit_help_label.setWordWrap(True)
        exit_help_label.setStyleSheet(" padding: 10px; border-radius: 5px;")
        self._update_exit_help(exit_help_label, lang)
        exit_layout.addWidget(exit_help_label)
        
        exit_page.setLayout(exit_layout)
        stacked_widget.addWidget(exit_page)
        
        # Страница 4: Автозапуск
        autostart_page = QWidget()
        autostart_layout = QVBoxLayout()
        autostart_layout.setContentsMargins(20, 20, 20, 20)
        
        # Автозапуск с Windows
        autostart_windows_label = QLabel(tr('settings_autostart_windows', lang) + ':')
        autostart_layout.addWidget(autostart_windows_label)
        self.dialog_autostart_windows = QComboBox()
        self.dialog_autostart_windows.addItems(['Да' if lang == 'ru' else 'Yes', 'Нет' if lang == 'ru' else 'No'])
        self.dialog_autostart_windows.setCurrentIndex(0 if self.autostart_manager.is_enabled() else 1)
        self.dialog_autostart_windows.currentIndexChanged.connect(lambda: self._update_autostart_help(autostart_help_label, lang))
        autostart_layout.addWidget(self.dialog_autostart_windows)
        
        autostart_layout.addSpacing(15)
        
        # Автозапуск последней стратегии
        auto_start_label = QLabel(tr('settings_auto_start', lang) + ':')
        autostart_layout.addWidget(auto_start_label)
        self.dialog_auto_start = QComboBox()
        self.dialog_auto_start.addItems(['Да' if lang == 'ru' else 'Yes', 'Нет' if lang == 'ru' else 'No'])
        self.dialog_auto_start.setCurrentIndex(0 if self.settings.get('auto_start_last_strategy', False) else 1)
        self.dialog_auto_start.currentIndexChanged.connect(lambda: self._update_autostart_help(autostart_help_label, lang))
        autostart_layout.addWidget(self.dialog_auto_start)
        
        autostart_layout.addSpacing(15)
        
        # Автоперезапуск стратегии
        auto_restart_label = QLabel(tr('settings_auto_restart_strategy', lang) + ':')
        autostart_layout.addWidget(auto_restart_label)
        self.dialog_auto_restart = QComboBox()
        self.dialog_auto_restart.addItems(['Да' if lang == 'ru' else 'Yes', 'Нет' if lang == 'ru' else 'No'])
        self.dialog_auto_restart.setCurrentIndex(0 if self.settings.get('auto_restart_strategy', False) else 1)
        self.dialog_auto_restart.currentIndexChanged.connect(lambda: self._update_autostart_help(autostart_help_label, lang))
        autostart_layout.addWidget(self.dialog_auto_restart)
        
        autostart_layout.addStretch()
        
        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        autostart_layout.addWidget(separator)
        
        # Справка
        autostart_help_label = QLabel()
        autostart_help_label.setWordWrap(True)
        autostart_help_label.setStyleSheet("  padding: 10px; border-radius: 5px;")
        self._update_autostart_help(autostart_help_label, lang)
        autostart_layout.addWidget(autostart_help_label)
        
        autostart_page.setLayout(autostart_layout)
        stacked_widget.addWidget(autostart_page)
        
        # Страница 5: Добавление команды /B
        b_flag_page = QWidget()
        b_flag_layout = QVBoxLayout()
        b_flag_layout.setContentsMargins(20, 20, 20, 20)
        
        # Добавлять /B при обновлении
        add_b_on_update_label = QLabel(tr('menu_add_b_flag_on_update', lang) + ':')
        b_flag_layout.addWidget(add_b_on_update_label)
        self.dialog_add_b_on_update = QComboBox()
        self.dialog_add_b_on_update.addItems(['Да' if lang == 'ru' else 'Yes', 'Нет' if lang == 'ru' else 'No'])
        self.dialog_add_b_on_update.setCurrentIndex(0 if self.settings.get('add_b_flag_on_update', False) else 1)
        self.dialog_add_b_on_update.currentIndexChanged.connect(lambda: self._update_b_flag_help(b_flag_help_label, lang))
        b_flag_layout.addWidget(self.dialog_add_b_on_update)
        
        b_flag_layout.addSpacing(15)
        
        # Кнопка "Добавить /B во все стратегии"
        add_b_button = QPushButton(tr('menu_add_b_flag', lang))
        add_b_button.clicked.connect(lambda: self.add_b_flag_to_all_strategies(silent=False))
        b_flag_layout.addWidget(add_b_button)
        
        b_flag_layout.addSpacing(10)
        
        # Кнопка "Удалить /B из всех стратегий"
        remove_b_button = QPushButton(tr('menu_remove_b_flag', lang))
        remove_b_button.clicked.connect(lambda: self.remove_b_flag_from_all_strategies(silent=False))
        b_flag_layout.addWidget(remove_b_button)
        
        b_flag_layout.addStretch()
        
        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        b_flag_layout.addWidget(separator)
        
        # Справка
        b_flag_help_label = QLabel()
        b_flag_help_label.setWordWrap(True)
        b_flag_help_label.setStyleSheet("  padding: 10px; border-radius: 5px;")
        self._update_b_flag_help(b_flag_help_label, lang)
        b_flag_layout.addWidget(b_flag_help_label)
        
        b_flag_page.setLayout(b_flag_layout)
        stacked_widget.addWidget(b_flag_page)
        
        # Страница 6: Обновление
        update_check_page = QWidget()
        update_check_layout = QVBoxLayout()
        update_check_layout.setContentsMargins(20, 20, 20, 20)
        
        # Проверка обновлений zapret
        remove_check_label = QLabel(('Проверка обновлений zapret' if lang == 'ru' else 'Check zapret updates') + ':')
        update_check_layout.addWidget(remove_check_label)
        self.dialog_remove_check_updates = QComboBox()
        self.dialog_remove_check_updates.addItems(['Да' if lang == 'ru' else 'Yes', 'Нет' if lang == 'ru' else 'No'])
        # Инвертируем логику: Да = оставлять проверку (не удалять), Нет = удалять проверку
        # remove_check_updates: True = удалять, False = не удалять
        # currentIndex 0 = Да = не удалять (False), currentIndex 1 = Нет = удалять (True)
        self.dialog_remove_check_updates.setCurrentIndex(1 if self.settings.get('remove_check_updates', False) else 0)
        self.dialog_remove_check_updates.currentIndexChanged.connect(lambda: self._update_update_check_help(update_check_help_label, lang))
        update_check_layout.addWidget(self.dialog_remove_check_updates)
        
        update_check_layout.addStretch()
        
        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        update_check_layout.addWidget(separator)
        
        # Справка
        update_check_help_label = QLabel()
        update_check_help_label.setWordWrap(True)
        update_check_help_label.setStyleSheet("  padding: 10px; border-radius: 5px;")
        self._update_update_check_help(update_check_help_label, lang)
        update_check_layout.addWidget(update_check_help_label)
        
        update_check_page.setLayout(update_check_layout)
        stacked_widget.addWidget(update_check_page)
        
        # Подключаем выбор категории к переключению страницы
        categories_list.currentRowChanged.connect(stacked_widget.setCurrentIndex)
        
        # Добавляем виджеты в основной layout
        main_layout.addWidget(categories_list)
        main_layout.addWidget(stacked_widget, 1)  # Растягиваем stacked_widget
        
        # Вертикальный layout для всего диалога
        dialog_layout = QVBoxLayout()
        dialog_layout.addLayout(main_layout)
        
        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        ok_button = QPushButton('OK' if lang == 'ru' else 'OK')
        ok_button.clicked.connect(dialog.accept)
        cancel_button = QPushButton('Отмена' if lang == 'ru' else 'Cancel')
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        dialog_layout.addLayout(button_layout)
        
        dialog.setLayout(dialog_layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Применяем изменения
            # Язык
            selected_lang = 'ru' if self.dialog_language_combo.currentIndex() == 0 else 'en'
            if selected_lang != self.settings.get('language', 'ru'):
                self.set_language(selected_lang)
            
            # Отображать в трее
            show_tray_value = self.dialog_show_tray.currentIndex() == 0
            if show_tray_value != self.settings.get('show_in_tray', True):
                self.settings['show_in_tray'] = show_tray_value
                self.config.set_setting('show_in_tray', show_tray_value)
                if show_tray_value:
                    if hasattr(self, 'tray') and self.tray:
                        self.tray.show()
                else:
                    if hasattr(self, 'tray') and self.tray:
                        self.tray.hide()
            
            # Запускать свернутым
            start_minimized_value = self.dialog_start_minimized.currentIndex() == 0
            if start_minimized_value != self.settings.get('start_minimized', False):
                self.settings['start_minimized'] = start_minimized_value
                self.config.set_setting('start_minimized', start_minimized_value)
            
            # Закрывать winws при выходе
            close_winws_value = self.dialog_close_winws.currentIndex() == 0
            if close_winws_value != self.settings.get('close_winws_on_exit', True):
                self.settings['close_winws_on_exit'] = close_winws_value
                self.config.set_setting('close_winws_on_exit', close_winws_value)
            
            # Автозапуск с Windows
            autostart_value = self.dialog_autostart_windows.currentIndex() == 0
            if autostart_value != self.autostart_manager.is_enabled():
                if autostart_value:
                    if not self.autostart_manager.enable():
                        self.dialog_autostart_windows.setCurrentIndex(1)
                        lang = self.settings.get('language', 'ru')
                        msg = QMessageBox(self)
                        msg.setWindowTitle('Ошибка' if lang == 'ru' else 'Error')
                        msg.setText('Не удалось включить автозапуск' if lang == 'ru' else 'Failed to enable autostart')
                        msg.setIcon(QMessageBox.Icon.Warning)
                        msg.exec()
                    else:
                        self.settings['autostart_enabled'] = True
                        self.config.set_setting('autostart_enabled', True)
                else:
                    if not self.autostart_manager.disable():
                        self.dialog_autostart_windows.setCurrentIndex(0)
                        lang = self.settings.get('language', 'ru')
                        msg = QMessageBox(self)
                        msg.setWindowTitle('Ошибка' if lang == 'ru' else 'Error')
                        msg.setText('Не удалось выключить автозапуск' if lang == 'ru' else 'Failed to disable autostart')
                        msg.setIcon(QMessageBox.Icon.Warning)
                        msg.exec()
                    else:
                        self.settings['autostart_enabled'] = False
                        self.config.set_setting('autostart_enabled', False)
            
            # Автозапуск последней стратегии
            auto_start_value = self.dialog_auto_start.currentIndex() == 0
            if auto_start_value != self.settings.get('auto_start_last_strategy', False):
                self.settings['auto_start_last_strategy'] = auto_start_value
                self.config.set_setting('auto_start_last_strategy', auto_start_value)
            
            # Автоперезапуск стратегии
            auto_restart_value = self.dialog_auto_restart.currentIndex() == 0
            if auto_restart_value != self.settings.get('auto_restart_strategy', False):
                self.settings['auto_restart_strategy'] = auto_restart_value
                self.config.set_setting('auto_restart_strategy', auto_restart_value)
            
            # Добавлять /B при обновлении
            add_b_on_update_value = self.dialog_add_b_on_update.currentIndex() == 0
            if add_b_on_update_value != self.settings.get('add_b_flag_on_update', False):
                self.settings['add_b_flag_on_update'] = add_b_on_update_value
                self.config.set_setting('add_b_flag_on_update', add_b_on_update_value)
            
            # Проверка обновлений zapret (инвертированная логика: Да = оставлять, Нет = удалять)
            # currentIndex 0 = Да = не удалять (False), currentIndex 1 = Нет = удалять (True)
            remove_check_updates_value = self.dialog_remove_check_updates.currentIndex() == 1
            if remove_check_updates_value != self.settings.get('remove_check_updates', False):
                self.settings['remove_check_updates'] = remove_check_updates_value
                self.config.set_setting('remove_check_updates', remove_check_updates_value)
    
    def _update_language_help(self, label, lang):
        """Обновляет текст справки для настройки языка"""
        help_text = {
            'ru': 'Выберите язык интерфейса приложения. Изменения вступят в силу после перезапуска приложения.',
            'en': 'Select the application interface language. Changes will take effect after restarting the application.'
        }
        label.setText(help_text.get(lang, help_text['ru']))
    
    def _update_tray_help(self, label, lang):
        """Обновляет текст справки для настроек трея"""
        show_tray = self.dialog_show_tray.currentIndex() == 0
        start_minimized = self.dialog_start_minimized.currentIndex() == 0
        
        if lang == 'ru':
            text = 'Отображать в трее: ' + ('Да' if show_tray else 'Нет') + '\n'
            text += 'Позволяет отображать иконку приложения в системном трее Windows.\n\n'
            text += 'Запускать свернутым: ' + ('Да' if start_minimized else 'Нет') + '\n'
            text += 'При включении приложение будет запускаться в свернутом виде в системном трее.'
        else:
            text = 'Show in tray: ' + ('Yes' if show_tray else 'No') + '\n'
            text += 'Allows displaying the application icon in the Windows system tray.\n\n'
            text += 'Start minimized: ' + ('Yes' if start_minimized else 'No') + '\n'
            text += 'When enabled, the application will start minimized to the system tray.'
        
        label.setText(text)
    
    def _update_exit_help(self, label, lang):
        """Обновляет текст справки для настройки поведения при выходе"""
        close_winws = self.dialog_close_winws.currentIndex() == 0
        
        if lang == 'ru':
            text = 'Закрывать winws при выходе: ' + ('Да' if close_winws else 'Нет') + '\n'
            text += 'При включении все процессы winws.exe будут автоматически завершены при закрытии приложения.'
        else:
            text = 'Close winws on exit: ' + ('Yes' if close_winws else 'No') + '\n'
            text += 'When enabled, all winws.exe processes will be automatically terminated when the application is closed.'
        
        label.setText(text)
    
    def _update_autostart_help(self, label, lang):
        """Обновляет текст справки для настроек автозапуска"""
        autostart_windows = self.dialog_autostart_windows.currentIndex() == 0
        auto_start = self.dialog_auto_start.currentIndex() == 0
        auto_restart = self.dialog_auto_restart.currentIndex() == 0
        
        if lang == 'ru':
            text = 'Автозапуск с Windows: ' + ('Да' if autostart_windows else 'Нет') + '\n'
            text += 'Приложение будет автоматически запускаться при входе в Windows.\n\n'
            text += 'Автозапуск последней стратегии: ' + ('Да' if auto_start else 'Нет') + '\n'
            text += 'При запуске приложения автоматически запустится последняя использованная стратегия.\n\n'
            text += 'Автоперезапуск стратегии: ' + ('Да' if auto_restart else 'Нет') + '\n'
            text += 'Если процесс winws.exe завершится, стратегия будет автоматически перезапущена.'
        else:
            text = 'Start with Windows: ' + ('Yes' if autostart_windows else 'No') + '\n'
            text += 'The application will automatically start when Windows starts.\n\n'
            text += 'Auto-start last strategy: ' + ('Yes' if auto_start else 'No') + '\n'
            text += 'When the application starts, the last used strategy will automatically launch.\n\n'
            text += 'Auto-restart strategy: ' + ('Yes' if auto_restart else 'No') + '\n'
            text += 'If the winws.exe process terminates, the strategy will be automatically restarted.'
        
        label.setText(text)
    
    def _update_b_flag_help(self, label, lang):
        """Обновляет текст справки для настроек добавления команды /B"""
        add_b_on_update = self.dialog_add_b_on_update.currentIndex() == 0
        
        if lang == 'ru':
            text = 'Добавлять /B при обновлении: ' + ('Да' if add_b_on_update else 'Нет') + '\n'
            text += 'При включении флаг /B будет автоматически добавляться ко всем стратегиям при их обновлении.\n\n'
            text += 'Кнопка "Добавить /B во все стратегии" позволяет вручную добавить флаг /B ко всем существующим стратегиям.\n\n'
            text += 'Кнопка "Удалить /B из всех стратегий" позволяет вручную удалить флаг /B из всех существующих стратегий.'
        else:
            text = 'Add /B on update: ' + ('Yes' if add_b_on_update else 'No') + '\n'
            text += 'When enabled, the /B flag will be automatically added to all strategies when they are updated.\n\n'
            text += 'The "Add /B to all strategies" button allows you to manually add the /B flag to all existing strategies.\n\n'
            text += 'The "Remove /B from all strategies" button allows you to manually remove the /B flag from all existing strategies.'
        
        label.setText(text)
    
    def _update_update_check_help(self, label, lang):
        """Обновляет текст справки для настройки проверки обновлений"""
        # Инвертированная логика: currentIndex 0 = Да = оставлять проверку, currentIndex 1 = Нет = удалять проверку
        keep_check = self.dialog_remove_check_updates.currentIndex() == 0
        
        if lang == 'ru':
            text = 'Проверка обновлений zapret: ' + ('Да' if keep_check else 'Нет') + '\n'
            if keep_check:
                text += 'Проверка обновлений zapret будет оставлена в стратегиях winws при их обновлении.'
            else:
                text += 'Проверка обновлений zapret будет удаляться из стратегий winws при их обновлении.'
        else:
            text = 'Check zapret updates: ' + ('Yes' if keep_check else 'No') + '\n'
            if keep_check:
                text += 'Zapret update checks will be kept in winws strategies when they are updated.'
            else:
                text += 'Zapret update checks will be removed from winws strategies when they are updated.'
        
        label.setText(text)
    
    def minimize_to_tray(self):
        """Сворачивает окно в трей"""
        self.hide()
    
    def quit_application(self):
        """Полностью закрывает приложение"""
        # Если нужно закрыть winws при выходе
        if self.settings.get('close_winws_on_exit', True):
            self.stop_winws_process(silent=True)
        
        QApplication.quit()
    
    def check_zapret_updates(self):
        """Проверяет наличие обновлений стратегий zapret"""
        lang = self.settings.get('language', 'ru')
        
        # Показываем диалог проверки
        progress_dialog = QProgressDialog(self)
        progress_dialog.setWindowTitle(tr('msg_check_updates_title', lang))
        progress_dialog.setLabelText(tr('update_checking', lang))
        progress_dialog.setRange(0, 0)  # Неопределенный прогресс
        progress_dialog.setCancelButton(None)
        progress_dialog.show()
        QApplication.processEvents()
        
        # Проверяем обновления
        update_info = self.zapret_updater.check_for_updates()
        progress_dialog.close()
        
        if 'error' in update_info:
            msg = QMessageBox(self)
            msg.setWindowTitle(tr('update_error_title', lang))
            msg.setText(update_info['error'])
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.exec()
            return
        
        if not update_info['has_update']:
            msg = QMessageBox(self)
            msg.setWindowTitle(tr('msg_check_updates_title', lang))
            msg.setText(tr('update_not_found', lang))
            msg.setInformativeText(tr('update_current_version', lang).format(update_info["current_version"]))
            msg.setIcon(QMessageBox.Icon.Information)
            msg.exec()
            return
        
        # Есть обновление - спрашиваем пользователя
        reply = QMessageBox.question(
            self,
            tr('update_available_title', lang),
            tr('update_available_text', lang).format(update_info["latest_version"], update_info["current_version"]),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.download_and_install_update(update_info)
    
    def download_and_install_update(self, update_info):
        """Скачивает и устанавливает обновление"""
        lang = self.settings.get('language', 'ru')
        
        if not update_info.get('download_url'):
            msg = QMessageBox(self)
            msg.setWindowTitle(tr('update_error_title', lang))
            msg.setText(tr('update_error_url_not_found', lang))
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.exec()
            return
        
        # Сначала останавливаем winws.exe, если он запущен
        winws_running = False
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] and proc.info['name'].lower() == 'winws.exe':
                        winws_running = True
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except Exception:
            pass
        
        if winws_running:
            # Показываем диалог остановки
            stop_dialog = QMessageBox(self)
            stop_dialog.setWindowTitle(tr('update_stopping_winws', lang))
            stop_dialog.setText(tr('update_winws_running', lang))
            stop_dialog.setInformativeText(tr('update_winws_stop_required', lang))
            stop_dialog.setIcon(QMessageBox.Icon.Question)
            stop_dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            stop_dialog.setDefaultButton(QMessageBox.StandardButton.Yes)
            
            reply = stop_dialog.exec()
            if reply == QMessageBox.StandardButton.Yes:
                # Останавливаем процесс
                self.stop_winws_process(silent=True)
                # Ждем немного, чтобы процесс точно завершился
                QApplication.processEvents()
                import time
                time.sleep(3)  # Увеличена задержка для полного освобождения файлов
                
                # Дополнительная проверка - ждем пока процесс точно завершится
                for i in range(10):
                    winws_still_running = False
                    try:
                        for proc in psutil.process_iter(['pid', 'name']):
                            try:
                                if proc.info['name'] and proc.info['name'].lower() == 'winws.exe':
                                    winws_still_running = True
                                    break
                            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                                pass
                    except Exception:
                        pass
                    
                    if not winws_still_running:
                        break
                    time.sleep(0.5)
                    QApplication.processEvents()
            else:
                # Пользователь отменил остановку
                return
        
        # Создаем диалог прогресса
        progress_dialog = QProgressDialog(self)
        progress_dialog.setWindowTitle(tr('update_title', lang))
        progress_dialog.setLabelText(tr('update_downloading', lang))
        progress_dialog.setRange(0, 100)
        progress_dialog.setCancelButton(None)
        progress_dialog.show()
        QApplication.processEvents()
        
        def update_progress(value):
            progress_dialog.setValue(int(value))
            QApplication.processEvents()
        
        try:
            # Скачиваем обновление
            progress_dialog.setLabelText(tr('update_downloading', lang))
            zip_path = self.zapret_updater.download_update(
                update_info['download_url'],
                progress_callback=update_progress
            )
            
            # Устанавливаем обновление
            progress_dialog.setLabelText(tr('update_installing', lang))
            progress_dialog.setValue(50)
            QApplication.processEvents()
            
            self.zapret_updater.extract_and_update(zip_path, update_info['latest_version'])
            
            progress_dialog.close()
            
            # Обновляем список стратегий в ComboBox
            current_strategy = self.combo_box.currentText()
            self.combo_box.clear()
            self.load_bat_files()
            # Восстанавливаем выбранную стратегию, если она еще существует
            index = self.combo_box.findText(current_strategy)
            if index >= 0:
                self.combo_box.setCurrentIndex(index)
            
            # Если включена настройка "Добавлять /B при обновлении", добавляем /B флаг
            if self.settings.get('add_b_flag_on_update', False):
                self.add_b_flag_to_all_strategies(silent=True)
            
            # Если включена настройка "Удалять проверку обновлений", удаляем строку check_updates
            if self.settings.get('remove_check_updates', False):
                self.remove_check_updates_from_all_strategies(silent=True)
            
            msg = QMessageBox(self)
            msg.setWindowTitle(tr('update_completed', lang))
            msg.setText(tr('update_completed_text', lang).format(update_info["latest_version"]))
            msg.setIcon(QMessageBox.Icon.Information)
            msg.exec()
            
        except Exception as e:
            progress_dialog.close()
            msg = QMessageBox(self)
            msg.setWindowTitle(tr('update_error_title', lang))
            msg.setText(tr('update_error_text', lang).format(str(e)))
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.exec()
    
    def manual_update_strategies(self):
        """Обновляет стратегии вручную из выбранного архива"""
        lang = self.settings.get('language', 'ru')
        winws_folder = get_winws_path()
        
        # Проверяем, запущен ли winws.exe
        winws_running = False
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] and proc.info['name'].lower() == 'winws.exe':
                        winws_running = True
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except Exception:
            pass
        
        if winws_running:
            reply = QMessageBox.question(
                self,
                tr('update_stopping_winws', lang),
                tr('update_winws_running', lang) + '\n' + tr('update_winws_stop_required', lang),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.stop_winws_process(silent=True)
                import time
                time.sleep(2)
            else:
                return
        
        # Открываем диалог выбора файла
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle(tr('update_manual_select_archive', lang))
        file_dialog.setNameFilter('ZIP файлы (*.zip);;Все файлы (*.*)')
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        
        if not file_dialog.exec():
            return
        
        selected_files = file_dialog.selectedFiles()
        if not selected_files:
            return
        
        archive_path = selected_files[0]
        
        # Показываем прогресс
        progress_dialog = QProgressDialog(self)
        progress_dialog.setWindowTitle(tr('update_manual_title', lang))
        progress_dialog.setLabelText(tr('update_manual_extracting', lang))
        progress_dialog.setRange(0, 0)
        progress_dialog.setCancelButton(None)
        progress_dialog.show()
        QApplication.processEvents()
        
        try:
            # Распаковываем архив
            self.extract_archive_to_winws(archive_path, winws_folder)
            
            progress_dialog.close()
            
            # Обновляем список стратегий в ComboBox
            current_strategy = self.combo_box.currentText()
            self.combo_box.clear()
            self.load_bat_files()
            # Восстанавливаем выбранную стратегию, если она еще существует
            index = self.combo_box.findText(current_strategy)
            if index >= 0:
                self.combo_box.setCurrentIndex(index)
            
            # Если включена настройка "Добавлять /B при обновлении", добавляем /B флаг
            if self.settings.get('add_b_flag_on_update', False):
                self.add_b_flag_to_all_strategies(silent=True)
            
            # Если включена настройка "Удалять проверку обновлений", удаляем строку check_updates
            if self.settings.get('remove_check_updates', False):
                self.remove_check_updates_from_all_strategies(silent=True)
            
            msg = QMessageBox(self)
            msg.setWindowTitle(tr('update_completed', lang))
            msg.setText(tr('update_manual_completed', lang))
            msg.setIcon(QMessageBox.Icon.Information)
            msg.exec()
            
        except Exception as e:
            progress_dialog.close()
            msg = QMessageBox(self)
            msg.setWindowTitle(tr('update_error_title', lang))
            msg.setText(tr('update_error_text', lang).format(str(e)))
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.exec()
    
    def extract_archive_to_winws(self, archive_path, winws_folder):
        """Распаковывает архив (ZIP или RAR) в папку winws"""
        import time
        import zipfile
        import shutil
        
        # Нормализуем пути до абсолютных
        winws_folder = os.path.abspath(winws_folder)
        archive_path = os.path.abspath(archive_path)
        
        # Создаем резервную копию
        backup_folder = f"{winws_folder}_backup"
        if os.path.exists(winws_folder):
            if os.path.exists(backup_folder):
                shutil.rmtree(backup_folder)
            shutil.copytree(winws_folder, backup_folder)
        
        # Ждем немного для освобождения файлов
        time.sleep(1)
        
        # Определяем тип архива
        archive_ext = os.path.splitext(archive_path)[1].lower()
        
        # Создаем временную папку для распаковки
        winws_parent = os.path.dirname(winws_folder) or os.getcwd()
        temp_extract = os.path.join(winws_parent, 'temp_manual_extract')
        if os.path.exists(temp_extract):
            shutil.rmtree(temp_extract)
        os.makedirs(temp_extract, exist_ok=True)
        
        try:
            if archive_ext == '.zip':
                # Распаковываем ZIP
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_extract)
            else:
                raise Exception(f'Неподдерживаемый формат архива: {archive_ext}. Поддерживается только ZIP формат.')
            
            # Ищем папку winws или .bat файлы в распакованном архиве
            winws_source = None
            
            # Сначала ищем папку winws
            for root, dirs, files in os.walk(temp_extract):
                if 'winws' in dirs:
                    winws_source = os.path.join(root, 'winws')
                    break
            
            # Если папки winws нет, ищем .bat файлы
            if not winws_source:
                bat_files_found = []
                for root, dirs, files in os.walk(temp_extract):
                    for file in files:
                        if file.endswith('.bat'):
                            bat_files_found.append((root, file))
                
                if bat_files_found:
                    # Определяем общую папку для всех .bat файлов
                    first_bat_dir = bat_files_found[0][0]
                    all_same_dir = all(dir_path == first_bat_dir for dir_path, _ in bat_files_found)
                    if all_same_dir:
                        winws_source = first_bat_dir
                    else:
                        winws_source = temp_extract
            
            if not winws_source:
                raise Exception('Не найдены .bat файлы или папка winws в архиве')
            
            # Обновляем файлы по одному
            if os.path.isdir(winws_source):
                # Нормализуем путь источника до абсолютного
                winws_source = os.path.abspath(winws_source)
                
                # Создаем папку winws если её нет
                if not os.path.exists(winws_folder):
                    os.makedirs(winws_folder, exist_ok=True)
                
                # Рекурсивно копируем все файлы и папки из winws_source в winws_folder
                def copy_tree(src, dst):
                    """Рекурсивно копирует дерево файлов и папок"""
                    src = os.path.abspath(src)
                    dst = os.path.abspath(dst)
                    
                    if os.path.isdir(src):
                        # Если папка назначения существует, удаляем её содержимое
                        if os.path.exists(dst):
                            # Удаляем существующую папку и её содержимое
                            for attempt in range(5):
                                try:
                                    shutil.rmtree(dst)
                                    break
                                except (PermissionError, OSError):
                                    if attempt < 4:
                                        time.sleep(0.5)
                                    else:
                                        raise
                        # Создаем папку назначения
                        os.makedirs(dst, exist_ok=True)
                        # Копируем содержимое папки
                        for item in os.listdir(src):
                            src_item = os.path.join(src, item)
                            dst_item = os.path.join(dst, item)
                            copy_tree(src_item, dst_item)
                    else:
                        # Копируем файл
                        # Сначала создаем родительские папки если нужно
                        parent_dir = os.path.dirname(dst)
                        if parent_dir:
                            os.makedirs(parent_dir, exist_ok=True)
                        # Удаляем существующий файл если есть
                        if os.path.exists(dst):
                            for attempt in range(5):
                                try:
                                    os.remove(dst)
                                    break
                                except (PermissionError, OSError):
                                    if attempt < 4:
                                        time.sleep(0.5)
                                    else:
                                        raise
                        shutil.copy2(src, dst)
                
                # Копируем все содержимое
                for item in os.listdir(winws_source):
                    src_item = os.path.join(winws_source, item)
                    dst_item = os.path.join(winws_folder, item)
                    copy_tree(src_item, dst_item)
            
            # Очищаем временные файлы
            try:
                shutil.rmtree(temp_extract)
            except Exception:
                pass
                
        except Exception as e:
            # Восстанавливаем из резервной копии при ошибке
            if os.path.exists(backup_folder):
                if os.path.exists(winws_folder):
                    try:
                        shutil.rmtree(winws_folder)
                    except Exception:
                        pass
                # Используем рекурсивное копирование вместо copytree
                os.makedirs(winws_folder, exist_ok=True)
                for item in os.listdir(backup_folder):
                    src_item = os.path.join(backup_folder, item)
                    dst_item = os.path.join(winws_folder, item)
                    if os.path.isdir(src_item):
                        shutil.copytree(src_item, dst_item)
                    else:
                        shutil.copy2(src_item, dst_item)
            raise
    
    def toggle_add_b_flag_on_update(self):
        """Переключает настройку добавления /B флага при обновлении"""
        value = self.add_b_flag_on_update_action.isChecked()
        self.settings['add_b_flag_on_update'] = value
        self.config.set_setting('add_b_flag_on_update', value)
    
    def show_test_window(self):
        """Открывает окно тестирования стратегий"""
        # Передаем None, чтобы TestWindow сам определил правильный путь
        test_window = TestWindow(self, winws_folder=None)
        test_window.exec()
    
    def run_diagnostics(self):
        """Запускает диагностику системы, выполняя все проверки из service.bat"""
        lang = self.settings.get('language', 'ru')
        
        # Создаем диалоговое окно для отображения результатов
        dialog = QDialog(self)
        dialog.setWindowTitle(tr('menu_run_diagnostics', lang))
        dialog.setMinimumSize(700, 500)
        
        layout = QVBoxLayout()
        
        # Текстовое поле для результатов
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("Consolas", 9))
        layout.addWidget(text_edit)
        
        # Кнопка закрытия
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_button = QPushButton('Закрыть' if lang == 'ru' else 'Close')
        close_button.clicked.connect(dialog.accept)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        
        # Добавляем начальное сообщение
        text_edit.append("=== ZAPRET DIAGNOSTICS ===\n")
        text_edit.append("Running diagnostics...\n\n")
        QApplication.processEvents()
        
        results = []
        
        # 1. Base Filtering Engine
        try:
            result = subprocess.run(['sc', 'query', 'BFE'], capture_output=True, text=True, timeout=5)
            if 'RUNNING' in result.stdout:
                results.append(("✓", "Base Filtering Engine check passed"))
            else:
                results.append(("✗", "[X] Base Filtering Engine is not running. This service is required for zapret to work"))
        except Exception as e:
            results.append(("?", f"Error checking BFE: {str(e)}"))
        
        # 2. Proxy check
        try:
            import winreg
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings")
                proxy_enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
                if proxy_enable:
                    proxy_server, _ = winreg.QueryValueEx(key, "ProxyServer")
                    results.append(("?", f"[?] System proxy is enabled: {proxy_server}"))
                    results.append(("?", "Make sure it's valid or disable it if you don't use a proxy"))
                else:
                    results.append(("✓", "Proxy check passed"))
                winreg.CloseKey(key)
            except FileNotFoundError:
                results.append(("✓", "Proxy check passed"))
        except Exception as e:
            results.append(("?", f"Error checking proxy: {str(e)}"))
        
        # 3. TCP timestamps check
        try:
            result = subprocess.run(['netsh', 'interface', 'tcp', 'show', 'global'], 
                                  capture_output=True, text=True, timeout=5)
            if 'timestamps' in result.stdout.lower() and 'enabled' in result.stdout.lower():
                results.append(("✓", "TCP timestamps check passed"))
            else:
                results.append(("?", "[?] TCP timestamps are disabled. Enabling timestamps..."))
                enable_result = subprocess.run(['netsh', 'interface', 'tcp', 'set', 'global', 'timestamps=enabled'],
                                              capture_output=True, text=True, timeout=5)
                if enable_result.returncode == 0:
                    results.append(("✓", "TCP timestamps successfully enabled"))
                else:
                    results.append(("✗", "[X] Failed to enable TCP timestamps"))
        except Exception as e:
            results.append(("?", f"Error checking TCP timestamps: {str(e)}"))
        
        # 4. AdguardSvc.exe
        try:
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] and proc.info['name'].lower() == 'adguardsvc.exe':
                    results.append(("✗", "[X] Adguard process found. Adguard may cause problems with Discord"))
                    results.append(("✗", "https://github.com/Flowseal/zapret-discord-youtube/issues/417"))
                    break
            else:
                results.append(("✓", "Adguard check passed"))
        except Exception:
            results.append(("✓", "Adguard check passed"))
        
        # 5. Killer services
        try:
            result = subprocess.run(['sc', 'query'], capture_output=True, text=True, timeout=5)
            if 'Killer' in result.stdout:
                results.append(("✗", "[X] Killer services found. Killer conflicts with zapret"))
                results.append(("✗", "https://github.com/Flowseal/zapret-discord-youtube/issues/2512#issuecomment-2821119513"))
            else:
                results.append(("✓", "Killer check passed"))
        except Exception as e:
            results.append(("?", f"Error checking Killer services: {str(e)}"))
        
        # 6. Intel Connectivity Network Service
        try:
            result = subprocess.run(['sc', 'query'], capture_output=True, text=True, timeout=5)
            if 'Intel' in result.stdout and 'Connectivity' in result.stdout and 'Network' in result.stdout:
                results.append(("✗", "[X] Intel Connectivity Network Service found. It conflicts with zapret"))
                results.append(("✗", "https://github.com/ValdikSS/GoodbyeDPI/issues/541#issuecomment-2661670982"))
            else:
                results.append(("✓", "Intel Connectivity check passed"))
        except Exception as e:
            results.append(("?", f"Error checking Intel Connectivity: {str(e)}"))
        
        # 7. Check Point
        try:
            result = subprocess.run(['sc', 'query'], capture_output=True, text=True, timeout=5)
            checkpoint_found = 'TracSrvWrapper' in result.stdout or 'EPWD' in result.stdout
            if checkpoint_found:
                results.append(("✗", "[X] Check Point services found. Check Point conflicts with zapret"))
                results.append(("✗", "Try to uninstall Check Point"))
            else:
                results.append(("✓", "Check Point check passed"))
        except Exception as e:
            results.append(("?", f"Error checking Check Point: {str(e)}"))
        
        # 8. SmartByte
        try:
            result = subprocess.run(['sc', 'query'], capture_output=True, text=True, timeout=5)
            if 'SmartByte' in result.stdout:
                results.append(("✗", "[X] SmartByte services found. SmartByte conflicts with zapret"))
                results.append(("✗", "Try to uninstall or disable SmartByte through services.msc"))
            else:
                results.append(("✓", "SmartByte check passed"))
        except Exception as e:
            results.append(("?", f"Error checking SmartByte: {str(e)}"))
        
        # 9. WinDivert64.sys file
        try:
            winws_folder = get_winws_path()
            bin_path = os.path.join(winws_folder, 'bin')
            sys_files = [f for f in os.listdir(bin_path) if f.endswith('.sys')] if os.path.exists(bin_path) else []
            if not sys_files:
                results.append(("✗", "WinDivert64.sys file NOT found."))
            else:
                results.append(("✓", f"WinDivert64.sys file found: {', '.join(sys_files)}"))
        except Exception as e:
            results.append(("?", f"Error checking WinDivert64.sys: {str(e)}"))
        
        # 10. VPN services
        try:
            result = subprocess.run(['sc', 'query'], capture_output=True, text=True, timeout=5)
            if 'VPN' in result.stdout:
                vpn_services = []
                for line in result.stdout.split('\n'):
                    if 'VPN' in line:
                        parts = line.split(':')
                        if len(parts) > 1:
                            vpn_services.append(parts[1].strip())
                if vpn_services:
                    results.append(("?", f"[?] VPN services found: {', '.join(vpn_services)}. Some VPNs can conflict with zapret"))
                    results.append(("?", "Make sure that all VPNs are disabled"))
                else:
                    results.append(("✓", "VPN check passed"))
            else:
                results.append(("✓", "VPN check passed"))
        except Exception as e:
            results.append(("?", f"Error checking VPN services: {str(e)}"))
        
        # 11. DNS (DoH check)
        try:
            ps_cmd = "Get-ChildItem -Recurse -Path 'HKLM:System\\CurrentControlSet\\Services\\Dnscache\\InterfaceSpecificParameters\\' -ErrorAction SilentlyContinue | Get-ItemProperty -ErrorAction SilentlyContinue | Where-Object { $_.DohFlags -gt 0 } | Measure-Object | Select-Object -ExpandProperty Count"
            result = subprocess.run(['powershell', '-Command', ps_cmd], capture_output=True, text=True, timeout=10)
            doh_found = result.stdout.strip().isdigit() and int(result.stdout.strip()) > 0
            if not doh_found:
                results.append(("?", "[?] Make sure you have configured secure DNS in a browser with some non-default DNS service provider,"))
                results.append(("?", "If you use Windows 11 you can configure encrypted DNS in the Settings to hide this warning"))
            else:
                results.append(("✓", "Secure DNS check passed"))
        except Exception:
            results.append(("?", "[?] Could not check secure DNS configuration"))
        
        # 12. WinDivert conflict
        try:
            winws_running = False
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] and proc.info['name'].lower() == 'winws.exe':
                    winws_running = True
                    break
            
            windivert_running = False
            try:
                result = subprocess.run(['sc', 'query', 'WinDivert'], capture_output=True, text=True, timeout=5)
                windivert_running = 'RUNNING' in result.stdout or 'STOP_PENDING' in result.stdout
            except:
                pass
            
            if not winws_running and windivert_running:
                results.append(("?", "[?] winws.exe is not running but WinDivert service is active. Attempting to delete WinDivert..."))
                try:
                    subprocess.run(['net', 'stop', 'WinDivert'], capture_output=True, timeout=5)
                    subprocess.run(['sc', 'delete', 'WinDivert'], capture_output=True, timeout=5)
                    result = subprocess.run(['sc', 'query', 'WinDivert'], capture_output=True, text=True, timeout=5)
                    if result.returncode != 0:
                        results.append(("✓", "WinDivert successfully removed"))
                    else:
                        results.append(("✗", "[X] Failed to delete WinDivert. Check manually if any other bypass is using WinDivert."))
                except Exception as e:
                    results.append(("✗", f"[X] Error removing WinDivert: {str(e)}"))
            else:
                results.append(("✓", "WinDivert conflict check passed"))
        except Exception as e:
            results.append(("?", f"Error checking WinDivert conflict: {str(e)}"))
        
        # Отображаем результаты
        for status, message in results:
            if status == "✓":
                text_edit.setTextColor(QColor(0, 128, 0))  # Зеленый
            elif status == "✗":
                text_edit.setTextColor(QColor(255, 0, 0))  # Красный
            else:
                text_edit.setTextColor(QColor(255, 165, 0))  # Оранжевый
            text_edit.append(f"{status} {message}")
            QApplication.processEvents()
        
        text_edit.setTextColor(QColor(0, 0, 0))  # Черный для остального текста
        text_edit.append("\n=== Diagnostics completed ===")
        
        dialog.exec()
    
    def add_b_flag_to_all_strategies(self, silent=False):
        """Добавляет /B флаг во все .bat файлы стратегий
        
        Args:
            silent: Если True, не показывает диалоги подтверждения и результатов
        """
        lang = self.settings.get('language', 'ru')
        winws_folder = get_winws_path()
        
        if not os.path.exists(winws_folder):
            msg = QMessageBox(self)
            msg.setWindowTitle('Ошибка')
            msg.setText('Папка winws не найдена')
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.exec()
            return
        
        # Ищем все .bat файлы
        bat_files = []
        for filename in os.listdir(winws_folder):
            if filename.endswith('.bat') and os.path.isfile(os.path.join(winws_folder, filename)):
                bat_files.append(filename)
        
        if not bat_files:
            if not silent:
                msg = QMessageBox(self)
                msg.setWindowTitle('Информация')
                msg.setText('Не найдено .bat файлов для обработки')
                msg.setIcon(QMessageBox.Icon.Information)
                msg.exec()
            return
        
        # Подтверждение (только если не silent режим)
        if not silent:
            reply = QMessageBox.question(
                self,
                'Добавить /B флаг',
                f'Будет обработано файлов: {len(bat_files)}\n\n'
                f'Во всех .bat файлах будет найдена строка:\n'
                f'start "zapret: %~n0" /min\n\n'
                f'И заменена на:\n'
                f'start "zapret: %~n0" /B /min\n\n'
                f'Продолжить?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # Обрабатываем файлы
        processed_count = 0
        modified_count = 0
        errors = []
        
        for filename in bat_files:
            file_path = os.path.join(winws_folder, filename)
            try:
                # Читаем файл
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Ищем и заменяем строку
                old_string = 'start "zapret: %~n0" /min'
                new_string = 'start "zapret: %~n0" /B /min'
                
                if old_string in content:
                    # Заменяем все вхождения
                    new_content = content.replace(old_string, new_string)
                    
                    # Сохраняем файл
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    
                    modified_count += 1
                
                processed_count += 1
            except Exception as e:
                errors.append(f'{filename}: {str(e)}')
        
        # Показываем результат (только если не silent режим)
        if not silent:
            result_text = f'Обработано файлов: {processed_count}\n'
            result_text += f'Изменено файлов: {modified_count}'
            
            if errors:
                result_text += f'\n\nОшибки:\n' + '\n'.join(errors)
            
            msg = QMessageBox(self)
            msg.setWindowTitle('Результат')
            msg.setText(result_text)
            if errors:
                msg.setIcon(QMessageBox.Icon.Warning)
            else:
                msg.setIcon(QMessageBox.Icon.Information)
            msg.exec()
    
    def remove_b_flag_from_all_strategies(self, silent=False):
        """Удаляет /B флаг из всех .bat файлов стратегий
        
        Args:
            silent: Если True, не показывает диалоги подтверждения и результатов
        """
        lang = self.settings.get('language', 'ru')
        winws_folder = get_winws_path()
        
        if not os.path.exists(winws_folder):
            msg = QMessageBox(self)
            msg.setWindowTitle('Ошибка' if lang == 'ru' else 'Error')
            msg.setText('Папка winws не найдена' if lang == 'ru' else 'winws folder not found')
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.exec()
            return
        
        # Ищем все .bat файлы
        bat_files = []
        for filename in os.listdir(winws_folder):
            if filename.endswith('.bat') and os.path.isfile(os.path.join(winws_folder, filename)):
                bat_files.append(filename)
        
        if not bat_files:
            if not silent:
                msg = QMessageBox(self)
                msg.setWindowTitle('Информация' if lang == 'ru' else 'Information')
                msg.setText('Не найдено .bat файлов для обработки' if lang == 'ru' else 'No .bat files found to process')
                msg.setIcon(QMessageBox.Icon.Information)
                msg.exec()
            return
        
        # Подтверждение (только если не silent режим)
        if not silent:
            if lang == 'ru':
                reply = QMessageBox.question(
                    self,
                    'Удалить /B флаг',
                    f'Будет обработано файлов: {len(bat_files)}\n\n'
                    f'Во всех .bat файлах будет найдена строка:\n'
                    f'start "zapret: %~n0" /B /min\n\n'
                    f'И заменена на:\n'
                    f'start "zapret: %~n0" /min\n\n'
                    f'Продолжить?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
            else:
                reply = QMessageBox.question(
                    self,
                    'Remove /B flag',
                    f'Files to process: {len(bat_files)}\n\n'
                    f'In all .bat files, the line:\n'
                    f'start "zapret: %~n0" /B /min\n\n'
                    f'Will be replaced with:\n'
                    f'start "zapret: %~n0" /min\n\n'
                    f'Continue?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # Обрабатываем файлы
        processed_count = 0
        modified_count = 0
        errors = []
        
        for filename in bat_files:
            file_path = os.path.join(winws_folder, filename)
            try:
                # Читаем файл
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Ищем и заменяем строку
                old_string = 'start "zapret: %~n0" /B /min'
                new_string = 'start "zapret: %~n0" /min'
                
                if old_string in content:
                    # Заменяем все вхождения
                    new_content = content.replace(old_string, new_string)
                    
                    # Сохраняем файл
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    
                    modified_count += 1
                
                processed_count += 1
            except Exception as e:
                errors.append(f'{filename}: {str(e)}')
        
        # Показываем результат (только если не silent режим)
        if not silent:
            if lang == 'ru':
                result_text = f'Обработано файлов: {processed_count}\n'
                result_text += f'Изменено файлов: {modified_count}'
                
                if errors:
                    result_text += f'\n\nОшибки:\n' + '\n'.join(errors)
                
                msg = QMessageBox(self)
                msg.setWindowTitle('Результат')
                msg.setText(result_text)
            else:
                result_text = f'Processed files: {processed_count}\n'
                result_text += f'Modified files: {modified_count}'
                
                if errors:
                    result_text += f'\n\nErrors:\n' + '\n'.join(errors)
                
                msg = QMessageBox(self)
                msg.setWindowTitle('Result')
                msg.setText(result_text)
            
            if errors:
                msg.setIcon(QMessageBox.Icon.Warning)
            else:
                msg.setIcon(QMessageBox.Icon.Information)
            msg.exec()
    
    def remove_check_updates_from_all_strategies(self, silent=False):
        """Удаляет строку "call service.bat check_updates" из всех .bat файлов стратегий
        
        Args:
            silent: Если True, не показывает диалоги подтверждения и результатов
        """
        lang = self.settings.get('language', 'ru')
        winws_folder = get_winws_path()
        
        if not os.path.exists(winws_folder):
            if not silent:
                msg = QMessageBox(self)
                msg.setWindowTitle('Ошибка')
                msg.setText('Папка winws не найдена')
                msg.setIcon(QMessageBox.Icon.Warning)
                msg.exec()
            return
        
        # Ищем все .bat файлы
        bat_files = []
        for filename in os.listdir(winws_folder):
            if filename.endswith('.bat') and os.path.isfile(os.path.join(winws_folder, filename)):
                bat_files.append(filename)
        
        if not bat_files:
            return
        
        # Обрабатываем файлы
        processed_count = 0
        modified_count = 0
        errors = []
        
        for filename in bat_files:
            file_path = os.path.join(winws_folder, filename)
            try:
                # Читаем файл
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                
                # Удаляем строки с "call service.bat check_updates"
                new_lines = []
                modified = False
                for line in lines:
                    # Проверяем, содержит ли строка "call service.bat check_updates"
                    # Учитываем возможные пробелы и регистр
                    stripped_line = line.strip()
                    # Проверяем точное совпадение или с возможными пробелами
                    if (stripped_line.lower() == 'call service.bat check_updates' or
                        'call service.bat check_updates' in stripped_line.lower()):
                        modified = True
                        continue  # Пропускаем эту строку
                    new_lines.append(line)
                
                if modified:
                    # Сохраняем файл
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.writelines(new_lines)
                    modified_count += 1
                
                processed_count += 1
            except Exception as e:
                errors.append(f'{filename}: {str(e)}')
        
        # Показываем результат (только если не silent режим)
        if not silent and (modified_count > 0 or errors):
            result_text = f'Обработано файлов: {processed_count}\n'
            result_text += f'Изменено файлов: {modified_count}'
            
            if errors:
                result_text += f'\n\nОшибки:\n' + '\n'.join(errors)
            
            msg = QMessageBox(self)
            msg.setWindowTitle('Результат')
            msg.setText(result_text)
            if errors:
                msg.setIcon(QMessageBox.Icon.Warning)
            else:
                msg.setIcon(QMessageBox.Icon.Information)
            msg.exec()
    
    def toggle_remove_check_updates(self):
        """Переключает настройку удаления проверки обновлений"""
        checked = self.remove_check_updates_action.isChecked()
        self.settings['remove_check_updates'] = checked
        self.config.set_setting('remove_check_updates', checked)
    
    def update_ipset_list(self):
        """Обновляет список IPSet из репозитория"""
        lang = self.settings.get('language', 'ru')
        winws_folder = get_winws_path()
        list_file = os.path.join(winws_folder, 'lists', 'ipset-all.txt')
        url = 'https://raw.githubusercontent.com/Flowseal/zapret-discord-youtube/refs/heads/main/.service/ipset-service.txt'
        
        # Показываем прогресс
        progress_dialog = QProgressDialog(self)
        progress_dialog.setWindowTitle(tr('update_ipset_list', lang))
        progress_dialog.setLabelText('Обновление ipset-all...' if lang == 'ru' else 'Updating ipset-all...')
        progress_dialog.setRange(0, 0)
        progress_dialog.setCancelButton(None)
        progress_dialog.show()
        QApplication.processEvents()
        
        try:
            # Создаем директорию если не существует
            os.makedirs(os.path.dirname(list_file), exist_ok=True)
            
            # Пробуем использовать curl
            curl_path = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'curl.exe')
            if os.path.exists(curl_path):
                result = subprocess.run(
                    [curl_path, '-L', '-o', list_file, url],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode != 0:
                    raise Exception(f'curl failed: {result.stderr}')
            else:
                # Используем PowerShell
                ps_command = f'''
$url = '{url}';
$out = '{list_file}';
$dir = Split-Path -Parent $out;
if (-not (Test-Path $dir)) {{ New-Item -ItemType Directory -Path $dir | Out-Null }};
$res = Invoke-WebRequest -Uri $url -TimeoutSec 10 -UseBasicParsing;
if ($res.StatusCode -eq 200) {{ $res.Content | Out-File -FilePath $out -Encoding UTF8 }} else {{ exit 1 }}
'''
                result = subprocess.run(
                    ['powershell', '-Command', ps_command],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode != 0:
                    raise Exception(f'PowerShell failed: {result.stderr}')
            
            progress_dialog.close()
            
            msg = QMessageBox(self)
            msg.setWindowTitle(tr('update_ipset_list', lang))
            msg.setText('IPSet List успешно обновлен.' if lang == 'ru' else 'IPSet List updated successfully.')
            msg.setIcon(QMessageBox.Icon.Information)
            msg.exec()
        except Exception as e:
            progress_dialog.close()
            msg = QMessageBox(self)
            msg.setWindowTitle('Ошибка' if lang == 'ru' else 'Error')
            msg.setText(f'Ошибка при обновлении IPSet List: {str(e)}' if lang == 'ru' else f'Error updating IPSet List: {str(e)}')
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.exec()
    
    def update_hosts_file(self):
        """Обновляет hosts файл из репозитория"""
        lang = self.settings.get('language', 'ru')
        hosts_file = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'drivers', 'etc', 'hosts')
        hosts_url = 'https://raw.githubusercontent.com/Flowseal/zapret-discord-youtube/refs/heads/main/.service/hosts'
        temp_file = os.path.join(os.environ.get('TEMP', 'C:\\Temp'), 'zapret_hosts.txt')
        
        # Показываем прогресс
        progress_dialog = QProgressDialog(self)
        progress_dialog.setWindowTitle(tr('update_hosts_file', lang))
        progress_dialog.setLabelText('Проверка hosts файла...' if lang == 'ru' else 'Checking hosts file...')
        progress_dialog.setRange(0, 0)
        progress_dialog.setCancelButton(None)
        progress_dialog.show()
        QApplication.processEvents()
        
        try:
            # Скачиваем файл
            curl_path = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'curl.exe')
            if os.path.exists(curl_path):
                result = subprocess.run(
                    [curl_path, '-L', '-s', '-o', temp_file, hosts_url],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode != 0:
                    raise Exception(f'curl failed: {result.stderr}')
            else:
                # Используем PowerShell
                ps_command = f'''
$url = '{hosts_url}';
$out = '{temp_file}';
$res = Invoke-WebRequest -Uri $url -TimeoutSec 10 -UseBasicParsing;
if ($res.StatusCode -eq 200) {{ $res.Content | Out-File -FilePath $out -Encoding UTF8 }} else {{ exit 1 }}
'''
                result = subprocess.run(
                    ['powershell', '-Command', ps_command],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode != 0:
                    raise Exception(f'PowerShell failed: {result.stderr}')
            
            if not os.path.exists(temp_file):
                raise Exception('Не удалось скачать hosts файл из репозитория' if lang == 'ru' else 'Failed to download hosts file from repository')
            
            # Читаем первую и последнюю строки из скачанного файла
            with open(temp_file, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
            
            if not lines:
                raise Exception('Скачанный файл пуст' if lang == 'ru' else 'Downloaded file is empty')
            
            first_line = lines[0]
            last_line = lines[-1]
            
            # Проверяем, нужно ли обновление
            needs_update = False
            if os.path.exists(hosts_file):
                with open(hosts_file, 'r', encoding='utf-8') as f:
                    hosts_content = f.read()
                    if first_line not in hosts_content or last_line not in hosts_content:
                        needs_update = True
            else:
                needs_update = True
            
            progress_dialog.close()
            
            if needs_update:
                # Открываем скачанный файл в notepad и проводник с hosts файлом
                msg = QMessageBox(self)
                msg.setWindowTitle(tr('update_hosts_file', lang))
                msg.setText('Hosts файл требует обновления. Пожалуйста, вручную скопируйте содержимое из открытого файла в ваш hosts файл.' if lang == 'ru' else 'Hosts file needs to be updated. Please manually copy the content from the opened file to your hosts file.')
                msg.setIcon(QMessageBox.Icon.Information)
                msg.exec()
                
                # Открываем скачанный файл в notepad
                subprocess.Popen(['notepad', temp_file])
                
                # Открываем проводник с hosts файлом
                subprocess.Popen(['explorer', '/select,', hosts_file])
            else:
                # Удаляем временный файл
                try:
                    os.remove(temp_file)
                except:
                    pass
                
                msg = QMessageBox(self)
                msg.setWindowTitle(tr('update_hosts_file', lang))
                msg.setText('Hosts файл актуален.' if lang == 'ru' else 'Hosts file is up to date.')
                msg.setIcon(QMessageBox.Icon.Information)
                msg.exec()
        except Exception as e:
            progress_dialog.close()
            msg = QMessageBox(self)
            msg.setWindowTitle('Ошибка' if lang == 'ru' else 'Error')
            msg.setText(f'Ошибка при обновлении Hosts File: {str(e)}' if lang == 'ru' else f'Error updating Hosts File: {str(e)}')
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.exec()
    
    def update_filter_statuses(self):
        """Обновляет статусы Game Filter и IPSet Filter из файлов и синхронизирует с конфигом"""
        winws_folder = get_winws_path()
        
        # Проверяем Game Filter
        game_flag_file = os.path.join(winws_folder, 'utils', 'game_filter.enabled')
        game_filter_enabled = os.path.exists(game_flag_file)
        
        # Синхронизируем с конфигом
        if game_filter_enabled != self.settings.get('game_filter_enabled', False):
            self.settings['game_filter_enabled'] = game_filter_enabled
            self.config.set_setting('game_filter_enabled', game_filter_enabled)
        
        if hasattr(self, 'game_filter_action'):
            self.game_filter_action.setChecked(game_filter_enabled)
        
        # Проверяем IPSet Filter
        ipset_file = os.path.join(winws_folder, 'lists', 'ipset-all.txt')
        ipset_mode = 'loaded'  # По умолчанию
        ipset_enabled = False
        
        if os.path.exists(ipset_file):
            try:
                with open(ipset_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    line_count = len([line for line in content.split('\n') if line.strip()])
                    
                    if line_count == 0:
                        ipset_mode = 'any'
                    elif content == '203.0.113.113/32':
                        ipset_mode = 'none'
                    else:
                        ipset_mode = 'loaded'
                        ipset_enabled = True
            except:
                pass
        
        # Синхронизируем с конфигом
        if ipset_mode != self.settings.get('ipset_filter_mode', 'loaded'):
            self.settings['ipset_filter_mode'] = ipset_mode
            self.config.set_setting('ipset_filter_mode', ipset_mode)
        
        if hasattr(self, 'ipset_filter_action'):
            self.ipset_filter_action.setChecked(ipset_enabled)
    
    def toggle_game_filter(self):
        """Переключает Game Filter"""
        winws_folder = get_winws_path()
        game_flag_file = os.path.join(winws_folder, 'utils', 'game_filter.enabled')
        
        lang = self.settings.get('language', 'ru')
        
        try:
            if os.path.exists(game_flag_file):
                # Отключаем
                os.remove(game_flag_file)
                game_filter_enabled = False
                msg = QMessageBox(self)
                msg.setWindowTitle(tr('settings_game_filter', lang))
                msg.setText('Game Filter отключен. Перезапустите zapret для применения изменений.' if lang == 'ru' else 'Game Filter disabled. Restart zapret to apply changes.')
                msg.setIcon(QMessageBox.Icon.Information)
                msg.exec()
            else:
                # Включаем
                os.makedirs(os.path.dirname(game_flag_file), exist_ok=True)
                with open(game_flag_file, 'w', encoding='utf-8') as f:
                    f.write('ENABLED')
                game_filter_enabled = True
                msg = QMessageBox(self)
                msg.setWindowTitle(tr('settings_game_filter', lang))
                msg.setText('Game Filter включен. Перезапустите zapret для применения изменений.' if lang == 'ru' else 'Game Filter enabled. Restart zapret to apply changes.')
                msg.setIcon(QMessageBox.Icon.Information)
                msg.exec()
            
            # Сохраняем в конфиг
            self.settings['game_filter_enabled'] = game_filter_enabled
            self.config.set_setting('game_filter_enabled', game_filter_enabled)
            
            # Обновляем статус
            self.update_filter_statuses()
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle('Ошибка' if lang == 'ru' else 'Error')
            msg.setText(f'Ошибка при переключении Game Filter: {str(e)}' if lang == 'ru' else f'Error toggling Game Filter: {str(e)}')
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.exec()
    
    def toggle_ipset_filter(self):
        """Переключает IPSet Filter"""
        winws_folder = get_winws_path()
        list_file = os.path.join(winws_folder, 'lists', 'ipset-all.txt')
        backup_file = list_file + '.backup'
        
        lang = self.settings.get('language', 'ru')
        ipset_mode = None
        
        try:
            if not os.path.exists(list_file):
                msg = QMessageBox(self)
                msg.setWindowTitle('Ошибка' if lang == 'ru' else 'Error')
                msg.setText('Файл ipset-all.txt не найден.' if lang == 'ru' else 'ipset-all.txt file not found.')
                msg.setIcon(QMessageBox.Icon.Warning)
                msg.exec()
                return
            
            # Читаем текущее состояние
            with open(list_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            line_count = len([line for line in content.split('\n') if line.strip()])
            
            if line_count == 0:
                # Режим "any" - переключаем на "loaded" (восстанавливаем из backup)
                if os.path.exists(backup_file):
                    os.remove(list_file)
                    os.rename(backup_file, list_file)
                    ipset_mode = 'loaded'
                    msg = QMessageBox(self)
                    msg.setWindowTitle(tr('settings_ipset_filter', lang))
                    msg.setText('IPSet фильтр переключен в режим loaded. Перезапустите zapret для применения изменений.' if lang == 'ru' else 'IPSet Filter switched to loaded mode. Restart zapret to apply changes.')
                    msg.setIcon(QMessageBox.Icon.Information)
                    msg.exec()
                else:
                    msg = QMessageBox(self)
                    msg.setWindowTitle('Ошибка' if lang == 'ru' else 'Error')
                    msg.setText('Резервная копия не найдена. Обновите список из меню обновлений сначала.' if lang == 'ru' else 'Backup not found. Update list from update menu first.')
                    msg.setIcon(QMessageBox.Icon.Warning)
                    msg.exec()
                    return
            elif content == '203.0.113.113/32':
                # Режим "none" - переключаем на "any" (делаем файл пустым)
                with open(list_file, 'w', encoding='utf-8') as f:
                    f.write('')
                ipset_mode = 'any'
                msg = QMessageBox(self)
                msg.setWindowTitle(tr('settings_ipset_filter', lang))
                msg.setText('IPSet фильтр переключен в режим any. Перезапустите zapret для применения изменений.' if lang == 'ru' else 'IPSet Filter switched to any mode. Restart zapret to apply changes.')
                msg.setIcon(QMessageBox.Icon.Information)
                msg.exec()
            else:
                # Режим "loaded" - переключаем на "none" (сохраняем backup и заменяем на один IP)
                if not os.path.exists(backup_file):
                    os.rename(list_file, backup_file)
                else:
                    os.remove(backup_file)
                    os.rename(list_file, backup_file)
                
                with open(list_file, 'w', encoding='utf-8') as f:
                    f.write('203.0.113.113/32')
                ipset_mode = 'none'
                msg = QMessageBox(self)
                msg.setWindowTitle(tr('settings_ipset_filter', lang))
                msg.setText('IPSet фильтр переключен в режим none. Перезапустите zapret для применения изменений.' if lang == 'ru' else 'IPSet Filter switched to none mode. Restart zapret to apply changes.')
                msg.setIcon(QMessageBox.Icon.Information)
                msg.exec()
            
            # Сохраняем в конфиг
            if ipset_mode:
                self.settings['ipset_filter_mode'] = ipset_mode
                self.config.set_setting('ipset_filter_mode', ipset_mode)
            
            # Обновляем статус
            self.update_filter_statuses()
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle('Ошибка' if lang == 'ru' else 'Error')
            msg.setText(f'Ошибка при переключении IPSet Filter: {str(e)}' if lang == 'ru' else f'Error toggling IPSet Filter: {str(e)}')
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.exec()
    
    def load_version_info(self):
        """Загружает информацию о версии и MD5 из app_version.json"""
        try:
            config_path = get_config_path("app/config/app_version.json")
            if os.path.exists(config_path):
                import json
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    version = data.get('version', 'unknown')
                    md5 = data.get('md5', 'unknown')
                    # Форматируем текст без квадратных скобок
                    version_text = f"{version}\n{md5}"
                    self.version_label.setText(version_text)
            else:
                self.version_label.setText("[unknown]\n[unknown]")
        except Exception as e:
            self.version_label.setText("[error]\n[error]")
    
    def open_github(self):
        """Открывает страницу GitHub проекта"""
        url = QUrl('https://github.com/th6c/metrosdpi')
        QDesktopServices.openUrl(url)
    
    def open_github_zapret(self):
        """Открывает страницу GitHub проекта zapret-discord-youtube"""
        url = QUrl('https://github.com/Flowseal/zapret-discord-youtube')
        QDesktopServices.openUrl(url)
    
    def open_help(self):
        """Открывает справку программы (PDF файл)"""
        lang = self.settings.get('language', 'ru')
        base_path = get_base_path()
        help_file = os.path.join(base_path, 'docs', 'metrosdpi.pdf')
        
        if os.path.exists(help_file):
            # Открываем PDF файл с помощью системного приложения по умолчанию
            QDesktopServices.openUrl(QUrl.fromLocalFile(help_file))
        else:
            msg = QMessageBox(self)
            msg.setWindowTitle(tr('help_file_not_found_title', lang))
            msg.setText(tr('help_file_not_found_text', lang).format(help_file))
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.exec()
    
    def open_winws_folder(self):
        """Открывает папку winws в проводнике Windows"""
        winws_folder = get_winws_path()
        if os.path.exists(winws_folder):
            # Открываем папку в проводнике Windows
            os.startfile(winws_folder)
        else:
            lang = self.settings.get('language', 'ru')
            msg = QMessageBox(self)
            msg.setWindowTitle(tr('msg_winws_not_found', lang))
            msg.setText(tr('msg_winws_not_found', lang))
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.exec()
    
    def load_bat_files(self):
        """Загружает названия .bat файлов из папки winws"""
        lang = self.settings.get('language', 'ru')
        winws_folder = get_winws_path()
        bat_files = []
        
        if os.path.exists(winws_folder):
            # Получаем все файлы из папки winws
            for filename in os.listdir(winws_folder):
                # Проверяем, что это .bat файл и это файл, а не папка
                if filename.endswith('.bat') and os.path.isfile(os.path.join(winws_folder, filename)):
                    # Убираем расширение .bat
                    name_without_ext = filename[:-4]  # Убираем последние 4 символа (.bat)
                    bat_files.append(name_without_ext)
            
            # Сортируем список для удобства
            bat_files.sort()
            
            # Добавляем в ComboBox
            if bat_files:
                self.combo_box.addItems(bat_files)
            else:
                self.combo_box.addItem(tr('msg_no_bat_files', lang))
        else:
            self.combo_box.addItem(tr('msg_winws_not_found', lang))
    
    def restore_last_strategy(self):
        """Восстанавливает последнюю выбранную стратегию"""
        last_strategy = self.settings.get('last_strategy', '')
        if last_strategy:
            index = self.combo_box.findText(last_strategy)
            if index >= 0:
                self.combo_box.setCurrentIndex(index)
                # Если включен автозапуск, запускаем стратегию
                if self.settings.get('auto_start_last_strategy', False):
                    # Небольшая задержка, чтобы окно успело отобразиться
                    QTimer.singleShot(500, self.auto_start_strategy)
    
    def auto_start_strategy(self):
        """Автоматически запускает выбранную стратегию"""
        if not self.is_running:
            self.toggle_action()
    
    def auto_start_last_strategy(self):
        """Автоматически запускает последнюю сохраненную стратегию при запуске программы
        Запускает стратегию только если last_strategy явно указан в конфиге и найден в списке"""
        last_strategy = self.settings.get('last_strategy', '')
        
        # Если last_strategy не указан (пустой), не запускаем ничего
        # Пользователь должен сам выбрать стратегию при первом запуске
        if not last_strategy:
            return
        
        # Пытаемся найти указанную стратегию в списке
        index = self.combo_box.findText(last_strategy)
        if index < 0:
            # Стратегия не найдена в списке - не запускаем
            return
        
        # Стратегия найдена - выбираем и запускаем её
        self.combo_box.setCurrentIndex(index)
        # Запускаем стратегию, если она еще не запущена
        if not self.is_running:
            self.start_bat_file()
    
    def restart_strategy(self):
        """Перезапускает стратегию, которая была запущена ранее"""
        # ВАЖНО: Проверяем настройку автоперезапуска ПЕРВЫМ делом
        # Если настройка выключена, не перезапускаем
        if not self.settings.get('auto_restart_strategy', False):
            return
        
        # Не перезапускаем, если пользователь явно остановил процесс или уже идет перезапуск
        if not self.running_strategy or self.is_restarting or self.user_stopped:
            return
        
        # Устанавливаем флаг перезапуска
        self.is_restarting = True
        
        # Проверяем, что стратегия все еще существует
        index = self.combo_box.findText(self.running_strategy)
        if index < 0:
            # Стратегия больше не существует
            self.running_strategy = None
            self.is_restarting = False
            return
        
        # Проверяем еще раз перед запуском (на случай, если пользователь нажал Stop во время задержки)
        if self.user_stopped:
            self.is_restarting = False
            return
        
        # Выбираем стратегию в ComboBox
        self.combo_box.setCurrentIndex(index)
        
        # Запускаем стратегию
        if not self.is_running:
            self.start_bat_file()
        
        # Сбрасываем флаг перезапуска через небольшую задержку
        QTimer.singleShot(2000, lambda: setattr(self, 'is_restarting', False))
    
    def on_strategy_changed(self, strategy_name):
        """Обработчик изменения стратегии в ComboBox"""
        if strategy_name and strategy_name not in ['Нет .bat файлов', 'Папка winws не найдена']:
            self.config.set_setting('last_strategy', strategy_name)
            self.settings['last_strategy'] = strategy_name
    
    def init_tray(self):
        self.tray = SystemTray(self)
        # Применяем настройку show_in_tray при инициализации
        if self.settings.get('show_in_tray', True):
            self.tray.show()
        else:
            self.tray.hide()
    
    def center_window(self):
        """Центрирует окно на экране"""
        screen = QApplication.primaryScreen().geometry()
        window_geometry = self.frameGeometry()
        window_geometry.moveCenter(screen.center())
        self.move(window_geometry.topLeft())
    
    def toggle_action(self):
        """Переключает состояние между Запустить и Остановить"""
        lang = self.settings.get('language', 'ru')
        if not self.is_running:
            # Запускаем .bat файл
            self.user_stopped = False  # Сбрасываем флаг при запуске
            self.start_bat_file()
        else:
            # Останавливаем процесс winws.exe
            # ВАЖНО: Устанавливаем флаги ДО остановки процесса, чтобы check_winws_process() их увидел
            self.user_stopped = True  # Устанавливаем флаг явной остановки пользователем
            self.running_strategy = None  # Очищаем название стратегии при явной остановке
            self.is_restarting = False  # Сбрасываем флаг перезапуска
            # Теперь останавливаем процесс
            self.stop_winws_process()
    
    def start_bat_file(self):
        """Запускает выбранный .bat файл"""
        lang = self.settings.get('language', 'ru')
        current_strategy = self.combo_box.currentText()
        
        # Проверяем, что стратегия выбрана
        if not current_strategy or current_strategy in [tr('msg_no_bat_files', lang), tr('msg_winws_not_found', lang)]:
            msg = QMessageBox(self)
            msg.setWindowTitle('Ошибка')
            msg.setText('Не выбрана стратегия для запуска')
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.exec()
            return
        
        # Формируем путь к .bat файлу
        bat_filename = f"{current_strategy}.bat"
        winws_folder = get_winws_path()
        bat_path = os.path.join(winws_folder, bat_filename)
        
        if not os.path.exists(bat_path):
            msg = QMessageBox(self)
            msg.setWindowTitle('Ошибка')
            msg.setText(f'Файл {bat_filename} не найден по пути: {bat_path}')
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.exec()
            return
        
        try:
            # Получаем абсолютный путь к файлу
            bat_path_abs = os.path.abspath(bat_path)
            bat_dir = os.path.dirname(bat_path_abs)
            
            # В Windows запускаем через cmd.exe в фоне
            if os.name == 'nt':
                # Запускаем .bat файл через cmd.exe в фоне (без окна консоли)
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                
                self.bat_process = subprocess.Popen(
                    ['cmd.exe', '/c', bat_path_abs],
                    cwd=bat_dir,
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                # Для других ОС
                self.bat_process = subprocess.Popen(
                    [bat_path_abs],
                    cwd=bat_dir,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            
            # Обновляем состояние
            self.is_running = True
            self.running_strategy = current_strategy  # Сохраняем название стратегии для перезапуска
            self.user_stopped = False  # Сбрасываем флаг явной остановки при запуске
            self.is_restarting = False  # Сбрасываем флаг перезапуска при успешном запуске
            
            # Проверяем, является ли файл служебным (service.bat и т.д.)
            # Для служебных файлов не проверяем появление winws.exe
            is_service_file = bat_filename.lower().startswith('service')
            
            import time
            # Сохраняем время запуска только для стратегий (не для служебных файлов)
            if not is_service_file:
                self.bat_start_time = time.time()  # Сохраняем время запуска для проверки
            else:
                self.bat_start_time = None  # Для служебных файлов не проверяем
            
            self.action_button.setText(tr('button_stop', lang))
            self.combo_box.setEnabled(False)  # Блокируем ComboBox
            
            # Сохраняем выбранную стратегию только если это не служебный файл
            if not is_service_file:
                self.config.set_setting('last_strategy', current_strategy)
                self.settings['last_strategy'] = current_strategy
            else:
                # Для служебных файлов не сохраняем как последнюю стратегию
                self.running_strategy = None
            
        except Exception as e:
            msg = QMessageBox(self)
            msg.setWindowTitle('Ошибка')
            msg.setText(f'Ошибка при запуске: {str(e)}')
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.exec()
            # В случае ошибки разблокируем ComboBox
            self.combo_box.setEnabled(True)
    
    def stop_winws_process(self, silent=False):
        """Останавливает процесс winws.exe
        
        Args:
            silent: Если True, не показывает сообщения об ошибках и не обновляет UI
        """
        lang = self.settings.get('language', 'ru')
        
        # Если это не silent режим (явная остановка пользователем), устанавливаем флаги ДО остановки процесса
        # чтобы предотвратить автоперезапуск в check_winws_process()
        # ВАЖНО: Флаги уже должны быть установлены в toggle_action(), но устанавливаем их здесь тоже для надежности
        if not silent:
            # Временно останавливаем мониторинг процесса, чтобы он не мешал остановке
            self.process_monitor_timer.stop()
            
            # Устанавливаем флаги синхронно ДО остановки процесса
            self.user_stopped = True  # Устанавливаем флаг явной остановки
            self.running_strategy = None  # Очищаем название стратегии сразу
            self.is_restarting = False  # Сбрасываем флаг перезапуска
        
        try:
            # Ищем и завершаем ВСЕ процессы winws.exe
            killed_count = 0
            processes_to_kill = []
            
            # Сначала собираем все процессы winws.exe
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] and proc.info['name'].lower() == 'winws.exe':
                        processes_to_kill.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # Завершаем все найденные процессы через terminate
            for proc in processes_to_kill:
                try:
                    proc.terminate()
                    killed_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # Ждем немного, чтобы процессы успели завершиться
            import time
            if killed_count > 0:
                time.sleep(0.5)
            
            # Проверяем, остались ли процессы, и убиваем их через kill
            remaining_processes = []
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] and proc.info['name'].lower() == 'winws.exe':
                        remaining_processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # Убиваем оставшиеся процессы через kill
            for proc in remaining_processes:
                try:
                    proc.kill()
                    killed_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # Обновляем состояние только если не silent режим
            if not silent:
                self.is_running = False
                self.bat_start_time = None  # Сбрасываем время запуска
                self.action_button.setText(tr('button_start', lang))
                self.combo_box.setEnabled(True)  # Разблокируем ComboBox
                self.bat_process = None
                
                # Возобновляем мониторинг процесса после остановки
                # Но только через небольшую задержку, чтобы дать процессу время завершиться
                QTimer.singleShot(2000, lambda: self.process_monitor_timer.start(1000))
            
        except Exception as e:
            if not silent:
                msg = QMessageBox(self)
                msg.setWindowTitle('Ошибка')
                msg.setText(f'Ошибка при остановке процесса: {str(e)}')
                msg.setIcon(QMessageBox.Icon.Critical)
                msg.exec()
    
    def check_winws_process(self):
        """Проверяет наличие процесса winws.exe и обновляет состояние кнопки
        Также проверяет, появился ли процесс winws.exe в течение 5 секунд после запуска стратегии"""
        lang = self.settings.get('language', 'ru')
        import time
        
        # Проверяем, запущен ли процесс winws.exe
        winws_running = False
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] and proc.info['name'].lower() == 'winws.exe':
                        winws_running = True
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
        except Exception:
            pass
        
        # Проверка запуска: если прошло более 5 секунд с момента запуска .bat файла
        # и процесс winws.exe не появился - останавливаем процесс запуска
        # ВАЖНО: Проверка выполняется только один раз, после чего bat_start_time сбрасывается
        if (self.bat_start_time is not None and 
            self.is_running and 
            not self.user_stopped and
            self.bat_process is not None):
            elapsed_time = time.time() - self.bat_start_time
            if elapsed_time >= 5.0:
                # Прошло 5 секунд - проверяем один раз и сбрасываем время запуска
                strategy_name = self.running_strategy if self.running_strategy else self.combo_box.currentText()
                self.bat_start_time = None  # Сбрасываем время запуска сразу, чтобы проверка не повторялась
                
                if not winws_running:
                    # Процесс не появился в течение 5 секунд - останавливаем запуск
                    # Останавливаем процесс .bat файла
                    try:
                        self.bat_process.terminate()
                        try:
                            self.bat_process.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            self.bat_process.kill()
                    except Exception:
                        pass
                    
                    # Обновляем состояние
                    self.is_running = False
                    self.running_strategy = None
                    self.bat_process = None
                    self.action_button.setText(tr('button_start', lang))
                    self.combo_box.setEnabled(True)
                    
                    # Показываем сообщение об ошибке
                    msg = QMessageBox(self)
                    msg.setWindowTitle('Ошибка запуска')
                    msg.setText(f'Стратегия "{strategy_name}" не запустилась.\n'
                               'Процесс winws.exe не появился в течение 5 секунд.\n\n'
                               'Возможно, стратегия не работает или требует дополнительной настройки.')
                    msg.setIcon(QMessageBox.Icon.Warning)
                    msg.exec()
                    return
        
        # Если процесс winws.exe появился, сбрасываем время запуска (если еще не сброшено)
        if winws_running and self.bat_start_time is not None:
            self.bat_start_time = None
        
        # Синхронизируем состояние кнопки с реальным состоянием процесса
        if winws_running and not self.is_running:
            # Процесс запущен, но кнопка показывает "Запустить"
            self.is_running = True
            self.action_button.setText(tr('button_stop', lang))
            self.combo_box.setEnabled(False)
        elif not winws_running and self.is_running:
            # Процесс остановлен, но кнопка показывает "Остановить"
            self.is_running = False
            self.action_button.setText(tr('button_start', lang))
            self.combo_box.setEnabled(True)
            self.bat_process = None
            
            # ВАЖНО: Проверяем флаг user_stopped ПЕРВЫМ делом
            # Если пользователь явно остановил процесс, НЕ запускаем автоперезапуск
            if self.user_stopped:
                # Пользователь явно остановил процесс - не перезапускаем
                # Флаг будет сброшен при следующем запуске стратегии
                # Также очищаем running_strategy на всякий случай
                self.running_strategy = None
                self.is_restarting = False  # Сбрасываем флаг перезапуска
                return
            
            # ВАЖНО: Проверяем настройку автоперезапуска ВТОРЫМ делом
            # Если настройка выключена, НЕ делаем НИЧЕГО связанного с перезапуском
            auto_restart_enabled = self.settings.get('auto_restart_strategy', False)
            if not auto_restart_enabled:
                # Настройка выключена - полностью отключаем логику перезапуска
                # Очищаем все связанные флаги
                self.running_strategy = None
                self.is_restarting = False
                return
            
            # Только если настройка ВКЛЮЧЕНА и все остальные условия выполнены
            # Если включен автоперезапуск и была запущена стратегия, перезапускаем её
            # Проверяем, что мы не в процессе перезапуска, чтобы избежать множественных перезапусков
            if (self.running_strategy and 
                not self.is_restarting):
                # Небольшая задержка перед перезапуском
                QTimer.singleShot(1000, self.restart_strategy)
    
    def closeEvent(self, event):
        """Обработка закрытия окна - скрывает в трей"""
        lang = self.settings.get('language', 'ru')
        if self.settings.get('show_in_tray', True):
            event.ignore()
            self.hide()
            self.tray.update_menu()  # Обновляем меню трея
        else:
            # Если трей отключен, закрываем приложение
            self.quit_application()

