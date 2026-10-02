#!/usr/bin/env python3
"""polycrew olay günlüğü (karar 0003).

Tek dosya: ``${XDG_CACHE_HOME:-~/.cache}/polycrew/olaylar.jsonl`` (``POLYCREW_OLAYLAR`` ile
değişir), satır başına bir JSON olay. Yalnız standart kütüphane.

İki kullanım:

- **Kanca** (argümansız, stdin'de Claude Code'un kanca yükü): ``PreToolUse`` (Agent aracı),
  ``SubagentStart`` ve ``SubagentStop`` olaya çevrilir. Alan adları sürümle değişebildiği için
  kısaltılmış ham yük de saklanır. Kanca hiçbir zaman hata vermez ve çıktı yazmaz.
- **Komut:** ``olay.py yaz <tur> anahtar=değer ...`` (dış işçiler, ``dis-ajan.sh``) ve
  ``olay.py puan <id> <not> [gerekçe]`` (PM'in notu).
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


def yaz(olay: dict) -> None:
    olay = {"ts": round(time.time(), 3), **olay}
    yol = dosya()
    yol.parent.mkdir(parents=True, exist_ok=True)
    with open(yol, "a", encoding="utf-8") as f:
        f.write(json.dumps(olay, ensure_ascii=False) + "\n")


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
        yaz({"tur": "puan", "id": argv[1], "not": _deger(argv[2]), "gerekce": " ".join(argv[3:])})
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
