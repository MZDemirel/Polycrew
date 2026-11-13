#!/usr/bin/env python3
"""polycrew olay günlüğü ve puan defteri (karar 0003).

İki dosya:
- Olay günlüğü: ``${XDG_CACHE_HOME:-~/.cache}/polycrew/olaylar.jsonl`` (``POLYCREW_EVENTS`` ile
  değişir), satır başına bir JSON olay.
- Puan defteri: ``${XDG_DATA_HOME:-~/.local/share}/polycrew/puanlar.jsonl`` (``POLYCREW_SCORES`` ile
  değişir), kalıcı notlar.

Komut satırı İngilizcedir; yazılan JSON alanları ve dosya adları Türkçe kalır (karar 0007). Eski
ortam değişkenleri (``POLYCREW_OLAYLAR``, ``POLYCREW_PUANLAR``) yedek olarak okunur.

Kullanım:
- **Kanca** (argümansız, stdin'de Claude Code'un kanca yükü): PreToolUse, SubagentStart, SubagentStop.
  Yalnız polycrew düzenindeki projede yazar (not dosyası proje klasöründe ya da üstünde);
  ``POLYCREW_WATCH_ALL=1`` her projeyi yazar (0013).
- **Komut:**
  - ``events.py write <tur> anahtar=değer ...``
  - ``events.py overlap <id> <kaynak> <başlangıç ts>``: aynı aracın çakışan koşusu varsa ``1 <kimlikler>``,
    yoksa ``0`` (0010, kimlikler 0014)
  - ``events.py score <id> <1-5> [reason] [--worker ...] [--role ...] [--field ...] [--difficulty ...] [--quota ...] [--duration ...] [--fixes ...] [--project ...]``
    Başarıda tek satır onay yazar. 3'ün altındaki puan, olay günlüğünün yanındaki
    ``<günlük>-tuzak-adaylari.jsonl`` dosyasına da bir satır yazar (aynı işin yeni puanı eskisinin yerine
    geçer); ``roster.py summary`` bunları öneri olarak listeler.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

try:
    import fcntl
except ImportError:  # Windows'ta (WSL dışı) kilit yok; yazım yine çalışır
    fcntl = None

KISA = 400  # karakter: ham yükteki uzun metinler (istem, son mesaj) bu kadar kalır
NOT_DOSYALARI = ("NEXT_SESSION.md", "SONRAKI_OTURUM.md")  # session_start.sh ile aynı (0007)
EN_COK_MB = 10  # 0013: günlük bunu aşınca son yarısı kalır (POLYCREW_EVENTS_MAX_MB, 0 kapatır)

# 0007: komut satırı bayrağı → günlükteki alan adı.
BAYRAK = {"worker": "isci", "role": "rol", "field": "alan", "difficulty": "zorluk",
          "quota": "kota", "duration": "sure", "fixes": "duzeltme", "project": "proje"}
# 0007: 0.5.0 öncesinin değerleri okurken yeni ada çevrilir; dosyalar değişmez.
ESKI_ROL = {"lider": "lead", "gelistirici": "developer", "gozden-gecirici": "reviewer",
            "sanatci": "artist", "tasarimci": "designer", "arastirmaci": "researcher",
            "gorsel-okuma": "image-reading", "resim": "image-generation"}
ESKI_ALAN = {"sanat": "art", "arastirma": "research", "inceleme": "review", "tasarim": "design",
             "betik": "script"}
ESKI_ZORLUK = {"K": "E", "O": "M", "Z": "H", "hafif": "E", "orta": "M", "agir": "H"}


# 0008: Claude rollerinde işçi adı model sürümünü taşır. Bu tarihten önceki sürümsüz satırlar,
# o dönemin transkriptlerinin gösterdiği sürüm olarak okunur.
SURUM_SINIRI = 1791763200  # 2026-10-12 00:00 UTC
ESKI_SURUM = {"sonnet": "sonnet-5-5", "opus": "opus-5-5"}
TRANSKRIPT_SATIR = 400  # model aranırken okunan en çok satır


def transkript_modeli(yol) -> str | None:
    """Agent transkriptinin başından gerçek model kimliği (``claude-sonnet-5-5``); yoksa None."""
    try:
        with open(yol, encoding="utf-8", errors="ignore") as f:
            for i, satir in enumerate(f):
                if i >= TRANSKRIPT_SATIR:
                    break
                try:
                    m = (json.loads(satir).get("message") or {}).get("model")
                except (ValueError, AttributeError):
                    continue
                if isinstance(m, str) and m and not m.startswith("<"):
                    return m
    except (OSError, TypeError):
        pass
    return None


def surumlu_isci(isci: str, model: str | None) -> str:
    """``claude/developer/sonnet`` + ``claude-sonnet-5-5`` → ``claude/developer/sonnet-5-5``."""
    parcalar = isci.split("/")
    if not model or len(parcalar) != 3 or parcalar[0] != "claude" or any(c.isdigit() for c in parcalar[2]):
        return isci
    kisa = model[len("claude-"):] if model.startswith("claude-") else model
    if not kisa.startswith(parcalar[2]):
        return isci  # verilen ad başka bir aile; kullanıcının yazdığına dokunma
    return "/".join([*parcalar[:2], kisa])


CAKISMA_PENCERESI = 6 * 3600.0  # saniye: bundan eski, bitişi gelmemiş koşu çakışma sayılmaz


def _olaylar() -> list[dict]:
    out = []
    try:
        with open(dosya(), encoding="utf-8", errors="ignore") as f:
            for satir in f:
                try:
                    e = json.loads(satir)
                except ValueError:
                    continue
                if isinstance(e, dict):
                    out.append(e)
    except OSError:
        pass
    return out


def cakisan_var(is_id: str, kaynak: str, baslangic: float, simdi: float | None = None) -> bool:
    """Aynı aracın başka bir koşusu [baslangic, simdi] aralığıyla çakıştı mı (0010)?"""
    return bool(cakisanlar(is_id, kaynak, baslangic, simdi))


def cakisanlar(is_id: str, kaynak: str, baslangic: float, simdi: float | None = None) -> list[str]:
    """[baslangic, simdi] aralığıyla çakışan aynı aracın koşuları (0014: ortak fark için kimlikler)."""
    simdi = time.time() if simdi is None else simdi
    basla, bitis = {}, {}
    for e in _olaylar():
        if e.get("kaynak") != kaynak or str(e.get("id")) == str(is_id):
            continue
        if e.get("tur") == "isci_basladi":
            basla[str(e.get("id"))] = float(e.get("ts") or 0)
        elif e.get("tur") == "isci_bitti":
            bitis[str(e.get("id"))] = float(e.get("ts") or 0)
    bulunan = []
    for kimlik, b in basla.items():
        if b > simdi or b < baslangic - CAKISMA_PENCERESI:
            continue
        if bitis.get(kimlik, simdi) >= baslangic:
            bulunan.append(kimlik)
    return bulunan


def is_bilgisi(is_id: str) -> dict:
    """Bir işin ölçülmüş süresi ve kotası (0010): dış işçide ``isci_bitti`` olayından, Claude
    agent'ında başlangıç ve bitişten. Bulunamayan alan sözlükte olmaz."""
    bilgi: dict = {}
    for e in _olaylar():
        if e.get("tur") == "isci_bitti" and str(e.get("id")) == str(is_id):
            if isinstance(e.get("sure_sn"), (int, float)):
                bilgi["sure"] = e["sure_sn"]
            if isinstance(e.get("kota"), (int, float)):
                bilgi["kota"] = e["kota"]
            if isinstance(e.get("kota_ortak"), (int, float)):
                bilgi["kota_ortak"] = e["kota_ortak"]  # 0014: çakışan koşularla birlikte; maliyete girmez
    if "sure" not in bilgi:
        ts = {e.get("tur"): e.get("ts") for e in _olaylar()
              if str(e.get("id")) == str(is_id) and e.get("tur") in ("agent_basladi", "agent_bitti")}
        if isinstance(ts.get("agent_basladi"), (int, float)) and isinstance(ts.get("agent_bitti"), (int, float)):
            bilgi["sure"] = round(ts["agent_bitti"] - ts["agent_basladi"], 1)
    if "sure" not in bilgi:
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "watch"))
            import watch  # tembel: kanca yolunda yüklenmez

            ham = _olaylar()
            for e in ham:
                if e.get("rol"):
                    e["rol"] = rol_adi(e["rol"])
            # Kimlik agent kimliği de olabilir: o agent'ın biten olayından işi bul.
            for i in watch.birlestir([e for e in ham if "tur" in e])["isler"]:
                if str(i.get("id")) == str(is_id) and i.get("kaynak") == "claude":
                    if i.get("baslangic") is not None and i.get("bitis") is not None:
                        bilgi["sure"] = round(i["bitis"] - i["baslangic"], 1)
        except Exception:  # noqa: BLE001 - puan yazmak süreye bağlı değildir
            pass
    return bilgi


def is_modeli(is_id: str) -> str | None:
    """Bir Claude işinin modelini olay günlüğünden bulur (kimlik agent kimliği ya da tool_use_id)."""
    try:
        # Önce doğrudan: bu kimlikle biten agent olayı (agent kimliği verildiyse).
        with open(dosya(), encoding="utf-8", errors="ignore") as f:
            for satir in f:
                try:
                    e = json.loads(satir)
                except ValueError:
                    continue
                if e.get("tur") == "agent_bitti" and str(e.get("id")) == str(is_id):
                    m = e.get("model") or transkript_modeli(e.get("transkript"))
                    if m:
                        return m
    except OSError:
        pass
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "watch"))
        import watch  # tembel: kanca yolunda yüklenmez

        for i in watch.birlestir(watch.oku())["isler"]:
            if str(i.get("id")) == str(is_id):
                m = i.get("model")
                if isinstance(m, str) and any(c.isdigit() for c in m):
                    return m
                return transkript_modeli(i.get("transkript"))
    except Exception:  # noqa: BLE001 - puan yazmak modele bağlı değildir
        pass
    return None


def rol_adi(rol, onek: bool = True):
    """Eski rol adını yenisine çevirir; ``onek=False`` ise ``polycrew:`` önekini atar."""
    if not isinstance(rol, str):
        return rol
    on, ayrac, ad = rol.rpartition(":")
    ad = ESKI_ROL.get(ad, ad)
    if on == "polycrew" and not onek:
        return ad
    return f"{on}{ayrac}{ad}"


def kayit_adlari(kayit: dict) -> dict:
    """Bir puan kaydının rol, alan, zorluk ve işçi değerlerini yeni adlara çevirir (kopya döner)."""
    k = dict(kayit)
    if k.get("rol"):
        k["rol"] = rol_adi(k["rol"], onek=False)
    if isinstance(k.get("alan"), str):
        k["alan"] = ESKI_ALAN.get(k["alan"], k["alan"])
    if isinstance(k.get("zorluk"), str):
        k["zorluk"] = ESKI_ZORLUK.get(k["zorluk"], k["zorluk"])
    if isinstance(k.get("isci"), str):
        parcalar = [ESKI_ROL.get(p, p) for p in k["isci"].split("/")]
        try:
            eski = float(k.get("ts")) < SURUM_SINIRI
        except (ValueError, TypeError):
            eski = False
        if eski and len(parcalar) == 3 and parcalar[0] == "claude":
            parcalar[2] = ESKI_SURUM.get(parcalar[2], parcalar[2])
        k["isci"] = "/".join(parcalar)
    return k


def dosya() -> Path:
    yol = os.environ.get("POLYCREW_EVENTS") or os.environ.get("POLYCREW_OLAYLAR")
    if yol:
        return Path(yol)
    kok = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return Path(kok) / "polycrew" / "olaylar.jsonl"


def defter_dosyasi() -> Path:
    yol = os.environ.get("POLYCREW_SCORES") or os.environ.get("POLYCREW_PUANLAR")
    if yol:
        return Path(yol)
    kok = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return Path(kok) / "polycrew" / "puanlar.jsonl"


@contextmanager
def kilit(yol: Path):
    """0018: ekleme ve kırpma aynı kilidi alır; yoksa kırpma arada eklenen satırı silebilirdi."""
    if fcntl is None:
        yield
        return
    try:
        tutamak = open(yol.with_name(yol.name + ".lock"), "a")
    except OSError:
        yield  # kilit dosyası açılamazsa eski davranış
        return
    with tutamak:
        try:
            fcntl.flock(tutamak, fcntl.LOCK_EX)
        except OSError:
            pass
        yield


def yaz(olay: dict) -> dict:
    if "ts" not in olay:
        olay = {"ts": round(time.time(), 3), **olay}
    yol = dosya()
    yol.parent.mkdir(parents=True, exist_ok=True)
    with kilit(yol):
        with open(yol, "a", encoding="utf-8") as f:
            f.write(json.dumps(olay, ensure_ascii=False) + "\n")
        try:
            kirp(yol)
        except OSError:
            pass  # bakım işi; puanın deftere yazılmasını asla durdurmaz
    return olay


def kirp(yol: Path) -> None:
    """0013: günlük sınırı aşınca en yeni satırlardan sınırın yarısı kalır (silinmez, solar).
    ``yaz`` bunu kilit altında çağırır (0018)."""
    try:
        sinir = float(os.environ.get("POLYCREW_EVENTS_MAX_MB") or EN_COK_MB) * 1024 * 1024
    except ValueError:
        sinir = EN_COK_MB * 1024 * 1024
    if sinir <= 0 or yol.stat().st_size <= sinir:
        return
    kalan, toplam = [], 0
    with open(yol, "rb") as f:
        satirlar = f.readlines()
    for satir in reversed(satirlar):
        toplam += len(satir)
        if toplam > sinir / 2:
            break
        kalan.append(satir)
    tutamak, gecici = tempfile.mkstemp(dir=yol.parent, prefix=yol.name + ".", suffix=".kirp")
    try:
        with os.fdopen(tutamak, "wb") as f:
            f.writelines(reversed(kalan))
        os.replace(gecici, yol)
    finally:
        if os.path.exists(gecici):
            os.unlink(gecici)


def proje_adi(yol) -> str | None:
    """Klasör yolundan proje adı: worktree'ler ana projelerine sayılır (0014)."""
    if not yol:
        return None
    kok = str(yol).rstrip("/").split("/.claude/worktrees/")[0]
    return os.path.basename(kok) or None


def duzen_var(yuk: dict) -> bool:
    """0013: kanca yalnız polycrew düzenini kullanan projede yazar (not dosyası klasörde ya da üstünde)."""
    if os.environ.get("POLYCREW_WATCH_ALL") == "1":
        return True
    for dizin in (os.environ.get("CLAUDE_PROJECT_DIR"), yuk.get("cwd")):
        if not dizin:
            continue
        # Sembolik bağdaki alt klasör için hem yazıldığı hem çözüldüğü yolun üstlerine bakılır.
        ham = Path(os.path.abspath(os.path.expanduser(dizin)))
        for yol in (ham, ham.resolve()):
            for d in (yol, *yol.parents):
                if any((d / ad).is_file() for ad in NOT_DOSYALARI):
                    return True
    return False


TUZAK_ESIGI = 3  # bundan düşük puan "tuzak adayı" olur
TUZAK_SAKLAMA = 90 * 86400  # saniye: bundan eski aday yeniden yazımda düşer (özet zaten son 30 günü gösterir)
TUZAK_ALANLARI = ("ts", "proje", "isci", "rol", "alan", "zorluk", "not", "gerekce", "id")


def adaylar_dosyasi() -> Path:
    """Tuzak adayları dosyası: olay günlüğünün yanında (POLYCREW_EVENTS'i izler, testler ayrı kalır)."""
    yol = dosya()
    return yol.with_name(f"{yol.stem}-tuzak-adaylari.jsonl")


def aday_guncelle(kayit: dict) -> None:
    """Düşük puanı tuzak adayları dosyasına yazar; aynı işin (proje + id) yeni puanı eskisinin yerine geçer,
    yeni puan eşik ve üstüyse eski aday silinir. Yalnız öneridir: hiçbir şey bunu kural diye okumaz."""
    try:
        yol = adaylar_dosyasi()
        yol.parent.mkdir(parents=True, exist_ok=True)
        # Paralel iki puan aynı dosyayı okuyup birbirinin adayını ezmesin: oku-yaz arası kilitli.
        with open(str(yol) + ".kilit", "w") as kilit:
            try:
                import fcntl
                fcntl.flock(kilit, fcntl.LOCK_EX)
            except (ImportError, OSError):
                pass  # kilit yoksa (Windows) eski davranış: son yazan kazanır
            _aday_yaz(yol, kayit)
    except OSError:
        pass  # öneri dosyası puanın yazılmasını asla durdurmaz


def _aday_yaz(yol: Path, kayit: dict) -> None:
    anahtar = (str(kayit.get("proje")), str(kayit.get("id")))
    puan = kayit.get("not")
    dusuk = isinstance(puan, (int, float)) and not isinstance(puan, bool) and puan < TUZAK_ESIGI
    kalan, degisti = [], False
    if yol.exists():
        for satir in yol.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                a = json.loads(satir)
            except ValueError:
                a = None
            if not isinstance(a, dict):
                degisti = degisti or bool(satir.strip())
                continue
            ts = a.get("ts")
            if (str(a.get("proje")), str(a.get("id"))) == anahtar:
                degisti = True
            elif isinstance(ts, (int, float)) and not isinstance(ts, bool) and ts < time.time() - TUZAK_SAKLAMA:
                degisti = True  # eskimiş aday: dosya sınırsız büyümesin
            else:
                kalan.append(satir)
    if not dusuk and not degisti:
        return
    if dusuk:
        kalan.append(json.dumps({k: kayit.get(k) for k in TUZAK_ALANLARI}, ensure_ascii=False))
    tutamak, gecici = tempfile.mkstemp(dir=yol.parent, prefix=yol.name + ".", suffix=".tmp")
    try:
        with os.fdopen(tutamak, "w", encoding="utf-8") as f:
            f.write("".join(satir + "\n" for satir in kalan))
        os.replace(gecici, yol)
    finally:
        if os.path.exists(gecici):
            os.unlink(gecici)


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
            **({"model": m} if ad == "SubagentStop" and (m := transkript_modeli(yuk.get("agent_transcript_path"))) else {}),
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

    # Bayrakları ekle (İngilizce bayrak günlükteki alan adına çevrilir)
    bayraklar = {BAYRAK.get(k, k): v for k, v in bayraklar.items()}
    for k, v in bayraklar.items():
        if k in ("kota", "sure", "duzeltme"):
            olay[k] = _sayi(v)
        else:
            olay[k] = v

    # 0010: elle verilmediyse ölçülmüş süre ve kota kendiliğinden yazılır.
    for alan, deger in is_bilgisi(is_id).items():
        olay.setdefault(alan, deger)

    deftere_yazilsin = "isci" in bayraklar and bool(bayraklar["isci"])
    if deftere_yazilsin and olay["isci"].startswith("claude/"):
        surumlu = surumlu_isci(olay["isci"], is_modeli(is_id))
        if surumlu == olay["isci"] and not any(c.isdigit() for c in olay["isci"].rsplit("/", 1)[-1]):
            print(f"model version not found for {is_id}; write it in --worker (e.g. claude/developer/sonnet-5-5)",
                  file=sys.stderr)
        olay["isci"] = surumlu
    if "proje" not in olay:
        olay["proje"] = proje_adi(os.getcwd())  # 0014: worktree'de ana proje; sayfanın süzgeci de bunu bekler

    return olay, deftere_yazilsin


def puan_isle(argv: list[str]) -> int:
    olay, deftere_yaz = puan_ayristir(argv)
    if not olay:
        print("Usage: events.py score <id> <1-5> [reason] [--worker ...] ...", file=sys.stderr)
        return 2
    olay_kaydi = yaz(olay)
    if deftere_yaz:
        defter_yaz(olay_kaydi)
    aday_guncelle(olay_kaydi)
    print(f"Scored {olay_kaydi['id']}: {olay_kaydi['not']} (worker {olay_kaydi.get('isci') or '-'})")  # 0014
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        try:
            yuk = json.load(sys.stdin)
            olay = kancadan(yuk)
            if olay and duzen_var(yuk):
                yaz(olay)
        except Exception:  # noqa: BLE001 - bir kanca oturumu asla durdurmaz
            pass
        return 0
    if argv[0] == "write" and len(argv) >= 2:
        olay = {"tur": argv[1]}
        for parca in argv[2:]:
            anahtar, _, deger = parca.partition("=")
            olay[anahtar] = _deger(deger)
        yaz(olay)
        return 0
    if argv[0] == "overlap" and len(argv) == 4:
        bulunan = cakisanlar(argv[1], argv[2], float(argv[3]))
        print(f"1 {','.join(bulunan)}" if bulunan else 0)
        return 0
    if argv[0] == "score" and len(argv) >= 3:
        return puan_isle(argv[1:])
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
