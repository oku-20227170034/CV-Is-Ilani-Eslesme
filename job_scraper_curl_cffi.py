"""
============================================================
  ASOZ IS ILANI ARACI  -  Indeed.com Turkiye
  Alternatif: curl_cffi (TLS/JA3 fingerprint bypass)
============================================================

KURULUM:
    pip install curl_cffi --upgrade
    pip install beautifulsoup4

KULLANIM:
    python job_scraper_curl_cffi.py

NOT:
    Bu dosya job_scraper.py'nin curl_cffi tabanli alternatif
    uygulamasidir. Iki dosya da ayni amaci (Indeed.com scraping)
    gerceklestirmektedir; bu dosya daha gelismis TLS bypass
    yetenekleri sunar.
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

# ── curl_cffi ──
try:
    from curl_cffi import requests as curl_requests
except ImportError:
    print("[HATA] pip install curl_cffi --upgrade")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────
MAX_LISTINGS = 15

HEADERS_INDEED = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Upgrade-Insecure-Requests': '1',
    'Referer': 'https://google.com',
}


def temizle(metin) -> str:
    if not metin:
        return "Belirtilmemis"
    return " ".join(str(metin).split()).strip()


def indeed_ara(arama: str) -> list:
    """
    Indeed.com Turkiye is ilanlarini ceker (curl_cffi versiyonu).
    """
    url = (
        "https://tr.indeed.com/jobs"
        f"?q={quote(arama)}"
        "&l=Turkiye"
        "&sort=date"
    )

    print(f"\nIndeed.com'da aranıyor: '{arama}'")
    print(f"URL: {url}")
    print("-" * 50)

    session = curl_requests.Session()

    print("[1/2] Indeed ana sayfasi ziyaret ediliyor...")
    try:
        session.get(
            "https://tr.indeed.com/",
            headers=HEADERS_INDEED,
            impersonate="chrome124",
            timeout=15
        )
        time.sleep(2)
    except Exception as e:
        print(f"    Uyari: {e}")

    print("[2/2] Arama sonuclari cekiliyor...")
    html = None

    for surum in ["chrome124", "chrome120", "chrome116", "chrome110"]:
        try:
            yanit = session.get(
                url,
                headers=HEADERS_INDEED,
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
        print("[!] Indeed'e erisilemedi.")
        return []

    soup = BeautifulSoup(html, "html.parser")
    kartlar = (
        soup.find_all("div", class_="job_seen_beacon") or
        soup.find_all("div", attrs={"data-jk": True}) or
        soup.find_all("li", class_=lambda c: c and "css-" in str(c))
    )

    print(f"    {len(kartlar)} ilan karti bulundu.")
    ilanlar = []

    for kart in kartlar:
        if len(ilanlar) >= MAX_LISTINGS:
            break
        try:
            baslik_el = (
                kart.find("h2", class_=lambda c: c and "jobTitle" in str(c)) or
                kart.find("span", attrs={"title": True})
            )
            if not baslik_el:
                continue
            baslik = temizle(baslik_el.get_text())
            if not baslik:
                continue

            sirket_el = kart.find("span", class_=lambda c: c and "companyName" in str(c))
            sirket = temizle(sirket_el.get_text()) if sirket_el else "Belirtilmemis"

            lokasyon_el = kart.find("div", class_=lambda c: c and "companyLocation" in str(c))
            lokasyon = temizle(lokasyon_el.get_text()) if lokasyon_el else "Turkiye"

            link_el = kart.find("a", href=True)
            if link_el:
                href = link_el["href"]
                link = ("https://tr.indeed.com" + href) if href.startswith("/") else href
            else:
                link = "Belirtilmemis"

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
    print("  ASOZ IS ILANI ARACI - Indeed.com Turkiye")
    print("  curl_cffi (TLS bypass) ile")
    print("=" * 60)

    arama = input("\nPozisyon girin (ornek: yazilim gelistirici): ").strip()
    if not arama:
        print("[!] Arama terimi bos olamaz.")
        return

    ilanlar = indeed_ara(arama)

    if ilanlar:
        print(f"\n{'='*60}")
        print(f"  Toplam {len(ilanlar)} is ilani | Indeed.com Turkiye")
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
