
from customtkinter import CTk, CTkButton, CTkLabel, CTkEntry, CTkFrame, CTkRadioButton, StringVar, CTkProgressBar
from tkinter import messagebox, filedialog
import threading
import os
import yt_dlp
import logging
import requests
import json

logging.basicConfig(
    format="%(levelname)s: %(message)s",
    level=logging.INFO  
)
log = logging.getLogger("cytdlp")

cookie = None

def opts():
    """yt-dlp options"""
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

class VideoDownloader(CTk):
    def __init__(self, language='vie'):
        super().__init__()
        
        self.load_colors()
        self.load_language(language)
        
        self.title(self.text['app_title'])
        self.geometry("700x750")
        self.resizable(False, False)
        self.configure(fg_color=self.colors['bg_color'])
        
        self.download_mode = StringVar(value="video")
        self.platform = StringVar(value="youtube")
        self.output_path = os.path.join(os.path.expanduser("~"), "Downloads")
        
        self.create_widgets()
    
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
        "platform_label": "✿ Chọn nền tảng:",
        "youtube": "📺 YouTube",
        "tiktok": "🎵 TikTok",
        "facebook": "👥 Facebook",
        "url_label": "✿ Video URL:",
        "url_placeholder": "Dán URL vào đây ♡",
        "mode_label": "♥ Chế độ tải:",
        "video_mode": "📹 Video (Chất lượng tốt nhất)",
        "audio_mode": "🎵 Audio (MP3)",
        "save_label": "📁 Vị trí lưu:",
        "browse_btn": "Chọn",
        "ready_status": "Có thể tải rùi ♡",
        "download_btn": "♡ Tải xuống ♡",
        "downloading_btn": "Đang tải...",
        "footer": "✿ Made with love by Ellie (◕‿◕✿) ♥",
        "warning_title": "Cảnh báo",
        "warning_message": "Hãy nhập URL video!",
        "success_title": "Hoàn thành",
        "success_message": "Tải xuống thành công! ♡",
        "error_title": "Lỗi",
        "error_message": "Tải xuống thất bại:\n{error}",
        "status_start": "Bắt đầu tải xuống... ✿",
        "status_complete": "✅ Tải xong! (❁´◡`❁)",
        "status_error": "❌ Lỗi: {error}",
        "status_youtube_video": "Đang tải video YouTube... 📹",
        "status_youtube_audio": "Đang tải audio YouTube... 🎵",
        "status_tiktok_info": "Đang lấy thông tin TikTok... 🎵",
        "status_tiktok_download": "Đang tải video TikTok... 📱",
        "status_facebook": "Đang tải video Facebook... 👥",
        "status_downloading": "Đang tải... {percent}% ♡",
        "status_processing": "Đang xử lý... ✨",
        "tiktok_error_info": "Không thể lấy thông tin video TikTok",
        "tiktok_error_url": "Không tìm thấy link video",
        "tiktok_error_api": "Lỗi kết nối API: {error}",
        "tiktok_error_json": "Lỗi xử lý dữ liệu từ API",
        "tiktok_error_download": "Lỗi tải TikTok: {error}",
        "facebook_error": "Lỗi tải Facebook: {error}"
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
        
        platform_frame = CTkFrame(main_frame, fg_color=self.colors['frame_color'], 
                                 corner_radius=15, border_width=3, 
                                 border_color=self.colors['button_color'])
        platform_frame.pack(fill="x", pady=10)
        
        platform_label = CTkLabel(
            platform_frame,
            text=self.text['platform_label'],
            font=("Comic Sans MS", 13, "bold"),
            text_color=self.colors['text_color']
        )
        platform_label.pack(anchor="w", padx=15, pady=(15, 10))
        
        platform_container = CTkFrame(platform_frame, fg_color="transparent")
        platform_container.pack(fill="x", padx=15, pady=(0, 15))
        
        for platform, text in [("youtube", self.text['youtube']), 
                               ("tiktok", self.text['tiktok']), 
                               ("facebook", self.text['facebook'])]:
            radio = CTkRadioButton(
                platform_container,
                text=text,
                variable=self.platform,
                value=platform,
                font=("Comic Sans MS", 11),
                text_color=self.colors['text_color'],
                fg_color=self.colors['accent_color'],
                hover_color=self.colors['button_hover'],
                command=self.on_platform_change
            )
            radio.pack(side="left", padx=8)
        
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
    
    def on_platform_change(self):
        if self.platform.get() in ["tiktok", "facebook"]:
            self.mode_frame.pack_forget()
        else:
            self.mode_frame.pack(fill="x", pady=10, before=self.path_entry.master.master)
    
    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.output_path)
        if folder:
            self.output_path = folder
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, folder)
    
    def update_progress(self, value, status_text):
        self.progress_bar.set(value)
        self.status_label.configure(text=status_text)
        self.update_idletasks()
    
    def start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning(self.text['warning_title'], 
                                 self.text['warning_message'])
            return
        
        self.download_btn.configure(state="disabled", text=self.text['downloading_btn'])
        self.update_progress(0.1, self.text['status_start'])

        thread = threading.Thread(target=self.download_thread, args=(url,))
        thread.daemon = True
        thread.start()
    
    def download_thread(self, url):
        try:
            platform = self.platform.get()
            
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
            self.after(100, lambda: messagebox.showinfo(self.text['success_title'], 
                                                       self.text['success_message']))
        except Exception as e:
            log.error(f"Download error: {e}")
            error_msg = self.text['error_message'].format(error=str(e))
            self.after(100, lambda: self.update_progress(0, 
                      self.text['status_error'].format(error=str(e))))
            self.after(100, lambda: messagebox.showerror(self.text['error_title'], error_msg))
        finally:
            self.after(100, lambda: self.download_btn.configure(state="normal", 
                                                               text=self.text['download_btn']))
    
    def download_youtube_video(self, url):
        os.makedirs(self.output_path, exist_ok=True)
        
        ydl_opts = {
            "format": "best[height<=1080]/best",
            "outtmpl": os.path.join(self.output_path, "%(title)s.%(ext)s"),
            "merge_output_format": "mp4",
            "noplaylist": False,   
            "yesplaylist": True,
            "progress_hooks": [self.progress_hook],
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            self.after(100, lambda: self.update_progress(0.3, self.text['status_youtube_video']))
            ydl.download([url])
    
    def download_youtube_audio(self, url):
        os.makedirs(self.output_path, exist_ok=True)
        
        ydl_opts = opts()
        ydl_opts.update({
            "format": "bestaudio/best",  
            "outtmpl": os.path.join(self.output_path, "%(title)s.%(ext)s"),
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
            self.after(100, lambda: self.update_progress(0.3, self.text['status_youtube_audio']))
            ydl.download([url])
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
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
            if not safe_title:
                safe_title = f"tiktok_{video_data.get('id', 'video')}"
            filename = f"{safe_title}.mp4"
            filepath = os.path.join(self.output_path, filename)
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
        
        ydl_opts = opts()
        ydl_opts.update({
            "format": "best",
            "outtmpl": os.path.join(self.output_path, "%(title)s.%(ext)s"),
            "merge_output_format": "mp4",
            "progress_hooks": [self.progress_hook],
        })
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
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
    with open('app/app', 'r', encoding='utf-8') as f:
        lines = f.readlines()
        lang = 'vie'
        for line in lines:
            if line.startswith('language='):
                lang = line.split('=')[1].strip()
            if line.startswith('ico='):
                icon_path = line.split('=')[1].strip()
                if os.path.exists(icon_path):
                    icon = icon_path
                else:
                    icon = "app/app.ico"
    app = VideoDownloader(language=lang)
    app.iconbitmap(icon)
    app.mainloop()