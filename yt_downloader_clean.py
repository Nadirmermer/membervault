"""
🔐 MemberVault - YouTube Üyelik İçerik İndiricisi V4.0
═══════════════════════════════════════════════════════════

YouTube kanal üyeliklerinizdeki özel içerikleri arşivleyin!

Özellikler:
✓ 3 Adımlı basit süreç (Cookie → Playlist → Download)
✓ Akıllı dosya kontrolü (mevcut videoları otomatik atla)
✓ Accordion video listesi (her playlist altında videoları göster)
✓ Her video için ayrı progress bar
✓ Modern, temiz, responsive UI
✓ Otomatik thumbnail temizleme
✓ Hata yönetimi ve tekrar deneme
✓ Kompakt log alanı

Kullanım:
1. Cookie'lerinizi yapıştırın (EditThisCookie ile)
2. Playlist/video linklerini ekleyin
3. Klasör seçin ve indirmeyi başlatın

Not: İnternet kesilirse veya hata olursa, program devam eder.
     Mevcut videolar tekrar indirilmez (akıllı atlama).
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import json
import subprocess
import threading
import queue
import time
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# ═══════════════════════════════════════════════════════════════════════════
# TEMA VE SABITLER
# ═══════════════════════════════════════════════════════════════════════════

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Zaman aşımı ayarları
VIDEO_TIMEOUT = 60  # Video indirme timeout (saniye)
PLAYLIST_TIMEOUT = 30  # Playlist bilgisi timeout
MIN_FILE_SIZE = 500 * 1024  # 500 KB - daha küçük dosyalar geçersiz

# Renk paleti
COLORS = {
    'primary': '#3b82f6',      # Mavi
    'success': '#10b981',      # Yeşil
    'warning': '#f59e0b',      # Turuncu
    'danger': '#ef4444',       # Kırmızı
    'bg_dark': '#0f172a',      # Koyu arka plan
    'bg_card': '#1e293b',      # Kart arka planı
    'bg_hover': '#334155',     # Hover arka plan
    'text_primary': '#f1f5f9', # Ana yazı
    'text_secondary': '#94a3b8', # İkincil yazı
    'border': '#475569'        # Kenarlık
}

# ═══════════════════════════════════════════════════════════════════════════
# ANA UYGULAMA SINIFI
# ═══════════════════════════════════════════════════════════════════════════

class YouTubeDownloader(ctk.CTk):
    """
    YouTube üye video indirici - Temiz ve basit
    
    Attributes:
        current_step: Hangi adımda olduğumuzu gösterir (0: Cookie, 1: Playlist, 2: Download)
        playlists: Eklenen playlist'lerin listesi
        all_videos: Tüm videoların listesi
        video_states: Her videonun durumu (pending/downloading/completed/failed)
        is_downloading: İndirme devam ediyor mu?
        download_stats: İndirme istatistikleri
    """
    
    def __init__(self):
        super().__init__()
        
        # ─────────────────────────────────────────────────────────────────
        # Pencere Ayarları
        # ─────────────────────────────────────────────────────────────────
        self.title("🔐 MemberVault - YouTube Üyelik İçerik İndiricisi v4.0")
        self.geometry("1400x850")
        self.minsize(1200, 700)
        
        # ─────────────────────────────────────────────────────────────────
        # Değişkenler
        # ─────────────────────────────────────────────────────────────────
        self.current_step = 0
        self.cookie_file = Path("cookies.txt")
        self.download_dir = Path.cwd() / "Videolar"
        self.ytdlp_path = self._find_ytdlp()
        self.checkpoint_file = Path("download_checkpoint.json")
        
        # Playlist ve video verileri
        self.playlists: List[Dict] = []
        self.all_videos: List[Dict] = []
        self.video_states: Dict[str, str] = {}
        
        # İndirme durumu
        self.is_downloading = False
        self.is_paused = False  # Duraklama durumu
        self.current_video_index = 0
        self.download_folder = None
        self.download_stats = {
            'total': 0,
            'downloaded': 0,
            'failed': 0,
            'skipped': 0,
            'start_time': None
        }
        
        # Her video için progress tracking
        self.video_progress: Dict[str, Dict] = {}  # {video_id: {'progress': 0, 'speed': '', 'eta': ''}}
        self.current_downloading_id = None
        
        # Thread-safe queue
        self.progress_queue = queue.Queue()
        
        # Log
        self.log_messages: List[str] = []
        self.log_file = Path("downloader_log.txt")
        self.init_log_file()
        
        # ─────────────────────────────────────────────────────────────────
        # UI Kurulum
        # ─────────────────────────────────────────────────────────────────
        self.setup_ui()
        
        # Checkpoint yükle (kaldığımız yerden devam)
        self.load_checkpoint()
        
        self.show_step(0)
        self.start_progress_monitor()
        
        # yt-dlp kontrolü
        if not self.ytdlp_path:
            self.after(100, lambda: messagebox.showwarning(
                "Uyarı",
                "⚠️ yt-dlp bulunamadı!\n\n"
                "Lütfen yükleyin:\n"
                "pip install yt-dlp\n\n"
                "veya yt-dlp.exe dosyasını bu klasöre koyun."
            ))
    
    # ═══════════════════════════════════════════════════════════════════════
    # YARDIMCI FONKSİYONLAR
    # ═══════════════════════════════════════════════════════════════════════
    
    def init_log_file(self):
        """Log dosyasını başlat"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*80}\n")
                f.write(f"Yeni Oturum Başlatıldı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{'='*80}\n\n")
        except Exception as e:
            print(f"Log dosyası oluşturulamadı: {e}")
    
    def log_to_file(self, message: str, level: str = "INFO"):
        """Mesajı dosyaya kaydet"""
        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] [{level.upper()}] {message}\n")
        except:
            pass  # Sessizce geç
    
    def save_checkpoint(self):
        """Mevcut durumu kaydet (kaldığımız yerden devam için)"""
        try:
            checkpoint_data = {
                'timestamp': datetime.now().isoformat(),
                'current_step': self.current_step,
                'playlists': self.playlists,
                'all_videos': self.all_videos,
                'video_states': self.video_states,
                'download_folder': str(self.download_folder) if self.download_folder else None,
                'download_stats': self.download_stats
            }
            
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
            
            self.log_to_file("Checkpoint kaydedildi", "DEBUG")
        except Exception as e:
            self.log_to_file(f"Checkpoint kaydetme hatası: {e}", "ERROR")
    
    def load_checkpoint(self):
        """Önceki durumu yükle"""
        if not self.checkpoint_file.exists():
            return
        
        try:
            with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 24 saatten eski checkpoint'leri yükleme
            checkpoint_time = datetime.fromisoformat(data['timestamp'])
            if (datetime.now() - checkpoint_time).total_seconds() > 86400:  # 24 saat
                self.log_to_file("Checkpoint çok eski, yüklenmedi", "INFO")
                return
            
            # Kullanıcıya sor
            if messagebox.askyesno(
                "Kaldığımız Yerden Devam",
                f"Önceki oturum bulundu!\n\n"
                f"Tarih: {checkpoint_time.strftime('%Y-%m-%d %H:%M')}\n"
                f"Playlist: {len(data.get('playlists', []))}\n"
                f"Video: {len(data.get('all_videos', []))}\n\n"
                f"Kaldığımız yerden devam etmek ister misiniz?"
            ):
                self.current_step = data.get('current_step', 0)
                self.playlists = data.get('playlists', [])
                self.all_videos = data.get('all_videos', [])
                self.video_states = data.get('video_states', {})
                self.download_stats = data.get('download_stats', self.download_stats)
                
                folder_path = data.get('download_folder')
                if folder_path:
                    self.download_folder = Path(folder_path)
                
                self.log_to_file("Checkpoint yüklendi, devam ediliyor", "SUCCESS")
                messagebox.showinfo("✅ Başarılı", "Önceki oturum yüklendi!\n\nKaldığımız yerden devam edebilirsiniz.")
        
        except Exception as e:
            self.log_to_file(f"Checkpoint yükleme hatası: {e}", "ERROR")
    
    def _find_ytdlp(self) -> Optional[Path]:
        """yt-dlp yolunu bul"""
        # Önce yerel klasörde ara
        local_paths = [
            Path(".venv/Scripts/yt-dlp.exe"),
            Path("yt-dlp.exe"),
            Path("yt-dlp"),
        ]
        
        for path in local_paths:
            if path.exists():
                return path
        
        # PATH'te ara (Windows)
        try:
            result = subprocess.run(
                ['where', 'yt-dlp'],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            if result.returncode == 0:
                return Path(result.stdout.strip().split('\n')[0])
        except:
            pass
        
        return None
    
    def sanitize_filename(self, filename: str) -> str:
        """Dosya adını Windows için güvenli hale getir"""
        # Geçersiz karakterleri kaldır
        invalid = '<>:"/\\|?*'
        for char in invalid:
            filename = filename.replace(char, '')
        
        # Fazla boşlukları temizle
        filename = ' '.join(filename.split())
        filename = filename.strip()
        
        # Nokta ile bitmemelidir
        while filename.endswith('.'):
            filename = filename[:-1].strip()
        
        return filename or "video"
    
    def format_time(self, seconds: float) -> str:
        """Saniyeyi okunabilir formata çevir (HH:MM:SS)"""
        return str(timedelta(seconds=int(seconds)))
    
    def format_size(self, bytes_size: int) -> str:
        """Byte'ı okunabilir formata çevir (KB, MB, GB)"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024
        return f"{bytes_size:.1f} PB"
    
    def log(self, message: str, level: str = "info"):
        """
        Log mesajı ekle - Hem UI'da hem dosyada
        
        Args:
            message: Log mesajı
            level: Log seviyesi (info, warning, error, success)
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Icon ekle
        icon = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '❌',
            'success': '✅'
        }.get(level, 'ℹ️')
        
        formatted = f"[{timestamp}] {icon} {message}"
        self.log_messages.append(formatted)
        
        # UI'da göster
        if hasattr(self, 'log_text'):
            self.log_text.configure(state="normal")
            self.log_text.insert("end", formatted + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        
        # Dosyaya kaydet
        self.log_to_file(message, level.upper())
    
    # ═══════════════════════════════════════════════════════════════════════
    # UI KURULUM
    # ═══════════════════════════════════════════════════════════════════════
    
    def setup_ui(self):
        """Ana UI yapısını oluştur"""
        # Grid yapılandırması
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Header
        self.grid_rowconfigure(1, weight=1)  # Content
        self.grid_rowconfigure(2, weight=0)  # Footer
        
        # Header
        self.create_header()
        
        # Content area
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)
        
        # Footer
        self.create_footer()
    
    def create_header(self):
        """Üst başlık alanı - Logo ve adım göstergeleri"""
        header = ctk.CTkFrame(self, height=100, fg_color=COLORS['bg_card'], corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(1, weight=1)
        
        # Sol: Logo
        logo_frame = ctk.CTkFrame(header, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=30, pady=20, sticky="w")
        
        ctk.CTkLabel(
            logo_frame,
            text="🎬 YouTube Downloader",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(side="left", padx=10)
        
        ctk.CTkLabel(
            logo_frame,
            text="V4 Clean",
            font=ctk.CTkFont(size=14),
            text_color=COLORS['text_secondary']
        ).pack(side="left")
        
        # Orta: Adım göstergeleri
        self.create_step_indicators(header)
    
    def create_step_indicators(self, parent):
        """Adım göstergeleri (1→2→3)"""
        steps_frame = ctk.CTkFrame(parent, fg_color="transparent")
        steps_frame.grid(row=0, column=1, pady=20)
        
        self.step_dots = []
        self.step_labels = []
        steps = [
            ("🍪", "Cookie"),
            ("📋", "Playlist"),
            ("⬇️", "İndirme")
        ]
        
        for i, (icon, text) in enumerate(steps):
            # Container
            step_container = ctk.CTkFrame(steps_frame, fg_color="transparent")
            step_container.grid(row=0, column=i*2, padx=10)
            
            # Dot
            dot = ctk.CTkLabel(
                step_container,
                text="●",
                font=ctk.CTkFont(size=24),
                text_color=COLORS['text_secondary']
            )
            dot.pack()
            self.step_dots.append(dot)
            
            # Label
            label = ctk.CTkLabel(
                step_container,
                text=f"{icon} {text}",
                font=ctk.CTkFont(size=11),
                text_color=COLORS['text_secondary']
            )
            label.pack(pady=(5, 0))
            self.step_labels.append(label)
            
            # Bağlantı çizgisi (sonuncu hariç)
            if i < len(steps) - 1:
                line = ctk.CTkLabel(
                    steps_frame,
                    text="━━━",
                    font=ctk.CTkFont(size=16),
                    text_color=COLORS['text_secondary']
                )
                line.grid(row=0, column=i*2+1)
    
    def create_footer(self):
        """Alt footer alanı"""
        footer = ctk.CTkFrame(self, height=50, fg_color=COLORS['bg_card'], corner_radius=0)
        footer.grid(row=2, column=0, sticky="ew")
        footer.grid_propagate(False)
        
        ctk.CTkLabel(
            footer,
            text="Made with ❤️ | Sade, Hızlı, Güvenilir | github.com/nadirmermer",
            font=ctk.CTkFont(size=11),
            text_color=COLORS['text_secondary']
        ).pack(pady=15)
    
    def update_step_indicators(self):
        """Adım göstergelerini güncelle"""
        for i, (dot, label) in enumerate(zip(self.step_dots, self.step_labels)):
            if i < self.current_step:
                # Tamamlanmış
                dot.configure(text_color=COLORS['success'])
                label.configure(text_color=COLORS['success'])
            elif i == self.current_step:
                # Aktif
                dot.configure(text_color=COLORS['primary'])
                label.configure(text_color=COLORS['primary'])
            else:
                # Bekliyor
                dot.configure(text_color=COLORS['text_secondary'])
                label.configure(text_color=COLORS['text_secondary'])
    
    # ═══════════════════════════════════════════════════════════════════════
    # ADIM YÖNETİMİ
    # ═══════════════════════════════════════════════════════════════════════
    
    def show_step(self, step: int):
        """
        Belirtilen adımı göster
        
        Args:
            step: Adım numarası (0: Cookie, 1: Playlist, 2: Download)
        """
        self.current_step = step
        
        # Content'i temizle
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Göstergeleri güncelle
        self.update_step_indicators()
        
        # İlgili adımı göster
        if step == 0:
            self.show_cookie_step()
        elif step == 1:
            self.show_playlist_step()
        elif step == 2:
            self.show_download_step()
    
    # ═══════════════════════════════════════════════════════════════════════
    # PROGRESS MONİTÖR
    # ═══════════════════════════════════════════════════════════════════════
    
    def start_progress_monitor(self):
        """Progress queue'yu sürekli kontrol et (thread-safe UI güncellemesi)"""
        def monitor():
            try:
                while not self.progress_queue.empty():
                    update = self.progress_queue.get_nowait()
                    # Progress güncellemelerini işle
                    if 'video_id' in update:
                        self.update_video_progress(update)
            except:
                pass
            
            # 100ms'de bir kontrol et
            self.after(100, monitor)
        
        monitor()
    
    def update_video_progress(self, data: Dict):
        """Video progress'ini güncelle"""
        video_id = data.get('video_id')
        percent = data.get('percent', 0)
        speed = data.get('speed', '')
        eta = data.get('eta', '')
        
        # Progress bar'ı güncelle
        if hasattr(self, f'progress_bar_{video_id}'):
            bar = getattr(self, f'progress_bar_{video_id}')
            bar.set(percent / 100)
        
        # Label'ı güncelle
        if hasattr(self, f'progress_label_{video_id}'):
            label = getattr(self, f'progress_label_{video_id}')
            label.configure(text=f"{percent:.1f}% | {speed} | ETA: {eta}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # ADIM 1: COOKIE YÖNETİMİ
    # ═══════════════════════════════════════════════════════════════════════
    
    def show_cookie_step(self):
        """Cookie adımı - Basit ve anlaşılır"""
        container = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=40, pady=20)
        
        # Başlık
        ctk.CTkLabel(
            container,
            text="🍪 Adım 1: Cookie Yükleme",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(pady=(0, 10))
        
        ctk.CTkLabel(
            container,
            text="YouTube üye videolarını indirmek için cookie'lerinizi yükleyin",
            font=ctk.CTkFont(size=14),
            text_color=COLORS['text_secondary']
        ).pack(pady=(0, 30))
        
        # Cookie durum kartı
        status_card = ctk.CTkFrame(
            container,
            fg_color=COLORS['bg_card'],
            corner_radius=15,
            border_width=2,
            border_color=COLORS['border']
        )
        status_card.pack(fill="x", pady=(0, 30))
        
        status_content = ctk.CTkFrame(status_card, fg_color="transparent")
        status_content.pack(fill="x", padx=30, pady=30)
        
        # Icon ve durum
        self.cookie_icon = ctk.CTkLabel(
            status_content,
            text="❓",
            font=ctk.CTkFont(size=48)
        )
        self.cookie_icon.pack(pady=(0, 10))
        
        self.cookie_status_label = ctk.CTkLabel(
            status_content,
            text="Cookie durumu kontrol ediliyor...",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS['text_primary']
        )
        self.cookie_status_label.pack(pady=(0, 5))
        
        self.cookie_detail_label = ctk.CTkLabel(
            status_content,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=COLORS['text_secondary']
        )
        self.cookie_detail_label.pack()
        
        # Cookie yükleme alanı
        load_frame = ctk.CTkFrame(container, fg_color=COLORS['bg_card'], corner_radius=15)
        load_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        ctk.CTkLabel(
            load_frame,
            text="✨ Cookie JSON'unu Buraya Yapıştırın",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(pady=(20, 10), padx=20)
        
        ctk.CTkLabel(
            load_frame,
            text="EditThisCookie uzantısından Export edin → JSON formatı",
            font=ctk.CTkFont(size=11),
            text_color=COLORS['text_secondary']
        ).pack(pady=(0, 15), padx=20)
        
        # Text area
        self.cookie_textbox = ctk.CTkTextbox(
            load_frame,
            height=220,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=COLORS['bg_dark'],
            border_width=2,
            border_color=COLORS['border']
        )
        self.cookie_textbox.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        self.cookie_textbox.insert("1.0", '[\n  {\n    "name": "HSID",\n    "value": "...",\n    "domain": ".youtube.com"\n  }\n]')
        
        # Butonlar
        button_frame = ctk.CTkFrame(load_frame, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        ctk.CTkButton(
            button_frame,
            text="💾 Kaydet ve Test Et",
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS['success'],
            hover_color=COLORS['success'],
            command=self.save_cookie_and_continue
        ).pack(fill="x", pady=(0, 5))
        
        button_frame2 = ctk.CTkFrame(load_frame, fg_color="transparent")
        button_frame2.pack(fill="x", padx=20, pady=(0, 20))
        
        ctk.CTkButton(
            button_frame2,
            text="📂 Dosyadan Yükle",
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary'],
            command=self.load_cookie_from_file
        ).pack(side="left", expand=True, fill="x", padx=(0, 5))
        
        ctk.CTkButton(
            button_frame2,
            text="❓ Nasıl Alınır?",
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color="transparent",
            border_width=2,
            border_color=COLORS['border'],
            hover_color=COLORS['bg_hover'],
            command=self.show_cookie_help
        ).pack(side="left", expand=True, fill="x", padx=5)
        
        ctk.CTkButton(
            button_frame2,
            text="⏭️ Test Atla",
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color=COLORS['warning'],
            hover_color=COLORS['warning'],
            command=lambda: self.show_step(1)
        ).pack(side="left", expand=True, fill="x", padx=(5, 0))
        
        # Mevcut cookie'yi kontrol et
        self.check_cookie_status(status_card)
    
    def check_cookie_status(self, status_card):
        """Mevcut cookie dosyasını kontrol et"""
        if self.cookie_file.exists():
            try:
                with open(self.cookie_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Gerekli cookie'leri kontrol et
                required = ['HSID', 'SSID', 'SID', 'APISID', 'SAPISID', 'LOGIN_INFO']
                found = [c for c in required if c in content]
                
                if len(found) >= 5:
                    self.cookie_icon.configure(text="✅")
                    self.cookie_status_label.configure(
                        text="Cookie Başarıyla Yüklü!",
                        text_color=COLORS['success']
                    )
                    self.cookie_detail_label.configure(
                        text=f"✓ {len(found)}/{len(required)} gerekli cookie bulundu | Dosya: {self.cookie_file.name}"
                    )
                    status_card.configure(border_color=COLORS['success'])
                else:
                    self.cookie_icon.configure(text="⚠️")
                    self.cookie_status_label.configure(
                        text="Eksik Cookie",
                        text_color=COLORS['warning']
                    )
                    self.cookie_detail_label.configure(
                        text=f"Sadece {len(found)}/{len(required)} cookie bulundu"
                    )
                    status_card.configure(border_color=COLORS['warning'])
            except:
                self.cookie_icon.configure(text="❌")
                self.cookie_status_label.configure(
                    text="Hatalı Cookie Dosyası",
                    text_color=COLORS['danger']
                )
                status_card.configure(border_color=COLORS['danger'])
        else:
            self.cookie_icon.configure(text="❌")
            self.cookie_status_label.configure(
                text="Cookie Yok",
                text_color=COLORS['danger']
            )
            self.cookie_detail_label.configure(
                text="Lütfen cookie yükleyin"
            )
            status_card.configure(border_color=COLORS['danger'])
    
    def save_cookie_and_continue(self):
        """Cookie'yi JSON'dan Netscape formatına çevir ve kaydet"""
        cookie_json = self.cookie_textbox.get("1.0", "end-1c").strip()
        
        # Boş veya placeholder kontrolü
        if not cookie_json or '"name": "HSID"' in cookie_json and '"value": "..."' in cookie_json:
            messagebox.showwarning("Uyarı", "⚠️ Lütfen gerçek cookie JSON'unu yapıştırın!")
            return
        
        try:
            # JSON parse et
            cookies = json.loads(cookie_json)
            
            if not isinstance(cookies, list):
                raise ValueError("Cookie formatı liste olmalı")
            
            # Netscape formatına dönüştür
            netscape_lines = ["# Netscape HTTP Cookie File\n"]
            
            for cookie in cookies:
                if not isinstance(cookie, dict):
                    continue
                
                domain = cookie.get('domain', '.youtube.com')
                flag = 'TRUE' if domain.startswith('.') else 'FALSE'
                path = cookie.get('path', '/')
                secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
                expiration = str(int(cookie.get('expirationDate', 0)))
                name = cookie.get('name', '')
                value = cookie.get('value', '')
                
                if name and value:
                    line = f"{domain}\t{flag}\t{path}\t{secure}\t{expiration}\t{name}\t{value}\n"
                    netscape_lines.append(line)
            
            # Kaydet
            with open(self.cookie_file, 'w', encoding='utf-8') as f:
                f.writelines(netscape_lines)
            
            self.log("Cookie kaydedildi, test ediliyor...", "info")
            
            # Loading dialog
            loading = ctk.CTkToplevel(self)
            loading.title("Test Ediliyor...")
            loading.geometry("400x180")
            loading.transient(self)
            loading.grab_set()
            
            ctk.CTkLabel(
                loading,
                text="🔍 Cookie Test Ediliyor...",
                font=ctk.CTkFont(size=16, weight="bold")
            ).pack(pady=30)
            
            ctk.CTkLabel(
                loading,
                text="YouTube'a bağlanılıyor...",
                font=ctk.CTkFont(size=12),
                text_color=COLORS['text_secondary']
            ).pack(pady=10)
            
            progress = ctk.CTkProgressBar(loading, mode="indeterminate")
            progress.pack(pady=20, padx=40, fill="x")
            progress.start()
            
            # Thread'de test et
            def test_thread():
                success = self.test_cookie()
                
                # UI güncellemelerini ana thread'de yap
                self.after(0, loading.destroy)
                
                if success:
                    self.after(0, lambda: self.log("✅ Cookie çalışıyor!", "success"))
                    self.after(0, lambda: messagebox.showinfo(
                        "✅ Başarılı", 
                        "Cookie başarıyla kaydedildi ve test edildi!\n\n"
                        "YouTube'a erişim sağlandı ✓\n\n"
                        "Şimdi playlist ekleyebilirsiniz."
                    ))
                    self.after(0, lambda: self.show_step(1))
                else:
                    self.after(0, lambda: self.log("❌ Cookie geçersiz veya test başarısız!", "error"))
                    self.after(0, lambda: messagebox.showerror(
                        "❌ Test Başarısız",
                        "Cookie kaydedildi ancak test başarısız!\n\n"
                        "2 seçenek:\n\n"
                        "1️⃣ Cookie yine de geçerli olabilir - 'Yine de devam et' için:\n"
                        "   → Direkt playlist ekranına geçmek için 'İleri' butonuna basın\n\n"
                        "2️⃣ Cookie geçersiz ise:\n"
                        "   • Cookie süresi dolmuş olabilir\n"
                        "   • YouTube'dan çıkış yapmış olabilirsiniz\n"
                        "   • İnternet bağlantınız kesilmiş olabilir\n\n"
                        "Test için: youtube.com/watch?v=dQw4w9WgXcQ"
                    ))
            
            thread = threading.Thread(target=test_thread, daemon=True)
            thread.start()
            
        except json.JSONDecodeError:
            messagebox.showerror("❌ Hata", "Geçersiz JSON formatı!\n\nLütfen doğru cookie JSON'unu yapıştırın.")
        except Exception as e:
            messagebox.showerror("❌ Hata", f"Cookie kaydedilemedi:\n\n{str(e)}")
    
    def test_cookie(self) -> bool:
        """Cookie'nin geçerli olup olmadığını test et"""
        try:
            # Basit bir YouTube URL'si ile test et
            test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Ünlü video :)
            
            cmd = [
                str(self.ytdlp_path),
                "--cookies", str(self.cookie_file),
                "--dump-json",
                "--skip-download",
                "--no-warnings",
                test_url
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,  # 30 saniye (daha uzun)
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            # Başarılı ise JSON dönmeli veya en azından hata olmamalı
            if result.returncode == 0:
                return True
            
            # Eğer output varsa ama error yoksa yine de geçerli kabul et
            if result.stdout.strip() and "ERROR" not in result.stderr:
                return True
            
            return False
        
        except subprocess.TimeoutExpired:
            self.log("Cookie testi zaman aşımına uğradı (yavaş internet?)", "warning")
            return False
        except Exception as e:
            self.log(f"Cookie test hatası: {str(e)}", "warning")
            return False
    
    def load_cookie_from_file(self):
        """Dosyadan cookie yükle"""
        file_path = filedialog.askopenfilename(
            title="Cookie Dosyası Seçin",
            filetypes=[
                ("JSON files", "*.json"),
                ("Text files", "*.txt"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # JSON formatındaysa dönüştür
            if file_path.endswith('.json'):
                self.cookie_textbox.delete("1.0", "end")
                self.cookie_textbox.insert("1.0", content)
                self.save_cookie_and_continue()
            else:
                # TXT formatı direkt kopyala
                self.cookie_file.write_text(content, encoding='utf-8')
                self.log("Cookie dosyası yüklendi", "success")
                messagebox.showinfo("✅ Başarılı", "Cookie dosyası yüklendi!")
                self.show_step(1)
        except Exception as e:
            messagebox.showerror("❌ Hata", f"Dosya yüklenemedi:\n\n{str(e)}")
    
    def show_cookie_help(self):
        """Cookie yardım penceresi"""
        help_win = ctk.CTkToplevel(self)
        help_win.title("🍪 Cookie Nasıl Alınır?")
        help_win.geometry("700x600")
        help_win.transient(self)
        help_win.grab_set()
        
        # Scroll frame
        scroll = ctk.CTkScrollableFrame(help_win, fg_color=COLORS['bg_dark'])
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        help_text = """
🍪 YOUTUBE COOKIE NASIL ALINIR?

═══════════════════════════════════════════════════════

📌 ADIM 1: Chrome Uzantısı Kur
   1. Google Chrome'u açın
   2. "EditThisCookie" uzantısını Chrome Web Store'dan yükleyin
   3. Yüklendikten sonra Chrome'u yeniden başlatın

📌 ADIM 2: YouTube'a Giriş Yapın
   1. youtube.com adresine gidin
   2. ÜYE OLDUĞUNUZ hesapla giriş yapın
   3. Bir üye videosunu açın ve izleyebildiğinizi kontrol edin

📌 ADIM 3: Cookie'leri Export Edin
   1. Sağ üst köşede EditThisCookie simgesine tıklayın (🍪)
   2. "Export" butonuna tıklayın (veya Ctrl+C yapın)
   3. JSON otomatik olarak panoya kopyalanır

📌 ADIM 4: Bu Programa Yapıştırın
   1. Kopyalanan JSON'u yukarıdaki alana yapıştırın (Ctrl+V)
   2. "💾 Kaydet ve Devam Et" butonuna tıklayın
   3. Cookie otomatik olarak doğru formata dönüştürülür

═══════════════════════════════════════════════════════

✅ ÖNEMLİ NOTLAR:
   • Cookie'ler KİŞİSELDİR, kimseyle paylaşmayın!
   • Cookie'ler zaman içinde sona erer (3-6 ay)
   • Eğer video indirilemezse cookie'yi yenileyin
   • Mutlaka ÜYE hesabınızla giriş yapın
   • Başkasının hesabı ile indirme yapmayın!

🔒 GÜVENLİK:
   • Cookie'leriniz sadece bu bilgisayarda kalır
   • Hiçbir yere gönderilmez
   • Sadece yt-dlp kullanır (güvenli)

═══════════════════════════════════════════════════════

💡 İPUCU:
   Cookie'leri aldıktan sonra bir .json dosyasına kaydedin.
   Böylece sona erdiğinde tekrar kullanabilirsiniz.

═══════════════════════════════════════════════════════
"""
        
        ctk.CTkLabel(
            scroll,
            text=help_text,
            font=ctk.CTkFont(family="Consolas", size=11),
            justify="left",
            anchor="nw"
        ).pack(fill="both", padx=10, pady=10)
        
        ctk.CTkButton(
            help_win,
            text="✅ Anladım!",
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary'],
            command=help_win.destroy
        ).pack(pady=20)
    
    def show_playlist_step(self):
        """Adım 2: Playlist/Video ekleme"""
        container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=40, pady=20)
        
        # Başlık ve butonlar
        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))
        
        # Sol: Başlık
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left")
        
        ctk.CTkLabel(
            title_frame,
            text="📋 Adım 2: Playlist/Video Ekleme",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            title_frame,
            text="Her satıra bir YouTube linki yazın (playlist veya tekil video)",
            font=ctk.CTkFont(size=14),
            text_color=COLORS['text_secondary']
        ).pack(anchor="w", pady=(5, 0))
        
        # Sağ: Butonlar
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right")
        
        ctk.CTkButton(
            btn_frame,
            text="◀️ Geri",
            height=40,
            width=100,
            font=ctk.CTkFont(size=13),
            fg_color="transparent",
            border_width=2,
            border_color=COLORS['border'],
            hover_color=COLORS['bg_hover'],
            command=lambda: self.show_step(0)
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text="▶️ İndirmeye Geç",
            height=40,
            width=150,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS['success'],
            hover_color=COLORS['success'],
            command=self.go_to_download
        ).pack(side="left", padx=5)
        
        # Ana içerik - 2 sütun
        content = ctk.CTkFrame(container, fg_color="transparent")
        content.pack(fill="both", expand=True)
        content.grid_columnconfigure(0, weight=2)
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=1)
        
        # Sol: Link girişi
        left_panel = ctk.CTkFrame(content, fg_color=COLORS['bg_card'], corner_radius=15)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        ctk.CTkLabel(
            left_panel,
            text="✨ Link Ekle",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(pady=(20, 10), padx=20)
        
        ctk.CTkLabel(
            left_panel,
            text="Her satıra bir YouTube linki (playlist veya video)",
            font=ctk.CTkFont(size=11),
            text_color=COLORS['text_secondary']
        ).pack(pady=(0, 15), padx=20)
        
        # Text area
        self.playlist_textbox = ctk.CTkTextbox(
            left_panel,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=COLORS['bg_dark'],
            border_width=2,
            border_color=COLORS['border']
        )
        self.playlist_textbox.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        
        # Placeholder
        placeholder_text = "https://www.youtube.com/playlist?list=PLxxxxxx\nhttps://www.youtube.com/watch?v=xxxxxx\nhttps://www.youtube.com/playlist?list=PLyyyyyy"
        self.playlist_textbox.insert("1.0", placeholder_text)
        
        # İlk tıklamada placeholder'ı temizle
        def clear_placeholder(event):
            if self.playlist_textbox.get("1.0", "end-1c") == placeholder_text:
                self.playlist_textbox.delete("1.0", "end")
            self.playlist_textbox.unbind("<Button-1>")
        
        self.playlist_textbox.bind("<Button-1>", clear_placeholder)
        
        # ÖNEMLİ: Büyük yeşil buton - textbox'ın hemen altında
        big_button_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        big_button_frame.pack(fill="x", padx=20, pady=(15, 15))
        
        ctk.CTkButton(
            big_button_frame,
            text="✅ LİNKLERİ EKLE VE BİLGİLERİ ÇEK",
            height=60,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=COLORS['success'],
            hover_color="#2d8a3e",
            text_color="white",
            corner_radius=10,
            command=self.add_playlists
        ).pack(fill="x")
        
        # Temizle butonu
        ctk.CTkButton(
            big_button_frame,
            text="🗑️ Temizle",
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color=COLORS['danger'],
            hover_color="#c92a2a",
            command=self.clear_playlists
        ).pack(fill="x", pady=(8, 0))
        
        # Ayarlar (butonların altında)
        settings_frame = ctk.CTkFrame(left_panel, fg_color=COLORS['bg_dark'], corner_radius=10)
        settings_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        settings_content = ctk.CTkFrame(settings_frame, fg_color="transparent")
        settings_content.pack(fill="x", padx=15, pady=15)
        
        ctk.CTkLabel(
            settings_content,
            text="⚙️ Video Kalitesi",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(anchor="w", pady=(0, 10))
        
        # Kalite
        quality_frame = ctk.CTkFrame(settings_content, fg_color="transparent")
        quality_frame.pack(fill="x", pady=5)
        
        self.quality_var = ctk.StringVar(value="best")
        for label, value in [("En İyi", "best"), ("1080p", "1080"), ("720p", "720"), ("480p", "480")]:
            ctk.CTkRadioButton(
                quality_frame,
                text=label,
                variable=self.quality_var,
                value=value,
                font=ctk.CTkFont(size=11)
            ).pack(side="left", padx=5)
        
        # Not: Kapak fotoğrafları her zaman videoya gömülü olacak
        ctk.CTkLabel(
            settings_content,
            text="� Not: Kapak fotoğrafları otomatik olarak videoya gömülü gelir",
            font=ctk.CTkFont(size=10),
            text_color=COLORS['text_secondary']
        ).pack(anchor="w", pady=(10, 0))
        
        # Sağ: Playlist listesi
        right_panel = ctk.CTkFrame(content, fg_color=COLORS['bg_card'], corner_radius=15)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        ctk.CTkLabel(
            right_panel,
            text="📋 Eklenen Listeler",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(pady=(20, 10), padx=20)
        
        # İstatistikler
        self.stats_frame = ctk.CTkFrame(right_panel, fg_color=COLORS['bg_dark'], corner_radius=10)
        self.stats_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        stats_content = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        stats_content.pack(fill="x", padx=15, pady=15)
        
        self.playlist_count_label = ctk.CTkLabel(
            stats_content,
            text="📋 Playlist: 0",
            font=ctk.CTkFont(size=13),
            text_color=COLORS['text_primary']
        )
        self.playlist_count_label.pack(anchor="w", pady=2)
        
        self.video_count_label = ctk.CTkLabel(
            stats_content,
            text="🎥 Video: 0",
            font=ctk.CTkFont(size=13),
            text_color=COLORS['text_primary']
        )
        self.video_count_label.pack(anchor="w", pady=2)
        
        # Playlist scroll
        self.playlist_scroll = ctk.CTkScrollableFrame(
            right_panel,
            fg_color="transparent"
        )
        self.playlist_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # Mevcut playlist'leri göster
        self.update_playlist_display()
    
    def add_playlists(self):
        """Playlist'leri ekle"""
        urls_text = self.playlist_textbox.get("1.0", "end-1c").strip()
        
        # Placeholder kontrolü
        if not urls_text or urls_text.startswith("https://www.youtube.com/playlist?list=PLxxxxxx"):
            messagebox.showwarning("Uyarı", "⚠️ Lütfen gerçek YouTube linklerini girin!")
            return
        
        # Satırları ayır
        urls = [line.strip() for line in urls_text.split('\n') if line.strip()]
        urls = [url for url in urls if 'youtube.com' in url or 'youtu.be' in url]
        
        if not urls:
            messagebox.showwarning("Uyarı", "Geçerli YouTube linki bulunamadı!")
            return
        
        # Loading dialog
        loading = ctk.CTkToplevel(self)
        loading.title("Yükleniyor...")
        loading.geometry("450x220")
        loading.transient(self)
        loading.grab_set()
        
        ctk.CTkLabel(
            loading,
            text="⏳ Playlist/Video bilgileri alınıyor...",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=30)
        
        progress_label = ctk.CTkLabel(
            loading,
            text=f"0 / {len(urls)}",
            font=ctk.CTkFont(size=14)
        )
        progress_label.pack(pady=10)
        
        progress_bar = ctk.CTkProgressBar(loading, mode="determinate")
        progress_bar.pack(pady=20, padx=40, fill="x")
        progress_bar.set(0)
        
        status_label = ctk.CTkLabel(
            loading,
            text="Başlıyor...",
            font=ctk.CTkFont(size=11),
            text_color=COLORS['text_secondary']
        )
        status_label.pack()
        
        def fetch():
            success = 0
            
            for i, url in enumerate(urls):
                if not loading.winfo_exists():
                    break
                
                self.after(0, lambda u=url: status_label.configure(text=f"İşleniyor: {u[:50]}..."))
                
                try:
                    cmd = [
                        str(self.ytdlp_path),
                        "--cookies", str(self.cookie_file),
                        "--flat-playlist",
                        "--dump-json",
                        url
                    ]
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=PLAYLIST_TIMEOUT,
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                    )
                    
                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        videos = []
                        pl_title = "İçerik"
                        pl_thumbnail = ""
                        
                        for line in lines:
                            if not line:
                                continue
                            try:
                                data = json.loads(line)
                                if data.get('_type') == 'playlist':
                                    pl_title = data.get('title', 'Playlist')
                                    pl_thumbnail = data.get('thumbnail', '')
                                elif data.get('id'):
                                    videos.append({
                                        'id': data['id'],
                                        'title': data.get('title', 'Video'),
                                        'url': f"https://www.youtube.com/watch?v={data['id']}",
                                        'thumbnail': data.get('thumbnail', ''),
                                        'duration': data.get('duration', 0)
                                    })
                            except:
                                continue
                        
                        # Tek video ise
                        if not videos and lines:
                            try:
                                data = json.loads(lines[0])
                                if data.get('id'):
                                    videos.append({
                                        'id': data['id'],
                                        'title': data.get('title', 'Video'),
                                        'url': url,
                                        'thumbnail': data.get('thumbnail', ''),
                                        'duration': data.get('duration', 0)
                                    })
                                    pl_title = data.get('title', 'Tek Video')
                                    pl_thumbnail = data.get('thumbnail', '')
                            except:
                                pass
                        
                        if videos:
                            # Thumbnail yoksa ilk videodan al
                            if not pl_thumbnail and videos:
                                pl_thumbnail = videos[0].get('thumbnail', '')
                            
                            self.after(0, lambda v=videos, t=pl_title, u=url, th=pl_thumbnail: 
                                      self._add_playlist_internal(v, t, u, th))
                            success += 1
                
                except subprocess.TimeoutExpired:
                    self.after(0, lambda: self.log(f"Timeout: {url[:50]}...", "warning"))
                except Exception as e:
                    self.after(0, lambda e=str(e): self.log(f"Hata: {e}", "error"))
                
                # Progress
                prog = (i + 1) / len(urls)
                self.after(0, lambda p=prog: progress_bar.set(p))
                self.after(0, lambda: progress_label.configure(text=f"{i+1} / {len(urls)}"))
            
            # Tamamlandı
            self.after(0, loading.destroy)
            
            if success > 0:
                self.after(0, lambda: messagebox.showinfo(
                    "✅ Başarılı",
                    f"{success} playlist/video eklendi!\n\n"
                    f"Toplam {len(self.all_videos)} video hazır."
                ))
            else:
                self.after(0, lambda: messagebox.showerror(
                    "❌ Hata",
                    "Hiçbir playlist/video eklenemedi!\n\n"
                    "Cookie'lerinizi kontrol edin veya linkleri gözden geçirin."
                ))
        
        thread = threading.Thread(target=fetch, daemon=True)
        thread.start()
    
    def _add_playlist_internal(self, videos: List[Dict], title: str, url: str, thumbnail: str = ""):
        """Playlist'i dahili olarak ekle - Thumbnail ile"""
        playlist = {
            'title': title if title and title != "Bilinmeyen" else self.extract_playlist_title_from_url(url),
            'url': url,
            'video_count': len(videos),
            'videos': videos,
            'quality': self.quality_var.get(),
            'thumbnail': thumbnail or (videos[0]['thumbnail'] if videos and videos[0].get('thumbnail') else "")
        }
        
        self.playlists.append(playlist)
        self.all_videos.extend(videos)
        
        # Video state'leri
        for video in videos:
            if video['id'] not in self.video_states:
                self.video_states[video['id']] = 'pending'
        
        self.update_playlist_display()
        self.update_stats()
        self.log(f"Eklendi: {playlist['title']} ({len(videos)} video)", "success")
        
        # Checkpoint kaydet
        self.save_checkpoint()
    
    def extract_playlist_title_from_url(self, url: str) -> str:
        """URL'den playlist başlığını çıkar (fallback)"""
        if 'watch?v=' in url:
            return "Tekil Video"
        elif 'list=' in url:
            import re
            match = re.search(r'list=([^&]+)', url)
            if match:
                return f"Playlist ({match.group(1)[:10]}...)"
        return "Eklenen İçerik"
    
    def update_playlist_display(self):
        """Playlist listesini göster"""
        for widget in self.playlist_scroll.winfo_children():
            widget.destroy()
        
        if not self.playlists:
            ctk.CTkLabel(
                self.playlist_scroll,
                text="Henüz playlist eklenmedi",
                font=ctk.CTkFont(size=12),
                text_color=COLORS['text_secondary']
            ).pack(pady=20)
            return
        
        for i, pl in enumerate(self.playlists):
            card = ctk.CTkFrame(self.playlist_scroll, fg_color=COLORS['bg_dark'], corner_radius=8)
            card.pack(fill="x", pady=3, padx=3)
            
            content = ctk.CTkFrame(card, fg_color="transparent")
            content.pack(fill="x", padx=10, pady=10)
            
            # Başlık
            title = pl['title'][:30] + "..." if len(pl['title']) > 30 else pl['title']
            ctk.CTkLabel(
                content,
                text=f"📋 {title}",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=COLORS['text_primary'],
                anchor="w"
            ).pack(fill="x")
            
            # Detay
            ctk.CTkLabel(
                content,
                text=f"🎥 {pl['video_count']} video • 📺 {pl['quality']}",
                font=ctk.CTkFont(size=10),
                text_color=COLORS['text_secondary'],
                anchor="w"
            ).pack(fill="x", pady=(2, 0))
            
            # Sil
            ctk.CTkButton(
                content,
                text="🗑️",
                width=30,
                height=24,
                font=ctk.CTkFont(size=11),
                fg_color=COLORS['danger'],
                hover_color=COLORS['danger'],
                command=lambda idx=i: self.remove_playlist(idx)
            ).pack(anchor="e", pady=(5, 0))
    
    def update_stats(self):
        """İstatistikleri güncelle"""
        if hasattr(self, 'playlist_count_label'):
            self.playlist_count_label.configure(text=f"📋 Playlist: {len(self.playlists)}")
        if hasattr(self, 'video_count_label'):
            self.video_count_label.configure(text=f"🎥 Video: {len(self.all_videos)}")
    
    def remove_playlist(self, index: int):
        """Playlist'i sil"""
        if messagebox.askyesno("Onay", "Bu playlist'i silmek istediğinizden emin misiniz?"):
            pl = self.playlists[index]
            video_ids = [v['id'] for v in pl['videos']]
            self.all_videos = [v for v in self.all_videos if v['id'] not in video_ids]
            del self.playlists[index]
            self.update_playlist_display()
            self.update_stats()
            self.log(f"Silindi: {pl['title']}", "info")
    
    def clear_playlists(self):
        """Tüm playlist'leri temizle"""
        if self.playlists and messagebox.askyesno("Onay", "Tüm playlist'leri silmek istediğinizden emin misiniz?"):
            self.playlists.clear()
            self.all_videos.clear()
            self.video_states.clear()
            self.update_playlist_display()
            self.update_stats()
            self.log("Tüm playlist'ler temizlendi", "info")
    
    def go_to_download(self):
        """İndirme adımına geç"""
        if not self.all_videos:
            messagebox.showwarning("Uyarı", "⚠️ Önce en az bir playlist/video ekleyin!")
            return
        
        self.show_step(2)
    
    def show_download_step(self):
        """Adım 3: İndirme"""
        container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=40, pady=20)
        
        # Başlık
        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(
            header,
            text="⬇️ Adım 3: İndirme",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(side="left")
        
        ctk.CTkButton(
            header,
            text="◀️ Geri",
            height=40,
            width=100,
            font=ctk.CTkFont(size=13),
            fg_color="transparent",
            border_width=2,
            border_color=COLORS['border'],
            hover_color=COLORS['bg_hover'],
            command=lambda: self.show_step(1)
        ).pack(side="right")
        
        # İstatistik kartları
        stats_container = ctk.CTkFrame(container, fg_color="transparent")
        stats_container.pack(fill="x", pady=(0, 20))
        
        for i in range(5):
            stats_container.grid_columnconfigure(i, weight=1)
        
        self.total_label = self._create_stat_card(stats_container, 0, "📊", "Toplam", "0")
        self.downloaded_label = self._create_stat_card(stats_container, 1, "✅", "İndirilen", "0")
        self.failed_label = self._create_stat_card(stats_container, 2, "❌", "Başarısız", "0")
        self.skipped_label = self._create_stat_card(stats_container, 3, "⏭️", "Atlanan", "0")
        self.current_label = self._create_stat_card(stats_container, 4, "⏳", "Kalan", "0")
        
        # Ana alan - 2 sütun
        content = ctk.CTkFrame(container, fg_color="transparent")
        content.pack(fill="both", expand=True)
        content.grid_columnconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=2)
        content.grid_rowconfigure(0, weight=1)
        
        # Sol: Kontroller
        left_panel = ctk.CTkFrame(content, fg_color=COLORS['bg_card'], corner_radius=15)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        ctk.CTkLabel(
            left_panel,
            text="⚙️ İndirme Ayarları",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(pady=(20, 15), padx=20)
        
        # Klasör seçimi
        folder_frame = ctk.CTkFrame(left_panel, fg_color=COLORS['bg_dark'], corner_radius=10)
        folder_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        folder_content = ctk.CTkFrame(folder_frame, fg_color="transparent")
        folder_content.pack(fill="x", padx=15, pady=15)
        
        ctk.CTkLabel(
            folder_content,
            text="📁 İndirme Klasörü:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(anchor="w", pady=(0, 5))
        
        self.folder_label = ctk.CTkLabel(
            folder_content,
            text="Henüz seçilmedi",
            font=ctk.CTkFont(size=11),
            text_color=COLORS['text_secondary'],
            anchor="w"
        )
        self.folder_label.pack(fill="x", pady=(0, 10))
        
        ctk.CTkButton(
            folder_content,
            text="📂 Klasör Seç",
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary'],
            command=self.select_download_folder
        ).pack(fill="x")
        
        # Progress
        progress_frame = ctk.CTkFrame(left_panel, fg_color=COLORS['bg_dark'], corner_radius=10)
        progress_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        progress_content = ctk.CTkFrame(progress_frame, fg_color="transparent")
        progress_content.pack(fill="x", padx=15, pady=15)
        
        ctk.CTkLabel(
            progress_content,
            text="📈 Genel İlerleme:",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(anchor="w", pady=(0, 5))
        
        self.overall_progress = ctk.CTkProgressBar(progress_content, mode="determinate")
        self.overall_progress.pack(fill="x", pady=(0, 5))
        self.overall_progress.set(0)
        
        self.overall_progress_label = ctk.CTkLabel(
            progress_content,
            text="0 / 0 (0%)",
            font=ctk.CTkFont(size=11),
            text_color=COLORS['text_secondary']
        )
        self.overall_progress_label.pack(anchor="w")
        
        # Butonlar
        button_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self.start_btn = ctk.CTkButton(
            button_frame,
            text="▶️ İndirmeyi Başlat",
            height=50,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=COLORS['success'],
            hover_color=COLORS['success'],
            command=self.start_download
        )
        self.start_btn.pack(fill="x", pady=(0, 5))
        
        # Duraklat/Devam butonu
        self.pause_btn = ctk.CTkButton(
            button_frame,
            text="⏸️ Duraklat",
            height=45,
            font=ctk.CTkFont(size=14),
            fg_color=COLORS['warning'],
            hover_color=COLORS['warning'],
            command=self.toggle_pause,
            state="disabled"
        )
        self.pause_btn.pack(fill="x", pady=(0, 5))
        
        self.stop_btn = ctk.CTkButton(
            button_frame,
            text="⏹️ Durdur",
            height=45,
            font=ctk.CTkFont(size=14),
            fg_color=COLORS['danger'],
            hover_color=COLORS['danger'],
            command=self.stop_download,
            state="disabled"
        )
        self.stop_btn.pack(fill="x", pady=(0, 5))
        
        ctk.CTkButton(
            button_frame,
            text="🔄 Başarısızları Tekrarla",
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary'],
            command=self.retry_failed
        ).pack(fill="x")
        
        # Sağ: Video listesi
        right_panel = ctk.CTkFrame(content, fg_color=COLORS['bg_card'], corner_radius=15)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        ctk.CTkLabel(
            right_panel,
            text="🎥 Video Listesi",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(pady=(20, 10), padx=20)
        
        # Video scroll
        self.video_scroll = ctk.CTkScrollableFrame(
            right_panel,
            fg_color="transparent"
        )
        self.video_scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # Video kartlarını oluştur
        self.create_video_cards()
    
    def _create_stat_card(self, parent, col, icon, label, value):
        """İstatistik kartı oluştur"""
        card = ctk.CTkFrame(parent, fg_color=COLORS['bg_card'], corner_radius=10)
        card.grid(row=0, column=col, sticky="ew", padx=5)
        
        ctk.CTkLabel(
            card,
            text=icon,
            font=ctk.CTkFont(size=24)
        ).pack(pady=(10, 0))
        
        value_label = ctk.CTkLabel(
            card,
            text=value,
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS['text_primary']
        )
        value_label.pack()
        
        ctk.CTkLabel(
            card,
            text=label,
            font=ctk.CTkFont(size=11),
            text_color=COLORS['text_secondary']
        ).pack(pady=(0, 10))
        
        return value_label
    
    def create_video_cards(self):
        """Gelişmiş video kartları - Progress bar ve detaylarla"""
        for widget in self.video_scroll.winfo_children():
            widget.destroy()
        
        if not self.playlists:
            ctk.CTkLabel(
                self.video_scroll,
                text="Video bulunamadı",
                font=ctk.CTkFont(size=12),
                text_color=COLORS['text_secondary']
            ).pack(pady=20)
            return
        
        # Playlist'lere göre grupla
        for pl in self.playlists:
            # Playlist başlığı
            pl_header = ctk.CTkFrame(self.video_scroll, fg_color=COLORS['bg_dark'], corner_radius=8)
            pl_header.pack(fill="x", pady=(5, 2), padx=3)
            
            pl_content = ctk.CTkFrame(pl_header, fg_color="transparent")
            pl_content.pack(fill="x", padx=15, pady=10)
            
            title = pl['title'][:40] + "..." if len(pl['title']) > 40 else pl['title']
            ctk.CTkLabel(
                pl_content,
                text=f"📋 {title}",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=COLORS['text_primary'],
                anchor="w"
            ).pack(side="left", fill="x", expand=True)
            
            # Playlist istatistikleri
            pl_done = sum(1 for v in pl['videos'] if self.video_states.get(v['id']) == 'done')
            pl_failed = sum(1 for v in pl['videos'] if self.video_states.get(v['id']) == 'failed')
            pl_skipped = sum(1 for v in pl['videos'] if self.video_states.get(v['id']) == 'skipped')
            
            stats_text = f"✅{pl_done} ❌{pl_failed} ⏭️{pl_skipped} | 🎥{pl['video_count']}"
            ctk.CTkLabel(
                pl_content,
                text=stats_text,
                font=ctk.CTkFont(size=10),
                text_color=COLORS['text_secondary']
            ).pack(side="right", padx=(10, 0))
            
            # Videolar - TÜM videoları göster (10 limit kaldırıldı)
            for video in pl['videos']:
                video_id = video['id']
                state = self.video_states.get(video_id, 'pending')
                
                # Video kartı
                card_color = COLORS['bg_hover']
                if state == 'downloading':
                    card_color = "#1e3a5f"  # Mavi ton
                elif state == 'failed':
                    card_color = "#4a1f1f"  # Kırmızı ton
                
                video_card = ctk.CTkFrame(self.video_scroll, fg_color=card_color, corner_radius=6)
                video_card.pack(fill="x", pady=1, padx=10)
                
                video_content = ctk.CTkFrame(video_card, fg_color="transparent")
                video_content.pack(fill="both", expand=True, padx=10, pady=6)
                
                # Üst satır: Başlık ve durum
                top_row = ctk.CTkFrame(video_content, fg_color="transparent")
                top_row.pack(fill="x")
                
                v_title = video['title'][:60] + "..." if len(video['title']) > 60 else video['title']
                ctk.CTkLabel(
                    top_row,
                    text=f"🎬 {v_title}",
                    font=ctk.CTkFont(size=11),
                    text_color=COLORS['text_primary'],
                    anchor="w"
                ).pack(side="left", fill="x", expand=True)
                
                # Durum ikonu ve text
                status_icons = {
                    'pending': ('⏳', 'Bekliyor'),
                    'downloading': ('⬇️', 'İndiriliyor'),
                    'done': ('✅', 'Tamamlandı'),
                    'failed': ('❌', 'Başarısız'),
                    'skipped': ('⏭️', 'Atlandı')
                }
                icon, status_text = status_icons.get(state, ('⏳', 'Bekliyor'))
                
                status_frame = ctk.CTkFrame(top_row, fg_color="transparent")
                status_frame.pack(side="right")
                
                ctk.CTkLabel(
                    status_frame,
                    text=f"{icon} {status_text}",
                    font=ctk.CTkFont(size=10),
                    text_color=COLORS['text_secondary']
                ).pack()
                
                # Progress bar ve detaylar (sadece downloading durumunda)
                if state == 'downloading' and video_id in self.video_progress:
                    progress_data = self.video_progress[video_id]
                    
                    # Progress bar
                    progress_bar = ctk.CTkProgressBar(
                        video_content,
                        mode="determinate",
                        height=6
                    )
                    progress_bar.pack(fill="x", pady=(5, 3))
                    progress_bar.set(progress_data.get('progress', 0) / 100.0)
                    
                    # Detaylar
                    details_text = []
                    if progress_data.get('progress'):
                        details_text.append(f"{progress_data['progress']:.1f}%")
                    if progress_data.get('size'):
                        details_text.append(f"📦 {progress_data['size']}")
                    if progress_data.get('speed'):
                        details_text.append(f"⚡ {progress_data['speed']}")
                    if progress_data.get('eta'):
                        details_text.append(f"⏱️ {progress_data['eta']}")
                    
                    if details_text:
                        ctk.CTkLabel(
                            video_content,
                            text=" • ".join(details_text),
                            font=ctk.CTkFont(size=9),
                            text_color=COLORS['text_secondary']
                        ).pack(anchor="w")
                
                # Hata mesajı (sadece failed durumunda)
                elif state == 'failed' and video_id in self.video_progress:
                    error_msg = self.video_progress[video_id].get('error', 'Bilinmeyen hata')
                    ctk.CTkLabel(
                        video_content,
                        text=f"⚠️ {error_msg}",
                        font=ctk.CTkFont(size=9),
                        text_color=COLORS['danger']
                    ).pack(anchor="w", pady=(3, 0))
        
        # İstatistikleri güncelle
        self.update_download_stats()
    
    def select_download_folder(self):
        """İndirme klasörünü seç"""
        folder = filedialog.askdirectory(title="İndirme Klasörü Seçin")
        
        if folder:
            self.download_folder = Path(folder)
            short_path = str(folder)[:40] + "..." if len(str(folder)) > 40 else str(folder)
            self.folder_label.configure(text=short_path, text_color=COLORS['success'])
            self.log(f"Klasör seçildi: {folder}", "success")
    
    def update_download_stats(self):
        """İndirme istatistiklerini güncelle - Süre tahmini ile"""
        total = len(self.all_videos)
        downloaded = sum(1 for v in self.all_videos if self.video_states.get(v['id']) == 'done')
        failed = sum(1 for v in self.all_videos if self.video_states.get(v['id']) == 'failed')
        skipped = sum(1 for v in self.all_videos if self.video_states.get(v['id']) == 'skipped')
        remaining = total - downloaded - failed - skipped
        
        self.total_label.configure(text=str(total))
        self.downloaded_label.configure(text=str(downloaded))
        self.failed_label.configure(text=str(failed))
        self.skipped_label.configure(text=str(skipped))
        self.current_label.configure(text=str(remaining))
        
        # Progress
        if total > 0:
            progress = (downloaded + skipped) / total
            self.overall_progress.set(progress)
            
            # Süre tahmini
            eta_text = f"{downloaded + skipped} / {total} ({int(progress * 100)}%)"
            
            if self.is_downloading and self.download_stats.get('start_time') and downloaded > 0:
                elapsed = time.time() - self.download_stats['start_time']
                avg_time_per_video = elapsed / downloaded
                estimated_remaining = avg_time_per_video * remaining
                
                eta_str = str(timedelta(seconds=int(estimated_remaining)))
                eta_text += f" | ⏱️ Tahmini: {eta_str}"
            
            self.overall_progress_label.configure(text=eta_text)
    
    def start_download(self):
        """İndirmeyi başlat"""
        if not self.download_folder:
            messagebox.showwarning("Uyarı", "⚠️ Önce indirme klasörü seçin!")
            return
        
        self.is_downloading = True
        self.is_paused = False
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.pause_btn.configure(state="normal", text="⏸️ Duraklat")
        
        self.log("İndirme başlatılıyor...", "info")
        
        # Thread'de indir
        thread = threading.Thread(target=self.download_worker, daemon=True)
        thread.start()
    
    def toggle_pause(self):
        """Duraklat/Devam et"""
        if self.is_paused:
            # Devam et
            self.is_paused = False
            self.pause_btn.configure(text="⏸️ Duraklat", fg_color=COLORS['warning'])
            self.log("▶️ İndirme devam ediyor...", "info")
        else:
            # Duraklat
            self.is_paused = True
            self.pause_btn.configure(text="▶️ Devam Et", fg_color=COLORS['success'])
            self.log("⏸️ İndirme duraklatıldı", "warning")
    
    def stop_download(self):
        """İndirmeyi tamamen durdur"""
        self.is_downloading = False
        self.is_paused = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.pause_btn.configure(state="disabled", text="⏸️ Duraklat")
        self.log("⏹️ İndirme durduruldu", "warning")
    
    def retry_failed(self):
        """Başarısız videoları tekrar dene"""
        failed_videos = [v for v in self.all_videos if self.video_states.get(v['id']) == 'failed']
        
        if not failed_videos:
            messagebox.showinfo("Bilgi", "Başarısız video yok!")
            return
        
        # State'leri ve hataları sıfırla
        for video in failed_videos:
            video_id = video['id']
            self.video_states[video_id] = 'pending'
            if video_id in self.video_progress:
                self.video_progress[video_id] = {}
        
        self.download_stats['failed'] = 0
        self.create_video_cards()
        self.log(f"🔄 {len(failed_videos)} başarısız video tekrar denenecek", "info")
        messagebox.showinfo("✅ Hazır", f"{len(failed_videos)} video tekrar denenecek!")
    
    def download_worker(self):
        """Gelişmiş indirme motoru - Akıllı tarama, progress tracking, hata detayları"""
        self.download_stats['start_time'] = time.time()
        
        # Önce mevcut dosyaları tara
        self.after(0, lambda: self.log("🔍 Klasör taranıyor, mevcut videolar kontrol ediliyor...", "info"))
        self.scan_existing_videos()
        
        # İstatistikleri güncelle
        self.after(0, self.update_download_stats)
        self.after(0, self.create_video_cards)
        
        skipped_count = sum(1 for v in self.all_videos if self.video_states.get(v['id']) == 'skipped')
        if skipped_count > 0:
            self.after(0, lambda: self.log(f"⏭️ {skipped_count} video zaten mevcut, atlanacak", "success"))
        
        # Sırayla indir
        for video in self.all_videos:
            # Durdurma kontrolü
            while self.is_paused and self.is_downloading:
                time.sleep(0.5)
            
            if not self.is_downloading:
                break
            
            video_id = video['id']
            
            # Zaten indirilmiş veya atlanmış mı?
            if self.video_states[video_id] in ['done', 'skipped']:
                continue
            
            # İndirmeyi başlat
            self.current_downloading_id = video_id
            self.video_states[video_id] = 'downloading'
            self.video_progress[video_id] = {'progress': 0, 'speed': '', 'eta': '', 'size': ''}
            
            self.after(0, self.create_video_cards)
            self.after(0, lambda t=video['title']: self.log(f"⬇️ İndiriliyor: {t[:50]}...", "info"))
            
            try:
                # yt-dlp komutu - Alt yazı, thumbnail ve progress tracking
                output_template = str(self.download_folder / "%(title)s.%(ext)s")
                
                cmd = [
                    str(self.ytdlp_path),
                    "--cookies", str(self.cookie_file),
                    "-f", "best",
                    "--write-thumbnail",       # Thumbnail indir
                    "--embed-thumbnail",       # Videoya göm
                    "--convert-thumbnails", "jpg",
                    "--write-subs",            # Alt yazı indir
                    "--write-auto-subs",       # Otomatik alt yazı da indir
                    "--sub-langs", "tr,en,all",  # Türkçe, İngilizce ve diğerleri
                    "--embed-subs",            # Alt yazıları videoya göm
                    "--convert-subs", "srt",   # SRT formatına çevir
                    "--newline",               # Her satır yeni progress
                    "--progress",              # Progress göster
                    "-o", output_template,
                    video['url']
                ]
                
                # Subprocess ile çalıştır ve çıktıyı oku
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                # Progress'i oku
                for line in process.stdout:
                    # Durdurma/duraklama kontrolü
                    while self.is_paused and self.is_downloading:
                        time.sleep(0.5)
                    
                    if not self.is_downloading:
                        process.kill()
                        break
                    
                    # Progress parse et
                    self.parse_progress_line(video_id, line)
                
                process.wait()
                
                if process.returncode == 0:
                    # Başarılı
                    self.cleanup_thumbnail_files(video['title'])
                    self.video_states[video_id] = 'done'
                    self.download_stats['downloaded'] += 1
                    self.after(0, lambda t=video['title']: self.log(f"✅ Tamamlandı: {t[:50]}", "success"))
                else:
                    # Başarısız
                    error_msg = self.get_error_message(process.returncode)
                    self.video_states[video_id] = 'failed'
                    self.video_progress[video_id]['error'] = error_msg
                    self.download_stats['failed'] += 1
                    self.after(0, lambda t=video['title'], e=error_msg: self.log(f"❌ Başarısız: {t[:40]} - {e}", "error"))
            
            except subprocess.TimeoutExpired:
                self.video_states[video_id] = 'failed'
                self.video_progress[video_id]['error'] = "Zaman aşımı (60 saniye)"
                self.download_stats['failed'] += 1
                self.after(0, lambda t=video['title']: self.log(f"⏱️ Zaman aşımı: {t[:40]}", "warning"))
            
            except Exception as e:
                self.video_states[video_id] = 'failed'
                error_msg = str(e)[:100]
                self.video_progress[video_id]['error'] = error_msg
                self.download_stats['failed'] += 1
                self.after(0, lambda t=video['title'], e=error_msg: self.log(f"❌ Hata: {t[:40]} - {e}", "error"))
            
            finally:
                self.current_downloading_id = None
                self.after(0, self.create_video_cards)
                self.after(0, self.update_download_stats)
        
        # Tamamlandı
        self.is_downloading = False
        self.is_paused = False
        self.after(0, lambda: self.start_btn.configure(state="normal"))
        self.after(0, lambda: self.stop_btn.configure(state="disabled"))
        self.after(0, lambda: self.pause_btn.configure(state="disabled"))
        
        # Özet
        elapsed = time.time() - self.download_stats['start_time']
        elapsed_str = str(timedelta(seconds=int(elapsed)))
        
        self.after(0, lambda: self.log(
            f"✅ Tamamlandı! "
            f"İndirilen: {self.download_stats['downloaded']}, "
            f"Başarısız: {self.download_stats['failed']}, "
            f"Atlanan: {self.download_stats['skipped']}, "
            f"Süre: {elapsed_str}",
            "success"
        ))
        
        # Thumbnail temizliği
        self.after(0, self.final_thumbnail_cleanup)
    
    def scan_existing_videos(self):
        """Klasördeki mevcut videoları tara ve atla"""
        if not self.download_folder or not self.download_folder.exists():
            return
        
        # Tüm video dosyalarını al
        video_extensions = ['.mp4', '.mkv', '.webm', '.avi', '.mov', '.flv', '.m4v']
        existing_files = []
        
        for ext in video_extensions:
            existing_files.extend(self.download_folder.glob(f"*{ext}"))
        
        # Video ID'lerini çıkar (YouTube video ID'leri genelde 11 karakter)
        existing_ids = set()
        for file in existing_files:
            filename = file.stem
            # Dosya adından video ID'yi bulmaya çalış
            # YouTube video ID formatı: 11 karakter, [A-Za-z0-9_-]
            import re
            match = re.search(r'[A-Za-z0-9_-]{11}', filename)
            if match:
                existing_ids.add(match.group())
        
        # Videoları kontrol et ve atla
        skipped = 0
        for video in self.all_videos:
            video_id = video['id']
            
            # ID eşleşmesi var mı?
            if video_id in existing_ids:
                self.video_states[video_id] = 'skipped'
                self.download_stats['skipped'] += 1
                skipped += 1
                continue
            
            # Başlık eşleşmesi var mı? (daha esnek)
            video_title = video['title']
            for file in existing_files:
                # Dosya adında video başlığı var mı?
                if self.normalize_title(video_title) in self.normalize_title(file.stem):
                    # Dosya boyutu yeterli mi? (500 KB'den büyük)
                    if file.stat().st_size > MIN_FILE_SIZE:
                        self.video_states[video_id] = 'skipped'
                        self.download_stats['skipped'] += 1
                        skipped += 1
                        break
    
    def normalize_title(self, title: str) -> str:
        """Başlığı normalize et (karşılaştırma için)"""
        # Küçük harfe çevir, özel karakterleri kaldır
        import re
        title = title.lower()
        title = re.sub(r'[^\w\s]', '', title)  # Sadece harf, rakam, boşluk
        title = re.sub(r'\s+', ' ', title).strip()  # Çoklu boşlukları tek yap
        return title
    
    def parse_progress_line(self, video_id: str, line: str):
        """yt-dlp progress satırını parse et"""
        try:
            # [download]  45.2% of 125.30MiB at 2.50MiB/s ETA 00:25
            if '[download]' in line and '%' in line:
                # Progress yüzde
                import re
                
                # Yüzde
                percent_match = re.search(r'(\d+\.?\d*)%', line)
                if percent_match:
                    progress = float(percent_match.group(1))
                    self.video_progress[video_id]['progress'] = progress
                
                # Boyut
                size_match = re.search(r'of\s+([\d.]+\s*[KMG]iB)', line)
                if size_match:
                    self.video_progress[video_id]['size'] = size_match.group(1)
                
                # Hız
                speed_match = re.search(r'at\s+([\d.]+\s*[KMG]iB/s)', line)
                if speed_match:
                    self.video_progress[video_id]['speed'] = speed_match.group(1)
                
                # ETA
                eta_match = re.search(r'ETA\s+(\d+:\d+)', line)
                if eta_match:
                    self.video_progress[video_id]['eta'] = eta_match.group(1)
                
                # UI güncelle
                self.after(0, self.update_video_progress_ui, video_id)
        
        except Exception:
            pass  # Parse hatası önemsiz
    
    def update_video_progress_ui(self, video_id: str):
        """Video progress UI'ını güncelle"""
        # create_video_cards'ı yeniden çağır (otomatik progress gösterecek)
        self.create_video_cards()
    
    def get_error_message(self, return_code: int) -> str:
        """Hata kodunu açıklama metnine çevir"""
        error_messages = {
            1: "Genel hata",
            2: "Yanlış parametreler",
            403: "Erişim engellendi (üyelik gerekli?)",
            404: "Video bulunamadı",
            429: "Çok fazla istek (rate limit)",
            -1: "İşlem iptal edildi"
        }
        return error_messages.get(return_code, f"Bilinmeyen hata (kod: {return_code})")
    
    def cleanup_thumbnail_files(self, video_title: str):
        """Belirli bir video için thumbnail dosyalarını temizle"""
        try:
            # Video başlığına göre .jpg, .png, .webp dosyalarını ara
            for ext in ['.jpg', '.jpeg', '.png', '.webp']:
                # Dosya adı video başlığıyla eşleşen thumbnail'leri bul
                pattern = f"{video_title}*{ext}"
                for thumb_file in self.download_folder.glob(pattern):
                    try:
                        thumb_file.unlink()
                        self.log(f"🗑️ Thumbnail silindi: {thumb_file.name}", "info")
                    except:
                        pass
        except Exception as e:
            self.log(f"Thumbnail temizleme hatası: {str(e)}", "warning")
    
    def final_thumbnail_cleanup(self):
        """İndirme sonrası tüm thumbnail dosyalarını temizle"""
        try:
            deleted = 0
            for ext in ['.jpg', '.jpeg', '.png', '.webp']:
                for thumb_file in self.download_folder.glob(f"*{ext}"):
                    # Sadece thumbnail dosyalarını sil (video dosyası olmayanlar)
                    # Video dosyaları genelde .mp4, .mkv, .webm olur
                    video_exts = ['.mp4', '.mkv', '.webm', '.avi', '.mov']
                    stem = thumb_file.stem
                    
                    # Aynı isimde video dosyası var mı?
                    has_video = any((self.download_folder / f"{stem}{vext}").exists() for vext in video_exts)
                    
                    if has_video:
                        # Bu thumbnail artık gereksiz
                        try:
                            thumb_file.unlink()
                            deleted += 1
                        except:
                            pass
            
            if deleted > 0:
                self.log(f"🗑️ {deleted} thumbnail dosyası temizlendi", "success")
        except Exception as e:
            self.log(f"Final temizleme hatası: {str(e)}", "warning")


# ═══════════════════════════════════════════════════════════════════════════
# PROGRAM BAŞLATMA
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = YouTubeDownloader()
    app.mainloop()
