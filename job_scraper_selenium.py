"""
============================================================
  ASOZ IS ILANI ARACI  -  Eleman.net Turkiye
  Selenium WebDriver tabanli (Bot bypass)
============================================================

KURULUM:
    pip install selenium webdriver-manager beautifulsoup4

KULLANIM:
    python job_scraper_selenium.py

NOT:
    Bu dosya eleman_scraper.py'nin Selenium tabanli yedek
    versiyonudur. Eleman.net'in anti-bot korumalarini
    gercek tarayici aciarak aser. Daha yavas ancak daha
    guvenilirdir.
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

# ── Selenium + WebDriver Manager ──
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    print("[HATA] pip install selenium webdriver-manager")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────
MAX_LISTINGS = 15
BASE_URL = "https://www.eleman.net"


def temizle(metin) -> str:
    if not metin:
        return "Belirtilmemis"
    return " ".join(str(metin).split()).strip()


def tarayici_baslat():
    """Headless Chrome tarayicisini baslatir."""
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


def eleman_ara(arama: str) -> list:
    """
    Eleman.net is ilanlarini Selenium ile ceker.
    """
    url = f"{BASE_URL}/is-ilanlari?q={quote(arama)}&sort=date"

    print(f"\nEleman.net'te aranıyor: '{arama}'")
    print(f"URL: {url}")
    print("Tarayici baslatiliyor (bu biraz zaman alabilir)...")

    driver = None
    ilanlar = []

    try:
        driver = tarayici_baslat()
        driver.get(BASE_URL)
        time.sleep(2)

        driver.get(url)
        print("Sayfa yukleniyor...")
        time.sleep(3)

        # Sayfanin yuklenmesini bekle
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "h3"))
            )
        except Exception:
            pass

        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")

        kartlar = (
            soup.find_all("a", class_=lambda c: c and "ilan" in str(c).lower()) or
            soup.find_all("div", class_=lambda c: c and "ilan" in str(c).lower())
        )

        print(f"    {len(kartlar)} ilan karti bulundu.")

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

    except Exception as e:
        print(f"[HATA] Selenium hatasi: {e}")
    finally:
        if driver:
            driver.quit()

    return ilanlar


def main():
    print("\n" + "=" * 60)
    print("  ASOZ IS ILANI ARACI - Eleman.net Turkiye")
    print("  Selenium WebDriver ile (Bot bypass)")
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