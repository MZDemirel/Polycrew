"""hooks/quota.py ve claude-statusline.py: ortak kota kuralları (0018)."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "hooks"))
import quota as kurallar  # noqa: E402
# 0019: testler masaüstü uygulamasının gerçek kota dosyasını okumasın.
os.environ.setdefault("POLYCREW_DESKTOP_USAGE", "/nonexistent/polycrew-test")

SIMDI = 1_800_000_000.0


class Eslemeler(unittest.TestCase):
    def test_agy_grubu_ve_argon_yedegi(self):
        self.assertEqual(kurallar.agy_grubu("gemini-4-argon-high"), "agy: Argon")
        self.assertEqual(kurallar.agy_grubu("gemini-4-argon-high", {"agy: Gemini"}), "agy: Gemini")
        self.assertEqual(kurallar.agy_grubu("claude-opus-4"), "agy: Claude/GPT")
        self.assertEqual(kurallar.agy_grubu("gpt-oss-120b"), "agy: Claude/GPT")
        self.assertEqual(kurallar.agy_grubu("gemini-3.8-flash-high"), "agy: Gemini")

    def test_isci_kovasi(self):
        self.assertTrue(kurallar.isci_kovasi_mi("codex/gpt-6.1-sol/high", "codex", "Codex"))
        self.assertFalse(kurallar.isci_kovasi_mi("codex/gpt-6.1-sol/high", "agy", "Codex"))
        self.assertTrue(kurallar.isci_kovasi_mi("agy/gemini-4-argon-high", "agy", "agy: Argon",
                                                {"agy: Argon", "agy: Gemini"}))
        self.assertFalse(kurallar.isci_kovasi_mi("agy/gemini-4-argon-high", "agy", "agy: Gemini",
                                                 {"agy: Argon", "agy: Gemini"}))
        self.assertTrue(kurallar.isci_kovasi_mi("claude/developer/fable-5-2", "claude", "Claude"))
        self.assertTrue(kurallar.isci_kovasi_mi("claude/developer/fable-5-2", "claude", "Claude: Fable"))
        self.assertFalse(kurallar.isci_kovasi_mi("claude/developer/sonnet-5-5", "claude", "Claude: Fable"))
        self.assertFalse(kurallar.isci_kovasi_mi("claude/developer", "claude", "Claude: Fable"))
        self.assertFalse(kurallar.tanimli("pahali/x"))

    def test_eski_adlar(self):
        k = kurallar.adlari_duzelt({"grup": "Gemini 4 Argon", "pencere": "weekly"})
        self.assertEqual((k["grup"], k["pencere"]), ("agy: Argon", "hafta"))


class Tazelik(unittest.TestCase):
    def test_sifirlanma_ve_yas(self):
        self.assertIsNone(kurallar.eski_neden("hafta", SIMDI - 3600, SIMDI + 60, SIMDI))
        self.assertEqual(kurallar.eski_neden("hafta", SIMDI - 3600, SIMDI - 1, SIMDI), "reset passed")
        self.assertEqual(kurallar.eski_neden("hafta", SIMDI - 4 * 86400, SIMDI + 86400, SIMDI), "older than a day")
        self.assertEqual(kurallar.eski_neden("5 saat", SIMDI - 5 * 3600 - 1, None, SIMDI), "older than 5 hours")
        self.assertIsNone(kurallar.eski_neden("5 saat", SIMDI - 5 * 3600, None, SIMDI))

    def test_yenilenme_metni(self):
        olcum = datetime(2026, 11, 13, 9, tzinfo=timezone.utc).timestamp()
        utc = kurallar.yenilenme({"saglayici": "agy", "yenilenir": "11-13T16:46"}, olcum)
        self.assertEqual(utc, datetime(2026, 11, 13, 16, 46, tzinfo=timezone.utc).timestamp())
        yerel = kurallar.yenilenme({"saglayici": "agy", "yenilenir": "11-13 19:46"}, olcum)  # 0018 sonrası
        self.assertEqual(yerel, datetime(2026, 11, 13, 19, 46).timestamp())
        self.assertEqual(kurallar.yenilenme({"yenilenir_epoch": 7.0, "yenilenir": "x"}, olcum), 7.0)
        self.assertIsNone(kurallar.yenilenme({"yenilenir_epoch": float("nan")}, olcum))
        self.assertIsNone(kurallar.yenilenme({"yenilenir": "?"}, olcum))
        self.assertIsNone(kurallar.zaman(float("inf")))
        self.assertIsNone(kurallar.zaman(True))


class Kaydet(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.gunluk = Path(self.d.name) / "olaylar.jsonl"
        self.ortam = patch.dict(os.environ, {"POLYCREW_EVENTS": str(self.gunluk)})
        self.ortam.start()

    def tearDown(self):
        self.ortam.stop()
        self.d.cleanup()

    def satirlar(self):
        if not self.gunluk.exists():
            return []
        return [json.loads(s) for s in self.gunluk.read_text(encoding="utf-8").splitlines()]

    def test_degismeyen_okuma_yazilmaz_aralikla_tazelenir(self):
        agy = {"saglayici": "agy", "grup": "agy: Gemini", "pencere": "5 saat", "kullanilan": 0,
               "yenilenir_epoch": SIMDI + 5 * 3600}
        self.assertTrue(kurallar.kaydet([agy], simdi=SIMDI))
        # Kullanılmayan pencerenin sıfırlanması kayar: yine aynı okuma sayılır.
        self.assertFalse(kurallar.kaydet([{**agy, "yenilenir_epoch": SIMDI + 5 * 3600 + 60}], simdi=SIMDI + 60))
        self.assertTrue(kurallar.kaydet([{**agy, "kullanilan": 3}], simdi=SIMDI + 120))
        self.assertFalse(kurallar.kaydet([{**agy, "kullanilan": 3}], simdi=SIMDI + 180))
        self.assertTrue(kurallar.kaydet([{**agy, "kullanilan": 3}], simdi=SIMDI + 120 + kurallar.YENIDEN))
        self.assertEqual(len(self.satirlar()), 3)
        self.assertEqual(self.satirlar()[0]["tur"], "kota")

    def test_sabit_pencerenin_yeni_sifirlanmasi_yazilir(self):
        # Codex incelemesi (0018): Claude %0 → yeni pencerede yine %0; sıfırlanma değişti, yeni okuma yazılır.
        claude = {"saglayici": "claude", "grup": "Claude", "pencere": "5 saat", "kullanilan": 0,
                  "yenilenir_epoch": SIMDI + 60}
        self.assertTrue(kurallar.kaydet([claude], simdi=SIMDI))
        self.assertTrue(kurallar.kaydet([{**claude, "yenilenir_epoch": SIMDI + 5 * 3600}], simdi=SIMDI + 120))
        # agy'nin kullanılan penceresinde de sıfırlanma sabittir.
        agy = {"saglayici": "agy", "grup": "agy: Gemini", "pencere": "hafta", "kullanilan": 4, "yenilenir_epoch": 1.0}
        self.assertTrue(kurallar.kaydet([agy], simdi=SIMDI))
        self.assertTrue(kurallar.kaydet([{**agy, "yenilenir_epoch": 2.0}], simdi=SIMDI + 1))

    def test_codex_yeni_kayit_yazilir(self):
        codex = {"saglayici": "codex", "grup": "Codex", "pencere": "5 saat", "kullanilan": 5, "olcum": "a"}
        self.assertTrue(kurallar.kaydet([codex], simdi=SIMDI))
        self.assertFalse(kurallar.kaydet([codex], simdi=SIMDI + 1))
        self.assertTrue(kurallar.kaydet([{**codex, "olcum": "b"}], simdi=SIMDI + 2))

    def test_bozuk_durum_dosyasi_ve_bos_liste(self):
        kurallar.durum_dosyasi().write_text("bozuk", encoding="utf-8")
        self.assertFalse(kurallar.kaydet([], simdi=SIMDI))
        self.assertTrue(kurallar.kaydet([{"saglayici": "codex", "grup": "Codex", "pencere": "hafta"}], simdi=SIMDI))

    def test_record_komutu(self):
        f = Path(self.d.name) / "k.json"
        f.write_text(json.dumps([{"saglayici": "codex", "grup": "Codex", "pencere": "hafta", "kullanilan": 1}]))
        bos = Path(self.d.name) / "bos.json"
        bos.write_text("")
        r = subprocess.run([sys.executable, str(KOK / "hooks/quota.py"), "record", str(f), str(bos)],
                           env={**os.environ}, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        [e] = self.satirlar()
        self.assertEqual(e["kovalar"][0]["kullanilan"], 1)


class DurumSatiri(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.proje = Path(self.d.name) / "proje"
        self.proje.mkdir()
        (self.proje / "NEXT_SESSION.md").write_text("# x\n", encoding="utf-8")
        self.gunluk = Path(self.d.name) / "olaylar.jsonl"

    def tearDown(self):
        self.d.cleanup()

    def calistir(self, yuk, *args, proje=None):
        ortam = {k: v for k, v in os.environ.items() if k not in ("POLYCREW_WATCH_ALL", "CLAUDE_PROJECT_DIR")}
        return subprocess.run([sys.executable, str(KOK / "skills/watch/claude-statusline.py"), *args],
                              input=yuk if isinstance(yuk, str) else json.dumps(yuk),
                              env={**ortam, "POLYCREW_EVENTS": str(self.gunluk)},
                              cwd=str(proje or self.proje), capture_output=True, text=True)

    def yuk(self, bes=12.5, dizin=None):
        import time
        simdi = getattr(self, "_simdi", None) or setattr(self, "_simdi", int(time.time())) or self._simdi
        return {"model": {"display_name": "Opus"}, "workspace": {"project_dir": str(dizin or self.proje)},
                "rate_limits": {"five_hour": {"used_percentage": bes, "resets_at": simdi + 3600},
                                "seven_day": {"used_percentage": 33, "resets_at": simdi + 86400}}}

    def test_yazar_tekrarlamaz_satir_basar(self):
        r = self.calistir(self.yuk())
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "Opus · 5h 12.5% · week 33%"))
        self.calistir(self.yuk())
        satirlar = self.gunluk.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(satirlar), 1)
        e = json.loads(satirlar[0])
        self.assertEqual((e["tur"], e["kaynak"]), ("kota", "claude"))
        self.assertEqual([(k["grup"], k["pencere"]) for k in e["kovalar"]], [("Claude", "5 saat"), ("Claude", "hafta")])
        self.assertTrue(all(k.get("yenilenir_epoch") for k in e["kovalar"]))
        self.calistir(self.yuk(bes=40))
        self.assertEqual(len(self.gunluk.read_text(encoding="utf-8").splitlines()), 2)

    def test_duzensiz_projede_ve_bozuk_girdide_yazmaz(self):
        baska = Path(self.d.name) / "baska"
        baska.mkdir()
        r = self.calistir(self.yuk(dizin=baska), proje=baska)
        self.assertEqual(r.returncode, 0)
        self.assertFalse(self.gunluk.exists())
        for yuk in ("bozuk", "{}", {"rate_limits": {"five_hour": {"used_percentage": "x"}}}, []):
            with self.subTest(yuk=yuk):
                r = self.calistir(yuk)
                self.assertEqual(r.returncode, 0)
                self.assertTrue(r.stdout.strip())
        self.assertFalse(self.gunluk.exists())

    def test_then_zincirler(self):
        r = self.calistir(self.yuk(), "--then", f"{sys.executable} -c \"import sys,json; print(json.load(sys.stdin)['model']['display_name'] + '!')\"")
        self.assertEqual(r.stdout.strip(), "Opus!")
        self.assertTrue(self.gunluk.exists())



@unittest.skipIf(sys.platform == "win32", "fcntl yok")
class GunlukKilidi(unittest.TestCase):
    def test_yazim_kilidi_bekler(self):
        # 0018: ekleme ve kırpma aynı kilidi alır; kilit tutulurken başka süreç yazamaz.
        import fcntl
        import time
        with tempfile.TemporaryDirectory() as d:
            gunluk = Path(d) / "olaylar.jsonl"
            with open(str(gunluk) + ".lock", "a") as kilit:
                fcntl.flock(kilit, fcntl.LOCK_EX)
                p = subprocess.Popen([sys.executable, str(KOK / "hooks/events.py"), "write", "deneme", "a=1"],
                                     env={**os.environ, "POLYCREW_EVENTS": str(gunluk)})
                time.sleep(0.5)
                self.assertIsNone(p.poll())
                self.assertFalse(gunluk.exists() and gunluk.read_text())
                fcntl.flock(kilit, fcntl.LOCK_UN)
                self.assertEqual(p.wait(timeout=10), 0)
            self.assertEqual(json.loads(gunluk.read_text())["tur"], "deneme")



class Masaustu(unittest.TestCase):
    """0019: Claude kotası masaüstü uygulamasının plan-usage-history.json örneklerinden."""

    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.gunluk = Path(self.d.name) / "olaylar.jsonl"
        self.dosya = Path(self.d.name) / "plan-usage-history.json"
        self.ortam = patch.dict(os.environ, {"POLYCREW_EVENTS": str(self.gunluk),
                                             "POLYCREW_DESKTOP_USAGE": str(self.dosya),
                                             "POLYCREW_DESKTOP_ORG": "org-a"})
        self.ortam.start()

    def tearDown(self):
        self.ortam.stop()
        self.d.cleanup()

    def ornekler(self, *ornek):
        self.dosya.write_text(json.dumps({"version": 2, "samples": [
            {"t": int(t * 1000), "org": org, "u": u} for t, org, u in ornek]}), encoding="utf-8")

    def olaylar(self):
        if not self.gunluk.exists():
            return []
        return [json.loads(x) for x in self.gunluk.read_text(encoding="utf-8").splitlines()]

    def test_en_yeni_ornek_ve_kurulus(self):
        self.ornekler((SIMDI - 1800, "org-a", {"fh": 5, "sd": 30}), (SIMDI - 900, "org-a", {"fh": 25, "sd": 35}),
                      (SIMDI - 60, "org-b", {"fh": 99, "sd": 99}))
        kovalar = kurallar.masaustu_kovalari(SIMDI)
        self.assertEqual([(k["pencere"], k["kullanilan"], k["kaynak"]) for k in kovalar],
                         [("5 saat", 25, "desktop"), ("hafta", 35, "desktop")])
        self.assertEqual(kurallar.zaman(kovalar[0]["olcum"]), SIMDI - 900)
        self.assertNotIn("yenilenir_epoch", kovalar[0])

    def test_bozuk_eski_ya_da_yok(self):
        for icerik in ("bozuk", "[]", '{"samples": 5}', '{"samples": [{"t": "x", "u": {}}]}'):
            with self.subTest(icerik=icerik):
                self.dosya.write_text(icerik, encoding="utf-8")
                self.assertEqual(kurallar.masaustu_kovalari(SIMDI), [])
                self.assertFalse(kurallar.masaustu_kaydet(SIMDI))
        self.ornekler((SIMDI - 4 * 3600, "org-a", {"fh": 5, "sd": 30}))  # uygulama kapalı, dosya dondu
        self.assertEqual(kurallar.masaustu_kovalari(SIMDI), [])
        self.ornekler((SIMDI - 60, "org-a", {"fh": 150, "sd": "x"}))
        self.assertEqual(kurallar.masaustu_kovalari(SIMDI), [])
        self.dosya.unlink()
        self.assertFalse(kurallar.masaustu_kaydet(SIMDI))
        self.assertEqual(self.olaylar(), [])

    def test_sifirlanma_onceki_okumadan_tasinir_yeni_okumayi_ezmez(self):
        pm = [{"saglayici": "claude", "grup": "Claude", "pencere": "5 saat", "kullanilan": 21,
               "olcum": datetime.fromtimestamp(SIMDI - 1200, timezone.utc).isoformat(),
               "yenilenir_epoch": SIMDI + 3600}]
        kurallar.kaydet(pm, yeniden=0, simdi=SIMDI - 1200, kaynak="claude")
        self.ornekler((SIMDI - 600, "org-a", {"fh": 25, "sd": 35}))
        self.assertTrue(kurallar.masaustu_kaydet(SIMDI))
        bes = [k for k in self.olaylar()[-1]["kovalar"] if k["pencere"] == "5 saat"][0]
        self.assertEqual((bes["kullanilan"], bes["yenilenir_epoch"]), (25, SIMDI + 3600))
        self.assertFalse(kurallar.masaustu_kaydet(SIMDI + 30))  # değişmedi
        # Statusline daha yeni ölçtüyse eski masaüstü örneği yazılmaz.
        sl = [{**pm[0], "kullanilan": 40, "olcum": datetime.fromtimestamp(SIMDI + 60, timezone.utc).isoformat()}]
        kurallar.kaydet(sl, yeniden=0, simdi=SIMDI + 60, kaynak="claude")
        sayi = len(self.olaylar())
        self.ornekler((SIMDI, "org-a", {"fh": 26, "sd": 35}))
        kurallar.masaustu_kaydet(SIMDI + 90)
        yazilan = self.olaylar()[sayi:]
        self.assertTrue(all(k["pencere"] != "5 saat" for e in yazilan for k in e["kovalar"]))

    def test_bilinen_sifirlanmadan_onceki_ornek_yazilmaz(self):
        # Codex incelemesi (0019): 10 dk önceki %99 örneği, 1 dk önce sıfırlanan pencereye aittir.
        pm = [{"saglayici": "claude", "grup": "Claude", "pencere": "5 saat", "kullanilan": 90,
               "yenilenir_epoch": SIMDI - 60}]
        kurallar.kaydet(pm, yeniden=0, simdi=SIMDI - 3600, kaynak="claude")
        self.ornekler((SIMDI - 600, "org-a", {"fh": 99, "sd": 35}))
        self.assertEqual([k["pencere"] for k in kurallar.masaustu_kovalari(SIMDI)], ["hafta"])

    @unittest.skipIf(sys.platform == "win32", "fcntl yok")
    def test_kilit_tutuluyorsa_beklemeden_atlar(self):
        import fcntl
        import time as zaman_modulu
        self.ornekler((SIMDI - 60, "org-a", {"fh": 3, "sd": 4}))
        yol = kurallar.durum_dosyasi()
        with open(str(yol) + ".lock", "a") as kilit:
            fcntl.flock(kilit, fcntl.LOCK_EX)
            bas = zaman_modulu.time()
            self.assertFalse(kurallar.masaustu_kaydet(SIMDI, bekle=0.2))
            self.assertLess(zaman_modulu.time() - bas, 1.5)
        self.assertEqual(self.olaylar(), [])
        self.assertTrue(kurallar.masaustu_kaydet(SIMDI))

    def test_komut(self):
        import time as zaman_modulu
        self.ornekler((zaman_modulu.time() - 60, "org-a", {"fh": 3, "sd": 4}))
        r = subprocess.run([sys.executable, str(KOK / "hooks/quota.py"), "desktop"], env={**os.environ},
                           capture_output=True, text=True)
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        self.assertEqual([k["kullanilan"] for k in self.olaylar()[-1]["kovalar"]], [3, 4])


if __name__ == "__main__":
    unittest.main()
