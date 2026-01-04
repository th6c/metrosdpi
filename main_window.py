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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.bat_process = None  # Процесс запущенного .bat файла
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
            last_strategy = self.settings.get('last_strategy', '')
            if last_strategy:
                # Небольшая задержка, чтобы окно успело полностью инициализироваться
                QTimer.singleShot(1000, lambda: self.auto_start_last_strategy())
        
        # Если включен автозапуск последней стратегии, запускаем её
        if self.settings.get('auto_start_last_strategy', False):
            last_strategy = self.settings.get('last_strategy', '')
            if last_strategy:
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
        self.file_menu = None
        self.settings_menu = None
        self.update_menu = None
        self.strategies_menu = None
        self.strategies_main_menu = None
        self.add_b_flag_submenu = None
        self.language_menu = None
        self.check_updates_action = None
        self.manual_update_action = None
    
    def init_menu_bar(self):
        """Создает меню бар"""
        self.menubar = self.menuBar()
        
        # Меню "Файл"
        self.file_menu = self.menubar.addMenu('')
        
        # Выход
        self.exit_action = QAction('', self)
        self.exit_action.setShortcut('Ctrl+Q')
        self.exit_action.triggered.connect(self.quit_application)
        self.file_menu.addAction(self.exit_action)
        
        # Меню "Стратегии"
        self.strategies_main_menu = self.menubar.addMenu('')
        
        # Подменю "Список всех стратегий"
        self.strategies_menu = self.strategies_main_menu.addMenu('')
        self.update_strategies_menu(self.strategies_menu)
        
        self.strategies_main_menu.addSeparator()
        
        # Подменю "Добавление команды /B"
        self.add_b_flag_submenu = self.strategies_main_menu.addMenu('')
        
        # Добавить /B во все стратегии
        self.add_b_flag_action = QAction('', self)
        self.add_b_flag_action.triggered.connect(self.add_b_flag_to_all_strategies)
        self.add_b_flag_submenu.addAction(self.add_b_flag_action)
        
        # Добавлять /B при обновлении
        self.add_b_flag_on_update_action = QAction('', self)
        self.add_b_flag_on_update_action.setCheckable(True)
        self.add_b_flag_on_update_action.setChecked(self.settings.get('add_b_flag_on_update', False))
        self.add_b_flag_on_update_action.triggered.connect(self.toggle_add_b_flag_on_update)
        self.add_b_flag_submenu.addAction(self.add_b_flag_on_update_action)
        
        self.strategies_main_menu.addSeparator()
        
        # Запуск теста
        self.run_test_action = QAction('', self)
        self.run_test_action.triggered.connect(self.show_test_window)
        self.strategies_main_menu.addAction(self.run_test_action)
        
        # Меню "Настройки"
        self.settings_menu = self.menubar.addMenu('')
        
        # Сменить язык
        self.language_menu = self.settings_menu.addMenu('')
        self.language_group = QActionGroup(self)
        self.language_group.setExclusive(True)
        
        self.ru_action = QAction('Russian (Русский)', self)
        self.ru_action.setCheckable(True)
        self.ru_action.setChecked(self.settings.get('language', 'ru') == 'ru')
        self.ru_action.triggered.connect(lambda: self.set_language('ru'))
        self.language_group.addAction(self.ru_action)
        self.language_menu.addAction(self.ru_action)
        
        self.en_action = QAction('English (Английский)', self)
        self.en_action.setCheckable(True)
        self.en_action.setChecked(self.settings.get('language', 'ru') == 'en')
        self.en_action.triggered.connect(lambda: self.set_language('en'))
        self.language_group.addAction(self.en_action)
        self.language_menu.addAction(self.en_action)
        
        self.settings_menu.addSeparator()
        
        # === Настройки трея ===
        # Отображать в трее
        self.show_tray_action = QAction('', self)
        self.show_tray_action.setCheckable(True)
        self.show_tray_action.setChecked(self.settings.get('show_in_tray', True))
        self.show_tray_action.triggered.connect(self.toggle_show_in_tray)
        self.settings_menu.addAction(self.show_tray_action)
        
        # Запускать свернутым в трей
        self.start_minimized_action = QAction('', self)
        self.start_minimized_action.setCheckable(True)
        self.start_minimized_action.setChecked(self.settings.get('start_minimized', False))
        self.start_minimized_action.triggered.connect(self.toggle_start_minimized)
        self.settings_menu.addAction(self.start_minimized_action)
        
        self.settings_menu.addSeparator()
        
        # === Поведение при выходе ===
        # Закрывать winws при выходе
        self.close_winws_action = QAction('', self)
        self.close_winws_action.setCheckable(True)
        self.close_winws_action.setChecked(self.settings.get('close_winws_on_exit', True))
        self.close_winws_action.triggered.connect(self.toggle_close_winws)
        self.settings_menu.addAction(self.close_winws_action)
        
        self.settings_menu.addSeparator()
        
        # === Автозапуск ===
        # Автозапуск с Windows
        self.autostart_action = QAction('', self)
        self.autostart_action.setCheckable(True)
        self.autostart_action.setChecked(self.autostart_manager.is_enabled())
        self.autostart_action.triggered.connect(self.toggle_autostart)
        self.settings_menu.addAction(self.autostart_action)
        
        # Автозапуск последней стратегии
        self.auto_start_action = QAction('', self)
        self.auto_start_action.setCheckable(True)
        self.auto_start_action.setChecked(self.settings.get('auto_start_last_strategy', False))
        self.auto_start_action.triggered.connect(self.toggle_auto_start)
        self.settings_menu.addAction(self.auto_start_action)
        
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
        
        # Удалять проверку обновлений в winws
        self.remove_check_updates_action = QAction('', self)
        self.remove_check_updates_action.setCheckable(True)
        self.remove_check_updates_action.setChecked(self.settings.get('remove_check_updates', False))
        self.remove_check_updates_action.triggered.connect(self.toggle_remove_check_updates)
        self.update_menu.addAction(self.remove_check_updates_action)
        
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
        if self.file_menu:
            self.file_menu.setTitle(tr('menu_file', lang))
        if hasattr(self, 'strategies_main_menu') and self.strategies_main_menu:
            self.strategies_main_menu.setTitle(tr('menu_strategies', lang))
        if self.strategies_menu:
            self.strategies_menu.setTitle(tr('menu_list_strategies', lang))
        if hasattr(self, 'add_b_flag_submenu') and self.add_b_flag_submenu:
            self.add_b_flag_submenu.setTitle(tr('menu_add_b_flag_submenu', lang))
        if hasattr(self, 'add_b_flag_action') and self.add_b_flag_action:
            self.add_b_flag_action.setText(tr('menu_add_b_flag', lang))
        if hasattr(self, 'add_b_flag_on_update_action') and self.add_b_flag_on_update_action:
            self.add_b_flag_on_update_action.setText(tr('menu_add_b_flag_on_update', lang))
        if hasattr(self, 'run_test_action') and self.run_test_action:
            self.run_test_action.setText(tr('menu_run_test', lang))
        if self.exit_action:
            self.exit_action.setText(tr('menu_exit', lang))
        
        if self.settings_menu:
            self.settings_menu.setTitle(tr('menu_settings', lang))
        if self.language_menu:
            self.language_menu.setTitle(tr('menu_change_language', lang))
        if self.show_tray_action:
            self.show_tray_action.setText(tr('settings_show_tray', lang))
        if self.close_winws_action:
            self.close_winws_action.setText(tr('settings_close_winws', lang))
        if self.start_minimized_action:
            self.start_minimized_action.setText(tr('settings_start_minimized', lang))
        if self.auto_start_action:
            self.auto_start_action.setText(tr('settings_auto_start', lang))
        if hasattr(self, 'autostart_action') and self.autostart_action:
            self.autostart_action.setText(tr('settings_autostart_windows', lang))
        
        if self.update_menu:
            self.update_menu.setTitle(tr('menu_update', lang))
        if self.check_updates_action:
            self.check_updates_action.setText(tr('update_check_zapret', lang))
        if self.manual_update_action:
            self.manual_update_action.setText(tr('update_manual', lang))
        if hasattr(self, 'remove_check_updates_action') and self.remove_check_updates_action:
            self.remove_check_updates_action.setText(tr('update_remove_check_updates', lang))
        
        # Обновляем меню "Справка"
        if hasattr(self, 'help_menu') and self.help_menu:
            self.help_menu.setTitle(tr('menu_help', lang))
        if hasattr(self, 'open_github_action') and self.open_github_action:
            self.open_github_action.setText(tr('help_open_github', lang))
        if hasattr(self, 'open_help_action') and self.open_help_action:
            self.open_help_action.setText(tr('help_open_help', lang))
        
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
            else:
                # Если не удалось выключить, ставим галочку обратно
                self.autostart_action.setChecked(True)
                lang = self.settings.get('language', 'ru')
                msg = QMessageBox(self)
                msg.setWindowTitle('Ошибка')
                msg.setText('Не удалось выключить автозапуск')
                msg.setIcon(QMessageBox.Icon.Warning)
                msg.exec()
    
    def minimize_to_tray(self):
        """Сворачивает окно в трей"""
        self.hide()
        self.tray.show_message('Окно свернуто в трей', 
                              'Нажмите на иконку в трее, чтобы открыть окно')
    
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
        progress_dialog.setLabelText('Проверка обновлений...')
        progress_dialog.setRange(0, 0)  # Неопределенный прогресс
        progress_dialog.setCancelButton(None)
        progress_dialog.show()
        QApplication.processEvents()
        
        # Проверяем обновления
        update_info = self.zapret_updater.check_for_updates()
        progress_dialog.close()
        
        if 'error' in update_info:
            msg = QMessageBox(self)
            msg.setWindowTitle('Ошибка')
            msg.setText(update_info['error'])
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.exec()
            return
        
        if not update_info['has_update']:
            msg = QMessageBox(self)
            msg.setWindowTitle(tr('msg_check_updates_title', lang))
            msg.setText('Обновления не найдены')
            msg.setInformativeText(f'Установлена актуальная версия: {update_info["current_version"]}')
            msg.setIcon(QMessageBox.Icon.Information)
            msg.exec()
            return
        
        # Есть обновление - спрашиваем пользователя
        reply = QMessageBox.question(
            self,
            'Обновление доступно',
            f'Найдена новая версия: {update_info["latest_version"]}\n'
            f'Текущая версия: {update_info["current_version"]}\n\n'
            f'Хотите обновить стратегии zapret?',
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
            msg.setWindowTitle('Ошибка')
            msg.setText('URL для скачивания не найден')
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
            stop_dialog.setWindowTitle('Остановка winws')
            stop_dialog.setText('Обнаружен запущенный процесс winws.exe')
            stop_dialog.setInformativeText('Необходимо остановить процесс перед обновлением. Остановить сейчас?')
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
        progress_dialog.setWindowTitle('Обновление')
        progress_dialog.setLabelText('Скачивание обновления...')
        progress_dialog.setRange(0, 100)
        progress_dialog.setCancelButton(None)
        progress_dialog.show()
        QApplication.processEvents()
        
        def update_progress(value):
            progress_dialog.setValue(int(value))
            QApplication.processEvents()
        
        try:
            # Скачиваем обновление
            progress_dialog.setLabelText('Скачивание обновления...')
            zip_path = self.zapret_updater.download_update(
                update_info['download_url'],
                progress_callback=update_progress
            )
            
            # Устанавливаем обновление
            progress_dialog.setLabelText('Установка обновления...')
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
            
            # Обновляем меню стратегий
            if hasattr(self, 'strategies_menu'):
                self.update_strategies_menu(self.strategies_menu)
            
            # Если включена настройка "Добавлять /B при обновлении", добавляем /B флаг
            if self.settings.get('add_b_flag_on_update', False):
                self.add_b_flag_to_all_strategies(silent=True)
            
            # Если включена настройка "Удалять проверку обновлений", удаляем строку check_updates
            if self.settings.get('remove_check_updates', False):
                self.remove_check_updates_from_all_strategies(silent=True)
            
            msg = QMessageBox(self)
            msg.setWindowTitle('Обновление завершено')
            msg.setText(f'Стратегии zapret успешно обновлены до версии {update_info["latest_version"]}')
            msg.setIcon(QMessageBox.Icon.Information)
            msg.exec()
            
        except Exception as e:
            progress_dialog.close()
            msg = QMessageBox(self)
            msg.setWindowTitle('Ошибка обновления')
            msg.setText(f'Ошибка при обновлении: {str(e)}')
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
                'Остановка winws',
                'Обнаружен запущенный процесс winws.exe\n'
                'Необходимо остановить процесс перед обновлением. Остановить сейчас?',
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
        file_dialog.setWindowTitle('Выберите архив для обновления')
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
        progress_dialog.setWindowTitle('Обновление стратегий')
        progress_dialog.setLabelText('Распаковка архива...')
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
            
            # Обновляем меню стратегий
            if hasattr(self, 'strategies_menu'):
                self.update_strategies_menu(self.strategies_menu)
            
            # Если включена настройка "Добавлять /B при обновлении", добавляем /B флаг
            if self.settings.get('add_b_flag_on_update', False):
                self.add_b_flag_to_all_strategies(silent=True)
            
            # Если включена настройка "Удалять проверку обновлений", удаляем строку check_updates
            if self.settings.get('remove_check_updates', False):
                self.remove_check_updates_from_all_strategies(silent=True)
            
            msg = QMessageBox(self)
            msg.setWindowTitle('Обновление завершено')
            msg.setText('Стратегии успешно обновлены из архива')
            msg.setIcon(QMessageBox.Icon.Information)
            msg.exec()
            
        except Exception as e:
            progress_dialog.close()
            msg = QMessageBox(self)
            msg.setWindowTitle('Ошибка обновления')
            msg.setText(f'Ошибка при обновлении: {str(e)}')
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
    
    def open_help(self):
        """Открывает справку программы (PDF файл)"""
        lang = self.settings.get('language', 'ru')
        base_path = get_base_path()
        help_file = os.path.join(base_path, 'ref', 'metrosdpi.pdf')
        
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
        """Автоматически запускает последнюю сохраненную стратегию при запуске программы"""
        last_strategy = self.settings.get('last_strategy', '')
        if not last_strategy:
            return
        
        # Проверяем, что стратегия существует в ComboBox
        index = self.combo_box.findText(last_strategy)
        if index >= 0:
            # Выбираем стратегию в ComboBox
            self.combo_box.setCurrentIndex(index)
            # Запускаем стратегию, если она еще не запущена
            if not self.is_running:
                self.start_bat_file()
    
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
            self.start_bat_file()
        else:
            # Останавливаем процесс winws.exe
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
            self.action_button.setText(tr('button_stop', lang))
            self.combo_box.setEnabled(False)  # Блокируем ComboBox
            
            # Сохраняем выбранную стратегию
            self.config.set_setting('last_strategy', current_strategy)
            self.settings['last_strategy'] = current_strategy
            
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
        
        try:
            # Ищем и завершаем все процессы winws.exe
            killed = False
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] and proc.info['name'].lower() == 'winws.exe':
                        proc.terminate()
                        killed = True
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # Если не удалось завершить через terminate, пробуем kill
            if not killed:
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        if proc.info['name'] and proc.info['name'].lower() == 'winws.exe':
                            proc.kill()
                            killed = True
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        pass
            
            # Обновляем состояние только если не silent режим
            if not silent:
                self.is_running = False
                self.action_button.setText(tr('button_start', lang))
                self.combo_box.setEnabled(True)  # Разблокируем ComboBox
                self.bat_process = None
            
        except Exception as e:
            if not silent:
                msg = QMessageBox(self)
                msg.setWindowTitle('Ошибка')
                msg.setText(f'Ошибка при остановке процесса: {str(e)}')
                msg.setIcon(QMessageBox.Icon.Critical)
                msg.exec()
    
    def check_winws_process(self):
        """Проверяет наличие процесса winws.exe и обновляет состояние кнопки"""
        lang = self.settings.get('language', 'ru')
        
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
    
    def closeEvent(self, event):
        """Обработка закрытия окна - скрывает в трей"""
        lang = self.settings.get('language', 'ru')
        if self.settings.get('show_in_tray', True):
            event.ignore()
            self.hide()
            self.tray.update_menu()  # Обновляем меню трея
            self.tray.show_message(tr('msg_app_minimized_to_tray', lang), 
                                  tr('msg_app_minimized_to_tray_info', lang))
        else:
            # Если трей отключен, закрываем приложение
            self.quit_application()

