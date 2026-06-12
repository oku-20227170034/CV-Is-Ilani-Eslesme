"""
HTML sayfasini BeautifulSoup ile incele - Test scripti 2
"""

import sys

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError as e:
    print(f"[HATA] {e}  -->  pip install requests beautifulsoup4")
    sys.exit(1)

# Incelenecek URL
URL = "https://www.eleman.net/is-ilanlari?q=yazilim&sort=date"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9",
}

print(f"URL inceleniyor: {URL}")
print("-" * 60)

try:
    resp = requests.get(URL, headers=HEADERS, timeout=15)
    print(f"HTTP Status : {resp.status_code}")
    print(f"Encoding    : {resp.encoding}")
    print(f"HTML boyutu : {len(resp.text)} karakter")
    print()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Tum h3 basliklarini listele
    h3_tags = soup.find_all("h3")
    print(f"=== H3 BASLIKLARI ({len(h3_tags)} adet) ===")
    for i, h3 in enumerate(h3_tags[:20], 1):
        print(f"  [{i:02d}] {h3.get_text(strip=True)[:80]}")
        print(f"       class: {h3.get('class', 'yok')}")

    print()

    # 'ilan' iceren tum element class'larini listele
    print("=== 'ilan' KELIMESINI ICEREN ELEMENTLER ===")
    ilan_els = soup.find_all(
        lambda tag: tag.get("class") and any("ilan" in c.lower() for c in tag.get("class", []))
    )
    class_sayac = {}
    for el in ilan_els:
        cls = " ".join(el.get("class", []))
        class_sayac[cls] = class_sayac.get(cls, 0) + 1

    for cls, cnt in sorted(class_sayac.items(), key=lambda x: -x[1])[:20]:
        print(f"  {cnt:3d}x  {cls}")

    print()

    # Ilk ilan kartini tam goster
    print("=== ILK ILAN KARTI (detay) ===")
    if ilan_els:
        first = ilan_els[0]
        print(f"Tag     : {first.name}")
        print(f"Class   : {first.get('class')}")
        print(f"Icerik  :\n{first.prettify()[:1000]}")

except Exception as e:
    print(f"[HATA] {e}")
    sys.exit(1)