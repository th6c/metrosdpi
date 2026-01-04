"""
Модуль для управления переводами интерфейса
"""

TRANSLATIONS = {
    'ru': {
        # Меню
        'menu_file': 'Файл',
        'menu_strategies': 'Стратегии',
        'menu_settings': 'Настройки',
        'menu_update': 'Обновление',
        'menu_help': 'Справка',
        'menu_change_language': 'Сменить язык',
        'menu_list_strategies': 'Список всех стратегий',
        'strategies_open_winws_folder': 'Открыть папку winws',
        'menu_add_b_flag_submenu': 'Добавление команды /B',
        'menu_add_b_flag': 'Добавить /B во все стратегии',
        'menu_add_b_flag_on_update': 'Добавлять /B при обновлении',
        'menu_run_test': 'Запуск теста',
        'menu_exit': 'Выход',
        
        # Настройки
        'settings_show_tray': 'Отображать в трее',
        'settings_close_winws': 'Закрывать winws при выходе',
        'settings_start_minimized': 'Запускать свернутым в трей',
        'settings_auto_start': 'Автозапуск последней стратегии',
        'settings_autostart_windows': 'Автозапуск с Windows',
        
        # Обновление
        'update_check_zapret': 'Проверить наличие обновление стратегий zapret',
        'update_manual': 'Обновить стратегии в ручную',
        'update_remove_check_updates': 'Удалять проверку обновлений в winws',
        
        # Кнопки
        'button_start': 'Запустить',
        'button_stop': 'Остановить',
        
        # Сообщения
        'msg_no_bat_files': 'Нет .bat файлов',
        'msg_winws_not_found': 'Папка winws не найдена',
        'msg_minimized_to_tray': 'Окно свернуто в трей',
        'msg_minimized_to_tray_info': 'Нажмите на иконку в трее, чтобы открыть окно',
        'msg_app_minimized_to_tray': 'Приложение свернуто в трей',
        'msg_app_minimized_to_tray_info': 'Нажмите на иконку в трее, чтобы открыть окно',
        'msg_check_updates_title': 'Проверка обновлений',
        'msg_check_updates_text': 'Проверка наличия обновлений стратегий zapret...',
        'msg_check_updates_info': 'Функция проверки обновлений будет реализована позже.',
        'msg_manual_update_title': 'Обновление стратегий',
        'msg_manual_update_text': 'Обновление стратегий вручную...',
        'msg_manual_update_info': 'Функция ручного обновления будет реализована позже.',
        
        # Трей меню
        'tray_show': 'Показать окно',
        'tray_hide': 'Скрыть окно',
        'tray_minimize': 'Свернуть окно',
        'tray_quit': 'Выход',
        
        # Test Window
        'test_window_title': 'Запуск теста стратегий',
        'test_start_button': 'Запустить тесты',
        'test_stop_button': 'Остановить',
        'test_close_button': 'Закрыть',
        'test_strategy_label': 'Стратегия:',
        'test_all_strategies': 'Все стратегии',
        'test_auto_scroll': 'Автоскролл',
        'test_status_ready': 'Готов к запуску тестов',
        'test_status_testing': 'Тестирование:',
        'test_status_stopping': 'Остановка тестов...',
        'test_status_finished': 'Тесты завершены',
        'test_error_title': 'Ошибка',
        'test_error_cannot_determine': 'Не удалось определить выбранную стратегию',
        'test_error_no_bat_files': 'Не найдено .bat файлов для тестирования',
        'tab_test_results': 'Результаты тестирования',
        'tab_best_strategies': 'Лучшие стратегии',
        'tab_targets': 'Targets',
        'targets_save_button': 'Сохранить',
        'targets_reload_button': 'Обновить',
        'targets_file_changed': 'Файл изменен извне. Обновить?',
        'targets_unsaved_changes': 'У вас есть несохраненные изменения. Перезагрузить файл? Несохраненные изменения будут потеряны.',
        'targets_saved': 'Файл сохранен',
        'targets_error_loading': 'Ошибка загрузки файла',
        'targets_error_saving': 'Ошибка сохранения файла',
        'table_col_strategy': 'Стратегия',
        'table_col_target': 'Target',
        'table_col_http_tls': 'HTTP/TLS',
        'table_col_ping': 'Ping',
        'best_strategies_col_rank': 'Место',
        'best_strategies_col_strategy': 'Стратегия',
        'best_strategies_col_http_ok': 'HTTP OK',
        'best_strategies_col_tls_ok': 'TLS OK',
        'best_strategies_col_ping_ok': 'Ping OK',
        
        # Справка
        'help_open_github': 'Открыть страницу Github',
        'help_open_help': 'Открыть справку программы',
        'help_file_not_found_title': 'Файл не найден',
        'help_file_not_found_text': 'Файл справки не найден:\n{0}',
    },
    'en': {
        # Меню
        'menu_file': 'File',
        'menu_strategies': 'Strategies',
        'menu_settings': 'Settings',
        'menu_update': 'Update',
        'menu_help': 'Help',
        'menu_change_language': 'Change language',
        'menu_list_strategies': 'List of all strategies',
        'strategies_open_winws_folder': 'Open winws folder',
        'menu_add_b_flag_submenu': 'Adding /B command',
        'menu_add_b_flag': 'Add /B to all strategies',
        'menu_add_b_flag_on_update': 'Add /B on update',
        'menu_run_test': 'Run test',
        'menu_exit': 'Exit',
        
        # Настройки
        'settings_show_tray': 'Show in tray',
        'settings_close_winws': 'Close winws on exit',
        'settings_start_minimized': 'Start minimized to tray',
        'settings_auto_start': 'Auto-start last strategy',
        'settings_autostart_windows': 'Start with Windows',
        
        # Обновление
        'update_check_zapret': 'Check for zapret strategy updates',
        'update_manual': 'Update strategies manually',
        'update_remove_check_updates': 'Remove check updates in winws',
        
        # Кнопки
        'button_start': 'Start',
        'button_stop': 'Stop',
        
        # Сообщения
        'msg_no_bat_files': 'No .bat files',
        'msg_winws_not_found': 'winws folder not found',
        'msg_minimized_to_tray': 'Window minimized to tray',
        'msg_minimized_to_tray_info': 'Click on the tray icon to open the window',
        'msg_app_minimized_to_tray': 'Application minimized to tray',
        'msg_app_minimized_to_tray_info': 'Click on the tray icon to open the window',
        'msg_check_updates_title': 'Check for updates',
        'msg_check_updates_text': 'Checking for zapret strategy updates...',
        'msg_check_updates_info': 'Update check function will be implemented later.',
        'msg_manual_update_title': 'Update strategies',
        'msg_manual_update_text': 'Updating strategies manually...',
        'msg_manual_update_info': 'Manual update function will be implemented later.',
        
        # Трей меню
        'tray_show': 'Show window',
        'tray_hide': 'Hide window',
        'tray_minimize': 'Minimize window',
        'tray_quit': 'Quit',
        
        # Test Window
        'test_window_title': 'Strategy Test',
        'test_start_button': 'Start Tests',
        'test_stop_button': 'Stop',
        'test_close_button': 'Close',
        'test_strategy_label': 'Strategy:',
        'test_all_strategies': 'All strategies',
        'test_auto_scroll': 'Auto-scroll',
        'test_status_ready': 'Ready to start tests',
        'test_status_testing': 'Testing:',
        'test_status_stopping': 'Stopping tests...',
        'test_status_finished': 'Tests completed',
        'test_error_title': 'Error',
        'test_error_cannot_determine': 'Could not determine selected strategy',
        'test_error_no_bat_files': 'No .bat files found for testing',
        'tab_test_results': 'Test Results',
        'tab_best_strategies': 'Best Strategies',
        'tab_targets': 'Targets',
        'targets_save_button': 'Save',
        'targets_reload_button': 'Reload',
        'targets_file_changed': 'File changed externally. Reload?',
        'targets_unsaved_changes': 'You have unsaved changes. Reload file? Unsaved changes will be lost.',
        'targets_saved': 'File saved',
        'targets_error_loading': 'Error loading file',
        'targets_error_saving': 'Error saving file',
        'table_col_strategy': 'Strategy',
        'table_col_target': 'Target',
        'table_col_http_tls': 'HTTP/TLS',
        'table_col_ping': 'Ping',
        'best_strategies_col_rank': 'Rank',
        'best_strategies_col_strategy': 'Strategy',
        'best_strategies_col_http_ok': 'HTTP OK',
        'best_strategies_col_tls_ok': 'TLS OK',
        'best_strategies_col_ping_ok': 'Ping OK',
        
        # Help
        'help_open_github': 'Open Github page',
        'help_open_help': 'Open program help',
        'help_file_not_found_title': 'File not found',
        'help_file_not_found_text': 'Help file not found:\n{0}',
    }
}


def tr(key: str, language: str = 'ru') -> str:
    """
    Получает перевод строки по ключу и языку
    
    Args:
        key: Ключ перевода
        language: Язык ('ru' или 'en')
    
    Returns:
        Переведенная строка или ключ, если перевод не найден
    """
    return TRANSLATIONS.get(language, TRANSLATIONS['ru']).get(key, key)

