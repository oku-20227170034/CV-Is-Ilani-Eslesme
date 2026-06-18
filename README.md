# Yapay Zeka Destekli CV ve İş İlanı Eşleştirme Sistemi

Bu proje, açık kaynak kodlu **Resume Matcher** altyapısı temel alınarak, Türkiye iş gücü piyasasına ve Türkçe doğal dil işleme (NLP) gereksinimlerine göre özelleştirilmiş ve geliştirilmiş bir **CV ve İş İlanı Eşleştirme Sistemi**dir. 

Sistem, yüklenen aday özgeçmişlerini (PDF, Word, Görsel formatlarında) OCR ve gelişmiş metin ayrıştırma zinciriyle okumakta, **Eleman.net** üzerinden canlı olarak kazıdığı iş ilanlarıyla semantik düzeyde karşılaştırmakta ve deterministik bir skorlama algoritması ile uyum raporları üretmektedir.

---

## 🚀 Öne Çıkan Özellikler ve Yapılan Geliştirmeler

### 1. Canlı Eleman.net İş İlanı Entegrasyonu (`eleman_scraper.py`)
- Statik veya lokal ilan tanımları yerine, **Eleman.net** portalı üzerinden canlı arama sorguları yapılarak en güncel iş ilanları asenkron olarak çekilir.
- Sunucu kaynaklı engellemeleri ve bot korumalarını aşmak için standart `requests` kütüphanesine ek olarak otomatik fallback yapan **`curl_cffi` (TLS/JA3 Chrome taklidi)** entegrasyonu mevcuttur.

### 2. Türkçe Destekli Hibrid OCR ve Belge Ayrıştırma Zinciri (`parser.py`)
- Metin tabanlı PDF ve DOCX dosyaları Microsoft **`markitdown`** ile paragraflar ve başlık hiyerarşisi korunarak Markdown formatına dönüştürülür.
- Piksel tabanlı görseller (PNG, JPEG) veya taranmış PDF'ler için **`kreuzberg`** (Tesseract sargısı) üzerinden **Türkçe (`tur`) ve İngilizce (`eng`)** dil paketleriyle OCR taraması yapılır.
- **Tarih Kurtarma Filtresi (Regex)**: Normalleştirme veya dil modeli çevrimi esnasında kaybolabilecek ay/yıl bazlı tarih verileri ("Haziran 2021 - Ağustos 2023" vb.) düzenli ifadelerle tespit edilerek korunur.

### 3. Çok Aşamalı Özgeçmiş İyileştirici (`refiner.py`)
- **Anahtar Kelime Enjeksiyonu**: İlanda aranan ancak adayın ana özgeçmişinde (master CV) yer almasına rağmen taslak CV'sinde eksik olan beceriler `re.escape()` ve kelime sınırları (`\b`) kontrol edilerek enjekte edilir.
- **AI İfade Temizleme**: Yapay zekanın sıkça ürettiği jenerik ve yapay kelimeler (`leveraged`, `synergized` vb.) regex tabanlı yerel sözlükle taranıp daha doğal Türkçe karşılıklarıyla değiştirilir.
- **Hizalama (Alignment) Denetimi**: LLM'lerin uydurduğu (hallucinate ettiği) asılsız şirket, okul veya sertifika verileri, orijinal CV ile karşılaştırılarak otomatik silinir.

### 4. Deterministik ve Ağırlıklı Skorlama Algoritması
- Dil modellerinin değişken (nondeterministik) skor üretmesini engellemek için skorlama Python tarafında çalışır.
- Zorunlu becerilere 2 kat, tercih edilen becerilere 1 kat ağırlık verilir.
- Adayın deneyim süresi uygunsa ek puan (+5 veya kıdemliyse +8), yetersizse ceza puanı (-15) uygulanır.
- Sektör uyumsuzluğu durumunda (örneğin yazılım ilanı için sadece finans tecrübesi olması) nihai skora **20 puanlık bir üst sınır (hard cap)** getirilir.

### 5. PyTorch & SBERT Semantik Vektör Benzerliği (Derin Öğrenme Modülü)
- Aday özgeçmişleri ile iş ilanlarının anlamsal temsilleri, Türkçe BERTürk (`dbmdz/bert-base-turkish-cased`) veya Sentence-Transformers (`SBERT`) derin öğrenme modelleri kullanılarak 768 boyutlu yoğun vektörlere dönüştürülür.
- Vektörler arasındaki **Kosinüs Benzerliği (Cosine Similarity)** hesaplanarak milisaniyeler içerisinde anlamsal yakınlık tespiti yapılır.
- `torch.no_grad()` ve `batch_size=32` optimizasyonlarıyla donanım RAM kullanımı yarı yarıya düşürülmüştür.

---

## 📂 Proje Dizin Yapısı

```bash
CV-Is-Ilani-Eslesme/
├── apps/
│   ├── backend/app/
│   │   ├── services/
│   │   │   ├── parser.py          # Belge metin çıkarıcı ve Tesseract OCR
│   │   │   ├── refiner.py         # Çok aşamalı CV iyileştirme modülü
│   │   │   └── eleman_scraper.py  # Eleman.net veri kazıma servisi
│   │   ├── routers/
│   │   │   └── job_matcher.py     # Semantik eşleştirme ve skorlama API'si
│   │   ├── prompts/
│   │   │   └── templates.py       # LLM için semantik kurallar ve şablonlar
│   │   └── database.py            # TinyDB veritabanı sargısı
│   └── frontend/
│       └── app/                   # Next.js 15 bileşenleri ve sayfaları
├── eleman_scraper.py              # CLI test kazıma betiği
├── docker_baslat.bat              # Docker ile tüm servisleri tek tıkla başlatan betik
└── README.md                      # Proje açıklama dosyası
```

---

## 🛠️ Kurulum ve Çalıştırma

### Gereksinimler
- **Docker**: Docker Desktop kurulu ve çalışıyor olmalıdır
- **Docker Compose**: Docker Desktop ile birlikte otomatik olarak gelir

### Hızlı Başlangıç (Windows)
Proje dizininde yer alan **`docker_baslat.bat`** dosyasına çift tıklayarak tüm servisleri (FastAPI backend port 8000, Next.js frontend port 3000) Docker üzerinden otomatik olarak başlatabilirsiniz.

### Manuel Başlatma

1. **Backend Servisini Başlatma**:
   ```bash
   cd apps/backend
   # Gerekli kütüphaneleri yükleyin
   pip install -r requirements.txt
   # .env dosyasını yapılandırın (OpenAI API vb.)
   cp .env.example .env
   # API'yi çalıştırın
   uvicorn app.main:app --reload --port 8000
   ```

2. **Frontend Servisini Başlatma**:
   ```bash
   cd apps/frontend
   # Paketleri yükleyin
   npm install
   # Arayüzü başlatın
   npm run dev
   ```
   Tarayıcınızda **`http://localhost:3000`** adresine giderek uygulamayı kullanmaya başlayabilirsiniz.

---

## 🧪 Model ve API Testleri
API uç noktalarının kararlılığını test etmek için kök dizindeki `test_api.py` betiğini çalıştırabilirsiniz:
```bash
python test_api.py
```
Bu betik, lokalde çalışan FastAPI backend sunucusuna örnek bir CV ve iş pozisyonu göndererek semantik eşleştirme sonuçlarını ve hesaplanan uyum skorunu JSON formatında konsola basacaktır.
