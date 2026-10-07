#!/usr/bin/env python3
"""polycrew olay günlüğü ve puan defteri (karar 0003).

İki dosya:
- Olay günlüğü: ``${XDG_CACHE_HOME:-~/.cache}/polycrew/olaylar.jsonl`` (``POLYCREW_OLAYLAR`` ile
  değişir), satır başına bir JSON olay.
- Puan defteri: ``${XDG_DATA_HOME:-~/.local/share}/polycrew/puanlar.jsonl`` (``POLYCREW_PUANLAR`` ile
  değişir), kalıcı notlar.

Kullanım:
- **Kanca** (argümansız, stdin'de Claude Code'un kanca yükü): PreToolUse, SubagentStart, SubagentStop.
- **Komut:**
  - ``olay.py yaz <tur> anahtar=değer ...``
  - ``olay.py puan <id> <not> [gerekçe] [--isci ...] [--rol ...] [--alan ...] [--zorluk ...] [--kota ...] [--sure ...] [--duzeltme ...] [--proje ...]``
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

KISA = 400  # karakter: ham yükteki uzun metinler (istem, son mesaj) bu kadar kalır


def dosya() -> Path:
    yol = os.environ.get("POLYCREW_OLAYLAR")
    if yol:
        return Path(yol)
    kok = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return Path(kok) / "polycrew" / "olaylar.jsonl"


def defter_dosyasi() -> Path:
    yol = os.environ.get("POLYCREW_PUANLAR")
    if yol:
        return Path(yol)
    kok = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return Path(kok) / "polycrew" / "puanlar.jsonl"


def yaz(olay: dict) -> dict:
    if "ts" not in olay:
        olay = {"ts": round(time.time(), 3), **olay}
    yol = dosya()
    yol.parent.mkdir(parents=True, exist_ok=True)
    with open(yol, "a", encoding="utf-8") as f:
        f.write(json.dumps(olay, ensure_ascii=False) + "\n")
    return olay


def defter_yaz(kayit: dict) -> None:
    yol = defter_dosyasi()
    yol.parent.mkdir(parents=True, exist_ok=True)
    with open(yol, "a", encoding="utf-8") as f:
        f.write(json.dumps(kayit, ensure_ascii=False) + "\n")


def _kisa(deger):
    if isinstance(deger, str):
        return deger if len(deger) <= KISA else deger[:KISA] + "…"
    if isinstance(deger, dict):
        return {k: _kisa(v) for k, v in deger.items()}
    if isinstance(deger, list):
        return [_kisa(v) for v in deger[:20]]
    return deger


def kancadan(yuk: dict) -> dict | None:
    """Claude Code kanca yükünden olay; ilgisiz yükte None."""
    ad = yuk.get("hook_event_name", "")
    ortak = {"oturum": yuk.get("session_id"), "kaynak": "claude", "cwd": yuk.get("cwd")}
    if ad == "PreToolUse":
        if yuk.get("tool_name") not in ("Agent", "Task"):
            return None
        girdi = yuk.get("tool_input") or {}
        return {
            **ortak,
            "tur": "agent_baslatildi",
            "id": yuk.get("tool_use_id"),
            "rol": girdi.get("subagent_type") or "general-purpose",
            "model": girdi.get("model"),
            "aciklama": girdi.get("description"),
            "arka_plan": girdi.get("run_in_background", True),
            "yalitim": girdi.get("isolation"),
            "istem": _kisa(girdi.get("prompt")),
            "ham": _kisa({k: v for k, v in yuk.items() if k != "hook_event_name"}),
        }
    if ad in ("SubagentStart", "SubagentStop"):
        return {
            **ortak,
            "tur": "agent_basladi" if ad == "SubagentStart" else "agent_bitti",
            "id": yuk.get("agent_id"),
            "rol": yuk.get("agent_type"),
            "transkript": yuk.get("agent_transcript_path"),
            "ham": _kisa({k: v for k, v in yuk.items() if k != "hook_event_name"}),
        }
    return None


def _deger(metin: str):
    try:
        return json.loads(metin)
    except ValueError:
        return metin


def _sayi(val):
    if isinstance(val, (int, float)):
        return val
    s = str(val).replace("%", "").strip()
    try:
        f = float(s)
        return int(f) if f.is_integer() else f
    except ValueError:
        return val


def _sayi_veya_deger(metin: str):
    if isinstance(metin, (int, float)):
        return metin
    s = metin.strip().strip("*")
    if "/" in s:
        sol, _, _ = s.partition("/")
        try:
            return _sayi(sol)
        except Exception:
            pass
    return _deger(s)


def puan_ayristir(argv: list[str]) -> tuple[dict, bool]:
    """puan argümanlarını ayrıştırır.

    Dönüş: (olay_sozlugu, deftere_yazilsin_mi)
    """
    bayraklar = {}
    pozisyonel = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg.startswith("--"):
            anahtar = arg[2:]
            if "=" in anahtar:
                k, _, v = anahtar.partition("=")
                bayraklar[k] = v
                i += 1
            elif i + 1 < len(argv):
                bayraklar[anahtar] = argv[i + 1]
                i += 2
            else:
                bayraklar[anahtar] = ""
                i += 1
        else:
            pozisyonel.append(arg)
            i += 1

    if len(pozisyonel) < 2:
        return {}, False

    is_id = pozisyonel[0]
    not_degeri = _sayi_veya_deger(pozisyonel[1])
    gerekce = " ".join(pozisyonel[2:]) if len(pozisyonel) > 2 else ""

    olay = {
        "tur": "puan",
        "id": is_id,
        "not": not_degeri,
        "gerekce": gerekce,
    }

    # Bayrakları ekle
    for k, v in bayraklar.items():
        if k in ("kota", "sure", "duzeltme"):
            olay[k] = _sayi(v)
        else:
            olay[k] = v

    deftere_yazilsin = "isci" in bayraklar and bool(bayraklar["isci"])
    if deftere_yazilsin and "proje" not in olay:
        olay["proje"] = Path.cwd().name

    return olay, deftere_yazilsin


def puan_isle(argv: list[str]) -> int:
    olay, deftere_yaz = puan_ayristir(argv)
    if not olay:
        print("Kullanım: olay.py puan <id> <not> [gerekçe] [--isci ...] ...", file=sys.stderr)
        return 2
    olay_kaydi = yaz(olay)
    if deftere_yaz:
        defter_yaz(olay_kaydi)
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        try:
            olay = kancadan(json.load(sys.stdin))
            if olay:
                yaz(olay)
        except Exception:  # noqa: BLE001 - bir kanca oturumu asla durdurmaz
            pass
        return 0
    if argv[0] == "yaz" and len(argv) >= 2:
        olay = {"tur": argv[1]}
        for parca in argv[2:]:
            anahtar, _, deger = parca.partition("=")
            olay[anahtar] = _deger(deger)
        yaz(olay)
        return 0
    if argv[0] == "puan" and len(argv) >= 3:
        return puan_isle(argv[1:])
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
