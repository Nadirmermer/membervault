# YouTube Video İndirici

YouTube videolarını ve playlist'lerini indirmek için geliştirilmiş Python tabanlı masaüstü uygulaması.

## ✨ Özellikler

### 🎯 Temel Özellikler
- ✅ Cookie tabanlı kimlik doğrulama
- ✅ Toplu video indirme
- ✅ Akıllı dosya kontrolü (mevcut videolar atlanır)
- ✅ Checkpoint sistemi (kaldığınız yerden devam)

### 📊 İndirme Özellikleri
- 🎥 Kalite seçimi: En İyi / 1080p / 720p / 480p
- 📈 Canlı progress bar
- 🖼️ Otomatik thumbnail
- 📝 Alt yazı desteği
- ⏸️ Duraklat/Devam
- 🔄 Hata yönetimi

## 🚀 Kurulum

### Gereksinimler
- Python 3.8 veya üstü
- Windows 10/11 (veya Linux/macOS)

### Adım 1: Python Paketlerini Yükleyin
```bash
pip install -r requirements.txt
```

### Adım 2: Programı Başlatın

**Tam özellikli GUI için:**
```bash
python youtube_downloader_gui.py
```

**Hızlı indirici için:**
```bash
python youtube_quick_downloader.py
```

## 📖 Kullanım

### 1️⃣ Cookie Ekleme
1. Tarayıcı eklentisi (EditThisCookie) ile cookie'leri dışa aktarın
2. Cookie alanına yapıştırın
3. "Kaydet ve Test Et" butonuna basın

### 2️⃣ Link Ekleme
1. YouTube playlist veya video linklerini yapıştırın
2. "Linkleri Ekle" butonuna basın
3. Kalite seçimi yapın

### 3️⃣ İndirme
1. İndirme klasörünü seçin
2. "İndirmeyi Başlat" butonuna basın
3. İlerlemeyi takip edin
## 🔒 Güvenlik Notları

- Cookie dosyalarını kimseyle paylaşmayın
- İndirilen içerikleri kişisel kullanım için saklayın
- Tüm veriler yerel bilgisayarınızda kalır

## 🐛 Sorun Giderme

### Yaygın Hatalar
- **Cookie Geçersiz**: Cookie'yi yeniden alın
- **Erişim Engellendi**: Üyelik durumunuzu kontrol edin
- **Yavaş İndirme**: İnternet bağlantınızı test edin
- **Zaman Aşımı**: Video boyutu veya bağlantı hızı kontrol edilmeli

## 📜 Kullanım Koşulları

⚠️ Bu yazılım kişisel kullanım içindir. İndirilen içerikleri:
- ❌ Başkalarıyla paylaşmayın
- ❌ Ticari amaçla kullanmayın
- ✅ Sadece kişisel arşivinizde tutun

## 🙏 Kullanılan Teknolojiler

- **yt-dlp**: Video indirme motoru
- **customtkinter**: Modern UI kütüphanesi
- **FFmpeg**: Video/ses işleme

---

**Son Güncelleme**: Şubat 2026

## 📁 Dosya Yapısı

```
youtube video/
├── youtube_downloader_gui.py       # 🎨 Tam özellikli GUI (önerilen)
├── youtube_quick_downloader.py     # ⚡ Hızlı basit indirici
├── requirements.txt                # Python bağımlılıkları
├── video_links.txt                 # Video linkleri
├── ffmpeg/                         # FFmpeg binary dosyaları
├── indirilen_videolar/            # İndirilen videolar (66 video)
└── README.md                       # Bu dosya
```

## 🎯 Hangi Programı Kullanmalıyım?

### 🎨 **youtube_downloader_gui.py** (Önerilen)
- ✅ Tam özellikli, modern GUI
- ✅ Playlist yönetimi ve video önizleme
- ✅ Her video için progress bar
- ✅ Duraklat/devam, hata yönetimi
- ✅ İstatistikler ve detaylı log
- 📌 **Çok sayıda video için ideal**

### ⚡ **youtube_quick_downloader.py** (Hızlı)
- ✅ Minimalist, tek ekran
- ✅ Hızlı indirme, sade arayüz
- ✅ Az sayıda video için pratik
- 📌 **Acil iş için ideal**

## 🔒 Güvenlik & Gizlilik

- ✅ **Tamamen Yerel**: Tüm veriler bilgisayarınızda kalır, hiçbir sunucuya gönderilmez
- ✅ **Şifre Gerektirmez**: Cookie'ler oturum bilgisi, şifre kaydetmez
- ✅ **Açık Kaynak**: Tüm kodu GitHub'da inceleyebilirsiniz
- ⚠️ **Cookie Güvenliği**: `cookies.txt` dosyasını kimseyle paylaşmayın
- ⚠️ **Üyelik Koruması**: Cookie'ler hesap erişimi sağlar, güvenli tutun
- 🔐 **Özel İçerikler**: İndirilen üyelik içerikleri sadece sizde kalmalı

## 🐛 Sorun Giderme & Destek

Sorun mu yaşıyorsunuz?

1. **Log Dosyasını Kontrol Edin**: `downloader_log.txt` dosyasında detaylı hata mesajları bulunur
2. **GitHub Issues**: [Issues sayfasından](https://github.com/Nadirmermer/membervault/issues) yeni bir issue açın
3. **Hata Raporu**: Log dosyasındaki ilgili kısmı issue'ya yapıştırın

### 💬 Topluluk Desteği
- **Discussions**: Sorularınız için [GitHub Discussions](https://github.com/Nadirmermer/membervault/discussions) kullanın
- **Wiki**: [Sık sorulan soruları](https://github.com/Nadirmermer/membervault/wiki) kontrol edin

## 🤝 Katkıda Bulunma

Katkılarınızı bekliyoruz! Lütfen [CONTRIBUTING.md](CONTRIBUTING.md) dosyasını okuyun.

### 🌟 Destek Olun
Projeyi beğendiyseniz:
- ⭐ GitHub'da yıldız verin
- � Hata bildirin
- 💡 Özellik önerin
- �📝 Dokümantasyonu geliştirin

## 📜 Lisans

Bu proje [MIT Lisansı](LICENSE) altında lisanslanmıştır.

**⚠️ Önemli Not**: MIT Lisansı yazılımın kullanımına izin verse de, YouTube içeriklerinin telif hakları ve üyelik şartları size aittir. Bu yazılımı kullanarak yasal sorumluluğu kabul edersiniz.

---

<div align="center">

**⭐ Projeyi beğendiyseniz yıldız vermeyi unutmayın!**

**🔐 MemberVault** - Üyelik içeriklerinizi güvenle arşivleyin

Made with ❤️ for YouTube membership content preservation

[Report Bug](https://github.com/Nadirmermer/membervault/issues) · [Request Feature](https://github.com/Nadirmermer/membervault/issues) · [Discussions](https://github.com/Nadirmermer/membervault/discussions)

</div>

## ⚠️ Önemli Yasal Uyarılar

### 📌 Kişisel Kulanım İçindir
Bu araç **yalnızca ödeme yaparak katıldığınız** YouTube kanal üyeliklerinizdeki içerikleri **kişisel arşivleme** amacıyla kullanılmalıdır.

### ⚖️ Yasal Sorumluluklar
- ✅ **İzin Verilen**: Üye olduğunuz kanallardaki içerikleri kişisel arşivleme
- ❌ **Yasak**: İndirilen içerikleri başkalarıyla paylaşmak
- ❌ **Yasak**: Ticari amaçla kullanmak veya satmak
- ❌ **Yasak**: Telif haklarını ihlal eden içerik dağıtımı

### 📜 YouTube Kullanım Şartları
Bu aracı kullanarak [YouTube Hizmet Şartları'nı](https://www.youtube.com/t/terms) kabul etmiş sayılırsınız. YouTube'un üyelik içerik politikalarına uymak **sizin sorumluluğunuzdadır**.

### 🛡️ Telif Hakları
İndirdiğiniz tüm içerikler telif hakkı koruması altındadır. İçerikleri:
- 🚫 Başka platformlarda yeniden yayınlamayın
- 🚫 Sosyal medyada paylaşmayın
- 🚫 Torrent/dosya paylaşım sitelerine yüklemeyin
- ✅ Sadece kişisel arşivinizde tutun

### ⚠️ Sorumluluk Reddi
Bu yazılımı kullanarak oluşabilecek her türlü yasal sorumluluk **kullanıcıya** aittir. Geliştirici, yasadışı kullanımdan sorumlu değildir.

## 🙏 Teşekkürler

- **yt-dlp**: Güçlü indirme motoru
- **customtkinter**: Modern UI framework
- **EditThisCookie**: Cookie yönetimi

---

**Versiyon**: 4.0 Clean Edition  
**Son Güncelleme**: Kasım 2025  
**Geliştirici**: YouTube Downloader Team

Keyifli İndirmeler! 🎉
