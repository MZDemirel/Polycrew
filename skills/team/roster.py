#!/usr/bin/env python3
"""polycrew dynamic roster: worker suggestions from the score ledger.

Usage:
  roster.py suggest [--role R] [--field F] [--difficulty E|M|H] [--half-life DAYS] [--no-seed]
  roster.py summary [--days N] [--half-life DAYS] [--no-seed] [--now TS]

Scores fade with age (0008): a score one half-life old (default 30 days) counts half, so an old
impression drifts back to the prior (3.5) instead of being remembered forever. --half-life 0 turns
fading off.
  roster.py add <id> <1-5> [reason] [--worker ...] [--role ...] ...

Records written before 0.5.0 (Turkish role, field and difficulty values) are mapped to the new
names when read; the files themselves are not changed.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import sys
import time
from pathlib import Path

# hooks modülünü içe aktarabilmek için ekle
KOK = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(KOK / "hooks"))
import events as olay  # noqa: E402


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
                            kayitlar.append(olay.kayit_adlari(k))
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
                        kayitlar.append(olay.kayit_adlari(k))
                except Exception:
                    continue

    return kayitlar


YARI_OMUR = 30.0  # gün: bu yaştaki puan yarım sayar (0008)
AZ_VERI = 3.0  # etkin n bunun altındaysa "little data"


def agirlik(ts, simdi: float | None, yari_omur: float) -> float:
    """Bir puanın yaşına göre ağırlığı; ``ts`` yoksa ya da soldurma kapalıysa 1."""
    if not yari_omur or yari_omur <= 0 or simdi is None:
        return 1.0
    try:
        yas_gun = max(0.0, (simdi - float(ts)) / 86400.0)
    except (ValueError, TypeError):
        return 1.0
    return 0.5 ** (yas_gun / yari_omur)


def duzeltilmis_puan(notlar: list[float], onsel: float = 3.5, k: float = 2.0,
                     agirliklar: list[float] | None = None) -> float:
    if not notlar:
        return onsel
    if agirliklar is None:
        agirliklar = [1.0] * len(notlar)
    return (onsel * k + sum(a * n for a, n in zip(agirliklar, notlar))) / (k + sum(agirliklar))


def kayit_filtrele(kayit: dict, rol: str | None, alan: str | None, zorluk: str | None) -> bool:
    if rol is not None and kayit.get("rol") != rol:
        return False
    if alan is not None and kayit.get("alan") != alan:
        return False
    if zorluk is not None and kayit.get("zorluk") != zorluk:
        return False
    return True


def isci_istatistik(kayitlar: list[dict], simdi: float | None = None,
                    yari_omur: float = YARI_OMUR) -> list[dict]:
    gruplar: dict[str, dict] = {}
    for k in kayitlar:
        isci = k.get("isci")
        if not isci:
            continue
        if isci not in gruplar:
            gruplar[isci] = {
                "notlar": [],
                "agirliklar": [],
                "kotalar": [],
                "sureler": [],
                "ts_ler": [],
            }
        try:
            n_val = float(k["not"])
        except (ValueError, TypeError, KeyError):
            continue
        gruplar[isci]["notlar"].append(n_val)
        gruplar[isci]["agirliklar"].append(agirlik(k.get("ts"), simdi, yari_omur))

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
        etkin = sum(veri["agirliklar"])
        dp = duzeltilmis_puan(notlar, agirliklar=veri["agirliklar"])
        ort_kota = sum(veri["kotalar"]) / len(veri["kotalar"]) if veri["kotalar"] else None
        ort_sure = sum(veri["sureler"]) / len(veri["sureler"]) if veri["sureler"] else None
        son_ts = max(veri["ts_ler"]) if veri["ts_ler"] else None

        sonuclar.append({
            "isci": isci,
            "n": n,
            "etkin": etkin,
            "ortalama": ort,
            "duzeltilmis": dp,
            "ort_kota": ort_kota,
            "ort_sure": ort_sure,
            "son_ts": son_ts,
            "durum": "little data" if etkin < AZ_VERI else "",
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
        return f"{int(kota)}%"
    return f"{kota:.1f}%"


def format_sure(sure: float | None) -> str:
    if sure is None:
        return "—"
    return f"{int(round(sure))} s"


def format_sayi(val: float, basamak: int = 1) -> str:
    return f"{val:.{basamak}f}"


def tablo_olustur_filtreli(istatistikler: list[dict]) -> str:
    satirlar = [
        "| Worker | n | Eff. n | Mean | Adjusted score | Avg quota | Avg duration | Last scored | Status |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for i in istatistikler:
        satirlar.append(
            f"| {i['isci']} | {i['n']} | {format_sayi(i['etkin'], 1)} | {format_sayi(i['ortalama'], 1)} | "
            f"{format_sayi(i['duzeltilmis'], 2)} | {format_kota(i['ort_kota'])} | "
            f"{format_sure(i['ort_sure'])} | {format_ts(i['son_ts'])} | {i['durum']} |"
        )
    return "\n".join(satirlar)


def tablo_olustur_filtresiz(kayitlar: list[dict], simdi: float | None = None,
                            yari_omur: float = YARI_OMUR) -> str:
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
        istatistikler = isci_istatistik(grup_kayitlari, simdi, yari_omur)
        if istatistikler:
            en_iyi = istatistikler[0]
            grup_listesi.append((rol, alan, en_iyi))

    if not grup_listesi:
        return "No score records found."

    grup_listesi.sort(key=lambda x: (x[0], x[1]))

    satirlar = [
        "| Role | Field | Best worker | Adjusted score | n | Eff. n | Mean | Avg quota | Avg duration | Last scored | Status |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for rol, alan, i in grup_listesi:
        satirlar.append(
            f"| {rol} | {alan} | {i['isci']} | {format_sayi(i['duzeltilmis'], 2)} | "
            f"{i['n']} | {format_sayi(i['etkin'], 1)} | {format_sayi(i['ortalama'], 1)} | {format_kota(i['ort_kota'])} | "
            f"{format_sure(i['ort_sure'])} | {format_ts(i['son_ts'])} | {i['durum']} |"
        )
    return "\n".join(satirlar)


def cmd_oneri(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="roster.py suggest", description="Roster suggestion table")
    parser.add_argument("--role", dest="rol", type=str, default=None, help="role filter")
    parser.add_argument("--field", dest="alan", type=str, default=None, help="field filter")
    parser.add_argument("--difficulty", dest="zorluk", type=str, default=None, help="difficulty filter (E, M, H)")
    parser.add_argument("--no-seed", dest="tohumsuz", action="store_true", help="leave out the seed data")
    parser.add_argument("--half-life", dest="yari_omur", type=float, default=YARI_OMUR,
                        help="days after which a score counts half (default: 30; 0 = no fading)")
    parser.add_argument("--now", dest="simdi", type=float, default=None, help="current time (epoch seconds, for tests)")
    args = parser.parse_args(argv)
    simdi = args.simdi if args.simdi is not None else time.time()

    # Eski adla verilen filtre de yeni ada çevrilir (0007).
    f = olay.kayit_adlari({"rol": args.rol, "alan": args.alan, "zorluk": args.zorluk})
    args.rol, args.alan, args.zorluk = f["rol"], f["alan"], f["zorluk"]
    kayitlar = kayitlari_oku(tohumsuz=args.tohumsuz)
    if not kayitlar:
        print("No score records found.")
        return 0

    filtre_var = any([args.rol is not None, args.alan is not None, args.zorluk is not None])
    if filtre_var:
        uygun_kayitlar = [k for k in kayitlar if kayit_filtrele(k, args.rol, args.alan, args.zorluk)]
        if not uygun_kayitlar:
            print("No score records match the filter.")
            return 0
        istatistikler = isci_istatistik(uygun_kayitlar, simdi, args.yari_omur)
        print(tablo_olustur_filtreli(istatistikler))
        return 0
    else:
        print(tablo_olustur_filtresiz(kayitlar, simdi, args.yari_omur))
        return 0


def kayit_pencerede_mi(kayit: dict, baslangic: float, simdi: float) -> bool:
    ts = kayit.get("ts")
    if ts is None:
        return False
    try:
        val = float(ts)
        return baslangic <= val <= simdi
    except (ValueError, TypeError):
        return False


def tablo_olustur_ozet(
    kayitlar: list[dict],
    gun: int = 7,
    simdi: float | None = None,
    yari_omur: float = YARI_OMUR,
) -> str:
    if not kayitlar:
        return "No records."

    if simdi is None:
        simdi = time.time()

    pencere_baslangic = simdi - (gun * 86400)
    pencere_kayitlari = [k for k in kayitlar if kayit_pencerede_mi(k, pencere_baslangic, simdi)]
    k_sayisi = len(pencere_kayitlari)

    tum_gruplar: dict[tuple[str, str], list[dict]] = {}
    for k in kayitlar:
        rol = k.get("rol") or "—"
        alan = k.get("alan") or "—"
        tum_gruplar.setdefault((rol, alan), []).append(k)

    pencere_gruplar: dict[tuple[str, str], list[dict]] = {}
    for k in pencere_kayitlari:
        rol = k.get("rol") or "—"
        alan = k.get("alan") or "—"
        pencere_gruplar.setdefault((rol, alan), []).append(k)

    sirali_ciftler = sorted(tum_gruplar.keys(), key=lambda x: (x[0], x[1]))

    # 0008: "dene" adayı aynı rolde görülmüş, bu rol + alanda az verisi olan ve rolün bütününde
    # önselin (3,5) altına düşmemiş işçidir. Kötü puan zamanla solar; işçi o zaman yeniden aday olur.
    rol_kayitlari: dict[str, list[dict]] = {}
    for k in kayitlar:
        rol_kayitlari.setdefault(k.get("rol") or "—", []).append(k)
    rol_istatistik = {rol: isci_istatistik(ks, simdi, yari_omur) for rol, ks in rol_kayitlari.items()}

    def dene_adayi(rol: str, alan: str, secilenler: set[str]) -> str:
        etkin = {i["isci"]: i["etkin"] for i in isci_istatistik(tum_gruplar[(rol, alan)], simdi, yari_omur)}
        adaylar = [(-i["duzeltilmis"], etkin.get(i["isci"], 0.0), i["isci"]) for i in rol_istatistik.get(rol, [])
                   if i["isci"] not in secilenler and etkin.get(i["isci"], 0.0) < AZ_VERI
                   and i["duzeltilmis"] >= 3.5]
        return min(adaylar)[2] if adaylar else "—"

    satirlar = [
        "| Role | Field | Roster | Score | n | Backup | Backup score | Basis | Try |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    for rol, alan in sirali_ciftler:
        pencere_kayit_grubu = pencere_gruplar.get((rol, alan), [])
        p_ist = isci_istatistik(pencere_kayit_grubu, simdi, yari_omur) if pencere_kayit_grubu else []

        if p_ist:
            p_ist.sort(key=lambda x: (-x["duzeltilmis"], -x["n"], x["isci"]))
            kadro = p_ist[0]
            kadro_isci = kadro["isci"]
            puan = format_sayi(kadro["duzeltilmis"], 2)
            n = kadro["n"]
            dayanak = "window, little data" if kadro["etkin"] < AZ_VERI else "window"

            if len(p_ist) >= 2:
                yedek = p_ist[1]
                yedek_isci = yedek["isci"]
                yedek_puani = format_sayi(yedek["duzeltilmis"], 2)
            else:
                yedek_isci = "—"
                yedek_puani = "—"
        else:
            tum_kayit_grubu = tum_gruplar[(rol, alan)]
            t_ist = isci_istatistik(tum_kayit_grubu, simdi, yari_omur)
            if not t_ist:
                continue
            t_ist.sort(key=lambda x: (-x["duzeltilmis"], -x["n"], x["isci"]))
            kadro = t_ist[0]
            kadro_isci = kadro["isci"]
            puan = format_sayi(kadro["duzeltilmis"], 2)
            n = kadro["n"]
            dayanak = "stale"

            if len(t_ist) >= 2:
                yedek = t_ist[1]
                yedek_isci = yedek["isci"]
                yedek_puani = format_sayi(yedek["duzeltilmis"], 2)
            else:
                yedek_isci = "—"
                yedek_puani = "—"

        dene = dene_adayi(rol, alan, {kadro_isci, yedek_isci})
        satirlar.append(
            f"| {rol} | {alan} | {kadro_isci} | {puan} | {n} | {yedek_isci} | {yedek_puani} | {dayanak} | {dene} |"
        )

    if len(satirlar) <= 2:
        return "No records."

    dt = datetime.fromtimestamp(simdi, tz=timezone.utc)
    tarih_str = dt.strftime("%Y-%m-%d")
    baslik = f"Roster summary: last {gun} days, {k_sayisi} records (generated: {tarih_str})"
    tablo = "\n".join(satirlar)
    return f"{baslik}\n\n{tablo}"


def cmd_ozet(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="roster.py summary", description="Roster summary table")
    parser.add_argument("--days", dest="gun", type=int, default=7, help="records of the last N days (default: 7)")
    parser.add_argument("--no-seed", dest="tohumsuz", action="store_true", help="leave out the seed data")
    parser.add_argument("--now", dest="simdi", type=float, default=None, help="current time (epoch seconds, for tests)")
    parser.add_argument("--half-life", dest="yari_omur", type=float, default=YARI_OMUR,
                        help="days after which a score counts half (default: 30; 0 = no fading)")
    args = parser.parse_args(argv)

    kayitlar = kayitlari_oku(tohumsuz=args.tohumsuz)
    cikti = tablo_olustur_ozet(kayitlar, gun=args.gun, simdi=args.simdi, yari_omur=args.yari_omur)
    print(cikti)
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2

    cmd = argv[0]
    if cmd == "suggest":
        return cmd_oneri(argv[1:])
    if cmd == "summary":
        return cmd_ozet(argv[1:])
    if cmd in ("add", "score"):
        return olay.puan_isle(argv[1:])

    print(f"Unknown command: {cmd}\n{__doc__}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
