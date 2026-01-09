"""
Модуль для управления переводами интерфейса
"""

TRANSLATIONS = {
    'ru': {
        # Меню
        'menu_file': 'Файл',
        'menu_strategies': 'Стратегии',
        'menu_tools': 'Инструменты',
        'menu_settings': 'Настройки',
        'menu_open_settings': 'Настройки',
        'menu_update': 'Обновление',
        'menu_help': 'Справка',
        'menu_change_language': 'Язык программы',
        'menu_list_strategies': 'Список всех стратегий',
        'strategies_open_winws_folder': 'Открыть папку winws',
        'menu_add_b_flag_submenu': 'Добавление команды /B',
        'menu_add_b_flag': 'Добавить /B во все стратегии',
        'menu_remove_b_flag': 'Удалить /B из всех стратегий',
        'menu_add_b_flag_on_update': 'Добавлять /B при обновлении',
        'menu_run_test': 'Запустить тестирование',
        'menu_run_diagnostics': 'Запустить диагностику',
        'menu_exit': 'Выход',
        
        # Настройки
        'settings_show_tray': 'Отображать в трее',
        'settings_close_winws': 'Закрывать winws при выходе',
        'settings_start_minimized': 'Запускать свернутым в трей',
        'settings_auto_start': 'Автозапуск последней стратегии',
        'settings_autostart_windows': 'Автозапуск с Windows',
        'settings_auto_restart_strategy': 'Автоперезапуск стратегии',
        'settings_game_filter': 'Game фильтр',
        'settings_ipset_filter': 'IPSet фильтр',
        'update_ipset_list': 'Обновить IPSet List',
        'update_hosts_file': 'Обновить Hosts File',
        
        # Обновление
        'update_check_zapret': 'Проверить обновление zapret (Flowseal)',
        'update_manual': 'Обновить стратегии в ручную (zip)',
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
        'tray_change_strategy': 'Изменить стратегию',
        'tray_current_strategy': 'Текущая стратегия:',
        'tray_restart_menu': 'Перезапуск',
        'tray_restart_application': 'Перезапустить программу',
        'tray_restart_strategy': 'Перезапустить стратегию',
        'tray_program_parameters': 'Параметры программы',
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
        'help_open_github': 'Открыть MetrosDPI Github',
        'help_open_help': 'Открыть справку программы',
        'help_open_github_zapret': 'Открыть Github Flowseal zapret',
        'help_file_not_found_title': 'Файл не найден',
        'help_file_not_found_text': 'Файл справки не найден:\n{0}',
        
        # Права администратора
        'admin_required_title': 'Требуются права администратора',
        'admin_required_text': 'Для работы программы требуются права администратора.\n\nПерезапустить программу с правами администратора?',
        'admin_error_title': 'Ошибка',
        'admin_error_text': 'Не удалось запросить права администратора:\n{0}\n\nПожалуйста, запустите программу от имени администратора вручную.',
        
        # Обновления
        'update_checking': 'Проверка обновлений...',
        'update_not_found': 'Обновления не найдены',
        'update_current_version': 'Установлена актуальная версия: {0}',
        'update_available_title': 'Обновление доступно',
        'update_available_text': 'Найдена новая версия: {0}\nТекущая версия: {1}\n\nХотите обновить стратегии zapret?',
        'update_error_title': 'Ошибка',
        'update_error_url_not_found': 'URL для скачивания не найден',
        'update_stopping_winws': 'Остановка winws',
        'update_winws_running': 'Обнаружен запущенный процесс winws.exe',
        'update_winws_stop_required': 'Необходимо остановить процесс перед обновлением. Остановить сейчас?',
        'update_title': 'Обновление',
        'update_downloading': 'Скачивание обновления...',
        'update_installing': 'Установка обновления...',
        'update_completed': 'Обновление завершено',
        'update_completed_text': 'Стратегии zapret успешно обновлены до версии {0}',
        'update_error_title': 'Ошибка обновления',
        'update_error_text': 'Ошибка при обновлении: {0}',
        'update_manual_title': 'Обновление стратегий',
        'update_manual_select_archive': 'Выберите архив для обновления',
        'update_manual_extracting': 'Распаковка архива...',
        'update_manual_completed': 'Стратегии успешно обновлены из архива',
    },
    'en': {
        # Меню
        'menu_file': 'File',
        'menu_strategies': 'Strategies',
        'menu_tools': 'Tools',
        'menu_settings': 'Settings',
        'menu_open_settings': 'Settings',
        'menu_update': 'Update',
        'menu_help': 'Help',
        'menu_change_language': 'Program language',
        'menu_list_strategies': 'List of all strategies',
        'strategies_open_winws_folder': 'Open winws folder',
        'menu_add_b_flag_submenu': 'Adding /B command',
        'menu_add_b_flag': 'Add /B to all strategies',
        'menu_remove_b_flag': 'Remove /B from all strategies',
        'menu_add_b_flag_on_update': 'Add /B on update',
        'menu_run_test': 'Run Testing',
        'menu_run_diagnostics': 'Run Diagnostics',
        'menu_exit': 'Exit',
        
        # Настройки
        'settings_show_tray': 'Show in tray',
        'settings_close_winws': 'Close winws on exit',
        'settings_start_minimized': 'Start minimized to tray',
        'settings_auto_start': 'Auto-start last strategy',
        'settings_autostart_windows': 'Start with Windows',
        'settings_auto_restart_strategy': 'Auto-restart strategy',
        'settings_game_filter': 'Game Filter',
        'settings_ipset_filter': 'IPSet Filter',
        'update_ipset_list': 'Update IPSet List',
        'update_hosts_file': 'Update Hosts File',
        
        # Обновление
        'update_check_zapret': 'Check for zapret (Flowseal) updates',
        'update_manual': 'Update strategies manually (zip)',
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
        'tray_change_strategy': 'Change strategy',
        'tray_current_strategy': 'Current strategy:',
        'tray_restart_menu': 'Restart',
        'tray_restart_application': 'Restart application',
        'tray_restart_strategy': 'Restart strategy',
        'tray_program_parameters': 'Program Parameters',
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
        'help_open_github': 'Open MetrosDPI Github',
        'help_open_help': 'Open program help',
        'help_open_github_zapret': 'Open Github Flowseal zapret',
        'help_file_not_found_title': 'File not found',
        'help_file_not_found_text': 'Help file not found:\n{0}',
        
        # Admin rights
        'admin_required_title': 'Administrator rights required',
        'admin_required_text': 'The program requires administrator rights to work.\n\nRestart the program with administrator rights?',
        'admin_error_title': 'Error',
        'admin_error_text': 'Failed to request administrator rights:\n{0}\n\nPlease run the program as administrator manually.',
        
        # Updates
        'update_checking': 'Checking for updates...',
        'update_not_found': 'No updates found',
        'update_current_version': 'Current version installed: {0}',
        'update_available_title': 'Update available',
        'update_available_text': 'New version found: {0}\nCurrent version: {1}\n\nDo you want to update zapret strategies?',
        'update_error_title': 'Error',
        'update_error_url_not_found': 'Download URL not found',
        'update_stopping_winws': 'Stopping winws',
        'update_winws_running': 'Running winws.exe process detected',
        'update_winws_stop_required': 'The process must be stopped before updating. Stop now?',
        'update_title': 'Update',
        'update_downloading': 'Downloading update...',
        'update_installing': 'Installing update...',
        'update_completed': 'Update completed',
        'update_completed_text': 'Zapret strategies successfully updated to version {0}',
        'update_error_title': 'Update error',
        'update_error_text': 'Error updating: {0}',
        'update_manual_title': 'Update strategies',
        'update_manual_select_archive': 'Select archive for update',
        'update_manual_extracting': 'Extracting archive...',
        'update_manual_completed': 'Strategies successfully updated from archive',
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

