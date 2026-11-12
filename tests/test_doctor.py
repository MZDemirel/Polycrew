"""Doctor: yalıtılmış proje, ortam ve günlükle salt okunur kurulum denetimi."""

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "skills" / "doctor"))
import doctor as doktor  # noqa: E402


class DoktorTesti(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.TemporaryDirectory()
        self.addCleanup(self.gecici.cleanup)
        self.klasor = Path(self.gecici.name)
        self.proje = self.klasor / "project"
        self.proje.mkdir()
        for ad in ("NEXT_SESSION.md", "CLAUDE.md", "PLAN.md"):
            (self.proje / ad).write_text("# Project\n", encoding="utf-8")
        self.gunluk = self.klasor / "events.jsonl"
        self.ayarlar = self.klasor / ".gemini" / "antigravity-cli" / "settings.json"
        self.ayarlar.parent.mkdir(parents=True)
        self.ayarlar.write_text(json.dumps({"permissions": {"allow": ["read_file(secret-path)"]}}), encoding="utf-8")
        self.betikler = [self.klasor / "first.sh", self.klasor / "second.sh"]
        for yol in self.betikler:
            yol.write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
        self.simdi = 1800000000.0
        self.kota_yaz(self.simdi)
        ortam = {"HOME": str(self.klasor), "PATH": os.environ.get("PATH", ""),
                 "POLYCREW_EVENTS": str(self.gunluk), "XDG_CACHE_HOME": str(self.klasor)}
        self.ortam = patch.dict(os.environ, ortam, clear=True)
        self.ortam.start()
        self.addCleanup(self.ortam.stop)
        bash = shutil.which("bash")
        self.assertIsNotNone(bash)
        self.araclar = {"bash": bash, "codex": "/fake/codex", "agy": "/fake/agy", "node": "/fake/node"}
        yama = patch.object(doktor.shutil, "which", side_effect=self.araclar.get)
        yama.start()
        self.addCleanup(yama.stop)
        saat = patch.object(doktor.time, "time", return_value=self.simdi)
        saat.start()
        self.addCleanup(saat.stop)

    def kota_yaz(self, ts, olcum=None):
        kovalar = [{"saglayici": ad, **({"olcum": olcum} if olcum is not None else {})}
                   for ad in doktor.SAGLAYICILAR]
        self.gunluk.write_text(json.dumps({"tur": "kota", "ts": ts, "kovalar": kovalar}) + "\n", encoding="utf-8")

    def calistir(self, *argumanlar):
        cikti = io.StringIO()
        with contextlib.redirect_stdout(cikti):
            kod = doktor.ana(["--project", str(self.proje), *argumanlar], betikler=self.betikler)
        return kod, cikti.getvalue()

    def sonuclar(self):
        kod, cikti = self.calistir("--json")
        return kod, {s["name"]: s for s in json.loads(cikti)}

    def test_temiz_proje(self):
        kod, sonuclar = self.sonuclar()
        self.assertEqual(kod, 0)
        self.assertTrue(all(s["status"] == "ok" for s in sonuclar.values()), sonuclar)

    def test_not_yoksa_uyari(self):
        (self.proje / "NEXT_SESSION.md").unlink()
        kod, sonuclar = self.sonuclar()
        self.assertEqual(kod, 0)
        self.assertEqual(sonuclar["Project notes"]["status"], "warn")
        self.assertIn("/project-setup", sonuclar["Project notes"]["detail"])

    def test_ust_klasor_ve_eski_not_adi(self):
        (self.proje / "NEXT_SESSION.md").rename(self.proje / "SONRAKI_OTURUM.md")
        alt = self.proje / "src" / "nested"
        alt.mkdir(parents=True)
        self.proje = alt
        _, sonuclar = self.sonuclar()
        for ad in ("Project notes", "CLAUDE.md", "PLAN.md"):
            self.assertEqual(sonuclar[ad]["status"], "ok")
        self.assertIn("SONRAKI_OTURUM.md", sonuclar["Project notes"]["detail"])

    def test_ortam_baska_projeyi_gosterse_de_not_yok(self):
        (self.proje / "NEXT_SESSION.md").unlink()
        diger = self.klasor / "other"
        diger.mkdir()
        (diger / "NEXT_SESSION.md").touch()
        with patch.dict(os.environ, {"CLAUDE_PROJECT_DIR": str(diger), "POLYCREW_WATCH_ALL": "1"}):
            _, sonuclar = self.sonuclar()
        self.assertEqual(sonuclar["Project notes"]["status"], "warn")

    def test_komsu_dosyalar_eksik(self):
        for ad in ("CLAUDE.md", "PLAN.md"):
            (self.proje / ad).unlink()
        _, sonuclar = self.sonuclar()
        for ad in ("CLAUDE.md", "PLAN.md"):
            self.assertEqual(sonuclar[ad]["status"], "warn")

    def test_ikinci_betik_bozuksa_hata(self):
        self.betikler[1].write_text("if then\n", encoding="utf-8")
        kod, sonuclar = self.sonuclar()
        self.assertEqual(kod, 1)
        kabuklar = [s for s in sonuclar.values() if s["name"].startswith("Shell ")]
        self.assertEqual([s["status"] for s in kabuklar], ["ok", "fail"])
        self.assertIn("second.sh", kabuklar[1]["detail"])

    def test_kota_yok_veya_eski(self):
        for ts in (None, self.simdi - 5 * 3600 - 1):
            with self.subTest(ts=ts):
                if ts is None:
                    self.gunluk.write_text("", encoding="utf-8")
                else:
                    self.kota_yaz(ts)
                kod, sonuclar = self.sonuclar()
                self.assertEqual(kod, 0)
                for ad in doktor.SAGLAYICILAR:
                    self.assertEqual(sonuclar[f"Quota ({ad})"]["status"], "warn")
                    self.assertIn("claude-quota.py" if ad == "claude" else "external-agent.sh quota",
                                  sonuclar[f"Quota ({ad})"]["detail"])
                self.assertNotIn("claude-quota.py", sonuclar["Quota (codex)"]["detail"])

    def test_kota_olcum_zamani_ve_saglayicilar_bagimsiz(self):
        eski = datetime.fromtimestamp(self.simdi - 6 * 3600, timezone.utc).isoformat()
        self.kota_yaz(self.simdi, eski)
        with self.gunluk.open("a", encoding="utf-8") as dosya:
            dosya.write(json.dumps({"tur": "kota", "ts": self.simdi + 1,
                                   "kovalar": [{"saglayici": "codex"}]}) + "\n")
            dosya.write("bad JSON\n[]\n")
        _, sonuclar = self.sonuclar()
        self.assertEqual(sonuclar["Quota (codex)"]["status"], "ok")
        self.assertEqual(sonuclar["Quota (claude)"]["status"], "warn")
        self.assertEqual(sonuclar["Quota (agy)"]["status"], "warn")

    def test_kotada_en_yeni_olay_siradan_bagimsiz(self):
        with self.gunluk.open("a", encoding="utf-8") as dosya:
            dosya.write(json.dumps({"tur": "kota", "ts": self.simdi - 6 * 3600,
                                   "kovalar": [{"saglayici": "codex"}]}) + "\n")
        _, sonuclar = self.sonuclar()
        self.assertEqual(sonuclar["Quota (codex)"]["status"], "ok")

    def test_buyuk_gunluk(self):
        with patch.dict(os.environ, {"POLYCREW_EVENTS_MAX_MB": "0.0001"}):
            _, sonuclar = self.sonuclar()
        self.assertEqual(sonuclar["Event log"]["status"], "warn")
        self.assertIn("80%", sonuclar["Event log"]["detail"])
        with patch.dict(os.environ, {"POLYCREW_EVENTS_MAX_MB": "0"}):
            self.assertEqual(self.sonuclar()[1]["Event log"]["status"], "ok")

    def test_gunluk_yoksa_olay_yok(self):
        self.gunluk.unlink()
        _, sonuclar = self.sonuclar()
        self.assertEqual(sonuclar["Event log"]["status"], "ok")
        self.assertIn("no events yet", sonuclar["Event log"]["detail"])
        self.assertFalse(self.gunluk.exists())

    def test_gunluk_klasoru_yok_veya_yazilamaz(self):
        with patch.dict(os.environ, {"POLYCREW_EVENTS": str(self.klasor / "missing" / "events.jsonl")}):
            _, sonuclar = self.sonuclar()
            # Yeni kurulum: klasör henüz yok ama üstü yazılabilir; kanca ilk olayda açar, uyarı değil.
            self.assertEqual(sonuclar["Event log folder"]["status"], "ok")
            self.assertIn("first event", sonuclar["Event log folder"]["detail"])
            self.assertEqual(sonuclar["Event log"]["status"], "ok")
            self.assertIn("no events yet", sonuclar["Event log"]["detail"])
            self.assertFalse((self.klasor / "missing").exists())
        with patch.object(doktor.os, "access", return_value=False):
            self.assertEqual(self.sonuclar()[1]["Event log folder"]["status"], "warn")

    def test_gunluk_salt_okunur_ya_da_klasor(self):
        self.gunluk.chmod(0o444)
        self.addCleanup(self.gunluk.chmod, 0o644)
        if not os.access(self.gunluk, os.W_OK):  # root her dosyaya yazabilir
            self.assertEqual(self.sonuclar()[1]["Event log"]["status"], "warn")
        self.gunluk.unlink()
        self.gunluk.mkdir()
        kod, sonuclar = self.sonuclar()
        self.assertEqual(kod, 1)
        self.assertEqual(sonuclar["Event log"]["status"], "fail")
        self.assertIn("no quota reading", sonuclar["Quota (codex)"]["detail"])  # iz değil, anlaşılır satır

    def test_bozuk_kota_satiri_ve_gelecek_tarih_eski_olcumu_gizlemez(self):
        self.kota_yaz(self.simdi - 6 * 3600)
        with self.gunluk.open("a", encoding="utf-8") as dosya:
            dosya.write(json.dumps({"tur": "kota", "ts": self.simdi, "kovalar": 5}) + "\n")
            dosya.write(json.dumps({"tur": "kota", "ts": self.simdi + 30 * 86400,
                                   "kovalar": [{"saglayici": "codex"}]}) + "\n")
        _, sonuclar = self.sonuclar()
        for ad in doktor.SAGLAYICILAR:
            self.assertEqual(sonuclar[f"Quota ({ad})"]["status"], "warn")
            self.assertIn("hours old", sonuclar[f"Quota ({ad})"]["detail"])

    def test_kurulu_olmayan_aracin_kotasi_sorulmaz_ve_eksik_betik(self):
        self.araclar.pop("codex")
        self.betikler.append(self.klasor / "yok.sh")
        kod, sonuclar = self.sonuclar()
        self.assertEqual(kod, 1)
        self.assertNotIn("Quota (codex)", sonuclar)
        self.assertIn("Quota (claude)", sonuclar)
        eksik = next(s for s in sonuclar.values() if s["name"].endswith("yok.sh"))
        self.assertEqual(eksik["status"], "fail")
        self.assertIn("missing", eksik["detail"])

    def test_olmayan_proje_klasoru(self):
        cikti = io.StringIO()
        with contextlib.redirect_stdout(cikti):
            doktor.ana(["--project", str(self.klasor / "yanlis-yol"), "--json"], betikler=self.betikler)
        satir = next(s for s in json.loads(cikti.getvalue()) if s["name"] == "Project notes")
        self.assertIn("does not exist", satir["detail"])

    def test_varsayilan_gunluk_yolu(self):
        del os.environ["POLYCREW_EVENTS"]
        _, sonuclar = self.sonuclar()
        self.assertIn(str(self.klasor / "polycrew" / "olaylar.jsonl"), sonuclar["Event log"]["detail"])

    def test_eksik_araclar_uyari(self):
        for ad in ("codex", "agy", "node", "bash"):
            with self.subTest(ad=ad):
                yol = self.araclar.pop(ad)
                try:
                    kod, sonuclar = self.sonuclar()
                finally:
                    self.araclar[ad] = yol
                self.assertEqual(kod, 0)
                if ad == "bash":
                    self.assertTrue(all(s["status"] == "warn" for s in sonuclar.values()
                                        if s["name"].startswith("Shell ")))
                else:
                    self.assertEqual(sonuclar[ad]["status"], "warn")
                if ad in ("codex", "agy"):
                    self.assertIn("Claude roles only", sonuclar[ad]["detail"])
                if ad == "agy":
                    self.assertNotIn("agy permissions", sonuclar)

    def test_agy_izinleri_eksik_bozuk_bos(self):
        for metin in (None, "{bad", "[]", '{"permissions": {"allow": []}}',
                      '{"permissions": {"allow": "secret-rule"}}'):
            with self.subTest(metin=metin):
                if metin is None:
                    self.ayarlar.unlink()
                else:
                    self.ayarlar.write_text(metin, encoding="utf-8")
                _, sonuclar = self.sonuclar()
                izin = sonuclar["agy permissions"]
                self.assertEqual(izin["status"], "warn")
                self.assertIn("first command without permission", izin["detail"])
                self.assertNotIn("secret-rule", izin["detail"])

    def test_json_duz_ciktiyla_ayni(self):
        kod, duz = self.calistir()
        json_kod, json_cikti = self.calistir("--json")
        sonuclar = json.loads(json_cikti)
        self.assertEqual(kod, json_kod)
        beklenen = [f"{s['status']} {s['name']}: {s['detail']}" for s in sonuclar]
        self.assertEqual(duz.splitlines()[:-1], beklenen)
        self.assertEqual(duz.splitlines()[-1], f"Summary: {len(sonuclar)} ok, 0 warn, 0 fail")
        self.assertTrue(all(set(s) == {"status", "name", "detail"} for s in sonuclar))

    def test_istisna_uyariya_donusur_ve_devam_eder(self):
        with patch.object(doktor, "python_surumu", side_effect=RuntimeError("secret-rule")):
            kod, sonuclar = self.sonuclar()
        self.assertEqual(kod, 0)
        self.assertEqual(sonuclar["Python version"]["status"], "warn")
        self.assertNotIn("secret-rule", str(sonuclar))
        self.assertTrue(any(ad.startswith("Shell ") for ad in sonuclar))

    def test_eski_python_hata(self):
        with patch.object(doktor.sys, "version_info", (3, 8, 20)):
            kod, sonuclar = self.sonuclar()
        self.assertEqual(kod, 1)
        self.assertEqual(sonuclar["Python version"]["status"], "fail")

    def test_denetim_dosyalari_degistirmez_ve_model_calistirmaz(self):
        def durum():
            return {str(p.relative_to(self.klasor)): p.read_bytes()
                    for p in self.klasor.rglob("*") if p.is_file()}

        once = durum()
        gercek = subprocess.run
        with patch.object(doktor.subprocess, "run", wraps=gercek) as komut:
            self.calistir()
        self.assertEqual(once, durum())
        self.assertEqual(len(komut.call_args_list), len(self.betikler))
        for cagri in komut.call_args_list:
            self.assertEqual(cagri.args[0][:2], [self.araclar["bash"], "-n"])
        self.assertNotIn("secret-path", self.calistir()[1])

    def test_komut_satiri_bytecode_bile_yazmaz(self):
        eklenti = self.klasor / "plugin"
        doktor_yolu = eklenti / "skills" / "doctor" / "doctor.py"
        olay_yolu = eklenti / "hooks" / "events.py"
        for kaynak, hedef in ((KOK / "skills" / "doctor" / "doctor.py", doktor_yolu),
                              (KOK / "hooks" / "events.py", olay_yolu)):
            hedef.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(kaynak, hedef)
        once = {p: (p.read_bytes(), p.stat().st_mtime_ns)
                for p in self.klasor.rglob("*") if p.is_file()}
        sonuc = subprocess.run([sys.executable, str(doktor_yolu), "--project", str(self.proje), "--json"],
                               capture_output=True, text=True, check=False)
        self.assertEqual(sonuc.returncode, 1)  # Sahte eklentide external-agent.sh yok.
        self.assertEqual(sonuc.stderr, "")
        self.assertTrue(json.loads(sonuc.stdout))
        sonra = {p: (p.read_bytes(), p.stat().st_mtime_ns)
                 for p in self.klasor.rglob("*") if p.is_file()}
        self.assertEqual(once, sonra)
        self.assertFalse(any(self.klasor.rglob("__pycache__")))


if __name__ == "__main__":
    unittest.main()
