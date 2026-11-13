#!/usr/bin/env python3
"""Claude Code status line that records the Claude plan quota for polycrew (0018).

Claude Code passes a JSON object on stdin to the status line command. For Pro, Max and Ultra plans it
carries `rate_limits.five_hour` and `rate_limits.seven_day` (`used_percentage`, `resets_at` in Unix
seconds) once the session has had its first answer. This script writes them to the polycrew event log
as a `kota` event when they changed or every 10 minutes, so the watch page and roster.py see a fresh
Claude reading without the PM typing it in. It prints one short line.

Settings (~/.claude/settings.json), edited by the user:

    "statusLine": {"type": "command",
                   "command": "python3 <plugin>/skills/watch/claude-statusline.py"}

Already have a status line? Chain it: `claude-statusline.py --then "<your command>"` prints that
command's output instead of its own line (the same JSON goes to its stdin).

It writes only in projects that use the polycrew workflow (a notes file in the project folder or above),
like the hooks, and it never fails the status line: any error leaves the line empty or plain.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "hooks"))

YENIDEN = 600.0  # saniye: değişmeyen okuma da bu aralıkla yazılır
PENCERE = {"five_hour": "5 saat", "seven_day": "hafta"}


def kovalar(yuk: dict, simdi: float) -> list[dict]:
    """``rate_limits``'ten Claude kovaları; alan yoksa ya da bozuksa boş liste."""
    sinirlar = yuk.get("rate_limits") if isinstance(yuk, dict) else None
    if not isinstance(sinirlar, dict):
        return []
    olcum = datetime.fromtimestamp(simdi).astimezone().isoformat()
    sonuc = []
    for ad, pencere in PENCERE.items():
        b = sinirlar.get(ad)
        if not isinstance(b, dict):
            continue
        yuzde, an = b.get("used_percentage"), b.get("resets_at")
        if not isinstance(yuzde, (int, float)) or isinstance(yuzde, bool) or not 0 <= yuzde <= 100:
            continue
        kova = {"saglayici": "claude", "grup": "Claude", "pencere": pencere, "kullanilan": round(float(yuzde), 1),
                "olcum": olcum, "kaynak": "statusline"}
        if isinstance(an, (int, float)) and not isinstance(an, bool) and an > 0:
            kova["yenilenir_epoch"] = float(an)
            kova["yenilenir"] = datetime.fromtimestamp(an).strftime("%m-%d %H:%M")
        sonuc.append(kova)
    return sonuc


def satir(yuk: dict, kova_listesi: list[dict]) -> str:
    model = ((yuk.get("model") or {}).get("display_name") if isinstance(yuk, dict) else None) or "Claude"
    parcalar = [str(model)]
    for k in kova_listesi:
        parcalar.append(f"{'5h' if k['pencere'] == '5 saat' else 'week'} {k['kullanilan']:g}%")
    return " · ".join(parcalar)


def main(argv: list[str]) -> int:
    then = None
    if len(argv) >= 2 and argv[0] == "--then":
        then = argv[1]
    ham = sys.stdin.read()
    try:
        yuk = json.loads(ham) if ham.strip() else {}
    except ValueError:
        yuk = {}
    liste: list[dict] = []
    try:
        import time

        import events as olay
        import quota as kurallar

        liste = kovalar(yuk, time.time())
        dizin = (yuk.get("workspace") or {}).get("project_dir") or yuk.get("cwd") if isinstance(yuk, dict) else None
        if liste and olay.duzen_var({"cwd": dizin or os.getcwd()}):
            kurallar.kaydet(liste, yeniden=YENIDEN, kaynak="claude")
    except Exception:  # noqa: BLE001 - durum satırı hiçbir zaman bozulmaz
        pass
    if then:
        try:
            r = subprocess.run(then, shell=True, input=ham, capture_output=True, text=True, timeout=10)
            sys.stdout.write(r.stdout)
            return 0
        except Exception:  # noqa: BLE001
            return 0
    print(satir(yuk, liste) if isinstance(yuk, dict) else "Claude")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
