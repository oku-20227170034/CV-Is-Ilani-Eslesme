"""
Indeed.com scraper testi - job_scraper.py'yi test eder
"""

import sys
import os

# Proje kokune ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from job_scraper import indeed_ara
except ImportError as e:
    print(f"[HATA] job_scraper import edilemedi: {e}")
    sys.exit(1)

print("=" * 60)
print("  INDEED.COM SCRAPER TESTI")
print("=" * 60)

TEST_ARAMALARI = [
    "yazilim gelistirici",
    "python developer",
]

for arama in TEST_ARAMALARI:
    print(f"\n>>> Arama: '{arama}'")
    try:
        ilanlar = indeed_ara(arama)
        print(f"    Sonuc: {len(ilanlar)} ilan bulundu")
        if ilanlar:
            print(f"    Ilk ilan: {ilanlar[0]['baslik']} - {ilanlar[0]['sirket']}")
    except Exception as e:
        print(f"    [HATA] {e}")

print("\n[OK] Test tamamlandi.")