# 📋 Değişiklik Günlüğü - MemberVault

## [4.0 MemberVault Edition] - 2025-11-09

### � Rebranding
- 🔐 **Yeni İsim**: MemberVault - YouTube Üyelik İçerik İndiricisi
- 📝 **Yeni Açıklama**: YouTube kanal üyeliklerinizdeki özel içerikleri arşivleme odaklı
- 🎨 **Profesyonel Branding**: Üyelik içeriklerine özel tasarım ve mesajlar
- ⚖️ **Geliştirilmiş Yasal Uyarılar**: Üyelik içerik kullanımı hakkında detaylı açıklamalar

### 🎉 Temel Özellikler

#### 🔄 Kaldığımız Yerden Devam
- ✅ Otomatik checkpoint sistemi
- ✅ Program kapansa bile devam edebilme
- ✅ 24 saat içindeki oturumları yükleme
- ✅ Kullanıcıya onay sorusu

#### 📝 Log Sistemi
- ✅ `downloader_log.txt` dosyasına otomatik kayıt
- ✅ Tarih ve saat damgası
- ✅ Log seviyeleri (INFO, WARNING, ERROR, SUCCESS)
- ✅ Hata ayıklama için detaylı bilgi

#### 🖼️ Gelişmiş Playlist Görüntüleme
- ✅ "Bilinmeyen" yerine gerçek playlist isimleri
- ✅ Playlist thumbnail önizlemesi (hazırlık)
- ✅ Her playlist için özet istatistikler
- ✅ Video süreleri gösterimi

#### 📝 Alt Yazı Desteği
- ✅ Otomatik alt yazı indirme
- ✅ Türkçe, İngilizce ve diğer diller
- ✅ Alt yazıları videoya gömme
- ✅ SRT formatına dönüştürme

#### 📊 Gelişmiş İndirme Sistemi
- ✅ Akıllı dosya tarama (mevcut videolar atlanır)
- ✅ Her video için canlı progress bar
- ✅ Hız ve kalan süre gösterimi (MB/s, ETA)
- ✅ Sıralı indirme (bir video bitsin, diğeri başlasın)
- ✅ Video boyutu gösterimi

#### ⏸️ Duraklat/Devam
- ✅ İndirmeyi duraklat butonu
- ✅ Devam et butonu
- ✅ Durum kaydetme (checkpoint)

#### 🎨 UI/UX İyileştirmeleri
- ✅ Büyük ve belirgin "LİNKLERİ EKLE" butonu
- ✅ Video kartlarında renk kodlama (mavi=indiriliyor, kırmızı=hata)
- ✅ Playlist başına özet istatistikler
- ✅ Detaylı hata mesajları
- ✅ Thumbnail otomatik temizleme

#### 🐛 Hata Yönetimi
- ✅ Detaylı hata mesajları (timeout, erişim engeli vb.)
- ✅ Her video için hata sebebi gösterimi
- ✅ Başarısız videoları tekrar deneme
- ✅ İnternet kesintisinde devam edebilme

### 🔧 Teknik İyileştirmeler
- ✅ Progress tracking thread sistemi
- ✅ JSON checkpoint sistemi
- ✅ Log dosyası yönetimi
- ✅ Video ID ve başlık eşleştirme algoritması
- ✅ Normalize edilmiş başlık karşılaştırması
- ✅ Alt yazı gömme desteği
- ✅ Thumbnail metadata gömme

### 📚 Dokümantasyon
- ✅ Detaylı README.md
- ✅ requirements.txt
- ✅ .gitignore
- ✅ CHANGELOG.md (bu dosya)
- ✅ Kullanım kılavuzu
- ✅ Sorun giderme rehberi

### 🎯 Performans
- ✅ Daha hızlı dosya tarama
- ✅ Optimize edilmiş UI güncelleme
- ✅ Thread-safe progress tracking
- ✅ Bellek optimizasyonu

### 🔒 Güvenlik
- ✅ Cookie test sistemi
- ✅ Güvenli dosya adı temizleme
- ✅ Timeout koruması
- ✅ Hata yakalama

---

## [3.0] - 2025-11-08

### Eklenenler
- 3 adımlı süreç (Cookie → Playlist → Download)
- Cookie test mekanizması
- Playlist bilgisi çekme
- Temel indirme sistemi

### Düzeltilenler
- Cookie dönüştürme (JSON → Netscape)
- UI donma sorunu (threading)

---

## [2.0] - 2025-11-07

### Eklenenler
- CustomTkinter UI
- Cookie yükleme
- Playlist listesi

---

## [1.0] - 2025-11-06

### Başlangıç
- İlk prototip
- Temel indirme fonksiyonu
