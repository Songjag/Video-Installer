from customtkinter import CTk, CTkButton, CTkLabel, CTkEntry, CTkFrame, CTkRadioButton, StringVar, CTkProgressBar
from tkinter import messagebox, filedialog
import threading
import os
import yt_dlp
import logging
import requests
import json
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item
import sys
import time

logging.basicConfig(
    format="%(levelname)s: %(message)s",
    level=logging.INFO  
)
log = logging.getLogger("cytdlp")
cookie = None

LOCK_FILE = "app.lock"

def opts():
    return {
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
                'player_skip': ['webpage'],
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        },
        'cookiefile': cookie,
        'retries': 3,
    }

class SingleInstance:
    def __init__(self):
        self.lock_file = LOCK_FILE
        if os.path.exists(self.lock_file):
            sys.exit(0)
        else:
            open(self.lock_file, 'w').close()
    
    def __del__(self):
        if os.path.exists(self.lock_file):
            os.remove(self.lock_file)

class VideoDownloader(CTk):
    def __init__(self, language='vie'):
        super().__init__()
        
        self.single_instance = SingleInstance()
        
        self.load_colors()
        self.load_language(language)
        self.title(self.text['app_title'])
        self.geometry("700x800")
        self.resizable(False, False)
        self.configure(fg_color=self.colors['bg_color'])

        self.download_mode = StringVar(value="video")
        self.platform = StringVar(value="youtube")
        self.output_path = os.path.join(os.path.expanduser("~"), "Downloads")
        self.is_downloading = False
        self.download_threads = []
        self.last_activity_time = time.time()
        
        self.tray_icon = None
        self.setup_tray_icon()
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.create_widgets()
        
        self.start_inactivity_timer()
    
    def start_inactivity_timer(self):
        def check_inactivity():
            while True:
                if not self.is_downloading:
                    if time.time() - self.last_activity_time > 120:
                        self.after(0, self.quit_app)
                        break
                time.sleep(10)
        
        timer_thread = threading.Thread(target=check_inactivity, daemon=True)
        timer_thread.start()
    
    def reset_activity_timer(self):
        self.last_activity_time = time.time()
    
    def setup_tray_icon(self):
        def create_icon_image():
            width = 64
            height = 64
            image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            
            draw.ellipse([4, 4, 60, 60], fill='#ff99bb', outline='#ff69b4', width=3)
            
            heart_color = 'white'
            draw.ellipse([18, 20, 32, 34], fill=heart_color)
            draw.ellipse([32, 20, 46, 34], fill=heart_color)
            draw.polygon([(18, 27), (46, 27), (32, 44)], fill=heart_color)
            
            return image
        
        icon_image = create_icon_image()
        
        menu = pystray.Menu(
            item(
                self.text.get('tray_show', 'Hiện cửa sổ ♡'),
                self.show_window,
                default=True
            ),
            item(
                self.text.get('tray_hide', 'Ẩn cửa sổ'),
                self.hide_window
            ),
            pystray.Menu.SEPARATOR,
            item(
                self.text.get('tray_downloading', 'Đang tải: Không'),
                lambda: None,
                enabled=False
            ),
            pystray.Menu.SEPARATOR,
            item(
                self.text.get('tray_exit', 'Thoát'),
                self.quit_app
            )
        )
        
        self.tray_icon = pystray.Icon(
            "video_downloader",
            icon_image,
            self.text['app_title'],
            menu
        )
        
        tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        tray_thread.start()
    
    def show_window(self, icon=None, item=None):
        self.after(0, self._show_window)
    
    def _show_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()
        self.window_visible = True
        self.reset_activity_timer()
    
    def hide_window(self, icon=None, item=None):
        self.withdraw()
        self.window_visible = False
        if self.tray_icon:
            self.tray_icon.notify(
                self.text.get('tray_notification_title', 'Đang chạy ngầm'),
                self.text.get('tray_notification_message', 'App đang chạy ở system tray ♡')
            )
    
    def quit_app(self, icon=None, item=None):
        if self.is_downloading:
            if icon:
                self.tray_icon.notify(
                    self.text.get('warning_title', 'Thông báo'),
                    self.text.get('tray_warning_downloading', 'Đang có video tải xuống! Vui lòng đợi...')
                )
            return
        
        if self.tray_icon:
            self.tray_icon.stop()
        
        self.quit()
        self.destroy()
    
    def update_tray_status(self, downloading=False):
        if not self.tray_icon:
            return
        
        try:
            status_text = self.text.get('tray_downloading', 'Đang tải: {}').format(
                self.text.get('yes', 'Có') if downloading else self.text.get('no', 'Không')
            )
            
            menu = pystray.Menu(
                item(
                    self.text.get('tray_show', 'Hiện cửa sổ ♡'),
                    self.show_window,
                    default=True
                ),
                item(
                    self.text.get('tray_hide', 'Ẩn cửa sổ'),
                    self.hide_window
                ),
                pystray.Menu.SEPARATOR,
                item(
                    status_text,
                    lambda: None,
                    enabled=False
                ),
                pystray.Menu.SEPARATOR,
                item(
                    self.text.get('tray_exit', 'Thoát'),
                    self.quit_app
                )
            )
            
            self.tray_icon.menu = menu
        except:
            pass
    
    def load_colors(self):
        try:
            with open('app/color.json', 'r', encoding='utf-8') as f:
                self.colors = json.load(f)
        except FileNotFoundError:
            self.colors = {
                "bg_color": "#ffc4da",
                "frame_color": "#ffffff",
                "accent_color": "#ff99bb",
                "button_color": "#ffc4da",
                "button_hover": "#ffb3d9",
                "text_color": "#ff6ba8",
                "progress_bg": "#ffe8f5",
                "border_color": "#ffb3d9"
            }
    
    def load_language(self, lang='vie'):
        try:
            with open('app/language.json', 'r', encoding='utf-8') as f:
                languages = json.load(f)
                self.text = languages.get(lang, languages['vie'])
        except FileNotFoundError:
            self.text = {
                "app_title": "♡ Tải Video ♡",
                "main_title": "♡ TẢI VIDEO ♡",
                "subtitle": "(❁´◡`❁) Tải video từ YouTube, TikTok, Facebook ✿",
                "download_btn": "♡ Tải xuống ♡",
                "ready_status": "Có thể tải rùi ♡"
            }
    
    def create_widgets(self):
        main_frame = CTkFrame(self, fg_color=self.colors['bg_color'], corner_radius=0)
        main_frame.pack(fill="both", expand=True, padx=30, pady=30)
        
        title_label = CTkLabel(
            main_frame,
            text=self.text['main_title'],
            font=("Comic Sans MS", 24, "bold"),
            text_color=self.colors['accent_color']
        )
        title_label.pack(pady=(0, 10))
        
        subtitle = CTkLabel(
            main_frame,
            text=self.text['subtitle'],
            font=("Comic Sans MS", 12),
            text_color=self.colors['text_color']
        )
        subtitle.pack(pady=(0, 15))
        
        input_frame = CTkFrame(main_frame, fg_color=self.colors['frame_color'], 
                              corner_radius=15, border_width=3, 
                              border_color=self.colors['button_color'])
        input_frame.pack(fill="x", pady=10)
        
        url_label = CTkLabel(
            input_frame,
            text=self.text['url_label'],
            font=("Comic Sans MS", 13, "bold"),
            text_color=self.colors['text_color']
        )
        url_label.pack(anchor="w", padx=15, pady=(15, 5))
        
        self.url_entry = CTkEntry(
            input_frame,
            placeholder_text=self.text['url_placeholder'],
            font=("Arial", 12),
            height=35,
            corner_radius=20,
            border_width=2,
            border_color=self.colors['button_color'],
            fg_color="white",
            text_color=self.colors['text_color']
        )
        self.url_entry.pack(fill="x", padx=15, pady=(0, 15))
        
        self.mode_frame = CTkFrame(main_frame, fg_color=self.colors['frame_color'], 
                                   corner_radius=15, border_width=3, 
                                   border_color=self.colors['button_color'])
        self.mode_frame.pack(fill="x", pady=10)
        
        mode_label = CTkLabel(
            self.mode_frame,
            text=self.text['mode_label'],
            font=("Comic Sans MS", 13, "bold"),
            text_color=self.colors['text_color']
        )
        mode_label.pack(anchor="w", padx=15, pady=(15, 10))
        
        radio_container = CTkFrame(self.mode_frame, fg_color="transparent")
        radio_container.pack(fill="x", padx=15, pady=(0, 15))
        
        self.video_radio = CTkRadioButton(
            radio_container,
            text=self.text['video_mode'],
            variable=self.download_mode,
            value="video",
            font=("Comic Sans MS", 12),
            text_color=self.colors['text_color'],
            fg_color=self.colors['accent_color'],
            hover_color=self.colors['button_hover']
        )
        self.video_radio.pack(side="left", padx=10)
        
        self.audio_radio = CTkRadioButton(
            radio_container,
            text=self.text['audio_mode'],
            variable=self.download_mode,
            value="audio",
            font=("Comic Sans MS", 12),
            text_color=self.colors['text_color'],
            fg_color=self.colors['accent_color'],
            hover_color=self.colors['button_hover']
        )
        self.audio_radio.pack(side="left", padx=10)
        
        filename_frame = CTkFrame(main_frame, fg_color=self.colors['frame_color'], 
                                 corner_radius=15, border_width=3, 
                                 border_color=self.colors['button_color'])
        filename_frame.pack(fill="x", pady=10)
        
        filename_label = CTkLabel(
            filename_frame,
            text=self.text.get('filename_label', '✿ Tên file (không bắt buộc):'),
            font=("Comic Sans MS", 13, "bold"),
            text_color=self.colors['text_color']
        )
        filename_label.pack(anchor="w", padx=15, pady=(15, 5))
        
        self.filename_entry = CTkEntry(
            filename_frame,
            placeholder_text=self.text.get('filename_placeholder', 'Để trống sẽ dùng tên gốc ♡'),
            font=("Arial", 12),
            height=35,
            corner_radius=20,
            border_width=2,
            border_color=self.colors['button_color'],
            fg_color="white",
            text_color=self.colors['text_color']
        )
        self.filename_entry.pack(fill="x", padx=15, pady=(0, 15))
        
        path_frame = CTkFrame(main_frame, fg_color=self.colors['frame_color'], 
                             corner_radius=15, border_width=3, 
                             border_color=self.colors['button_color'])
        path_frame.pack(fill="x", pady=10)
        
        path_label = CTkLabel(
            path_frame,
            text=self.text['save_label'],
            font=("Comic Sans MS", 13, "bold"),
            text_color=self.colors['text_color']
        )
        path_label.pack(anchor="w", padx=15, pady=(15, 5))
        
        path_container = CTkFrame(path_frame, fg_color="transparent")
        path_container.pack(fill="x", padx=15, pady=(0, 15))
        
        self.path_entry = CTkEntry(
            path_container,
            font=("Arial", 11),
            height=35,
            corner_radius=20,
            border_width=2,
            border_color=self.colors['button_color'],
            fg_color="white",
            text_color=self.colors['text_color']
        )
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.path_entry.insert(0, self.output_path)
        
        browse_btn = CTkButton(
            path_container,
            text=self.text['browse_btn'],
            command=self.browse_folder,
            width=80,
            height=35,
            corner_radius=20,
            fg_color=self.colors['button_color'],
            hover_color=self.colors['button_hover'],
            text_color="white",
            font=("Comic Sans MS", 11, "bold")
        )
        browse_btn.pack(side="right")
        
        self.progress_bar = CTkProgressBar(
            main_frame,
            height=15,
            corner_radius=10,
            fg_color=self.colors['progress_bg'],
            progress_color=self.colors['accent_color'],
            border_width=2,
            border_color=self.colors['button_color']
        )
        self.progress_bar.pack(fill="x", pady=10)
        self.progress_bar.set(0)
        
        self.status_label = CTkLabel(
            main_frame,
            text=self.text['ready_status'],
            font=("Comic Sans MS", 11),
            text_color=self.colors['text_color']
        )
        self.status_label.pack(pady=5)
        
        self.download_btn = CTkButton(
            main_frame,
            text=self.text['download_btn'],
            command=self.start_download,
            height=45,
            corner_radius=25,
            fg_color=self.colors['accent_color'],
            hover_color="#ff88b8",
            text_color="white",
            font=("Comic Sans MS", 16, "bold"),
            border_width=3,
            border_color="white"
        )
        self.download_btn.pack(fill="x", pady=15)
        
        footer = CTkLabel(
            main_frame,
            text=self.text['footer'],
            font=("Comic Sans MS", 10),
            text_color=self.colors['text_color']
        )
        footer.pack(pady=(5, 0))
    
    def on_closing(self):
        if self.is_downloading:
            self.hide_window()
        else:
            if messagebox.askyesno(
                self.text.get('confirm_title', 'Xác nhận'),
                self.text.get('confirm_exit', 'Bạn có chắc muốn thoát không?')
            ):
                self.quit_app()
    
    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.output_path)
        if folder:
            self.output_path = folder
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, folder)
        self.reset_activity_timer()
    
    def update_progress(self, value, status_text):
        self.progress_bar.set(value)
        self.status_label.configure(text=status_text)
        self.update_idletasks()
    
    def get_output_filename(self, default_title):
        custom_name = self.filename_entry.get().strip()
        if custom_name:
            safe_name = "".join(c for c in custom_name if c.isalnum() or c in (' ', '-', '_', '.')).strip()
            return safe_name if safe_name else default_title
        return default_title
    
    def check_file_exists(self, filepath):
        if os.path.exists(filepath):
            response = messagebox.askyesnocancel(
                self.text.get('file_exists_title', 'File đã tồn tại'),
                self.text.get('file_exists_message', f'File "{os.path.basename(filepath)}" đã tồn tại!\n\nYES: Ghi đè\nNO: Đổi tên tự động\nCANCEL: Hủy tải')
            )
            
            if response is None:
                return None
            elif response is False:
                base, ext = os.path.splitext(filepath)
                counter = 1
                while os.path.exists(f"{base}_{counter}{ext}"):
                    counter += 1
                return f"{base}_{counter}{ext}"
        return filepath
    def detect_platform(self, url: str):
        url = url.lower()
        if "youtube.com" in url or "youtu.be" in url:
            return "youtube"
        elif "tiktok.com" in url:
            return "tiktok"
        elif "facebook.com" in url or "fb.watch" in url:
            return "facebook"
        else:
            return None
        
    def start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning(self.text['warning_title'], 
                                 self.text['warning_message'])
            return
        
        platform = self.detect_platform(url)
        if not platform:
            messagebox.showerror(
                self.text.get('error_title', 'Lỗi'),
                self.text.get('unsupported_platform', 'URL không được hỗ trợ!\n\nChỉ hỗ trợ: YouTube, TikTok, Facebook')
            )
            return
        
        if platform in ['tiktok', 'facebook']:
            self.download_mode.set('video')
        
        self.reset_activity_timer()
        self.is_downloading = True
        self.update_tray_status(downloading=True)
        self.download_btn.configure(state="disabled", text=self.text['downloading_btn'])
        self.update_progress(0.1, self.text['status_start'])

        thread = threading.Thread(target=self.download_thread, args=(url, platform))
        thread.daemon = False
        thread.start()
        self.download_threads.append(thread)
    
    def download_thread(self, url, platform):
        try:
            if platform == "youtube":
                if self.download_mode.get() == "video":
                    self.download_youtube_video(url)
                else:
                    self.download_youtube_audio(url)
            elif platform == "tiktok":
                self.download_tiktok(url)
            elif platform == "facebook":
                self.download_facebook(url)
            
            self.after(100, lambda: self.update_progress(1.0, self.text['status_complete']))
            log.info("Download completed successfully")
        except Exception as e:
            log.error(f"Download error: {e}")
            error_msg = self.text['error_message'].format(error=str(e))
            self.after(100, lambda: self.update_progress(0, 
                      self.text['status_error'].format(error=str(e))))
            self.after(100, lambda: messagebox.showerror(self.text['error_title'], error_msg))
        finally:
            self.is_downloading = False
            self.update_tray_status(downloading=False)
            self.after(100, lambda: self.download_btn.configure(state="normal", 
                                                               text=self.text['download_btn']))
            self.reset_activity_timer()
    
    def download_youtube_video(self, url):
        os.makedirs(self.output_path, exist_ok=True)
        
        custom_name = self.filename_entry.get().strip()
        if custom_name:
            safe_name = "".join(c for c in custom_name if c.isalnum() or c in (' ', '-', '_')).strip()
            template = f"{safe_name}.%(ext)s" if safe_name else "%(title)s.%(ext)s"
        else:
            template = "%(title)s.%(ext)s"
        
        output_template = os.path.join(self.output_path, template)
        
        ydl_opts = {
            "format": "best[height<=1080]/best",
            "outtmpl": output_template,
            "merge_output_format": "mp4",
            "noplaylist": False,
            "yesplaylist": True,
            "progress_hooks": [self.progress_hook],
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'video')
            ext = 'mp4'
            
            if custom_name:
                safe_name = "".join(c for c in custom_name if c.isalnum() or c in (' ', '-', '_')).strip()
                filename = f"{safe_name}.{ext}" if safe_name else f"{title}.{ext}"
            else:
                filename = f"{title}.{ext}"
            
            filepath = os.path.join(self.output_path, filename)
            filepath = self.check_file_exists(filepath)
            
            if filepath is None:
                raise Exception(self.text.get('download_cancelled', 'Đã hủy tải xuống'))
            
            ydl_opts['outtmpl'] = filepath.replace(f".{ext}", ".%(ext)s")
            
            self.after(100, lambda: self.update_progress(0.3, self.text['status_youtube_video']))
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl2:
                ydl2.download([url])
    
    def download_youtube_audio(self, url):
        os.makedirs(self.output_path, exist_ok=True)
        
        custom_name = self.filename_entry.get().strip()
        if custom_name:
            safe_name = "".join(c for c in custom_name if c.isalnum() or c in (' ', '-', '_')).strip()
            template = f"{safe_name}.%(ext)s" if safe_name else "%(title)s.%(ext)s"
        else:
            template = "%(title)s.%(ext)s"
        
        output_template = os.path.join(self.output_path, template)
        
        ydl_opts = opts()
        ydl_opts.update({
            "format": "bestaudio/best",
            "outtmpl": output_template,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "extractaudio": True,
            "audioformat": "mp3",
            "audioquality": 0,
            "progress_hooks": [self.progress_hook],
        })
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'audio')
            
            if custom_name:
                safe_name = "".join(c for c in custom_name if c.isalnum() or c in (' ', '-', '_')).strip()
                filename = f"{safe_name}.mp3" if safe_name else f"{title}.mp3"
            else:
                filename = f"{title}.mp3"
            
            filepath = os.path.join(self.output_path, filename)
            filepath = self.check_file_exists(filepath)
            
            if filepath is None:
                raise Exception(self.text.get('download_cancelled', 'Đã hủy tải xuống'))
            
            ydl_opts['outtmpl'] = filepath.replace(".mp3", ".%(ext)s")
            
            self.after(100, lambda: self.update_progress(0.3, self.text['status_youtube_audio']))
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl2:
                ydl2.download([url])
    
    def download_tiktok(self, url):
        os.makedirs(self.output_path, exist_ok=True)
        
        self.after(100, lambda: self.update_progress(0.2, self.text['status_tiktok_info']))
        
        api_url = f"https://www.tikwm.com/api/?url={url}"
        
        try:
            response = requests.get(api_url)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') != 0:
                raise Exception(self.text['tiktok_error_info'])
            
            video_data = data.get('data', {})
            video_url = video_data.get('play')
            title = video_data.get('title', 'tiktok_video')
            
            if not video_url:
                raise Exception(self.text['tiktok_error_url'])
            
            custom_name = self.filename_entry.get().strip()
            if custom_name:
                safe_title = "".join(c for c in custom_name if c.isalnum() or c in (' ', '-', '_')).strip()
            else:
                safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
            
            if not safe_title:
                safe_title = f"tiktok_{video_data.get('id', 'video')}"
            
            filename = f"{safe_title}.mp4"
            filepath = os.path.join(self.output_path, filename)
            
            filepath = self.check_file_exists(filepath)
            if filepath is None:
                raise Exception(self.text.get('download_cancelled', 'Đã hủy tải xuống'))
            
            self.after(100, lambda: self.update_progress(0.4, self.text['status_tiktok_download']))
            
            video_response = requests.get(video_url, stream=True)
            video_response.raise_for_status()
            
            total_size = int(video_response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(filepath, 'wb') as file:
                for chunk in video_response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = downloaded / total_size
                            percent = int(progress * 100)
                            status = self.text['status_downloading'].format(percent=percent)
                            self.after(0, lambda p=progress, s=status: 
                                     self.update_progress(0.4 + (p * 0.5), s))
            
            log.info(f"TikTok video saved: {filepath}")
            
        except requests.RequestException as e:
            raise Exception(self.text['tiktok_error_api'].format(error=str(e)))
        except json.JSONDecodeError:
            raise Exception(self.text['tiktok_error_json'])
        except Exception as e:
            if 'tiktok_error' in str(e):
                raise
            raise Exception(self.text['tiktok_error_download'].format(error=str(e)))
    
    def download_facebook(self, url):
        os.makedirs(self.output_path, exist_ok=True)
        
        self.after(100, lambda: self.update_progress(0.2, self.text['status_facebook']))
        
        custom_name = self.filename_entry.get().strip()
        if custom_name:
            safe_name = "".join(c for c in custom_name if c.isalnum() or c in (' ', '-', '_')).strip()
            template = f"{safe_name}.%(ext)s" if safe_name else "%(title)s.%(ext)s"
        else:
            template = "%(title)s.%(ext)s"
        
        output_template = os.path.join(self.output_path, template)
        
        ydl_opts = opts()
        ydl_opts.update({
            "format": "best",
            "outtmpl": output_template,
            "merge_output_format": "mp4",
            "progress_hooks": [self.progress_hook],
        })
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'facebook_video')
                
                if custom_name:
                    safe_name = "".join(c for c in custom_name if c.isalnum() or c in (' ', '-', '_')).strip()
                    filename = f"{safe_name}.mp4" if safe_name else f"{title}.mp4"
                else:
                    filename = f"{title}.mp4"
                
                filepath = os.path.join(self.output_path, filename)
                filepath = self.check_file_exists(filepath)
                
                if filepath is None:
                    raise Exception(self.text.get('download_cancelled', 'Đã hủy tải xuống'))
                
                ydl_opts['outtmpl'] = filepath.replace(".mp4", ".%(ext)s")
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl2:
                    ydl2.download([url])
                    
            log.info("Facebook video downloaded successfully")
        except Exception as e:
            raise Exception(self.text['facebook_error'].format(error=str(e)))
    
    def progress_hook(self, d):
        if d['status'] == 'downloading':
            try:
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                if total > 0:
                    progress = downloaded / total
                    percent = int(progress * 100)
                    status = self.text['status_downloading'].format(percent=percent)
                    self.after(0, lambda p=progress, s=status: 
                             self.update_progress(0.3 + (p * 0.6), s))
            except:
                pass
        elif d['status'] == 'finished':
            self.after(0, lambda: self.update_progress(0.9, self.text['status_processing']))


if __name__ == "__main__":
    app = VideoDownloader(language='vie')
    try:
        app.iconbitmap('app/app.ico')
    except:
        pass
    app.mainloop()