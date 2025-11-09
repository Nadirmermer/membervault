"""
🎬 YouTube Member Playlist Downloader - ULTIMATE EDITION
Modern, Kullanıcı Dostu, Profesyonel Tasarım
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
# from tkinterdnd2 import DND_FILES, TkinterDnD  # Opsiyonel - yüklü değilse
import threading
import subprocess
import json
import os
import re
import time
from pathlib import Path
from datetime import datetime, timedelta
import queue

# Modern tema
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Sabitler
MAX_DISPLAY_VIDEOS = 100
VIDEO_TIMEOUT = 30
COOKIE_TEST_TIMEOUT = 15
PLAYLIST_INFO_TIMEOUT = 10

# Renk paleti - Modern ve profesyonel
COLORS = {
    'primary': '#2563eb',      # Parlak mavi
    'primary_hover': '#1d4ed8',
    'success': '#10b981',      # Yeşil
    'success_hover': '#059669',
    'warning': '#f59e0b',      # Turuncu
    'warning_hover': '#d97706',
    'danger': '#ef4444',       # Kırmızı
    'danger_hover': '#dc2626',
    'bg_dark': '#0f172a',      # Koyu arka plan
    'bg_card': '#1e293b',      # Kart arka planı
    'bg_hover': '#334155',     # Hover arka planı
    'text_primary': '#f1f5f9',
    'text_secondary': '#94a3b8',
    'border': '#334155'
}


class ModernYouTubeDownloader(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Pencere ayarları
        self.title("🎬 YouTube Playlist İndirici - Ultimate Edition")
        self.geometry("1400x900")
        self.minsize(1200, 700)
        
        # Değişkenler
        self.playlists = []
        self.all_videos = []
        self.is_downloading = False
        self.current_video_index = 0
        self.download_stats = {
            'total_videos': 0,
            'downloaded': 0,
            'failed': 0,
            'skipped': 0,
            'start_time': None,
            'last_progress_time': None,
            'last_progress_percent': 0.0
        }
        
        # Log sakla
        self.log_messages = []
        
        # Video durumları
        self.video_states = {}  # {video_id: 'pending', 'downloading', 'completed', 'failed'}
        
        # Checkpoint dosyası
        self.checkpoint_file = Path("download_progress.json")
        
        self.ytdlp_path = Path(".venv/Scripts/yt-dlp.exe")
        self.cookie_file = Path("cookies.txt")
        self.download_dir = Path.cwd()
        
        # yt-dlp kontrolü
        if not self.ytdlp_path.exists():
            alt_paths = [Path("yt-dlp.exe"), Path("yt-dlp"), Path.cwd() / "yt-dlp.exe"]
            for alt_path in alt_paths:
                if alt_path.exists():
                    self.ytdlp_path = alt_path
                    break
        
        self.progress_queue = queue.Queue()
        self.current_step = "cookie"
        
        
        # UI kurulum
        self.setup_modern_ui()
        self.check_cookie()
        self.start_progress_monitor()
    
        # yt-dlp kontrolü
        if not self.ytdlp_path.exists():
            self.after(100, lambda: messagebox.showwarning(
                "Uyarı",
                "yt-dlp bulunamadı!\n\n"
                "Lütfen .venv/Scripts/ klasörüne yt-dlp.exe dosyasını ekleyin.\n"
                "Veya sistem PATH'ine yt-dlp ekleyin."
            ))
    
    def setup_modern_ui(self):
        """Modern UI yapısı"""
        # Ana grid yapılandırması
        self.grid_columnconfigure(0, weight=0)  # Sidebar
        self.grid_columnconfigure(1, weight=1)  # Main content
        self.grid_rowconfigure(0, weight=1)
        
        # Sidebar
        self.create_sidebar()
        
        # Main content area
        self.main_content = ctk.CTkFrame(self, fg_color="transparent")
        self.main_content.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main_content.grid_columnconfigure(0, weight=1)
        self.main_content.grid_rowconfigure(0, weight=1)
        
        # İlk ekranı göster
        self.show_cookie_screen()
    
    def create_sidebar(self):
        """Modern sidebar"""
        sidebar = ctk.CTkFrame(self, width=280, corner_radius=0, fg_color=COLORS['bg_dark'])
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        
        # Logo ve başlık
        logo_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_frame.pack(pady=(30, 20), padx=20)
        
        ctk.CTkLabel(
            logo_frame,
            text="🎬",
            font=ctk.CTkFont(size=50)
        ).pack()
        
        ctk.CTkLabel(
            logo_frame,
            text="YouTube Downloader",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack()
        
        ctk.CTkLabel(
            logo_frame,
            text="Ultimate Edition",
            font=ctk.CTkFont(size=12),
            text_color=COLORS['text_secondary']
        ).pack()
        
        # Navigasyon butonları
        nav_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav_frame.pack(fill="x", padx=15, pady=20)
        
        self.nav_buttons = {}
        
        nav_items = [
            ("🍪", "Cookie", "cookie"),
            ("📋", "Playlist", "playlist"),
            ("⬇️", "İndirme", "download"),
        ]
        
        for icon, text, step in nav_items:
            btn = ctk.CTkButton(
                nav_frame,
                text=f"{icon}  {text}",
                height=50,
                font=ctk.CTkFont(size=14),
                fg_color="transparent",
                text_color=COLORS['text_secondary'],
                hover_color=COLORS['bg_hover'],
                anchor="w",
                command=lambda s=step: self.navigate_to(s)
            )
            btn.pack(fill="x", pady=3)
            self.nav_buttons[step] = btn
        
        # Versiyon ve bilgi
        info_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        info_frame.pack(side="bottom", fill="x", padx=15, pady=20)
        
        ctk.CTkLabel(
            info_frame,
            text="v3.0 Ultimate Edition",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack()
        
        ctk.CTkLabel(
            info_frame,
            text="Made with ❤️",
            font=ctk.CTkFont(size=9),
            text_color=COLORS['text_secondary']
        ).pack(pady=(5, 0))
        
        self.update_nav_active("cookie")
    
    def update_nav_active(self, active_step):
        """Navigasyon butonlarını güncelle"""
        for step, btn in self.nav_buttons.items():
            if step == active_step:
                btn.configure(
                    fg_color=COLORS['primary'],
                    text_color=COLORS['text_primary'],
                    font=ctk.CTkFont(size=14, weight="bold")
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=COLORS['text_secondary'],
                    font=ctk.CTkFont(size=14)
                )
    
    def navigate_to(self, step):
        """Sayfalar arası geçiş"""
        if step == "cookie":
            self.show_cookie_screen()
        elif step == "playlist":
            if not self.cookie_file.exists():
                messagebox.showwarning("Uyarı", "Önce cookie yüklemelisiniz!")
                return
            self.show_playlist_screen()
        elif step == "download":
            if not self.all_videos:
                messagebox.showwarning("Uyarı", "Önce playlist ekleyin!")
                return
            self.show_download_screen()
    
    
    def clear_main_content(self):
        """Ana içeriği temizle"""
        for widget in self.main_content.winfo_children():
            widget.destroy()
    
    # ========================================
    # EKRAN 1: COOKIE KURULUMU
    # ========================================
    
    def show_cookie_screen(self):
        """Modern cookie kurulum ekranı"""
        self.clear_main_content()
        self.current_step = "cookie"
        self.update_nav_active("cookie")
        
        # Ana container
        container = ctk.CTkScrollableFrame(self.main_content, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=40, pady=30)
        
        # Başlık
        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 30))
        
        ctk.CTkLabel(
            header,
            text="🍪 Cookie Kurulumu",
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            header,
            text="YouTube üye videolarını indirmek için cookie'lerinizi yükleyin",
            font=ctk.CTkFont(size=14),
            text_color=COLORS['text_secondary']
        ).pack(anchor="w", pady=(5, 0))
        
        # Cookie durumu kartı
        self.cookie_status_card = ctk.CTkFrame(container, corner_radius=15, fg_color=COLORS['bg_card'])
        self.cookie_status_card.pack(fill="x", pady=(0, 25))
        
        status_content = ctk.CTkFrame(self.cookie_status_card, fg_color="transparent")
        status_content.pack(fill="x", padx=30, pady=30)
        
        # Icon ve durum
        icon_status = ctk.CTkFrame(status_content, fg_color="transparent")
        icon_status.pack(fill="x")
        
        self.cookie_icon = ctk.CTkLabel(
            icon_status,
            text="❓",
            font=ctk.CTkFont(size=60)
        )
        self.cookie_icon.pack(side="left", padx=(0, 20))
        
        info_frame = ctk.CTkFrame(icon_status, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True)
        
        self.cookie_status_text = ctk.CTkLabel(
            info_frame,
            text="Cookie durumu kontrol ediliyor...",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS['text_primary'],
            anchor="w"
        )
        self.cookie_status_text.pack(fill="x")
        
        self.cookie_detail_text = ctk.CTkLabel(
            info_frame,
            text="",
            font=ctk.CTkFont(size=13),
            text_color=COLORS['text_secondary'],
            anchor="w",
            justify="left"
        )
        self.cookie_detail_text.pack(fill="x", pady=(5, 0))
        
        # Butonlar için alan
        self.cookie_button_frame = ctk.CTkFrame(status_content, fg_color="transparent")
        self.cookie_button_frame.pack(fill="x", pady=(20, 0))
        
        # Yöntemler
        methods_header = ctk.CTkLabel(
            container,
            text="Cookie Yükleme Yöntemleri",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS['text_primary'],
            anchor="w"
        )
        methods_header.pack(fill="x", pady=(0, 15))
        
        methods_grid = ctk.CTkFrame(container, fg_color="transparent")
        methods_grid.pack(fill="x")
        methods_grid.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Yöntem 1: Yapıştır (ÖNERİLEN)
        paste_card = ctk.CTkFrame(methods_grid, fg_color=COLORS['primary'], corner_radius=15)
        paste_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        paste_content = ctk.CTkFrame(paste_card, fg_color="transparent")
        paste_content.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(
            paste_content,
            text="✨",
            font=ctk.CTkFont(size=40)
        ).pack()
        
        ctk.CTkLabel(
            paste_content,
            text="Yapıştır",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="white"
        ).pack(pady=(10, 5))
        
        ctk.CTkLabel(
            paste_content,
            text="JSON'u direkt yapıştır\n(ÖNERİLEN)",
            font=ctk.CTkFont(size=11),
            text_color="white",
            wraplength=150,
            justify="center"
        ).pack(pady=(0, 15))
        
        ctk.CTkButton(
            paste_content,
            text="📋 Yapıştır",
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="white",
            text_color=COLORS['primary'],
            hover_color="#e0e0e0",
            command=self.paste_cookie_json
        ).pack(fill="x")
        
        # Yöntem 2: JSON
        json_card = ctk.CTkFrame(methods_grid, fg_color=COLORS['bg_card'], corner_radius=15)
        json_card.grid(row=0, column=1, sticky="nsew", padx=5)
        
        json_content = ctk.CTkFrame(json_card, fg_color="transparent")
        json_content.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(
            json_content,
            text="📄",
            font=ctk.CTkFont(size=40)
        ).pack()
        
        ctk.CTkLabel(
            json_content,
            text="JSON Dosyası",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(pady=(10, 5))
        
        ctk.CTkLabel(
            json_content,
            text="Dosyadan yükle",
            font=ctk.CTkFont(size=11),
            text_color=COLORS['text_secondary'],
            wraplength=150,
            justify="center"
        ).pack(pady=(0, 15))
        
        ctk.CTkButton(
            json_content,
            text="📂 Dosya Seç",
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary_hover'],
            command=self.import_cookie_json
        ).pack(fill="x")
        
        # Yöntem 3: TXT
        txt_card = ctk.CTkFrame(methods_grid, fg_color=COLORS['bg_card'], corner_radius=15)
        txt_card.grid(row=0, column=2, sticky="nsew", padx=(10, 0))
        
        txt_content = ctk.CTkFrame(txt_card, fg_color="transparent")
        txt_content.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(
            txt_content,
            text="📝",
            font=ctk.CTkFont(size=40)
        ).pack()
        
        ctk.CTkLabel(
            txt_content,
            text="TXT Dosyası",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(pady=(10, 5))
        
        ctk.CTkLabel(
            txt_content,
            text="Netscape formatı",
            font=ctk.CTkFont(size=11),
            text_color=COLORS['text_secondary'],
            wraplength=150,
            justify="center"
        ).pack(pady=(0, 15))
        
        ctk.CTkButton(
            txt_content,
            text="📂 Dosya Seç",
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary_hover'],
            command=self.import_cookie_txt
        ).pack(fill="x")
        
        # Sürükle-bırak alanı
        drop_frame = ctk.CTkFrame(container, corner_radius=15, fg_color=COLORS['bg_card'], border_width=2, border_color=COLORS['border'])
        drop_frame.pack(fill="x", pady=(20, 0))
        
        drop_label = ctk.CTkLabel(
            drop_frame,
            text="📥 Veya dosyayı buraya sürükleyin\n\nJSON veya TXT cookie dosyası",
            font=ctk.CTkFont(size=14),
            text_color=COLORS['text_secondary'],
            justify="center"
        )
        drop_label.pack(pady=40)
        
        # Sürükle-bırak fonksiyonu (TkinterDnD2 yüklüyse)
        # drop_frame.drop_target_register(DND_FILES)
        # drop_frame.dnd_bind('<<Drop>>', self.on_drop_cookie)
        
        # Yardım
        help_btn = ctk.CTkButton(
            container,
            text="❓ Cookie Nasıl Alınır?",
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color="transparent",
            border_width=2,
            border_color=COLORS['border'],
            hover_color=COLORS['bg_hover'],
            command=self.show_cookie_help
        )
        help_btn.pack(pady=(20, 0))
        
        # Cookie durumunu kontrol et
        self.check_cookie()
    
    
    def on_drop_cookie(self, event):
        """Sürükle-bırak cookie yükleme"""
        file_path = event.data.strip('{}')
        if file_path.endswith('.json'):
            self.import_cookie_from_path(file_path, 'json')
        elif file_path.endswith('.txt'):
            self.import_cookie_from_path(file_path, 'txt')
        else:
            messagebox.showerror("Hata", "Sadece .json veya .txt dosyaları destekleniyor!")
    
    def check_cookie(self):
        """Cookie durumunu kontrol et ve göster"""
        if not hasattr(self, 'cookie_icon'):
            return False
            
        if self.cookie_file.exists():
            try:
                with open(self.cookie_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                cookie_count = sum(1 for line in lines if line.strip() and not line.strip().startswith('#'))
                content = ''.join(lines)
                
                required_cookies = ['HSID', 'SSID', 'SID', 'APISID', 'SAPISID', 'LOGIN_INFO']
                found_cookies = [c for c in required_cookies if c in content]
                missing_cookies = [c for c in required_cookies if c not in content]
                
                # Butonları temizle
                for widget in self.cookie_button_frame.winfo_children():
                    widget.destroy()
                
                if missing_cookies:
                    # Eksik cookie
                    self.cookie_icon.configure(text="⚠️")
                    self.cookie_status_text.configure(
                        text="Cookie Eksik",
                        text_color=COLORS['warning']
                    )
                    self.cookie_detail_text.configure(
                        text=f"Toplam: {cookie_count} cookie\n✅ Bulunan: {', '.join(found_cookies) if found_cookies else 'Yok'}\n❌ Eksik: {', '.join(missing_cookies)}"
                    )
                    
                    btn_grid = ctk.CTkFrame(self.cookie_button_frame, fg_color="transparent")
                    btn_grid.pack(fill="x")
                    btn_grid.grid_columnconfigure(0, weight=1)
                    
                    ctk.CTkButton(
                        btn_grid,
                        text="🔄 Yeni Cookie Yükle",
                        height=45,
                        font=ctk.CTkFont(size=14, weight="bold"),
                        fg_color=COLORS['warning'],
                        hover_color=COLORS['warning_hover'],
                        command=self.show_cookie_screen
                    ).grid(row=0, column=0, columnspan=2, sticky="ew")
                    
                    return False
                else:
                    # Cookie tamam
                    self.cookie_icon.configure(text="✅")
                    self.cookie_status_text.configure(
                        text="Cookie Hazır",
                        text_color=COLORS['success']
                    )
                    self.cookie_detail_text.configure(
                        text=f"Toplam: {cookie_count} cookie • Tüm kritik cookie'ler mevcut"
                    )
                    
                    btn_grid = ctk.CTkFrame(self.cookie_button_frame, fg_color="transparent")
                    btn_grid.pack(fill="x")
                    btn_grid.grid_columnconfigure((0, 1, 2), weight=1)
                    
                    ctk.CTkButton(
                        btn_grid,
                        text="🔄 Değiştir",
                        height=42,
                        font=ctk.CTkFont(size=13),
                        fg_color="transparent",
                        border_width=2,
                        border_color=COLORS['border'],
                        hover_color=COLORS['bg_hover'],
                        command=self.show_cookie_screen
                    ).grid(row=0, column=0, sticky="ew", padx=(0, 5))
                    
                    ctk.CTkButton(
                        btn_grid,
                        text="🧪 Test Et",
                        height=42,
                        font=ctk.CTkFont(size=13),
                        fg_color="transparent",
                        border_width=2,
                        border_color=COLORS['border'],
                        hover_color=COLORS['bg_hover'],
                            command=self.test_cookie_connection
                    ).grid(row=0, column=1, sticky="ew", padx=5)
                        
                    ctk.CTkButton(
                        btn_grid,
                            text="▶️ Devam Et",
                        height=42,
                        font=ctk.CTkFont(size=13, weight="bold"),
                        fg_color=COLORS['success'],
                        hover_color=COLORS['success_hover'],
                        command=lambda: self.navigate_to('playlist')
                    ).grid(row=0, column=2, sticky="ew", padx=(5, 0))
                    
                    return True
            except Exception as e:
                self.cookie_icon.configure(text="❌")
                self.cookie_status_text.configure(
                    text="Cookie Hatası",
                    text_color=COLORS['danger']
                )
                self.cookie_detail_text.configure(text=f"Hata: {str(e)}")
                return False
        else:
            self.cookie_icon.configure(text="❌")
            self.cookie_status_text.configure(
                text="Cookie Bulunamadı",
                text_color=COLORS['danger']
            )
            self.cookie_detail_text.configure(text="Lütfen cookie dosyası yükleyin")
        return False
    
    def paste_cookie_json(self):
        """Cookie'yi direkt yapıştır"""
        paste_window = ctk.CTkToplevel(self)
        paste_window.title("📋 Cookie Yapıştır")
        paste_window.geometry("700x600")
        paste_window.transient(self)
        paste_window.grab_set()
        
        # Başlık
        header = ctk.CTkFrame(paste_window, fg_color=COLORS['primary'], height=80)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        ctk.CTkLabel(
            header,
            text="✨ Cookie JSON Yapıştır",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="white"
        ).pack(pady=20)
        
        # Açıklama
        info_frame = ctk.CTkFrame(paste_window, fg_color=COLORS['bg_card'])
        info_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(
            info_frame,
            text="💡 EditThisCookie uzantısından Export (Ctrl+C) yapın ve buraya yapıştırın",
            font=ctk.CTkFont(size=12),
            text_color=COLORS['text_secondary']
        ).pack(pady=10, padx=15)
        
        # Text alanı
        text_frame = ctk.CTkFrame(paste_window, fg_color="transparent")
        text_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        ctk.CTkLabel(
            text_frame,
            text="Cookie JSON:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(anchor="w", pady=(0, 5))
        
        cookie_text = ctk.CTkTextbox(
            text_frame,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=COLORS['bg_dark'],
            wrap="word"
        )
        cookie_text.pack(fill="both", expand=True)
        cookie_text.insert("1.0", "[\n  {\n    \"name\": \"...\",\n    \"value\": \"...\",\n    ...\n  }\n]")
        
        # Butonlar
        btn_frame = ctk.CTkFrame(paste_window, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        def process_paste():
            cookie_json = cookie_text.get("1.0", "end-1c").strip()
            if not cookie_json:
                messagebox.showwarning("Uyarı", "Lütfen cookie JSON'unu yapıştırın!")
                return
            
            try:
                # JSON'u parse et
                cookies = json.loads(cookie_json)
                
                # Geçici dosyaya kaydet
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
                    json.dump(cookies, f)
                    temp_path = f.name
                
                # Import et
                paste_window.destroy()
                self.import_cookie_from_path(temp_path, 'json')
                
                # Geçici dosyayı sil
                import os
                os.unlink(temp_path)
                
            except json.JSONDecodeError as e:
                messagebox.showerror("Hata", f"Geçersiz JSON formatı!\n\n{str(e)}")
            except Exception as e:
                messagebox.showerror("Hata", f"Cookie işlenemedi:\n\n{str(e)}")
        
        ctk.CTkButton(
            btn_frame,
            text="✅ Kaydet ve Kullan",
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS['success'],
            hover_color=COLORS['success_hover'],
            command=process_paste
        ).pack(side="left", expand=True, fill="x", padx=(0, 5))
        
        ctk.CTkButton(
            btn_frame,
            text="❌ İptal",
            height=45,
            font=ctk.CTkFont(size=14),
            fg_color=COLORS['danger'],
            hover_color=COLORS['danger_hover'],
            command=paste_window.destroy
        ).pack(side="left", expand=True, fill="x", padx=(5, 0))
    
    def import_cookie_json(self):
        """JSON cookie import"""
        file_path = filedialog.askopenfilename(
            title="JSON Cookie Dosyası Seçin",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file_path:
            self.import_cookie_from_path(file_path, 'json')
    
    def import_cookie_txt(self):
        """TXT cookie import"""
        file_path = filedialog.askopenfilename(
            title="Cookie TXT Dosyası Seçin",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            self.import_cookie_from_path(file_path, 'txt')
    
    def import_cookie_from_path(self, file_path, file_type):
        """Dosya yolundan cookie import et"""
        try:
            if file_type == 'json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                
                with open(self.cookie_file, 'w', encoding='utf-8') as f:
                    f.write("# Netscape HTTP Cookie File\n")
                    f.write("# This file is generated by yt-dlp. Do not edit.\n\n")
                    
                    converted_count = 0
                    for cookie in cookies:
                        if not cookie.get('name') or not cookie.get('value'):
                            continue
                        
                        domain = cookie.get('domain', '')
                        if cookie.get('hostOnly', False):
                            if domain.startswith('.'):
                                domain = domain[1:]
                        else:
                            if not domain.startswith('.'):
                                domain = '.' + domain
                        
                        flag = 'FALSE' if cookie.get('hostOnly', False) else 'TRUE'
                        path = cookie.get('path', '/')
                        secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
                        
                        expiration_date = cookie.get('expirationDate', 0)
                        if expiration_date:
                            expiration = int(float(expiration_date))
                        else:
                            expiration = 0
                        
                        name = cookie.get('name', '')
                        value = cookie.get('value', '')
                        
                        line = f"{domain}\t{flag}\t{path}\t{secure}\t{expiration}\t{name}\t{value}\n"
                        f.write(line)
                        converted_count += 1
                
                critical_cookies = ['HSID', 'SSID', 'SID', 'APISID', 'SAPISID', 'LOGIN_INFO']
                imported_names = [c.get('name', '') for c in cookies]
                found_critical = [c for c in critical_cookies if c in imported_names]
                missing_critical = [c for c in critical_cookies if c not in imported_names]
                
                status_msg = f"✅ {converted_count} cookie başarıyla import edildi!\n\n"
                if found_critical:
                    status_msg += f"✅ Kritik cookie'ler: {', '.join(found_critical)}\n"
                if missing_critical:
                    status_msg += f"⚠️ Eksik kritik cookie'ler: {', '.join(missing_critical)}\n"
                
                messagebox.showinfo("Başarılı", status_msg)
                
            else:  # txt
                import shutil
                shutil.copy(file_path, self.cookie_file)
                messagebox.showinfo("Başarılı", "✅ Cookie dosyası başarıyla yüklendi!")
            
            self.check_cookie()
            
        except Exception as e:
            messagebox.showerror("Hata", f"Cookie import edilemedi:\n{str(e)}")
    
    def test_cookie_connection(self):
        """Cookie test et"""
        test_window = ctk.CTkToplevel(self)
        test_window.title("🧪 Cookie Testi")
        test_window.geometry("500x300")
        test_window.transient(self)
        test_window.grab_set()
        
        ctk.CTkLabel(
            test_window,
            text="🧪 Cookie Test Ediliyor...",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=30)
        
        status_label = ctk.CTkLabel(
            test_window,
            text="Lütfen bekleyin...",
            font=ctk.CTkFont(size=13),
            text_color="gray"
        )
        status_label.pack(pady=20)
        
        progress = ctk.CTkProgressBar(test_window, mode="indeterminate")
        progress.pack(pady=20, padx=40, fill="x")
        progress.start()
        
        def run_test():
            try:
                test_url = "https://www.youtube.com/watch?v=z68azNOLhys"
                
                cmd = [
                    str(self.ytdlp_path),
                    "--cookies", str(self.cookie_file),
                    "--simulate",
                    "--no-warnings",
                    test_url
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=COOKIE_TEST_TIMEOUT
                )
                
                progress.stop()
                progress.pack_forget()
                
                if result.returncode == 0:
                        status_label.configure(
                        text="✅ Cookie Çalışıyor!\n\nÜye videolarına erişim sağlandı.",
                            text_color="green"
                    )
                else:
                        status_label.configure(
                        text="❌ Cookie Çalışmıyor\n\nCookie'leri yenileyin.",
                            text_color="red"
                    )
                
                        ctk.CTkButton(
                            test_window,
                    text="Tamam",
                            command=test_window.destroy
                        ).pack(pady=20)
                    
            except Exception as e:
                progress.stop()
                status_label.configure(
                    text=f"❌ Test Hatası:\n\n{str(e)}",
                    text_color="red"
                )
        
        thread = threading.Thread(target=run_test, daemon=True)
        thread.start()
    
    def show_cookie_help(self):
        """Cookie yardım penceresi"""
        help_window = ctk.CTkToplevel(self)
        help_window.title("🍪 Cookie Nasıl Alınır?")
        help_window.geometry("700x600")
        help_window.transient(self)
        
        scroll = ctk.CTkScrollableFrame(help_window)
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        help_text = """
🍪 YOUTUBE COOKIE NASIL ALINIR?

📋 Adım 1: Chrome Uzantısı Kur
1. Google Chrome'u açın
2. "EditThisCookie" uzantısını yükleyin
3. Chrome'u yeniden başlatın

📋 Adım 2: YouTube'a Giriş Yapın
1. youtube.com'a gidin
2. ÜYE OLDUĞUNUZ hesapla giriş yapın
3. Bir üye videosunu açın ve izleyebildiğinizden emin olun

📋 Adım 3: Cookie'leri Export Edin
1. EditThisCookie simgesine tıklayın (🍪)
2. "Export" butonuna tıklayın
3. JSON formatında cookie'ler panoya kopyalanacak

📋 Adım 4: JSON Dosyası Oluşturun
1. Notepad veya herhangi bir text editor açın
2. Kopyalanan JSON'u yapıştırın (Ctrl+V)
3. Dosyayı "cookies.json" olarak kaydedin

📋 Adım 5: Bu Programa Import Edin
1. "📂 JSON Dosyası Seç" butonuna tıklayın
2. Kaydettiğiniz cookies.json dosyasını seçin
3. Veya dosyayı sürükle-bırak alanına bırakın

✅ Tamamlandı!
Cookie başarıyla kurulduysa ✅ yeşil işaret göreceksiniz.

❗ ÖNEMLİ NOTLAR:
• Cookie'ler kişiseldir, kimseyle paylaşmayın
• Cookie'ler bir süre sonra sona erer, yenilemeniz gerekebilir
• Mutlaka ÜYE olduğunuz kanalın hesabıyla giriş yapın
• Eğer video indirilemiyorsa, cookie'yi yenileme zamanı gelmiş olabilir

🔒 GÜVENLİK:
Cookie'leriniz sadece bu bilgisayarda kalır, hiçbir yere gönderilmez.
"""
        
        ctk.CTkLabel(
            scroll,
            text=help_text,
            font=ctk.CTkFont(size=13),
            justify="left",
            anchor="w"
        ).pack(fill="both", padx=20, pady=20)
        
        ctk.CTkButton(
            help_window,
            text="Anladım!",
            height=40,
            command=help_window.destroy
        ).pack(pady=20)
    
    # ========================================
    # EKRAN 2-3: DİĞER EKRANLAR (DEVAM EDECEK)
    # ========================================
    
    def show_playlist_screen(self):
        """Modern playlist ekranı"""
        self.clear_main_content()
        self.current_step = "playlist"
        self.update_nav_active("playlist")
        
        # Ana container
        container = ctk.CTkFrame(self.main_content, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=40, pady=30)
        
        # Grid yapısı (2 satır, 2 sütun)
        container.grid_rowconfigure(0, weight=0)  # Header
        container.grid_rowconfigure(1, weight=1)  # Content
        container.grid_columnconfigure(0, weight=1, minsize=350)
        container.grid_columnconfigure(1, weight=2)
        
        # Başlık
        header = ctk.CTkFrame(container, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 20))
        
        ctk.CTkLabel(
            header,
            text="📋 Playlist Yönetimi",
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(side="left")
        
        # Sağ üst butonlar
        header_btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        header_btn_frame.pack(side="right")
        
        ctk.CTkButton(
            header_btn_frame,
            text="📂 Klasör Seç",
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color=COLORS['bg_card'],
            hover_color=COLORS['bg_hover'],
            command=self.select_download_folder
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            header_btn_frame,
            text="📄 TXT'den Yükle",
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color=COLORS['warning'],
            hover_color=COLORS['warning_hover'],
            command=self.import_playlists_from_txt
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            header_btn_frame,
            text="▶️ İndirmeyi Başlat",
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS['success'],
            hover_color=COLORS['success_hover'],
            command=lambda: self.navigate_to('download')
        ).pack(side="left", padx=5)
        
        # Sol panel: Playlist ekle
        left_panel = ctk.CTkFrame(container, fg_color=COLORS['bg_card'], corner_radius=15)
        left_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 15))
        
        ctk.CTkLabel(
            left_panel,
            text="➕ Playlist Ekle",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(pady=(20, 15), padx=20)
        
        # URL girişi
        url_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        url_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        ctk.CTkLabel(
            url_frame,
            text="Playlist URL:",
            font=ctk.CTkFont(size=13),
            text_color=COLORS['text_secondary']
        ).pack(anchor="w", pady=(0, 5))
        
        self.playlist_url_entry = ctk.CTkEntry(
            url_frame,
            height=45,
            font=ctk.CTkFont(size=13),
            placeholder_text="https://www.youtube.com/playlist?list=..."
        )
        self.playlist_url_entry.pack(fill="x")
        
        # Kalite seçimi
        quality_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        quality_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        ctk.CTkLabel(
            quality_frame,
            text="Video Kalitesi:",
            font=ctk.CTkFont(size=13),
            text_color=COLORS['text_secondary']
        ).pack(anchor="w", pady=(0, 5))
        
        self.quality_var = ctk.StringVar(value="best")
        quality_options = ctk.CTkFrame(quality_frame, fg_color="transparent")
        quality_options.pack(fill="x")
        
        qualities = [
            ("En İyi", "best"),
            ("1080p", "1080"),
            ("720p", "720"),
            ("480p", "480")
        ]
        
        for i, (label, value) in enumerate(qualities):
            ctk.CTkRadioButton(
                quality_options,
                text=label,
                variable=self.quality_var,
                value=value,
                font=ctk.CTkFont(size=12)
            ).pack(anchor="w", pady=2)
        
        # Thumbnail seçeneği
        thumbnail_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        thumbnail_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        self.thumbnail_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            thumbnail_frame,
            text="🖼️ Kapak Fotoğraflarını İndir",
            variable=self.thumbnail_var,
            font=ctk.CTkFont(size=13),
            checkbox_width=22,
            checkbox_height=22
        ).pack(anchor="w")
        
        # Ekle butonu
        ctk.CTkButton(
            left_panel,
            text="➕ Playlist Ekle",
            height=50,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary_hover'],
            command=self.add_playlist
        ).pack(fill="x", padx=20, pady=(0, 15))
        
        # İstatistikler
        stats_frame = ctk.CTkFrame(left_panel, fg_color=COLORS['bg_dark'], corner_radius=10)
        stats_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self.stats_label = ctk.CTkLabel(
            stats_frame,
            text="📊 İstatistikler\n\nPlaylist: 0\nVideo: 0",
            font=ctk.CTkFont(size=13),
            justify="left"
        )
        self.stats_label.pack(pady=15, padx=15)
        
        # Sağ panel: Playlist listesi
        right_panel = ctk.CTkFrame(container, fg_color=COLORS['bg_card'], corner_radius=15)
        right_panel.grid(row=1, column=1, sticky="nsew")
        
        ctk.CTkLabel(
            right_panel,
            text="📋 Eklenen Playlist'ler",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(pady=(20, 10), padx=20)
        
        # Playlist scroll alanı
        self.playlist_scroll = ctk.CTkScrollableFrame(
            right_panel,
            fg_color="transparent"
        )
        self.playlist_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # Eğer playlist varsa göster
        self.update_playlist_display()
        self.update_stats_display()
    
    def show_download_screen(self):
        """Modern indirme ekranı"""
        self.clear_main_content()
        self.current_step = "download"
        self.update_nav_active("download")
        
        if not self.all_videos:
            messagebox.showwarning("Uyarı", "Önce playlist ekleyin!")
            self.navigate_to('playlist')
            return
        
        # Ana container
        container = ctk.CTkFrame(self.main_content, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=40, pady=30)
        
        # Grid yapısı (2 satır, 2 sütun: sol video listesi, sağ progress/log)
        container.grid_rowconfigure(0, weight=0)  # Header
        container.grid_rowconfigure(1, weight=1)  # Content
        container.grid_columnconfigure(0, weight=1, minsize=400)  # Video listesi
        container.grid_columnconfigure(1, weight=2)  # Progress/Log
        
        # Başlık
        header = ctk.CTkFrame(container, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 20))
        
        # Sol: Başlık
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", fill="both", expand=True)
        
        ctk.CTkLabel(
            title_frame,
            text="⬇️ Video İndirme",
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(anchor="w")
        
        # Klasör bilgisi
        folder_text = str(self.download_dir)
        if len(folder_text) > 50:
            folder_text = "..." + folder_text[-47:]
        
        self.folder_label = ctk.CTkLabel(
            title_frame,
            text=f"📂 {folder_text}",
            font=ctk.CTkFont(size=12),
            text_color=COLORS['text_secondary']
        )
        self.folder_label.pack(anchor="w", pady=(3, 0))
        
        # Sağ: Kontrol butonları
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right")
        
        ctk.CTkButton(
            btn_frame,
            text="📂 Klasör Değiştir",
            height=40,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS['bg_card'],
            hover_color=COLORS['bg_hover'],
            command=self.change_download_folder
        ).pack(side="left", padx=5)
        
        self.download_btn = ctk.CTkButton(
            btn_frame,
            text="▶️ Başlat",
            height=45,
            width=140,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS['success'],
            hover_color=COLORS['success_hover'],
            command=self.start_download
        )
        self.download_btn.pack(side="left", padx=5)
        
        self.retry_btn = ctk.CTkButton(
            btn_frame,
            text="🔄 Başarısızları Tekrarla",
            height=40,
            width=160,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS['warning'],
            hover_color=COLORS['warning_hover'],
            command=self.retry_failed
        )
        self.retry_btn.pack(side="left", padx=5)
        
        self.stop_btn = ctk.CTkButton(
            btn_frame,
            text="⏸️ Durdur",
            height=45,
            width=100,
            font=ctk.CTkFont(size=14),
            fg_color=COLORS['danger'],
            hover_color=COLORS['danger_hover'],
            command=self.stop_download,
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=5)
        
        # Sol panel: Video listesi
        left_panel = ctk.CTkFrame(container, fg_color=COLORS['bg_card'], corner_radius=15)
        left_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 15))
        
        ctk.CTkLabel(
            left_panel,
            text="📹 Video Listesi",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(pady=(20, 10), padx=20)
        
        # Video scroll alanı
        self.video_list_scroll = ctk.CTkScrollableFrame(
            left_panel,
            fg_color="transparent"
        )
        self.video_list_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Videoları listele
        self.update_video_list_display()
        
        # Sağ panel: Progress ve Log
        right_panel = ctk.CTkFrame(container, fg_color=COLORS['bg_card'], corner_radius=15)
        right_panel.grid(row=1, column=1, sticky="nsew")
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_rowconfigure(3, weight=1)
        
        # İlerleme istatistikleri
        stats_frame = ctk.CTkFrame(right_panel, fg_color=COLORS['bg_dark'], corner_radius=10)
        stats_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        stats_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        # Stat kartları
        stat_items = [
            ("📊 Toplam", "total_stat", "0"),
            ("✅ İndirilen", "downloaded_stat", "0"),
            ("❌ Başarısız", "failed_stat", "0"),
            ("⏭️ Atlanan", "skipped_stat", "0")
        ]
        
        for i, (label, var_name, default) in enumerate(stat_items):
            stat_card = ctk.CTkFrame(stats_frame, fg_color="transparent")
            stat_card.grid(row=0, column=i, padx=10, pady=15)
            
            ctk.CTkLabel(
                stat_card,
                text=label,
                font=ctk.CTkFont(size=11),
                text_color=COLORS['text_secondary']
            ).pack()
            
            stat_label = ctk.CTkLabel(
                stat_card,
                text=default,
                font=ctk.CTkFont(size=24, weight="bold"),
                text_color=COLORS['text_primary']
            )
            stat_label.pack()
            setattr(self, var_name, stat_label)
        
        # İlerleme çubuğu
        progress_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        progress_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 15))
        
        self.progress_label = ctk.CTkLabel(
            progress_frame,
            text="Hazır",
            font=ctk.CTkFont(size=14),
            text_color=COLORS['text_secondary']
        )
        self.progress_label.pack(anchor="w", pady=(0, 5))
        
        self.progress_bar = ctk.CTkProgressBar(progress_frame, height=20)
        self.progress_bar.pack(fill="x")
        self.progress_bar.set(0)
        
        self.progress_detail = ctk.CTkLabel(
            progress_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=COLORS['text_secondary']
        )
        self.progress_detail.pack(anchor="w", pady=(5, 0))
        
        # Log alanı
        log_header = ctk.CTkFrame(right_panel, fg_color="transparent")
        log_header.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 10))
        
        ctk.CTkLabel(
            log_header,
            text="📝 İndirme Logları",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(side="left")
        
        ctk.CTkButton(
            log_header,
            text="🗑️ Temizle",
            height=30,
            width=100,
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            hover_color=COLORS['bg_hover'],
            command=self.clear_log
        ).pack(side="right")
        
        self.log_text = ctk.CTkTextbox(
            right_panel,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=COLORS['bg_dark'],
            wrap="word"
        )
        self.log_text.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 20))
        
        # Önceki log'ları geri yükle
        if self.log_messages:
            for msg in self.log_messages:
                self.log_text.insert('end', msg + '\n')
            self.log_text.see('end')
        else:
            self.log_message("💡 İndirmeye başlamak için '▶️ Başlat' butonuna tıklayın.")
    
    # ========================================
    # PLAYLIST İŞLEMLERİ
    # ========================================
    
    def add_playlist(self):
        """Playlist ekle"""
        url = self.playlist_url_entry.get().strip()
        if not url:
            messagebox.showwarning("Uyarı", "Lütfen playlist URL'si girin!")
            return
        
        # URL kontrolü
        if 'youtube.com' not in url or 'list=' not in url:
            messagebox.showwarning("Uyarı", "Geçerli bir YouTube playlist URL'si girin!")
            return
        
        # Loading göster
        loading = ctk.CTkToplevel(self)
        loading.title("Yükleniyor...")
        loading.geometry("400x200")
        loading.transient(self)
        loading.grab_set()
        
        ctk.CTkLabel(
            loading,
            text="⏳ Playlist bilgileri alınıyor...",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=30)
        
        progress = ctk.CTkProgressBar(loading, mode="indeterminate")
        progress.pack(pady=20, padx=40, fill="x")
        progress.start()
        
        def fetch_playlist():
            try:
                # Playlist bilgilerini JSON formatında al
                cmd = [
                    str(self.ytdlp_path),
                    "--cookies", str(self.cookie_file),
                    "--flat-playlist",
                    "--dump-json",
                    "--no-warnings",
                    url
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60  # 60 saniye timeout
                )
                
                if result.returncode != 0:
                    error_msg = result.stderr if result.stderr else "Bilinmeyen hata"
                    self.after(0, lambda: loading.destroy())
                    self.after(0, lambda: messagebox.showerror("Hata", f"Playlist alınamadı:\n\n{error_msg[:200]}"))
                    return
                
                # JSON satırlarını parse et
                videos = []
                playlist_title = None
                
                for line in result.stdout.strip().split('\n'):
                    if not line.strip():
                        continue
                    try:
                        video_data = json.loads(line)
                        
                        # Playlist başlığını al (ilk satırdan)
                        if playlist_title is None and 'playlist_title' in video_data:
                            playlist_title = video_data['playlist_title']
                        
                        # Video bilgilerini ekle
                        if 'id' in video_data and 'title' in video_data:
                            videos.append({
                                'title': video_data['title'],
                                'id': video_data['id'],
                                'url': f"https://www.youtube.com/watch?v={video_data['id']}"
                            })
                    except json.JSONDecodeError:
                        continue
                
                if not videos:
                    self.after(0, lambda: loading.destroy())
                    self.after(0, lambda: messagebox.showwarning("Uyarı", "Playlist'te video bulunamadı!\n\nLütfen cookie'nizin geçerli olduğundan emin olun."))
                    return
                
                # Playlist'i ekle
                if not playlist_title:
                    playlist_title = f"Playlist {len(self.playlists) + 1}"
                
                playlist_info = {
                        'url': url,
                        'title': playlist_title,
                        'video_count': len(videos),
                    'quality': self.quality_var.get()
                }
                
                self.playlists.append(playlist_info)
                self.all_videos.extend(videos)
                
                self.after(0, lambda: loading.destroy())
                self.after(0, lambda: messagebox.showinfo("Başarılı", f"✅ {len(videos)} video eklendi!\n\nPlaylist: {playlist_title}"))
                self.after(0, self.update_playlist_display)
                self.after(0, self.update_stats_display)
                self.after(0, lambda: self.playlist_url_entry.delete(0, 'end'))
                
            except subprocess.TimeoutExpired:
                self.after(0, lambda: loading.destroy())
                self.after(0, lambda: messagebox.showerror("Hata", "Zaman aşımı! Playlist çok büyük veya bağlantı yavaş."))
            except Exception as e:
                self.after(0, lambda: loading.destroy())
                self.after(0, lambda: messagebox.showerror("Hata", f"Playlist eklenemedi:\n\n{str(e)}"))
        
        thread = threading.Thread(target=fetch_playlist, daemon=True)
        thread.start()
    
    def update_playlist_display(self):
        """Playlist listesini güncelle"""
        if not hasattr(self, 'playlist_scroll'):
            return
        
        # Temizle
        for widget in self.playlist_scroll.winfo_children():
            widget.destroy()
        
        if not self.playlists:
            ctk.CTkLabel(
                self.playlist_scroll,
                text="Henüz playlist eklenmedi",
                font=ctk.CTkFont(size=13),
                text_color=COLORS['text_secondary']
            ).pack(pady=20)
            return
        
        # Her playlist için kart
        for i, pl in enumerate(self.playlists):
            card = ctk.CTkFrame(self.playlist_scroll, fg_color=COLORS['bg_dark'], corner_radius=10)
            card.pack(fill="x", pady=5, padx=5)
            
            content = ctk.CTkFrame(card, fg_color="transparent")
            content.pack(fill="x", padx=15, pady=15)
            
            # Başlık
            ctk.CTkLabel(
                content,
                text=f"📋 {pl['title']}",
                font=ctk.CTkFont(size=15, weight="bold"),
                text_color=COLORS['text_primary'],
                anchor="w"
            ).pack(fill="x")
            
            # Detaylar
            details_text = f"🎥 {pl['video_count']} video • 📺 {pl['quality']}"
            ctk.CTkLabel(
                content,
                text=details_text,
                font=ctk.CTkFont(size=11),
                text_color=COLORS['text_secondary'],
                anchor="w"
            ).pack(fill="x", pady=(3, 0))
            
            # Sil butonu
            ctk.CTkButton(
                content,
                text="🗑️ Sil",
                height=28,
                width=80,
                font=ctk.CTkFont(size=11),
                fg_color=COLORS['danger'],
                hover_color=COLORS['danger_hover'],
                command=lambda idx=i: self.remove_playlist(idx)
            ).pack(anchor="e", pady=(8, 0))
    
    def update_stats_display(self):
        """İstatistikleri güncelle"""
        if hasattr(self, 'stats_label'):
            self.stats_label.configure(
                text=f"📊 İstatistikler\n\nPlaylist: {len(self.playlists)}\nVideo: {len(self.all_videos)}"
            )
    
    def remove_playlist(self, index):
        """Playlist sil"""
        if messagebox.askyesno("Onay", "Bu playlist'i silmek istediğinizden emin misiniz?"):
            # Video sayısını al
            video_count = self.playlists[index]['video_count']
            
            # Playlist'i sil
            del self.playlists[index]
            
            # İlgili videoları sil
            self.all_videos = self.all_videos[video_count:]
            
            self.update_playlist_display()
            self.update_stats_display()
    
    def select_download_folder(self):
        """İndirme klasörü seç"""
        folder = filedialog.askdirectory(title="İndirme Klasörü Seçin")
        if folder:
            self.download_dir = Path(folder)
            messagebox.showinfo("Başarılı", f"İndirme klasörü:\n{folder}")
    
    def import_playlists_from_txt(self):
        """TXT dosyasından playlist'leri yükle"""
        file_path = filedialog.askopenfilename(
            title="Playlist TXT Dosyası Seçin",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            if not urls:
                messagebox.showwarning("Uyarı", "TXT dosyasında playlist URL'si bulunamadı!")
                return
            
            # Loading göster
            loading = ctk.CTkToplevel(self)
            loading.title("Yükleniyor...")
            loading.geometry("450x250")
            loading.transient(self)
            loading.grab_set()
            
            ctk.CTkLabel(
                loading,
                text="⏳ Playlist'ler yükleniyor...",
                font=ctk.CTkFont(size=18, weight="bold")
            ).pack(pady=30)
            
            progress_label = ctk.CTkLabel(
                loading,
                text=f"0 / {len(urls)} playlist",
                font=ctk.CTkFont(size=14)
            )
            progress_label.pack(pady=10)
            
            progress = ctk.CTkProgressBar(loading, mode="determinate")
            progress.pack(pady=20, padx=40, fill="x")
            progress.set(0)
            
            def load_playlists():
                success_count = 0
                total_videos = 0
                
                for idx, url in enumerate(urls):
                    if not self.winfo_exists():
                        break
                    
                    # Progress güncelle
                    self.after(0, lambda i=idx: progress_label.configure(text=f"{i+1} / {len(urls)} playlist"))
                    self.after(0, lambda p=(idx+1)/len(urls): progress.set(p))
                    
                    try:
                        # Playlist bilgilerini al
                        cmd = [
                            str(self.ytdlp_path),
                            "--cookies", str(self.cookie_file),
                            "--flat-playlist",
                            "--dump-json",
                            "--no-warnings",
                            url
                        ]
                        
                        result = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            timeout=60
                        )
                        
                        if result.returncode != 0:
                            continue
                        
                        # Videoları parse et
                        videos = []
                        playlist_title = None
                        
                        for line in result.stdout.strip().split('\n'):
                            if not line.strip():
                                continue
                            try:
                                video_data = json.loads(line)
                                if playlist_title is None and 'playlist_title' in video_data:
                                    playlist_title = video_data['playlist_title']
                                if 'id' in video_data and 'title' in video_data:
                                    videos.append({
                                        'title': video_data['title'],
                                        'id': video_data['id'],
                                        'url': f"https://www.youtube.com/watch?v={video_data['id']}"
                                    })
                            except json.JSONDecodeError:
                                continue
                        
                        if videos:
                            if not playlist_title:
                                playlist_title = f"Playlist {len(self.playlists) + 1}"
                            
                            playlist_info = {
                                'url': url,
                                'title': playlist_title,
                                'video_count': len(videos),
                                'quality': self.quality_var.get() if hasattr(self, 'quality_var') else 'best',
                                'download_thumbnails': self.thumbnail_var.get() if hasattr(self, 'thumbnail_var') else True
                            }
                            
                            self.playlists.append(playlist_info)
                            self.all_videos.extend(videos)
                            success_count += 1
                            total_videos += len(videos)
                    
                    except Exception:
                        continue
                
                # Tamamlandı
                self.after(0, lambda: loading.destroy())
                self.after(0, lambda: messagebox.showinfo(
                    "Başarılı",
                    f"✅ {success_count} playlist yüklendi!\n\n"
                    f"📊 Toplam {total_videos} video"
                ))
                self.after(0, self.update_playlist_display)
                self.after(0, self.update_stats_display)
            
            thread = threading.Thread(target=load_playlists, daemon=True)
            thread.start()
                    
        except Exception as e:
            messagebox.showerror("Hata", f"TXT dosyası okunamadı:\n\n{str(e)}")
    
    # ========================================
    # İNDİRME İŞLEMLERİ
    # ========================================
    
    def start_download(self):
        """İndirmeyi başlat"""
        if self.is_downloading:
            messagebox.showwarning("Uyarı", "İndirme zaten devam ediyor!")
            return
        
        if not self.all_videos:
            messagebox.showwarning("Uyarı", "İndirilecek video yok!")
            return
        
        # Klasörü kontrol et
        if not self.download_dir.exists():
            try:
                self.download_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Hata", f"İndirme klasörü oluşturulamadı:\n{str(e)}")
                return
        
        self.is_downloading = True
        self.current_video_index = 0
        
        # Checkpoint'i yükle veya yeni oluştur
        self.load_checkpoint()
        
        # Klasörü tara ve zaten indirilen videoları işaretle
        self.scan_existing_files()
        
        # Kaç video atlanacak hesapla
        already_completed = sum(1 for s in self.video_states.values() if s == 'completed')
        videos_to_download = len(self.all_videos) - already_completed
        
        # İstatistikleri sıfırla
        self.download_stats = {
            'total_videos': len(self.all_videos),
            'downloaded': already_completed,  # Zaten tamamlananları say
            'failed': 0,
            'skipped': 0,
            'start_time': time.time()
        }
        
        # UI güncelle
        self.download_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        
        if hasattr(self, 'total_stat'):
            self.total_stat.configure(text=str(self.download_stats['total_videos']))
            self.downloaded_stat.configure(text=str(already_completed))
            self.failed_stat.configure(text="0")
            self.skipped_stat.configure(text="0")
        
        # Video listesini güncelle
        if hasattr(self, 'video_list_scroll'):
            self.update_video_list_display()
        
        self.log_message("🚀 İNDİRME BAŞLIYOR")
        self.log_message(f"{'='*70}")
        self.log_message(f"� Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log_message(f"� Klasör: {self.download_dir}")
        self.log_message(f"🎥 Kalite: {self.playlists[0]['quality'] if self.playlists else 'best'}")
        self.log_message(f"\n� VİDEO İSTATİSTİKLERİ:")
        self.log_message(f"   📺 Toplam Video: {len(self.all_videos)}")
        self.log_message(f"   ✅ Zaten İndirilmiş: {already_completed}")
        self.log_message(f"   📥 İndirilecek: {videos_to_download}")
        
        if already_completed > 0:
            skip_percent = (already_completed / len(self.all_videos)) * 100
            self.log_message(f"   💡 Atlanma Oranı: %{skip_percent:.1f}")
        
        # Playlist bilgileri
        if self.playlists:
            self.log_message(f"\n📋 PLAYLIST LİSTESİ:")
            for i, pl in enumerate(self.playlists, 1):
                self.log_message(f"   {i}. {pl.get('title', 'Bilinmeyen Playlist')} ({pl.get('video_count', 0)} video)")
        
        # Thumbnail bilgisi
        if hasattr(self, 'thumbnail_var'):
            if self.thumbnail_var.get():
                self.log_message(f"\n🖼️ Kapak fotoğrafları: İndirilecek")
            else:
                self.log_message(f"\n🖼️ Kapak fotoğrafları: İndirilmeyecek")
        
        self.log_message(f"{'='*70}\n")
        
        # Eğer hepsi zaten indirildiyse uyar
        if videos_to_download == 0:
            self.log_message("✅ TÜM VİDEOLAR ZATEN İNDİRİLMİŞ!")
            self.log_message("💡 İndirilecek yeni video yok.\n")
            self.is_downloading = False
            self.download_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            messagebox.showinfo("Bilgi", 
                f"Tüm videolar zaten indirilmiş!\n\n"
                f"✅ Toplam: {len(self.all_videos)} video\n"
                f"📁 Klasör: {self.download_dir}")
            return
        
        # İndirme thread'i başlat
        thread = threading.Thread(target=self.download_worker, daemon=True)
        thread.start()
    
    def stop_download(self):
        """İndirmeyi durdur"""
        if messagebox.askyesno("Onay", "İndirmeyi durdurmak istediğinizden emin misiniz?"):
            self.is_downloading = False
            self.log_message("\n⏸️ İndirme kullanıcı tarafından durduruldu!")
            
            if hasattr(self, 'download_btn'):
                self.download_btn.configure(state="normal")
                self.stop_btn.configure(state="disabled")
    
    def download_worker(self):
        """İndirme worker thread - videolar sırayla indirilir"""
        failed_videos = []  # Başarısız videoları kaydet
        
        for i, video in enumerate(self.all_videos):
            if not self.is_downloading:
                break
            
            self.current_video_index = i + 1
            video_id = video['id']
            video_title = video['title']
            
            # Hedef dosya adını oluştur (önce kontrol için)
            safe_title = self.sanitize_filename(video_title)
            target_file = self.download_dir / f"{safe_title}.mp4"
            
            # 1. Checkpoint'ten completed kontrolü
            if self.video_states.get(video_id) == 'completed':
                self.log_message(f"\n[{self.current_video_index}/{len(self.all_videos)}] ⏭️ Atlanıyor (önceden indirilmiş): {video_title[:60]}...")
                self.download_stats['skipped'] += 1
                if hasattr(self, 'skipped_stat'):
                    self.after(0, lambda: self.skipped_stat.configure(
                        text=str(self.download_stats['skipped'])
                    ))
                continue
            
            # 2. KAPSAMLI Dosya varlık kontrolü - farklı formatlar ve adlandırmalar
            existing_file = self.find_existing_video_file(video_id, safe_title)
            if existing_file:
                file_size = existing_file.stat().st_size
                size_mb = file_size / (1024 * 1024)
                self.log_message(f"\n[{self.current_video_index}/{len(self.all_videos)}] ⏭️ ATLANACAK (dosya mevcut)")
                self.log_message(f"   📝 Video: {video_title[:60]}...")
                self.log_message(f"   📁 Dosya: {existing_file.name}")
                self.log_message(f"   💾 Boyut: {size_mb:.1f} MB")
                
                self.video_states[video_id] = 'completed'
                self.download_stats['skipped'] += 1
                
                if hasattr(self, 'skipped_stat'):
                    self.after(0, lambda: self.skipped_stat.configure(
                        text=str(self.download_stats['skipped'])
                    ))
                if hasattr(self, 'downloaded_stat'):
                    current_completed = sum(1 for s in self.video_states.values() if s == 'completed')
                    self.after(0, lambda cc=current_completed: self.downloaded_stat.configure(text=str(cc)))
                
                self.after(0, self.update_video_list_display)
                self.save_checkpoint()
                continue
            
            try:
                # Video durumunu güncelle
                self.video_states[video_id] = 'downloading'
                self.after(0, self.update_video_list_display)
                
                # Progress güncelle
                progress = i / len(self.all_videos)
                self.after(0, lambda p=progress: self.progress_bar.set(p))
                
                # Süre tahmini
                if self.download_stats['start_time'] and i > 0:
                    elapsed = time.time() - self.download_stats['start_time']
                    avg_time = elapsed / i
                    remaining = avg_time * (len(self.all_videos) - i)
                    remaining_str = str(timedelta(seconds=int(remaining)))
                    detail_text = f"Tahmini kalan süre: {remaining_str}"
                else:
                    detail_text = "Süre hesaplanıyor..."
                
                self.after(0, lambda: self.progress_label.configure(
                    text=f"📥 İndiriliyor: {self.current_video_index}/{len(self.all_videos)}"
                ))
                self.after(0, lambda d=detail_text: self.progress_detail.configure(text=d))
                
                self.log_message(f"\n{'='*70}")
                self.log_message(f"[{self.current_video_index}/{len(self.all_videos)}] 📥 İNDİRİLİYOR")
                self.log_message(f"{'='*70}")
                self.log_message(f"📝 Başlık: {video['title'][:60]}{'...' if len(video['title']) > 60 else ''}")
                self.log_message(f"🆔 Video ID: {video_id}")
                self.log_message(f"🔗 URL: {video['url']}")
                
                # Klasörü kontrol et ve oluştur
                if not self.download_dir.exists():
                    self.download_dir.mkdir(parents=True, exist_ok=True)
                    self.log_message(f"📁 Klasör oluşturuldu: {self.download_dir}")
                
                # Kalite ayarı - ESNEKLEŞTİRİLMİŞ FORMAT
                quality = self.playlists[0]['quality'] if self.playlists else 'best'
                if quality == 'best':
                    # En esnek format seçenekleri - her durumda çalışır
                    format_str = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best'
                else:
                    # Kalite seçili ise de esnek olsun
                    format_str = f'bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best'
                
                self.log_message(f"🎥 Kalite: {quality}")
                
                # İndirme komutu
                cmd = [
                    str(self.ytdlp_path),
                    "--cookies", str(self.cookie_file),
                    "-f", format_str,
                    "--merge-output-format", "mp4",
                    "-o", str(self.download_dir / "%(title)s.%(ext)s"),
                    "--no-playlist",
                    "--no-mtime",  # Dosya zamanını değiştirme
                    "--newline",  # Progress için
                    "--progress",  # Progress göster
                    video['url']
                ]
                
                # Thumbnail ekle - videoya göm ama klasörde bırakma
                if hasattr(self, 'thumbnail_var') and self.thumbnail_var.get():
                    cmd.extend([
                        "--write-thumbnail",
                        "--embed-thumbnail",
                        "--convert-thumbnails", "jpg",
                    ])
                    self.log_message("🖼️ Kapak fotoğrafı: Videoya gömülecek")
                
                self.log_message(f"⏳ İndirme başladı...")
                download_start = time.time()
                
                # Gerçek zamanlı progress tracking
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    bufsize=1
                )
                
                # Progress izleme
                last_progress_update = time.time()
                stdout_lines = []
                timeout_seconds = VIDEO_TIMEOUT * 60  # 30 dakika
                start_time = time.time()
                error_detected = False
                
                while True:
                    # Timeout kontrolü
                    if time.time() - start_time > timeout_seconds:
                        process.kill()
                        raise subprocess.TimeoutExpired(cmd, timeout_seconds)
                    
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    
                    if line:
                        stdout_lines.append(line)
                        line_stripped = line.strip()
                        
                        # Hızlı hata tespiti - 5 saniye içinde ERROR görürse hemen sonlandır
                        if 'ERROR:' in line_stripped and time.time() - start_time < 5:
                            error_detected = True
                            self.log_message(f"⚠️ Hızlı hata tespiti: {line_stripped[:100]}")
                            # Biraz daha çıktı topla
                            time.sleep(0.5)
                            while True:
                                extra_line = process.stdout.readline()
                                if not extra_line:
                                    break
                                stdout_lines.append(extra_line)
                                if len(stdout_lines) > 50:  # Fazla bekleme
                                    break
                            process.kill()
                            break
                        
                        # yt-dlp progress satırlarını yakala
                        if '[download]' in line_stripped and '%' in line_stripped:
                            # Progress bilgilerini parse et
                            progress_info = self.parse_download_progress(line_stripped)
                            if progress_info and time.time() - last_progress_update > 0.5:  # 0.5 saniyede bir güncelle
                                last_progress_update = time.time()
                                percent = progress_info.get('percent', 0)
                                speed = progress_info.get('speed', '')
                                eta = progress_info.get('eta', '')
                                
                                # UI'yi güncelle
                                detail_text = f"Video İlerlemesi: {percent:.1f}%"
                                if speed:
                                    detail_text += f" | Hız: {speed}"
                                if eta:
                                    detail_text += f" | Kalan: {eta}"
                                
                                self.after(0, lambda d=detail_text: self.progress_detail.configure(text=d))
                
                process.wait()
                download_time = time.time() - download_start
                
                # Sonucu kontrol et
                result_returncode = process.returncode
                result_output = ''.join(stdout_lines)
                
                if result_returncode == 0:
                    self.download_stats['downloaded'] += 1
                    self.video_states[video_id] = 'completed'
                    self.log_message(f"✅ BAŞARILI! (Süre: {int(download_time)}s)")
                    
                    # Thumbnail dosyasını temizle (videoya gömülmüş olmalı)
                    if hasattr(self, 'thumbnail_var') and self.thumbnail_var.get():
                        self.cleanup_thumbnails(safe_title)
                    
                    self.after(0, lambda: self.downloaded_stat.configure(
                        text=str(self.download_stats['downloaded'])
                    ))
                else:
                    self.download_stats['failed'] += 1
                    self.video_states[video_id] = 'failed'
                    
                    # Hata mesajını detaylı logla
                    error_lines = result_output.split('\n')
                    
                    # Son anlamlı hata satırını bul
                    relevant_error = "Bilinmeyen hata"
                    for line in reversed(error_lines):
                        line = line.strip()
                        if line and not line.startswith('[') and 'ERROR' in line.upper():
                            relevant_error = line
                            break
                    
                    # Format hatası ise basit format ile tekrar dene
                    if 'Requested format is not available' in relevant_error and quality == 'best':
                        self.log_message(f"⚠️ Format hatası, basit format ile tekrar deneniyor...")
                        
                        # Basit format komutu
                        simple_cmd = [
                            str(self.ytdlp_path),
                            "--cookies", str(self.cookie_file),
                            "-f", "best",  # En basit format
                            "-o", str(self.download_dir / "%(title)s.%(ext)s"),
                            "--no-playlist",
                            "--no-mtime",
                            "--newline",
                            "--progress",
                            video['url']
                        ]
                        
                        # Thumbnail ekle
                        if hasattr(self, 'thumbnail_var') and self.thumbnail_var.get():
                            simple_cmd.extend([
                                "--write-thumbnail",
                                "--embed-thumbnail",
                                "--convert-thumbnails", "jpg",
                            ])
                        
                        try:
                            # Basit format ile tekrar dene
                            simple_process = subprocess.Popen(
                                simple_cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                text=True,
                                encoding='utf-8',
                                errors='replace',
                                bufsize=1
                            )
                            
                            simple_output = []
                            while True:
                                line = simple_process.stdout.readline()
                                if not line and simple_process.poll() is not None:
                                    break
                                if line:
                                    simple_output.append(line)
                            
                            simple_process.wait()
                            
                            if simple_process.returncode == 0:
                                # Başarılı!
                                self.download_stats['failed'] -= 1  # Geri al
                                self.download_stats['downloaded'] += 1
                                self.video_states[video_id] = 'completed'
                                self.log_message(f"✅ BAŞARILI! (Basit format ile)")
                                
                                # Thumbnail temizle
                                if hasattr(self, 'thumbnail_var') and self.thumbnail_var.get():
                                    self.cleanup_thumbnails(safe_title)
                                
                                self.after(0, lambda: self.downloaded_stat.configure(
                                    text=str(self.download_stats['downloaded'])
                                ))
                                self.after(0, lambda: self.failed_stat.configure(
                                    text=str(self.download_stats['failed'])
                                ))
                                self.after(0, self.update_video_list_display)
                                self.save_checkpoint()
                                continue  # Sonraki videoya geç
                            else:
                                self.log_message(f"⚠️ Basit format ile de başarısız")
                        except Exception as e:
                            self.log_message(f"⚠️ Basit format denemesi başarısız: {str(e)[:50]}")
                    
                    # Gerçekten başarısız
                    self.log_message(f"❌ BAŞARISIZ!")
                    self.log_message(f"⚠️ Hata: {relevant_error[:150]}")
                    
                    # Başarısız videoyu kaydet
                    failed_videos.append({
                        'index': self.current_video_index,
                        'title': video['title'],
                        'id': video_id,
                        'url': video['url'],
                        'error': relevant_error[:200]
                    })
                    
                    self.after(0, lambda: self.failed_stat.configure(
                        text=str(self.download_stats['failed'])
                    ))
                
                # Video listesini güncelle
                self.after(0, self.update_video_list_display)
                
                # Checkpoint kaydet
                self.save_checkpoint()
                
            except subprocess.TimeoutExpired:
                self.download_stats['failed'] += 1
                self.video_states[video_id] = 'failed'
                error_msg = f"Zaman aşımı! Video {VIDEO_TIMEOUT} dakikada indirilemedi."
                self.log_message(f"❌ BAŞARISIZ!")
                self.log_message(f"⚠️ {error_msg}")
                
                failed_videos.append({
                    'index': self.current_video_index,
                    'title': video['title'],
                    'id': video_id,
                    'url': video['url'],
                    'error': error_msg
                })
                
                self.after(0, lambda: self.failed_stat.configure(
                    text=str(self.download_stats['failed'])
                ))
                self.after(0, self.update_video_list_display)
                self.save_checkpoint()
                
            except Exception as e:
                self.download_stats['failed'] += 1
                self.video_states[video_id] = 'failed'
                error_msg = str(e)
                self.log_message(f"❌ BAŞARISIZ!")
                self.log_message(f"⚠️ Hata: {error_msg[:150]}")
                
                failed_videos.append({
                    'index': self.current_video_index,
                    'title': video['title'],
                    'id': video_id,
                    'url': video['url'],
                    'error': error_msg[:200]
                })
                
                self.after(0, lambda: self.failed_stat.configure(
                    text=str(self.download_stats['failed'])
                ))
                self.after(0, self.update_video_list_display)
                self.save_checkpoint()
        
        # İndirme tamamlandı
        self.is_downloading = False
        
        elapsed = time.time() - self.download_stats['start_time']
        elapsed_str = str(timedelta(seconds=int(elapsed)))
        
        self.log_message(f"\n\n{'='*70}")
        self.log_message(f"🎉 İNDİRME TAMAMLANDI!")
        self.log_message(f"{'='*70}")
        self.log_message(f"⏱️ Toplam Süre: {elapsed_str}")
        self.log_message(f"📊 Toplam Video: {self.download_stats['total_videos']}")
        self.log_message(f"✅ Başarılı: {self.download_stats['downloaded']}")
        self.log_message(f"❌ Başarısız: {self.download_stats['failed']}")
        self.log_message(f"📂 Klasör: {self.download_dir}")
        
        # Başarısız videoların detaylı listesi
        if failed_videos:
            self.log_message(f"\n{'='*70}")
            self.log_message(f"❌ BAŞARISIZ VİDEOLAR ({len(failed_videos)} adet):")
            self.log_message(f"{'='*70}")
            for i, fv in enumerate(failed_videos, 1):
                self.log_message(f"\n{i}. [{fv['index']}] {fv['title'][:60]}")
                self.log_message(f"   ID: {fv['id']}")
                self.log_message(f"   URL: {fv['url']}")
                self.log_message(f"   Hata: {fv['error'][:150]}")
            
            # Başarısız videoları dosyaya kaydet
            failed_log_file = self.download_dir / "failed_videos.log"
            try:
                with open(failed_log_file, 'w', encoding='utf-8') as f:
                    f.write(f"BAŞARISIZ VİDEOLAR - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"{'='*70}\n\n")
                    for i, fv in enumerate(failed_videos, 1):
                        f.write(f"{i}. [{fv['index']}] {fv['title']}\n")
                        f.write(f"   Video ID: {fv['id']}\n")
                        f.write(f"   URL: {fv['url']}\n")
                        f.write(f"   Hata: {fv['error']}\n\n")
                self.log_message(f"\n💾 Başarısız videolar kaydedildi: {failed_log_file}")
            except Exception as e:
                self.log_message(f"\n⚠️ Log dosyası kaydedilemedi: {str(e)}")
        
        # Son checkpoint
        self.save_checkpoint()
        
        self.after(0, lambda: self.download_btn.configure(state="normal"))
        self.after(0, lambda: self.stop_btn.configure(state="disabled"))
        
        # Başarısız varsa retry butonunu vurgula
        failed_count = self.download_stats['failed']
        if failed_count > 0:
            self.after(0, lambda: self.retry_btn.configure(
                text=f"🔄 {failed_count} Başarısız Videoyu Tekrarla"
            ))
        
        self.after(0, lambda: messagebox.showinfo("Tamamlandı", 
            f"İndirme tamamlandı!\n\n"
            f"✅ Başarılı: {self.download_stats['downloaded']}\n"
            f"❌ Başarısız: {self.download_stats['failed']}\n"
            f"⏱️ Süre: {elapsed_str}\n\n"
            f"{'💡 Başarısız videolar için:\n• 🔄 butonuna tıklayarak tekrar deneyin\n• failed_videos.log dosyasını kontrol edin' if failed_count > 0 else '🎉 Tüm videolar başarıyla indirildi!'}"
        ))
    
    def update_video_list_display(self):
        """Video listesini güncelle"""
        if not hasattr(self, 'video_list_scroll'):
            return
        
        # Temizle
        for widget in self.video_list_scroll.winfo_children():
            widget.destroy()
        
        # Her video için kart
        for i, video in enumerate(self.all_videos):
            video_id = video['id']
            state = self.video_states.get(video_id, 'pending')
            
            # Duruma göre renk
            if state == 'downloading':
                fg_color = COLORS['primary']
                icon = "⏬"
                status_text = "İndiriliyor..."
            elif state == 'completed':
                fg_color = COLORS['success']
                icon = "✅"
                status_text = "Tamamlandı"
            elif state == 'failed':
                fg_color = COLORS['danger']
                icon = "❌"
                status_text = "Başarısız"
            else:  # pending
                fg_color = COLORS['bg_dark']
                icon = "⏸️"
                status_text = "Bekliyor"
            
            card = ctk.CTkFrame(self.video_list_scroll, fg_color=fg_color, corner_radius=8)
            card.pack(fill="x", pady=3, padx=5)
            
            content = ctk.CTkFrame(card, fg_color="transparent")
            content.pack(fill="x", padx=10, pady=8)
            
            # Sıra ve icon
            top_row = ctk.CTkFrame(content, fg_color="transparent")
            top_row.pack(fill="x")
            
            ctk.CTkLabel(
                top_row,
                text=f"{icon} {i+1}/{len(self.all_videos)}",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="white" if state in ['downloading', 'completed', 'failed'] else COLORS['text_primary']
            ).pack(side="left")
            
            ctk.CTkLabel(
                top_row,
                text=status_text,
                font=ctk.CTkFont(size=10),
                text_color="white" if state in ['downloading', 'completed', 'failed'] else COLORS['text_secondary']
            ).pack(side="right")
            
            # Başlık
            title = video['title'][:50] + "..." if len(video['title']) > 50 else video['title']
            ctk.CTkLabel(
                content,
                text=title,
                font=ctk.CTkFont(size=10),
                text_color="white" if state in ['downloading', 'completed', 'failed'] else COLORS['text_primary'],
                anchor="w",
                justify="left"
            ).pack(fill="x", pady=(3, 0))
    
    def load_checkpoint(self):
        """Checkpoint'i yükle - önceki indirme durumunu kontrol eder"""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Aynı playlist'ler mi kontrol et
                saved_video_ids = set(data.get('video_ids', []))
                current_video_ids = set(v['id'] for v in self.all_videos)
                
                if saved_video_ids == current_video_ids:
                    # Checkpoint'ten durumları yükle
                    self.video_states = data.get('video_states', {})
                    
                    # İstatistikleri hesapla
                    completed = sum(1 for s in self.video_states.values() if s == 'completed')
                    failed = sum(1 for s in self.video_states.values() if s == 'failed')
                    pending = len(self.all_videos) - completed - failed
                    
                    self.log_message("📥 Önceki indirme durumu yüklendi!")
                    self.log_message(f"   📅 Kayıt Tarihi: {data.get('last_updated', 'Bilinmiyor')}")
                    self.log_message(f"   📊 Toplam: {len(self.all_videos)} video")
                    self.log_message(f"   ✅ Tamamlanmış: {completed}")
                    self.log_message(f"   ❌ Başarısız: {failed}")
                    self.log_message(f"   ⏸️ Kalan: {pending}")
                    
                    if completed > 0:
                        self.log_message(f"   💡 {completed} video zaten indirilmiş, atlanacak\n")
                    else:
                        self.log_message("")
                    
                    return
                else:
                    # Farklı playlist'ler, yeni checkpoint oluştur
                    self.log_message("⚠️ Farklı playlist seti algılandı, yeni checkpoint oluşturuluyor\n")
            except json.JSONDecodeError:
                self.log_message(f"⚠️ Checkpoint bozuk, yeni checkpoint oluşturuluyor\n")
            except Exception as e:
                self.log_message(f"⚠️ Checkpoint yüklenemedi: {str(e)}\n")
        
        # Checkpoint yoksa veya yüklenemezse, tüm videoları pending yap
        self.video_states = {}
        for video in self.all_videos:
            self.video_states[video['id']] = 'pending'
    
    def save_checkpoint(self):
        """Checkpoint'i kaydet - ilerlemeyi saklar"""
        try:
            # İstatistikleri hesapla
            completed_count = sum(1 for s in self.video_states.values() if s == 'completed')
            failed_count = sum(1 for s in self.video_states.values() if s == 'failed')
            pending_count = len(self.all_videos) - completed_count - failed_count
            
            data = {
                'video_ids': [v['id'] for v in self.all_videos],
                'video_states': self.video_states,
                'download_dir': str(self.download_dir),
                'timestamp': time.time(),
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'statistics': {
                    'total': len(self.all_videos),
                    'completed': completed_count,
                    'failed': failed_count,
                    'pending': pending_count
                },
                'playlists': [
                    {
                        'url': pl['url'],
                        'title': pl.get('title', 'Bilinmeyen Playlist')
                    }
                    for pl in self.playlists
                ]
            }
            
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            # Checkpoint kaydedilemezse sessizce devam et
            pass
    
    def cleanup_thumbnails(self, video_title):
        """İndirme sonrası thumbnail dosyalarını temizle"""
        try:
            # Olası thumbnail uzantıları
            thumbnail_exts = ['.jpg', '.jpeg', '.png', '.webp']
            
            for ext in thumbnail_exts:
                thumb_file = self.download_dir / f"{video_title}{ext}"
                if thumb_file.exists():
                    thumb_file.unlink()
                    self.log_message(f"   🧹 Thumbnail temizlendi: {thumb_file.name}")
        except Exception as e:
            # Thumbnail temizlenemezse sessizce devam et
            pass
    
    def scan_existing_files(self):
        """Klasördeki mevcut dosyaları tara ve video ID'leri ile eşleştir - GELİŞTİRİLMİŞ"""
        if not self.download_dir.exists():
            return
        
        self.log_message("🔍 Mevcut klasör taranıyor...")
        self.log_message(f"   📂 Konum: {self.download_dir}\n")
        
        # Klasördeki tüm video dosyaları
        existing_files = []
        video_extensions = ['.mp4', '.mkv', '.webm', '.avi', '.flv', '.mov', '.m4a']
        
        for ext in video_extensions:
            for file_path in self.download_dir.glob(f"*{ext}"):
                try:
                    # Sadece 500KB'dan büyük dosyaları geçerli say (çok küçük dosyalar hatalı)
                    file_size = file_path.stat().st_size
                    if file_size < 512 * 1024:  # 500 KB
                        continue
                    
                    file_stem = file_path.stem
                    # Dosya adını normalize et (küçük harf, fazla boşlukları temizle)
                    normalized_name = ' '.join(file_stem.lower().split())
                    
                    existing_files.append({
                        'path': file_path,
                        'size': file_size,
                        'name': file_path.name,
                        'stem': file_stem,
                        'normalized': normalized_name
                    })
                except:
                    continue
        
        self.log_message(f"   📊 Klasörde {len(existing_files)} geçerli video dosyası bulundu\n")
        
        if len(existing_files) == 0:
            self.log_message("📝 Klasör boş, tüm videolar indirilecek...\n")
            return
        
        skipped_count = 0
        skipped_videos = []
        
        for video in self.all_videos:
            video_id = video['id']
            
            # Zaten completed olarak işaretli olanları atla
            if self.video_states.get(video_id) == 'completed':
                skipped_count += 1
                continue
            
            # Video başlığını temizle ve normalize et
            video_title = video['title']
            clean_title = self.sanitize_filename(video_title)
            normalized_title = ' '.join(clean_title.lower().split())
            
            # Video ID'yi lowercase yap
            video_id_lower = video_id.lower()
            
            # Dosya eşleşmesi ara
            found = False
            matched_file = None
            match_reason = ""
            
            for file_info in existing_files:
                file_stem = file_info['stem']
                file_normalized = file_info['normalized']
                
                # 1. Video ID eşleşmesi (en güvenilir)
                if video_id_lower in file_normalized or video_id in file_stem:
                    found = True
                    matched_file = file_info
                    match_reason = "Video ID eşleşmesi"
                    break
                
                # 2. Tam başlık eşleşmesi
                if normalized_title == file_normalized:
                    found = True
                    matched_file = file_info
                    match_reason = "Tam başlık eşleşmesi"
                    break
                
                # 3. Başlık dosya adında tam olarak geçiyor
                if normalized_title in file_normalized:
                    found = True
                    matched_file = file_info
                    match_reason = "Başlık dosya adında"
                    break
                
                # 4. Dosya adı başlıkta tam olarak geçiyor
                if file_normalized in normalized_title:
                    found = True
                    matched_file = file_info
                    match_reason = "Dosya adı başlıkta"
                    break
                
                # 5. Uzunluk kontrolü ile kısmi eşleşme (en az 15 karakter ve %70 benzerlik)
                if len(normalized_title) >= 15 and len(file_normalized) >= 15:
                    # Ortak kelimeler
                    title_words = set(normalized_title.split())
                    file_words = set(file_normalized.split())
                    common_words = title_words & file_words
                    
                    # En az 3 ortak kelime ve %70 benzerlik
                    if len(common_words) >= 3:
                        similarity = len(common_words) / max(len(title_words), len(file_words))
                        if similarity >= 0.7:
                            found = True
                            matched_file = file_info
                            match_reason = f"Kelime benzerliği (%{int(similarity*100)})"
                            break
            
            if found and matched_file:
                self.video_states[video_id] = 'completed'
                skipped_count += 1
                size_mb = matched_file['size'] / (1024 * 1024)
                skipped_videos.append({
                    'title': video_title[:55],
                    'file': matched_file['name'][:40],
                    'size': size_mb,
                    'reason': match_reason
                })
        
        if skipped_count > 0:
            self.log_message(f"✅ {skipped_count} video zaten indirilmiş, atlanacak:\n")
            
            # İlk 15 videoyu göster
            display_count = min(15, len(skipped_videos))
            for i, sv in enumerate(skipped_videos[:display_count], 1):
                self.log_message(f"   {i:2d}. {sv['title']}...")
                self.log_message(f"       📁 {sv['file']}... ({sv['size']:.1f} MB) [{sv['reason']}]")
            
            if len(skipped_videos) > display_count:
                self.log_message(f"\n   ... ve {len(skipped_videos) - display_count} video daha")
            
            self.log_message(f"\n💡 Toplam {len(self.all_videos)} videodan {skipped_count} tanesi atlanacak")
            self.log_message(f"📥 {len(self.all_videos) - skipped_count} yeni video indirilecek\n")
            
            self.save_checkpoint()
            
            # İstatistikleri güncelle
            if hasattr(self, 'downloaded_stat'):
                self.downloaded_stat.configure(text=str(skipped_count))
            if hasattr(self, 'skipped_stat'):
                self.skipped_stat.configure(text=str(skipped_count))
        else:
            self.log_message("📝 Tüm videolar yeni, hepsi indirilecek...\n")
    
    def sanitize_filename(self, filename):
        """Dosya adını temizle ve normalize et"""
        # Windows için geçersiz karakterleri kaldır
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '')
        
        # Birden fazla boşluğu tek boşluğa çevir
        filename = ' '.join(filename.split())
        
        # Başındaki ve sonundaki boşlukları kaldır
        filename = filename.strip()
        
        # Nokta ile biten dosya adlarını düzelt (Windows sorunu)
        while filename.endswith('.'):
            filename = filename[:-1].strip()
        
        return filename
    
    def find_existing_video_file(self, video_id, expected_filename):
        """
        Klasörde video dosyasını ara - çok kapsamlı kontrol
        Video ID, dosya adı, benzerlik ile kontrol yapar
        """
        if not self.download_dir.exists():
            return None
        
        video_extensions = ['.mp4', '.mkv', '.webm', '.avi', '.flv', '.mov', '.m4a']
        min_file_size = 512 * 1024  # 500 KB - bundan küçük dosyalar hatalı kabul edilir
        
        # Normalize edilmiş arama terimleri
        expected_normalized = ' '.join(expected_filename.lower().split())
        video_id_lower = video_id.lower()
        
        # Tüm video dosyalarını tara
        for ext in video_extensions:
            for file_path in self.download_dir.glob(f"*{ext}"):
                try:
                    # Boyut kontrolü
                    file_size = file_path.stat().st_size
                    if file_size < min_file_size:
                        continue
                    
                    file_stem = file_path.stem
                    file_normalized = ' '.join(file_stem.lower().split())
                    
                    # Kontrol 1: Video ID eşleşmesi (en güvenilir)
                    if video_id_lower in file_normalized or video_id in file_stem:
                        return file_path
                    
                    # Kontrol 2: Tam dosya adı eşleşmesi
                    if expected_normalized == file_normalized:
                        return file_path
                    
                    # Kontrol 3: Beklenen ad dosya adında
                    if len(expected_normalized) > 10 and expected_normalized in file_normalized:
                        return file_path
                    
                    # Kontrol 4: Dosya adı beklenen adda
                    if len(file_normalized) > 10 and file_normalized in expected_normalized:
                        return file_path
                    
                    # Kontrol 5: Kelime bazlı benzerlik (güçlü eşleşme)
                    if len(expected_normalized) >= 15 and len(file_normalized) >= 15:
                        expected_words = set(expected_normalized.split())
                        file_words = set(file_normalized.split())
                        
                        # Ortak kelimeleri say
                        common_words = expected_words & file_words
                        
                        # En az 4 ortak kelime ve %75 benzerlik
                        if len(common_words) >= 4:
                            similarity = len(common_words) / max(len(expected_words), len(file_words))
                            if similarity >= 0.75:
                                return file_path
                        
                        # Veya çok kısa başlıklar için en az 2 ortak kelime ve %85 benzerlik
                        elif len(common_words) >= 2:
                            similarity = len(common_words) / max(len(expected_words), len(file_words))
                            if similarity >= 0.85:
                                return file_path
                    
                except Exception:
                    continue
        
        return None
    
    def parse_download_progress(self, line):
        """yt-dlp progress satırını parse et"""
        try:
            # [download]  45.2% of 125.5MiB at 2.5MiB/s ETA 00:24
            import re
            
            # Yüzde bilgisi
            percent_match = re.search(r'(\d+\.?\d*)%', line)
            percent = float(percent_match.group(1)) if percent_match else 0
            
            # Hız bilgisi
            speed_match = re.search(r'at\s+([\d.]+\s*[KMG]iB/s)', line)
            speed = speed_match.group(1) if speed_match else ''
            
            # Kalan süre
            eta_match = re.search(r'ETA\s+(\d+:\d+)', line)
            eta = eta_match.group(1) if eta_match else ''
            
            return {
                'percent': percent,
                'speed': speed,
                'eta': eta
            }
        except:
            return None
    
    def retry_failed(self):
        """Başarısız videoları tekrar indir"""
        if self.is_downloading:
            messagebox.showwarning("Uyarı", "İndirme devam ediyor!")
            return
        
        # Başarısız videoları bul
        failed_count = sum(1 for s in self.video_states.values() if s == 'failed')
        
        if failed_count == 0:
            messagebox.showinfo("Bilgi", "Başarısız video yok!")
            return
        
        if not messagebox.askyesno("Onay", f"{failed_count} başarısız video tekrar indirilecek. Devam edilsin mi?"):
            return
        
        # Başarısız videoları pending yap
        for video_id, state in self.video_states.items():
            if state == 'failed':
                self.video_states[video_id] = 'pending'
        
        self.log_message(f"\n🔄 {failed_count} başarısız video yeniden indirilecek...\n")
        
        # İndirmeyi başlat
        self.is_downloading = True
        self.current_video_index = 0
        
        self.download_stats = {
            'total_videos': failed_count,
            'downloaded': sum(1 for s in self.video_states.values() if s == 'completed'),
            'failed': 0,
            'skipped': 0,
            'start_time': time.time()
        }
        
        # UI güncelle
        if hasattr(self, 'download_btn'):
            self.download_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
        
        if hasattr(self, 'video_list_scroll'):
            self.update_video_list_display()
        
        # İndirme thread'i başlat
        thread = threading.Thread(target=self.download_worker, daemon=True)
        thread.start()
    
    def change_download_folder(self):
        """İndirme klasörünü değiştir"""
        folder = filedialog.askdirectory(title="İndirme Klasörü Seçin", initialdir=self.download_dir)
        if folder:
            self.download_dir = Path(folder)
            
            # Klasör label'ını güncelle
            if hasattr(self, 'folder_label'):
                folder_text = str(self.download_dir)
                if len(folder_text) > 50:
                    folder_text = "..." + folder_text[-47:]
                self.folder_label.configure(text=f"📂 {folder_text}")
            
            self.log_message(f"\n📂 İndirme klasörü değiştirildi: {self.download_dir}")
    
    def log_message(self, message):
        """Log mesajı ekle ve otomatik olarak dosyaya kaydet"""
        # Log'u sakla
        self.log_messages.append(message)
        
        # Ekranda göster
        if hasattr(self, 'log_text'):
            self.log_text.insert('end', message + '\n')
            self.log_text.see('end')
        
        # Otomatik dosya kaydı (opsiyonel)
        try:
            log_file = self.download_dir / "download.log"
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(message + '\n')
        except:
            pass  # Hata olursa sessizce devam et
    
    def clear_log(self):
        """Log'u temizle"""
        self.log_messages = []
        if hasattr(self, 'log_text'):
            self.log_text.delete('1.0', 'end')
            self.log_message("💡 Log temizlendi.")
    
    def save_full_log(self):
        """Tam log dosyasını kaydet"""
        try:
            log_file = self.download_dir / f"download_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write("="*70 + "\n")
                f.write(f"YOUTUBE DOWNLOADER LOG - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*70 + "\n\n")
                for msg in self.log_messages:
                    f.write(msg + '\n')
            self.log_message(f"\n💾 Log dosyası kaydedildi: {log_file}")
            messagebox.showinfo("Başarılı", f"Log dosyası kaydedildi:\n{log_file}")
        except Exception as e:
            messagebox.showerror("Hata", f"Log kaydedilemedi:\n{str(e)}")
    
    def start_progress_monitor(self):
        """Progress monitörü"""
        def monitor():
            try:
                while not self.progress_queue.empty():
                    self.progress_queue.get_nowait()
            except:
                pass
            self.after(100, monitor)
        monitor()
    

if __name__ == "__main__":
    app = ModernYouTubeDownloader()
    app.mainloop()
