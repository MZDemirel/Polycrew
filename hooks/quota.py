#!/usr/bin/env python3
"""polycrew kota kuralları: tek kaynak (0018).

``watch.py``, ``roster.py``, ``doctor.py``, ``claude-quota.py``, ``claude-statusline.py`` ve
``external-agent.sh`` aynı kuralları buradan alır:

- eski grup ve pencere adları (agy'nin ham adları) → günlükteki ad;
- işçi → kota kovası (Codex, agy grubu, Claude'un genel ve model başına haftalık kovası);
- sıfırlanma zamanı (önce ``yenilenir_epoch``; eski olaylarda kısaltılmış metin: agy UTC, öbürleri yerel);
- tazelik: sıfırlanma geçtiyse ya da okuma penceresinden eskiyse (5 saatte 5 saat, haftada 1 gün) eski;
- yazım: içeriği değişmeyen okuma yeniden yazılmaz (günlüğün çoğu tekrar eden kota olayıydı).

Komut:
  quota.py record <kovalar.json> [...]   dosyalardaki kovaları tek ``kota`` olayı olarak yazar,
                                         değişmediyse yazmaz (external-agent.sh quota)
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import events as olay  # noqa: E402

# external-agent.sh'nin eski sürümü agy'nin ham adlarını yazıyordu; aynı kova.
ESKI_GRUP = {"Gemini Models": "agy: Gemini", "Claude and GPT models": "agy: Claude/GPT",
             "Gemini 4 Argon": "agy: Argon"}
ESKI_PENCERE = {"weekly": "hafta", "5h": "5 saat"}
SINIR = {"5 saat": 5 * 3600.0, "hafta": 24 * 3600.0}  # saniye: okuma bunca eskiyse "eski"
SINIR_AD = {"5 saat": "5 hours", "hafta": "a day"}
YENIDEN = 30 * 60.0  # saniye: değişmeyen okuma da bu aralıkla yazılır (yaşı tazelensin)


def zaman(deger) -> float | None:
    """ISO zamanı ya da Unix saniyesi → Unix saniyesi; çözülemezse ya da sonlu değilse None."""
    try:
        if isinstance(deger, bool):
            return None
        if isinstance(deger, (int, float)):
            sayi = float(deger)
        else:
            sayi = datetime.fromisoformat(deger.replace("Z", "+00:00")).timestamp()
        return sayi if math.isfinite(sayi) else None
    except (ValueError, TypeError, AttributeError, OverflowError):
        return None


def adlari_duzelt(kova: dict) -> dict:
    """Eski grup ve pencere adlarını bugünkü adlara çevirir (kopya döner)."""
    return {**kova, "grup": ESKI_GRUP.get(kova.get("grup"), kova.get("grup")),
            "pencere": ESKI_PENCERE.get(kova.get("pencere"), kova.get("pencere"))}


def yenilenme(kova: dict, olcum: float) -> float | None:
    """Kovanın sıfırlanma zamanı: yeni olaylarda ``yenilenir_epoch``; eskilerde kısaltılmış metinden.

    Eski metin ``11-12 16:07`` (Codex ve Claude, yerel saat) ya da ``11-12T16:07`` (agy, UTC) biçimindedir;
    yıl ölçümden gelir, yıl dönümünde sıfırlanma ertesi yıla düşer.
    """
    epoch = kova.get("yenilenir_epoch")
    if isinstance(epoch, (int, float)) and not isinstance(epoch, bool) and math.isfinite(epoch) and epoch > 0:
        return float(epoch)
    metin = kova.get("yenilenir")
    if not metin or metin == "?":
        return None
    try:
        # 0018 öncesi agy metni UTC'ydi ve "T" taşıyordu; 0018'den sonra agy de yerel ve epoch'lu yazar.
        utc = kova.get("saglayici") == "agy" and "T" in str(metin)
        yil = (datetime.fromtimestamp(olcum, tz=timezone.utc) if utc else datetime.fromtimestamp(olcum)).year
        for ek in (0, 1):
            gun = datetime.strptime(f"{yil + ek}-{str(metin).replace('T', ' ')}", "%Y-%m-%d %H:%M")
            if utc:
                gun = gun.replace(tzinfo=timezone.utc)
            if gun.timestamp() >= olcum - 86400:
                return gun.timestamp()
    except (ValueError, TypeError, OverflowError, OSError):
        pass
    return None


def eski_neden(pencere: str, olcum: float, yenilenir: float | None, simdi: float) -> str | None:
    """Okuma eskiyse nedeni (İngilizce, ekranda görünür); tazeyse None.

    Sıfırlanma anı geçtiyse okuma eski pencereye aittir; ölçümden önce geçmiş olsa da (Codex'in son kaydı
    eski pencereden kalabilir, 0017). Geçmediyse yaşına bakılır:
    5 saatlik pencerede 5 saat, haftalıkta bir gün (0018: 4 günlük Claude okuması taze görünüyordu).
    """
    if yenilenir is not None and yenilenir <= simdi:
        return "reset passed"
    sinir = SINIR.get(pencere, SINIR["5 saat"])
    if simdi - olcum > sinir:
        return f"older than {SINIR_AD.get(pencere, '5 hours')}"
    return None


def agy_grubu(model: str, gruplar=None) -> str:
    """agy modelinin kota grubu. Argon'un kendi haftalık kovası var; okumada yoksa Gemini'ye sayılır."""
    model = (model or "").lower()
    if "claude" in model or "gpt" in model:
        return "agy: Claude/GPT"
    if "argon" in model and (gruplar is None or "agy: Argon" in gruplar):
        return "agy: Argon"
    return "agy: Gemini"


def isci_kovasi_mi(isci: str, saglayici, grup, gruplar=None) -> bool:
    """Bu kova bu işçinin kotası mı? ``gruplar``: okumadaki agy grupları (Argon'un yedeğine karar verir).

    Claude işçisi (``claude/<rol>/<model>``) genel ``Claude`` kovasını ve adı modelinde geçen
    ``Claude: <ad>`` kovasını sayar (model başına haftalık sınır).
    """
    parcalar = str(isci or "").split("/")
    arac = parcalar[0]
    if arac != saglayici:
        return False
    if arac == "codex":
        return grup == "Codex"
    if arac == "agy":
        return grup == agy_grubu(parcalar[1] if len(parcalar) > 1 else "", gruplar)
    if arac == "claude":
        if grup == "Claude":
            return True
        model = (parcalar[-1] if len(parcalar) > 2 else "").lower()
        return isinstance(grup, str) and grup.startswith("Claude: ") and bool(model) \
            and grup[len("Claude: "):].strip().lower() in model
    return False


def tanimli(isci: str) -> bool:
    return str(isci or "").split("/")[0] in ("codex", "agy", "claude")


# --- yazım ---

def durum_dosyasi() -> Path:
    """Son yazılan okumaların özeti: olay günlüğünün yanında (POLYCREW_EVENTS'i izler)."""
    yol = olay.dosya()
    return yol.with_name(f"{yol.stem}-son-kota.json")


def _imza(kova: dict) -> str:
    # Sıfırlanma zamanı imzaya girmez: kullanılmayan agy penceresinin sıfırlanması her okumada "şimdi + 5
    # saat"tir, kayar. Yeni pencere zaten kullanımı da değiştirir; değişmezse YENIDEN aralığı tazeler.
    atla = {"yenilenir", "yenilenir_epoch"} | (set() if kova.get("saglayici") == "codex" else {"olcum"})
    return json.dumps({k: v for k, v in kova.items() if k not in atla}, sort_keys=True, ensure_ascii=False)


def kaydet(kovalar: list[dict], yeniden: float = YENIDEN, simdi: float | None = None, **ek) -> bool:
    """Kovaları tek ``kota`` olayı olarak yazar; hepsi son yazımla aynıysa ve ``yeniden`` saniye
    dolmadıysa yazmaz. Codex'in ölçüm zamanı imzaya girer (yeni kayıt = yeni ölçüm); agy ve Claude'unki
    girmez, onlar ``yeniden`` aralığıyla tazelenir. Yazdıysa True."""
    simdi = time.time() if simdi is None else simdi
    kovalar = [k for k in kovalar if isinstance(k, dict)]
    if not kovalar:
        return False
    yol = durum_dosyasi()
    try:
        durum = json.loads(yol.read_text(encoding="utf-8"))
        if not isinstance(durum, dict):
            durum = {}
    except (OSError, ValueError):
        durum = {}
    anahtar = lambda k: "|".join(str(k.get(a)) for a in ("saglayici", "grup", "pencere"))  # noqa: E731
    degisti = False
    for k in kovalar:
        once = durum.get(anahtar(k))
        if not isinstance(once, dict) or once.get("imza") != _imza(k) \
                or not isinstance(once.get("ts"), (int, float)) or not 0 <= simdi - once["ts"] < yeniden:
            degisti = True
            break
    if not degisti:
        return False
    olay.yaz({"ts": round(simdi, 3), "tur": "kota", **ek, "kovalar": kovalar})
    for k in kovalar:
        durum[anahtar(k)] = {"imza": _imza(k), "ts": simdi}
    try:
        gecici = yol.with_name(yol.name + f".{os.getpid()}")
        gecici.write_text(json.dumps(durum, ensure_ascii=False), encoding="utf-8")
        os.replace(gecici, yol)
    except OSError:
        pass
    return True


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "record":
        kovalar = []
        for f in argv[1:]:
            try:
                veri = json.load(open(f, encoding="utf-8"))
            except (OSError, ValueError):
                continue
            kovalar += [k for k in veri if isinstance(k, dict)] if isinstance(veri, list) else []
        kaydet(kovalar)
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
