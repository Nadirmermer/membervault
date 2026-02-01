"""
🚀 HIZLI YouTube İndirici - Sıfır Bekleme!
Cookie yapıştır → Linkleri yapıştır → İndir
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import subprocess
import threading
from pathlib import Path
import time
import sys
import zipfile
import urllib.request
import platform

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class HizliIndirici(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("🚀 Hızlı YouTube İndirici")
        self.geometry("800x700")
        
        self.download_folder = None
        self.is_downloading = False
        
        # yt-dlp yolunu bul
        self.ytdlp_path = self.find_ytdlp()
        
        # Ana container
        main = ctk.CTkFrame(self, fg_color="#1a1a2e")
        main.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Başlık
        ctk.CTkLabel(
            main,
            text="🚀 HIZLI İNDİRİCİ",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#00ff88"
        ).pack(pady=(10, 20))
        
        # 1. Cookie Alanı
        ctk.CTkLabel(
            main,
            text="1️⃣ Cookie'leri Yapıştırın (Netscape format)",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        ).pack(fill="x", pady=(0, 5))
        
        self.cookie_text = ctk.CTkTextbox(main, height=120, font=ctk.CTkFont(size=11))
        self.cookie_text.pack(fill="x", pady=(0, 15))
        self.cookie_text.insert("1.0", "# Cookie'lerinizi buraya yapıştırın...\n# EditThisCookie → Export\n# JSON veya Netscape format - ikisi de çalışır!")
        
        # 2. Link Alanı
        ctk.CTkLabel(
            main,
            text="2️⃣ Video Linklerini Yapıştırın (Her satıra bir link)",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        ).pack(fill="x", pady=(0, 5))
        
        self.links_text = ctk.CTkTextbox(main, height=150, font=ctk.CTkFont(size=11))
        self.links_text.pack(fill="x", pady=(0, 15))
        self.links_text.insert("1.0", "https://youtube.com/watch?v=...\nhttps://youtube.com/watch?v=...")
        
        # 3. Klasör Seçimi
        folder_frame = ctk.CTkFrame(main, fg_color="#16213e")
        folder_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            folder_frame,
            text="3️⃣ İndirme Klasörü",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left", padx=10, pady=10)
        
        self.folder_label = ctk.CTkLabel(
            folder_frame,
            text="Henüz seçilmedi",
            font=ctk.CTkFont(size=11),
            text_color="#888"
        )
        self.folder_label.pack(side="left", padx=10, expand=True, fill="x")
        
        ctk.CTkButton(
            folder_frame,
            text="📂 Seç",
            width=100,
            height=35,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#0f4c75",
            hover_color="#1b6ca8",
            command=self.select_folder
        ).pack(side="right", padx=10, pady=10)
        
        # 4. İNDİR Butonu - SÜPER BÜYÜK
        self.download_btn = ctk.CTkButton(
            main,
            text="⬇️ HEMEN İNDİR",
            height=70,
            font=ctk.CTkFont(size=24, weight="bold"),
            fg_color="#00ff88",
            hover_color="#00cc66",
            text_color="#000",
            command=self.start_download,
            corner_radius=15
        )
        self.download_btn.pack(fill="x", pady=(10, 15))
        
        # Log Alanı
        ctk.CTkLabel(
            main,
            text="📊 İndirme Durumu",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        ).pack(fill="x", pady=(0, 5))
        
        self.log_text = ctk.CTkTextbox(main, height=150, font=ctk.CTkFont(size=10))
        self.log_text.pack(fill="both", expand=True)
        
        if self.ytdlp_path:
            self.log(f"✅ Hazır! yt-dlp bulundu: {self.ytdlp_path}")
        else:
            self.log("⚠️ yt-dlp bulunamadı, indiriliyor...")
            threading.Thread(target=self.download_ytdlp, daemon=True).start()
    
    def find_ytdlp(self):
        """yt-dlp'yi bul veya indir"""
        # 1. Python modülü olarak (en güvenilir)
        try:
            result = subprocess.run(
                [sys.executable, "-m", "yt_dlp", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return "python_module"
        except:
            pass
        
        # 2. Mevcut klasörde yt-dlp.exe
        local_ytdlp = Path("yt-dlp.exe")
        if local_ytdlp.exists():
            try:
                result = subprocess.run([str(local_ytdlp), "--version"], capture_output=True, timeout=5)
                if result.returncode == 0:
                    return local_ytdlp
            except:
                pass
        
        # 3. System PATH'te
        try:
            result = subprocess.run(
                ["where.exe", "yt-dlp"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return Path(result.stdout.strip().split('\n')[0])
        except:
            pass
        
        return None
    
    def download_ytdlp(self):
        """yt-dlp'yi indir"""
        try:
            ytdlp_url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
            ytdlp_path = Path("yt-dlp.exe")
            
            self.log("📥 yt-dlp indiriliyor...")
            urllib.request.urlretrieve(ytdlp_url, ytdlp_path)
            
            self.ytdlp_path = ytdlp_path
            self.log("✅ yt-dlp indirildi!")
            
        except Exception as e:
            self.log(f"❌ yt-dlp indirilemedi: {str(e)}")
    
    def log(self, msg):
        """Log mesajı ekle"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {msg}\n")
        self.log_text.see("end")
    
    def select_folder(self):
        """Klasör seç"""
        folder = filedialog.askdirectory(title="İndirme Klasörü")
        if folder:
            self.download_folder = Path(folder)
            self.folder_label.configure(text=str(folder), text_color="#00ff88")
            self.log(f"📂 Klasör seçildi: {folder}")
    
    def start_download(self):
        """İndirmeyi başlat"""
        if self.is_downloading:
            messagebox.showwarning("Uyarı", "Zaten indiriliyor!")
            return
        
        # Cookie kontrolü
        cookie_content = self.cookie_text.get("1.0", "end").strip()
        if not cookie_content or cookie_content.startswith("#"):
            messagebox.showerror("Hata", "❌ Cookie yapıştırın!")
            return
        
        # Link kontrolü
        links_content = self.links_text.get("1.0", "end").strip()
        links = [l.strip() for l in links_content.split("\n") if l.strip() and not l.startswith("#")]
        if not links:
            messagebox.showerror("Hata", "❌ En az 1 link ekleyin!")
            return
        
        # Klasör kontrolü
        if not self.download_folder:
            messagebox.showerror("Hata", "❌ Klasör seçin!")
            return
        
        self.is_downloading = True
        self.download_btn.configure(state="disabled", text="⏳ İNDİRİLİYOR...")
        
        # Thread'de indir
        thread = threading.Thread(target=self.download_worker, args=(cookie_content, links), daemon=True)
        thread.start()
    
    def download_worker(self, cookie_content, links):
        """İndirme işçisi"""
        try:
            # yt-dlp kontrolü
            if not self.ytdlp_path:
                self.log("❌ yt-dlp bulunamadı! Lütfen bekleyin veya manuel indirin.")
                return
            
            # Python modülü değilse exists kontrolü yap
            if self.ytdlp_path != "python_module" and not self.ytdlp_path.exists():
                self.log("❌ yt-dlp dosyası bulunamadı!")
                return
            
            # Cookie formatını kontrol et ve dönüştür
            cookie_file = Path("temp_cookies.txt")
            
            # JSON formatında mı kontrol et
            if cookie_content.strip().startswith('[') or cookie_content.strip().startswith('{'):
                self.log("🔄 Cookie JSON formatında, Netscape'e çeviriliyor...")
                try:
                    import json
                    cookies = json.loads(cookie_content)
                    
                    # Netscape formatına çevir
                    netscape_lines = ["# Netscape HTTP Cookie File\n"]
                    for cookie in cookies:
                        domain = cookie.get('domain', '.youtube.com')
                        flag = 'TRUE' if domain.startswith('.') else 'FALSE'
                        path = cookie.get('path', '/')
                        secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
                        expiration = str(int(cookie.get('expirationDate', 0)))
                        name = cookie.get('name', '')
                        value = cookie.get('value', '')
                        
                        netscape_lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{expiration}\t{name}\t{value}\n")
                    
                    cookie_content = ''.join(netscape_lines)
                    self.log("✅ Cookie Netscape formatına çevrildi!")
                except Exception as e:
                    self.log(f"⚠️ JSON dönüştürme hatası: {str(e)}")
            
            cookie_file.write_text(cookie_content, encoding='utf-8')
            
            self.log(f"🎯 {len(links)} video indirilecek...")
            
            # Her video için
            for i, url in enumerate(links, 1):
                if not self.is_downloading:
                    break
                
                self.log(f"\n⏳ [{i}/{len(links)}] İndiriliyor: {url[:50]}...")
                
                try:
                    # Python modülü olarak mı yoksa exe olarak mı çalıştırılacak?
                    # yt_downloader_clean.py ile aynı parametreler
                    if self.ytdlp_path == "python_module":
                        cmd = [
                            sys.executable, "-m", "yt_dlp",
                            "--cookies", str(cookie_file),
                            "-f", "bestvideo+bestaudio/best",
                            "--write-thumbnail",
                            "--embed-thumbnail",
                            "--convert-thumbnails", "jpg",
                            "--merge-output-format", "mkv",
                            "--concurrent-fragments", "8",
                            "--newline",
                            "--progress",
                            "-o", str(self.download_folder / "%(title)s.%(ext)s"),
                            url
                        ]
                    else:
                        cmd = [
                            str(self.ytdlp_path),
                            "--cookies", str(cookie_file),
                            "-f", "bestvideo+bestaudio/best",
                            "--write-thumbnail",
                            "--embed-thumbnail",
                            "--convert-thumbnails", "jpg",
                            "--merge-output-format", "mkv",
                            "--concurrent-fragments", "8",
                            "--newline",
                            "--progress",
                            "-o", str(self.download_folder / "%(title)s.%(ext)s"),
                            url
                        ]
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=300,
                        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                    )
                    
                    if result.returncode == 0:
                        self.log(f"✅ [{i}/{len(links)}] Tamamlandı!")
                        # Son birkaç satırı göster
                        lines = result.stdout.strip().split('\n')
                        for line in lines[-3:]:
                            if line.strip():
                                self.log(f"  {line.strip()}")
                    else:
                        # Hata detayını göster
                        self.log(f"❌ [{i}/{len(links)}] HATA!")
                        # stderr'deki hata mesajını göster
                        error_lines = result.stderr.strip().split('\n')
                        for line in error_lines[-5:]:
                            if line.strip():
                                self.log(f"  ⚠️ {line.strip()}")
                
                except Exception as e:
                    self.log(f"❌ Hata: {str(e)}")
                    import traceback
                    self.log(f"Detay: {traceback.format_exc()[:300]}")
            
            # Temizlik
            if cookie_file.exists():
                cookie_file.unlink()
            
            self.log("\n🎉 TÜMÜ TAMAMLANDI!")
            
        except Exception as e:
            self.log(f"❌ Kritik hata: {str(e)}")
        
        finally:
            self.is_downloading = False
            self.after(0, lambda: self.download_btn.configure(state="normal", text="⬇️ HEMEN İNDİR"))

if __name__ == "__main__":
    app = HizliIndirici()
    app.mainloop()
