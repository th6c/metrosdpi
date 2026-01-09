import os
import requests
import zipfile
import shutil
from pathlib import Path
import json
from path_utils import get_winws_path, get_base_path


class ZapretUpdater:
    """Класс для проверки и обновления стратегий zapret"""
    
    GITHUB_REPO = "Flowseal/zapret-discord-youtube"
    GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    
    def __init__(self):
        # Получаем пути динамически
        self.WINWS_FOLDER = get_winws_path()
        base_path = get_base_path()
        self.VERSION_FILE = os.path.join(base_path, "app/config/zapret_version.json")
        self.current_version = self.get_current_version()
    
    def get_current_version(self):
        """Получает текущую установленную версию"""
        try:
            if os.path.exists(self.VERSION_FILE):
                with open(self.VERSION_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('version', 'unknown')
        except Exception:
            pass
        return 'unknown'
    
    def save_version(self, version):
        """Сохраняет версию в файл"""
        try:
            os.makedirs(os.path.dirname(self.VERSION_FILE), exist_ok=True)
            with open(self.VERSION_FILE, 'w', encoding='utf-8') as f:
                json.dump({'version': version}, f, indent=4)
        except Exception as e:
            print(f"Ошибка при сохранении версии: {e}")
    
    def check_for_updates(self):
        """Проверяет наличие обновлений на GitHub"""
        try:
            response = requests.get(self.GITHUB_API_URL, timeout=10)
            response.raise_for_status()
            release_data = response.json()
            
            latest_version = release_data.get('tag_name', '').lstrip('v')
            download_url = None
            
            # Ищем zip архив для скачивания
            for asset in release_data.get('assets', []):
                if asset.get('name', '').endswith('.zip'):
                    download_url = asset.get('browser_download_url')
                    break
            
            return {
                'has_update': latest_version != self.current_version,
                'latest_version': latest_version,
                'current_version': self.current_version,
                'download_url': download_url,
                'release_url': release_data.get('html_url', ''),
                'release_notes': release_data.get('body', '')
            }
        except requests.RequestException as e:
            return {
                'has_update': False,
                'error': f'Ошибка при проверке обновлений: {str(e)}'
            }
        except Exception as e:
            return {
                'has_update': False,
                'error': f'Неожиданная ошибка: {str(e)}'
            }
    
    def download_update(self, download_url, progress_callback=None):
        """Скачивает обновление"""
        try:
            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Создаем временную папку для загрузки
            temp_dir = os.path.join(os.path.dirname(self.WINWS_FOLDER), 'temp_update')
            os.makedirs(temp_dir, exist_ok=True)
            
            zip_path = os.path.join(temp_dir, 'update.zip')
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_size > 0:
                            progress = (downloaded / total_size) * 100
                            progress_callback(progress)
            
            return zip_path
        except Exception as e:
            raise Exception(f'Ошибка при скачивании: {str(e)}')
    
    def extract_and_update(self, zip_path, version):
        """Распаковывает архив и обновляет файлы в winws"""
        import time
        backup_folder = None
        try:
            # Создаем резервную копию текущей папки winws
            backup_folder = f"{self.WINWS_FOLDER}_backup"
            if os.path.exists(self.WINWS_FOLDER):
                if os.path.exists(backup_folder):
                    shutil.rmtree(backup_folder)
                shutil.copytree(self.WINWS_FOLDER, backup_folder)
            
            # Распаковываем архив во временную папку
            temp_extract = os.path.join(os.path.dirname(self.WINWS_FOLDER), 'temp_extract')
            if os.path.exists(temp_extract):
                shutil.rmtree(temp_extract)
            os.makedirs(temp_extract, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_extract)
            
            # Ищем .bat файлы в распакованном архиве
            # Проверяем несколько возможных мест:
            # 1. Прямо в корне архива
            # 2. В папке winws
            # 3. В любой другой папке
            
            winws_source = None
            bat_files_found = []
            
            # Сначала ищем папку winws
            for root, dirs, files in os.walk(temp_extract):
                if 'winws' in dirs:
                    winws_source = os.path.join(root, 'winws')
                    break
            
            # Если папки winws нет, ищем .bat файлы напрямую
            if not winws_source:
                for root, dirs, files in os.walk(temp_extract):
                    for file in files:
                        if file.endswith('.bat'):
                            bat_files_found.append((root, file))
            
            # Если нашли .bat файлы, но нет папки winws, создаем структуру
            if bat_files_found and not winws_source:
                # Определяем общую папку для всех .bat файлов
                if len(bat_files_found) > 0:
                    # Берем первую найденную папку как источник
                    first_bat_dir = bat_files_found[0][0]
                    # Проверяем, все ли .bat файлы в одной папке
                    all_same_dir = all(dir_path == first_bat_dir for dir_path, _ in bat_files_found)
                    if all_same_dir:
                        winws_source = first_bat_dir
                    else:
                        # Если .bat файлы в разных папках, используем корень архива
                        winws_source = temp_extract
            
            # Если все еще не нашли, используем корень распакованного архива
            if not winws_source:
                # Проверяем, есть ли .bat файлы в корне
                root_files = os.listdir(temp_extract)
                bat_in_root = [f for f in root_files if f.endswith('.bat')]
                if bat_in_root:
                    winws_source = temp_extract
                else:
                    # Ищем любую папку с .bat файлами
                    for root, dirs, files in os.walk(temp_extract):
                        bat_files = [f for f in files if f.endswith('.bat')]
                        if bat_files:
                            winws_source = root
                            break
            
            if not winws_source:
                raise Exception('Не найдены .bat файлы в архиве')
            
            # Ждем немного, чтобы убедиться, что все процессы завершились
            import time
            time.sleep(2)
            
            # Обновляем файлы по одному, не удаляя всю папку
            if os.path.isdir(winws_source):
                # Создаем список всех файлов и папок для обновления
                items_to_update = []
                for root, dirs, files in os.walk(winws_source):
                    # Добавляем файлы
                    for file in files:
                        rel_path = os.path.relpath(os.path.join(root, file), winws_source)
                        items_to_update.append(('file', rel_path, os.path.join(root, file)))
                    # Добавляем папки
                    for dir_name in dirs:
                        rel_path = os.path.relpath(os.path.join(root, dir_name), winws_source)
                        items_to_update.append(('dir', rel_path, os.path.join(root, dir_name)))
                
                # Создаем папку winws если её нет
                os.makedirs(self.WINWS_FOLDER, exist_ok=True)
                
                # Обновляем файлы и папки
                for item_type, rel_path, src_path in items_to_update:
                    dst_path = os.path.join(self.WINWS_FOLDER, rel_path)
                    
                    # Создаем родительские папки если нужно
                    parent_dir = os.path.dirname(dst_path)
                    if parent_dir:
                        os.makedirs(parent_dir, exist_ok=True)
                    
                    try:
                        if item_type == 'dir':
                            # Если папка существует, удаляем её
                            if os.path.exists(dst_path):
                                for attempt in range(5):
                                    try:
                                        shutil.rmtree(dst_path)
                                        break
                                    except (PermissionError, OSError):
                                        if attempt < 4:
                                            time.sleep(0.5)
                                        else:
                                            raise
                            shutil.copytree(src_path, dst_path)
                        else:
                            # Если файл существует, удаляем его
                            if os.path.exists(dst_path):
                                # Пробуем удалить несколько раз с задержкой
                                for attempt in range(5):
                                    try:
                                        os.remove(dst_path)
                                        break
                                    except (PermissionError, OSError):
                                        if attempt < 4:
                                            time.sleep(0.5)
                                        else:
                                            raise
                            shutil.copy2(src_path, dst_path)
                    except (PermissionError, OSError) as e:
                        # Если не удалось обновить файл, пропускаем его
                        print(f"Не удалось обновить {rel_path}: {e}")
                        continue
            else:
                raise Exception('Источник для копирования не найден')
            
            # Сохраняем версию
            self.save_version(version)
            self.current_version = version
            
            # Очищаем временные файлы
            try:
                shutil.rmtree(temp_extract)
                os.remove(zip_path)
                if os.path.exists(os.path.dirname(zip_path)):
                    try:
                        os.rmdir(os.path.dirname(zip_path))
                    except OSError:
                        pass  # Папка не пустая
            except Exception:
                pass
            
            return True
        except Exception as e:
            # Восстанавливаем из резервной копии при ошибке
            if backup_folder and os.path.exists(backup_folder):
                if os.path.exists(self.WINWS_FOLDER):
                    shutil.rmtree(self.WINWS_FOLDER)
                shutil.copytree(backup_folder, self.WINWS_FOLDER)
            raise Exception(f'Ошибка при обновлении: {str(e)}')

