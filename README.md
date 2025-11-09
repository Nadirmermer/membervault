# 🔐 MemberVault - YouTube Üyelik İçerik İndiricisi

Katıldığınız YouTube kanal üyeliklerinizden (membership) erişebildiğiniz özel içerikleri (premium videolar, canlı yayınlar, topluluk gönderileri) toplu olarak indirmenizi sağlayan profesyonel masaüstü uygulaması.

> **💡 MemberVault Nedir?** Ödeme yaparak katıldığınız YouTube kanal üyeliklerinizdeki özel içerikleri, kendi kişisel arşivinize güvenle kaydetmenizi sağlar. İçerik üreticilerinin yayından kaldırdığı veya değiştirdiği üyelik içeriklerinizi kaybetmeyin!

## ✨ Özellikler

### 🎯 Temel Özellikler
- ✅ **3 Adımlı Basit Süreç**: Cookie → Playlist → İndirme
- ✅ **Üyelik İçeriklerine Erişim**: Katıldığınız kanal üyeliklerindeki özel içerikler
- ✅ **Toplu Arşivleme**: Birden fazla üyelik playlist'ini aynı anda yönetin
- ✅ **Akıllı Dosya Kontrolü**: Mevcut videolar otomatik atlanır
- ✅ **Kaldığımız Yerden Devam**: Program kapansa bile checkpoint sistemi ile devam edebilir

### 📊 İndirme Özellikleri
- 🎥 **Kalite Seçimi**: En İyi / 1080p / 720p / 480p
- 📈 **Canlı Progress Bar**: Her video için ayrı ilerleme çubuğu
- ⚡ **Hız & Süre**: Gerçek zamanlı hız ve kalan süre tahmini
- 🖼️ **Otomatik Thumbnail**: Kapak fotoğrafları videoya gömülü
- 📝 **Alt Yazı Desteği**: Türkçe, İngilizce ve diğer diller videoya gömülü
- ⏸️ **Duraklat/Devam**: İndirmeyi istediğiniz zaman duraklatın
- 🔄 **Hata Yönetimi**: Başarısız videoları tekrar deneme

### 🎨 Kullanıcı Arayüzü
- 🌙 **Modern Dark Theme**: Göz yormayan karanlık tema
- 📱 **Responsive Tasarım**: Her ekran boyutuna uyumlu
- 📋 **Detaylı Video Listesi**: Durum ikonları ve progress barlar
- 📊 **İstatistikler**: Toplam, İndirilen, Başarısız, Atlanan sayıları
- 📝 **Kompakt Log**: Tüm işlemler kaydedilir

## 🚀 Kurulum

### Gereksinimler
- Python 3.8 veya üstü
- Windows 10/11 (veya Linux/macOS)

### Adım 1: Python Paketlerini Yükleyin
```bash
pip install -r requirements.txt
```

### Adım 2: Programı Başlatın
```bash
python yt_downloader_clean.py
```

## 📖 Kullanım Kılavuzu

### 1️⃣ Adım 1: Üyelik Cookie'sini Hazırlama

#### Cookie Nasıl Alınır?
1. **Chrome Extension Yükleyin**: [EditThisCookie](https://chrome.google.com/webstore/detail/editthiscookie/)
2. **Üyeliğiniz Olan Hesapla Giriş Yapın**: YouTube'da üye olduğunuz kanala ait hesabınızla giriş yapın
3. **Extension'ı Açın**: Sağ üstteki çerez simgesine tıklayın
4. **Export** butonuna basın (JSON formatında kopyalar)
5. **Programa Yapıştırın**: Cookie alanına yapıştırıp "Kaydet ve Test Et"

#### Neden Cookie Gerekli?
YouTube kanal üyelik içerikleri sadece ödeme yapıp katılan kullanıcılara açıktır. Cookie'ler üyelik kimliğinizi doğrular.

### 2️⃣ Adım 2: Üyelik Playlist Linklerini Ekleme

1. **Üyelik İçerik Linklerini Yapıştırın**: Her satıra bir YouTube linki
   ```
   https://www.youtube.com/playlist?list=PLxxxxxx (Üyelik playlist'i)
   https://www.youtube.com/watch?v=yyyyyyyy (Tekil üyelik videosu)
   ```

2. **"✅ LİNKLERİ EKLE VE BİLGİLERİ ÇEK"** butonuna basın

3. **Kalite Seçin**: En İyi (önerilen) / 1080p / 720p / 480p

4. **Sağ Panelde Kontrol Edin**: Eklenen playlist'ler ve video sayıları

### 3️⃣ Adım 3: İndirme

1. **📁 Klasör Seçin**: İndirme klasörünü belirleyin (zorunlu)

2. **▶️ İndirmeyi Başlatın**:
   - Program önce klasörü tarar (mevcut videolar atlanır)
   - Videolar sırayla indirilir
   - Her video için progress bar gösterilir

3. **⏸️ Duraklat/Devam**: İstediğiniz zaman duraklatabilirsiniz

4. **⏹️ Durdur**: Tamamen durdurmak için

5. **🔄 Başarısızları Tekrarla**: Hata alan videoları yeniden dene

## 🎯 İpuçları

### Hız İpuçları
- ✅ **Tek seferde çok playlist eklemeyin** (5-10 playlist ideal)
- ✅ **İnternet bağlantınızı kontrol edin** (en az 10 Mbps önerilen)
- ✅ **Diğer indirme programlarını kapatın**

### Sorun Giderme

#### "Cookie Geçersiz" Hatası
- Cookie'nin süresi dolmuş olabilir → Yeniden alın
- YouTube'dan çıkış yapmış olabilirsiniz → Tekrar giriş yapın
- "Test Atla" butonu ile devam edip deneyebilirsiniz

#### "Erişim Engellendi" Hatası
- Video üyelere özel olabilir → Üyeliğinizi kontrol edin
- Cookie doğru hesaptan mı? → Kontrol edin
- YouTube rate limit → 15-20 dakika bekleyin

#### İndirme Çok Yavaş
- İnternet bağlantınızı test edin
- Başka programlar internet kullanıyor mu?
- YouTube sunucuları yavaş olabilir (akşam saatlerinde)

#### "Zaman Aşımı" Hatası
- Video çok büyük olabilir (1 saatten uzun)
- İnternet bağlantısı kesilmiş olabilir
- Videoyu manuel olarak deneyin

## 📁 Dosya Yapısı

```
membervault/
├── yt_downloader_clean.py      # Ana program
├── cookies.txt                  # Üyelik cookie dosyası (otomatik oluşturulur)
├── download_checkpoint.json     # İlerleme kaydı (kaldığımız yerden devam)
├── downloader_log.txt          # Detaylı log dosyası
├── requirements.txt             # Python paketleri
├── README.md                    # Bu dosya
├── LICENSE                      # MIT Lisansı
├── CONTRIBUTING.md              # Katkı rehberi
├── CODE_OF_CONDUCT.md          # Davranış kuralları
├── CHANGELOG.md                 # Versiyon geçmişi
├── CHECKLIST.md                 # Yayınlama kontrol listesi
├── Videolar/                    # İndirilen videolar (varsayılan)
└── .venv/                       # Python sanal ortamı (önerilen)
```

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
