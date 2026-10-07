#!/usr/bin/env python3
"""PM'in masaüstü aracından okuduğu Claude kotasını günlüğe aktar; argümansız son ölçümü göster."""

from __future__ import annotations

import argparse
import math
import sys
from datetime import datetime

import izle


def yuzde(metin: str) -> float:
    sayi = float(metin)
    if not math.isfinite(sayi) or not 0 <= sayi <= 100:
        raise argparse.ArgumentTypeError("yüzde 0–100 arasında olmalı")
    return sayi


def iso(metin: str) -> datetime:
    try:
        if "T" not in metin and " " not in metin:
            raise ValueError
        return datetime.fromisoformat(metin.replace("Z", "+00:00")).astimezone()
    except ValueError:
        raise argparse.ArgumentTypeError("yenilenme zamanı ISO tarih ve saat olmalı") from None


def token(metin: str) -> int:
    sayi = int(metin)
    if sayi < 0:
        raise argparse.ArgumentTypeError("token sayısı negatif olamaz")
    return sayi


def goster(kovalar: list[dict], simdi: float) -> None:
    if not kovalar:
        print("Claude: ölçüm yok (PM yazar)")
        return
    for k in kovalar:
        yas = max(0, int(simdi - k["olcum_ts"]))
        ek = f" · plan {k['plan']}" if k.get("plan") else ""
        if "token" in k:
            ek += f" · {k['token']} token"
        if k.get("yenilenir"):
            ek += f" · yenilenir {k['yenilenir']}"
        if k.get("eski"):
            ek += " · eski ölçüm"
        print(f"Claude {k['pencere']}: %{k['kullanilan']:g} · ölçüm {k['olcum']} · yaş {yas} sn{ek}")
    if any(k["kullanilan"] >= esik
           for k in kovalar for pencere, esik in (("hafta", 70), ("5 saat", 80))
           if k["pencere"] == pencere):
        print("Uyarı: Claude işlerini dış işçiye kaydır")


def main(argv: list[str]) -> int:
    if not argv:
        veri = izle.birlestir(izle.oku())
        kovalar = (veri["kota"] or {}).get("kovalar", [])
        goster([k for k in kovalar if k.get("saglayici") == "claude"], veri["simdi"])
        return 0
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bes-saat", type=yuzde, required=True)
    ap.add_argument("--bes-saat-yenilenir", type=iso, required=True)
    ap.add_argument("--hafta", type=yuzde, required=True)
    ap.add_argument("--hafta-yenilenir", type=iso, required=True)
    ap.add_argument("--plan")
    ap.add_argument("--baglam", type=yuzde)
    ap.add_argument("--baglam-token", type=token)
    args = ap.parse_args(argv)
    if args.baglam_token is not None and args.baglam is None:
        ap.error("--baglam-token için --baglam da verilmeli")
    simdi = datetime.now().astimezone()
    ortak = {"saglayici": "claude", "grup": "Claude", "olcum": simdi.isoformat()}
    if args.plan:
        ortak["plan"] = args.plan
    kovalar = [
        {**ortak, "pencere": "5 saat", "kullanilan": args.bes_saat,
         "yenilenir": args.bes_saat_yenilenir.strftime("%m-%d %H:%M")},
        {**ortak, "pencere": "hafta", "kullanilan": args.hafta,
         "yenilenir": args.hafta_yenilenir.strftime("%m-%d %H:%M")},
    ]
    if args.baglam is not None:
        k = {**ortak, "pencere": "bağlam", "kullanilan": args.baglam}
        if args.baglam_token is not None:
            k["token"] = args.baglam_token
        kovalar.append(k)
    izle.olay.yaz({"tur": "kota", "kaynak": "claude", "ts": simdi.timestamp(), "kovalar": kovalar})
    goster([izle.kota_kovasi(k, simdi.timestamp(), simdi.timestamp()) for k in kovalar], simdi.timestamp())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
