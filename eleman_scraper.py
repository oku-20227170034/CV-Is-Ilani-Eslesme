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
import time
from urllib.parse import quote

# Windows / VSCode terminali icin UTF-8 zorla
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ── BeautifulSoup zorunlu ────────────────────────────────────
try:
    from bs4 import BeautifulSoup
except ImportError:
    print("[HATA] BeautifulSoup bulunamadi.  -->  pip install beautifulsoup4")
    sys.exit(1)

# ── requests zorunlu ────────────────────────────────────────
import requests as std_requests

# ── curl_cffi opsiyonel (fallback) ──────────────────────────
CURL_CFFI_MEVCUT = False
try:
    from curl_cffi import requests as curl_requests
    CURL_CFFI_MEVCUT = True
except ImportError:
    pass

MAX_LISTINGS = 15

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'tr-TR,tr;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

BASE_URL = "https://www.eleman.net"


def temizle(metin) -> str:
    if not metin:
        return "Belirtilmemis"
    return " ".join(str(metin).split()).strip()


def _get(url, timeout=15):
    """requests ile ister, 403/429 gelirse curl_cffi'ye gecer."""
    try:
        r = std_requests.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code in (200, 201):
            return r.text
        if r.status_code in (403, 429) and CURL_CFFI_MEVCUT:
            r2 = curl_requests.get(url, headers=HEADERS, impersonate="chrome124", timeout=timeout)
            if r2.status_code == 200:
                return r2.text
    except Exception:
        if CURL_CFFI_MEVCUT:
            try:
                r2 = curl_requests.get(url, headers=HEADERS, impersonate="chrome124", timeout=timeout)
                if r2.status_code == 200:
                    return r2.text
            except Exception:
                pass
    return None


def eleman_ara(arama: str) -> list:
    url = f"{BASE_URL}/is-ilanlari?q={quote(arama)}&sort=date"
    print(f"\nEleman.net'te aranıyor: '{arama}'")
    print(f"URL: {url}")
    print("-" * 50)

    html = _get(url)
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
                elif any(k in m for k in ["Istanbul", "İstanbul", "Ankara", "Izmir", "İzmir", "Antalya", "Bursa", "Turkiye", "Türkiye"]):
                    lokasyon = m

            href = kart.get("href") or (kart.find("a", href=True) or {}).get("href", "")
            link = (BASE_URL + href) if href and href.startswith("/") else href or "Belirtilmemis"

            # Detay sayfasindan aciklama cek
            aciklama = ""
            if link and link != "Belirtilmemis":
                try:
                    det_html = _get(link, timeout=10)
                    if det_html:
                        det_soup = BeautifulSoup(det_html, "html.parser")
                        desc_el = det_soup.find("div", class_=lambda c: c and ("desc" in str(c).lower() or "aciklama" in str(c).lower()))
                        if desc_el:
                            aciklama = temizle(desc_el.get_text())[:300]
                    time.sleep(0.5)
                except Exception:
                    pass

            ilanlar.append({
                "baslik": baslik,
                "sirket": sirket,
                "lokasyon": lokasyon,
                "link": link,
                "aciklama": aciklama,
            })
        except Exception:
            continue

    return ilanlar


def yazdir(ilanlar: list):
    if not ilanlar:
        print("\n[!] Hicbir ilan bulunamadi.\n")
        return

    print(f"\n{'=' * 65}")
    print(f"  Toplam {len(ilanlar)} is ilani  |  Eleman.net Turkiye")
    print(f"{'=' * 65}\n")

    for i, ilan in enumerate(ilanlar, 1):
        ayrac = "-" * 55
        print(f"  [{i:02d}] {ayrac}")
        print(f"  | Baslik   : {ilan['baslik']}")
        print(f"  | Sirket   : {ilan['sirket']}")
        print(f"  | Lokasyon : {ilan['lokasyon']}")
        print(f"  | Link     : {ilan['link'][:80]}")

        aciklama = ilan.get("aciklama", "")
        if aciklama:
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
