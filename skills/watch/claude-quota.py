#!/usr/bin/env python3
"""Write the Claude quota the PM read from the desktop app's usage tool (or /usage) to the event log;
without arguments show the last reading.

--model-week NAME PCT RESETS records a per-model weekly limit ("Weekly · Fable"); a Claude worker whose
model name contains NAME counts it (0018). Reset times must lie ahead, within the window's length.
"""

from __future__ import annotations

import argparse
import math
import sys
from datetime import datetime

import watch as izle


def yuzde(metin: str) -> float:
    try:
        sayi = float(metin)
    except ValueError:
        raise argparse.ArgumentTypeError("percentage must be a number") from None
    if not math.isfinite(sayi) or not 0 <= sayi <= 100:
        raise argparse.ArgumentTypeError("percentage must be between 0 and 100")
    return sayi


def iso(metin: str) -> datetime:
    try:
        if "T" not in metin and " " not in metin:
            raise ValueError
        return datetime.fromisoformat(metin.replace("Z", "+00:00")).astimezone()
    except ValueError:
        raise argparse.ArgumentTypeError("reset time must be an ISO date and time") from None


def token(metin: str) -> int:
    sayi = int(metin)
    if sayi < 0:
        raise argparse.ArgumentTypeError("token count cannot be negative")
    return sayi


# Günlükteki pencere adları Türkçe kalır (şema, 0007); ekrana İngilizce yazılır.
ETIKET = {"5 saat": "5 hours", "hafta": "week", "bağlam": "context"}


def goster(kovalar: list[dict], simdi: float) -> None:
    if not kovalar:
        print("Claude: no reading yet (the PM records it)")
        return
    for k in kovalar:
        yas = max(0, int(simdi - k["olcum_ts"]))
        ek = f" · plan {k['plan']}" if k.get("plan") else ""
        if "token" in k:
            ek += f" · {k['token']} token"
        if k.get("yenilenir"):
            ek += f" · resets {k['yenilenir']}"
        if k.get("eski"):
            ek += f" · stale reading ({k.get('eski_neden')})" if k.get("eski_neden") else " · stale reading"
        ad = ETIKET.get(k["pencere"], k["pencere"])
        if k.get("grup", "Claude") != "Claude":
            ad = f"{ad} ({k['grup'].split(': ', 1)[-1]})"
        print(f"Claude {ad}: {k['kullanilan']:g}% · measured {k['olcum']} · age {yas} s{ek}")
    if any(k["kullanilan"] >= esik and not k.get("eski")
           for k in kovalar for pencere, esik in (("hafta", 70), ("5 saat", 80))
           if k["pencere"] == pencere):
        print("Warning: shift Claude's jobs to external workers")


def main(argv: list[str]) -> int:
    if not argv:
        izle.kurallar.masaustu_kaydet()  # 0019: masaüstü uygulamasının son okuması (varsa, değiştiyse)
        veri = izle.birlestir(izle.oku())
        kovalar = (veri["kota"] or {}).get("kovalar", [])
        goster([k for k in kovalar if k.get("saglayici") == "claude"], veri["simdi"])
        return 0
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--five-hour", dest="bes_saat", type=yuzde, required=True)
    ap.add_argument("--five-hour-resets", dest="bes_saat_yenilenir", type=iso, required=True)
    ap.add_argument("--week", dest="hafta", type=yuzde, required=True)
    ap.add_argument("--week-resets", dest="hafta_yenilenir", type=iso, required=True)
    ap.add_argument("--plan")
    ap.add_argument("--context", dest="baglam", type=yuzde)
    ap.add_argument("--context-tokens", dest="baglam_token", type=token)
    ap.add_argument("--model-week", dest="model_hafta", nargs=3, action="append", default=[],
                    metavar=("NAME", "PCT", "RESETS"), help="per-model weekly limit, e.g. Fable 23 2026-11-13T18:00Z")
    args = ap.parse_args(argv)
    if args.baglam_token is not None and args.baglam is None:
        ap.error("--context-tokens also needs --context")
    simdi = datetime.now().astimezone()
    # 0018: sıfırlanma ileride ve pencerenin boyunu aşmayacak kadar yakın olmalı (yanlış alan yazılmasın).
    PAY = 5 * 60

    def sifirlanma(an: datetime, saniye: float, bayrak: str) -> datetime:
        fark = an.timestamp() - simdi.timestamp()
        if not 0 < fark <= saniye + PAY:
            ap.error(f"{bayrak} must be in the future and within the window's length")
        return an

    sifirlanma(args.bes_saat_yenilenir, 5 * 3600, "--five-hour-resets")
    sifirlanma(args.hafta_yenilenir, 7 * 86400, "--week-resets")
    model_haftalari = []
    for ad, yuzde_metni, an_metni in args.model_hafta:
        try:
            deger, an = yuzde(yuzde_metni), iso(an_metni)
        except argparse.ArgumentTypeError as hata:
            ap.error(f"--model-week {ad}: {hata}")
        if not ad.strip() or ":" in ad:
            ap.error("--model-week NAME must be a model name such as Fable")
        model_haftalari.append((ad.strip(), deger, sifirlanma(an, 7 * 86400, "--model-week RESETS")))
    ortak = {"saglayici": "claude", "grup": "Claude", "olcum": simdi.isoformat()}
    if args.plan:
        ortak["plan"] = args.plan
    def kova(pencere, deger, an, grup="Claude"):
        return {**ortak, "grup": grup, "pencere": pencere, "kullanilan": deger,
                "yenilenir": an.strftime("%m-%d %H:%M"), "yenilenir_epoch": an.timestamp()}

    kovalar = [kova("5 saat", args.bes_saat, args.bes_saat_yenilenir),
               kova("hafta", args.hafta, args.hafta_yenilenir)]
    kovalar += [kova("hafta", deger, an, f"Claude: {ad}") for ad, deger, an in model_haftalari]
    if args.baglam is not None:
        k = {**ortak, "pencere": "bağlam", "kullanilan": args.baglam}
        if args.baglam_token is not None:
            k["token"] = args.baglam_token
        kovalar.append(k)
    # 0019: ortak yazıcıdan (her zaman yazar): sıfırlanma anı durum dosyasına da girer, masaüstü okuması onu taşır.
    izle.kurallar.kaydet(kovalar, yeniden=0, simdi=simdi.timestamp(), kaynak="claude")
    goster([izle.kota_kovasi(k, simdi.timestamp(), simdi.timestamp()) for k in kovalar], simdi.timestamp())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
