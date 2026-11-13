#!/usr/bin/env python3
"""polycrew dynamic roster: worker suggestions from the score ledger.

Usage:
  roster.py suggest [--role R] [--field F] [--difficulty E|M|H] [--half-life DAYS] [--no-seed]
  roster.py summary [--days N] [--half-life DAYS] [--no-seed] [--now TS]
  roster.py structure [--days N] [--half-life DAYS] [--no-seed] [--now TS]
  common: [--no-cost] [--providers claude,codex,agy] [--no-quota] [--quota-low-5h PCT] [--quota-low-week PCT]

`structure` prints suggestions about the shape of the team (Claude or external per role, workers to
avoid, whether a lead is used) and the remaining quota of each provider (newest reading in the event
log). It changes nothing: the user decides (0011).

`summary` also lists, under the table, pitfall candidates: scores below 3 of the workers in the table
(newest first, at most 5, last 30 days; written by `events.py score` next to the event log). They are
suggestions only: nothing reads them as rules and no ranking changes because of them.

Quota (suggest, summary, structure): the newest quota reading per provider in the event log. A worker
with under 20% left in the 5-hour window or under 10% left in the week (`--quota-low-5h`,
`--quota-low-week`) drops below the others in its row and is marked "low quota". A missing or stale
reading (its reset time has passed, or it is older than 5 hours / one day for the 5-hour / weekly
window) changes nothing; a note says so, for Claude too. A stale reading already under the limit still
counts as low while its window has not reset (usage only grows). Argon workers count agy's Argon group
(Gemini when agy reports none); Claude workers count the general windows and the per-model weekly window
named in their model. The rules live in hooks/quota.py (0018). `--no-quota` turns it all off.

A later score for the same job (project + id) replaces the earlier one. When two workers are within
0.10 of each other, the clearly cheaper one (20% less quota, else 20% less time) goes first (0009).
Workers of an external tool that is not installed (codex, agy) are left out.

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
import shutil
import sys
import time
from pathlib import Path

# hooks modülünü içe aktarabilmek için ekle
KOK = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(KOK / "hooks"))
import events as olay  # noqa: E402
import quota as kurallar  # noqa: E402


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

    return tekillestir(kayitlar)


def tekillestir(kayitlar: list[dict]) -> list[dict]:
    """Aynı işin (proje + id) sonraki puanı öncekinin yerine geçer (0009); id'siz kayıt kalır."""
    son: dict[tuple, int] = {}
    for sira, k in enumerate(kayitlar):
        if k.get("id") not in (None, ""):
            son[(k.get("proje"), str(k["id"]))] = sira
    return [k for sira, k in enumerate(kayitlar)
            if k.get("id") in (None, "") or son[(k.get("proje"), str(k["id"]))] == sira]


DIS_ARACLAR = ("codex", "agy")  # işçi adının ilk parçası; araç PATH'te yoksa önerilmez (0009)


def kurulu_saglayicilar(verilen: str | None = None) -> set[str] | None:
    """Kullanılabilir dış araçlar; ``verilen`` (ya da POLYCREW_PROVIDERS) yoksa PATH'e bakılır."""
    verilen = verilen or os.environ.get("POLYCREW_PROVIDERS")
    if verilen:
        return {p.strip() for p in verilen.split(",") if p.strip()}
    return {a for a in DIS_ARACLAR if shutil.which(a)}


def saglayici_suz(kayitlar: list[dict], kurulu: set[str]) -> tuple[list[dict], list[str]]:
    """Kurulu olmayan dış aracın işçilerini çıkarır; (kalan kayıtlar, dışarıda kalan araçlar)."""
    disarida = set()
    kalan = []
    for k in kayitlar:
        arac = str(k.get("isci") or "").split("/", 1)[0]
        if arac in DIS_ARACLAR and arac not in kurulu:
            disarida.add(arac)
        else:
            kalan.append(k)
    return kalan, sorted(disarida)


MALIYET = True  # --no-cost kapatır
YAKIN_PUAN = 0.10  # bu kadar yakın iki işçide ucuz olan öne geçer
BELIRGIN = 0.20  # "ucuz": en az bu oranda az kota ya da kısa süre


def maliyet_sirasi(liste: list[dict]) -> list[dict]:
    """Puana göre sıralı listede, yakın puanlı komşulardan belirgin ucuz olanı öne alır (0009)."""
    if not MALIYET:
        return liste
    for i in range(len(liste) - 1):
        ust, alt = liste[i], liste[i + 1]
        if ust["duzeltilmis"] - alt["duzeltilmis"] > YAKIN_PUAN:
            continue
        neden = None
        if ust["ort_kota"] is not None and alt["ort_kota"] is not None:
            if alt["ort_kota"] <= ust["ort_kota"] * (1 - BELIRGIN):
                neden = "cheaper"
        elif ust["ort_sure"] is not None and alt["ort_sure"] is not None:
            if alt["ort_sure"] <= ust["ort_sure"] * (1 - BELIRGIN):
                neden = "faster"
        if neden:
            liste[i], liste[i + 1] = alt, ust
            if alt.get("neden") != neden:
                alt["neden"] = neden
                alt["durum"] = f"{alt['durum']}, {neden}" if alt["durum"] else neden
    return liste


# Kota: olay günlüğündeki en yeni kota okuması. Az kotası kalan işçi satırında alta iner.
# Eşleme, sıfırlanma ve tazelik kuralları hooks/quota.py'de (0018: sayfa ve doctor ile tek kaynak).
KOTA_AZ_5SA = 20.0  # yüzde: 5 saatlik pencerede bundan az kalan işçi "low quota"
KOTA_AZ_HAFTA = 10.0  # yüzde: haftalıkta bundan az kalan işçi "low quota"
KOTA_ESKI = kurallar.SINIR  # saniye: okuma pencerenin bunca ötesinde eski sayılır
KOTA_PENCERE_AD = {"5 saat": "5 hours", "hafta": "week"}
KOTA_SAGLAYICILAR = ("claude", "codex", "agy")
_kota_zamani = kurallar.zaman
_kota_yenilenme = kurallar.yenilenme


def kota_okumalari(agy_gruplari: set | None = None) -> dict[tuple, dict]:
    """Olay günlüğündeki en yeni kota okuması, (sağlayıcı, grup, pencere) başına.

    ``agy_gruplari`` verilirse en yeni agy okumasındaki grup adlarıyla doldurulur: Argon'un kendi kovası
    yalnız agy onu bugün de veriyorsa sayılır (eski bir okumada kalan Argon kovası Gemini'ye düşmeyi
    engellemesin, 0018)."""
    son: dict[tuple, dict] = {}
    son_agy = (None, set())
    for e in olay._olaylar():
        ts = _kota_zamani(e.get("ts"))
        if e.get("tur") != "kota" or ts is None:
            continue
        kovalar = e.get("kovalar")
        gruplar = {kurallar.adlari_duzelt(k).get("grup") for k in kovalar if isinstance(k, dict)
                   and k.get("saglayici") == "agy"} if isinstance(kovalar, list) else set()
        if gruplar and (son_agy[0] is None or ts >= son_agy[0]):
            son_agy = (ts, gruplar)
        for k in kovalar if isinstance(kovalar, list) else []:  # bozuk olay öbür sağlayıcıları düşürmez
            if not isinstance(k, dict):
                continue
            k = kurallar.adlari_duzelt(k)
            # agy'nin "kullanilan"ı tam sayıya yuvarlıdır (%19,6 kalan → 20); eşik için yuvarlanmamış "hassas" okunur.
            # Codex'te "hassas" pencere sıfırlanınca 0 yazılır, o yüzden orada "kullanilan".
            kullanilan = k.get("hassas") if k.get("saglayici") == "agy" and k.get("hassas") is not None else k.get("kullanilan")
            if not isinstance(kullanilan, (int, float)) or isinstance(kullanilan, bool):
                kullanilan = None  # okunamayan kova (agy "?"): kalan bilinmiyor, ama eski okumayı da geçersiz kılar
            pencere = k.get("pencere")
            if pencere not in KOTA_ESKI:
                continue  # Claude'un "bağlam" kovası bağlam doluluğudur, kota değil
            olcum = _kota_zamani(k.get("olcum"))
            olcum = ts if olcum is None else olcum
            anahtar = (k.get("saglayici"), k.get("grup"), pencere)
            if anahtar not in son or olcum >= son[anahtar]["olcum"]:
                son[anahtar] = {"kullanilan": None if kullanilan is None else float(kullanilan), "olcum": olcum,
                                "yenilenir": _kota_yenilenme(k, olcum)}
    if agy_gruplari is not None:
        agy_gruplari.update(son_agy[1])
    return {a: v for a, v in son.items() if v["kullanilan"] is not None}


def isci_kota_grubu(isci: str) -> tuple[str, str | None] | None:
    """İşçinin kotasının sağlayıcısı ve (okumadan bağımsız) grubu; Claude'da None (genel ve model kovası).

    Asıl eşleme ``kurallar.isci_kovasi_mi``'dedir: Argon'un kovası okumada yoksa Gemini'ye düşer.
    """
    parcalar = str(isci or "").split("/")
    if parcalar[0] == "codex":
        return "codex", "Codex"
    if parcalar[0] == "agy":
        return "agy", kurallar.agy_grubu(parcalar[1] if len(parcalar) > 1 else "")
    if parcalar[0] == "claude":
        return "claude", None
    return None


class KotaBilgisi:
    """Kota okumaları ve eşikler; ``durum(işçi)`` low / ok / stale / none döner (tanınmayan araçta None)."""

    def __init__(self, okumalar: dict[tuple, dict], simdi: float,
                 az_5sa: float = KOTA_AZ_5SA, az_hafta: float = KOTA_AZ_HAFTA, agy_gruplari: set | None = None):
        self.okumalar, self.simdi, self.az_5sa, self.az_hafta = okumalar, simdi, az_5sa, az_hafta
        self.agy_gruplari = agy_gruplari  # en yeni agy okumasının grupları; yoksa okumalardan

    def eski_neden(self, pencere: str, kova: dict) -> str | None:
        """Okuma pencereden eskiyse nedeni: sıfırlanma geçti, ya da yaşı pencereyi aştı."""
        return kurallar.eski_neden(pencere, kova["olcum"], kova["yenilenir"], self.simdi)

    def az_mi(self, pencere: str, kullanilan: float) -> bool:
        kalan = 100.0 - kullanilan
        return (pencere == "5 saat" and kalan < self.az_5sa) or (pencere == "hafta" and kalan < self.az_hafta)

    def isci_kovalari(self, isci: str) -> list[tuple[str, dict]]:
        """İşçinin kotasını gösteren kovalar (pencere, okuma)."""
        gruplar = self.agy_gruplari if self.agy_gruplari else {g for (s, g, _p) in self.okumalar if s == "agy"}
        return [(p, v) for (s, g, p), v in sorted(self.okumalar.items(), key=lambda x: tuple(map(str, x[0])))
                if kurallar.isci_kovasi_mi(isci, s, g, gruplar)]

    def durum(self, isci: str) -> str | None:
        if not kurallar.tanimli(isci):
            return None
        kovalar = self.isci_kovalari(isci)
        if not kovalar:
            return "none"
        # 0018: kullanım pencere içinde yalnız artar. Sıfırlanması henüz gelmemiş eski okuma eşiğin
        # altındaysa (kalan az) işçi yine "low": bugün en az o kadar dolu.
        for pencere, v in kovalar:
            if self.az_mi(pencere, v["kullanilan"]) and v["yenilenir"] is not None and v["yenilenir"] > self.simdi:
                return "low"
        taze = [(p, v) for p, v in kovalar if not self.eski_neden(p, v)]
        if not taze:
            return "stale"
        for pencere, v in taze:
            if self.az_mi(pencere, v["kullanilan"]):
                return "low"
        return "ok"

    def notlar(self, isciler) -> list[str]:
        """Sıra ayarlanamayan sağlayıcılar için tek satırlık not (okuma yok ya da eski); Claude için yazılmaz."""
        yok, eski = set(), set()
        for isci in isciler:
            d, hedef = self.durum(isci), isci_kota_grubu(isci)
            if hedef:
                (yok if d == "none" else eski if d == "stale" else set()).add(hedef[0])
        parcalar = []
        if yok:
            parcalar.append(f"no quota reading for {', '.join(sorted(yok))}")
        if eski:
            parcalar.append(f"stale quota reading for {', '.join(sorted(eski))}")
        if not parcalar:
            return []
        if "claude" in yok | eski:
            # 0018: Claude okuması kendiliğinden gelmez (statusline betiği yoksa); PM yazar.
            return [f"Quota: {'; '.join(parcalar)}; the order is not adjusted for them "
                    "(run external-agent.sh quota; for Claude read the desktop usage tool or /usage and record it "
                    "with claude-quota.py)."]
        return [f"Quota: {'; '.join(parcalar)}; the order is not adjusted for them "
                "(run external-agent.sh quota to refresh)."]


ADAY_GUN = 30  # gün: bundan eski tuzak adayı özette görünmez
ADAY_SATIR = 5  # özette en çok bu kadar aday satırı
ADAY_GEREKCE = 110  # karakter: gerekçe bu kadar kısaltılır


def adaylari_oku() -> list[dict]:
    """Tuzak adayları (events.py score, 3'ün altı); dosya yoksa ya da bozuksa boş. Yalnız öneridir."""
    adaylar: dict[tuple, dict] = {}
    try:
        satirlar = olay.adaylar_dosyasi().read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []
    for satir in satirlar:
        try:
            a = json.loads(satir)
        except ValueError:
            continue
        if isinstance(a, dict) and isinstance(a.get("isci"), str) and a["isci"]:
            adaylar[(str(a.get("proje")), str(a.get("id")))] = olay.kayit_adlari(a)  # aynı işin sonraki puanı geçerli
    return list(adaylar.values())


def aday_satirlari(adaylar: list[dict], isciler, simdi: float) -> list[str]:
    """Tabloda geçen işçilerin son ``ADAY_GUN`` gündeki tuzak adayları, en yeni önde, en çok ``ADAY_SATIR``."""
    uygun = []
    for a in adaylar:
        try:
            ts = float(a.get("ts"))
        except (TypeError, ValueError):
            continue
        if a.get("isci") in isciler and simdi - ADAY_GUN * 86400 <= ts <= simdi:
            uygun.append((ts, a))
    uygun.sort(key=lambda x: -x[0])
    satirlar = []
    for ts, a in uygun[:ADAY_SATIR]:
        gerekce = " ".join(str(a.get("gerekce") or "").split())
        if len(gerekce) > ADAY_GEREKCE:
            gerekce = gerekce[:ADAY_GEREKCE - 1].rstrip() + "…"
        yer = "/".join(str(a[k]) for k in ("rol", "alan") if a.get(k))
        puan = a.get("not")
        puan = int(puan) if isinstance(puan, float) and puan.is_integer() else puan
        satirlar.append(f"- {format_ts(ts)} {a['isci']}" + (f" {yer}" if yer else "") + f" score {puan}"
                        + (f": {gerekce}" if gerekce else ""))
    if not satirlar:
        return []
    return ["Pitfall candidates (suggestions only, newest first; nothing reads them as rules):", *satirlar]


def kota_siralama(liste: list[dict], kota: KotaBilgisi | None) -> list[dict]:
    """Az kotası kalan işçileri satırın sonuna alır (kendi aralarındaki sıra kalır) ve "low quota" yazar."""
    if kota is None:
        return liste
    az = [i for i in liste if kota.durum(i["isci"]) == "low"]
    if not az:
        return liste
    for i in az:
        i["kota_az"] = True
        i["durum"] = f"{i['durum']}, low quota" if i["durum"] else "low quota"
    return [i for i in liste if not i.get("kota_az")] + az


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
                    yari_omur: float = YARI_OMUR, kota_bilgi: KotaBilgisi | None = None) -> list[dict]:
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
    return kota_siralama(maliyet_sirasi(sonuclar), kota_bilgi)


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
                            yari_omur: float = YARI_OMUR, kota: KotaBilgisi | None = None) -> str:
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
        istatistikler = isci_istatistik(grup_kayitlari, simdi, yari_omur, kota)
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


def ortak_bayraklar(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--no-cost", dest="maliyetsiz", action="store_true",
                        help="do not let the cheaper of two near-equal workers go first")
    parser.add_argument("--providers", dest="saglayicilar", type=str, default=None,
                        help="installed external tools, comma separated (default: detect codex and agy on PATH)")
    parser.add_argument("--no-quota", dest="kotasiz", action="store_true",
                        help="do not read the quota readings of the event log")
    parser.add_argument("--quota-low-5h", dest="kota_az_5sa", type=float, default=KOTA_AZ_5SA,
                        help=f"a worker with less than this percent left in the 5-hour window counts as low (default: {KOTA_AZ_5SA:g})")
    parser.add_argument("--quota-low-week", dest="kota_az_hafta", type=float, default=KOTA_AZ_HAFTA,
                        help=f"a worker with less than this percent left in the week counts as low (default: {KOTA_AZ_HAFTA:g})")


def ortak_uygula(args, kayitlar: list[dict]) -> tuple[list[dict], list[str]]:
    global MALIYET
    MALIYET = not args.maliyetsiz
    return saglayici_suz(kayitlar, kurulu_saglayicilar(args.saglayicilar))


def kota_kur(args, simdi: float) -> KotaBilgisi | None:
    """``--no-quota`` yoksa olay günlüğündeki okumalardan kota bilgisi; günlük okunamazsa None."""
    if args.kotasiz:
        return None
    try:
        gruplar: set = set()
        okumalar = kota_okumalari(gruplar)
        return KotaBilgisi(okumalar, simdi, args.kota_az_5sa, args.kota_az_hafta, gruplar)
    except Exception:  # noqa: BLE001 - kota yalnız bir ipucudur; sıralama onsuz da çalışır
        return None


def notlari_yaz(kota: KotaBilgisi | None, isciler) -> None:
    for satir in kota.notlar(isciler) if kota else []:
        print(f"\n{satir}")


def disarida_yaz(disarida: list[str]) -> None:
    if disarida:
        print(f"\nLeft out (not installed): {', '.join(disarida)}")


def cmd_oneri(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="roster.py suggest", description="Roster suggestion table")
    parser.add_argument("--role", dest="rol", type=str, default=None, help="role filter")
    parser.add_argument("--field", dest="alan", type=str, default=None, help="field filter")
    parser.add_argument("--difficulty", dest="zorluk", type=str, default=None, help="difficulty filter (E, M, H)")
    parser.add_argument("--no-seed", dest="tohumsuz", action="store_true", help="leave out the seed data")
    parser.add_argument("--half-life", dest="yari_omur", type=float, default=YARI_OMUR,
                        help="days after which a score counts half (default: 30; 0 = no fading)")
    parser.add_argument("--now", dest="simdi", type=float, default=None, help="current time (epoch seconds, for tests)")
    ortak_bayraklar(parser)
    args = parser.parse_args(argv)
    simdi = args.simdi if args.simdi is not None else time.time()

    # Eski adla verilen filtre de yeni ada çevrilir (0007).
    f = olay.kayit_adlari({"rol": args.rol, "alan": args.alan, "zorluk": args.zorluk})
    args.rol, args.alan, args.zorluk = f["rol"], f["alan"], f["zorluk"]
    kayitlar, disarida = ortak_uygula(args, kayitlari_oku(tohumsuz=args.tohumsuz))
    if not kayitlar:
        print("No score records found.")
        disarida_yaz(disarida)
        return 0
    kota = kota_kur(args, simdi)

    filtre_var = any([args.rol is not None, args.alan is not None, args.zorluk is not None])
    if filtre_var:
        uygun_kayitlar = [k for k in kayitlar if kayit_filtrele(k, args.rol, args.alan, args.zorluk)]
        if not uygun_kayitlar:
            print("No score records match the filter.")
        else:
            print(tablo_olustur_filtreli(isci_istatistik(uygun_kayitlar, simdi, args.yari_omur, kota)))
            notlari_yaz(kota, {k["isci"] for k in uygun_kayitlar})
    else:
        print(tablo_olustur_filtresiz(kayitlar, simdi, args.yari_omur, kota))
        notlari_yaz(kota, {k["isci"] for k in kayitlar})
    disarida_yaz(disarida)
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


def _gelecekte(kayit: dict, simdi: float) -> bool:
    try:
        return float(kayit.get("ts")) > simdi
    except (TypeError, ValueError):
        return False


def tablo_olustur_ozet(
    kayitlar: list[dict],
    gun: int = 7,
    simdi: float | None = None,
    yari_omur: float = YARI_OMUR,
    kota: KotaBilgisi | None = None,
    adaylar: list[dict] | None = None,
) -> str:
    if not kayitlar:
        return "No records."

    if simdi is None:
        simdi = time.time()
    kayitlar = [k for k in kayitlar if not _gelecekte(k, simdi)]  # 0014: hiçbir sütunda sayılmaz
    if not kayitlar:
        return "No records."

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
                   and i["duzeltilmis"] >= 3.5 and not (kota and kota.durum(i["isci"]) == "low")]
        return min(adaylar)[2] if adaylar else "—"

    satirlar = [
        "| Role | Field | Roster | Score | n | Backup | Backup score | Basis | Try |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    gorunen: set[str] = set()  # tabloda geçen işçiler: kota notu ve tuzak adayları bunlara bakar
    for rol, alan in sirali_ciftler:
        # 0014: sıralama bütün geçmişten (yarı ömürle sönümlü); pencere yalnız dayanağı belirler.
        # Önceden yalnız penceredeki puanlar sayılıyordu: tek bir yeni puan 11 puanlı işçiyi tablodan atıyordu.
        tum_kayit_grubu = tum_gruplar[(rol, alan)]
        t_ist = isci_istatistik(tum_kayit_grubu, simdi, yari_omur)
        if not t_ist:
            continue
        t_ist.sort(key=lambda x: (-x["duzeltilmis"], -x["n"], -(x["son_ts"] or 0), x["isci"]))
        maliyet_sirasi(t_ist)
        t_ist = kota_siralama(t_ist, kota)  # az kotalı işçi yedeğe iner
        kadro = t_ist[0]
        kadro_isci = kadro["isci"]
        puan = format_sayi(kadro["duzeltilmis"], 2)
        n = kadro["n"]
        pencerede = {k.get("isci") for k in pencere_gruplar.get((rol, alan), [])}
        if kadro_isci in pencerede:
            dayanak = "window, little data" if kadro["etkin"] < AZ_VERI else "window"
        else:
            dayanak = "stale"
        if kadro.get("neden"):
            dayanak += f", {kadro['neden']}"
        if kadro.get("kota_az"):
            dayanak += ", low quota"
        elif len(t_ist) >= 2 and t_ist[1].get("kota_az"):
            dayanak += ", backup low quota"
        if len(t_ist) >= 2:
            yedek_isci = t_ist[1]["isci"]
            yedek_puani = format_sayi(t_ist[1]["duzeltilmis"], 2)
        else:
            yedek_isci = "—"
            yedek_puani = "—"

        dene = dene_adayi(rol, alan, {kadro_isci, yedek_isci})
        gorunen.update({kadro_isci, yedek_isci, dene} - {"—"})
        satirlar.append(
            f"| {rol} | {alan} | {kadro_isci} | {puan} | {n} | {yedek_isci} | {yedek_puani} | {dayanak} | {dene} |"
        )

    if len(satirlar) <= 2:
        return "No records."

    dt = datetime.fromtimestamp(simdi, tz=timezone.utc)
    tarih_str = dt.strftime("%Y-%m-%d")
    baslik = f"Roster summary: last {gun} days, {k_sayisi} records (generated: {tarih_str})"
    tablo = "\n".join(satirlar)
    alt = kota.notlar(gorunen) if kota else []
    adaylar_metni = "\n".join(aday_satirlari(adaylar or [], gorunen, simdi))
    return "\n\n".join([baslik, tablo, *alt, *([adaylar_metni] if adaylar_metni else [])])


YAPI_FARK = 0.25  # iki taraf arasında bundan büyük fark "prefer" demektir (0011)
KACIN_PUAN = 3.0  # bir rolde bunun altına düşen işçi "avoid"
KACIN_N = 2.0  # ... yeter ki bu kadar etkin verisi olsun


def yapi_satirlari(kayitlar: list[dict], simdi: float, yari_omur: float) -> tuple[list[dict], list[dict]]:
    """Rol başına Claude ve dış işçi karşılaştırması ile kaçınılacak işçiler (0011)."""
    roller: dict[str, list[dict]] = {}
    for k in kayitlar:
        roller.setdefault(k.get("rol") or "—", []).append(k)

    def en_iyi(liste: list[dict]) -> dict | None:
        yeterli = [i for i in liste if i["etkin"] >= AZ_VERI]
        return (yeterli or liste or [None])[0]

    satirlar, kacin = [], []
    for rol in sorted(roller):
        ist = isci_istatistik(roller[rol], simdi, yari_omur)
        c = en_iyi([i for i in ist if i["isci"].split("/", 1)[0] == "claude"])
        d = en_iyi([i for i in ist if i["isci"].split("/", 1)[0] in DIS_ARACLAR])
        c_var = bool(c) and c["etkin"] >= AZ_VERI
        d_var = bool(d) and d["etkin"] >= AZ_VERI
        if c_var and d_var:
            fark = c["duzeltilmis"] - d["duzeltilmis"]
            if fark > YAPI_FARK:
                oneri = "prefer Claude"
            elif fark < -YAPI_FARK:
                oneri = "prefer external"
            else:
                oneri = "equal: external first, keep Claude quota"
        elif c_var:
            oneri = "external: little data" if d else "only Claude measured"
        elif d_var:
            oneri = "Claude: little data" if c else "only external measured"
        else:
            oneri = "not enough data"
        satirlar.append({"rol": rol, "claude": c, "dis": d, "oneri": oneri})
        kacin += [{"rol": rol, **i} for i in ist if i["etkin"] >= KACIN_N and i["duzeltilmis"] < KACIN_PUAN]
    return satirlar, kacin


def takim_kullanimi(simdi: float, gun: int) -> dict | None:
    """Olay günlüğünden: son ``gun`` günde başlatılan lider sayısı ve en çok eşzamanlı işçi."""
    try:
        sys.path.insert(0, str(KOK / "skills" / "watch"))
        import watch  # tembel: yalnız bu komutta gerekir

        isler = watch.birlestir(watch.oku(), simdi)["isler"]
    except Exception:  # noqa: BLE001 - günlük yoksa takım satırı yazılmaz
        return None
    bas = simdi - gun * 86400
    isler = [i for i in isler if i.get("baslangic") is not None and bas <= i["baslangic"] <= simdi]
    if not isler:
        return None
    lider = sum(1 for i in isler if olay.rol_adi(i.get("rol"), onek=False) == "lead")
    noktalar = []
    for i in isler:
        if i.get("bitis") is not None and i["bitis"] >= i["baslangic"]:
            noktalar += [(i["baslangic"], 1), (i["bitis"], -1)]
    acik = en_cok = 0
    for _, adim in sorted(noktalar, key=lambda n: (n[0], n[1])):
        acik += adim
        en_cok = max(en_cok, acik)
    return {"is": len(isler), "lider": lider, "eszamanli": en_cok}


def kota_satirlari(kota: KotaBilgisi, saglayicilar) -> list[str]:
    """Sağlayıcı başına kalan kota: günlükteki en yeni okuma; eskiyse "stale", azsa "low" (0011 yapı çıktısı)."""
    satirlar = []
    for saglayici in KOTA_SAGLAYICILAR:
        if saglayici not in saglayicilar:
            continue
        gruplar: dict[str | None, list[str]] = {}
        for (s, grup, pencere), v in sorted(kota.okumalar.items(), key=lambda x: tuple(map(str, x[0]))):
            if s != saglayici:
                continue
            kalan = 100.0 - v["kullanilan"]
            etiket = f"{KOTA_PENCERE_AD.get(pencere, pencere)} {format_kota(kalan)} left"
            neden = kota.eski_neden(pencere, v)
            if neden:
                etiket += f" (stale: {neden})"
            elif (pencere == "5 saat" and kalan < kota.az_5sa) or (pencere == "hafta" and kalan < kota.az_hafta):
                etiket += " (low)"
            gruplar.setdefault(grup, []).append(etiket)
        if not gruplar:
            satirlar.append(f"- {saglayici}: no reading")
        for grup, parcalar in gruplar.items():
            ad = saglayici if grup in (None, "Codex", "Claude") else (
                grup if str(grup).lower().startswith(saglayici) else f"{saglayici}: {grup}")
            satirlar.append(f"- {ad}: {', '.join(parcalar)}")
    return satirlar


def tablo_olustur_yapi(kayitlar: list[dict], simdi: float, yari_omur: float, gun: int,
                       kota: KotaBilgisi | None = None, saglayicilar=KOTA_SAGLAYICILAR) -> str:
    satirlar, kacin = yapi_satirlari(kayitlar, simdi, yari_omur)

    def hucre(i: dict | None) -> str:
        if not i:
            return "— | —"
        return f"{i['isci']} | {format_sayi(i['duzeltilmis'], 2)} ({format_sayi(i['etkin'], 1)})"

    cikti = ["Team structure suggestions (suggestions only: the user decides)", ""]
    if satirlar:
        cikti += ["| Role | Best Claude | Score (eff. n) | Best external | Score (eff. n) | Suggestion |",
                  "|---|---|---|---|---|---|"]
        cikti += [f"| {s['rol']} | {hucre(s['claude'])} | {hucre(s['dis'])} | {s['oneri']} |" for s in satirlar]
    else:
        cikti.append("No score records found.")
    for k in kacin:
        cikti.append(f"\nAvoid: {k['isci']} as {k['rol']} "
                     f"({format_sayi(k['duzeltilmis'], 2)}, eff. n {format_sayi(k['etkin'], 1)})")
    kullanim = takim_kullanimi(simdi, gun)
    if kullanim:
        cikti.append(f"\nTeam: {kullanim['is']} jobs in the last {gun} days, at most {kullanim['eszamanli']} "
                     f"running at once, {kullanim['lider']} lead(s) started.")
        if kullanim["lider"] == 0:
            cikti.append("The small team (PM → workers) is what is actually used; a lead is not needed at this size.")
    if kota:
        cikti.append("\nQuota left (newest reading in the event log):")
        cikti += kota_satirlari(kota, saglayicilar)
    return "\n".join(cikti)


def cmd_yapi(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="roster.py structure", description="Team structure suggestions")
    parser.add_argument("--days", dest="gun", type=int, default=30, help="event log window for team use (default: 30)")
    parser.add_argument("--no-seed", dest="tohumsuz", action="store_true", help="leave out the seed data")
    parser.add_argument("--now", dest="simdi", type=float, default=None, help="current time (epoch seconds, for tests)")
    parser.add_argument("--half-life", dest="yari_omur", type=float, default=YARI_OMUR,
                        help="days after which a score counts half (default: 30; 0 = no fading)")
    ortak_bayraklar(parser)
    args = parser.parse_args(argv)
    simdi = args.simdi if args.simdi is not None else time.time()
    kayitlar, disarida = ortak_uygula(args, kayitlari_oku(tohumsuz=args.tohumsuz))
    kurulu = {"claude", *(kurulu_saglayicilar(args.saglayicilar) or set())}
    print(tablo_olustur_yapi(kayitlar, simdi, args.yari_omur, args.gun, kota_kur(args, simdi), kurulu))
    disarida_yaz(disarida)
    return 0


def cmd_ozet(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="roster.py summary", description="Roster summary table")
    parser.add_argument("--days", dest="gun", type=int, default=7, help="records of the last N days (default: 7)")
    parser.add_argument("--no-seed", dest="tohumsuz", action="store_true", help="leave out the seed data")
    parser.add_argument("--now", dest="simdi", type=float, default=None, help="current time (epoch seconds, for tests)")
    parser.add_argument("--half-life", dest="yari_omur", type=float, default=YARI_OMUR,
                        help="days after which a score counts half (default: 30; 0 = no fading)")
    ortak_bayraklar(parser)
    args = parser.parse_args(argv)
    simdi = args.simdi if args.simdi is not None else time.time()

    kayitlar, disarida = ortak_uygula(args, kayitlari_oku(tohumsuz=args.tohumsuz))
    cikti = tablo_olustur_ozet(kayitlar, gun=args.gun, simdi=simdi, yari_omur=args.yari_omur,
                               kota=kota_kur(args, simdi), adaylar=adaylari_oku())
    print(cikti)
    disarida_yaz(disarida)
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2

    cmd = argv[0]
    if cmd in ("-h", "--help"):
        print(__doc__)
        return 0
    if cmd == "suggest":
        return cmd_oneri(argv[1:])
    if cmd == "structure":
        return cmd_yapi(argv[1:])
    if cmd == "summary":
        return cmd_ozet(argv[1:])
    if cmd in ("add", "score"):
        return olay.puan_isle(argv[1:])

    print(f"Unknown command: {cmd}\n{__doc__}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
