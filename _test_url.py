"""
URL baglanti testi - Eleman.net ve Indeed.com erisimi kontrol eder
"""

import urllib.request
import urllib.error
import sys
import time

URLS = [
    ("Eleman.net Ana Sayfa", "https://www.eleman.net/"),
    ("Eleman.net Arama", "https://www.eleman.net/is-ilanlari?q=yazilim"),
    ("Indeed.com Turkiye Ana Sayfa", "https://tr.indeed.com/"),
    ("Indeed.com Arama", "https://tr.indeed.com/jobs?q=yazilim&l=Turkiye"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9",
}

print("=" * 60)
print("  URL BAGLANTI TESTI")
print("=" * 60)

for ad, url in URLS:
    print(f"\n[TEST] {ad}")
    print(f"  URL: {url}")
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        start = time.time()
        with urllib.request.urlopen(req, timeout=15) as resp:
            elapsed = time.time() - start
            print(f"  Status  : {resp.status} OK")
            print(f"  Sure    : {elapsed:.2f}s")
            print(f"  Boyut   : {len(resp.read())} byte")
    except urllib.error.HTTPError as e:
        print(f"  [HTTP HATA] {e.code} - {e.reason}")
    except urllib.error.URLError as e:
        print(f"  [URL HATA] {e.reason}")
    except Exception as e:
        print(f"  [HATA] {e}")
    time.sleep(1)

print("\n" + "=" * 60)
print("  Test tamamlandi.")
print("=" * 60)