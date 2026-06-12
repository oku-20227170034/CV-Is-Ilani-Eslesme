"""
============================================================
  ASOZ RESUME MATCHER - Cok Dil Destegi Olusturucu
  generate_translations.py

  Amac: en.json (kaynak) dosyasini okuyup diger dillere
  (tr, es, ja, zh) ceviri uretir veya mevcut cevirileri
  gunceller.

  Kullanim:
    python generate_translations.py

  Gereksinimler:
    pip install openai   (veya litellm)
============================================================
"""

import json
import os
import sys
import time

# ─────────────────────────────────────────────────────────────
# AYARLAR
# ─────────────────────────────────────────────────────────────

# Proje koku
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Frontend messages klasoru
MESSAGES_DIR = os.path.join(BASE_DIR, "apps", "frontend", "messages")

# Kaynak dil (her zaman en.json)
SOURCE_LANG = "en"
SOURCE_FILE = os.path.join(MESSAGES_DIR, "en.json")

# Hedef diller
TARGET_LANGS = {
    "tr": "Turkish (Türkçe)",
    "es": "Spanish (Español)",
    "ja": "Japanese (日本語)",
    "zh": "Chinese Simplified (中文简体)",
}

# LLM API ayarlari
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
LLM_MODEL = "gpt-4o-mini"

# ─────────────────────────────────────────────────────────────
# YARDIMCI FONKSIYONLAR
# ─────────────────────────────────────────────────────────────

def load_json(path: str) -> dict:
    """JSON dosyasini yukler."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: dict):
    """JSON dosyasini kaydeder (guzel formatlanmis)."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  Kaydedildi: {path}")


def flatten_dict(d: dict, prefix: str = "") -> dict:
    """Ic ice sozlugu duzlestir: {'a': {'b': 'c'}} -> {'a.b': 'c'}"""
    result = {}
    for key, value in d.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.update(flatten_dict(value, full_key))
        else:
            result[full_key] = value
    return result


def unflatten_dict(d: dict) -> dict:
    """Duzlestirilen sozlugu geri cevir: {'a.b': 'c'} -> {'a': {'b': 'c'}}"""
    result = {}
    for key, value in d.items():
        parts = key.split(".")
        current = result
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
    return result


def find_missing_keys(source: dict, target: dict, prefix: str = "") -> list:
    """Kaynak sozlukte olup hedefte olmayan anahtarlari bulur."""
    missing = []
    for key, value in source.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if key not in target:
            missing.append(full_key)
        elif isinstance(value, dict) and isinstance(target.get(key), dict):
            missing.extend(find_missing_keys(value, target[key], full_key))
    return missing


def translate_texts(texts: list, target_lang_name: str) -> list:
    """
    OpenAI API kullanarak metinleri cevir.
    texts: ['key1: value1', 'key2: value2', ...] formatinda
    """
    if not OPENAI_API_KEY:
        print("  [UYARI] OPENAI_API_KEY bulunamadi. Manuel ceviri gerekiyor.")
        return [t.split(": ", 1)[-1] if ": " in t else t for t in texts]

    try:
        import openai
        client = openai.OpenAI(api_key=OPENAI_API_KEY)

        batch_text = "\n".join(texts)
        prompt = (
            f"Translate the following UI strings from English to {target_lang_name}. "
            f"Keep the same format (one string per line). "
            f"Do NOT translate: {{variable}} placeholders, HTML tags, or JSON keys. "
            f"Only translate the values after the colon.\n\n"
            f"{batch_text}"
        )

        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        translated = response.choices[0].message.content.strip()
        return translated.split("\n")

    except Exception as e:
        print(f"  [HATA] Ceviri hatasi: {e}")
        return [t.split(": ", 1)[-1] if ": " in t else t for t in texts]


def deep_merge(base: dict, override: dict) -> dict:
    """override sozlugundeki degerleri base'e ekle/guncelle."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


# ─────────────────────────────────────────────────────────────
# ANA FONKSIYON
# ─────────────────────────────────────────────────────────────

def process_language(lang_code: str, lang_name: str, source_data: dict):
    """Tek bir dil icin ceviri islemini gerceklestirir."""
    target_file = os.path.join(MESSAGES_DIR, f"{lang_code}.json")

    print(f"\n{'='*50}")
    print(f"  Dil: {lang_name} ({lang_code})")
    print(f"{'='*50}")

    # Mevcut ceviriyi yukle (varsa)
    if os.path.exists(target_file):
        target_data = load_json(target_file)
        print(f"  Mevcut ceviri yuklendu: {target_file}")
    else:
        target_data = {}
        print(f"  Yeni ceviri olusturuluyor: {target_file}")

    # Eksik anahtarlari bul
    missing_keys = find_missing_keys(source_data, target_data)

    if not missing_keys:
        print(f"  [OK] Tum anahtarlar mevcut! ({len(flatten_dict(source_data))} anahtar)")
        return

    print(f"  Eksik anahtar sayisi: {len(missing_keys)}")

    # Kaynak degerlerini al
    flat_source = flatten_dict(source_data)
    texts_to_translate = []
    for key in missing_keys:
        value = flat_source.get(key, "")
        texts_to_translate.append(f"{key}: {value}")

    # Toplu ceviri (batch 30'ar)
    BATCH_SIZE = 30
    translated_flat = {}

    for i in range(0, len(texts_to_translate), BATCH_SIZE):
        batch = texts_to_translate[i:i+BATCH_SIZE]
        print(f"  Ceviri yapiliyor... ({i+1}-{min(i+BATCH_SIZE, len(texts_to_translate))}/{len(texts_to_translate)})")

        translated_batch = translate_texts(batch, lang_name)

        for j, item in enumerate(batch):
            key = item.split(": ", 1)[0]
            if j < len(translated_batch):
                translated_val = translated_batch[j]
                # "key: value" formatindaysa sadece value al
                if translated_val.startswith(f"{key}: "):
                    translated_val = translated_val[len(f"{key}: "):]
                translated_flat[key] = translated_val
            else:
                # Ceviri alinamadiysa orijinali kullan
                original_val = flat_source.get(key, "")
                translated_flat[key] = original_val

        time.sleep(0.5)  # Rate limit icin bekle

    # Ceviriyi ic ice yapiya donustur
    new_translations = unflatten_dict(translated_flat)

    # Mevcut ceviriyle birlestir
    merged = deep_merge(target_data, new_translations)

    # Kaydet
    save_json(target_file, merged)
    print(f"  [OK] {len(missing_keys)} yeni anahtar eklendi!")


def main():
    print("\n" + "=" * 60)
    print("  RESUME MATCHER - Ceviri Olusturucu")
    print("=" * 60)

    # Kaynak dosyayi kontrol et
    if not os.path.exists(SOURCE_FILE):
        print(f"[HATA] Kaynak dosya bulunamadi: {SOURCE_FILE}")
        sys.exit(1)

    if not os.path.exists(MESSAGES_DIR):
        print(f"[HATA] Messages klasoru bulunamadi: {MESSAGES_DIR}")
        sys.exit(1)

    # Kaynak yukle
    source_data = load_json(SOURCE_FILE)
    total_keys = len(flatten_dict(source_data))
    print(f"\nKaynak: {SOURCE_FILE}")
    print(f"Toplam anahtar: {total_keys}")

    # API key kontrolu
    if not OPENAI_API_KEY:
        print("\n[UYARI] OPENAI_API_KEY env degiskeni bulunamadi.")
        print("        Eksik ceviriler orijinal Ingilizce degerlerle doldurulacak.")
        print("        API key kullanmak icin: set OPENAI_API_KEY=sk-...")

    # Her dil icin islemi calistir
    for lang_code, lang_name in TARGET_LANGS.items():
        try:
            process_language(lang_code, lang_name, source_data)
        except Exception as e:
            print(f"  [HATA] {lang_code} dilinde hata: {e}")
            continue

    print(f"\n{'='*60}")
    print("  Tum ceviriler islendi!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
