"""
============================================================
  ASOZ IS ILANI ARACI  -  Eleman.net Turkiye
  curl_cffi (TLS/JA3 fingerprint bypass) ile alternatif versiyon
============================================================

KURULUM:
    pip install curl_cffi --upgrade
    pip install beautifulsoup4

KULLANIM:
    python job_scraper_eleman.py
"""

import sys
import time
from urllib.parse import quote

# ── BeautifulSoup ──
try:
    from bs4 import BeautifulSoup
except ImportError:
    print("[HATA] pip install beautifulsoup4")
    sys.exit(1)

# ── curl_cffi (dokumantan: github.com/lexiforest/curl_cffi) ──
try:
    from curl_cffi import requests as curl_requests
except ImportError:
    print("[HATA] pip install curl_cffi --upgrade")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────
MAX_LISTINGS = 15
BASE_URL = "https://www.eleman.net"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Upgrade-Insecure-Requests': '1',
    'Referer': 'https://google.com',
}


def temizle(metin) -> str:
    if not metin:
        return "Belirtilmemis"
    return " ".join(str(metin).split()).strip()


def eleman_ara(arama: str) -> list:
    """
    Eleman.net is ilanlarini curl_cffi ile ceker.

    curl_cffi kutuphanesi Chrome'un TLS parmak izini (JA3/JA4) birebir
    taklit eder. Bot korumalarini bu sekilde aser.
    """
    url = f"{BASE_URL}/is-ilanlari?q={quote(arama)}&sort=date"

    print(f"\nEleman.net'te aranıyor: '{arama}'")
    print(f"URL: {url}")
    print("-" * 50)

    session = curl_requests.Session()

    # Adim 1: Ana sayfa ziyareti (gercek kullanici gibi davran)
    print("[1/2] Eleman.net ana sayfasi ziyaret ediliyor...")
    try:
        session.get(
            BASE_URL,
            headers=HEADERS,
            impersonate="chrome124",
            timeout=15
        )
        time.sleep(1)
    except Exception as e:
        print(f"    Uyari - ana sayfa: {e}")

    # Adim 2: Arama istegi
    print("[2/2] Arama sonuclari cekiliyor...")
    html = None

    for surum in ["chrome124", "chrome120", "chrome116"]:
        try:
            yanit = session.get(
                url,
                headers=HEADERS,
                impersonate=surum,
                timeout=20
            )
            print(f"    {surum} -> HTTP {yanit.status_code}")
            if yanit.status_code == 200:
                html = yanit.text
                break
            elif yanit.status_code in (403, 429):
                time.sleep(2)
                continue
        except Exception as e:
            print(f"    {surum} hata: {e}")
            continue

    if not html:
        print("[!] Eleman.net'e erisilemedi.")
        return []

    soup = BeautifulSoup(html, "html.parser")
    kartlar = (
        soup.find_all("a", class_=lambda c: c and "ilan" in str(c).lower()) or
        soup.find_all("div", class_=lambda c: c and "ilan" in str(c).lower())
    )

    print(f"    {len(kartlar)} ilan karti bulundu.")
    ilanlar = []

    for kart in kartlar:
        if len(ilanlar) >= MAX_LISTINGS:
            break
        try:
            baslik_el = kart.find("h3") or kart.find("h2")
            if not baslik_el:
                continue
            baslik = temizle(baslik_el.get_text())
            if not baslik:
                continue

            metinler = [temizle(s) for s in kart.stripped_strings if s]
            sirket = "Belirtilmemis"
            lokasyon = "Belirtilmemis"
            for m in metinler:
                if any(k in m for k in ["A.S.", "A.Ş.", "Ltd.", "San.", "Tic."]):
                    sirket = m
                elif any(k in m for k in ["İstanbul", "Ankara", "İzmir", "Antalya", "Bursa", "Türkiye"]):
                    lokasyon = m

            href = kart.get("href") or ""
            if not href and kart.find("a", href=True):
                href = kart.find("a", href=True)["href"]
            link = (BASE_URL + href) if href.startswith("/") else href or "Belirtilmemis"

            ilanlar.append({
                "baslik":   baslik,
                "sirket":   sirket,
                "lokasyon": lokasyon,
                "link":     link,
            })
        except Exception:
            continue

    return ilanlar


def main():
    print("\n" + "=" * 60)
    print("  ASOZ IS ILANI ARACI - Eleman.net Turkiye")
    print("  curl_cffi (TLS bypass) ile")
    print("=" * 60)

    arama = input("\nPozisyon girin (ornek: yazilim gelistirici): ").strip()
    if not arama:
        print("[!] Arama terimi bos olamaz.")
        return

    ilanlar = eleman_ara(arama)

    if ilanlar:
        print(f"\n{'='*60}")
        print(f"  Toplam {len(ilanlar)} is ilani | Eleman.net Turkiye")
        print(f"{'='*60}\n")

        for i, ilan in enumerate(ilanlar, 1):
            print(f"  [{i:02d}] {'-'*54}")
            print(f"       Baslik   : {ilan['baslik']}")
            print(f"       Sirket   : {ilan['sirket']}")
            print(f"       Lokasyon : {ilan['lokasyon']}")
            print(f"       Link     : {ilan['link'][:80]}")
            print()

        print(f"  [OK] {len(ilanlar)} ilan basariyla cekildi!\n")
    else:
        print("\n[!] Hicbir ilan bulunamadi.\n")


if __name__ == "__main__":
    main()
