from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from translator import tr
from path_utils import get_base_path, get_winws_path
import os
import subprocess
import threading
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed


class TestWindow(QDialog):
    def __init__(self, parent=None, winws_folder=None):
        super().__init__(parent)
        # Преобразуем путь к winws в абсолютный
        if winws_folder is None:
            # Если путь не передан, используем стандартный путь
            self.winws_folder = get_winws_path()
        elif not os.path.isabs(winws_folder):
            # Если путь относительный, используем базовую директорию приложения
            base_dir = get_base_path()
            self.winws_folder = os.path.join(base_dir, winws_folder)
        else:
            self.winws_folder = winws_folder
        self.test_results = []
        self.is_running = False
        self.strategy_stats = {}  # Статистика по стратегиям: {strategy_name: {'http_ok': 0, 'tls_ok': 0, 'ping_ok': 0, 'total': 0}}
        # Получаем язык из родительского окна или используем русский по умолчанию
        self.language = 'ru'
        if parent:
            if hasattr(parent, 'settings'):
                self.language = parent.settings.get('language', 'ru')
            elif hasattr(parent, 'config'):
                # Если у родителя есть config, загружаем настройки
                try:
                    settings = parent.config.load_settings()
                    self.language = settings.get('language', 'ru')
                except:
                    pass
        self.init_ui()
        self.retranslate_ui()
    
    def init_ui(self):
        self.setMinimumSize(900, 600)
        
        layout = QVBoxLayout()
        
        # Кнопки управления, ComboBox и Checkbox в одной линии
        button_layout = QHBoxLayout()
        self.action_button = QPushButton()
        self.action_button.clicked.connect(self.toggle_tests)
        button_layout.addWidget(self.action_button)
        
        # ComboBox для выбора стратегии
        self.strategy_label = QLabel()
        self.strategy_combo = QComboBox()
        self.strategy_combo.setMinimumWidth(200)
        self.load_strategies_to_combo()
        button_layout.addWidget(self.strategy_label)
        button_layout.addWidget(self.strategy_combo)
        
        # Checkbox для автоскролла
        self.auto_scroll_checkbox = QCheckBox()
        self.auto_scroll_checkbox.setChecked(True)  # По умолчанию включен
        self.auto_scroll_checkbox.stateChanged.connect(self.on_auto_scroll_changed)
        button_layout.addWidget(self.auto_scroll_checkbox)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Вкладки
        self.tabs = QTabWidget()
        
        # Вкладка 1: Результаты тестирования
        results_tab = QWidget()
        results_layout = QVBoxLayout()
        results_tab.setLayout(results_layout)
        
        # Таблица результатов
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.horizontalHeader().setStretchLastSection(True)
        # Растягиваем все колонки на всю ширину таблицы
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # Убираем нумерацию строк
        self.table.verticalHeader().setVisible(False)
        results_layout.addWidget(self.table)
        
        self.results_tab = results_tab
        self.tabs.addTab(results_tab, '')
        
        # Вкладка 2: Лучшие стратегии
        best_tab = QWidget()
        best_layout = QVBoxLayout()
        best_tab.setLayout(best_layout)
        
        # Таблица лучших стратегий
        self.best_table = QTableWidget()
        self.best_table.setColumnCount(4)  # Убрали колонку "Место"
        self.best_table.horizontalHeader().setStretchLastSection(True)
        self.best_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.best_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.best_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # Убираем нумерацию строк
        self.best_table.verticalHeader().setVisible(False)
        best_layout.addWidget(self.best_table)
        
        self.best_tab = best_tab
        self.tabs.addTab(best_tab, '')
        
        # Вкладка 3: Targets (редактирование targets.txt)
        targets_tab = QWidget()
        targets_layout = QVBoxLayout()
        targets_tab.setLayout(targets_layout)
        
        # Кнопки для управления файлом
        targets_buttons_layout = QHBoxLayout()
        self.targets_save_button = QPushButton()
        self.targets_save_button.clicked.connect(self.save_targets_file)
        self.targets_reload_button = QPushButton()
        self.targets_reload_button.clicked.connect(self.reload_targets_file)
        targets_buttons_layout.addWidget(self.targets_reload_button)
        targets_buttons_layout.addStretch()
        targets_buttons_layout.addWidget(self.targets_save_button)
        targets_layout.addLayout(targets_buttons_layout)
        
        # Текстовый редактор для targets.txt
        self.targets_editor = QTextEdit()
        self.targets_editor.setFont(QFont("Consolas", 10))
        self.targets_editor.textChanged.connect(self.on_targets_text_changed)
        targets_layout.addWidget(self.targets_editor)
        
        self.targets_tab = targets_tab
        self.tabs.addTab(targets_tab, '')
        
        # Инициализируем путь к файлу targets.txt
        self.targets_file_path = os.path.join(self.winws_folder, 'utils', 'targets.txt')
        
        # Отслеживание изменений файла извне
        self.file_watcher = QFileSystemWatcher()
        if os.path.exists(self.targets_file_path):
            self.file_watcher.addPath(self.targets_file_path)
        self.file_watcher.fileChanged.connect(self.on_targets_file_changed_externally)
        
        # Флаг для отслеживания изменений в редакторе
        self.targets_text_changed = False
        
        # Загружаем файл при инициализации
        self.load_targets_file()
        
        layout.addWidget(self.tabs)
        
        # Словарь для хранения статистики по стратегиям
        self.strategy_stats = {}
        
        # Инициализируем список целей для тестирования
        self.init_targets()
        
        # Прогресс бар
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        
        # Статус
        self.status_label = QLabel()
        layout.addWidget(self.status_label)
        
        # Кнопки внизу
        bottom_layout = QHBoxLayout()
        self.close_button = QPushButton()
        self.close_button.clicked.connect(self.close)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.close_button)
        layout.addLayout(bottom_layout)
        
        self.setLayout(layout)
    
    def retranslate_ui(self):
        """Обновляет все тексты интерфейса в соответствии с выбранным языком"""
        # Обновляем язык из родительского окна, если оно доступно
        parent = self.parent()
        if parent:
            if hasattr(parent, 'settings'):
                self.language = parent.settings.get('language', 'ru')
            elif hasattr(parent, 'config'):
                # Если у родителя есть config, загружаем настройки
                try:
                    settings = parent.config.load_settings()
                    self.language = settings.get('language', 'ru')
                except:
                    pass
        
        self.setWindowTitle(tr('test_window_title', self.language))
        # Обновляем текст кнопки в зависимости от состояния
        if self.is_running:
            self.action_button.setText(tr('test_stop_button', self.language))
        else:
            self.action_button.setText(tr('test_start_button', self.language))
        self.close_button.setText(tr('test_close_button', self.language))
        self.strategy_label.setText(tr('test_strategy_label', self.language))
        self.status_label.setText(tr('test_status_ready', self.language))
        
        # Обновляем заголовки таблиц
        self.table.setHorizontalHeaderLabels([
            tr('table_col_strategy', self.language),
            tr('table_col_target', self.language),
            tr('table_col_http_tls', self.language),
            tr('table_col_ping', self.language)
        ])
        
        self.best_table.setHorizontalHeaderLabels([
            tr('best_strategies_col_strategy', self.language),
            tr('best_strategies_col_http_ok', self.language),
            tr('best_strategies_col_tls_ok', self.language),
            tr('best_strategies_col_ping_ok', self.language)
        ])
        
        # Обновляем названия вкладок
        self.tabs.setTabText(0, tr('tab_test_results', self.language))
        self.tabs.setTabText(1, tr('tab_best_strategies', self.language))
        if self.tabs.count() > 2:
            self.tabs.setTabText(2, tr('tab_targets', self.language))
        
        # Обновляем кнопки вкладки Targets
        if hasattr(self, 'targets_save_button'):
            self.targets_save_button.setText(tr('targets_save_button', self.language))
        if hasattr(self, 'targets_reload_button'):
            self.targets_reload_button.setText(tr('targets_reload_button', self.language))
        
        # Обновляем checkbox автоскролла
        if hasattr(self, 'auto_scroll_checkbox'):
            self.auto_scroll_checkbox.setText(tr('test_auto_scroll', self.language))
        
        # Обновляем ComboBox
        self.load_strategies_to_combo()
    
    def load_strategies_to_combo(self):
        """Загружает список стратегий в ComboBox"""
        current_index = self.strategy_combo.currentIndex()
        current_data = self.strategy_combo.itemData(current_index) if current_index >= 0 else None
        
        self.strategy_combo.clear()
        self.strategy_combo.addItem(tr('test_all_strategies', self.language))
        self.strategy_combo.insertSeparator(1)
        
        # Получаем список .bat файлов
        if os.path.exists(self.winws_folder):
            bat_files = []
            for file in os.listdir(self.winws_folder):
                if file.endswith('.bat') and not file.startswith('service'):
                    bat_files.append(file)
            
            # Сортируем и добавляем в ComboBox
            bat_files.sort()
            for bat_file in bat_files:
                strategy_name = os.path.splitext(bat_file)[0]
                self.strategy_combo.addItem(strategy_name, bat_file)
        
        # Восстанавливаем выбранный элемент, если он был
        if current_data:
            for i in range(self.strategy_combo.count()):
                if self.strategy_combo.itemData(i) == current_data:
                    self.strategy_combo.setCurrentIndex(i)
                    break
    
    def init_targets(self):
        """Инициализирует список целей для тестирования"""
        # Загружаем цели из файла targets.txt, если он существует
        targets_file = os.path.join(self.winws_folder, 'utils', 'targets.txt')
        self.targets = []
        
        if os.path.exists(targets_file):
            try:
                with open(targets_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and '=' in line:
                            match = re.match(r'^\s*(\w+(?:\s+\w+)*)\s*=\s*"(.+)"\s*$', line)
                            if match:
                                name = match.group(1)
                                value = match.group(2)
                                if value.startswith('PING:'):
                                    ping_target = value.replace('PING:', '').strip()
                                    self.targets.append({
                                        'name': name,
                                        'url': None,
                                        'ping_target': ping_target
                                    })
                                else:
                                    self.targets.append({
                                        'name': name,
                                        'url': value,
                                        'ping_target': None
                                    })
            except Exception:
                pass
        
        # Если файл не найден или пуст, используем значения по умолчанию
        if not self.targets:
            self.targets = [
                {'name': 'Discord Main', 'url': 'https://discord.com', 'ping_target': None},
                {'name': 'Discord Gateway', 'url': 'https://gateway.discord.gg', 'ping_target': None},
                {'name': 'Discord CDN', 'url': 'https://cdn.discordapp.com', 'ping_target': None},
                {'name': 'Discord Updates', 'url': 'https://updates.discord.com', 'ping_target': None},
                {'name': 'YouTube Web', 'url': 'https://www.youtube.com', 'ping_target': None},
                {'name': 'YouTube Short', 'url': 'https://youtu.be', 'ping_target': None},
                {'name': 'YouTube Image', 'url': 'https://i.ytimg.com', 'ping_target': None},
                {'name': 'YouTube Video Redirect', 'url': 'https://redirector.googlevideo.com', 'ping_target': None},
                {'name': 'Google Main', 'url': 'https://www.google.com', 'ping_target': None},
                {'name': 'Google Gstatic', 'url': 'https://www.gstatic.com', 'ping_target': None},
                {'name': 'Cloudflare Web', 'url': 'https://www.cloudflare.com', 'ping_target': None},
                {'name': 'Cloudflare CDN', 'url': 'https://cdnjs.cloudflare.com', 'ping_target': None},
                {'name': 'Cloudflare DNS 1.1.1.1', 'url': None, 'ping_target': '1.1.1.1'},
                {'name': 'Cloudflare DNS 1.0.0.1', 'url': None, 'ping_target': '1.0.0.1'},
                {'name': 'Google DNS 8.8.8.8', 'url': None, 'ping_target': '8.8.8.8'},
                {'name': 'Google DNS 8.8.4.4', 'url': None, 'ping_target': '8.8.4.4'},
                {'name': 'Quad9 DNS 9.9.9.9', 'url': None, 'ping_target': '9.9.9.9'},
            ]
    
    def toggle_tests(self):
        """Переключает состояние тестов: запускает или останавливает"""
        if self.is_running:
            self.stop_tests()
        else:
            self.start_tests()
    
    def start_tests(self):
        if self.is_running:
            return
        
        # Получаем выбранную стратегию из ComboBox
        selected_index = self.strategy_combo.currentIndex()
        
        # Если выбрано "Все стратегии" (индекс 0)
        if selected_index == 0:
            # Получаем список всех .bat файлов
            bat_files = []
            if os.path.exists(self.winws_folder):
                for file in os.listdir(self.winws_folder):
                    if file.endswith('.bat') and not file.startswith('service'):
                        bat_files.append(file)
        else:
            # Получаем выбранный .bat файл
            bat_file = self.strategy_combo.itemData(selected_index)
            if bat_file:
                bat_files = [bat_file]
            else:
                QMessageBox.warning(self, tr('test_error_title', self.language), 
                                     tr('test_error_cannot_determine', self.language))
                return
        
        if not bat_files:
            QMessageBox.warning(self, tr('test_error_title', self.language), 
                             tr('test_error_no_bat_files', self.language))
            return
        
        self.is_running = True
        self.action_button.setText(tr('test_stop_button', self.language))
        # Прогресс = количество .bat файлов * количество целей
        total_tests = len(bat_files) * len(self.targets)
        self.progress.setRange(0, total_tests)
        self.progress.setValue(0)
        
        # Очищаем таблицы перед новым тестом
        self.table.setRowCount(0)
        self.best_table.setRowCount(0)
        self.strategy_stats = {}
        
        # Запускаем тесты в отдельном потоке
        thread = threading.Thread(target=self.run_tests, args=(bat_files,))
        thread.daemon = True
        thread.start()
    
    def stop_tests(self):
        self.is_running = False
        self.action_button.setText(tr('test_start_button', self.language))
        self.status_label.setText(tr('test_status_stopping', self.language))
    
    def run_tests(self, bat_files):
        self.test_results = []
        test_count = 0
        
        for bat_file in bat_files:
            if not self.is_running:
                break
            
            # Обновляем статус
            status_text = f"{tr('test_status_testing', self.language)} {bat_file}"
            QMetaObject.invokeMethod(self, "update_status", Qt.ConnectionType.QueuedConnection, 
                                    Q_ARG(str, status_text))
            
            # Добавляем заголовок стратегии в таблицу
            QMetaObject.invokeMethod(self, "add_strategy_header", Qt.ConnectionType.QueuedConnection,
                                    Q_ARG(str, bat_file))
            
            # Останавливаем winws если запущен
            self.stop_winws()
            
            # Запускаем .bat файл
            bat_path = os.path.join(self.winws_folder, bat_file)
            process = subprocess.Popen(
                ['cmd.exe', '/c', bat_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.winws_folder,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # Ждем инициализации
            import time
            time.sleep(5)
            
            # Инициализируем статистику для этой стратегии
            strategy_name = os.path.splitext(bat_file)[0]
            # Используем прямой доступ к словарю, так как мы в отдельном потоке
            # Но нужно передать данные через сигнал для обновления UI
            strategy_stats = {
                'http_ok': 0,
                'tls12_ok': 0,
                'tls13_ok': 0,
                'ping_ok': 0,
                'total_targets': 0
            }
            
            # Сначала выполняем HTTP/TLS тесты для всех целей последовательно
            results = {}
            for target in self.targets:
                if not self.is_running:
                    break
                
                # Выполняем только HTTP/TLS тесты (без ping)
                result = self.test_target_http_tls(target)
                results[target['name']] = {
                    'target': target,
                    'result': result
                }
                
                # Обновляем статистику HTTP/TLS
                strategy_stats['total_targets'] += 1
                if result.get('http') == 'OK':
                    strategy_stats['http_ok'] += 1
                if result.get('tls12') == 'OK':
                    strategy_stats['tls12_ok'] += 1
                if result.get('tls13') == 'OK':
                    strategy_stats['tls13_ok'] += 1
                
                # Добавляем результат в таблицу (без ping пока)
                QMetaObject.invokeMethod(self, "add_result_to_table", Qt.ConnectionType.QueuedConnection,
                                        Q_ARG(str, target['name']), Q_ARG(dict, result))
                
                test_count += 1
                # Обновляем прогресс
                QMetaObject.invokeMethod(self, "update_progress", Qt.ConnectionType.QueuedConnection,
                                        Q_ARG(int, test_count))
            
            # Теперь выполняем все ping-тесты параллельно
            if self.is_running:
                ping_results = self.test_targets_ping_parallel(self.targets)
                
                # Обновляем результаты с ping-данными и сразу обновляем таблицу
                for target_name, ping_result in ping_results.items():
                    if target_name in results:
                        results[target_name]['result']['ping'] = ping_result
                        
                        # Обновляем статистику ping
                        ping_val = ping_result
                        if ping_val != 'N/A' and ping_val != 'ERROR' and ping_val != 'Timeout' and 'ms' in str(ping_val):
                            strategy_stats['ping_ok'] += 1
                        
                        # Немедленно обновляем строку в таблице с ping-результатом
                        QMetaObject.invokeMethod(self, "update_result_ping", Qt.ConnectionType.QueuedConnection,
                                                Q_ARG(str, target_name), Q_ARG(str, ping_result))
            
            # Обновляем статистику стратегии в главном потоке
            QMetaObject.invokeMethod(self, "update_strategy_stats", Qt.ConnectionType.QueuedConnection,
                                    Q_ARG(str, strategy_name),
                                    Q_ARG(int, strategy_stats['http_ok']),
                                    Q_ARG(int, strategy_stats['tls12_ok']),
                                    Q_ARG(int, strategy_stats['tls13_ok']),
                                    Q_ARG(int, strategy_stats['ping_ok']),
                                    Q_ARG(int, strategy_stats['total_targets']))
            
            # Обновляем таблицу лучших стратегий после тестирования стратегии
            QMetaObject.invokeMethod(self, "update_best_strategies", Qt.ConnectionType.QueuedConnection)
            
            # Останавливаем winws после тестирования всех целей для этого .bat файла
            self.stop_winws()
            
            # Добавляем пустую строку-разделитель между .bat файлами
            QMetaObject.invokeMethod(self, "add_separator", Qt.ConnectionType.QueuedConnection)
        
        # Завершение
        QMetaObject.invokeMethod(self, "tests_finished", Qt.ConnectionType.QueuedConnection)
    
    def test_target_http_tls(self, target):
        """Тестирует HTTP/TLS для одной цели (без ping)"""
        result = {
            'http': 'N/A',
            'tls12': 'N/A',
            'tls13': 'N/A',
            'ping': 'N/A'  # Будет заполнено позже
        }
        
        try:
            # Если это URL, тестируем HTTP/TLS
            if target.get('url'):
                url = target['url']
                test_configs = [
                    ('http', ['--http1.1']),
                    ('tls12', ['--tlsv1.2', '--tls-max', '1.2']),
                    ('tls13', ['--tlsv1.3', '--tls-max', '1.3'])
                ]
                
                for test_name, args in test_configs:
                    try:
                        curl_args = ['curl.exe', '-I', '-s', '-m', '5', '-o', 'NUL'] + args + [url]
                        curl_process = subprocess.run(
                            curl_args,
                            capture_output=True,
                            timeout=10,
                            encoding='utf-8',
                            errors='replace',
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                        
                        output = curl_process.stdout if isinstance(curl_process.stdout, str) else curl_process.stdout.decode('utf-8', errors='replace')
                        stderr = curl_process.stderr if isinstance(curl_process.stderr, str) else curl_process.stderr.decode('utf-8', errors='replace')
                        combined = output + stderr
                        
                        # Проверяем на unsupported
                        if (curl_process.returncode == 35 or 
                            'not supported' in combined.lower() or 
                            'unsupported' in combined.lower() or
                            'protocol' in combined.lower() and 'not' in combined.lower()):
                            result[test_name] = 'UNSUP'
                        elif curl_process.returncode == 0:
                            result[test_name] = 'OK'
                        else:
                            result[test_name] = 'ERROR'
                    except Exception:
                        result[test_name] = 'ERROR'
        except Exception:
            pass
        
        return result
    
    def test_target_ping(self, target):
        """Тестирует ping для одной цели"""
        ping_target = target.get('ping_target')
        if not ping_target and target.get('url'):
            # Для URL целей используем хост из URL для ping
            try:
                from urllib.parse import urlparse
                parsed = urlparse(target['url'])
                ping_target = parsed.hostname
                # Если hostname не определен, пробуем извлечь из URL напрямую
                if not ping_target:
                    url = target['url']
                    # Убираем протокол
                    if '://' in url:
                        url = url.split('://')[1]
                    # Берем первую часть до / или :
                    ping_target = url.split('/')[0].split(':')[0]
            except Exception:
                ping_target = None
        
        if not ping_target:
            return 'N/A'
        
        # Используем cp866 для Windows команд (ping выводит в cp866 на русской Windows)
        # Или cp1251 для английской Windows
        try:
            ping_process = subprocess.run(
                ['ping', '-n', '3', ping_target],
                capture_output=True,
                timeout=10,
                encoding='cp866',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except Exception:
            # В случае ошибки пробуем альтернативную кодировку
            try:
                ping_process = subprocess.run(
                    ['ping', '-n', '3', ping_target],
                    capture_output=True,
                    timeout=10,
                    encoding='cp1251',
                    errors='replace',
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            except Exception:
                return 'ERROR'
        
        if ping_process.returncode == 0:
            # Парсим среднее время
            try:
                output = ping_process.stdout if isinstance(ping_process.stdout, str) else ping_process.stdout.decode('cp866', errors='replace')
            except:
                try:
                    output = ping_process.stdout if isinstance(ping_process.stdout, str) else ping_process.stdout.decode('cp1251', errors='replace')
                except:
                    return 'OK'
            
            # Ищем среднее время в разных форматах (русский и английский)
            match = (
                re.search(r'Среднее\s*=\s*(\d+)', output, re.IGNORECASE) or
                re.search(r'Average\s*=\s*(\d+)', output, re.IGNORECASE) or
                re.search(r'Среднее\s*=\s*(\d+)\s*мс', output, re.IGNORECASE) or
                re.search(r'Average\s*=\s*(\d+)\s*ms', output, re.IGNORECASE) or
                re.search(r'(?:Среднее|Average)\s*=\s*(\d+)', output, re.IGNORECASE)
            )
            if match:
                return f"{match.group(1)} ms"
            else:
                # Если не нашли среднее, но ping успешен, ищем любое время ответа
                time_match = (
                    re.search(r'время[<>=]\s*(\d+)\s*мс', output, re.IGNORECASE) or
                    re.search(r'time[<>=]\s*(\d+)\s*ms', output, re.IGNORECASE) or
                    re.search(r'время[<>=]\s*(\d+)', output, re.IGNORECASE) or
                    re.search(r'time[<>=]\s*(\d+)', output, re.IGNORECASE) or
                    re.search(r'Минимальное\s*=\s*(\d+)', output, re.IGNORECASE) or
                    re.search(r'Minimum\s*=\s*(\d+)', output, re.IGNORECASE) or
                    re.search(r'Максимальное\s*=\s*(\d+)', output, re.IGNORECASE) or
                    re.search(r'Maximum\s*=\s*(\d+)', output, re.IGNORECASE)
                )
                if time_match:
                    return f"{time_match.group(1)} ms"
                else:
                    return 'OK'
        else:
            return 'Timeout'
    
    def test_targets_ping_parallel(self, targets):
        """Выполняет ping для всех таргетов параллельно"""
        ping_results = {}
        
        # Фильтруем таргеты, для которых нужен ping
        targets_to_ping = []
        for target in targets:
            ping_target = target.get('ping_target')
            if not ping_target and target.get('url'):
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(target['url'])
                    ping_target = parsed.hostname
                    if not ping_target:
                        url = target['url']
                        if '://' in url:
                            url = url.split('://')[1]
                        ping_target = url.split('/')[0].split(':')[0]
                except Exception:
                    ping_target = None
            
            if ping_target:
                targets_to_ping.append((target['name'], target))
            else:
                # Если у таргета нет ping_target, добавляем N/A
                ping_results[target['name']] = 'N/A'
        
        if not targets_to_ping:
            return ping_results
        
        # Выполняем ping параллельно
        max_workers = min(len(targets_to_ping), 20)  # Максимум 20 потоков
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Создаем словарь future -> target_name для отслеживания
            future_to_target = {}
            for target_name, target in targets_to_ping:
                if not self.is_running:
                    break
                future = executor.submit(self.test_target_ping, target)
                future_to_target[future] = target_name
            
            # Собираем результаты по мере их готовности и сразу обновляем UI
            for future in as_completed(future_to_target):
                if not self.is_running:
                    break
                target_name = future_to_target[future]
                try:
                    ping_result = future.result()
                    ping_results[target_name] = ping_result
                except Exception:
                    ping_results[target_name] = 'ERROR'
        
        return ping_results
    
    def stop_winws(self):
        """Останавливает процесс winws.exe"""
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] and proc.info['name'].lower() == 'winws.exe':
                    proc.kill()
        except Exception:
            pass
    
    @pyqtSlot(str)
    def update_status(self, text):
        self.status_label.setText(text)
    
    def on_auto_scroll_changed(self, state):
        """Обработчик изменения состояния checkbox автоскролла"""
        # state: 0 = unchecked, 2 = checked
        pass  # Просто сохраняем состояние, проверка будет в методе scroll_if_enabled
    
    def scroll_if_enabled(self):
        """Выполняет скролл вниз только если автоскролл включен"""
        if self.auto_scroll_checkbox.isChecked():
            self.table.scrollToBottom()
    
    @pyqtSlot(str)
    def add_strategy_header(self, bat_file):
        """Добавляет заголовок стратегии в таблицу"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Заголовок стратегии (без расширения .bat)
        strategy_name = os.path.splitext(bat_file)[0]
        
        # Создаем элемент для названия стратегии в первой колонке
        header_item = QTableWidgetItem(strategy_name)
        font = header_item.font()
        font.setBold(True)
        header_item.setFont(font)
        self.table.setItem(row, 0, header_item)
        
        # Остальные колонки пустые для заголовка
        self.table.setItem(row, 1, QTableWidgetItem(''))
        self.table.setItem(row, 2, QTableWidgetItem(''))
        self.table.setItem(row, 3, QTableWidgetItem(''))
        
        # Автоскролл вниз (если включен)
        self.scroll_if_enabled()
    
    @pyqtSlot(str, dict)
    def add_result_to_table(self, target_name, result):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Форматируем имя цели (убираем пробелы для компактности, как в примере)
        # Пример: "Discord Gateway" -> "DiscordGateway", "Cloudflare DNS 1.1.1.1" -> "CloudflareDNS1111"
        display_name = target_name.replace(' ', '').replace('.', '')
        
        # Добавляем отступ для подчиненности под стратегией
        display_name = '  ' + display_name
        
        # Первая колонка пустая (название стратегии уже в заголовке)
        self.table.setItem(row, 0, QTableWidgetItem(''))
        # Вторая колонка - название цели
        self.table.setItem(row, 1, QTableWidgetItem(display_name))
        
        # Форматируем результаты: HTTP/TLS в отдельную колонку, Ping в отдельную
        http_val = result.get('http', 'N/A')
        tls12_val = result.get('tls12', 'N/A')
        tls13_val = result.get('tls13', 'N/A')
        ping_val = result.get('ping', 'N/A')
        
        # Формируем строку HTTP/TLS результатов
        http_tls_parts = []
        if http_val != 'N/A' or tls12_val != 'N/A' or tls13_val != 'N/A':
            # Форматируем с правильным выравниванием (как в примере: HTTP:OK    TLS1.2:OK    TLS1.3:OK)
            http_text = f"HTTP:{http_val}"
            tls12_text = f"TLS1.2:{tls12_val}"
            tls13_text = f"TLS1.3:{tls13_val}"
            # Добавляем пробелы для выравнивания
            http_tls_parts.append(f"{http_text:<12} {tls12_text:<12} {tls13_text:<12}")
        
        http_tls_text = ' '.join(http_tls_parts) if http_tls_parts else 'N/A'
        http_tls_item = QTableWidgetItem(http_tls_text)
        self.table.setItem(row, 2, http_tls_item)
        
        # Формируем строку Ping результатов
        ping_text = ping_val if ping_val != 'N/A' else 'N/A'
        if ping_text != 'N/A' and ping_text:
            ping_text = f"{ping_text}"
        ping_item = QTableWidgetItem(ping_text)
        self.table.setItem(row, 3, ping_item)
        
        # Цветовая индикация для HTTP/TLS колонки
        item = self.table.item(row, 2)
        if item:
            text = item.text()
            # Определяем общий статус по результатам
            has_error = 'ERROR' in text
            has_ok = 'OK' in text
            has_unsup = 'UNSUP' in text
            
            if has_error:
                item.setForeground(QColor(255, 0, 0))  # Красный
            elif has_ok and not has_error:
                item.setForeground(QColor(0, 128, 0))  # Зеленый
            elif has_unsup:
                item.setForeground(QColor(255, 165, 0))  # Оранжевый
            else:
                item.setForeground(QColor(128, 128, 128))  # Серый
        
        # Цветовая индикация для Ping колонки
        ping_item = self.table.item(row, 3)
        if ping_item:
            ping_text = ping_item.text()
            if ping_text == 'N/A' or ping_text == 'Timeout' or ping_text == 'ERROR':
                ping_item.setForeground(QColor(255, 0, 0))  # Красный
            elif 'ms' in ping_text:
                ping_item.setForeground(QColor(0, 128, 0))  # Зеленый
            else:
                ping_item.setForeground(QColor(128, 128, 128))  # Серый
        
        # Автоскролл вниз при добавлении новой строки (если включен)
        self.scroll_if_enabled()
    
    @pyqtSlot(str, str)
    def update_result_ping(self, target_name, ping_result):
        """Обновляет ping результат в таблице для указанного таргета"""
        # Форматируем имя цели так же, как в add_result_to_table
        display_name = target_name.replace(' ', '').replace('.', '')
        display_name = '  ' + display_name
        
        # Ищем все строки с этим таргетом (может быть несколько, если тестируется несколько стратегий)
        found = False
        for row in range(self.table.rowCount()):
            target_item = self.table.item(row, 1)  # Колонка Target
            if target_item:
                item_text = target_item.text().strip()
                # Сравниваем без учета отступа (может быть разное количество пробелов)
                if item_text == display_name.strip() or item_text == target_name.replace(' ', '').replace('.', ''):
                    # Обновляем колонку Ping (индекс 3)
                    ping_item = QTableWidgetItem(ping_result)
                    # Применяем цветовую индикацию для ping
                    if ping_result != 'N/A' and ping_result != 'ERROR' and ping_result != 'Timeout' and 'ms' in str(ping_result):
                        ping_item.setForeground(QColor(0, 128, 0))  # Зеленый для успешного ping
                    elif ping_result == 'ERROR' or ping_result == 'Timeout':
                        ping_item.setForeground(QColor(255, 0, 0))  # Красный для ошибки
                    else:
                        ping_item.setForeground(QColor(128, 128, 128))  # Серый
                    self.table.setItem(row, 3, ping_item)
                    found = True
                    # Принудительно обновляем таблицу
                    self.table.viewport().update()
                    # Автоскролл вниз (если включен)
                    self.scroll_if_enabled()
        
        # Если не нашли по отформатированному имени, пробуем найти по оригинальному имени
        if not found:
            for row in range(self.table.rowCount()):
                target_item = self.table.item(row, 1)  # Колонка Target
                if target_item:
                    item_text = target_item.text().strip()
                    # Пробуем найти по частичному совпадению (без учета форматирования)
                    if target_name.replace(' ', '').replace('.', '') in item_text.replace(' ', '').replace('.', ''):
                        ping_item = QTableWidgetItem(ping_result)
                        if ping_result != 'N/A' and ping_result != 'ERROR' and ping_result != 'Timeout' and 'ms' in str(ping_result):
                            ping_item.setForeground(QColor(0, 128, 0))
                        elif ping_result == 'ERROR' or ping_result == 'Timeout':
                            ping_item.setForeground(QColor(255, 0, 0))
                        else:
                            ping_item.setForeground(QColor(128, 128, 128))
                        self.table.setItem(row, 3, ping_item)
                        # Принудительно обновляем таблицу и обрабатываем события
                        self.table.viewport().update()
                        self.scroll_if_enabled()
                        QApplication.processEvents()
                        break
    
    @pyqtSlot()
    def add_separator(self):
        """Добавляет пустую строку-разделитель между группами тестов разных .bat файлов"""
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(''))
        self.table.setItem(row, 1, QTableWidgetItem(''))
        self.table.setItem(row, 2, QTableWidgetItem(''))
        self.table.setItem(row, 3, QTableWidgetItem(''))
        
        # Автоскролл вниз (если включен)
        self.scroll_if_enabled()
    
    @pyqtSlot(int)
    def update_progress(self, value):
        self.progress.setValue(value)
    
    @pyqtSlot(str, int, int, int, int, int)
    def update_strategy_stats(self, strategy_name, http_ok, tls12_ok, tls13_ok, ping_ok, total_targets):
        """Обновляет статистику стратегии из главного потока"""
        self.strategy_stats[strategy_name] = {
            'http_ok': http_ok,
            'tls12_ok': tls12_ok,
            'tls13_ok': tls13_ok,
            'ping_ok': ping_ok,
            'total_targets': total_targets
        }
    
    @pyqtSlot()
    def update_best_strategies(self):
        """Обновляет таблицу лучших стратегий на основе текущей статистики
        Классифицирует стратегии по качеству работы:
        - Зеленые: наилучшие (рабочие) стратегии (>70% успеха)
        - Желтые: средние стратегии (30-70% успеха)
        - Красные: нерабочие стратегии (<30% успеха)
        """
        # Очищаем таблицу
        self.best_table.setRowCount(0)
        
        # Подготавливаем данные стратегий с расчетом процента успеха
        strategies_data = []
        for strategy_name, stats in self.strategy_stats.items():
            total_targets = stats['total_targets']
            if total_targets == 0:
                continue
            
            # Считаем общее количество успешных тестов
            # HTTP OK + TLS1.2 OK + TLS1.3 OK + Ping OK
            total_tests = total_targets * 4  # HTTP + TLS1.2 + TLS1.3 + Ping для каждого таргета
            total_ok = stats['http_ok'] + stats['tls12_ok'] + stats['tls13_ok'] + stats['ping_ok']
            
            # Рассчитываем процент успеха
            success_percent = (total_ok / total_tests * 100) if total_tests > 0 else 0
            
            strategies_data.append({
                'name': strategy_name,
                'http_ok': stats['http_ok'],
                'tls_ok': stats['tls12_ok'] + stats['tls13_ok'],
                'ping_ok': stats['ping_ok'],
                'total': total_targets,
                'success_percent': success_percent
            })
        
        # Сортируем по проценту успеха (от лучших к худшим)
        strategies_data.sort(key=lambda x: x['success_percent'], reverse=True)
        
        # Добавляем все стратегии в таблицу с цветовой классификацией
        for strategy in strategies_data:
            row = self.best_table.rowCount()
            self.best_table.insertRow(row)
            
            # Название стратегии
            name_item = QTableWidgetItem(strategy['name'])
            self.best_table.setItem(row, 0, name_item)
            
            # HTTP OK
            http_item = QTableWidgetItem(f"{strategy['http_ok']}/{strategy['total']}")
            self.best_table.setItem(row, 1, http_item)
            
            # TLS OK (TLS1.2 + TLS1.3)
            tls_item = QTableWidgetItem(f"{strategy['tls_ok']}/{strategy['total'] * 2}")
            self.best_table.setItem(row, 2, tls_item)
            
            # Ping OK
            ping_item = QTableWidgetItem(f"{strategy['ping_ok']}/{strategy['total']}")
            self.best_table.setItem(row, 3, ping_item)
            
            # Цветовая классификация по проценту успеха
            success_percent = strategy['success_percent']
            if success_percent >= 70:
                # Зеленый - наилучшие (рабочие) стратегии
                color = QColor(0, 200, 0)  # Яркий зеленый
            elif success_percent >= 30:
                # Желтый - средние стратегии
                color = QColor(255, 200, 0)  # Желтый
            else:
                # Красный - нерабочие стратегии
                color = QColor(255, 0, 0)  # Красный
            
            # Применяем цвет ко всем ячейкам строки
            for col in range(4):
                item = self.best_table.item(row, col)
                if item:
                    item.setForeground(color)
        
        # Автоскролл вверх
        self.best_table.scrollToTop()
    
    @pyqtSlot()
    def tests_finished(self):
        self.is_running = False
        self.action_button.setText(tr('test_start_button', self.language))
        self.status_label.setText(tr('test_status_finished', self.language))
        self.progress.setValue(self.progress.maximum())
        
        # Финальное обновление таблицы лучших стратегий
        self.update_best_strategies()
    
    def load_targets_file(self):
        """Загружает содержимое файла targets.txt в редактор"""
        try:
            if os.path.exists(self.targets_file_path):
                with open(self.targets_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Блокируем сигнал textChanged, чтобы не устанавливать флаг изменений
                self.targets_editor.blockSignals(True)
                self.targets_editor.setPlainText(content)
                self.targets_editor.blockSignals(False)
                self.targets_text_changed = False
            else:
                # Если файл не существует, создаем его с базовым содержимым
                default_content = """# targets.txt - endpoint list for zapret.ps1 tests

#

# Format:

#   KeyName = "https://host..."   -> Runs HTTP/TLS checks + ping

#   KeyName = "PING:1.2.3.4"       -> Ping only

#

# Keys must be a single word (letters/digits/underscore), because the

# script parses them as simple identifiers. You can add or remove lines.

### Discord

DiscordMain           = "https://discord.com"

DiscordGateway        = "https://gateway.discord.gg"

DiscordCDN            = "https://cdn.discordapp.com"

DiscordUpdates        = "https://updates.discord.com"

### YouTube

YouTubeWeb            = "https://www.youtube.com"

YouTubeShort          = "https://youtu.be"

YouTubeImage          = "https://i.ytimg.com"

YouTubeVideoRedirect  = "https://redirector.googlevideo.com"

### Google

GoogleMain            = "https://www.google.com"

GoogleGstatic         = "https://www.gstatic.com"

### Cloudflare

CloudflareWeb         = "https://www.cloudflare.com"

CloudflareCDN         = "https://cdnjs.cloudflare.com"

### Public DNS (PING-only)

CloudflareDNS1111     = "PING:1.1.1.1"

CloudflareDNS1001     = "PING:1.0.0.1"

GoogleDNS8888         = "PING:8.8.8.8"

GoogleDNS8844         = "PING:8.8.4.4"

Quad9DNS9999          = "PING:9.9.9.9"
"""
                # Создаем директорию, если её нет
                os.makedirs(os.path.dirname(self.targets_file_path), exist_ok=True)
                with open(self.targets_file_path, 'w', encoding='utf-8') as f:
                    f.write(default_content)
                self.targets_editor.blockSignals(True)
                self.targets_editor.setPlainText(default_content)
                self.targets_editor.blockSignals(False)
                self.targets_text_changed = False
                # Добавляем файл в watcher
                if os.path.exists(self.targets_file_path):
                    self.file_watcher.addPath(self.targets_file_path)
        except Exception as e:
            QMessageBox.warning(self, tr('test_error_title', self.language), 
                              f"{tr('targets_error_loading', self.language)}: {str(e)}")
    
    def save_targets_file(self):
        """Сохраняет содержимое редактора в файл targets.txt"""
        try:
            content = self.targets_editor.toPlainText()
            # Временно отключаем watcher, чтобы не сработало событие изменения файла
            if os.path.exists(self.targets_file_path):
                self.file_watcher.removePath(self.targets_file_path)
            
            # Создаем директорию, если её нет
            os.makedirs(os.path.dirname(self.targets_file_path), exist_ok=True)
            
            with open(self.targets_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Включаем watcher обратно
            if os.path.exists(self.targets_file_path):
                self.file_watcher.addPath(self.targets_file_path)
            
            self.targets_text_changed = False
            
            # Показываем сообщение об успешном сохранении
            QMessageBox.information(self, tr('test_error_title', self.language), 
                                  tr('targets_saved', self.language))
            
            # Перезагружаем цели для тестирования
            self.init_targets()
        except Exception as e:
            QMessageBox.warning(self, tr('test_error_title', self.language), 
                              f"{tr('targets_error_saving', self.language)}: {str(e)}")
            # Включаем watcher обратно в случае ошибки
            if os.path.exists(self.targets_file_path):
                self.file_watcher.addPath(self.targets_file_path)
    
    def reload_targets_file(self):
        """Перезагружает файл targets.txt из диска"""
        if self.targets_text_changed:
            reply = QMessageBox.question(
                self,
                tr('test_error_title', self.language),
                tr('targets_unsaved_changes', self.language),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
        self.load_targets_file()
        # Перезагружаем цели для тестирования
        self.init_targets()
    
    def on_targets_text_changed(self):
        """Обработчик изменения текста в редакторе"""
        self.targets_text_changed = True
    
    def on_targets_file_changed_externally(self, path):
        """Обработчик изменения файла targets.txt извне"""
        if path == self.targets_file_path:
            # Если файл был изменен извне и у нас есть несохраненные изменения, спрашиваем
            if self.targets_text_changed:
                reply = QMessageBox.question(
                    self,
                    tr('test_error_title', self.language),
                    tr('targets_file_changed', self.language),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.load_targets_file()
                    # Перезагружаем цели для тестирования
                    self.init_targets()
            else:
                # Если нет несохраненных изменений, просто перезагружаем
                self.load_targets_file()
                # Перезагружаем цели для тестирования
                self.init_targets()
            
            # Переподключаем watcher (файл мог быть удален и создан заново)
            if os.path.exists(self.targets_file_path):
                if self.targets_file_path not in self.file_watcher.files():
                    self.file_watcher.addPath(self.targets_file_path)

