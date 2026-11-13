#!/usr/bin/env python3
"""polycrew kurulumunu salt okunur denetle; yalnız standart kütüphane."""

from __future__ import annotations

import sys

if __name__ == "__main__":
    sys.dont_write_bytecode = True  # Denetim, içe aktarmada bile dosya oluşturmaz.

import argparse
import json
import math
import os
import shutil
import subprocess
import time
from datetime import datetime
from functools import lru_cache
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent.parent
KOTA_YASI = 5 * 3600
GELECEK_PAYI = 300  # saat kayması payı (sn)
SAGLAYICILAR = ("claude", "codex", "agy")


@lru_cache(maxsize=1)
def olay_modulu():
    onceki = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        sys.path.insert(0, str(KOK / "hooks"))
        import events as olay
        import quota  # noqa: F401 - kota_sifirlanmalari için (0018)

        return olay
    finally:
        sys.dont_write_bytecode = onceki


def denetle(ad, islem):
    """Her denetimin hatasını kendi satırında tut; ayrıntıda hassas veri gösterme."""
    try:
        durum, ayrinti = islem()
    except Exception as hata:
        durum, ayrinti = "warn", f"check could not finish ({type(hata).__name__}); inspect this setup item"
    return {"status": durum, "name": ad, "detail": ayrinti}


def python_surumu():
    surum = ".".join(str(sayi) for sayi in sys.version_info[:3])
    if sys.version_info < (3, 9):
        return "fail", f"Python {surum}; install Python 3.9 or newer"
    return "ok", f"Python {surum}"


def arac(ad):
    yol = shutil.which(ad)
    if yol:
        return "ok", yol
    if ad == "node":
        return "warn", "not on PATH; office layout tests are skipped; install Node.js to run them"
    return "warn", "not on PATH; the team will use Claude roles only; install this tool to enable external workers"


@lru_cache(maxsize=None)
def not_dosyasi(proje):
    olay = olay_modulu()
    if not olay.duzen_var({"cwd": str(proje)}):
        return None
    # Ortak yardımcı yalnız bool döndürür; komşu dosyalar için konumu da gerekir.
    ham = Path(os.path.abspath(os.path.expanduser(str(proje))))
    for yol in (ham, ham.resolve()):
        for dizin in (yol, *yol.parents):
            for ad in olay.NOT_DOSYALARI:
                dosya = dizin / ad
                if dosya.is_file():
                    return dosya
    return None


def proje_dosyasi(proje, ad=None):
    if not Path(os.path.expanduser(str(proje))).is_dir():
        return "warn", f"project folder does not exist: {proje}; check the --project path"
    notlar = not_dosyasi(proje)
    if notlar is None:
        return "warn", "notes file not found in project or parents; run /project-setup (hooks ignore projects without notes)"
    yol = notlar.parent / ad if ad else notlar
    if not yol.is_file():
        return "warn", f"missing {yol}; run /project-setup"
    return "ok", str(yol)


def gunluk_klasoru():
    yol = olay_modulu().dosya()
    # Kanca klasörü ilk olayda kendisi açar (events.yaz): eksik klasör hata değil, yazılabilir en yakın üst yeter.
    ust = yol.parent
    while not ust.exists() and ust != ust.parent:
        ust = ust.parent
    if not ust.is_dir() or not os.access(ust, os.W_OK):
        return "warn", f"{ust} is not writable, so the event log cannot be written; adjust its permissions or set POLYCREW_EVENTS"
    if ust != yol.parent:
        return "ok", f"{yol.parent}: not there yet; the hook creates it at the first event"
    return "ok", f"{yol.parent}: folder exists and is writable"


def gunluk():
    olay = olay_modulu()
    yol = olay.dosya()
    if not yol.exists():
        return "ok", f"{yol}: no events yet"
    if not yol.is_file():
        return "fail", f"{yol} is not a file; remove it or point POLYCREW_EVENTS at a file"
    if not os.access(yol, os.W_OK):
        return "warn", f"{yol} is read-only; new events will be lost; adjust its permissions"
    boyut = yol.stat().st_size
    try:
        sinir = float(os.environ.get("POLYCREW_EVENTS_MAX_MB") or olay.EN_COK_MB) * 1024 * 1024
    except ValueError:
        sinir = olay.EN_COK_MB * 1024 * 1024
    if sinir > 0 and boyut > sinir * 0.8:
        return "warn", f"{yol}: {boyut} bytes, over 80% of trim limit ({sinir:g} bytes); archive the log or adjust POLYCREW_EVENTS_MAX_MB"
    return "ok", f"{yol}: {boyut} bytes"


def zaman(deger):
    """Watch gibi ISO ölçümünü, yoksa olayın Unix zamanını oku."""
    try:
        sonuc = (float(deger) if isinstance(deger, (int, float)) else
                 datetime.fromisoformat(deger.replace("Z", "+00:00")).timestamp())
        return sonuc if math.isfinite(sonuc) else None
    except (ValueError, TypeError, AttributeError, OverflowError, OSError):
        return None


def kota_olcumleri():
    """Günlüğü bir kez oku: sağlayıcı başına en yeni kota olayının ölçüm zamanı. Bozuk satır atlanır."""
    yol = olay_modulu().dosya()
    son = {}  # sağlayıcı -> (olay zamanı, ölçüm zamanı)
    if not yol.is_file():
        return son
    simdi = time.time()
    with yol.open(encoding="utf-8", errors="replace") as dosya:
        for satir in dosya:
            try:
                kayit = json.loads(satir)
            except ValueError:
                continue
            if not isinstance(kayit, dict) or kayit.get("tur") != "kota" or not isinstance(kayit.get("kovalar"), list):
                continue
            ts = zaman(kayit.get("ts"))
            if ts is None or ts > simdi + GELECEK_PAYI:  # gelecek tarihli kayıt eski ölçümü gizlemesin
                continue
            olcumler, sifirlanan = {}, {}
            for kova in kayit["kovalar"]:
                if not isinstance(kova, dict) or kova.get("saglayici") not in SAGLAYICILAR:
                    continue
                olcum = zaman(kova.get("olcum"))
                if olcum is None or olcum > simdi + GELECEK_PAYI:
                    olcum = ts
                ad = kova["saglayici"]
                olcumler[ad] = max(olcum, olcumler.get(ad, olcum))
                # 0018: yaşı genç olsa da penceresi o okumadan sonra sıfırlanmış kova eskidir (hooks/quota.py).
                kurallar = sys.modules.get("quota")
                yenilenir = kurallar.yenilenme(kurallar.adlari_duzelt(kova), olcum) if kurallar else None
                if yenilenir is not None and yenilenir <= simdi:
                    pencere = {"5 saat": "5-hour", "hafta": "weekly"}.get(
                        kurallar.adlari_duzelt(kova).get("pencere"), str(kova.get("pencere") or "a"))
                    sifirlanan.setdefault(ad, set()).add(pencere)
            for ad, olcum in olcumler.items():
                if ad not in son or ts >= son[ad][0]:
                    son[ad] = (ts, olcum, sorted(sifirlanan.get(ad, ())))
    SIFIRLANAN.clear()
    SIFIRLANAN.update({ad: pencereler for ad, (_, _, pencereler) in son.items() if pencereler})
    return {ad: olcum for ad, (_, olcum, _) in son.items()}


SIFIRLANAN: dict = {}  # sağlayıcı -> son okumasından sonra sıfırlanan pencereler (kota_olcumleri doldurur)


def kota(saglayici, olcumler):
    # Claude'un kullanımı CLI'dan okunmaz; onu PM yazar. Codex ve agy'yi betik ölçer.
    nasil = ("the PM records it with skills/watch/claude-quota.py (from the desktop usage tool or /usage), "
             "or install skills/watch/claude-statusline.py as the status line" if saglayici == "claude"
             else "run external-agent.sh quota")
    son_olcum = olcumler.get(saglayici)
    if son_olcum is None:
        return "warn", f"no quota reading; {nasil}"
    yas = max(0, time.time() - son_olcum)
    if yas > KOTA_YASI:
        return "warn", f"last reading is {yas / 3600:.1f} hours old; {nasil}"
    if SIFIRLANAN.get(saglayici):
        return "warn", (f"the {' and '.join(SIFIRLANAN[saglayici])} window reset after the last reading "
                        f"({yas / 3600:.1f} hours old); {nasil}")
    return "ok", f"last reading is {yas / 3600:.1f} hours old"


def agy_izinleri():
    yol = Path(os.environ.get("HOME") or os.path.expanduser("~")) / ".gemini" / "antigravity-cli" / "settings.json"
    uyari = "check settings.json permissions.allow; headless agy drops the job at the first command without permission"
    if not yol.is_file():
        return "warn", f"{yol} is missing; {uyari}"
    try:
        ayarlar = json.loads(yol.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError):
        return "warn", f"settings.json is not valid JSON; {uyari}"
    izinler = ayarlar.get("permissions") if isinstance(ayarlar, dict) else None
    kurallar = izinler.get("allow") if isinstance(izinler, dict) else None
    if not isinstance(kurallar, list) or not kurallar:
        return "warn", f"permissions.allow must be a non-empty list; {uyari}"
    return "ok", "settings.json has a non-empty permissions.allow list"


def kabuk_betigi(yol):
    if not Path(yol).is_file():
        return "fail", f"{Path(yol).name} is missing from the plugin; update or reinstall polycrew"
    bash = shutil.which("bash")
    if not bash:
        return "warn", "bash is not on PATH; install bash to check shell syntax"
    sonuc = subprocess.run([bash, "-n", str(yol)], capture_output=True, text=True,
                           check=False, timeout=10)
    if sonuc.returncode:
        return "fail", f"{yol.name}: fix shell syntax; run bash -n on this file"
    return "ok", "bash -n passed"


def betik_listesi():
    return [*sorted((KOK / "hooks").glob("*.sh")), KOK / "skills" / "external-agent" / "external-agent.sh"]


def raporla(proje, betikler=None):
    # Önbellek yalnız bu denetim boyunca geçerli; aynı süreç başka projeyi de denetleyebilir.
    not_dosyasi.cache_clear()
    sonuclar = [denetle("Python version", python_surumu)]
    arac_sonuclari = {}
    for ad in ("codex", "agy", "node"):
        sonuc = denetle(ad, lambda ad=ad: arac(ad))
        arac_sonuclari[ad] = sonuc
        sonuclar.append(sonuc)
    for ad in (None, "CLAUDE.md", "PLAN.md"):
        sonuclar.append(denetle(ad or "Project notes", lambda ad=ad: proje_dosyasi(proje, ad)))
    sonuclar.append(denetle("Event log folder", gunluk_klasoru))
    sonuclar.append(denetle("Event log", gunluk))
    try:
        olcumler, okuma_hatasi = kota_olcumleri(), None
    except Exception as hata:  # tek satır: üç sağlayıcı için aynı hatayı yinelemeyelim
        olcumler, okuma_hatasi = {}, type(hata).__name__
    for saglayici in SAGLAYICILAR:
        # Kurulu olmayan aracın kotası sorulmaz: eksik araç yukarıda zaten uyarıldı.
        if saglayici in arac_sonuclari and arac_sonuclari[saglayici]["status"] != "ok":
            continue
        if okuma_hatasi:
            sonuclar.append({"status": "warn", "name": f"Quota ({saglayici})",
                             "detail": f"event log could not be read ({okuma_hatasi}); see the Event log line"})
            continue
        sonuclar.append(denetle(f"Quota ({saglayici})", lambda saglayici=saglayici: kota(saglayici, olcumler)))
    if arac_sonuclari["agy"]["status"] == "ok":
        sonuclar.append(denetle("agy permissions", agy_izinleri))

    def kabuklar():
        for yol in betik_listesi() if betikler is None else betikler:
            yol = Path(yol)
            ad = str(yol.relative_to(KOK)) if KOK in yol.parents else str(yol)
            sonuclar.append(denetle(f"Shell {ad}", lambda yol=yol: kabuk_betigi(yol)))
        return "ok", "shell scripts located"

    kesif = denetle("Hook scripts", kabuklar)
    if kesif["status"] != "ok":
        sonuclar.append(kesif)
    return sonuclar


def ana(argumanlar=None, betikler=None):
    ayristirici = argparse.ArgumentParser(description="Check the polycrew setup without changing anything.")
    ayristirici.add_argument("--project", default=".", metavar="DIR", help="project folder (default: current folder)")
    ayristirici.add_argument("--json", action="store_true", help="print only the check list as JSON")
    secenekler = ayristirici.parse_args(argumanlar)
    sonuclar = raporla(secenekler.project, betikler)
    if secenekler.json:
        print(json.dumps(sonuclar, ensure_ascii=False))
    else:
        for sonuc in sonuclar:
            print(f"{sonuc['status']} {sonuc['name']}: {sonuc['detail']}")
        sayilar = {durum: sum(s["status"] == durum for s in sonuclar) for durum in ("ok", "warn", "fail")}
        print(f"Summary: {sayilar['ok']} ok, {sayilar['warn']} warn, {sayilar['fail']} fail")
    return int(any(sonuc["status"] == "fail" for sonuc in sonuclar))


if __name__ == "__main__":
    sys.exit(ana())
