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
import platform
import urllib.request
import zipfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Cookie extraction için
try:
    from cookie_extractor import CookieExtractor
    COOKIE_EXTRACTOR_AVAILABLE = True
except ImportError:
    COOKIE_EXTRACTOR_AVAILABLE = False

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
        self.archive_file = Path("download_archive.txt")  # yt-dlp archive sistemi
        
        # FFmpeg yönetimi
        self.ffmpeg_path = None
        self.setup_ffmpeg()
        
        # Playlist ve video verileri
        self.playlists: List[Dict] = []
        self.all_videos: List[Dict] = []
        self.video_states: Dict[str, str] = {}
        
        # İndirme durumu
        self.is_downloading = False
        self.is_paused = False  # Duraklama durumu
        self.current_video_index = 0
        self.download_folder = None
        
        # Concurrent downloads ayarları
        self.concurrent_videos = 2  # Aynı anda indirilecek video sayısı
        self.concurrent_fragments = 4  # Paralel fragment sayısı
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
        
        # Thumbnail cache
        self.thumbnail_cache: Dict[str, any] = {}  # {url: CTkImage}
        
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
    
    def setup_ffmpeg(self):
        """FFmpeg'i kur ve yapılandır"""
        if platform.system() == "Windows":
            # Windows: Yerel FFmpeg kullan
            ffmpeg_dir = Path.cwd() / "ffmpeg"
            ffmpeg_dir.mkdir(exist_ok=True)
            self.ffmpeg_path = ffmpeg_dir / "ffmpeg.exe"
            
            # FFmpeg yoksa indir
            if not self.ffmpeg_path.exists():
                if not self.check_system_ffmpeg():
                    # Arka planda indir (kullanıcıyı bekletme)
                    threading.Thread(target=self._download_ffmpeg_windows, args=(ffmpeg_dir,), daemon=True).start()
                else:
                    self.ffmpeg_path = "ffmpeg"  # Sistem FFmpeg kullan
        else:
            # Linux/macOS: Sistem FFmpeg kullan
            if self.check_system_ffmpeg():
                self.ffmpeg_path = "ffmpeg"
            else:
                self.ffmpeg_path = None
                self.log("⚠️ FFmpeg bulunamadı. Video/audio birleştirme çalışmayabilir.", "warning")
    
    def check_system_ffmpeg(self) -> bool:
        """Sistem FFmpeg'i kontrol et"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            return result.returncode == 0
        except:
            return False
    
    def _download_ffmpeg_windows(self, ffmpeg_dir: Path):
        """Windows için FFmpeg indir"""
        try:
            self.log("📥 FFmpeg indiriliyor... (İlk kullanımda)", "info")
            ffmpeg_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
            zip_path = ffmpeg_dir / "ffmpeg.zip"
            
            # ZIP'i indir
            urllib.request.urlretrieve(ffmpeg_url, zip_path)
            
            # ZIP'i çıkar
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(ffmpeg_dir)
            
            # ZIP'i sil
            zip_path.unlink()
            
            # Çıkarılan klasörü bul
            extracted_dir = None
            for item in ffmpeg_dir.iterdir():
                if item.is_dir() and item.name.startswith("ffmpeg"):
                    extracted_dir = item
                    break
            
            if extracted_dir:
                # ffmpeg.exe'yi doğru yere kopyala
                bin_dir = extracted_dir / "bin"
                if (bin_dir / "ffmpeg.exe").exists():
                    shutil.copy2(bin_dir / "ffmpeg.exe", self.ffmpeg_path)
                    # Çıkarılan klasörü sil
                    shutil.rmtree(extracted_dir)
                    self.log("✅ FFmpeg başarıyla indirildi ve kuruldu!", "success")
                else:
                    self.log("❌ FFmpeg indirme hatası: ffmpeg.exe bulunamadı", "error")
            else:
                self.log("❌ FFmpeg indirme hatası: Çıkarılan klasör bulunamadı", "error")
        
        except Exception as e:
            self.log(f"❌ FFmpeg indirme hatası: {str(e)}", "error")
            # Sistem FFmpeg'i dene
            if self.check_system_ffmpeg():
                self.ffmpeg_path = "ffmpeg"
                self.log("✅ Sistem FFmpeg kullanılıyor", "success")
    
    def check_ffmpeg(self) -> bool:
        """FFmpeg'in mevcut olup olmadığını kontrol et"""
        # Yerel FFmpeg kontrolü
        if self.ffmpeg_path and isinstance(self.ffmpeg_path, Path) and self.ffmpeg_path.exists():
            try:
                result = subprocess.run(
                    [str(self.ffmpeg_path), "-version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                return result.returncode == 0
            except:
                pass
        
        # Sistem FFmpeg kontrolü
        return self.check_system_ffmpeg()
    
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
        
        # UI'da göster (indirme ekranındaki log_text_widget varsa onu kullan)
        if hasattr(self, 'log_text_widget') and self.log_text_widget.winfo_exists():
            try:
                self.log_text_widget.configure(state="normal")
                self.log_text_widget.insert("end", formatted + "\n")
                
                # Max 500 satır tut
                lines = self.log_text_widget.get("1.0", "end").split('\n')
                if len(lines) > 500:
                    self.log_text_widget.delete("1.0", f"{len(lines)-500}.0")
                
                self.log_text_widget.see("end")
                self.log_text_widget.configure(state="disabled")
            except:
                pass
        elif hasattr(self, 'log_text'):
            self.log_text.configure(state="normal")
            self.log_text.insert("end", formatted + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        
        # Dosyaya kaydet
        self.log_to_file(message, level.upper())
    
    def clear_log_display(self):
        """Log ekranını temizle"""
        try:
            if hasattr(self, 'log_text_widget'):
                self.log_text_widget.configure(state="normal")
                self.log_text_widget.delete("1.0", "end")
                self.log_text_widget.configure(state="disabled")
                self.log("📋 Log ekranı temizlendi", "info")
        except:
            pass
    
    def load_thumbnail(self, url: str, size: Tuple[int, int] = (60, 34)) -> Optional[ctk.CTkImage]:
        """
        URL'den thumbnail yükle ve cache'le
        
        Args:
            url: Thumbnail URL
            size: Boyut (width, height)
            
        Returns:
            CTkImage veya None
        """
        if not PIL_AVAILABLE or not url:
            return None
        
        # Cache'de var mı?
        cache_key = f"{url}_{size[0]}x{size[1]}"
        if cache_key in self.thumbnail_cache:
            return self.thumbnail_cache[cache_key]
        
        try:
            # URL'den indir
            with urllib.request.urlopen(url, timeout=5) as response:
                image_data = response.read()
            
            # PIL Image oluştur
            image = Image.open(BytesIO(image_data))
            image = image.convert("RGB")
            
            # CTkImage oluştur
            ctk_image = ctk.CTkImage(
                light_image=image,
                dark_image=image,
                size=size
            )
            
            # Cache'e ekle
            self.thumbnail_cache[cache_key] = ctk_image
            return ctk_image
            
        except Exception as e:
            # Thumbnail yükleme başarısız (sessizce geç)
            return None
    
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
        
        # Content area - Kompakt
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=8)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)
        
        # Footer
        self.create_footer()
    
    def create_header(self):
        """Üst başlık alanı - Kompakt"""
        header = ctk.CTkFrame(self, height=70, fg_color=COLORS['bg_card'], corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(1, weight=1)
        
        # Sol: Logo - Kompakt
        logo_frame = ctk.CTkFrame(header, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=15, pady=12, sticky="w")
        
        ctk.CTkLabel(
            logo_frame,
            text="🎬 YouTube Downloader",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(side="left", padx=5)
        
        ctk.CTkLabel(
            logo_frame,
            text="V4 Clean",
            font=ctk.CTkFont(size=11),
            text_color=COLORS['text_secondary']
        ).pack(side="left")
        
        # Orta: Adım göstergeleri
        self.create_step_indicators(header)
    
    def create_step_indicators(self, parent):
        """Adım göstergeleri - Kompakt"""
        steps_frame = ctk.CTkFrame(parent, fg_color="transparent")
        steps_frame.grid(row=0, column=1, pady=12)
        
        self.step_dots = []
        self.step_labels = []
        steps = [
            ("🍪", "Cookie"),
            ("📋", "Playlist"),
            ("⬇️", "İndirme")
        ]
        
        for i, (icon, text) in enumerate(steps):
            # Container - Kompakt
            step_container = ctk.CTkFrame(steps_frame, fg_color="transparent")
            step_container.grid(row=0, column=i*2, padx=6)
            
            # Dot - Kompakt
            dot = ctk.CTkLabel(
                step_container,
                text="●",
                font=ctk.CTkFont(size=18),
                text_color=COLORS['text_secondary']
            )
            dot.pack()
            self.step_dots.append(dot)
            
            # Label - Kompakt
            label = ctk.CTkLabel(
                step_container,
                text=f"{icon} {text}",
                font=ctk.CTkFont(size=9),
                text_color=COLORS['text_secondary']
            )
            label.pack(pady=(3, 0))
            self.step_labels.append(label)
            
            # Bağlantı çizgisi (sonuncu hariç) - Kompakt
            if i < len(steps) - 1:
                line = ctk.CTkLabel(
                    steps_frame,
                    text="━━",
                    font=ctk.CTkFont(size=12),
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
        """Cookie adımı - Kompakt ve modern"""
        container = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Başlık - Daha küçük
        ctk.CTkLabel(
            container,
            text="🍪 Cookie Yükleme",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(pady=(0, 5))
        
        ctk.CTkLabel(
            container,
            text="YouTube üye videoları için cookie gerekli",
            font=ctk.CTkFont(size=11),
            text_color=COLORS['text_secondary']
        ).pack(pady=(0, 15))
        
        # Cookie durum kartı - Kompakt
        status_card = ctk.CTkFrame(
            container,
            fg_color=COLORS['bg_card'],
            corner_radius=8,
            border_width=1,
            border_color=COLORS['border']
        )
        status_card.pack(fill="x", pady=(0, 15))
        
        status_content = ctk.CTkFrame(status_card, fg_color="transparent")
        status_content.pack(fill="x", padx=15, pady=12)
        
        # Icon ve durum - Yatay düzen
        status_row = ctk.CTkFrame(status_content, fg_color="transparent")
        status_row.pack(fill="x")
        
        self.cookie_icon = ctk.CTkLabel(
            status_row,
            text="❓",
            font=ctk.CTkFont(size=24)
        )
        self.cookie_icon.pack(side="left", padx=(0, 10))
        
        status_text_col = ctk.CTkFrame(status_row, fg_color="transparent")
        status_text_col.pack(side="left", fill="x", expand=True)
        
        self.cookie_status_label = ctk.CTkLabel(
            status_text_col,
            text="Cookie durumu kontrol ediliyor...",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS['text_primary'],
            anchor="w"
        )
        self.cookie_status_label.pack(anchor="w")
        
        self.cookie_detail_label = ctk.CTkLabel(
            status_text_col,
            text="",
            font=ctk.CTkFont(size=10),
            text_color=COLORS['text_secondary'],
            anchor="w"
        )
        self.cookie_detail_label.pack(anchor="w", pady=(2, 0))
        
        # Cookie yükleme alanı - Kompakt
        load_frame = ctk.CTkFrame(container, fg_color=COLORS['bg_card'], corner_radius=8)
        load_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        ctk.CTkLabel(
            load_frame,
            text="Cookie JSON'unu Yapıştırın",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(pady=(12, 5), padx=15)
        
        ctk.CTkLabel(
            load_frame,
            text="EditThisCookie → Export → JSON",
            font=ctk.CTkFont(size=9),
            text_color=COLORS['text_secondary']
        ).pack(pady=(0, 8), padx=15)
        
        # Text area - Daha küçük
        self.cookie_textbox = ctk.CTkTextbox(
            load_frame,
            height=150,
            font=ctk.CTkFont(family="Consolas", size=10),
            fg_color=COLORS['bg_dark'],
            border_width=1,
            border_color=COLORS['border']
        )
        self.cookie_textbox.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        self.cookie_textbox.insert("1.0", '[\n  {\n    "name": "HSID",\n    "value": "...",\n    "domain": ".youtube.com"\n  }\n]')
        
        # Butonlar - Kompakt
        button_frame = ctk.CTkFrame(load_frame, fg_color="transparent")
        button_frame.pack(fill="x", padx=15, pady=(0, 12))
        
        # Otomatik cookie extraction butonu
        ctk.CTkButton(
            button_frame,
            text="🌐 Browser'dan Otomatik Çıkar",
            height=38,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#4FC3F7",
            hover_color="#29B6F6",
            text_color="white",
            command=self.extract_cookies_from_browser
        ).pack(fill="x", pady=(0, 6))
        
        ctk.CTkButton(
            button_frame,
            text="💾 Kaydet ve Test Et",
            height=36,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS['success'],
            hover_color=COLORS['success'],
            command=self.save_cookie_and_continue
        ).pack(fill="x", pady=(0, 6))
        
        button_frame2 = ctk.CTkFrame(load_frame, fg_color="transparent")
        button_frame2.pack(fill="x", padx=15, pady=(0, 12))
        
        ctk.CTkButton(
            button_frame2,
            text="📂 Dosyadan Yükle",
            height=32,
            font=ctk.CTkFont(size=11),
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary'],
            command=self.load_cookie_from_file
        ).pack(side="left", expand=True, fill="x", padx=(0, 4))
        
        ctk.CTkButton(
            button_frame2,
            text="❓ Yardım",
            height=32,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            border_width=1,
            border_color=COLORS['border'],
            hover_color=COLORS['bg_hover'],
            command=self.show_cookie_help
        ).pack(side="left", expand=True, fill="x", padx=4)
        
        ctk.CTkButton(
            button_frame2,
            text="⏭️ Atla",
            height=32,
            font=ctk.CTkFont(size=11),
            fg_color=COLORS['warning'],
            hover_color=COLORS['warning'],
            command=lambda: self.show_step(1)
        ).pack(side="left", expand=True, fill="x", padx=(4, 0))
        
        # Mevcut cookie'yi kontrol et
        self.check_cookie_status(status_card)
        
        # Sistem bilgisi footer
        system_info_frame = ctk.CTkFrame(container, fg_color=COLORS['bg_card'], corner_radius=8)
        system_info_frame.pack(fill="x", pady=(10, 0))
        
        system_content = ctk.CTkFrame(system_info_frame, fg_color="transparent")
        system_content.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(
            system_content,
            text="⚙️ Sistem Durumu",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(anchor="w", pady=(0, 5))
        
        self.cookie_screen_system_status = ctk.CTkLabel(
            system_content,
            text="Kontrol ediliyor...",
            font=ctk.CTkFont(size=9),
            text_color=COLORS['text_secondary'],
            anchor="w"
        )
        self.cookie_screen_system_status.pack(anchor="w")
        
        # Hızlı sistem kontrolü
        self.after(500, self.update_cookie_screen_system_status)
    
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

                else:
                    self.cookie_icon.configure(text="⚠️")
                    self.cookie_status_label.configure(
                        text="Eksik Cookie",
                        text_color=COLORS['warning']
                    )
                    self.cookie_detail_label.configure(
                        text=f"Sadece {len(found)}/{len(required)} cookie bulundu"
                    )

            except:
                self.cookie_icon.configure(text="❌")
                self.cookie_status_label.configure(
                    text="Hatalı Cookie Dosyası",
                    text_color=COLORS['danger']
                )

        else:
            self.cookie_icon.configure(text="❌")
            self.cookie_status_label.configure(
                text="Cookie Yok",
                text_color=COLORS['danger']
            )
            self.cookie_detail_label.configure(
                text="Lütfen cookie yükleyin"
            )

    
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
    
    def extract_cookies_from_browser(self):
        """Browser'dan otomatik cookie çıkar"""
        if not COOKIE_EXTRACTOR_AVAILABLE:
            messagebox.showerror(
                "❌ Özellik Mevcut Değil",
                "Cookie extractor modülü bulunamadı!\n\n"
                "Lütfen cookie_extractor.py dosyasının mevcut olduğundan emin olun."
            )
            return
        
        # Loading dialog
        loading = ctk.CTkToplevel(self)
        loading.title("Cookie Çıkarılıyor...")
        loading.geometry("450x200")
        loading.transient(self)
        loading.grab_set()
        
        status_label = ctk.CTkLabel(
            loading,
            text="🌐 Browser'dan cookie'ler çıkarılıyor...",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        status_label.pack(pady=30)
        
        detail_label = ctk.CTkLabel(
            loading,
            text="Edge → Chrome → Firefox sırasıyla deneniyor...",
            font=ctk.CTkFont(size=11),
            text_color=COLORS['text_secondary']
        )
        detail_label.pack(pady=10)
        
        progress = ctk.CTkProgressBar(loading, mode="indeterminate")
        progress.pack(pady=20, padx=40, fill="x")
        progress.start()
        
        def extract_thread():
            try:
                extractor = CookieExtractor(output_file=str(self.cookie_file))
                
                # Önce Edge'i dene
                self.after(0, lambda: detail_label.configure(text="Edge tarayıcısı kontrol ediliyor..."))
                success = extractor.extract_cookies(browser="edge")
                
                if not success:
                    # Chrome'u dene
                    self.after(0, lambda: detail_label.configure(text="Chrome tarayıcısı kontrol ediliyor..."))
                    success = extractor.extract_cookies(browser="chrome")
                
                if not success:
                    # Firefox'u dene
                    self.after(0, lambda: detail_label.configure(text="Firefox tarayıcısı kontrol ediliyor..."))
                    success = extractor.extract_cookies(browser="firefox")
                
                self.after(0, loading.destroy)
                
                if success:
                    # Cookie dosyasını kontrol et - gerçekten içerik var mı?
                    try:
                        with open(self.cookie_file, 'r', encoding='utf-8') as f:
                            cookie_content = f.read()
                        
                        # Dosya boş mu veya sadece header mı kontrol et
                        lines = [line.strip() for line in cookie_content.split('\n') if line.strip() and not line.strip().startswith('#')]
                        
                        if len(lines) < 3:  # En az 3 cookie satırı olmalı
                            self.after(0, loading.destroy)
                            self.after(0, lambda: self.log("❌ Cookie dosyası boş veya geçersiz!", "error"))
                            self.after(0, lambda: messagebox.showerror(
                                "❌ Cookie Çıkarılamadı",
                                "Cookie dosyası oluşturuldu ancak içerik bulunamadı!\n\n"
                                "Olası nedenler:\n"
                                "• YouTube'a giriş yapmamış olabilirsiniz\n"
                                "• Browser'da YouTube cookie'leri yok\n"
                                "• Browser açıkken cookie dosyasına erişilemiyor olabilir\n\n"
                                "Çözüm:\n"
                                "• YouTube'a giriş yapın ve bir video izleyin\n"
                                "• Browser'ı kapatıp tekrar deneyin\n"
                                "• Manuel olarak cookie export edin"
                            ))
                            return
                        
                        # Başarılı - cookie'ler var
                        self.after(0, loading.destroy)
                        self.after(0, lambda: self.log(f"✅ Cookie'ler browser'dan başarıyla çıkarıldı! ({len(lines)} cookie)", "success"))
                        self.after(0, lambda: messagebox.showinfo(
                            "✅ Başarılı",
                            f"Cookie'ler browser'dan başarıyla çıkarıldı!\n\n"
                            f"✓ {len(lines)} cookie bulundu\n"
                            f"✓ Dosya: {self.cookie_file.name}\n\n"
                            "Cookie'ler Netscape formatında kaydedildi ve hazır.\n"
                            "Şimdi playlist ekleyebilirsiniz."
                        ))
                    except Exception as e:
                        self.after(0, loading.destroy)
                        self.after(0, lambda: self.log(f"❌ Cookie dosyası okunamadı: {str(e)}", "error"))
                        self.after(0, lambda: messagebox.showerror(
                            "❌ Hata",
                            f"Cookie dosyası okunamadı:\n\n{str(e)}"
                        ))
                        return
                    
                    # Cookie durumunu güncelle
                    if hasattr(self, 'cookie_status_label'):
                        self.after(0, lambda: self.check_cookie_status(
                            self.content_frame.winfo_children()[0].winfo_children()[0] 
                            if self.content_frame.winfo_children() else None
                        ))
                else:
                    self.after(0, lambda: self.log("❌ Cookie çıkarılamadı!", "error"))
                    self.after(0, lambda: messagebox.showerror(
                        "❌ Cookie Çıkarılamadı",
                        "Browser'dan cookie çıkarılamadı!\n\n"
                        "Olası nedenler:\n"
                        "• YouTube'a giriş yapmamış olabilirsiniz\n"
                        "• Browser açıkken cookie dosyasına erişilemiyor olabilir\n"
                        "• Edge/Chrome/Firefox yüklü değil olabilir\n\n"
                        "Çözüm:\n"
                        "• YouTube'a giriş yapın\n"
                        "• Browser'ı kapatıp tekrar deneyin\n"
                        "• Manuel olarak cookie export edin (EditThisCookie uzantısı)"
                    ))
            except Exception as e:
                self.after(0, loading.destroy)
                self.after(0, lambda: self.log(f"❌ Cookie extraction hatası: {str(e)}", "error"))
                self.after(0, lambda: messagebox.showerror(
                    "❌ Hata",
                    f"Cookie çıkarılırken hata oluştu:\n\n{str(e)}\n\n"
                    "Lütfen manuel olarak cookie export edin."
                ))
        
        thread = threading.Thread(target=extract_thread, daemon=True)
        thread.start()
    
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
        """Adım 2: Playlist/Video ekleme - Kompakt"""
        container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=15, pady=8)
        
        # Başlık ve butonlar - Kompakt
        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))
        
        # Sol: Başlık
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left")
        
        ctk.CTkLabel(
            title_frame,
            text="📋 Playlist Ekleme",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            title_frame,
            text="Her satıra bir YouTube linki (playlist veya video)",
            font=ctk.CTkFont(size=10),
            text_color=COLORS['text_secondary']
        ).pack(anchor="w", pady=(2, 0))
        
        # Sağ: Butonlar - Kompakt
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right")
        
        ctk.CTkButton(
            btn_frame,
            text="◀️ Geri",
            height=32,
            width=80,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            border_width=1,
            border_color=COLORS['border'],
            hover_color=COLORS['bg_hover'],
            command=lambda: self.show_step(0)
        ).pack(side="left", padx=3)
        
        ctk.CTkButton(
            btn_frame,
            text="▶️ İndirmeye Geç",
            height=40,
            width=140,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS['success'],
            hover_color=COLORS['success'],
            command=self.go_to_download
        ).pack(side="left", padx=3)
        
        # Ana içerik - 2 sütun
        content = ctk.CTkFrame(container, fg_color="transparent")
        content.pack(fill="both", expand=True)
        content.grid_columnconfigure(0, weight=2)
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=1)
        
        # Sol: Link girişi - Kompakt
        left_panel = ctk.CTkFrame(content, fg_color=COLORS['bg_card'], corner_radius=8)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        
        ctk.CTkLabel(
            left_panel,
            text="Link Ekle",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(pady=(12, 5), padx=15)
        
        ctk.CTkLabel(
            left_panel,
            text="Her satıra bir link",
            font=ctk.CTkFont(size=9),
            text_color=COLORS['text_secondary']
        ).pack(pady=(0, 8), padx=15)
        
        # Text area - Kompakt
        self.playlist_textbox = ctk.CTkTextbox(
            left_panel,
            font=ctk.CTkFont(family="Consolas", size=10),
            fg_color=COLORS['bg_dark'],
            border_width=1,
            border_color=COLORS['border']
        )
        self.playlist_textbox.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        
        # Placeholder
        placeholder_text = "https://www.youtube.com/playlist?list=PLxxxxxx\nhttps://www.youtube.com/watch?v=xxxxxx\nhttps://www.youtube.com/playlist?list=PLyyyyyy"
        self.playlist_textbox.insert("1.0", placeholder_text)
        
        # İlk tıklamada placeholder'ı temizle
        def clear_placeholder(event):
            if self.playlist_textbox.get("1.0", "end-1c") == placeholder_text:
                self.playlist_textbox.delete("1.0", "end")
            self.playlist_textbox.unbind("<Button-1>")
        
        self.playlist_textbox.bind("<Button-1>", clear_placeholder)
        
        # Butonlar - Kompakt
        big_button_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        big_button_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        ctk.CTkButton(
            big_button_frame,
            text="✅ LİNKLERİ EKLE VE BİLGİLERİ ÇEK",
            height=42,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS['success'],
            hover_color="#2d8a3e",
            text_color="white",
            corner_radius=6,
            command=self.add_playlists
        ).pack(fill="x", pady=(0, 5))
        
        # Temizle butonu
        ctk.CTkButton(
            big_button_frame,
            text="🗑️ Temizle",
            height=32,
            font=ctk.CTkFont(size=11),
            fg_color=COLORS['danger'],
            hover_color="#c92a2a",
            command=self.clear_playlists
        ).pack(fill="x")
        
        # Ayarlar - Kompakt
        settings_frame = ctk.CTkFrame(left_panel, fg_color=COLORS['bg_dark'], corner_radius=6)
        settings_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        settings_content = ctk.CTkFrame(settings_frame, fg_color="transparent")
        settings_content.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            settings_content,
            text="Video Kalitesi",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(anchor="w", pady=(0, 6))
        
        # Kalite - Kompakt
        quality_frame = ctk.CTkFrame(settings_content, fg_color="transparent")
        quality_frame.pack(fill="x", pady=2)
        
        self.quality_var = ctk.StringVar(value="best")
        quality_options = [
            ("En İyi", "best"),
            ("4K", "4K"),
            ("1440p", "1440p"),
            ("1080p", "1080p"),
            ("720p", "720p"),
            ("480p", "480p"),
            ("360p", "360p"),
            ("En Düşük", "worst")
        ]
        
        # İki satırda göster - Kompakt
        row1 = ctk.CTkFrame(quality_frame, fg_color="transparent")
        row1.pack(fill="x", pady=1)
        row2 = ctk.CTkFrame(quality_frame, fg_color="transparent")
        row2.pack(fill="x", pady=1)
        
        for i, (label, value) in enumerate(quality_options):
            row = row1 if i < 4 else row2
            ctk.CTkRadioButton(
                row,
                text=label,
                variable=self.quality_var,
                value=value,
                font=ctk.CTkFont(size=10)
            ).pack(side="left", padx=3)
        
        # Video/Audio Merge Checkbox - Kompakt
        self.merge_video_audio_var = ctk.BooleanVar(value=True)
        merge_checkbox = ctk.CTkCheckBox(
            settings_content,
            text="Video/Audio Birleştir",
            variable=self.merge_video_audio_var,
            font=ctk.CTkFont(size=10)
        )
        merge_checkbox.pack(anchor="w", pady=(6, 3))
        
        # Alt Yazı Ayarları - Kompakt
        subtitle_frame = ctk.CTkFrame(settings_content, fg_color=COLORS['bg_card'], corner_radius=6)
        subtitle_frame.pack(fill="x", pady=(6, 0))
        
        subtitle_content = ctk.CTkFrame(subtitle_frame, fg_color="transparent")
        subtitle_content.pack(fill="x", padx=8, pady=8)
        
        ctk.CTkLabel(
            subtitle_content,
            text="Alt Yazı",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(anchor="w", pady=(0, 5))
        
        # Download Subtitles - Kompakt
        self.download_subs_var = ctk.BooleanVar(value=True)
        subs_checkbox = ctk.CTkCheckBox(
            subtitle_content,
            text="Alt Yazı İndir",
            variable=self.download_subs_var,
            font=ctk.CTkFont(size=10),
            command=lambda: self._update_subtitle_dropdowns()
        )
        subs_checkbox.pack(anchor="w", pady=1)
        
        # Subtitle Language Dropdown - Kompakt
        subtitle_lang_frame = ctk.CTkFrame(subtitle_content, fg_color="transparent")
        subtitle_lang_frame.pack(anchor="w", pady=(3, 1), padx=(18, 0))
        
        ctk.CTkLabel(
            subtitle_lang_frame,
            text="Dil:",
            font=ctk.CTkFont(size=9),
            text_color=COLORS['text_secondary']
        ).pack(side="left", padx=(0, 4))
        
        # Dropdown label mapping
        lang_labels = {
            "tr": "Türkçe",
            "en": "English",
            "all": "Tüm Diller",
            "es": "Español",
            "fr": "Français",
            "de": "Deutsch",
            "it": "Italiano",
            "pt": "Português",
            "ru": "Русский",
            "ja": "日本語",
            "ko": "한국어",
            "zh": "中文",
            "ar": "العربية",
            "hi": "हिन्दी"
        }
        
        # Subtitle language dropdown values (görünen isimlerle)
        subtitle_lang_values = [
            "tr - Türkçe", "en - English", "all - Tüm Diller",
            "es - Español", "fr - Français", "de - Deutsch",
            "it - Italiano", "pt - Português", "ru - Русский",
            "ja - 日本語", "ko - 한국어", "zh - 中文",
            "ar - العربية", "hi - हिन्दी"
        ]
        
        self.subtitle_language_var = ctk.StringVar(value="tr - Türkçe")
        self.subtitle_language_dropdown = ctk.CTkComboBox(
            subtitle_lang_frame,
            values=subtitle_lang_values,
            variable=self.subtitle_language_var,
            width=160,
            height=26,
            font=ctk.CTkFont(size=9),
            state="normal" if self.download_subs_var.get() else "disabled"
        )
        self.subtitle_language_dropdown.pack(side="left")
        
        # Auto-translate Subtitles - Kompakt
        self.auto_subs_var = ctk.BooleanVar(value=False)
        auto_subs_checkbox = ctk.CTkCheckBox(
            subtitle_content,
            text="Otomatik Çeviri",
            variable=self.auto_subs_var,
            font=ctk.CTkFont(size=10),
            command=lambda: self._update_subtitle_dropdowns()
        )
        auto_subs_checkbox.pack(anchor="w", pady=(4, 1))
        
        # Auto-translate Language Dropdown - Kompakt
        auto_translate_lang_frame = ctk.CTkFrame(subtitle_content, fg_color="transparent")
        auto_translate_lang_frame.pack(anchor="w", pady=(3, 1), padx=(18, 0))
        
        ctk.CTkLabel(
            auto_translate_lang_frame,
            text="Çeviri:",
            font=ctk.CTkFont(size=9),
            text_color=COLORS['text_secondary']
        ).pack(side="left", padx=(0, 4))
        
        # Auto-translate language dropdown values (görünen isimlerle)
        auto_translate_lang_values = [
            "tr - Türkçe", "en - English", "es - Español", "fr - Français",
            "de - Deutsch", "it - Italiano", "pt - Português", "ru - Русский",
            "ja - 日本語", "ko - 한국어", "zh - 中文", "ar - العربية", "hi - हिन्दी"
        ]
        
        self.auto_translate_language_var = ctk.StringVar(value="tr - Türkçe")
        self.auto_translate_language_dropdown = ctk.CTkComboBox(
            auto_translate_lang_frame,
            values=auto_translate_lang_values,
            variable=self.auto_translate_language_var,
            width=160,
            height=26,
            font=ctk.CTkFont(size=9),
            state="disabled"
        )
        self.auto_translate_language_dropdown.pack(side="left")
        
        # Embed Subtitles - Kompakt
        self.embed_subs_var = ctk.BooleanVar(value=True)
        embed_subs_checkbox = ctk.CTkCheckBox(
            subtitle_content,
            text="Videoya Göm",
            variable=self.embed_subs_var,
            font=ctk.CTkFont(size=10),
            command=lambda: self._update_subtitle_dropdowns()
        )
        embed_subs_checkbox.pack(anchor="w", pady=(4, 0))
        
        # Sağ: Playlist listesi - Kompakt
        right_panel = ctk.CTkFrame(content, fg_color=COLORS['bg_card'], corner_radius=8)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        
        ctk.CTkLabel(
            right_panel,
            text="Eklenen Listeler",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(pady=(12, 6), padx=15)
        
        # İstatistikler - Kompakt
        self.stats_frame = ctk.CTkFrame(right_panel, fg_color=COLORS['bg_dark'], corner_radius=6)
        self.stats_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        stats_content = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        stats_content.pack(fill="x", padx=10, pady=8)
        
        self.playlist_count_label = ctk.CTkLabel(
            stats_content,
            text="📋 Playlist: 0",
            font=ctk.CTkFont(size=11),
            text_color=COLORS['text_primary']
        )
        self.playlist_count_label.pack(anchor="w", pady=1)
        
        self.video_count_label = ctk.CTkLabel(
            stats_content,
            text="🎥 Video: 0",
            font=ctk.CTkFont(size=11),
            text_color=COLORS['text_primary']
        )
        self.video_count_label.pack(anchor="w", pady=1)
        
        # Playlist scroll - Kompakt
        self.playlist_scroll = ctk.CTkScrollableFrame(
            right_panel,
            fg_color="transparent"
        )
        self.playlist_scroll.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        
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
                                    # Format bilgilerini al
                                    formats = data.get('formats', [])
                                    best_quality = "-"
                                    file_size = "-"
                                    ext = "-"
                                    
                                    if formats:
                                        video_formats = [f for f in formats if f.get('vcodec') != 'none' and f.get('height')]
                                        if video_formats:
                                            best_format = max(video_formats, key=lambda x: (x.get('height', 0), x.get('fps', 0), x.get('tbr', 0)))
                                            best_quality = f"{best_format.get('height', '-')}p"
                                            filesize = best_format.get('filesize', 0) or best_format.get('filesize_approx', 0)
                                            if filesize:
                                                file_size = f"{round(filesize/1024/1024, 2)} MB"
                                            ext = best_format.get('ext', '-')
                                    
                                    videos.append({
                                        'id': data['id'],
                                        'title': data.get('title', 'Video'),
                                        'url': f"https://www.youtube.com/watch?v={data['id']}",
                                        'thumbnail': data.get('thumbnail', ''),
                                        'duration': data.get('duration', 0),
                                        'quality': best_quality,
                                        'size': file_size,
                                        'ext': ext
                                    })
                            except:
                                continue
                        
                        # Tek video ise
                        if not videos and lines:
                            try:
                                data = json.loads(lines[0])
                                if data.get('id'):
                                    # Format bilgilerini al
                                    formats = data.get('formats', [])
                                    best_quality = "-"
                                    file_size = "-"
                                    ext = "-"
                                    
                                    if formats:
                                        video_formats = [f for f in formats if f.get('vcodec') != 'none' and f.get('height')]
                                        if video_formats:
                                            best_format = max(video_formats, key=lambda x: (x.get('height', 0), x.get('fps', 0), x.get('tbr', 0)))
                                            best_quality = f"{best_format.get('height', '-')}p"
                                            filesize = best_format.get('filesize', 0) or best_format.get('filesize_approx', 0)
                                            if filesize:
                                                file_size = f"{round(filesize/1024/1024, 2)} MB"
                                            ext = best_format.get('ext', '-')
                                    
                                    videos.append({
                                        'id': data['id'],
                                        'title': data.get('title', 'Video'),
                                        'url': url,
                                        'thumbnail': data.get('thumbnail', ''),
                                        'duration': data.get('duration', 0),
                                        'quality': best_quality,
                                        'size': file_size,
                                        'ext': ext
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
                    f"📹 Toplam {len(self.all_videos)} video hazır.\n\n"
                    f"➡️ Şimdi sağ üstteki '▶️ İndirmeye Geç' butonuna basın."
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
        """Adım 3: İndirme - Kompakt"""
        container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=15, pady=8)
        
        # Başlık - Kompakt
        header = ctk.CTkFrame(container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(
            header,
            text="⬇️ İndirme",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(side="left")
        
        ctk.CTkButton(
            header,
            text="◀️ Geri",
            height=32,
            width=80,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            border_width=1,
            border_color=COLORS['border'],
            hover_color=COLORS['bg_hover'],
            command=lambda: self.show_step(1)
        ).pack(side="right")
        
        # İstatistik kartları - Kompakt
        stats_container = ctk.CTkFrame(container, fg_color="transparent")
        stats_container.pack(fill="x", pady=(0, 10))
        
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
        
        # Sol: Kontroller - Scroll edilebilir
        left_panel = ctk.CTkScrollableFrame(content, fg_color=COLORS['bg_card'], corner_radius=8)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        
        ctk.CTkLabel(
            left_panel,
            text="İndirme Ayarları",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(pady=(12, 8), padx=15)
        
        # Klasör seçimi - Kompakt
        folder_frame = ctk.CTkFrame(left_panel, fg_color=COLORS['bg_dark'], corner_radius=6)
        folder_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        folder_content = ctk.CTkFrame(folder_frame, fg_color="transparent")
        folder_content.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            folder_content,
            text="İndirme Klasörü",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(anchor="w", pady=(0, 4))
        
        self.folder_label = ctk.CTkLabel(
            folder_content,
            text="Henüz seçilmedi",
            font=ctk.CTkFont(size=9),
            text_color=COLORS['text_secondary'],
            anchor="w"
        )
        self.folder_label.pack(fill="x", pady=(0, 6))
        
        ctk.CTkButton(
            folder_content,
            text="📂 Klasör Seç",
            height=32,
            font=ctk.CTkFont(size=11),
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary'],
            command=self.select_download_folder
        ).pack(fill="x")
        
        # Progress - Kompakt
        progress_frame = ctk.CTkFrame(left_panel, fg_color=COLORS['bg_dark'], corner_radius=6)
        progress_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        progress_content = ctk.CTkFrame(progress_frame, fg_color="transparent")
        progress_content.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            progress_content,
            text="Genel İlerleme",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(anchor="w", pady=(0, 4))
        
        self.overall_progress = ctk.CTkProgressBar(progress_content, mode="determinate", height=18)
        self.overall_progress.pack(fill="x", pady=(0, 4))
        self.overall_progress.set(0)
        
        self.overall_progress_label = ctk.CTkLabel(
            progress_content,
            text="0 / 0 (0%)",
            font=ctk.CTkFont(size=9),
            text_color=COLORS['text_secondary']
        )
        self.overall_progress_label.pack(anchor="w")
        
        # Concurrent Downloads Ayarları - Kompakt
        concurrent_frame = ctk.CTkFrame(left_panel, fg_color=COLORS['bg_dark'], corner_radius=6)
        concurrent_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        concurrent_content = ctk.CTkFrame(concurrent_frame, fg_color="transparent")
        concurrent_content.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            concurrent_content,
            text="Performans",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(anchor="w", pady=(0, 6))
        
        # Concurrent Videos Slider - Kompakt
        ctk.CTkLabel(
            concurrent_content,
            text=f"Video: {self.concurrent_videos}",
            font=ctk.CTkFont(size=9),
            text_color=COLORS['text_secondary']
        ).pack(anchor="w", pady=(0, 3))
        
        self.concurrent_videos_slider = ctk.CTkSlider(
            concurrent_content,
            from_=1,
            to=5,
            number_of_steps=4,
            command=self.update_concurrent_videos_label,
            height=16
        )
        self.concurrent_videos_slider.set(self.concurrent_videos)
        self.concurrent_videos_slider.pack(fill="x", pady=(0, 6))
        
        self.concurrent_videos_label = ctk.CTkLabel(
            concurrent_content,
            text=f"{self.concurrent_videos} video",
            font=ctk.CTkFont(size=9),
            text_color=COLORS['text_secondary']
        )
        self.concurrent_videos_label.pack(anchor="w", pady=(0, 6))
        
        # Concurrent Fragments Slider - Kompakt
        ctk.CTkLabel(
            concurrent_content,
            text=f"Fragment: {self.concurrent_fragments}",
            font=ctk.CTkFont(size=9),
            text_color=COLORS['text_secondary']
        ).pack(anchor="w", pady=(0, 3))
        
        self.concurrent_fragments_slider = ctk.CTkSlider(
            concurrent_content,
            from_=1,
            to=10,
            number_of_steps=9,
            command=self.update_concurrent_fragments_label,
            height=16
        )
        self.concurrent_fragments_slider.set(self.concurrent_fragments)
        self.concurrent_fragments_slider.pack(fill="x", pady=(0, 6))
        
        self.concurrent_fragments_label = ctk.CTkLabel(
            concurrent_content,
            text=f"{self.concurrent_fragments} fragment",
            font=ctk.CTkFont(size=9),
            text_color=COLORS['text_secondary']
        )
        self.concurrent_fragments_label.pack(anchor="w")
        
        # Archive Yönetimi - Kompakt
        archive_frame = ctk.CTkFrame(left_panel, fg_color=COLORS['bg_dark'], corner_radius=6)
        archive_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        archive_content = ctk.CTkFrame(archive_frame, fg_color="transparent")
        archive_content.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            archive_content,
            text="Archive",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(anchor="w", pady=(0, 4))
        
        ctk.CTkLabel(
            archive_content,
            text="Önceki indirmeler atlanır",
            font=ctk.CTkFont(size=9),
            text_color=COLORS['text_secondary']
        ).pack(anchor="w", pady=(0, 6))
        
        ctk.CTkButton(
            archive_content,
            text="🗑️ Temizle",
            height=30,
            font=ctk.CTkFont(size=10),
            fg_color=COLORS['warning'],
            hover_color=COLORS['warning'],
            command=self.clear_archive
        ).pack(fill="x")
        
        # Sistem Sağlık Paneli - Gelişmiş
        system_frame = ctk.CTkFrame(left_panel, fg_color=COLORS['bg_dark'], corner_radius=6)
        system_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        system_content = ctk.CTkFrame(system_frame, fg_color="transparent")
        system_content.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            system_content,
            text="⚕️ Sistem Sağlık",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(anchor="w", pady=(0, 4))
        
        # Sistem durumu göstergesi
        self.system_status_label = ctk.CTkLabel(
            system_content,
            text="Henüz kontrol edilmedi",
            font=ctk.CTkFont(size=9),
            text_color=COLORS['text_secondary'],
            anchor="w",
            justify="left"
        )
        self.system_status_label.pack(anchor="w", pady=(0, 6), fill="x")
        
        button_row = ctk.CTkFrame(system_content, fg_color="transparent")
        button_row.pack(fill="x")
        
        ctk.CTkButton(
            button_row,
            text="🔍 Kontrol",
            height=30,
            width=80,
            font=ctk.CTkFont(size=10),
            fg_color="#9C27B0",
            hover_color="#7B1FA2",
            command=self.show_system_health_dialog
        ).pack(side="left", expand=True, fill="x", padx=(0, 3))
        
        # Archive temizleme butonu
        ctk.CTkButton(
            button_row,
            text="🗑️ Archive",
            height=30,
            width=80,
            font=ctk.CTkFont(size=10),
            fg_color="#FF6B35",
            hover_color="#E55A2B",
            command=self.clear_archive_file
        ).pack(side="left", expand=True, fill="x", padx=(3, 0))
        
        # Otomatik sistem kontrolü (sayfa yüklendiğinde)
        self.after(1000, self.update_system_status_quick)
        
        # Butonlar - Büyük ve Belirgin
        button_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        button_frame.pack(fill="x", padx=15, pady=(10, 15))
        
        self.start_btn = ctk.CTkButton(
            button_frame,
            text="▶️ İNDİRMEYİ BAŞLAT",
            height=50,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            command=self.start_download,
            border_width=2,
            border_color="#34d399"
        )
        self.start_btn.pack(fill="x", pady=(0, 6))
        
        # Duraklat/Devam butonu - Kompakt
        self.pause_btn = ctk.CTkButton(
            button_frame,
            text="⏸️ Duraklat",
            height=34,
            font=ctk.CTkFont(size=11),
            fg_color=COLORS['warning'],
            hover_color=COLORS['warning'],
            command=self.toggle_pause,
            state="disabled"
        )
        self.pause_btn.pack(fill="x", pady=(0, 4))
        
        self.stop_btn = ctk.CTkButton(
            button_frame,
            text="⏹️ Durdur",
            height=34,
            font=ctk.CTkFont(size=11),
            fg_color=COLORS['danger'],
            hover_color=COLORS['danger'],
            command=self.stop_download,
            state="disabled"
        )
        self.stop_btn.pack(fill="x", pady=(0, 4))
        
        ctk.CTkButton(
            button_frame,
            text="🔄 Başarısızları Tekrarla",
            height=32,
            font=ctk.CTkFont(size=11),
            fg_color=COLORS['primary'],
            hover_color=COLORS['primary'],
            command=self.retry_failed
        ).pack(fill="x")
        
        # Sağ: Video listesi ve Log - İki panelli
        right_panel = ctk.CTkFrame(content, fg_color="transparent", corner_radius=8)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        right_panel.grid_rowconfigure(0, weight=2)  # Video listesi (daha büyük)
        right_panel.grid_rowconfigure(1, weight=1)  # Log paneli (daha küçük)
        right_panel.grid_columnconfigure(0, weight=1)
        
        # Üst: Video Listesi
        video_panel = ctk.CTkFrame(right_panel, fg_color=COLORS['bg_card'], corner_radius=8)
        video_panel.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        
        ctk.CTkLabel(
            video_panel,
            text="📋 Video Listesi",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(pady=(12, 6), padx=15)
        
        # Video scroll - Kompakt
        self.video_scroll = ctk.CTkScrollableFrame(
            video_panel,
            fg_color="transparent"
        )
        self.video_scroll.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        
        # Alt: Log Paneli
        log_panel = ctk.CTkFrame(right_panel, fg_color=COLORS['bg_card'], corner_radius=8)
        log_panel.grid(row=1, column=0, sticky="nsew")
        
        log_header = ctk.CTkFrame(log_panel, fg_color="transparent")
        log_header.pack(fill="x", padx=15, pady=(12, 6))
        
        ctk.CTkLabel(
            log_header,
            text="📝 İşlem Günlüğü",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(side="left")
        
        # Temizle butonu
        ctk.CTkButton(
            log_header,
            text="🗑️ Temizle",
            height=24,
            width=70,
            font=ctk.CTkFont(size=9),
            fg_color="transparent",
            border_width=1,
            border_color=COLORS['border'],
            hover_color=COLORS['bg_hover'],
            command=self.clear_log_display
        ).pack(side="right")
        
        # Log text area
        self.log_text_widget = ctk.CTkTextbox(
            log_panel,
            height=150,
            font=ctk.CTkFont(family="Consolas", size=9),
            fg_color=COLORS['bg_dark'],
            wrap="word"
        )
        self.log_text_widget.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.log_text_widget.configure(state="disabled")  # Read-only
        
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
                
                # Video kartı - Durum renkleri
                card_color = COLORS['bg_hover']
                border_color = COLORS['border']
                border_width = 1
                
                if state == 'downloading':
                    card_color = "#1e3a5f"  # Mavi ton
                    border_color = "#4FC3F7"  # Parlak mavi border
                    border_width = 2
                elif state == 'done':
                    card_color = "#1B4332"  # Koyu yeşil
                    border_color = "#43A047"  # Yeşil border
                    border_width = 2
                elif state == 'failed':
                    card_color = "#4a1f1f"  # Kırmızı ton
                    border_color = "#F44336"  # Kırmızı border
                    border_width = 2
                elif state == 'skipped':
                    card_color = "#2d3748"  # Gri ton
                    border_color = "#718096"  # Gri border
                    border_width = 1
                
                video_card = ctk.CTkFrame(
                    self.video_scroll, 
                    fg_color=card_color, 
                    corner_radius=6,
                    border_width=border_width,
                    border_color=border_color
                )
                video_card.pack(fill="x", pady=2, padx=10)
                
                video_content = ctk.CTkFrame(video_card, fg_color="transparent")
                video_content.pack(fill="both", expand=True, padx=10, pady=6)
                
                # Ana satır: Thumbnail + Bilgiler
                main_row = ctk.CTkFrame(video_content, fg_color="transparent")
                main_row.pack(fill="x")
                
                # Thumbnail (gerçek resim veya ikon)
                thumbnail_frame = ctk.CTkFrame(main_row, fg_color=COLORS['bg_dark'], width=60, height=34, corner_radius=3)
                thumbnail_frame.pack(side="left", padx=(0, 8))
                thumbnail_frame.pack_propagate(False)
                
                # Thumbnail yükle (arka planda)
                thumbnail_url = video.get('thumbnail', '')
                thumbnail_image = self.load_thumbnail(thumbnail_url, size=(60, 34)) if thumbnail_url else None
                
                if thumbnail_image:
                    # Gerçek thumbnail
                    thumbnail_label = ctk.CTkLabel(
                        thumbnail_frame,
                        text="",
                        image=thumbnail_image
                    )
                    thumbnail_label.pack(expand=True, fill="both")
                else:
                    # Fallback ikon
                    thumbnail_label = ctk.CTkLabel(
                        thumbnail_frame,
                        text="📹",
                        font=ctk.CTkFont(size=16),
                        text_color=COLORS['text_secondary']
                    )
                    thumbnail_label.pack(expand=True)
                
                # Video bilgileri (sağ taraf)
                info_column = ctk.CTkFrame(main_row, fg_color="transparent")
                info_column.pack(side="left", fill="both", expand=True)
                
                # Üst satır: Başlık ve durum
                top_row = ctk.CTkFrame(info_column, fg_color="transparent")
                top_row.pack(fill="x")
                
                # Video başlığı (daha belirgin)
                v_title = video['title'][:50] + "..." if len(video['title']) > 50 else video['title']
                title_label = ctk.CTkLabel(
                    top_row,
                    text=v_title,
                    font=ctk.CTkFont(size=11, weight="bold" if state == 'downloading' else "normal"),
                    text_color=COLORS['text_primary'],
                    anchor="w"
                )
                title_label.pack(side="left", fill="x", expand=True)
                
                # Durum ikonu ve text (renkli)
                status_icons = {
                    'pending': ('⏳', 'Bekliyor', COLORS['text_secondary']),
                    'downloading': ('⬇️', 'İndiriliyor', '#4FC3F7'),
                    'done': ('✅', 'Tamamlandı', '#43A047'),
                    'failed': ('❌', 'Başarısız', '#F44336'),
                    'skipped': ('⏭️', 'Atlandı', '#718096')
                }
                icon, status_text, status_color = status_icons.get(state, ('⏳', 'Bekliyor', COLORS['text_secondary']))
                
                status_frame = ctk.CTkFrame(top_row, fg_color="transparent")
                status_frame.pack(side="right")
                
                # Durum badge (daha görsel)
                status_badge = ctk.CTkFrame(
                    status_frame,
                    fg_color=status_color if state in ['done', 'failed'] else "transparent",
                    corner_radius=4
                )
                status_badge.pack()
                
                ctk.CTkLabel(
                    status_badge,
                    text=f"{icon} {status_text}",
                    font=ctk.CTkFont(size=10, weight="bold" if state in ['done', 'failed', 'downloading'] else "normal"),
                    text_color="white" if state in ['done', 'failed'] else status_color
                ).pack(padx=6, pady=2)
                
                # Video detay bilgileri (süre, kalite, format, boyut)
                details_row = ctk.CTkFrame(info_column, fg_color="transparent")
                details_row.pack(fill="x", pady=(3, 0))
                
                detail_parts = []
                
                # Süre
                duration = video.get('duration', 0)
                if duration:
                    hours = duration // 3600
                    minutes = (duration % 3600) // 60
                    secs = duration % 60
                    if hours > 0:
                        duration_str = f"{hours:02d}:{minutes:02d}:{secs:02d}"
                    else:
                        duration_str = f"{minutes:02d}:{secs:02d}"
                    detail_parts.append(f"⏱️ {duration_str}")
                else:
                    detail_parts.append("⏱️ -")
                
                # Kalite
                quality = video.get('quality', '-')
                if quality != '-':
                    detail_parts.append(f"📺 {quality}")
                
                # Format
                ext = video.get('ext', '-')
                if ext != '-':
                    detail_parts.append(f"📄 {ext.upper()}")
                
                # Boyut
                size = video.get('size', '-')
                if size != '-':
                    detail_parts.append(f"💾 {size}")
                
                if detail_parts:
                    details_text = " | ".join(detail_parts)
                    ctk.CTkLabel(
                        details_row,
                        text=details_text,
                        font=ctk.CTkFont(size=9),
                        text_color=COLORS['text_secondary']
                    ).pack(anchor="w")
                
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
    
    def update_concurrent_videos_label(self, value):
        """Concurrent videos slider değiştiğinde label'ı güncelle"""
        self.concurrent_videos = int(value)
        if hasattr(self, 'concurrent_videos_label'):
            self.concurrent_videos_label.configure(text=f"{self.concurrent_videos} video aynı anda")
    
    def update_concurrent_fragments_label(self, value):
        """Concurrent fragments slider değiştiğinde label'ı güncelle"""
        self.concurrent_fragments = int(value)
        if hasattr(self, 'concurrent_fragments_label'):
            self.concurrent_fragments_label.configure(text=f"{self.concurrent_fragments} fragment paralel")
    
    def _update_subtitle_dropdowns(self):
        """Subtitle checkbox'ları değiştiğinde dropdown'ları aktif/pasif yap"""
        # Subtitle language dropdown
        if hasattr(self, 'subtitle_language_dropdown'):
            if self.download_subs_var.get():
                self.subtitle_language_dropdown.configure(state="normal")
            else:
                self.subtitle_language_dropdown.configure(state="disabled")
        
        # Auto-translate language dropdown
        if hasattr(self, 'auto_translate_language_dropdown'):
            if self.auto_subs_var.get():
                self.auto_translate_language_dropdown.configure(state="normal")
            else:
                self.auto_translate_language_dropdown.configure(state="disabled")
        
        # Embed subtitles checkbox - sadece alt yazı veya otomatik çeviri aktifken aktif olmalı
        if hasattr(self, 'embed_subs_var'):
            if self.download_subs_var.get() or self.auto_subs_var.get():
                # Embed checkbox'ı aktif et (UI'da zaten var, sadece mantık kontrolü)
                pass
    
    def clear_archive_file(self):
        """Archive dosyasını temizle"""
        if not self.archive_file.exists():
            messagebox.showinfo("ℹ️ Bilgi", "Archive dosyası zaten temiz!")
            return
        
        if messagebox.askyesno(
            "🗑️ Archive Temizle",
            f"Archive dosyası temizlenecek:\n\n{self.archive_file}\n\n"
            "Bu işlem sonrası tüm videolar tekrar indirilebilir.\n\n"
            "Devam etmek istiyor musunuz?"
        ):
            try:
                # Archive dosyasını sil
                self.archive_file.unlink()
                self.log("✅ Archive dosyası temizlendi", "success")
                messagebox.showinfo("✅ Başarılı", "Archive dosyası temizlendi!\n\nArtık tüm videolar tekrar indirilebilir.")
            except Exception as e:
                self.log(f"❌ Archive temizleme hatası: {str(e)}", "error")
                messagebox.showerror("❌ Hata", f"Archive temizlenemedi:\n\n{str(e)}")
    
    def clear_archive(self):
        """Archive dosyasını temizle"""
        if messagebox.askyesno(
            "Archive Temizle",
            "Archive dosyasını temizlemek istediğinizden emin misiniz?\n\n"
            "Bu işlem, daha önce indirilen videoların tekrar indirilmesine neden olur."
        ):
            try:
                if self.archive_file.exists():
                    self.archive_file.unlink()
                    self.log("Archive dosyası temizlendi", "success")
                    messagebox.showinfo("✅ Başarılı", "Archive dosyası temizlendi!\n\nDaha önce indirilen videolar tekrar indirilecek.")
                else:
                    messagebox.showinfo("Bilgi", "Archive dosyası bulunamadı.")
            except Exception as e:
                self.log(f"Archive temizleme hatası: {str(e)}", "error")
                messagebox.showerror("❌ Hata", f"Archive temizlenirken hata oluştu:\n\n{str(e)}")
    
    def update_system_status_quick(self):
        """Hızlı sistem durumu kontrolü (temel kontroller)"""
        try:
            status_parts = []
            
            # yt-dlp
            if self.ytdlp_path and self.ytdlp_path.exists() if isinstance(self.ytdlp_path, Path) else True:
                status_parts.append("✅ yt-dlp")
            else:
                status_parts.append("❌ yt-dlp")
            
            # FFmpeg
            if self.check_ffmpeg():
                status_parts.append("✅ FFmpeg")
            else:
                status_parts.append("⚠️ FFmpeg")
            
            # Cookie
            if self.cookie_file.exists():
                status_parts.append("✅ Cookie")
            else:
                status_parts.append("⚠️ Cookie")
            
            status_text = " | ".join(status_parts)
            
            # İndirme ekranındaki label'ı güncelle
            if hasattr(self, 'system_status_label'):
                self.system_status_label.configure(text=status_text)
            
            # Cookie ekranındaki label'ı güncelle
            if hasattr(self, 'cookie_screen_system_status'):
                self.cookie_screen_system_status.configure(text=status_text)
        except:
            pass
    
    def update_cookie_screen_system_status(self):
        """Cookie ekranı için sistem durumu güncelle"""
        self.update_system_status_quick()
    
    def show_system_health_dialog(self):
        """Detaylı sistem sağlık raporunu dialog'da göster"""
        # Sistem durumunu kontrol et
        issues = self._get_system_issues()
        
        # Dialog oluştur
        dialog = ctk.CTkToplevel(self)
        dialog.title("⚕️ Sistem Sağlık Raporu")
        dialog.geometry("600x500")
        dialog.transient(self)
        dialog.grab_set()
        
        # Başlık
        ctk.CTkLabel(
            dialog,
            text="⚕️ Sistem Sağlık Durumu",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS['text_primary']
        ).pack(pady=(20, 10))
        
        # Rapor scroll frame
        report_frame = ctk.CTkScrollableFrame(
            dialog,
            fg_color=COLORS['bg_dark'],
            corner_radius=8
        )
        report_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Her bir kontrol için satır
        for issue in issues:
            # Renk belirleme
            if "✅" in issue:
                color = COLORS['success']
            elif "⚠️" in issue:
                color = COLORS['warning']
            elif "❌" in issue:
                color = COLORS['danger']
            else:
                color = COLORS['text_secondary']
            
            ctk.CTkLabel(
                report_frame,
                text=issue,
                font=ctk.CTkFont(size=11),
                text_color=color,
                anchor="w",
                justify="left"
            ).pack(anchor="w", pady=3, padx=15)
        
        # Kapat butonu
        ctk.CTkButton(
            dialog,
            text="✅ Kapat",
            height=40,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS['primary'],
            command=dialog.destroy
        ).pack(pady=(0, 20), padx=20, fill="x")
        
        # Hızlı durumu güncelle
        self.update_system_status_quick()
    
    def _get_system_issues(self):
        """Sistem sorunlarını listele (yardımcı fonksiyon)"""
        issues = []
        
        # 1. yt-dlp kontrolü
        try:
            if self.ytdlp_path:
                result = subprocess.run(
                    [str(self.ytdlp_path), "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                if result.returncode == 0:
                    version = result.stdout.strip()
                    issues.append(f"✅ yt-dlp: {version}")
                else:
                    issues.append("❌ yt-dlp: Çalışmıyor")
            else:
                issues.append("❌ yt-dlp: Bulunamadı")
        except Exception as e:
            issues.append(f"❌ yt-dlp: Hata - {str(e)[:50]}")
        
        # 2. FFmpeg kontrolü
        if self.check_ffmpeg():
            if isinstance(self.ffmpeg_path, Path) and self.ffmpeg_path.exists():
                issues.append("✅ FFmpeg: Yerel kurulum mevcut")
            else:
                issues.append("✅ FFmpeg: Sistem kurulumu mevcut")
        else:
            issues.append("❌ FFmpeg: Bulunamadı (video/audio birleştirme çalışmayabilir)")
        
        # 3. İnternet bağlantısı
        try:
            result = subprocess.run(
                ["ping", "youtube.com", "-n", "1"] if platform.system() == "Windows" else ["ping", "-c", "1", "youtube.com"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            if result.returncode == 0:
                issues.append("✅ İnternet: Bağlantı OK")
            else:
                issues.append("❌ İnternet: Bağlantı sorunu")
        except:
            issues.append("⚠️ İnternet: Test edilemedi")
        
        # 4. Disk alanı
        if self.download_folder:
            try:
                total, used, free = shutil.disk_usage(self.download_folder)
                free_gb = free / (1024**3)
                if free_gb > 1:
                    issues.append(f"✅ Disk: {free_gb:.1f} GB boş")
                else:
                    issues.append(f"⚠️ Disk: Sadece {free_gb:.1f} GB boş")
            except:
                issues.append("⚠️ Disk: Kontrol edilemedi")
        else:
            issues.append("⚠️ Disk: İndirme klasörü seçilmemiş")
        
        # 5. Cookie durumu
        if self.cookie_file.exists():
            try:
                with open(self.cookie_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                required = ['HSID', 'SSID', 'SID', 'APISID', 'SAPISID', 'LOGIN_INFO']
                found = [c for c in required if c in content]
                if len(found) >= 5:
                    issues.append(f"✅ Cookie: {len(found)}/{len(required)} gerekli cookie mevcut")
                else:
                    issues.append(f"⚠️ Cookie: Sadece {len(found)}/{len(required)} cookie mevcut")
            except:
                issues.append("❌ Cookie: Dosya okunamadı")
        else:
            issues.append("⚠️ Cookie: Dosya bulunamadı")
        
        # 6. Archive durumu
        if self.archive_file.exists():
            try:
                with open(self.archive_file, 'r', encoding='utf-8') as f:
                    archive_lines = len([l for l in f.readlines() if l.strip()])
                issues.append(f"📦 Archive: {archive_lines} video kayıtlı")
            except:
                issues.append("⚠️ Archive: Okunamadı")
        else:
            issues.append("✅ Archive: Temiz (yeni başlangıç)")
        
        # 7. Log dosyası kontrolü
        if self.log_file.exists():
            try:
                size_mb = self.log_file.stat().st_size / (1024 * 1024)
                if size_mb > 10:
                    issues.append(f"⚠️ Log: {size_mb:.1f} MB (büyük dosya)")
                else:
                    issues.append(f"✅ Log: {size_mb:.1f} MB")
                
                # Son hataları kontrol et
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    recent_errors = [line for line in lines[-50:] if "ERROR" in line.upper() or "❌" in line]
                    if recent_errors:
                        issues.append(f"⚠️ Son hatalar: {len(recent_errors)} hata bulundu")
                        if recent_errors:
                            last_error = recent_errors[-1].strip()[:80]
                            issues.append(f"   Son hata: {last_error}...")
                    else:
                        issues.append("✅ Log: Son hatalar yok")
            except Exception as e:
                issues.append(f"⚠️ Log: Kontrol edilemedi - {str(e)[:30]}")
        
        return issues
    
    def check_system_issues(self):
        """Sistem durumunu kontrol et - Eski versiyon için wrapper"""
        # Yeni dialog'u çağır
        self.show_system_health_dialog()
    
    def select_download_folder(self):
        """İndirme klasörünü seç"""
        # Varsayılan olarak Desktop kullan
        default_folder = Path.home() / "Desktop" / "YouTube Downloads"
        folder = filedialog.askdirectory(
            title="İndirme Klasörü Seçin",
            initialdir=str(default_folder.parent) if default_folder.parent.exists() else None
        )
        
        if folder:
            self.download_folder = Path(folder)
            short_path = str(folder)[:40] + "..." if len(str(folder)) > 40 else str(folder)
            self.folder_label.configure(text=short_path, text_color=COLORS['success'])
            self.log(f"📂 Klasör seçildi: {folder}", "success")
    
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
        """Gelişmiş indirme motoru - Concurrent downloads, archive sistemi, progress tracking"""
        self.download_stats['start_time'] = time.time()
        
        # Önce mevcut dosyaları tara (archive sistemi kullanılacak, bu sadece UI için)
        self.after(0, lambda: self.log("🔍 Mevcut dosyalar taranıyor...", "info"))
        self.scan_existing_videos()  # ⚡ FIX: Mevcut dosya taramasını aktif et
        self.after(0, self.create_video_cards)  # UI'ı güncelle
        
        # İndirilecek videoları filtrele
        videos_to_download = [
            v for v in self.all_videos 
            if self.video_states.get(v['id']) not in ['done', 'skipped']
        ]
        
        if not videos_to_download:
            self.after(0, lambda: self.log("✅ Tüm videolar zaten indirilmiş!", "success"))
            self.is_downloading = False
            return
        
        self.after(0, lambda: self.log(f"📥 {len(videos_to_download)} video indirilecek (Aynı anda: {self.concurrent_videos})", "info"))
        
        # Concurrent downloads ile indir
        with ThreadPoolExecutor(max_workers=self.concurrent_videos) as executor:
            # Tüm videoları executor'a gönder
            futures = {}
            for video in videos_to_download:
                if not self.is_downloading:
                    break
                future = executor.submit(self.download_single_video, video)
                futures[future] = video
                time.sleep(0.3)  # Videolar arasında kısa bekleme
            
            # Tamamlananları bekle
            for future in as_completed(futures):
                if not self.is_downloading:
                    # Kalan görevleri iptal et
                    for f in futures:
                        if not f.done():
                            f.cancel()
                    break
                
                video = futures[future]
                try:
                    future.result()  # Hata varsa burada fırlatılır
                except Exception as e:
                    video_id = video['id']
                    self.video_states[video_id] = 'failed'
                    self.video_progress[video_id] = {'error': str(e)[:100]}
                    self.download_stats['failed'] += 1
                    self.after(0, lambda t=video['title'], e=str(e): self.log(f"❌ Hata: {t[:40]} - {e}", "error"))
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
    
    def download_single_video(self, video: Dict):
        """Tek bir videoyu indir - Thread-safe"""
        video_id = video['id']
        
        # Durdurma kontrolü
        while self.is_paused and self.is_downloading:
            time.sleep(0.5)
        
        if not self.is_downloading:
            return
        
        # İndirmeyi başlat
        self.video_states[video_id] = 'downloading'
        self.video_progress[video_id] = {'progress': 0, 'speed': '', 'eta': '', 'size': ''}
        
        self.after(0, self.create_video_cards)
        self.after(0, lambda t=video['title']: self.log(f"⬇️ İndiriliyor: {t[:50]}...", "info"))
        
        try:
            # Video'nun hangi playlist'e ait olduğunu bul
            playlist_name = "Videolar"  # Varsayılan
            for pl in self.playlists:
                if any(v['id'] == video_id for v in pl['videos']):
                    # Playlist adını temizle (dosya adı için güvenli)
                    playlist_name = self.sanitize_filename(pl['title'])
                    break
            
            # Output path - Playlist klasörüne göre organize et
            output_template = str(self.download_folder / playlist_name / "%(title)s.%(ext)s")
            
            # Kalite formatını belirle
            quality = self.quality_var.get() if hasattr(self, 'quality_var') else "best"
            format_map = {
                "best": "bestvideo+bestaudio/best",
                "4K": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
                "1440p": "bestvideo[height<=1440]+bestaudio/best[height<=1440]",
                "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
                "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
                "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
                "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]",
                "worst": "worst",
                "1080": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",  # Eski format desteği
                "720": "bestvideo[height<=720]+bestaudio/best[height<=720]",
                "480": "bestvideo[height<=480]+bestaudio/best[height<=480]"
            }
            format_string = format_map.get(quality, "bestvideo+bestaudio/best")
            
            # Merge seçeneği
            merge_video_audio = self.merge_video_audio_var.get() if hasattr(self, 'merge_video_audio_var') else True
            
            # Alt yazı ayarları
            download_subs = self.download_subs_var.get() if hasattr(self, 'download_subs_var') else True
            auto_subs = self.auto_subs_var.get() if hasattr(self, 'auto_subs_var') else False
            embed_subs = self.embed_subs_var.get() if hasattr(self, 'embed_subs_var') else True
            
            # Dil seçimleri
            subtitle_lang = "tr"
            if hasattr(self, 'subtitle_language_var'):
                lang_value = self.subtitle_language_var.get()
                # Dropdown'dan dil kodunu çıkar (örn: "tr - Türkçe" -> "tr")
                if " - " in lang_value:
                    subtitle_lang = lang_value.split(" - ")[0]
                else:
                    subtitle_lang = lang_value
            
            auto_translate_lang = "tr"
            if hasattr(self, 'auto_translate_language_var'):
                lang_value = self.auto_translate_language_var.get()
                # Dropdown'dan dil kodunu çıkar
                if " - " in lang_value:
                    auto_translate_lang = lang_value.split(" - ")[0]
                else:
                    auto_translate_lang = lang_value
            
            # Komut oluştur
            cmd = [
                str(self.ytdlp_path),
                "--cookies", str(self.cookie_file),
                "-f", format_string,
                "--write-thumbnail",       # Thumbnail indir
                "--embed-thumbnail",       # Videoya göm
                "--convert-thumbnails", "jpg",
                "--download-archive", str(self.archive_file),  # Archive sistemi
                "--concurrent-fragments", str(self.concurrent_fragments),  # Paralel fragment
                "--newline",               # Her satır yeni progress
                "--progress",              # Progress göster
                "-o", output_template,
            ]
            
            # Alt yazı seçenekleri
            if download_subs:
                if subtitle_lang == "all":
                    # Tüm dilleri indir
                    cmd.extend(["--write-subs", "--all-subs", "--convert-subs", "srt"])
                else:
                    # Belirli dil(ler) - virgülle ayrılmış dil kodları desteklenir
                    cmd.extend(["--write-subs", "--sub-langs", subtitle_lang, "--convert-subs", "srt"])
            
            if auto_subs:
                # Otomatik çeviri alt yazıları
                cmd.extend(["--write-auto-subs", "--sub-langs", auto_translate_lang])
            
            if embed_subs and (download_subs or auto_subs):
                cmd.append("--embed-subs")
            
            # Video/audio merge ayarları
            if merge_video_audio and self.check_ffmpeg():
                # Format'tan sonra merge ayarlarını ekle
                format_idx = cmd.index("-f") + 2
                cmd.insert(format_idx, "--merge-output-format")
                cmd.insert(format_idx + 1, "mkv")
                cmd.insert(format_idx + 2, "--audio-quality")
                cmd.insert(format_idx + 3, "0")
                
                # FFmpeg path belirt
                if self.ffmpeg_path and isinstance(self.ffmpeg_path, Path) and self.ffmpeg_path.exists():
                    output_idx = cmd.index("-o")
                    cmd.insert(output_idx, "--ffmpeg-location")
                    cmd.insert(output_idx + 1, str(self.ffmpeg_path.parent))
            
            # URL'yi ekle
            cmd.append(video['url'])
            
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
            self.video_progress[video_id]['error'] = "Zaman aşımı"
            self.download_stats['failed'] += 1
            self.after(0, lambda t=video['title']: self.log(f"⏱️ Zaman aşımı: {t[:40]}", "warning"))
        
        except Exception as e:
            self.video_states[video_id] = 'failed'
            error_msg = str(e)[:100]
            self.video_progress[video_id]['error'] = error_msg
            self.download_stats['failed'] += 1
            self.after(0, lambda t=video['title'], e=error_msg: self.log(f"❌ Hata: {t[:40]} - {e}", "error"))
        
        finally:
            self.after(0, self.create_video_cards)
            self.after(0, self.update_download_stats)
    
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
        """Video progress UI'ını güncelle - Optimize edilmiş"""
        # Sadece ilgili video kartını güncelle (tüm kartları yeniden çizmek yerine)
        # Not: Şimdilik tüm kartları güncelliyoruz, gelecekte optimize edilebilir
        if hasattr(self, 'video_scroll') and self.video_scroll.winfo_exists():
            # Her 2 saniyede bir güncelle (fazla sık güncelleme yapma)
            current_time = time.time()
            if not hasattr(self, '_last_ui_update'):
                self._last_ui_update = 0
            
            if current_time - self._last_ui_update > 2.0:  # 2 saniye throttle
                self.create_video_cards()
                self._last_ui_update = current_time
    
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
