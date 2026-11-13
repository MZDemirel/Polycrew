#!/usr/bin/env python3
"""polycrew watch: takımın agent'larını ve dış işçilerini canlı gösteren yerel sayfa (karar 0003).

    watch.py [--port 8770]                      canlı sayfa: http://localhost:8770
    watch.py report [--hours 24] [--lang en|tr] [--project AD | --all-projects] --out x.html
                                                durağan rapor (veri gömülü; Artifact olarak yayımlanır)

Proje süzgeci (0014): sayfa ``?project=<ad>`` ile, rapor varsayılan olarak çalıştırıldığı klasörün
projesiyle süzülür; başka projelerin işleri ve raporları görünmez. Proje adı yolun
``/.claude/worktrees/`` öncesindeki son klasörüdür.

Sayfa İngilizce ve Türkçedir: tarayıcı diline göre açılır, üstteki EN/TR ile ya da ``?lang=`` ile
değişir.

Olaylar ``hooks/events.py``'nin yazdığı günlükten okunur. Yalnız standart kütüphane.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK.parent.parent / "hooks"))
import events as olay  # noqa: E402
import quota as kurallar  # noqa: E402

SAYFA = KOK / "page.html"
DIS_AJAN = KOK.parent / "external-agent" / "external-agent.sh"
ESLESME = 180.0  # saniye: bir SubagentStart, bu kadar önceki aynı roldeki başlatmaya bağlanır
ESKI = 6 * 3600.0  # saniye: bitişi gelmeyen iş bu kadar sonra "bilinmiyor"
KOTA_ONBELLEK = 300.0  # 0018: 60 sn'de günlüğün çoğu kota olayıydı
RAPOR_SINIR = 20000  # karakter


def zaman(deger) -> float | None:
    """ISO ölçümü ya da eski olayların Unix zamanını çöz."""
    try:
        if isinstance(deger, (int, float)):
            return float(deger)
        return datetime.fromisoformat(deger.replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError, AttributeError, OverflowError):
        return None


def kota_kovasi(kova: dict, ts: float, simdi: float) -> dict:
    """Bir kota kovası, sayfa için: ölçüm ve sıfırlanma anı, eski mi ve neden (kurallar hooks/quota.py, 0018)."""
    k = kurallar.adlari_duzelt(kova)
    olcum_ts = zaman(k.get("olcum"))
    if olcum_ts is None:
        olcum_ts = ts
        k["olcum"] = datetime.fromtimestamp(ts).astimezone().isoformat()
    k["olcum_ts"] = olcum_ts
    # 0017: yeni ölçümler kesin sıfırlanma anını taşır; 0018: eski agy metni UTC okunur.
    k["yenilenir_ts"] = kurallar.yenilenme(k, olcum_ts)
    neden = kurallar.eski_neden(k.get("pencere"), olcum_ts, k["yenilenir_ts"], simdi)
    k["eski"] = neden is not None
    k["eski_neden"] = neden
    return k


def _ust_bilgisi(e: dict) -> tuple[str | None, str | None]:
    """Ham kancadaki açık üst kimliği, çağıran agent veya transkript yolu."""
    h = e.get("ham") or {}
    for alan in ("parent_agent_id", "parent_session_id"):
        if h.get(alan):
            return str(h[alan]), f"ham.{alan}"
    if e["tur"] == "agent_baslatildi" and h.get("agent_id"):
        return str(h["agent_id"]), "ham.agent_id"
    yol = str(h.get("transcript_path") or "")
    if "/subagents/agent-" in yol:
        return Path(yol).stem.removeprefix("agent-"), "ham.transcript_path"
    # session_id ana PM oturumuyla ortak olabilir; yalnız bilinen agent kimliğiyle eşleşir.
    if h.get("session_id") or e.get("oturum"):
        return str(h.get("session_id") or e["oturum"]), "ham.session_id"
    return None, None


def oku(yol: Path | None = None) -> list[dict]:
    yol = yol or olay.dosya()
    if not yol.exists():
        return []
    out = []
    for satir in yol.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            e = json.loads(satir)
        except ValueError:
            continue
        if isinstance(e, dict) and "tur" in e:
            if e.get("rol"):
                e["rol"] = olay.rol_adi(e["rol"])  # 0.5.0 öncesinin rol adları (0007)
            out.append(e)
    return out


def _saglayici(kaynak: str | None, model: str | None) -> str:
    """Renk ailesi. agy'deki Claude modeli de dış işçidir: Claude Code agent'ı gibi turuncu görünmez (0014)."""
    if kaynak == "codex":
        return "codex"
    if kaynak == "agy":
        return "gemini"
    return "claude"


proje_adi = olay.proje_adi  # 0014: tek kaynak events.py (puan da aynı adı yazar)


def birlestir(olaylar: list[dict], simdi: float | None = None) -> dict:
    """Olaylardan işler, anahtar başına son kota, agent ağacı ve puanlar."""
    simdi = time.time() if simdi is None else simdi
    isler: dict[str, dict] = {}
    agent_kimligi: dict[str, str] = {}  # SubagentStart'ın agent_id'si -> iş anahtarı
    kovalar: dict[tuple, dict] = {}
    kota_ts = None
    sahipsiz_puan = []

    def yeni(anahtar: str, e: dict, **alan) -> dict:
        i = {
            "id": anahtar,
            "kaynak": e.get("kaynak", "claude"),
            "oturum": e.get("oturum"),
            "baslangic": None,
            "bitis": None,
            "durum": "calisiyor",
            "puan": None,
            "ust_id": None,
            "ust_kaynak": None,
            "proje": proje_adi(e.get("cwd") or e.get("klasor")),
            **alan,
        }
        isler[anahtar] = i
        return i

    def bagla(i: dict, e: dict) -> None:
        ust, kaynak = _ust_bilgisi(e)
        oncelik = {"ham.parent_agent_id": 0, "ham.parent_session_id": 1,
                   "ham.agent_id": 2, "ham.transcript_path": 3, "ham.session_id": 4}
        if ust and oncelik[kaynak] <= oncelik.get(i.get("ust_kaynak"), 5):
            i.update(ust_aday=ust, ust_kaynak=kaynak)
        h = e.get("ham") or {}
        for alan in ("agent_session_id", "subagent_session_id"):
            if h.get(alan):
                agent_kimligi[str(h[alan])] = i["id"]
        if not i.get("model"):
            i["model"] = e.get("model") or h.get("model")
        if not i.get("proje"):
            i["proje"] = proje_adi(e.get("cwd"))

    for e in sorted(olaylar, key=lambda e: e.get("ts", 0)):
        tur, ts = e["tur"], e.get("ts", 0)
        if tur == "agent_baslatildi":
            anahtar = str(e.get("id") or f"agent-{ts}")
            i = yeni(
                anahtar,
                e,
                rol=e.get("rol"),
                model=e.get("model"),
                aciklama=e.get("aciklama"),
                istem=e.get("istem"),
                arka_plan=e.get("arka_plan"),
                baslangic=ts,
            )
            bagla(i, e)
        elif tur == "agent_basladi":
            ust, ust_kaynak = _ust_bilgisi(e)
            aday = [
                i
                for i in isler.values()
                if i["kaynak"] == "claude"
                and "agent_id" not in i
                and i["baslangic"] is not None
                and 0 <= ts - i["baslangic"] <= ESLESME
                and (not e.get("rol") or i.get("rol") in (e.get("rol"), None))
                and (not e.get("oturum") or not i.get("oturum") or i["oturum"] == e["oturum"])
                and (ust_kaynak == "ham.session_id" or not ust or not i.get("ust_aday") or i["ust_aday"] == ust)
            ]
            i = isler.get(agent_kimligi.get(str(e.get("id")), ""))
            if i is not None:
                # SendMessage ile sürdürülen agent yeniden başlar: yine çalışıyor.
                i.update(durum="calisiyor", bitis=None)
            if i is None:
                # Paralel başlatılanlar başlatılma sırasıyla başlar: en eski eşleşmemiş başlatma.
                i = min(aday, key=lambda i: i["baslangic"]) if aday else None
            if i is None:
                i = yeni(str(e.get("id") or f"agent-{ts}"), e, rol=e.get("rol"), baslangic=ts)
            i["agent_id"] = e.get("id")
            if e.get("id"):
                agent_kimligi[str(e["id"])] = i["id"]
            bagla(i, e)
        elif tur == "agent_bitti":
            ust, ust_kaynak = _ust_bilgisi(e)
            anahtar = agent_kimligi.get(str(e.get("id")))
            i = isler.get(anahtar) if anahtar else isler.get(str(e.get("id")))
            if i is None:
                # Başlama olayı gelmediyse: aynı roldeki, hâlâ çalışan en son başlatma.
                acik = [
                    j
                    for j in isler.values()
                    if j["kaynak"] == "claude"
                    and j["durum"] == "calisiyor"
                    and j["baslangic"] is not None
                    and "agent_id" not in j
                    and (not e.get("rol") or j.get("rol") == e.get("rol"))
                    and (not e.get("oturum") or not j.get("oturum") or j["oturum"] == e["oturum"])
                    and (ust_kaynak == "ham.session_id" or not ust
                         or not j.get("ust_aday") or j["ust_aday"] == ust)
                ]
                i = max(acik, key=lambda j: j["baslangic"]) if acik else None
            if i is None and not e.get("rol"):
                continue  # harness'in rolsüz iç agent'ı (özet, başlık): bir iş değil
            if i is None:
                i = yeni(str(e.get("id") or f"agent-{ts}"), e, rol=e.get("rol"))
            i.update(bitis=ts, durum="bitti", transkript=e.get("transkript"))
            if e.get("model"):
                i["model"] = e["model"]  # transkriptten okunan gerçek model (0008)
            if e.get("id"):
                agent_kimligi[str(e["id"])] = i["id"]
            bagla(i, e)
        elif tur == "isci_basladi":
            yeni(
                str(e.get("id")),
                e,
                rol=e.get("kip"),
                model=e.get("model"),
                efor=e.get("efor"),
                aciklama=e.get("aciklama"),
                klasor=e.get("klasor"),
                kayit=e.get("kayit"),
                baslangic=ts,
            )
        elif tur == "isci_bitti":
            i = isler.get(str(e.get("id"))) or yeni(str(e.get("id")), e, kayit=e.get("kayit"))
            i.update(
                bitis=ts,
                durum="bitti" if e.get("cikis") in (0, "0") else "hata",
                cikis=e.get("cikis"),
                sure_sn=e.get("sure_sn"),
                token=_token(e.get("kullanim")),
            )
        elif tur == "kota":
            kota_ts = ts
            kovalar_e = e.get("kovalar")
            for k in kovalar_e if isinstance(kovalar_e, list) else []:  # bozuk olay sayfayı düşürmez
                if isinstance(k, dict):
                    k = kurallar.adlari_duzelt(k)  # eski agy adları (aynı kova)
                    anahtar = (k.get("saglayici"), k.get("grup"), k.get("pencere"))
                    okunan = kota_kovasi(k, ts, simdi)  # "yeni" adı bu fonksiyonda iş kurucusudur
                    # 0019: aynı kovaya üç kaynak yazar (masaüstü, statusline, PM); en yeni ölçüm kazanır.
                    if anahtar not in kovalar or okunan["olcum_ts"] >= kovalar[anahtar]["olcum_ts"]:
                        kovalar[anahtar] = okunan
        elif tur == "puan":
            hedef = str(e.get("id"))
            i = isler.get(hedef) or isler.get(agent_kimligi.get(hedef, ""))
            p = {"not": e.get("not"), "gerekce": e.get("gerekce"), "ts": ts, "proje": e.get("proje")}
            if i:
                i["puan"] = p
            else:
                sahipsiz_puan.append({"id": hedef, **p})

    for i in isler.values():
        ust = i.pop("ust_aday", None)
        if i["kaynak"] == "claude" and ust:
            hedef = agent_kimligi.get(ust, ust)
            if hedef in isler and hedef != i["id"]:
                i["ust_id"] = hedef
        if i["ust_id"] is None:
            i["ust_kaynak"] = None
        i["saglayici"] = _saglayici(i["kaynak"], i.get("model"))
        bas = i["baslangic"]
        if i["durum"] == "calisiyor" and bas is not None and simdi - bas > ESKI:
            i["durum"] = "bilinmiyor"
        son = i["bitis"] if i["bitis"] is not None else (simdi if i["durum"] == "calisiyor" else bas)
        i["sure"] = round(son - bas, 1) if bas is not None and son is not None else None

    def sira(i):
        return i["baslangic"] if i["baslangic"] is not None else (i["bitis"] or 0)

    sirali = sorted(isler.values(), key=sira)
    kota = {"ts": kota_ts, "kovalar": list(kovalar.values())} if kota_ts is not None else None
    return {"simdi": simdi, "isler": sirali, "kota": kota, "puanlar": sahipsiz_puan,
            "harita": agent_haritasi(sirali, simdi)}


def agent_haritasi(isler: list[dict], simdi: float) -> dict:
    """Seçili işlerden sanal PM kökü; eksik üst ve döngüler PM'e bağlanır."""
    dugumler = {i["id"]: {**i, "cocuklar": []} for i in isler}
    ustler = {i["id"]: i.get("ust_id") if i["kaynak"] == "claude" else None for i in isler}
    bas = min((i["baslangic"] for i in isler if i["baslangic"] is not None), default=None)
    bit = max((i["bitis"] if i["bitis"] is not None else
               simdi if i["durum"] == "calisiyor" else i["baslangic"] or simdi
               for i in isler), default=simdi)
    pm = {"id": "polycrew-pm", "rol": "PM", "kaynak": "claude", "saglayici": "claude",
          "model": None, "durum": "calisiyor" if any(i["durum"] == "calisiyor" for i in isler)
          else "hata" if any(i["durum"] == "hata" for i in isler)
          else "bilinmiyor" if any(i["durum"] == "bilinmiyor" for i in isler) else "bitti",
          "sure": round(bit - bas, 1) if bas is not None else None, "puan": None,
          "sanal": True, "cocuklar": []}
    for i in isler:
        ust = i.get("ust_id") if i["kaynak"] == "claude" else None
        ziyaret = {i["id"]}
        yol = ust
        while yol in dugumler and yol not in ziyaret:
            ziyaret.add(yol)
            yol = ustler[yol]
        if yol in ziyaret:
            ust = None
        hedef = dugumler.get(ust, pm)
        dugumler[i["id"]]["ust_id"] = hedef["id"]
        hedef["cocuklar"].append(dugumler[i["id"]])
    return pm


def _token(kullanim) -> int | None:
    if not isinstance(kullanim, dict):
        return None
    u = kullanim.get("usage", kullanim)
    if not isinstance(u, dict):
        return None
    if "total_tokens" in u:
        return u["total_tokens"]
    toplam = (u.get("input_tokens") or 0) + (u.get("output_tokens") or 0)
    return toplam or None


def suz(veri: dict, saat: float | None, proje: str | None = None) -> dict:
    """Zaman penceresi ve proje (0014). Bitişi gelmemiş ama çalışmayan (bilinmiyor) iş pencereye
    başlangıcıyla girer; yoksa günler önceki bir iş çizelgeyi günlere yayar. Kota süzülmez."""
    simdi = veri["simdi"]
    isler = veri["isler"]
    projeler = sorted({i["proje"] for i in isler if i.get("proje")})
    if saat:
        sinir = simdi - saat * 3600

        def son(i):
            if i["bitis"] is not None:
                return i["bitis"]
            return simdi if i["durum"] == "calisiyor" else (i["baslangic"] if i["baslangic"] is not None else simdi)

        isler = [i for i in isler if son(i) >= sinir]
    puanlar = veri.get("puanlar", [])
    if proje:
        isler = [i for i in isler if i.get("proje") == proje]
        puanlar = [p for p in puanlar if p.get("proje") == proje]
    return {**veri, "isler": isler, "puanlar": puanlar, "projeler": projeler, "proje": proje or None,
            "harita": agent_haritasi(isler, simdi)}


def rapor_metni(i: dict) -> str:
    """Bir işin son mesajı: dış işçide ``rapor.md``, Claude agent'ında transkriptin son
    asistan metni; yoksa boş (sayfa kendi dilinde "rapor yok" yazar)."""
    if i.get("kayit"):
        r = Path(i["kayit"]) / "rapor.md"
        if r.exists():
            return r.read_text(encoding="utf-8", errors="ignore")[:RAPOR_SINIR]
        return ""
    t = i.get("transkript")
    if t and Path(t).exists():
        son = ""
        for satir in Path(t).read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                e = json.loads(satir)
            except ValueError:
                continue
            m = e.get("message") or {}
            if e.get("type") == "assistant" or m.get("role") == "assistant":
                icerik = m.get("content")
                if isinstance(icerik, str):
                    metin = icerik
                else:
                    metin = "\n".join(
                        p.get("text", "") for p in icerik or [] if isinstance(p, dict)
                    )
                if metin.strip():
                    son = metin
        return son[:RAPOR_SINIR]
    return ""


def gorev_metni(i: dict) -> str:
    if i.get("kayit"):
        g = Path(i["kayit"]) / "gorev.md"
        if g.exists():
            return g.read_text(encoding="utf-8", errors="ignore")[:RAPOR_SINIR]
    return i.get("istem") or ""


class _Kota:
    def __init__(self):
        self.zaman = 0.0
        self.kilit = threading.Lock()

    def tazele(self) -> None:
        """``external-agent.sh quota`` (o da bir ``kota`` olayı yazar); KOTA_ONBELLEK'te bir kez."""
        with self.kilit:
            if time.time() - self.zaman < KOTA_ONBELLEK or not DIS_AJAN.exists():
                return
            self.zaman = time.time()
        def calistir():
            kurallar.masaustu_kaydet()  # 0019: Claude, masaüstü uygulamasından (istisna atmaz)
            try:
                subprocess.run(["bash", str(DIS_AJAN), "quota"], capture_output=True, timeout=120, check=False)
            except (subprocess.TimeoutExpired, OSError):
                pass  # kota bir ipucudur; bir sonraki tazelemede yeniden denenir

        threading.Thread(target=calistir, daemon=True).start()


KOTA = _Kota()


class Sunucu(BaseHTTPRequestHandler):
    def log_message(self, *a):  # sessiz
        pass

    def _gonder(self, govde: bytes, tur: str, kod: int = 200) -> None:
        self.send_response(kod)
        self.send_header("Content-Type", tur)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(govde)))
        self.end_headers()
        self.wfile.write(govde)

    def _json(self, veri) -> None:
        self._gonder(json.dumps(veri, ensure_ascii=False).encode(), "application/json")

    def do_GET(self):  # noqa: N802
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.path == "/":
            self._gonder(SAYFA.read_bytes(), "text/html; charset=utf-8")
        elif u.path == "/api/durum":
            if q.get("kota") == "1":
                KOTA.tazele()
            try:
                saat = float(q["saat"]) if q.get("saat") not in (None, "", "0") else None
            except ValueError:
                saat = None
            if saat is not None and not (math.isfinite(saat) and saat > 0):
                saat = None
            self._json(suz(birlestir(oku()), saat, q.get("proje") or None))
        elif u.path == "/api/is":
            i = next((i for i in birlestir(oku())["isler"] if i["id"] == q.get("id")), None)
            if i is None:
                self._json({"hata": "iş yok"})
            else:
                self._json({"rapor": rapor_metni(i), "gorev": gorev_metni(i)})
        else:
            self._gonder(b"yok", "text/plain", 404)


def rapor_html(saat: float | None, dil: str | None = None, proje: str | None = None) -> str:
    """Durağan rapor; ``dil`` (``en`` ya da ``tr``) verilmezse okuyanın tarayıcı dili. ``proje``
    verilirse yalnız o projenin işleri ve raporları gömülür (0014)."""
    veri = suz(birlestir(oku()), saat, proje)
    veri.pop("projeler", None)  # başka projelerin adları rapora girmez
    if dil:
        veri["dil"] = dil
    for i in veri["isler"]:
        i["_rapor"] = rapor_metni(i)
        i["_gorev"] = gorev_metni(i)
    gomulu = json.dumps(veri, ensure_ascii=False).replace("</", "<\\/")
    sayfa = SAYFA.read_text(encoding="utf-8")
    tarih = datetime.fromtimestamp(veri["simdi"]).strftime("%Y-%m-%d")
    baslik = " · ".join(p for p in ("Polycrew", proje, tarih) if p)
    sayfa = sayfa.replace("<title>Polycrew Team Watch</title>", f"<title>{html.escape(baslik)}</title>", 1)
    if dil:
        sayfa = sayfa.replace('<html lang="en">', f'<html lang="{dil}">', 1)
    return sayfa.replace("/*VERI*/null", gomulu, 1)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("komut", nargs="?", choices=["report"])
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--hours", dest="saat", type=float, default=24.0)
    ap.add_argument("--out", dest="cikti", type=Path)
    ap.add_argument("--lang", dest="dil", choices=["en", "tr"], help="report language (default: the reader's browser)")
    ap.add_argument("--project", dest="proje", help="report: only this project (default: the current folder's project)")
    ap.add_argument("--all-projects", dest="hepsi", action="store_true", help="report: every project in the log")
    a = ap.parse_args(argv)
    if a.komut == "report":
        proje = None if a.hepsi else (a.proje or proje_adi(os.getcwd()))
        metin = rapor_html(a.saat, a.dil, proje)
        if a.cikti:
            a.cikti.write_text(metin, encoding="utf-8")
            print(a.cikti)
        else:
            sys.stdout.write(metin)
        return 0
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Sunucu)
    print(f"polycrew watch: http://localhost:{a.port}  (log: {olay.dosya()})", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
