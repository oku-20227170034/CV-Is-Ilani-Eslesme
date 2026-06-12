import asyncio
import json
import math
from fastapi import APIRouter, HTTPException
from typing import List

from app.services.eleman_scraper import eleman_ara
from app.llm import complete_json
from pydantic import BaseModel

router = APIRouter(prefix="/job-matcher", tags=["Job Matcher"])

class JobMatcherRequest(BaseModel):
    cv_text: str
    position: str

class JobMatchResult(BaseModel):
    baslik: str
    sirket: str
    lokasyon: str
    link: str
    ilan_no: str
    uyum_skoru: int
    eksik_yetkinlikler: List[str]
    cv_onerileri: List[str]
    aciklama: str
    skor_aciklamasi: str | None = None
    eslesen_beceriler: List[str] = []
    maksimum_ulasabilir_skor: int | None = None
    cinsiyet: str | None = None
    yas: str | None = None
    deneyim: str | None = None
    calisma_sekli: str | None = None
    egitim: str | None = None

class JobMatcherResponse(BaseModel):
    matches: List[JobMatchResult]


def calculate_score(
    zorunlu_beceriler: List[str],
    tercih_beceriler: List[str],
    eslesen_zorunlu: List[str],
    eslesen_tercih: List[str],
    deneyim_durumu: str,   # "fazla" | "uygun" | "eksik" | "belirsiz"
    egitim_uyumu: bool | None,
    sektor_uyumu: bool,
) -> tuple[int, int, str]:
    """
    Skoru Python'da deterministik olarak hesaplar.
    Returns: (uyum_skoru, maksimum_skor, aciklama)
    """
    # Ağırlıklar: zorunlu=2, tercih=1
    toplam_puan = len(zorunlu_beceriler) * 2 + len(tercih_beceriler) * 1
    if toplam_puan == 0:
        return 50, 70, "İlanda beceri bilgisi bulunamadı."

    mevcut_puan = len(eslesen_zorunlu) * 2 + len(eslesen_tercih) * 1
    base_skor = (mevcut_puan / toplam_puan) * 100

    # Düzeltmeler
    duzeltmeler = []
    if deneyim_durumu == "fazla":
        base_skor += 8
        duzeltmeler.append("+8 (deneyim fazla)")
    elif deneyim_durumu == "uygun":
        base_skor += 5
        duzeltmeler.append("+5 (deneyim uygun)")
    elif deneyim_durumu == "eksik":
        base_skor -= 15
        duzeltmeler.append("-15 (deneyim eksik)")

    if egitim_uyumu is True:
        base_skor += 5
        duzeltmeler.append("+5 (eğitim uyumlu)")
    elif egitim_uyumu is False:
        base_skor -= 10
        duzeltmeler.append("-10 (eğitim uyumsuz)")

    # Sektör uyumsuzluğu hard cap
    if not sektor_uyumu:
        base_skor = min(base_skor, 20)
        duzeltmeler.append("(sektör farklı → max 20)")

    # Eksik beceri oranı hard cap
    toplam_beceri = len(zorunlu_beceriler) + len(tercih_beceriler)
    eslesen_toplam = len(eslesen_zorunlu) + len(eslesen_tercih)
    eksik_sayi = toplam_beceri - eslesen_toplam
    eksik_oran = eksik_sayi / toplam_beceri if toplam_beceri > 0 else 0

    if eksik_oran > 0.70 and sektor_uyumu:
        base_skor = min(base_skor, 35)
    elif eksik_oran > 0.50 and sektor_uyumu:
        base_skor = min(base_skor, 55)
    elif eksik_oran > 0.30 and sektor_uyumu:
        base_skor = min(base_skor, 75)

    uyum_skoru = max(0, min(100, round(base_skor)))

    # Maksimum ulaşılabilir skor (tüm zorunlular eklense)
    max_puan = toplam_puan
    max_base = (max_puan / toplam_puan) * 100
    if deneyim_durumu in ("fazla", "uygun"):
        max_base += 5
    if egitim_uyumu is not False:
        max_base += 5
    maks_skor = max(0, min(95, round(max_base * 0.92)))  # gerçekçi sınır

    # Açıklama
    aciklama_parcalari = [
        f"{toplam_beceri} beceriden {eslesen_toplam}'i eşleşti "
        f"(base %{round((mevcut_puan/toplam_puan)*100)})"
    ]
    if duzeltmeler:
        aciklama_parcalari.append(", ".join(duzeltmeler))
    aciklama_parcalari.append(f"→ Final skor: {uyum_skoru}")
    aciklama = ". ".join(aciklama_parcalari)

    return uyum_skoru, maks_skor, aciklama


async def analyze_single_job(ilan: dict, cv_text: str) -> dict | None:
    """Tek bir iş ilanı için beceri tespiti ve semantik eşleştirme yapar."""
    detay = ilan.get("detay", {})
    aciklama_full = detay.get("aciklama", "")
    aciklama_truncated = aciklama_full[:400] + "..." if len(aciklama_full) > 400 else aciklama_full

    ilan_payload = {
        "baslik": ilan.get("baslik", ""),
        "sirket": ilan.get("sirket", ""),
        "lokasyon": ilan.get("lokasyon", ""),
        "link": ilan.get("link", ""),
        "ilan_no": detay.get("ilan_no", ""),
        "aciklama": aciklama_truncated,
        "deneyim_kriteri": detay.get("deneyim", ""),
        "egitim_kriteri": detay.get("egitim", ""),
        "calisma_sekli": detay.get("calisma_sekli", ""),
    }

    system_prompt = """Sen bir CV ve iş ilanı analiz motorusun. Görevin, verilen tek bir iş ilanı ile kullanıcının CV'sini analiz edip becerileri tespit etmek ve bunları SEMANTİK BENZERLİK (Semantic Similarity) kurallarına göre eşleştirmektir. SKOR HESAPLAMA YAPMA — skor ayrıca hesaplanacak.

Sen her türlü meslek ve sektörde (muhasebe, sağlık, eğitim, satış, mühendislik, lojistik, finans, pazarlama, insan kaynakları, grafik tasarım, yazılım, e-ticaret, hukuk vb.) uzman seviyesinde analiz yapabilirsin.

ÖNEMLİ KURALLAR:

1. YETENEK ÇIKARMA (SKILL EXTRACTION) - TÜM MESLEKLER İÇİN:
- Metinlerden (hem CV hem de iş ilanından) sadece GERÇEK mesleki/teknik becerileri, sertifikaları, lisansları, araçları ve yetkinlikleri çıkar.
- Şirket adlarını, marka isimlerini (örn. Trendyol, Arçelik, THY, Garanti Bankası vb.) ASLA ayrı birer beceri olarak çıkarma. Bunlar yerine genel mesleki yetkinliği yaz.
- Lokasyonları (İstanbul, Ankara vb.), yaş, cinsiyet gibi kriterleri beceri listesine ekleme.
- Belgelenmiş sertifika ve lisansları (örn. "İSG Uzmanlık Belgesi", "ACCA", "CPA", "Hemşirelik Diploması") mutlaka listele.

2. ANLAMSAL BENZERLİK VE SEMANTİK EŞLEŞTİRME (SEMANTIC SIMILARITY) - 20 MESLEK İÇİN ÖRNEKLER:

--- MUHASEBECİ / MALİ MÜŞAVİR ---
- CV'de "SMMM stajı", "muhasebe programları kullanımı", "bilanço düzenleme" varsa → İlandaki "muhasebe bilgisi", "Muhasebeci", "Mali Müşavir" KARŞILANMIŞ sayılır.
- CV'de "Logo Tiger", "Luca", "Netsis", "SAP FI", "e-Defter", "e-Fatura" varsa → İlandaki "muhasebe yazılımı", "ERP deneyimi" KARŞILANMIŞ sayılır.
- CV'de "vergi beyannamesi", "KDV", "gelir tablosu", "mizan" varsa → İlandaki "vergi mevzuatı bilgisi", "mali raporlama" KARŞILANMIŞ sayılır.

--- SATIŞ TEMSİLCİSİ / SAHA SATIŞI ---
- CV'de "saha satışı", "müşteri ziyareti", "hedef odaklı çalışma" varsa → İlandaki "satış deneyimi", "sahaya yönelik çalışma" KARŞILANMIŞ sayılır.
- CV'de "CRM", "Salesforce", "satış rakamlarını tutturma", "satış hedefi gerçekleştirme" varsa → İlandaki "müşteri portföyü yönetimi" KARŞILANMIŞ sayılır.
- CV'de "B2B satış", "bayi yönetimi", "teklif hazırlama", "müzakere" varsa → İlandaki "ticari satış deneyimi" KARŞILANMIŞ sayılır.

--- MÜŞTERİ TEMSİLCİSİ / ÇAĞRI MERKEZİ ---
- CV'de "çağrı merkezi deneyimi", "inbound/outbound çağrı", "müşteri şikayeti çözme" varsa → İlandaki "müşteri hizmetleri", "çağrı merkezi" KARŞILANMIŞ sayılır.
- CV'de "Genesys", "Avaya", "CRM programı", "biletleme sistemi (ticketing)" varsa → İlandaki "çağrı merkezi yazılımı" KARŞILANMIŞ sayılır.
- CV'de "empati", "ikna kabiliyeti", "sözlü iletişim" varsa → İlandaki "iletişim becerileri", "müşteri odaklılık" KARŞILANMIŞ sayılır.

--- OFİS SEKRETERİ / İDARİ ASİSTAN ---
- CV'de "Microsoft Office (Word, Excel, Outlook, PowerPoint)", "toplantı organizasyonu", "evrak takibi" varsa → İlandaki "ofis yönetimi", "sekreterlik" KARŞILANMIŞ sayılır.
- CV'de "yazışma takibi", "arşivleme", "randevu yönetimi", "dosyalama" varsa → İlandaki "idari destek", "ofis koordinasyonu" KARŞILANMIŞ sayılır.
- CV'de "çok hatlı telefon", "resepsiyonistlik", "misafir karşılama" varsa → İlandaki "karşılama ve yönlendirme" KARŞILANMIŞ sayılır.

--- İNSAN KAYNAKLARI UZMANI ---
- CV'de "işe alım süreci", "mülakat tekniği", "yetkinlik bazlı mülakat" varsa → İlandaki "İK işe alım", "Talent Acquisition" KARŞILANMIŞ sayılır.
- CV'de "bordro hesaplama", "SGK bildirimi", "4857 İş Kanunu bilgisi" varsa → İlandaki "özlük işlemleri", "İK operasyonları" KARŞILANMIŞ sayılır.
- CV'de "performans yönetimi", "oryantasyon programı", "çalışan memnuniyeti anketi" varsa → İlandaki "İK süreçleri", "HRIS" KARŞILANMIŞ sayılır.
- CV'de "IK yönetim sistemi", "SAP HR", "PDKS" varsa → İlandaki "İK yazılımı" KARŞILANMIŞ sayılır.

--- PAZARLAMA UZMANI ---
- CV'de "dijital pazarlama", "Google Ads", "Meta Ads (Facebook/Instagram reklamı)", "SEO/SEM" varsa → İlandaki "dijital reklam yönetimi", "performans pazarlama" KARŞILANMIŞ sayılır.
- CV'de "sosyal medya yönetimi", "içerik takvimi", "Instagram/Facebook analitik" varsa → İlandaki "sosyal medya uzmanı" KARŞILANMIŞ sayılır.
- CV'de "pazar araştırması", "rakip analizi", "marka yönetimi", "ürün lansmanı" varsa → İlandaki "pazarlama stratejisi" KARŞILANMIŞ sayılır.
- CV'de "Google Analytics", "Hotjar", "A/B testi" varsa → İlandaki "veri odaklı pazarlama" KARŞILANMIŞ sayılır.

--- GRAFİK TASARIMCI ---
- CV'de "Adobe Photoshop", "Illustrator", "InDesign", "Figma", "Canva", "CorelDRAW" varsa → İlandaki "grafik tasarım yazılımı" KARŞILANMIŞ sayılır.
- CV'de "logo tasarımı", "kurumsal kimlik", "baskı tasarımı", "ambalaj tasarımı" varsa → İlandaki "grafik tasarım deneyimi" KARŞILANMIŞ sayılır.
- CV'de "motion design", "After Effects", "video kurgu", "animasyon" varsa → İlandaki "görsel içerik üretimi", "video prodüksiyon" KARŞILANMIŞ sayılır.
- CV'de "UI/UX tasarımı", "prototipleme", "kullanıcı deneyimi" varsa → İlandaki "dijital tasarım" KARŞILANMIŞ sayılır.

--- YAZILIM GELİŞTİRİCİ / WEB TASARIMCI ---
- CV'de "Python", "Django", "Flask", "FastAPI" varsa → İlandaki "Python geliştirici" KARŞILANMIŞ sayılır.
- CV'de "React", "Vue", "Angular", "HTML/CSS/JavaScript", "TypeScript" varsa → İlandaki "front-end geliştirici", "web tasarımcı" KARŞILANMIŞ sayılır.
- CV'de "PostgreSQL", "MySQL", "MongoDB", "Redis" varsa → İlandaki "veritabanı yönetimi" KARŞILANMIŞ sayılır.
- CV'de "Java", "Spring Boot", ".NET", "C#" varsa → İlandaki "back-end geliştirici" KARŞILANMIŞ sayılır.

--- ELEKTRİK TEKNİKERİ ---
- CV'de "elektrik pano montajı", "kablo tesisatı", "trafo bakımı", "topraklama" varsa → İlandaki "elektrik teknikeri", "elektrik bakım-onarım" KARŞILANMIŞ sayılır.
- CV'de "PLC programlama", "SCADA", "otomasyon sistemleri" varsa → İlandaki "endüstriyel otomasyon teknikeri" KARŞILANMIŞ sayılır.
- CV'de "Elektrik Mühendisliği/Teknikerliği diplomas", "elektrik teknikerliği" varsa → İlandaki "elektrik mezunu", "elektrik teknikeri" KARŞILANMIŞ sayılır.
- CV'de "kesintisiz güç kaynağı (UPS)", "enerji verimliliği", "aydınlatma sistemi" varsa → İlandaki "elektrik bakım" KARŞILANMIŞ sayılır.

--- MAKİNE TEKNİKERİ ---
- CV'de "CNC operatörü", "torna freze", "hydraulik pnömatik sistemi" varsa → İlandaki "makine teknikeri", "üretim bakım" KARŞILANMIŞ sayılır.
- CV'de "Makine Mühendisliği/Teknikerliği", "mekanik bakım-onarım" varsa → İlandaki "makine mezunu" KARŞILANMIŞ sayılır.
- CV'de "kaynak (MIG/TIG/elektrik)", "pres operatörü", "üretim hattı bakımı" varsa → İlandaki "makine bakım teknikeri" KARŞILANMIŞ sayılır.

--- HEMŞİRE / SAĞLIK PERSONELİ ---
- CV'de "hemşirelik diploması", "hemşire lisansı", "klinik hemşireliği" varsa → İlandaki "hemşire", "sağlık personeli" KARŞILANMIŞ sayılır.
- CV'de "hasta bakımı", "ilaç uygulama", "enjeksiyon", "yaşam belirtileri takibi" varsa → İlandaki "hasta bakım sorumluluğu" KARŞILANMIŞ sayılır.
- CV'de "yoğun bakım", "ameliyathane hemşiresi", "acil servis", "diyaliz ünitesi" varsa → İlandaki "klinik deneyim" KARŞILANMIŞ sayılır.
- CV'de "diyetisyen", "beslenme uzmanı", "klinik diyetetik", "diyet listesi hazırlama" varsa → İlandaki "diyetisyen", "beslenme danışmanı" KARŞILANMIŞ sayılır.
- CV'de "fizyoterapist", "rehabilitasyon", "fizik tedavi" varsa → İlandaki "fizyoterapi uzmanı" KARŞILANMIŞ sayılır.

--- ÖĞRETMEN / EĞİTMEN ---
- CV'de "sınıf yönetimi", "ders planı hazırlama", "MEB müfredatı" varsa → İlandaki "öğretmen", "eğitimci" KARŞILANMIŞ sayılır.
- CV'de "öğretmenlik sertifikası", "pedagojik formasyon", "eğitim fakültesi mezuniyeti" varsa → İlandaki "öğretmenlik belgesi" KARŞILANMIŞ sayılır.
- CV'de "İngilizce öğretmenliği", "CELTA", "TESOL", "IELTS" varsa → İlandaki "yabancı dil öğretmeni" KARŞILANMIŞ sayılır.
- CV'de "özel ders", "dershane deneyimi", "LGS/YKS hazırlık" varsa → İlandaki "öğrenci koçluğu" KARŞILANMIŞ sayılır.

--- BANKA PERSONELİ / FİNANS ---
- CV'de "bankacılık deneyimi", "kredi değerlendirme", "mevduat işlemleri", "müşteri portföyü" varsa → İlandaki "banka personeli", "bireysel bankacılık" KARŞILANMIŞ sayılır.
- CV'de "SWIFT", "EFT/havale işlemleri", "kasa işlemleri", "ATM yönetimi" varsa → İlandaki "bankacılık operasyonları" KARŞILANMIŞ sayılır.
- CV'de "finans/bankacılık mezuniyeti", "iktisat lisansı", "işletme mezuniyeti" varsa → İlandaki "finans mezunu" KARŞILANMIŞ sayılır.
- CV'de "risk analizi", "mali analiz", "bilanço okuma" varsa → İlandaki "finansal analiz" KARŞILANMIŞ sayılır.

--- LOJİSTİK UZMANI ---
- CV'de "lojistik operasyon", "nakliye yönetimi", "kargo takibi", "route planlama" varsa → İlandaki "lojistik uzmanı" KARŞILANMIŞ sayılır.
- CV'de "gümrük işlemleri", "ithalat/ihracat belgesi", "freight forwarding" varsa → İlandaki "dış ticaret lojistiği" KARŞILANMIŞ sayılır.
- CV'de "tedarik zinciri yönetimi", "ERP (SAP MM, Logo)", "sevkiyat planlaması" varsa → İlandaki "tedarik zinciri" KARŞILANMIŞ sayılır.

--- DEPO SORUMLUSU ---
- CV'de "depo yönetimi", "stok takibi", "WMS (Warehouse Management System)" varsa → İlandaki "depo sorumlusu", "ambar yönetimi" KARŞILANMIŞ sayılır.
- CV'de "barkod sistemi", "FIFO/LIFO", "envanter sayımı", "forklift" varsa → İlandaki "depo operasyonu" KARŞILANMIŞ sayılır.
- CV'de "mal kabul/sevkiyat", "stok raporlama", "depo düzeni" varsa → İlandaki "lojistik depo yönetimi" KARŞILANMIŞ sayılır.

--- VERİ GİRİŞİ ELEMANI / BÜRO HİZMETLERİ ---
- CV'de "Microsoft Excel (hızlı veri girişi)", "klavye hızı", "veri doğrulama", "veri temizleme" varsa → İlandaki "veri giriş elemanı" KARŞILANMIŞ sayılır.
- CV'de "10 parmak yazarlık", "ofis programları", "tablo düzenleme" varsa → İlandaki "büro hizmetleri" KARŞILANMIŞ sayılır.

--- PROJE YÖNETİCİSİ / PMO ---
- CV'de "proje planlama", "MS Project", "Jira", "Asana", "Gantt chart" varsa → İlandaki "proje yöneticisi", "proje koordinatörü" KARŞILANMIŞ sayılır.
- CV'de "PMP sertifikası", "Agile/Scrum", "bütçe takibi", "kaynak planlaması" varsa → İlandaki "proje yönetim metodolojisi" KARŞILANMIŞ sayılır.
- CV'de "paydaş yönetimi", "risk yönetimi", "süreç iyileştirme" varsa → İlandaki "proje yönetimi yetkinlikleri" KARŞILANMIŞ sayılır.

--- İŞ GÜVENLİĞİ UZMANI ---
- CV'de "İSG uzmanlık belgesi (A/B/C sınıfı)", "OSGB deneyimi", "risk değerlendirme raporu" varsa → İlandaki "iş güvenliği uzmanı" KARŞILANMIŞ sayılır.
- CV'de "acil durum planı", "kaza analizi", "ramak kala olayı bildirimi" varsa → İlandaki "iş sağlığı ve güvenliği yönetimi" KARŞILANMIŞ sayılır.
- CV'de "yangın tatbikatı", "KKD denetimi", "ekipman güvenlik kontrolleri" varsa → İlandaki "İSG uygulamaları" KARŞILANMIŞ sayılır.

--- E-TİCARET UZMANI ---
- CV'de "e-ticaret platform yönetimi", "Trendyol/Hepsiburada/N11 satıcı paneli", "pazaryeri entegrasyonu" varsa → İlandaki "e-ticaret yöneticisi" KARŞILANMIŞ sayılır.
- CV'de "ürün listeleme optimizasyonu", "fiyatlandırma stratejisi", "pazaryeri reklamı (reklam kampanyası)" varsa → İlandaki "e-ticaret operasyonları" KARŞILANMIŞ sayılır.
- CV'de "sipariş yönetimi", "iade süreçleri", "müşteri yorumları yönetimi" varsa → İlandaki "e-ticaret müşteri deneyimi" KARŞILANMIŞ sayılır.

Verilen iş ilanı için şunları çıkar:
1. zorunlu_beceriler: İlanda aranan tüm zorunlu nitelikler, sertifikalar, deneyimler ve yetkinlikler.
2. tercih_beceriler: "tercih edilir", "artı puan", "avantaj" ifadeli yetkinlikler.
3. eslesen_zorunlu: CV'de semantik olarak karşılanan zorunlu beceriler.
4. eslesen_tercih: CV'de semantik olarak karşılanan tercih becerileri.
5. eksik_beceriler: CV'de gerçekten bulunmayan beceriler.
6. deneyim_durumu: "fazla" | "uygun" | "eksik" | "belirsiz"
7. egitim_uyumu: true | false | null
8. sektor_uyumu: true | false
9. cv_onerileri: Eksik beceriler için 3-5 somut ve uygulanabilir öneri (o mesleğe özgü, genel değil)

YANIT FORMATI (SADECE JSON):
{
  "baslik": "İlan Başlığı",
  "sirket": "Şirket Adı",
  "lokasyon": "Şehir",
  "link": "https://...",
  "ilan_no": "1234567",
  "zorunlu_beceriler": ["Muhasebe Bilgisi", "Logo Tiger", "Vergi Mevzuatı"],
  "tercih_beceriler": ["SMMM Stajı", "SAP"],
  "eslesen_zorunlu": ["Muhasebe Bilgisi", "Vergi Mevzuatı"],
  "eslesen_tercih": [],
  "eksik_beceriler": ["Logo Tiger", "SAP"],
  "deneyim_durumu": "uygun",
  "egitim_uyumu": true,
  "sektor_uyumu": true,
  "cv_onerileri": ["Logo Tiger veya Luca muhasebe yazılımını öğrenmek seni öne çıkarır."]
}"""

    prompt = f"""KULLANICI CV'Sİ:
{cv_text}

İŞ İLANI (JSON):
{json.dumps(ilan_payload, ensure_ascii=False, indent=2)}

Bu ilan için CV'deki becerileri ilanın gereksinimleriyle eşleştir. Sadece NLP görevi yap, skor hesaplama!
"""

    try:
        # Tek ilan için max_tokens 1500 yeterlidir (hızlı yanıt için)
        response = await complete_json(prompt=prompt, system_prompt=system_prompt, max_tokens=1500)
        return response
    except Exception as e:
        import logging
        logging.error(f"İlan analiz hatası ({ilan.get('baslik')}): {str(e)}")
        return None


@router.post("/analyze", response_model=JobMatcherResponse)
async def analyze_jobs(request: JobMatcherRequest) -> JobMatcherResponse:
    if not request.cv_text.strip() or not request.position.strip():
        raise HTTPException(status_code=400, detail="cv_text ve position zorunludur.")

    # 1. Scrape jobs (thread'de çalıştır, event loop'u bloklama)
    # Maksimum 5 ilan çekecek şekilde limiti 5 olarak gönderiyoruz
    try:
        ilanlar = await asyncio.to_thread(eleman_ara, request.position, 5)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"İlanlar çekilirken hata oluştu: {str(e)}")

    if not ilanlar:
        return JobMatcherResponse(matches=[])

    # 2. Bütün ilanları paralel olarak LLM ile analiz et
    tasks = [analyze_single_job(ilan, request.cv_text) for ilan in ilanlar]
    matches = await asyncio.gather(*tasks)

    results = []
    for original_ilan, m in zip(ilanlar, matches):
        if not m:
            continue

        detay = original_ilan.get("detay", {})

        # Python'da deterministik skor hesapla
        zorunlu = m.get("zorunlu_beceriler", [])
        tercih = m.get("tercih_beceriler", [])
        esl_zorunlu = m.get("eslesen_zorunlu", [])
        esl_tercih = m.get("eslesen_tercih", [])
        deneyim_durumu = m.get("deneyim_durumu", "belirsiz")
        egitim_uyumu = m.get("egitim_uyumu", None)
        sektor_uyumu = m.get("sektor_uyumu", True)

        uyum_skoru, maks_skor, skor_aciklamasi = calculate_score(
            zorunlu_beceriler=zorunlu,
            tercih_beceriler=tercih,
            eslesen_zorunlu=esl_zorunlu,
            eslesen_tercih=esl_tercih,
            deneyim_durumu=deneyim_durumu,
            egitim_uyumu=egitim_uyumu,
            sektor_uyumu=sektor_uyumu,
        )

        # Tüm eşleşen beceriler (gösterim için)
        eslesen_tumu = esl_zorunlu + esl_tercih

        results.append(JobMatchResult(
            baslik=m.get("baslik") or original_ilan.get("baslik", "Bilinmiyor"),
            sirket=m.get("sirket") or original_ilan.get("sirket", "Bilinmiyor"),
            lokasyon=m.get("lokasyon") or original_ilan.get("lokasyon", "Bilinmiyor"),
            link=m.get("link") or original_ilan.get("link", ""),
            ilan_no=str(m.get("ilan_no")) or str(detay.get("ilan_no", "")),
            uyum_skoru=uyum_skoru,
            eksik_yetkinlikler=m.get("eksik_beceriler", []),
            cv_onerileri=m.get("cv_onerileri", []),
            aciklama=detay.get("aciklama") or m.get("aciklama", ""),
            skor_aciklamasi=skor_aciklamasi,
            eslesen_beceriler=eslesen_tumu,
            maksimum_ulasabilir_skor=maks_skor,
            cinsiyet=detay.get("cinsiyet"),
            yas=detay.get("yas"),
            deneyim=detay.get("deneyim"),
            calisma_sekli=detay.get("calisma_sekli"),
            egitim=detay.get("egitim")
        ))

    results.sort(key=lambda x: x.uyum_skoru, reverse=True)
    return JobMatcherResponse(matches=results)
