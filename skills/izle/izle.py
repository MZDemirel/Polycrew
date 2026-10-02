#!/usr/bin/env python3
"""polycrew izle: takımın agent'larını ve dış işçilerini canlı gösteren yerel sayfa (karar 0003).

    izle.py [--port 8770]                       canlı sayfa: http://localhost:8770
    izle.py rapor [--saat 24] --cikti x.html    durağan rapor (veri gömülü; Artifact olarak yayımlanır)

Olaylar ``hooks/olay.py``'nin yazdığı günlükten okunur. Yalnız standart kütüphane.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK.parent.parent / "hooks"))
import olay  # noqa: E402

SAYFA = KOK / "sayfa.html"
DIS_AJAN = KOK.parent / "dis-ajan" / "dis-ajan.sh"
ESLESME = 180.0  # saniye: bir SubagentStart, bu kadar önceki aynı roldeki başlatmaya bağlanır
ESKI = 6 * 3600.0  # saniye: bitişi gelmeyen iş bu kadar sonra "bilinmiyor"
KOTA_ONBELLEK = 60.0
RAPOR_SINIR = 20000  # karakter


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
            out.append(e)
    return out


def _saglayici(kaynak: str | None, model: str | None) -> str:
    if kaynak == "codex":
        return "codex"
    if kaynak == "agy":
        return "claude" if model and "claude" in model else "gemini"
    return "claude"


def birlestir(olaylar: list[dict], simdi: float | None = None) -> dict:
    """Olaylardan işler (agent ve dış işçi başına bir kayıt), son kota ve puanlar."""
    simdi = simdi or time.time()
    isler: dict[str, dict] = {}
    agent_kimligi: dict[str, str] = {}  # SubagentStart'ın agent_id'si -> iş anahtarı
    kota = None
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
            **alan,
        }
        isler[anahtar] = i
        return i

    for e in sorted(olaylar, key=lambda e: e.get("ts", 0)):
        tur, ts = e["tur"], e.get("ts", 0)
        if tur == "agent_baslatildi":
            anahtar = str(e.get("id") or f"agent-{ts}")
            yeni(
                anahtar,
                e,
                rol=e.get("rol"),
                model=e.get("model"),
                aciklama=e.get("aciklama"),
                istem=e.get("istem"),
                arka_plan=e.get("arka_plan"),
                baslangic=ts,
            )
        elif tur == "agent_basladi":
            aday = [
                i
                for i in isler.values()
                if i["kaynak"] == "claude"
                and "agent_id" not in i
                and i["baslangic"] is not None
                and 0 <= ts - i["baslangic"] <= ESLESME
                and (not e.get("rol") or i.get("rol") in (e.get("rol"), None))
            ]
            i = max(aday, key=lambda i: i["baslangic"]) if aday else None
            if i is None:
                i = yeni(str(e.get("id") or f"agent-{ts}"), e, rol=e.get("rol"), baslangic=ts)
            i["agent_id"] = e.get("id")
            if e.get("id"):
                agent_kimligi[str(e["id"])] = i["id"]
        elif tur == "agent_bitti":
            anahtar = agent_kimligi.get(str(e.get("id")))
            i = isler.get(anahtar) if anahtar else None
            if i is None:
                i = yeni(str(e.get("id") or f"agent-{ts}"), e, rol=e.get("rol"))
            i.update(bitis=ts, durum="bitti", transkript=e.get("transkript"))
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
            kota = {"ts": ts, "kovalar": e.get("kovalar") or []}
        elif tur == "puan":
            hedef = str(e.get("id"))
            i = isler.get(hedef) or isler.get(agent_kimligi.get(hedef, ""))
            p = {"not": e.get("not"), "gerekce": e.get("gerekce"), "ts": ts}
            if i:
                i["puan"] = p
            else:
                sahipsiz_puan.append({"id": hedef, **p})

    for i in isler.values():
        i["saglayici"] = _saglayici(i["kaynak"], i.get("model"))
        bas = i["baslangic"]
        if i["durum"] == "calisiyor" and bas is not None and simdi - bas > ESKI:
            i["durum"] = "bilinmiyor"
        son = i["bitis"] if i["bitis"] is not None else (simdi if i["durum"] == "calisiyor" else bas)
        i["sure"] = round(son - bas, 1) if bas is not None and son is not None else None

    def sira(i):
        return i["baslangic"] if i["baslangic"] is not None else (i["bitis"] or 0)

    sirali = sorted(isler.values(), key=sira)
    return {"simdi": simdi, "isler": sirali, "kota": kota, "puanlar": sahipsiz_puan}


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


def suz(veri: dict, saat: float | None) -> dict:
    if not saat:
        return veri
    sinir = veri["simdi"] - saat * 3600
    isler = [
        i for i in veri["isler"] if (veri["simdi"] if i["bitis"] is None else i["bitis"]) >= sinir
    ]
    return {**veri, "isler": isler}


def rapor_metni(i: dict) -> str:
    """Bir işin son mesajı: dış işçide ``rapor.md``, Claude agent'ında transkriptin son
    asistan metni."""
    if i.get("kayit"):
        r = Path(i["kayit"]) / "rapor.md"
        if r.exists():
            return r.read_text(encoding="utf-8", errors="ignore")[:RAPOR_SINIR] or "(boş rapor)"
        return "(rapor yok)"
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
        return son[:RAPOR_SINIR] or "(transkriptte metin yok)"
    return "(henüz rapor yok)" if i.get("durum") == "calisiyor" else "(rapor bulunamadı)"


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
        """``dis-ajan.sh kota`` (o da bir ``kota`` olayı yazar); KOTA_ONBELLEK'te bir kez."""
        with self.kilit:
            if time.time() - self.zaman < KOTA_ONBELLEK or not DIS_AJAN.exists():
                return
            self.zaman = time.time()
        threading.Thread(
            target=lambda: subprocess.run(
                ["bash", str(DIS_AJAN), "kota"], capture_output=True, timeout=120, check=False
            ),
            daemon=True,
        ).start()


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
            saat = float(q["saat"]) if q.get("saat") not in (None, "", "0") else None
            self._json(suz(birlestir(oku()), saat))
        elif u.path == "/api/is":
            i = next((i for i in birlestir(oku())["isler"] if i["id"] == q.get("id")), None)
            if i is None:
                self._json({"hata": "iş yok"})
            else:
                self._json({"rapor": rapor_metni(i), "gorev": gorev_metni(i)})
        else:
            self._gonder(b"yok", "text/plain", 404)


def rapor_html(saat: float | None) -> str:
    veri = suz(birlestir(oku()), saat)
    for i in veri["isler"]:
        i["_rapor"] = rapor_metni(i)
        i["_gorev"] = gorev_metni(i)
    gomulu = json.dumps(veri, ensure_ascii=False).replace("</", "<\\/")
    sayfa = SAYFA.read_text(encoding="utf-8")
    return sayfa.replace("/*VERI*/null", gomulu, 1)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("komut", nargs="?", choices=["rapor"])
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--saat", type=float, default=24.0)
    ap.add_argument("--cikti", type=Path)
    a = ap.parse_args(argv)
    if a.komut == "rapor":
        html = rapor_html(a.saat)
        if a.cikti:
            a.cikti.write_text(html, encoding="utf-8")
            print(a.cikti)
        else:
            sys.stdout.write(html)
        return 0
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Sunucu)
    print(f"polycrew izle: http://localhost:{a.port}  (günlük: {olay.dosya()})", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
