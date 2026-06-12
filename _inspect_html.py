"""
HTML sayfasini indirip icerigi incele - Test scripti 1
"""

import urllib.request
import sys

# Incelenecek URL
URL = "https://www.eleman.net/is-ilanlari?q=yazilim"

print(f"URL inceleniyor: {URL}")
print("-" * 60)

req = urllib.request.Request(
    URL,
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "tr-TR,tr;q=0.9",
    }
)

try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode("utf-8", errors="replace")
        print(f"HTTP Status : {resp.status}")
        print(f"Content-Type: {resp.headers.get('Content-Type', 'N/A')}")
        print(f"HTML boyutu : {len(html)} karakter")
        print()
        print("=== HTML (ilk 3000 karakter) ===")
        print(html[:3000])
        print()
        print("=== HTML (son 1000 karakter) ===")
        print(html[-1000:])

        # Baslik taglarini say
        import re
        h2_count = len(re.findall(r'<h2', html, re.IGNORECASE))
        h3_count = len(re.findall(r'<h3', html, re.IGNORECASE))
        a_count = len(re.findall(r'<a ', html, re.IGNORECASE))
        print(f"\n=== TAG SAYIMLARI ===")
        print(f"<h2> : {h2_count}")
        print(f"<h3> : {h3_count}")
        print(f"<a>  : {a_count}")

        # 'ilan' kelimesini icerenclass'lari bul
        ilan_classes = re.findall(r'class="([^"]*ilan[^"]*)"', html, re.IGNORECASE)
        unique_classes = list(set(ilan_classes))
        print(f"\n'ilan' iceren class'lar ({len(unique_classes)} adet):")
        for cls in unique_classes[:20]:
            print(f"  - {cls}")

except Exception as e:
    print(f"[HATA] {e}")
    sys.exit(1)