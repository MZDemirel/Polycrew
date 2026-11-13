#!/usr/bin/env python3
"""polycrew kota kuralları: tek kaynak (0018).

``watch.py``, ``roster.py``, ``doctor.py``, ``claude-quota.py``, ``claude-statusline.py`` ve
``external-agent.sh`` aynı kuralları buradan alır:

- eski grup ve pencere adları (agy'nin ham adları) → günlükteki ad;
- işçi → kota kovası (Codex, agy grubu, Claude'un genel ve model başına haftalık kovası);
- sıfırlanma zamanı (önce ``yenilenir_epoch``; eski olaylarda kısaltılmış metin: agy UTC, öbürleri yerel);
- tazelik: sıfırlanma geçtiyse ya da okuma penceresinden eskiyse (5 saatte 5 saat, haftada 1 gün) eski;
- yazım: içeriği değişmeyen okuma yeniden yazılmaz (günlüğün çoğu tekrar eden kota olayıydı).

Claude kotası masaüstü uygulamasından kendiliğinden (0019): uygulama ``plan-usage-history.json``'a
15 dakikada bir 5 saat ve 7 gün yüzdesini yazar. Belgelenmemiş bir iç dosyadır: okunamazsa ya da biçimi
değişirse hiçbir şey yazılmaz, PM adımı (claude-quota.py) ve statusline yine çalışır.

Komut:
  quota.py record <kovalar.json> [...]   dosyalardaki kovaları tek ``kota`` olayı olarak yazar,
                                         değişmediyse yazmaz (external-agent.sh quota)
  quota.py desktop                       masaüstü uygulamasının son Claude okumasını yazar (değiştiyse)
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
    # Sıfırlanma anı imzaya girer (yeni pencere = yeni okuma); yalnız kullanılmayan agy penceresinde girmez,
    # onun sıfırlanması her okumada "şimdi + 5 saat"tir, kayar. Ölçüm zamanı yalnız Codex'te girer.
    kayan = kova.get("saglayici") == "agy" and not kova.get("kullanilan")
    atla = ({"yenilenir", "yenilenir_epoch"} if kayan else set()) | (
        set() if kova.get("saglayici") == "codex" else {"olcum"})
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
    yol.parent.mkdir(parents=True, exist_ok=True)
    # Okuma, karşılaştırma, olay ve durum yazımı tek kilit altında: statusline ile quota aynı anda yazabilir.
    with olay.kilit(yol):
        return _kaydet(yol, kovalar, yeniden, simdi, ek)


def _kaydet(yol: Path, kovalar: list[dict], yeniden: float, simdi: float, ek: dict) -> bool:
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
        durum[anahtar(k)] = {"imza": _imza(k), "ts": simdi, "yenilenir_epoch": k.get("yenilenir_epoch"),
                             "olcum": zaman(k.get("olcum"))}
    try:
        gecici = yol.with_name(yol.name + f".{os.getpid()}")
        gecici.write_text(json.dumps(durum, ensure_ascii=False), encoding="utf-8")
        os.replace(gecici, yol)
    except OSError:
        pass
    return True


# --- masaüstü uygulaması (0019) ---

MASAUSTU_PENCERE = {"fh": "5 saat", "sd": "hafta"}
MASAUSTU_EN_ESKI = 3 * 3600.0  # saniye: bundan eski örnek yazılmaz (uygulama kapalıyken dosya donar)


def masaustu_dosyasi() -> Path | None:
    ozel = os.environ.get("POLYCREW_DESKTOP_USAGE")
    if ozel:
        return Path(ozel)
    ev = Path(os.path.expanduser("~"))
    for aday in (ev / ".config" / "Claude", ev / "Library" / "Application Support" / "Claude"):
        if (aday / "plan-usage-history.json").is_file():
            return aday / "plan-usage-history.json"
    return None


def _kurulus() -> str | None:
    """Claude Code'un oturum açtığı kuruluş (``~/.claude.json``); yoksa None (bütün örnekler)."""
    if os.environ.get("POLYCREW_DESKTOP_USAGE"):
        return os.environ.get("POLYCREW_DESKTOP_ORG") or None
    try:
        hesap = json.loads(Path(os.path.expanduser("~/.claude.json")).read_text(encoding="utf-8")).get("oauthAccount")
        kimlik = hesap.get("organizationUuid") if isinstance(hesap, dict) else None
        return kimlik if isinstance(kimlik, str) and kimlik else None
    except (OSError, ValueError, AttributeError):
        return None


def masaustu_kovalari(simdi: float | None = None) -> list[dict]:
    """Masaüstü uygulamasının en yeni örneğinden Claude kovaları; okunamazsa boş liste.

    Örnekte sıfırlanma anı yoktur: aynı pencerenin son yazılan okumasında (PM ya da statusline) sıfırlanma
    hâlâ ilerideyse o an taşınır; geçmişse ya da yoksa sıfırlanma boş kalır, tazeliğe yaş karar verir.
    """
    simdi = time.time() if simdi is None else simdi
    yol = masaustu_dosyasi()
    if yol is None:
        return []
    try:
        veri = json.loads(yol.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    ornekler = veri.get("samples") if isinstance(veri, dict) else None
    if not isinstance(ornekler, list):
        return []
    kurulus = _kurulus()
    en_yeni = None
    for o in ornekler:
        if not isinstance(o, dict) or not isinstance(o.get("u"), dict):
            continue
        if kurulus and o.get("org") not in (None, kurulus):
            continue
        t = o.get("t")
        if not isinstance(t, (int, float)) or isinstance(t, bool) or not math.isfinite(t):
            continue
        if en_yeni is None or t > en_yeni["t"]:
            en_yeni = o
    if en_yeni is None:
        return []
    olcum = en_yeni["t"] / 1000.0
    if not simdi - MASAUSTU_EN_ESKI <= olcum <= simdi + 300:
        return []
    try:
        durum = json.loads(durum_dosyasi().read_text(encoding="utf-8"))
        if not isinstance(durum, dict):
            durum = {}
    except (OSError, ValueError):
        durum = {}
    kovalar = []
    for alan, pencere in MASAUSTU_PENCERE.items():
        deger = en_yeni["u"].get(alan)
        if not isinstance(deger, (int, float)) or isinstance(deger, bool) or not 0 <= deger <= 100:
            continue
        kova = {"saglayici": "claude", "grup": "Claude", "pencere": pencere, "kullanilan": deger,
                "olcum": datetime.fromtimestamp(olcum).astimezone().isoformat(), "kaynak": "desktop"}
        once = durum.get(f"claude|Claude|{pencere}")
        epoch = once.get("yenilenir_epoch") if isinstance(once, dict) else None
        if isinstance(epoch, (int, float)) and not isinstance(epoch, bool) and epoch > max(simdi, olcum):
            kova["yenilenir_epoch"] = float(epoch)
            kova["yenilenir"] = datetime.fromtimestamp(epoch).strftime("%m-%d %H:%M")
        kovalar.append(kova)
    return kovalar


def masaustu_kaydet(simdi: float | None = None) -> bool:
    """Masaüstü okumasını yazar; daha yeni bir Claude okuması zaten yazılmışsa ya da değişmediyse yazmaz.
    Hiçbir hatada istisna atmaz (kancadan çağrılır)."""
    try:
        kovalar = masaustu_kovalari(simdi)
        if not kovalar:
            return False
        try:
            durum = json.loads(durum_dosyasi().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            durum = {}
        # Statusline ya da PM daha yeni ölçtüyse eski masaüstü örneği onu ezmesin.
        yeni = []
        for k in kovalar:
            once = durum.get(f"claude|Claude|{k['pencere']}") if isinstance(durum, dict) else None
            once_olcum = once.get("olcum") if isinstance(once, dict) else None
            if isinstance(once_olcum, (int, float)) and once_olcum > zaman(k["olcum"]):
                continue
            yeni.append(k)
        return kaydet(yeni, kaynak="claude") if yeni else False
    except Exception:  # noqa: BLE001 - kota bir ipucudur; kanca ve sayfa asla düşmez
        return False


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
    if argv == ["desktop"]:
        masaustu_kaydet()
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
