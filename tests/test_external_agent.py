"""Dış işçi betiğinin koşu yolu, sahte codex ve agy ile uçtan uca (0010).

Gerçek araçlar çağrılmaz: geçici bir PATH'in başına sahte ``codex`` ve ``agy`` konur, HOME geçicidir.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
BETIK = KOK / "skills" / "external-agent" / "external-agent.sh"
OLAY = KOK / "hooks" / "events.py"

# Sahte codex: görevi stdin'den okur, -o dosyasına rapor yazar, yeni bir oturum dosyasına
# FAKE_CODEX_USED yüzdesini bırakır (gerçek codex'in rate_limits kaydı gibi).
SAHTE_CODEX = r'''#!/usr/bin/env python3
import json, os, sys, time
a = sys.argv[1:]
sys.stdin.read()
open(a[a.index("-o") + 1], "w").write("codex raporu")
d = os.path.expanduser("~/.codex/sessions/2026/10/11")
os.makedirs(d, exist_ok=True)
with open(os.path.join(d, "kosu-%d.jsonl" % os.getpid()), "w") as f:
    f.write(json.dumps({"timestamp": "t2", "payload": {"rate_limits": {
        "primary": {"used_percent": float(os.environ["FAKE_CODEX_USED"]), "resets_at": time.time() + 3600},
        "secondary": {"used_percent": 5, "resets_at": 0}}}}) + "\n")
print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 7}}))
'''

# Sahte agy: /quota durum dosyasındaki kalan oranları verir; bir görev koşusu modelin grubundan düşer.
SAHTE_AGY = r'''#!/usr/bin/env python3
import json, os, sys
a = sys.argv[1:]
yol = os.path.expanduser("~/agy_durum.json")
durum = json.load(open(yol))
if a[a.index("-p") + 1] == "/quota":
    print(json.dumps({"command": {"data": {"groups": [
        {"name": "Gemini Models", "buckets": [
            {"window": "5h", "remaining_fraction": durum["gemini"], "reset_time": "2026-10-11T22:00:00Z"}]},
        {"name": "Claude and GPT models", "buckets": [
            {"window": "weekly", "remaining_fraction": durum["claude"], "reset_time": "2026-10-12T10:00:00Z"}]},
    ]}}}))
else:
    model = a[a.index("--model") + 1]
    grup = "claude" if "claude" in model else "gemini"
    durum[grup] = round(durum[grup] - float(os.environ.get("FAKE_AGY_HARCA", "0.04")), 4)
    json.dump(durum, open(yol, "w"))
    print(json.dumps({"response": "agy raporu", "usage": {"t": 1}, "status": "ok"}))
'''


class DisIsciKosuTesti(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.TemporaryDirectory()
        self.ev = Path(self.gecici.name)
        kutu = self.ev / "bin"
        kutu.mkdir()
        for ad, icerik in (("codex", SAHTE_CODEX), ("agy", SAHTE_AGY)):
            (kutu / ad).write_text(icerik, encoding="utf-8")
            (kutu / ad).chmod((kutu / ad).stat().st_mode | stat.S_IXUSR)
        self.is_klasoru = self.ev / "is"
        self.is_klasoru.mkdir()
        self.gorev = self.ev / "gorev.md"
        self.gorev.write_text("# Task: deneme\n\nbir şey yap\n", encoding="utf-8")
        self.gunluk = self.ev / "olaylar.jsonl"
        self.defter = self.ev / "puanlar.jsonl"
        self.env = {
            "PATH": f"{kutu}:{os.path.dirname(sys.executable)}:/usr/bin:/bin",
            "HOME": str(self.ev),
            "EXTERNAL_AGENT_LOG": str(self.ev / "kayit"),
            "POLYCREW_EVENTS": str(self.gunluk),
            "POLYCREW_SCORES": str(self.defter),
            "FAKE_CODEX_USED": "52",
        }
        (self.ev / "agy_durum.json").write_text(json.dumps({"gemini": 0.80, "claude": 0.50}), encoding="utf-8")
        self._codex_oncesi(40)

    def tearDown(self):
        self.gecici.cleanup()

    def _codex_oncesi(self, yuzde, yenilenir=None):
        d = self.ev / ".codex" / "sessions" / "2026" / "10" / "10"
        d.mkdir(parents=True, exist_ok=True)
        f = d / "eski.jsonl"
        f.write_text(json.dumps({"timestamp": "t1", "payload": {"rate_limits": {
            "primary": {"used_percent": yuzde, "resets_at": time.time() + 3600 if yenilenir is None else yenilenir},
            "secondary": {"used_percent": 5, "resets_at": 0}}}}) + "\n", encoding="utf-8")
        eski = time.time() - 3600
        os.utime(f, (eski, eski))

    def kos(self, *argv, **ek):
        return subprocess.run(["bash", str(BETIK), *argv], capture_output=True, text=True, check=False,
                              env={**self.env, **ek})

    def kosu(self, arac, model, **ek):
        r = self.kos(arac, model, "-", "read", str(self.is_klasoru), str(self.gorev), **ek)
        self.assertEqual(r.returncode, 0, r.stderr)
        return Path(r.stdout.strip().splitlines()[-1])

    def olaylar(self, tur):
        return [e for e in map(json.loads, self.gunluk.read_text(encoding="utf-8").splitlines()) if e["tur"] == tur]

    def test_codex_kosusu_kota_farkini_yazar(self):
        kayit = self.kosu("codex", "gpt-x")
        self.assertEqual((kayit / "rapor.md").read_text(), "codex raporu")
        self.assertGreaterEqual(float((kayit / "sure_sn").read_text()), 0)
        self.assertEqual((kayit / "cikis_kodu").read_text().strip(), "0")
        kota = json.loads((kayit / "kota.json").read_text())
        self.assertEqual((kota["once"], kota["sonra"], kota["fark"], kota["pencere"]), (40.0, 52.0, 12.0, "5 saat"))
        bitti = self.olaylar("isci_bitti")[-1]
        self.assertEqual((bitti["id"], bitti["kota"], bitti["kip"] if "kip" in bitti else None),
                         (kayit.name, 12.0, None))
        self.assertEqual(self.olaylar("isci_basladi")[-1]["kip"], "okur")  # şema değişmedi (0007)

        # Puan: kota ve süre elle verilmeden deftere yazılır; elle verilen ezer.
        subprocess.run([sys.executable, str(OLAY), "score", kayit.name, "4", "--worker", "codex/gpt-x/high"],
                       check=True, env=self.env)
        subprocess.run([sys.executable, str(OLAY), "score", kayit.name, "4", "--worker", "codex/gpt-x/high",
                        "--quota", "30", "--duration", "99"], check=True, env=self.env)
        ilk, ikinci = map(json.loads, self.defter.read_text(encoding="utf-8").splitlines())
        self.assertEqual(ilk["kota"], 12.0)
        self.assertEqual(ilk["sure"], bitti["sure_sn"])
        self.assertEqual((ikinci["kota"], ikinci["sure"]), (30, 99))

    def test_agy_modele_gore_gruptan_olcer(self):
        gemini = json.loads((self.kosu("agy", "gemini-3.8-flash-high") / "kota.json").read_text())
        self.assertEqual((gemini["once"], gemini["sonra"], gemini["fark"], gemini["pencere"]), (20.0, 24.0, 4.0, "5 saat"))
        claude = json.loads((self.kosu("agy", "claude-opus-4-6-thinking") / "kota.json").read_text())
        self.assertEqual((claude["once"], claude["sonra"], claude["fark"], claude["pencere"]), (50.0, 54.0, 4.0, "hafta"))

    def test_pencere_yenilenirse_fark_yazilmaz(self):
        kayit = self.kosu("codex", "gpt-x", FAKE_CODEX_USED="3")  # 40 → 3: pencere yenilendi
        kota = json.loads((kayit / "kota.json").read_text())
        self.assertIsNone(kota["fark"])
        self.assertIn("reset", kota["neden"])
        self.assertNotIn("kota", self.olaylar("isci_bitti")[-1])

    def test_eski_pencereden_kalan_olcum_sifirdan_sayilir(self):
        # Son kayıt %40 ama penceresi bir saat önce yenilenmiş: bu koşunun payı 52 - 40 değil, 52.
        self._codex_oncesi(40, yenilenir=time.time() - 3600)
        kota = json.loads((self.kosu("codex", "gpt-x") / "kota.json").read_text())
        self.assertEqual((kota["once"], kota["sonra"], kota["fark"]), (0.0, 52.0, 52.0))

    def test_cakisan_kosuda_fark_yazilmaz(self):
        with open(self.gunluk, "a", encoding="utf-8") as f:
            f.write(json.dumps({"tur": "isci_basladi", "ts": time.time() - 30, "id": "baska", "kaynak": "codex"}) + "\n")
            f.write(json.dumps({"tur": "isci_basladi", "ts": time.time() - 30, "id": "agy-isi", "kaynak": "agy"}) + "\n")
        kota = json.loads((self.kosu("codex", "gpt-x") / "kota.json").read_text())
        self.assertIsNone(kota["fark"])
        self.assertIn("overlapped", kota["neden"])
        # Başka aracın koşusu çakışma sayılmaz.
        with open(self.gunluk, "w", encoding="utf-8") as f:
            f.write(json.dumps({"tur": "isci_basladi", "ts": time.time() - 30, "id": "agy-isi", "kaynak": "agy"}) + "\n")
        kota = json.loads((self.kosu("codex", "gpt-x", FAKE_CODEX_USED="64") / "kota.json").read_text())
        self.assertEqual((kota["once"], kota["fark"]), (52.0, 12.0))  # önceki koşunun bıraktığı 52'den

    def test_olcum_kapatilabilir(self):
        kayit = self.kosu("codex", "gpt-x", EXTERNAL_AGENT_NO_QUOTA="1")
        self.assertFalse((kayit / "kota.json").exists())
        self.assertEqual((kayit / "rapor.md").read_text(), "codex raporu")
        self.assertNotIn("kota", self.olaylar("isci_bitti")[-1])

    def test_quota_alt_komutu(self):
        r = self.kos("quota")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("codex   5 hours used 40%", r.stdout)
        self.assertIn("codex   week    used 5%", r.stdout)
        self.assertIn("agy     agy: Gemini", r.stdout)
        self.assertIn("left 80%", r.stdout)
        kovalar = self.olaylar("kota")[-1]["kovalar"]
        self.assertEqual(len(kovalar), 4)
        self.assertEqual({k["pencere"] for k in kovalar}, {"5 saat", "hafta"})
        self.assertNotIn("hassas", kovalar[0])  # şemaya yeni alan girmez


class ClaudeSuresiTesti(unittest.TestCase):
    def test_claude_agentinda_sure_dolar_kota_bos_kalir(self):
        with tempfile.TemporaryDirectory() as d:
            gunluk, defter = Path(d) / "o.jsonl", Path(d) / "p.jsonl"
            with open(gunluk, "w", encoding="utf-8") as f:
                for e in ({"tur": "agent_basladi", "ts": 100, "id": "ag1", "rol": "polycrew:developer", "kaynak": "claude"},
                          {"tur": "agent_bitti", "ts": 160, "id": "ag1", "rol": "polycrew:developer", "kaynak": "claude"}):
                    f.write(json.dumps(e) + "\n")
            env = {**os.environ, "POLYCREW_EVENTS": str(gunluk), "POLYCREW_SCORES": str(defter)}
            for kimlik in ("ag1", "bilinmeyen"):
                subprocess.run([sys.executable, str(OLAY), "score", kimlik, "4", "--worker", "claude/developer/sonnet-9"],
                               check=True, env=env)
            bulunan, bilinmeyen = map(json.loads, defter.read_text(encoding="utf-8").splitlines())
            self.assertEqual(bulunan["sure"], 60)
            self.assertNotIn("kota", bulunan)
            self.assertNotIn("sure", bilinmeyen)


if __name__ == "__main__":
    unittest.main()
