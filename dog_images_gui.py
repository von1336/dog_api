import os
import sys
import json
import logging
import asyncio
import requests
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin
import tkinter as tk
from tkinter import messagebox, filedialog

import customtkinter as ctk
from PIL import Image, ImageTk
import tqdm


class Config:
    DOG_API_BASE_URL: str = "https://dog.ceo/api"
    YANDEX_DISK_API_URL: str = "https://cloud-api.yandex.net/v1/disk"
    YANDEX_DISK_TOKEN: str = ""
    BASE_FOLDER_NAME: str = "DogImages"
    RESULTS_JSON_FILE: str = "dog_images_results.json"
    LOG_FORMAT: str = "%(asctime)s - %(levelname)s - %(message)s"
    LOG_LEVEL: str = "DEBUG"
    REQUEST_TIMEOUT: int = 30
    CONFIG_FILE: str = "app_config.json"


def load_config():
    try:
        if os.path.exists(Config.CONFIG_FILE):
            with open(Config.CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                Config.YANDEX_DISK_TOKEN = data.get('token', '')
                Config.BASE_FOLDER_NAME = data.get('folder_name', 'DogImages')
    except Exception as e:
        logging.warning(f"Не удалось загрузить конфигурацию: {e}")


def save_config():
    try:
        data = {
            'token': Config.YANDEX_DISK_TOKEN,
            'folder_name': Config.BASE_FOLDER_NAME
        }
        with open(Config.CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.warning(f"Не удалось сохранить конфигурацию: {e}")


class DogAPI:
    def __init__(self):
        self.base_url = Config.DOG_API_BASE_URL
        self.timeout = Config.REQUEST_TIMEOUT
    
    def get_all_breeds(self) -> Dict[str, List[str]]:
        try:
            url = f"{self.base_url}/breeds/list/all"
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            if data.get('status') != 'success':
                raise ValueError(f"API вернул статус: {data.get('status')}")
            
            breeds = data.get('message', {})
            logging.info(f"Получено {len(breeds)} пород собак")
            return breeds
            
        except requests.RequestException as e:
            logging.error(f"Ошибка при получении списка пород: {e}")
            raise
        except ValueError as e:
            logging.error(f"Ошибка в данных API: {e}")
            raise
    
    def get_breed_image(self, breed: str, sub_breed: Optional[str] = None) -> Optional[str]:
        try:
            if sub_breed:
                url = f"{self.base_url}/breed/{breed}/{sub_breed}/images/random"
                breed_name = f"{breed}/{sub_breed}"
            else:
                url = f"{self.base_url}/breed/{breed}/images/random"
                breed_name = breed
            
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            if data.get('status') != 'success':
                logging.warning(f"API вернул статус '{data.get('status')}' для породы {breed_name}")
                return None
            
            image_url = data.get('message')
            if image_url:
                logging.info(f"Получен URL изображения для породы {breed_name}")
                return image_url
            else:
                logging.warning(f"Изображение для породы {breed_name} не найдено")
                return None
                
        except requests.RequestException as e:
            logging.error(f"Ошибка при получении изображения породы {breed_name}: {e}")
            return None
        except ValueError as e:
            logging.error(f"Ошибка в данных API для породы {breed_name}: {e}")
            return None
    
    def get_breed_images_data(self, breeds: Dict[str, List[str]], progress_callback=None) -> List[Dict]:
        images_data = []
        total_operations = sum(max(1, len(sub_breeds)) for sub_breeds in breeds.values())
        current_operation = 0
        
        for breed, sub_breeds in breeds.items():
            if sub_breeds:
                for sub_breed in sub_breeds:
                    image_url = self.get_breed_image(breed, sub_breed)
                    if image_url:
                        images_data.append({
                            'breed': breed,
                            'sub_breed': sub_breed,
                            'image_url': image_url,
                            'breed_full_name': f"{breed}_{sub_breed}"
                        })
                    
                    current_operation += 1
                    if progress_callback:
                        progress_callback(current_operation, total_operations, f"Получение URL для {breed}/{sub_breed}")
            else:
                image_url = self.get_breed_image(breed)
                if image_url:
                    images_data.append({
                        'breed': breed,
                        'sub_breed': None,
                        'image_url': image_url,
                        'breed_full_name': breed
                    })
                
                current_operation += 1
                if progress_callback:
                    progress_callback(current_operation, total_operations, f"Получение URL для {breed}")
        
        logging.info(f"Собрано {len(images_data)} изображений для загрузки")
        return images_data


class YandexDiskAPI:
    def __init__(self, token: str):
        self.token = token
        self.base_url = Config.YANDEX_DISK_API_URL
        self.headers = {
            'Authorization': f'OAuth {self.token}',
            'Content-Type': 'application/json'
        }
        self.timeout = Config.REQUEST_TIMEOUT
    
    def check_token(self) -> bool:
        try:
            url = self.base_url
            logging.debug(f"Проверка токена: URL={url}")
            
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            
            logging.debug(f"Token check response status: {response.status_code}")
            
            if response.status_code == 200:
                logging.info("Токен Яндекс.Диска валиден")
                return True
            else:
                logging.error(f"Токен невалиден. Код ответа: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            logging.error(f"Ошибка при проверке токена: {e}")
            return False
    
    def create_folder(self, path: str) -> bool:
        try:
            url = f"{self.base_url}/resources"
            params = {'path': path}
            
            logging.debug(f"Создание папки: URL={url}, path={path}")
            
            response = requests.put(
                url, 
                headers=self.headers, 
                params=params, 
                timeout=self.timeout
            )
            
            logging.debug(f"Response status: {response.status_code}")
            
            if response.status_code == 201:
                logging.info(f"Папка '{path}' создана успешно")
                return True
            elif response.status_code == 409:
                logging.info(f"Папка '{path}' уже существует")
                return True
            else:
                logging.error(f"Ошибка создания папки '{path}'. Код ответа: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            logging.error(f"Ошибка при создании папки '{path}': {e}")
            return False
    
    def upload_file_from_url(self, file_url: str, disk_path: str) -> Optional[Dict[str, Any]]:
        try:
            remote_upload_result = self._upload_from_remote_url(file_url, disk_path)
            if remote_upload_result:
                return remote_upload_result
            
            upload_url = self._get_upload_url(disk_path)
            if not upload_url:
                return None
            
            logging.info(f"Скачивание файла из {file_url}")
            file_response = requests.get(file_url, timeout=self.timeout)
            file_response.raise_for_status()
            
            logging.info(f"Загрузка файла на Яндекс.Диск: {disk_path}")
            upload_response = requests.put(
                upload_url,
                data=file_response.content,
                timeout=self.timeout
            )
            
            if upload_response.status_code in [201, 202]:
                logging.info(f"Файл '{disk_path}' загружен успешно")
                return {
                    'disk_path': disk_path,
                    'source_url': file_url,
                    'status': 'uploaded',
                    'size': len(file_response.content)
                }
            else:
                logging.error(f"Ошибка загрузки файла '{disk_path}'. Код ответа: {upload_response.status_code}")
                return None
                
        except requests.RequestException as e:
            logging.error(f"Ошибка при загрузке файла '{disk_path}': {e}")
            return None
    
    def _upload_from_remote_url(self, source_url: str, disk_path: str) -> Optional[Dict[str, Any]]:
        try:
            url = f"{self.base_url}/resources/upload"
            params = {
                'path': disk_path,
                'url': source_url
            }
            
            logging.debug(f"Remote upload: URL={url}, disk_path={disk_path}, source_url={source_url}")
            
            response = requests.post(
                url,
                headers=self.headers,
                params=params,
                timeout=self.timeout
            )
            
            logging.debug(f"Remote upload response status: {response.status_code}")
            
            if response.status_code in [201, 202]:
                logging.info(f"Файл '{disk_path}' загружен через remote upload")
                return {
                    'disk_path': disk_path,
                    'source_url': source_url,
                    'status': 'uploaded_remote',
                    'method': 'remote_upload'
                }
            else:
                logging.warning(f"Remote upload не удался для '{disk_path}'. Код: {response.status_code}")
                return None
                
        except requests.RequestException as e:
            logging.warning(f"Ошибка remote upload для '{disk_path}': {e}")
            return None
    
    def _get_upload_url(self, disk_path: str) -> Optional[str]:
        try:
            url = f"{self.base_url}/resources/upload"
            params = {'path': disk_path, 'overwrite': 'true'}
            
            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                upload_url = data.get('href')
                return upload_url
            else:
                logging.error(f"Ошибка получения URL для загрузки. Код ответа: {response.status_code}")
                return None
                
        except requests.RequestException as e:
            logging.error(f"Ошибка при получении URL для загрузки: {e}")
            return None


def setup_logging(log_widget=None) -> None:
    
    class GUILogHandler(logging.Handler):
        
        def __init__(self, text_widget):
            super().__init__()
            self.text_widget = text_widget
        
        def emit(self, record):
            if self.text_widget:
                msg = self.format(record)
                self.text_widget.after(0, lambda: self._append_log(msg))
        
        def _append_log(self, msg):
            if self.text_widget:
                self.text_widget.configure(state='normal')
                self.text_widget.insert('end', msg + '\n')
                self.text_widget.configure(state='disabled')
                self.text_widget.see('end')
    
    handlers = [
        logging.FileHandler('dog_images_downloader_gui.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
    
    if log_widget:
        gui_handler = GUILogHandler(log_widget)
        gui_handler.setFormatter(logging.Formatter(Config.LOG_FORMAT))
        handlers.append(gui_handler)
    
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format=Config.LOG_FORMAT,
        handlers=handlers,
        force=True
    )


def extract_filename_from_url(url: str) -> str:
    return url.split('/')[-1]


def create_filename(breed_name: str, image_url: str) -> str:
    original_filename = extract_filename_from_url(image_url)
    return f"{breed_name}_{original_filename}"


def save_results_to_json(results: List[Dict[str, Any]], filename: str) -> None:
    try:
        json_data = {
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'total_images': len(results),
                'successful_uploads': len([r for r in results if r.get('upload_status') == 'success']),
                'failed_uploads': len([r for r in results if r.get('upload_status') == 'failed'])
            },
            'results': results
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        logging.info(f"Результаты сохранены в файл: {filename}")
        
    except Exception as e:
        logging.error(f"Ошибка при сохранении результатов в JSON: {e}")


class DogImagesDownloaderGUI:
    
    def __init__(self):
        
        load_config()
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.root = ctk.CTk()
        self.root.title("Загрузчик изображений собак на Яндекс.Диск")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        self.is_running = False
        self.current_results = []
        
        self.create_widgets()
        self.setup_logging()
        
        logging.info("GUI приложение инициализировано")
    
    def create_widgets(self):
        title_frame = ctk.CTkFrame(self.root)
        title_frame.pack(fill="x", padx=10, pady=5)
        
        title_label = ctk.CTkLabel(
            title_frame, 
            text="Загрузчик изображений собак на Яндекс.Диск",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=10)
        
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        left_frame = ctk.CTkFrame(main_frame)
        left_frame.pack(side="left", fill="y", padx=5, pady=5)
        
        settings_label = ctk.CTkLabel(left_frame, text="Настройки", font=ctk.CTkFont(size=16, weight="bold"))
        settings_label.pack(pady=10)
        
        token_label = ctk.CTkLabel(left_frame, text="Токен Яндекс.Диска:")
        token_label.pack(pady=(10, 5))
        
        self.token_entry = ctk.CTkEntry(
            left_frame, 
            placeholder_text="Введите токен Яндекс.Диска...",
            width=300,
            show="*"
        )
        self.token_entry.pack(pady=5, padx=10)
        if Config.YANDEX_DISK_TOKEN:
            self.token_entry.insert(0, Config.YANDEX_DISK_TOKEN)
        
        self.show_token_var = ctk.BooleanVar()
        show_token_cb = ctk.CTkCheckBox(
            left_frame, 
            text="Показать токен", 
            variable=self.show_token_var,
            command=self.toggle_token_visibility
        )
        show_token_cb.pack(pady=5)
        
        folder_label = ctk.CTkLabel(left_frame, text="Папка на Яндекс.Диске:")
        folder_label.pack(pady=(15, 5))
        
        self.folder_entry = ctk.CTkEntry(left_frame, width=300)
        self.folder_entry.pack(pady=5, padx=10)
        self.folder_entry.insert(0, Config.BASE_FOLDER_NAME)
        
        self.check_token_btn = ctk.CTkButton(
            left_frame,
            text="Проверить токен",
            command=self.check_token,
            width=200
        )
        self.check_token_btn.pack(pady=15)
        
        self.start_btn = ctk.CTkButton(
            left_frame,
            text="Начать загрузку",
            command=self.start_download,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            width=200
        )
        self.start_btn.pack(pady=20)
        
        self.stop_btn = ctk.CTkButton(
            left_frame,
            text="Остановить",
            command=self.stop_download,
            width=200,
            fg_color="red"
        )
        self.stop_btn.pack(pady=5)
        self.stop_btn.configure(state="disabled")
        
        stats_label = ctk.CTkLabel(left_frame, text="Статистика", font=ctk.CTkFont(size=14, weight="bold"))
        stats_label.pack(pady=(20, 10))
        
        self.stats_frame = ctk.CTkFrame(left_frame)
        self.stats_frame.pack(fill="x", padx=10, pady=5)
        
        self.stats_breeds = ctk.CTkLabel(self.stats_frame, text="Пород: 0")
        self.stats_breeds.pack(pady=2)
        
        self.stats_uploaded = ctk.CTkLabel(self.stats_frame, text="Загружено: 0")
        self.stats_uploaded.pack(pady=2)
        
        self.stats_failed = ctk.CTkLabel(self.stats_frame, text="Ошибок: 0")
        self.stats_failed.pack(pady=2)
        
        right_frame = ctk.CTkFrame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        
        progress_label = ctk.CTkLabel(right_frame, text="Прогресс", font=ctk.CTkFont(size=16, weight="bold"))
        progress_label.pack(pady=10)
        
        self.progress_bar = ctk.CTkProgressBar(right_frame, width=400)
        self.progress_bar.pack(pady=10, padx=20, fill="x")
        self.progress_bar.set(0)
        
        self.progress_label = ctk.CTkLabel(right_frame, text="Готов к запуску")
        self.progress_label.pack(pady=5)
        
        logs_label = ctk.CTkLabel(right_frame, text="Логи", font=ctk.CTkFont(size=16, weight="bold"))
        logs_label.pack(pady=(20, 10))
        
        log_frame = ctk.CTkFrame(right_frame)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.log_textbox = ctk.CTkTextbox(
            log_frame,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word"
        )
        self.log_textbox.pack(fill="both", expand=True, padx=10, pady=10)
        
        log_buttons_frame = ctk.CTkFrame(right_frame)
        log_buttons_frame.pack(fill="x", padx=10, pady=5)
        
        clear_logs_btn = ctk.CTkButton(
            log_buttons_frame,
            text="Очистить логи",
            command=self.clear_logs,
            width=120
        )
        clear_logs_btn.pack(side="left", padx=5, pady=5)
        
        save_logs_btn = ctk.CTkButton(
            log_buttons_frame,
            text="Сохранить логи",
            command=self.save_logs,
            width=120
        )
        save_logs_btn.pack(side="left", padx=5, pady=5)
        
        results_btn = ctk.CTkButton(
            log_buttons_frame,
            text="Результаты",
            command=self.show_results,
            width=120
        )
        results_btn.pack(side="right", padx=5, pady=5)
    
    def setup_logging(self):
        setup_logging(self.log_textbox)
    
    def toggle_token_visibility(self):
        if self.show_token_var.get():
            self.token_entry.configure(show="")
        else:
            self.token_entry.configure(show="*")
    
    def check_token(self):
        token = self.token_entry.get().strip()
        if not token:
            messagebox.showerror("Ошибка", "Введите токен Яндекс.Диска!")
            return
        
        self.check_token_btn.configure(text="Проверяем...", state="disabled")
        
        def check_in_thread():
            try:
                yandex_disk = YandexDiskAPI(token)
                is_valid = yandex_disk.check_token()
                
                self.root.after(0, lambda: self._token_check_result(is_valid))
                
            except Exception as e:
                logging.error(f"Ошибка при проверке токена: {e}")
                self.root.after(0, lambda: self._token_check_result(False))
        
        threading.Thread(target=check_in_thread, daemon=True).start()
    
    def _token_check_result(self, is_valid: bool):
        self.check_token_btn.configure(text="Проверить токен", state="normal")
        
        if is_valid:
            messagebox.showinfo("Успех", "Токен валиден!")
            logging.info("Токен Яндекс.Диска проверен и валиден")
        else:
            messagebox.showerror("Ошибка", "Токен невалиден!")
            logging.error("Токен Яндекс.Диска невалиден")
    
    def start_download(self):
        if self.is_running:
            return
        
        token = self.token_entry.get().strip()
        folder_name = self.folder_entry.get().strip()
        
        if not token:
            messagebox.showerror("Ошибка", "Введите токен Яндекс.Диска!")
            return
        
        if not folder_name:
            messagebox.showerror("Ошибка", "Введите название папки!")
            return
        
        self.is_running = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress_bar.set(0)
        self.current_results = []
        
        Config.YANDEX_DISK_TOKEN = token
        Config.BASE_FOLDER_NAME = folder_name
        save_config()
        
        logging.info("Начинаем загрузку изображений собак...")
        
        threading.Thread(target=self._download_process, daemon=True).start()
    
    def stop_download(self):
        self.is_running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.progress_label.configure(text="Остановлено пользователем")
        logging.warning("Загрузка остановлена пользователем")
    
    def _download_process(self):
        try:
            dog_api = DogAPI()
            yandex_disk = YandexDiskAPI(Config.YANDEX_DISK_TOKEN)
            
            if not yandex_disk.check_token():
                self.root.after(0, lambda: self._download_finished(False, "Токен невалиден"))
                return
            
            self.root.after(0, lambda: self.progress_label.configure(text="Получение списка пород..."))
            breeds = dog_api.get_all_breeds()
            
            if not self.is_running:
                return
            
            total_breeds = len(breeds)
            self.root.after(0, lambda: self.stats_breeds.configure(text=f"Пород: {total_breeds}"))
            
            base_folder = Config.BASE_FOLDER_NAME
            self.root.after(0, lambda: self.progress_label.configure(text=f"Создание папки {base_folder}..."))
            
            if not yandex_disk.create_folder(base_folder):
                self.root.after(0, lambda: self._download_finished(False, "Не удалось создать базовую папку"))
                return
            
            if not self.is_running:
                return
            
            self.root.after(0, lambda: self.progress_label.configure(text="Получение URLs изображений..."))
            
            def progress_callback(current, total, status):
                if self.is_running:
                    progress = current / total
                    self.root.after(0, lambda: self.progress_bar.set(progress))
                    self.root.after(0, lambda: self.progress_label.configure(text=f"{status} ({current}/{total})"))
            
            images_data = dog_api.get_breed_images_data(breeds, progress_callback)
            
            if not self.is_running:
                return
            
            if not images_data:
                self.root.after(0, lambda: self._download_finished(False, "Не удалось получить изображения"))
                return
            
            results = []
            successful_uploads = 0
            failed_uploads = 0
            
            breeds_folders = {}
            for img_data in images_data:
                breed_folder = img_data['breed']
                if breed_folder not in breeds_folders:
                    breeds_folders[breed_folder] = []
                breeds_folders[breed_folder].append(img_data)
            
            total_images = len(images_data)
            current_image = 0
            
            for breed_name, breed_images in breeds_folders.items():
                if not self.is_running:
                    break
                
                breed_folder_path = f"{base_folder}/{breed_name}"
                if not yandex_disk.create_folder(breed_folder_path):
                    logging.error(f"Не удалось создать папку для породы {breed_name}")
                    continue
                
                for img_data in breed_images:
                    if not self.is_running:
                        break
                    
                    try:
                        current_image += 1
                        progress = current_image / total_images
                        
                        filename = create_filename(img_data['breed_full_name'], img_data['image_url'])
                        disk_path = f"{breed_folder_path}/{filename}"
                        
                        status_text = f"Загрузка {img_data['breed_full_name']} ({current_image}/{total_images})"
                        self.root.after(0, lambda p=progress, s=status_text: [
                            self.progress_bar.set(p),
                            self.progress_label.configure(text=s)
                        ])
                        
                        upload_result = yandex_disk.upload_file_from_url(img_data['image_url'], disk_path)
                        
                        result = {
                            'breed': img_data['breed'],
                            'sub_breed': img_data['sub_breed'],
                            'breed_full_name': img_data['breed_full_name'],
                            'source_url': img_data['image_url'],
                            'filename': filename,
                            'disk_path': disk_path,
                            'upload_status': 'success' if upload_result else 'failed',
                            'upload_info': upload_result,
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        results.append(result)
                        
                        if upload_result:
                            successful_uploads += 1
                        else:
                            failed_uploads += 1
                        
                        self.root.after(0, lambda s=successful_uploads, f=failed_uploads: [
                            self.stats_uploaded.configure(text=f"Загружено: {s}"),
                            self.stats_failed.configure(text=f"Ошибок: {f}")
                        ])
                        
                    except Exception as e:
                        logging.error(f"Ошибка при обработке изображения {img_data['image_url']}: {e}")
                        failed_uploads += 1
                        self.root.after(0, lambda f=failed_uploads: self.stats_failed.configure(text=f"Ошибок: {f}"))
            
            if results:
                self.current_results = results
                save_results_to_json(results, Config.RESULTS_JSON_FILE)
            
            if self.is_running:
                success_message = f"Загрузка завершена!\nУспешно: {successful_uploads}\nОшибок: {failed_uploads}"
                self.root.after(0, lambda: self._download_finished(True, success_message))
            
        except Exception as e:
            logging.error(f"Критическая ошибка в процессе загрузки: {e}")
            self.root.after(0, lambda: self._download_finished(False, f"Критическая ошибка: {e}"))
    
    def _download_finished(self, success: bool, message: str):
        self.is_running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        
        if success:
            self.progress_bar.set(1.0)
            self.progress_label.configure(text="Загрузка завершена успешно!")
            messagebox.showinfo("Успех", message)
        else:
            self.progress_label.configure(text="Ошибка при загрузке")
            messagebox.showerror("Ошибка", message)
        
        logging.info(f"Процесс загрузки завершен: {message}")
    
    def clear_logs(self):
        self.log_textbox.configure(state='normal')
        self.log_textbox.delete('1.0', 'end')
        self.log_textbox.configure(state='disabled')
        logging.info("Логи очищены")
    
    def save_logs(self):
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".log",
                filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")],
                initialfile=f"dog_downloader_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            )
            
            if filename:
                logs = self.log_textbox.get('1.0', 'end')
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(logs)
                
                messagebox.showinfo("Успех", f"Логи сохранены в файл:\n{filename}")
                logging.info(f"Логи сохранены в файл: {filename}")
        
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить логи:\n{e}")
            logging.error(f"Ошибка сохранения логов: {e}")
    
    def show_results(self):
        if not self.current_results:
            messagebox.showinfo("Информация", "Нет результатов для отображения.\nСначала запустите загрузку.")
            return
        
        results_window = ctk.CTkToplevel(self.root)
        results_window.title("Результаты загрузки")
        results_window.geometry("800x600")
        
        title_label = ctk.CTkLabel(
            results_window, 
            text="Результаты загрузки", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=10)
        
        stats_frame = ctk.CTkFrame(results_window)
        stats_frame.pack(fill="x", padx=10, pady=5)
        
        total = len(self.current_results)
        successful = len([r for r in self.current_results if r.get('upload_status') == 'success'])
        failed = total - successful
        
        stats_text = f"Всего: {total} | Успешно: {successful} | Ошибок: {failed}"
        stats_label = ctk.CTkLabel(stats_frame, text=stats_text, font=ctk.CTkFont(size=14))
        stats_label.pack(pady=10)
        
        results_frame = ctk.CTkFrame(results_window)
        results_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        results_text = ctk.CTkTextbox(results_frame, font=ctk.CTkFont(family="Consolas", size=10))
        results_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        header = f"{'Порода':<20} {'Подпорода':<15} {'Статус':<10} {'Время':<20}\n"
        separator = "-" * 80 + "\n"
        
        results_text.insert('end', header)
        results_text.insert('end', separator)
        
        for result in self.current_results:
            breed = result.get('breed', '')[:19]
            sub_breed = result.get('sub_breed', '')[:14] if result.get('sub_breed') else '-'
            status = 'OK' if result.get('upload_status') == 'success' else 'ERR'
            timestamp = result.get('timestamp', '')[:19] if result.get('timestamp') else ''
            
            line = f"{breed:<20} {sub_breed:<15} {status:<10} {timestamp:<20}\n"
            results_text.insert('end', line)
        
        results_text.configure(state='disabled')
        
        buttons_frame = ctk.CTkFrame(results_window)
        buttons_frame.pack(fill="x", padx=10, pady=5)
        
        close_btn = ctk.CTkButton(
            buttons_frame,
            text="Закрыть",
            command=results_window.destroy,
            width=100
        )
        close_btn.pack(side="right", padx=5, pady=5)
        
        export_btn = ctk.CTkButton(
            buttons_frame,
            text="Экспорт JSON",
            command=lambda: self._export_results(),
            width=120
        )
        export_btn.pack(side="right", padx=5, pady=5)
    
    def _export_results(self):
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                initialfile=f"dog_images_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            if filename:
                save_results_to_json(self.current_results, filename)
                messagebox.showinfo("Успех", f"Результаты экспортированы в:\n{filename}")
        
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось экспортировать результаты:\n{e}")
    
    def run(self):
        try:
            logging.info("Запуск GUI приложения")
            self.root.mainloop()
        except KeyboardInterrupt:
            logging.info("Приложение закрыто пользователем")
        except Exception as e:
            logging.error(f"Ошибка при запуске приложения: {e}")


def main():
    try:
        app = DogImagesDownloaderGUI()
        app.run()
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 