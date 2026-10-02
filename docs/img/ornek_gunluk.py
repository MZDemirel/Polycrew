#!/usr/bin/env python3
"""README resimleri için örnek olay günlüğü (İngilizce ya da Türkçe), şimdiye göre zamanlanmış.

    python3 docs/img/ornek_gunluk.py en /tmp/ornek-en.jsonl
    POLYCREW_OLAYLAR=/tmp/ornek-en.jsonl python3 skills/izle/izle.py --port 8771
    google-chrome --headless=new --window-size=1400,1900 --screenshot=docs/img/izle-en.png \
        "http://localhost:8771/?lang=en"
"""

import json
import sys
import time

# (dakika önce başladı, süre dk ya da None = çalışıyor, sağlayıcı, model ya da rol, efor/kip, iş (en, tr),
#  çıkış, token, puan, gerekçe (en, tr))
ISLER = [
    (590, 2.2, "claude", "polycrew:sanatci", "", ("Review the free color ramp", "Serbest rampayı incele"),
     0, None, 5, ("measured every material, found the pale skin", "her malzemeyi ölçtü, soluk teni buldu")),
    (585, 1.0, "agy", "gemini-3.1-pro-high", "okur", ("Review the ramp branch", "Rampa dalını gözden geçir"),
     1, 50_000, None, None),
    (560, 2.1, "agy", "gemini-3.1-pro-high", "okur", ("Review the ramp branch", "Rampa dalını gözden geçir"),
     0, 43_000, 3, ("two real findings, one false alarm", "iki gerçek bulgu, bir yanlış alarm")),
    (520, 18.0, "codex", "gpt-6.1-sol", "yazar", ("Tone count and light direction", "Ton sayısı ve ışık yönü"),
     0, 3_660_000, 4, ("clean code, stopped at the file limit", "temiz kod, dosya sınırında durdu")),
    (500, 20.0, "claude", "polycrew:gelistirici", "", ("Finish the inner lines", "İç çizgileri bitir"),
     0, None, 4, ("fixed the rule in four languages", "kuralı dört dilde düzeltti")),
    (470, 6.5, "claude", "polycrew:sanatci", "", ("Review the inner lines", "İç çizgileri incele"),
     0, None, 5, ("disproved the 85% claim by measuring", "%85 iddiasını ölçerek çürüttü")),
    (440, 3.5, "codex", "gpt-6.1-sol", "okur", ("Review the inner lines branch", "İç çizgi dalını gözden geçir"),
     0, 577_000, 5, ("proved a null bug in two adapters", "iki bağdaştırıcıda null hatasını kanıtladı")),
    (380, 19.5, "codex", "gpt-6.1-sol", "yazar", ("Outline styles", "Kontur biçimleri"),
     0, 4_210_000, 4, ("all done in one run", "hepsi tek koşuda bitti")),
    (60, 6.8, "codex", "gpt-6-astra", "okur", ("Review the outline styles", "Kontur dalını gözden geçir"),
     0, 977_000, 4, ("no bugs, but six times the cost", "hata yok ama altı kat pahalı")),
    (9, None, "claude", "polycrew:gelistirici", "", ("Lock frame count to the step rhythm", "Kare sayısını adım ritmine kilitle"),
     None, None, None, None),
    (3, None, "codex", "gpt-6.1-sol", "okur", ("Review the frame count branch", "Kare sayısı dalını gözden geçir"),
     None, None, None, None),
]


def main(dil: str, yol: str) -> None:
    k = 0 if dil == "en" else 1
    simdi = time.time()
    olaylar = []
    for n, (once, dk, kaynak, model, kip, is_, cikis, tok, puan, neden) in enumerate(ISLER):
        bas = simdi - once * 60
        kimlik = f"ornek-{n}"
        if kaynak == "claude":
            olaylar.append({"ts": bas, "tur": "agent_baslatildi", "id": kimlik, "kaynak": "claude",
                            "rol": model, "aciklama": is_[k], "istem": is_[k]})
            if dk is not None:
                olaylar.append({"ts": bas + dk * 60, "tur": "agent_bitti", "id": kimlik, "kaynak": "claude"})
        else:
            olaylar.append({"ts": bas, "tur": "isci_basladi", "id": kimlik, "kaynak": kaynak, "model": model,
                            "efor": "xhigh" if "astra" in model else "high", "kip": kip, "aciklama": is_[k]})
            if dk is not None:
                olaylar.append({"ts": bas + dk * 60, "tur": "isci_bitti", "id": kimlik, "kaynak": kaynak,
                                "cikis": cikis, "kullanim": {"total_tokens": tok}})
        if puan is not None:
            olaylar.append({"ts": bas + (dk or 0) * 60 + 30, "tur": "puan", "id": kimlik, "not": puan,
                            "gerekce": neden[k]})
    olaylar.append({"ts": simdi - 30, "tur": "kota", "kovalar": [
        {"saglayici": "codex", "grup": "Codex", "pencere": "5h", "kullanilan": 28, "yenilenir": "17:24"},
        {"saglayici": "codex", "grup": "Codex", "pencere": "week" if dil == "en" else "hafta",
         "kullanilan": 21, "yenilenir": "10-08 23:50"},
        {"saglayici": "agy", "grup": "Gemini Models", "pencere": "weekly", "kullanilan": 6, "yenilenir": "10-08 15:24"},
        {"saglayici": "agy", "grup": "Claude and GPT models", "pencere": "weekly", "kullanilan": 34,
         "yenilenir": "10-08 22:58"},
    ]})
    with open(yol, "w", encoding="utf-8") as f:
        for e in sorted(olaylar, key=lambda e: e["ts"]):
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
