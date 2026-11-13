"""Dış işçi betiğinin koşu yolu, sahte codex ve agy ile uçtan uca (0010).

Gerçek araçlar çağrılmaz: geçici bir PATH'in başına sahte ``codex`` ve ``agy`` konur, HOME geçicidir.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
BETIK = KOK / "skills" / "external-agent" / "external-agent.sh"
OLAY = KOK / "hooks" / "events.py"

# Sahte codex: görevi stdin'den okur, -o dosyasına rapor yazar, yeni bir oturum dosyasına
# FAKE_CODEX_USED yüzdesini bırakır (gerçek codex'in rate_limits kaydı gibi).
SAHTE_CODEX = r'''#!/usr/bin/env python3
import json, os, sys, time
a = sys.argv[1:]
open(os.path.expanduser("~/codex_stdin.txt"), "w").write(sys.stdin.read())
time.sleep(float(os.environ.get("FAKE_CODEX_SLEEP", "0")))
open(a[a.index("-o") + 1], "w").write("codex raporu")
d = os.path.expanduser("~/.codex/sessions/2026/10/11")
os.makedirs(d, exist_ok=True)
if os.environ.get("FAKE_CODEX_NO_RECORD"):
    sys.exit(1)
with open(os.path.join(d, "kosu-%d.jsonl" % os.getpid()), "w") as f:
    f.write(json.dumps({"timestamp": "t2", "payload": {"rate_limits": {
        "primary": {"used_percent": float(os.environ["FAKE_CODEX_USED"]), "resets_at": time.time() + 3600},
        "secondary": {"used_percent": 5, "resets_at": time.time() + 3 * 86400}}}}) + "\n")
print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 7}}))
'''

# Sahte agy: /quota durum dosyasındaki kalan oranları verir; bir görev koşusu modelin grubundan düşer.
SAHTE_AGY = r'''#!/usr/bin/env python3
import json, os, sys
a = sys.argv[1:]
yol = os.path.expanduser("~/agy_durum.json")
durum = json.load(open(yol))
if a[a.index("-p") + 1] == "/quota":
    claude = [{"window": "weekly", "remaining_fraction": durum["claude"], "reset_time": "2026-10-12T10:00:00Z"}]
    if "claude_5h" in durum:
        claude.insert(0, {"window": "5h", "remaining_fraction": durum["claude_5h"], "reset_time": "2026-10-11T22:00:00Z"})
    if durum["claude"] <= 0:
        claude[-1] = {"window": "weekly"}  # tükenmiş kova: alanlar yok (0014)
    print(json.dumps({"command": {"data": {"groups": [
        {"name": "Gemini Models", "buckets": [
            {"window": "5h", "remaining_fraction": durum["gemini"], "reset_time": "2026-10-11T22:00:00Z"}]},
        {"name": "Claude and GPT models", "buckets": claude},
    ] + ([{"name": "Gemini 4 Argon", "buckets": [
            {"window": "weekly", "remaining_fraction": durum["argon"], "reset_time": "2026-10-12T10:00:00Z"}]}]
         if "argon" in durum else [])}}}))
elif os.environ.get("FAKE_AGY_FAIL"):
    print(json.dumps({"response": "yarım düşünce"}))
    sys.stderr.write("RESOURCE_EXHAUSTED (code 429): Individual quota reached\n")
    sys.exit(3)
else:
    model = a[a.index("--model") + 1]
    grup = "claude" if "claude" in model else "argon" if "argon" in model and "argon" in durum else "gemini"
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
            "secondary": {"used_percent": 5, "resets_at": time.time() + 3 * 86400}}}}) + "\n", encoding="utf-8")
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
                       check=True, env=self.env, stdout=subprocess.DEVNULL)
        subprocess.run([sys.executable, str(OLAY), "score", kayit.name, "4", "--worker", "codex/gpt-x/high",
                        "--quota", "30", "--duration", "99"], check=True, env=self.env,
                       stdout=subprocess.DEVNULL)
        ilk, ikinci = map(json.loads, self.defter.read_text(encoding="utf-8").splitlines())
        self.assertEqual(ilk["kota"], 12.0)
        self.assertEqual(ilk["sure"], bitti["sure_sn"])
        self.assertEqual((ikinci["kota"], ikinci["sure"]), (30, 99))

    def test_agy_modele_gore_gruptan_olcer(self):
        gemini = json.loads((self.kosu("agy", "gemini-3.8-flash-high") / "kota.json").read_text())
        self.assertEqual((gemini["once"], gemini["sonra"], gemini["fark"], gemini["pencere"]), (20.0, 24.0, 4.0, "5 saat"))
        claude = json.loads((self.kosu("agy", "claude-opus-4-6-thinking") / "kota.json").read_text())
        self.assertEqual((claude["once"], claude["sonra"], claude["fark"], claude["pencere"]), (50.0, 54.0, 4.0, "hafta"))

    def test_agy_en_dolu_pencereyi_olcer(self):
        # 0014: 5 saat boşken haftalık dolu; koşu haftalık sınıra takılır, ölçü haftalıktan.
        (self.ev / "agy_durum.json").write_text(json.dumps({"gemini": 0.8, "claude": 0.32, "claude_5h": 1.0}),
                                                encoding="utf-8")
        kota = json.loads((self.kosu("agy", "claude-opus-4-6-thinking") / "kota.json").read_text())
        self.assertEqual((kota["once"], kota["pencere"], kota["grup"], kota["fark"]),
                         (68.0, "hafta", "agy: Claude/GPT", 4.0))

    def test_tukenmis_agy_kovasi_cokmez_ve_dusen_kosu_raporda(self):
        (self.ev / "agy_durum.json").write_text(json.dumps({"gemini": 0.8, "claude": 0.0, "claude_5h": 1.0}),
                                                encoding="utf-8")
        r = self.kos("quota")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("left ?%", r.stdout)
        self.assertEqual(len(self.olaylar("kota")[-1]["kovalar"]), 5)  # codex 2, gemini 1, claude 2
        r = self.kos("agy", "claude-opus-4-6-thinking", "-", "read", str(self.is_klasoru), str(self.gorev),
                     FAKE_AGY_FAIL="1")
        self.assertEqual(r.returncode, 3)
        kayit = Path(r.stdout.strip().splitlines()[-1])
        rapor = (kayit / "rapor.md").read_text()
        self.assertTrue(rapor.startswith("yarım düşünce"))
        self.assertIn("**Run failed:** exit code 3", rapor)
        self.assertIn("RESOURCE_EXHAUSTED", rapor)
        kota = json.loads((kayit / "kota.json").read_text())
        self.assertEqual((kota["once"], kota["pencere"], kota["grup"]), (0.0, "5 saat", "agy: Claude/GPT"))
        # Grubun tek kovası tükenmişse ölçü yok ama koşu ve kayıt çökmez.
        (self.ev / "agy_durum.json").write_text(json.dumps({"gemini": 0.8, "claude": 0.0}), encoding="utf-8")
        kota = json.loads((self.kosu("agy", "claude-opus-4-6-thinking") / "kota.json").read_text())
        self.assertEqual((kota["once"], kota["fark"], kota["neden"]), (None, None, "quota could not be read"))

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
        kayit = self.kosu("codex", "gpt-x")
        kota = json.loads((kayit / "kota.json").read_text())
        self.assertIsNone(kota["fark"])
        self.assertIn("overlapped", kota["neden"])
        # 0014: pay ayrılamaz ama birlikte doluş ve çakışanlar kalır; puana kota_ortak, kota değil.
        self.assertEqual((kota["ortak_fark"], kota["cakisanlar"]), (12.0, ["baska"]))
        bitti = self.olaylar("isci_bitti")[-1]
        self.assertEqual((bitti.get("kota_ortak"), "kota" in bitti), (12.0, False))
        subprocess.run([sys.executable, str(OLAY), "score", kayit.name, "4", "--worker", "codex/gpt-x/high"],
                       check=True, env=self.env, stdout=subprocess.DEVNULL)
        puan = json.loads(self.defter.read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual((puan.get("kota_ortak"), "kota" in puan), (12.0, False))
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

    def test_timeout_olmadan_python_ile_kosar(self):
        # macOS: GNU timeout yok, bash 3.2'de boş dizi set -u ile düşer (0013). Resimli ve resimsiz koşu.
        resim = self.ev / "r.png"
        resim.write_bytes(b"x")
        r = self.kos("codex", "gpt-x", "-", "read", str(self.is_klasoru), str(self.gorev), str(resim),
                     _POLYCREW_ZAMAN="python")
        self.assertEqual(r.returncode, 0, r.stderr)
        kayit = Path(r.stdout.strip().splitlines()[-1])
        self.assertEqual((kayit / "rapor.md").read_text(), "codex raporu")
        self.assertIn(str(resim), (kayit / "komut.txt").read_text())
        gelen = (self.ev / "codex_stdin.txt").read_text(encoding="utf-8")
        self.assertIn("Rules: do not git push", gelen)
        self.assertIn("bir şey yap", gelen)
        kayit = self.kosu("agy", "gemini-3.8-flash-high", _POLYCREW_ZAMAN="python")
        self.assertEqual((kayit / "rapor.md").read_text(), "agy raporu")

    def test_sure_asiminda_124_ile_kesilir(self):
        for yol in ("", "python"):
            with self.subTest(yol=yol or "timeout"):
                bas = time.time()
                r = self.kos("codex", "gpt-x", "-", "read", str(self.is_klasoru), str(self.gorev),
                             EXTERNAL_AGENT_TIMEOUT="1", FAKE_CODEX_SLEEP="20", EXTERNAL_AGENT_NO_QUOTA="1",
                             _POLYCREW_ZAMAN=yol)
                self.assertLess(time.time() - bas, 15)
                kayit = Path(r.stdout.strip().splitlines()[-1])
                self.assertEqual((kayit / "cikis_kodu").read_text().strip(), "124")

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
        # 0018: "hassas" artık yazılır (roster.py agy'de yuvarlanmamış değeri okur); sıfırlanma kesin anla.
        self.assertIn("hassas", kovalar[0])
        self.assertTrue(all(k.get("yenilenir_epoch") for k in kovalar))
        # Değişmeyen okuma ikinci kez yazılmaz.
        self.assertEqual(self.kos("quota").returncode, 0)
        self.assertEqual(len(self.olaylar("kota")), 1)

    def test_argon_kosusu_kendi_kovasindan_olculur(self):
        # 0018: Argon koşusu Gemini kovasından ölçülüyordu (fark 0).
        (self.ev / "agy_durum.json").write_text(json.dumps({"gemini": 0.80, "claude": 0.50, "argon": 0.30}),
                                                encoding="utf-8")
        kota = json.loads((self.kosu("agy", "gemini-4-argon-high") / "kota.json").read_text())
        self.assertEqual((kota["grup"], kota["once"], kota["sonra"], kota["fark"]), ("agy: Argon", 70.0, 74.0, 4.0))

    def test_codex_yeni_kayit_yazmazsa_fark_bos(self):
        # 0018: Codex kayıt yazmadan düşerse sonraki okuma öncekinin aynısıdır: fark 0 değil, bilinmiyor.
        self._codex_kaydi(0.5, time.time() + 3600, time.time() + 86400)
        r = self.kos("codex", "gpt-x", "-", "read", str(self.is_klasoru), str(self.gorev), FAKE_CODEX_NO_RECORD="1")
        kota = json.loads((Path(r.stdout.strip().splitlines()[-1]) / "kota.json").read_text())
        self.assertIsNone(kota["fark"])
        self.assertEqual(kota["neden"], "no new reading after the run")

    def test_quota_codex_pencere_suresinden_bos_sifirlanma_atlanir(self):
        # 0018: pencere sıradan değil window_minutes'ten; sıfırlanması olmayan kova yazılmaz (null'da çöküyordu).
        f = self.ev / ".codex" / "sessions" / "2026" / "10" / "10" / "eski.jsonl"
        f.write_text(json.dumps({"timestamp": "2026-11-13T10:00:00Z", "payload": {"rate_limits": {
            "primary": {"used_percent": 7, "window_minutes": 10080, "resets_at": time.time() + 86400},
            "secondary": {"used_percent": 9, "window_minutes": 300, "resets_at": None}}}}) + "\n",
            encoding="utf-8")
        r = self.kos("quota")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("codex   week    used 7", r.stdout)
        self.assertNotIn("used 9", r.stdout)
        codex = [k for k in self.olaylar("kota")[-1]["kovalar"] if k["saglayici"] == "codex"]
        self.assertEqual([(k["pencere"], k["kullanilan"]) for k in codex], [("hafta", 7)])

    def test_quota_agy_argon_grubu_ve_yerel_saat(self):
        (self.ev / "bin" / "agy").write_text(r'''#!/usr/bin/env python3
import json
print(json.dumps({"command": {"data": {"groups": [
    {"name": "Gemini Models", "buckets": [{"window": "weekly", "remaining_fraction": 1.0, "reset_time": "2026-11-16T13:59:00Z"}]},
    {"name": "Gemini 4 Argon", "buckets": [{"window": "weekly", "remaining_fraction": 0.17, "reset_time": "2026-11-16T12:43:00Z"}]}]}}}))
''', encoding="utf-8")
        r = self.kos("quota")
        self.assertEqual(r.returncode, 0, r.stderr)
        yerel = datetime.fromtimestamp(datetime(2026, 11, 16, 12, 43, tzinfo=timezone.utc).timestamp()).strftime("%m-%d %H:%M")
        self.assertIn(f"agy     agy: Argon             week    left 17%  resets {yerel}", r.stdout)
        argon = [k for k in self.olaylar("kota")[-1]["kovalar"] if k["grup"] == "agy: Argon"][0]
        self.assertEqual((argon["yenilenir"], argon["kullanilan"]), (yerel, 83))

    def _codex_kaydi(self, yas_saat, birinci_yenilenir, ikinci_yenilenir):
        """Codex'in son oturum kaydını verilen yaşta (ISO zamanla) ve sıfırlanma zamanlarıyla yazar."""
        olcum = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(time.time() - yas_saat * 3600))
        f = self.ev / ".codex" / "sessions" / "2026" / "10" / "10" / "eski.jsonl"
        f.write_text(json.dumps({"timestamp": olcum, "payload": {"rate_limits": {
            "primary": {"used_percent": 81, "resets_at": birinci_yenilenir},
            "secondary": {"used_percent": 23, "resets_at": ikinci_yenilenir}}}}) + "\n", encoding="utf-8")

    def _codex_satirlari(self):
        r = self.kos("quota")
        self.assertEqual(r.returncode, 0, r.stderr)
        return {s.split()[1]: s for s in r.stdout.splitlines() if s.startswith("codex")}

    def test_quota_bayat_codex_okumasi_stale_yazilir(self):
        simdi, gun = time.time(), 86400
        self._codex_kaydi(1, simdi + 3600, simdi + 3 * gun)  # taze
        satir = self._codex_satirlari()
        self.assertNotIn("stale", satir["5"] + satir["week"])
        self._codex_kaydi(6, simdi + 3600, simdi + 3 * gun)  # 5 saatlik pencereden eski, haftalık değil
        satir = self._codex_satirlari()
        self.assertIn("stale (older than 5 hours)", satir["5"])
        self.assertNotIn("stale", satir["week"])
        self._codex_kaydi(30, simdi + 3600, simdi + 3 * gun)  # bir günden eski
        self.assertIn("stale (older than a day)", self._codex_satirlari()["week"])
        self._codex_kaydi(1, simdi - 60, simdi + 3 * gun)  # sıfırlanma geçti
        satir = self._codex_satirlari()
        self.assertIn("stale (reset passed)", satir["5"])
        self.assertNotIn("stale", satir["week"])
        # Kesin sıfırlanma zamanı olaya yazılır (roster.py bayatlığı bundan karar verir); model koşusu başlamaz.
        kova = [k for k in self.olaylar("kota")[-1]["kovalar"] if k["saglayici"] == "codex"][0]
        self.assertAlmostEqual(kova["yenilenir_epoch"], simdi - 60, delta=1)
        self.assertFalse((self.ev / "codex_stdin.txt").exists())
        agy = [k for k in self.olaylar("kota")[-1]["kovalar"] if k["saglayici"] == "agy"][0]
        self.assertEqual(agy["yenilenir_epoch"], datetime(2026, 10, 11, 22, tzinfo=timezone.utc).timestamp())


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
                               check=True, env=env, stdout=subprocess.DEVNULL)
            bulunan, bilinmeyen = map(json.loads, defter.read_text(encoding="utf-8").splitlines())
            self.assertEqual(bulunan["sure"], 60)
            self.assertNotIn("kota", bulunan)
            self.assertNotIn("sure", bilinmeyen)


if __name__ == "__main__":
    unittest.main()
