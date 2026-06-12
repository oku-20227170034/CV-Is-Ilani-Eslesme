# -*- coding: utf-8 -*-
"""
============================================================
  ASOZ IS ILANI ARACI  -  Eleman.net Turkiye
  ------------------------------------------------------------
  - Once requests ile dener (hafif, hizli)
  - Basarisiz olursa curl_cffi'ye gecer (TLS bypass)
  - Her ilanin detay sayfasini da ceker (aciklama, gereksinimler vb.)
============================================================

KURULUM:
    pip install requests beautifulsoup4
    pip install curl_cffi       (opsiyonel, fallback icin)

KULLANIM:
    python eleman_scraper.py
"""

import sys
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote

# ── BeautifulSoup zorunlu ────────────────────────────────────
try:
    from bs4 import BeautifulSoup
except ImportError:
    print("[HATA] BeautifulSoup bulunamadi.  -->  pip install beautifulsoup4")
    sys.exit(1)

# ── requests zorunlu ────────────────────────────────────────
import requests as std_requests

# ── curl_cffi opsiyonel (fallback) ──────────────────────────
try:
    from curl_cffi import requests as curl_requests
    CURL_CFFI_MEVCUT = True
except ImportError:
    CURL_CFFI_MEVCUT = False

# ─────────────────────────────────────────────────────────────
MAX_LISTINGS   = 15     # Liste sayfasindan cekilecek maks ilan sayisi (filtreleme sonrasi 5+ sonuc icin)
DETAY_TIMEOUT  = 12     # Detay sayfasi istek suresi (saniye)
LISTE_TIMEOUT  = 15     # Liste sayfasi istek suresi (saniye)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

BASE_URL = "https://www.eleman.net"

# ─────────────────────────────────────────────────────────────
# YARDIMCI FONKSİYONLAR
# ─────────────────────────────────────────────────────────────

def temizle(metin) -> str:
    """Gereksiz bosluk ve satir sonlarini kaldirir."""
    if not metin:
        return "Belirtilmemis"
    return " ".join(str(metin).split()).strip()


def normalize(metin: str) -> str:
    """
    Turkce karakterleri ASCII karsiliklariyla degistirir.
    Buyuk/kucuk harf farki kaldirilir.
    Boylece 'Yazilim' == 'yazılım' eslesmesi saglanir.
    """
    eslesme = {
        'a': 'a', 'A': 'a',
        'b': 'b', 'B': 'b',
        'c': 'c', 'C': 'c',
        'c\u0327': 'c', '\u00e7': 'c', '\u00c7': 'c',
        'd': 'd', 'D': 'd',
        'e': 'e', 'E': 'e',
        'f': 'f', 'F': 'f',
        'g': 'g', 'G': 'g',
        '\u011f': 'g', '\u011e': 'g',
        'h': 'h', 'H': 'h',
        'i': 'i', 'I': 'i',
        '\u0131': 'i', '\u0130': 'i',
        'j': 'j', 'J': 'j',
        'k': 'k', 'K': 'k',
        'l': 'l', 'L': 'l',
        'm': 'm', 'M': 'm',
        'n': 'n', 'N': 'n',
        'o': 'o', 'O': 'o',
        '\u00f6': 'o', '\u00d6': 'o',
        'p': 'p', 'P': 'p',
        'r': 'r', 'R': 'r',
        's': 's', 'S': 's',
        '\u015f': 's', '\u015e': 's',
        't': 't', 'T': 't',
        'u': 'u', 'U': 'u',
        '\u00fc': 'u', '\u00dc': 'u',
        'v': 'v', 'V': 'v',
        'y': 'y', 'Y': 'y',
        'z': 'z', 'Z': 'z',
    }
    return ''.join(eslesme.get(c, c.lower()) for c in metin)



def ilgili_mi(baslik: str, arama: str) -> bool:
    """
    Is ilaninin arama terimiyle ilgili olup olmadigini kontrol eder.

    Strateji:
    1. Arama teriminin herhangi bir kelimesi (3+ harf) baslikta geciyorsa -> KABUL
    2. Baslik tamamen bos veya anlamsizsa -> RET
    3. Diger durumlar -> KABUL (eleman.net zaten arama kategorisine gore filtreli dondurur)

    NOT: Onceki TEKNIK_KELIMELER filtresi kaldirildi; bu filtre yazilim disindaki
    meslekleri (diyetisyen, muhasebeci, pazarlamaci vb.) yanisira filtreleyip
    hicbir sonuc donmemesine neden oluyordu.
    """
    if not baslik or len(baslik.strip()) < 2:
        return False

    baslik_norm = normalize(baslik)

    # Arama teriminin her kelimesini kontrol et (kismi esleme)
    arama_kelimeleri = [k for k in arama.split() if len(k) >= 3]
    if arama_kelimeleri:
        for kelime in arama_kelimeleri:
            # Kelimenin ilk 4 harfini kök olarak kullan (Türkçe çekim ekleri için)
            kok = normalize(kelime[:4] if len(kelime) >= 4 else kelime)
            if kok in baslik_norm:
                return True

    # Arama terimi baslikta hic geçmiyorsa ama eleman.net'ten geliyorsa kabul et
    # (eleman.net zaten ilgili kategoriyle filtrelenmiş sonuc dondurur)
    return True



def _get(url: str, timeout: int = LISTE_TIMEOUT) -> str | None:
    """
    HTTP GET isteği gönderir.
    Önce standart requests dener; başarısız olursa curl_cffi'ye geçer.
    Başarı durumunda HTML metnini döndürür, yoksa None döner.
    """
    # — Deneme 1: requests ————————————————————————————————
    try:
        yanit = std_requests.get(url, headers=HEADERS, timeout=timeout)
        if yanit.status_code == 200:
            return yanit.text
        else:
            print(f"    [requests] HTTP {yanit.status_code} -> curl_cffi fallback deneniyor...")
    except Exception as e:
        print(f"    [requests] Hata: {e} -> curl_cffi fallback deneniyor...")

    # — Deneme 2: curl_cffi (TLS fingerprint bypass) ————————
    if not CURL_CFFI_MEVCUT:
        print("    [!] curl_cffi yuklu degil. Sadece requests kullanilabilir.")
        print("        Yuklemek icin:  pip install curl_cffi")
        return None

    try:
        yanit = curl_requests.get(
            url,
            headers=HEADERS,
            impersonate="chrome124",
            timeout=timeout,
        )
        if yanit.status_code == 200:
            print("    [curl_cffi] Basarili!")
            return yanit.text
        else:
            print(f"    [curl_cffi] HTTP {yanit.status_code} - Erisilemedi.")
    except Exception as e:
        print(f"    [curl_cffi] Hata: {e}")

    return None


# ─────────────────────────────────────────────────────────────
# DETAY SAYFASI ÇEKİCİ
# ─────────────────────────────────────────────────────────────

def detay_cek(link: str) -> dict:
    """
    Eleman.net ilan detay sayfasini ceker.
    Gercek HTML class'lari kullanilarak su alanlar elde edilir:
      - aciklama      : Gercek is tanimi metni  (class: u-font-size-sm)
      - calisma_sekli : Tam Zamanli / Yari Zamanli vb.
      - deneyim       : Ornek -> 'Deneyim: 3-4 Yil'
      - egitim        : Ornek -> 'Egitim: Lise'
      - cinsiyet      : Kadin / Erkek / Farketmez
      - yas           : Yas araligi, ornek -> '30 - 45 arasi'
      - ilan_no       : Ilan numarasi
    Tum bu badge'ler class='is_ilani_ozellik_kutusu' span'lari icerisindedir.
    """
    bos = {
        "aciklama":      "Belirtilmemis",
        "calisma_sekli": "Belirtilmemis",
        "deneyim":       "Belirtilmemis",
        "egitim":        "Belirtilmemis",
        "cinsiyet":      "Belirtilmemis",
        "yas":           "Belirtilmemis",
        "ilan_no":       "Belirtilmemis",
    }

    if not link or link == "Belirtilmemis":
        return bos

    html = _get(link, timeout=DETAY_TIMEOUT)
    if not html:
        return bos

    soup = BeautifulSoup(html, "html.parser")
    detay = bos.copy()

    # ── 1) GERCEK ILAN ACIKLAMASI ─────────────────────────────
    # class="u-font-size-sm" icinde asil is tanimi metni bulunur.
    # "d-information" div'i genel kutu; icindeki "u-font-size-sm" asil metni verir.
    d_info = soup.find("div", class_="d-information")
    if d_info:
        u_font = d_info.find("div", class_="u-font-size-sm")
        if u_font:
            metin = u_font.get_text(separator="\n").strip()
            # Clean up excessive newlines
            metin = re.sub(r'\n\s*\n', '\n\n', metin)
            if len(metin) > 10:
                detay["aciklama"] = metin

        # ilan_no -> "Eleman.net'te yayinlanmaktadir. Ilan No: XXXXXX"
        ilan_no_text = d_info.get_text()
        no_match = re.search(r'[Ii]lan No[:\s]+([\d]+)', ilan_no_text)
        if no_match:
            detay["ilan_no"] = no_match.group(1)

    # ── 2) BADGE'LER (is_ilani_ozellik_kutusu span'lari) ───────
    # Her span bir ozellik badge'i: Kadin, 30-45 arasi, Egitim: Lise, Deneyim: 3-4 Yil, Tam Zamanli
    badge_spanlar = soup.find_all("span", class_="is_ilani_ozellik_kutusu")
    for span in badge_spanlar:
        metin      = temizle(span.get_text())
        metin_kucuk = metin.lower()

        # Ilan No (No: 4641618)
        if metin_kucuk.startswith("no:"):
            detay["ilan_no"] = metin.replace("No:", "").strip()

        # Egitim (Egitim: Lise)
        elif metin_kucuk.startswith("egitim:") or "egitim" in metin_kucuk:
            detay["egitim"] = metin

        # Deneyim (Deneyim: 3-4 Yil)
        elif metin_kucuk.startswith("deneyim:") or "deneyim" in metin_kucuk:
            detay["deneyim"] = metin

        # Calisma Sekli (Tam Zamanli, Yari Zamanli, Part Time, Freelance)
        elif any(x in metin_kucuk for x in ["zamanli", "part", "full", "freelance", "sezonal"]):
            detay["calisma_sekli"] = metin

        # Cinsiyet (Kadin, Erkek)
        elif any(x in metin_kucuk for x in ["kadin", "erkek", "farketmez", "cinsiyet"]):
            detay["cinsiyet"] = metin

        # Yas araligı (30 - 45 arasi, 25 - 35 arasi gibi)
        elif "arasi" in metin_kucuk or re.search(r'\d+\s*-\s*\d+', metin):
            detay["yas"] = metin

    return detay


# ─────────────────────────────────────────────────────────────
# LISTE SAYFASI ÇEKİCİ
# ─────────────────────────────────────────────────────────────

def eleman_ara(arama: str, limit: int = 5) -> list:
    """Eleman.net uzerinden is ilanlarini listeler ve her ilanin detayini ceker."""
    # Eleman.net Turkce karakterleri (hemşire → hemsire) duzgun islemiyor.
    # Bu nedenle once normalize edip ASCII karsiligi ile arama yapiyoruz.
    arama_normalize = normalize(arama)       # ş→s, ğ→g, ü→u, ö→o, ı→i, ç→c
    arama_url = f"{BASE_URL}/is-ilanlari?aranan={quote(arama_normalize)}"

    print(f"\nEleman.net'te aranıyor: '{arama}' (normalize: '{arama_normalize}')")
    print(f"  URL: {arama_url}")
    print("-" * 60)

    ilanlar    = []
    sayfa_no   = 1
    max_sayfa  = 5

    # ── Sayfalama döngüsü ─────────────────────────────────────
    while len(ilanlar) < limit and sayfa_no <= max_sayfa:
        sayfa_url = arama_url + (f"&sayfa={sayfa_no}" if sayfa_no > 1 else "")

        if sayfa_no == 1:
            print("[1/3] Siteye baglaniliyor...")
        else:
            print(f"  -> Sayfa {sayfa_no} taranıyor...")

        html = _get(sayfa_url)

        if sayfa_no == 1:
            if html:
                print("  [OK] Baglanti basarili!")
                print("[2/3] İlan kartları ayıklanıyor...")
            else:
                print("[!] Siteye baglanilamadi.")
                break

        if not html:
            break

        soup = BeautifulSoup(html, "html.parser")

        # Eleman.net ilan kart class'ları (birden fazla alternatif)
        kartlar = (
            soup.find_all("div", class_="ilan_listeleme_bol") or
            soup.find_all("div", class_=lambda c: c and "ilan-liste" in str(c)) or
            soup.find_all("article", class_=lambda c: c and "ilan" in str(c))
        )

        if not kartlar:
            print(f"  [!] Sayfa {sayfa_no}'de ilan bulunamadı, durduruluyor.")
            break

        for kart in kartlar:
            if len(ilanlar) >= limit:
                break
            try:
                # Başlık
                baslik_el = kart.find("h3") or kart.find("h2") or kart.find("h4")
                if not baslik_el:
                    continue
                baslik = temizle(baslik_el.get_text())
                if not baslik:
                    continue

                # Baslik filtresi: Arama terimiyle ilgili olmayan ilanlari atla
                if not ilgili_mi(baslik, arama):
                    continue

                # Sirket & Lokasyon
                sirket   = "Belirtilmemis"
                lokasyon = "Turkiye"
                subtitle_el = kart.find("span", class_="c-showcase-box__subtitle")
                if subtitle_el:
                    tam = temizle(subtitle_el.get_text())
                    parcalar = [p.strip() for p in tam.split("-")]
                    if parcalar:
                        sirket = parcalar[0]
                    if len(parcalar) >= 2:
                        lokasyon = " - ".join(parcalar[1:])

                # Link
                link_el = kart.find("a", href=True)
                link    = ""
                if link_el:
                    href = link_el["href"]
                    link = (BASE_URL + href) if href.startswith("/") else href

                # Tekrar eklemeyi önle
                if any(i["link"] == link for i in ilanlar):
                    continue

                ilanlar.append({
                    "baslik":   baslik,
                    "sirket":   sirket,
                    "lokasyon": lokasyon,
                    "link":     link,
                })

            except Exception:
                continue

        sayfa_no += 1

    print(f"  [OK] {len(ilanlar)} ilan listelendi. Detaylar paralel çekiliyor...\n")

    # ── Her ilan için detay çek (paralel) ────────────────────
    print("[3/3] Detay sayfaları paralel işleniyor...")
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_ilan = {executor.submit(detay_cek, ilan["link"]): ilan for ilan in ilanlar}
        for future in as_completed(future_to_ilan):
            ilan = future_to_ilan[future]
            try:
                ilan["detay"] = future.result()
            except Exception:
                ilan["detay"] = {}

    print(f"\n  [TAMAMLANDI] Tüm detaylar hazır!\n")
    return ilanlar


# ─────────────────────────────────────────────────────────────
# EKRANA YAZICI
# ─────────────────────────────────────────────────────────────

def yazdir(ilanlar: list):
    """Ilanlari ve detaylarini terminale yazar."""
    if not ilanlar:
        print("\n[!] Hiçbir ilan bulunamadi.\n")
        return

    print(f"\n{'='*65}")
    print(f"  Toplam {len(ilanlar)} iş ilanı | Eleman.net Türkiye")
    print(f"{'='*65}\n")

    for i, ilan in enumerate(ilanlar, 1):
        d = ilan.get("detay", {})
        ayrac = "-" * 57

        print(f"  +--[{i:02d}]{ayrac}+")
        print(f"  |  Pozisyon    : {ilan['baslik']}")
        print(f"  |  Sirket      : {ilan['sirket']}")
        print(f"  |  Lokasyon    : {ilan['lokasyon']}")
        print(f"  |  Link        : {ilan['link']}")
        if d.get("ilan_no") != "Belirtilmemis":
            print(f"  |  Ilan No     : {d['ilan_no']}")
        print(f"  |")
        print(f"  |  -- DETAYLAR -----------------------------------------------")

        if d.get("cinsiyet") != "Belirtilmemis":
            print(f"  |  Cinsiyet    : {d['cinsiyet']}")
        if d.get("yas") != "Belirtilmemis":
            print(f"  |  Yas         : {d['yas']}")
        if d.get("egitim") != "Belirtilmemis":
            print(f"  |  Egitim      : {d['egitim']}")
        if d.get("deneyim") != "Belirtilmemis":
            print(f"  |  Deneyim     : {d['deneyim']}")
        if d.get("calisma_sekli") != "Belirtilmemis":
            print(f"  |  Calisma     : {d['calisma_sekli']}")

        # Aciklamayi satirlara bolerek yaz
        if d.get("aciklama") != "Belirtilmemis":
            aciklama = d["aciklama"]
            if len(aciklama) > 400:
                aciklama = aciklama[:400] + "..."
            kelimeler = aciklama.split()
            satir = ""
            satirlar = []
            for kelime in kelimeler:
                if len(satir) + len(kelime) + 1 > 60:
                    satirlar.append(satir)
                    satir = kelime
                else:
                    satir = (satir + " " + kelime).strip()
            if satir:
                satirlar.append(satir)
            print(f"  |")
            print(f"  |  Aciklama:")
            for s in satirlar:
                print(f"  |     {s}")

        print(f"  +{ayrac}---+\n")

    print(f"  [OK] {len(ilanlar)} ilan basariyla cekildi!\n")


# ─────────────────────────────────────────────────────────────
# ANA FONKSİYON
# ─────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 65)
    print("  ASOZ İŞ İLANI ARACI  -  Eleman.net Türkiye")
    print("  Altyapi: requests  ->  curl_cffi (otomatik fallback)")
    print("=" * 65)

    if CURL_CFFI_MEVCUT:
        print("  [OK] curl_cffi mevcut (fallback aktif)")
    else:
        print("  [!] curl_cffi yuklu degil (yalnizca requests kullanilir)")

    arama = input("\nPozisyon girin (ornek: yazilim gelistirici): ").strip()
    if not arama:
        print("[!] Arama terimi boş olamaz.")
        return

    ilanlar = eleman_ara(arama)
    yazdir(ilanlar)


if __name__ == "__main__":
    main()
