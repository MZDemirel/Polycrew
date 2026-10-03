#!/usr/bin/env python3
"""polycrew dinamik kadro ve puan öneri aracı.

Kullanım:
  kadro.py oneri [--rol R] [--alan A] [--zorluk Z] [--tohumsuz]
  kadro.py ekle <id> <not> [gerekçe] [--isci ...] [--rol ...] ...
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import sys
from pathlib import Path

# hooks modülünü içe aktarabilmek için ekle
KOK = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(KOK / "hooks"))
import olay  # noqa: E402


def tohum_dosyasi() -> Path:
    return KOK / "deney" / "puanlar-tohum.jsonl"


def kayitlari_oku(tohumsuz: bool = False) -> list[dict]:
    kayitlar = []

    # 1. Tohum verisi
    if not tohumsuz:
        t_yol = tohum_dosyasi()
        if t_yol.exists():
            with open(t_yol, "r", encoding="utf-8") as f:
                for satir in f:
                    satir = satir.strip()
                    if not satir:
                        continue
                    try:
                        k = json.loads(satir)
                        if isinstance(k, dict) and "isci" in k and "not" in k:
                            kayitlar.append(k)
                    except Exception:
                        continue

    # 2. Kalıcı defter verisi
    d_yol = olay.defter_dosyasi()
    if d_yol.exists():
        with open(d_yol, "r", encoding="utf-8") as f:
            for satir in f:
                satir = satir.strip()
                if not satir:
                    continue
                try:
                    k = json.loads(satir)
                    if isinstance(k, dict) and "isci" in k and "not" in k:
                        kayitlar.append(k)
                except Exception:
                    continue

    return kayitlar


def duzeltilmis_puan(notlar: list[float], onsel: float = 3.5, k: float = 2.0) -> float:
    if not notlar:
        return onsel
    return (onsel * k + sum(notlar)) / (k + len(notlar))


def kayit_filtrele(kayit: dict, rol: str | None, alan: str | None, zorluk: str | None) -> bool:
    if rol is not None and kayit.get("rol") != rol:
        return False
    if alan is not None and kayit.get("alan") != alan:
        return False
    if zorluk is not None and kayit.get("zorluk") != zorluk:
        return False
    return True


def isci_istatistik(kayitlar: list[dict]) -> list[dict]:
    gruplar: dict[str, dict] = {}
    for k in kayitlar:
        isci = k.get("isci")
        if not isci:
            continue
        if isci not in gruplar:
            gruplar[isci] = {
                "notlar": [],
                "kotalar": [],
                "sureler": [],
                "ts_ler": [],
            }
        try:
            n_val = float(k["not"])
            gruplar[isci]["notlar"].append(n_val)
        except (ValueError, TypeError):
            continue

        kota = k.get("kota")
        if kota is not None:
            try:
                gruplar[isci]["kotalar"].append(float(kota))
            except (ValueError, TypeError):
                pass

        sure = k.get("sure")
        if sure is not None:
            try:
                gruplar[isci]["sureler"].append(float(sure))
            except (ValueError, TypeError):
                pass

        ts = k.get("ts")
        if ts is not None:
            try:
                gruplar[isci]["ts_ler"].append(float(ts))
            except (ValueError, TypeError):
                pass

    sonuclar = []
    for isci, veri in gruplar.items():
        notlar = veri["notlar"]
        if not notlar:
            continue
        n = len(notlar)
        ort = sum(notlar) / n
        dp = duzeltilmis_puan(notlar)
        ort_kota = sum(veri["kotalar"]) / len(veri["kotalar"]) if veri["kotalar"] else None
        ort_sure = sum(veri["sureler"]) / len(veri["sureler"]) if veri["sureler"] else None
        son_ts = max(veri["ts_ler"]) if veri["ts_ler"] else None

        sonuclar.append({
            "isci": isci,
            "n": n,
            "ortalama": ort,
            "duzeltilmis": dp,
            "ort_kota": ort_kota,
            "ort_sure": ort_sure,
            "son_ts": son_ts,
            "durum": "veri az" if n < 3 else "",
        })

    sonuclar.sort(key=lambda x: (x["duzeltilmis"], x["n"], x["ortalama"]), reverse=True)
    return sonuclar


def format_ts(ts: float | None) -> str:
    if ts is None:
        return "—"
    try:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return str(ts)


def format_kota(kota: float | None) -> str:
    if kota is None:
        return "—"
    if kota.is_integer():
        return f"%{int(kota)}"
    return f"%{kota:.1f}".replace(".", ",")


def format_sure(sure: float | None) -> str:
    if sure is None:
        return "—"
    return f"{int(round(sure))} sn"


def format_sayi(val: float, basamak: int = 1) -> str:
    s = f"{val:.{basamak}f}"
    return s.replace(".", ",")


def tablo_olustur_filtreli(istatistikler: list[dict]) -> str:
    satirlar = [
        "| İşçi | n | Ortalama | Düzeltilmiş Puan | Ort. Kota | Ort. Süre | Son Not Tarihi | Durum |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i in istatistikler:
        satirlar.append(
            f"| {i['isci']} | {i['n']} | {format_sayi(i['ortalama'], 1)} | "
            f"{format_sayi(i['duzeltilmis'], 2)} | {format_kota(i['ort_kota'])} | "
            f"{format_sure(i['ort_sure'])} | {format_ts(i['son_ts'])} | {i['durum']} |"
        )
    return "\n".join(satirlar)


def tablo_olustur_filtresiz(kayitlar: list[dict]) -> str:
    gruplar: dict[tuple[str, str], list[dict]] = {}
    for k in kayitlar:
        rol = k.get("rol") or "—"
        alan = k.get("alan") or "—"
        anahtar = (rol, alan)
        if anahtar not in gruplar:
            gruplar[anahtar] = []
        gruplar[anahtar].append(k)

    grup_listesi = []
    for (rol, alan), grup_kayitlari in gruplar.items():
        istatistikler = isci_istatistik(grup_kayitlari)
        if istatistikler:
            en_iyi = istatistikler[0]
            grup_listesi.append((rol, alan, en_iyi))

    if not grup_listesi:
        return "Puan kaydı bulunamadı."

    grup_listesi.sort(key=lambda x: (x[0], x[1]))

    satirlar = [
        "| Rol | Alan | En İyi İşçi | Düzeltilmiş Puan | n | Ortalama | Ort. Kota | Ort. Süre | Son Not Tarihi | Durum |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for rol, alan, i in grup_listesi:
        satirlar.append(
            f"| {rol} | {alan} | {i['isci']} | {format_sayi(i['duzeltilmis'], 2)} | "
            f"{i['n']} | {format_sayi(i['ortalama'], 1)} | {format_kota(i['ort_kota'])} | "
            f"{format_sure(i['ort_sure'])} | {format_ts(i['son_ts'])} | {i['durum']} |"
        )
    return "\n".join(satirlar)


def cmd_oneri(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="kadro.py oneri", description="Kadro önerisi tablosu")
    parser.add_argument("--rol", type=str, default=None, help="Rol filtresi")
    parser.add_argument("--alan", type=str, default=None, help="Alan filtresi")
    parser.add_argument("--zorluk", type=str, default=None, help="Zorluk filtresi (K, O, Z)")
    parser.add_argument("--tohumsuz", action="store_true", help="Tohum verisini dahil etme")
    args = parser.parse_args(argv)

    kayitlar = kayitlari_oku(tohumsuz=args.tohumsuz)
    if not kayitlar:
        print("Puan kaydı bulunamadı.")
        return 0

    filtre_var = any([args.rol is not None, args.alan is not None, args.zorluk is not None])
    if filtre_var:
        uygun_kayitlar = [k for k in kayitlar if kayit_filtrele(k, args.rol, args.alan, args.zorluk)]
        if not uygun_kayitlar:
            print("Filtreye uyan puan kaydı bulunamadı.")
            return 0
        istatistikler = isci_istatistik(uygun_kayitlar)
        print(tablo_olustur_filtreli(istatistikler))
        return 0
    else:
        print(tablo_olustur_filtresiz(kayitlar))
        return 0


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2

    cmd = argv[0]
    if cmd == "oneri":
        return cmd_oneri(argv[1:])
    if cmd in ("ekle", "puan"):
        return olay.puan_isle(argv[1:])

    print(f"Bilinmeyen komut: {cmd}\n{__doc__}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
