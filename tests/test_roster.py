"""polycrew dinamik kadro ve puan defteri testleri (python3 -m unittest discover tests)."""

from __future__ import annotations

import atexit
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "skills" / "team"))
sys.path.insert(0, str(KOK / "hooks"))
import roster as kadro  # noqa: E402
import events as olay  # noqa: E402


# Günlük verilmeyen çağrı makinenin gerçek olay günlüğünü (kota okumaları dahil) okumasın.
BOS_KLASOR = tempfile.mkdtemp(prefix="polycrew-test-")
atexit.register(shutil.rmtree, BOS_KLASOR, ignore_errors=True)
BOS_GUNLUK = Path(BOS_KLASOR) / "olaylar.jsonl"


def calistir_olay(argv: list[str], gunluk: Path | None = None, defter: Path | None = None):
    env = {**os.environ, "POLYCREW_EVENTS": str(gunluk or BOS_GUNLUK)}
    if defter:
        env["POLYCREW_SCORES"] = str(defter)
    return subprocess.run(
        [sys.executable, str(KOK / "hooks" / "events.py"), *argv],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def calistir_kadro(argv: list[str], defter: Path | None = None, gunluk: Path | None = None,
                   saglayicilar: str = "claude,codex,agy"):
    env = {**os.environ, "POLYCREW_PROVIDERS": saglayicilar,  # makinede kurulu araca bağlı olmasın
           "POLYCREW_EVENTS": str(gunluk or BOS_GUNLUK)}
    if defter:
        env["POLYCREW_SCORES"] = str(defter)
    return subprocess.run(
        [sys.executable, str(KOK / "skills" / "team" / "roster.py"), *argv],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


class KadroVePuanTesti(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.gunluk = Path(self.d.name) / "olaylar.jsonl"
        self.defter = Path(self.d.name) / "puanlar.jsonl"

    def tearDown(self):
        self.d.cleanup()

    def test_eski_puan_kullanimi_defter_yazmaz(self):
        r = calistir_olay(["score", "k1", "4", "eski", "gerekce"], gunluk=self.gunluk, defter=self.defter)
        self.assertEqual(r.returncode, 0)
        self.assertTrue(self.gunluk.exists())
        self.assertFalse(self.defter.exists())

        with open(self.gunluk, encoding="utf-8") as f:
            satirlar = [json.loads(s) for s in f]
        self.assertEqual(len(satirlar), 1)
        self.assertEqual(satirlar[0]["id"], "k1")
        self.assertEqual(satirlar[0]["not"], 4)
        self.assertEqual(satirlar[0]["gerekce"], "eski gerekce")

    def test_bayrakli_kullanim_hem_gunluge_hem_deftere_yazar(self):
        r = calistir_olay(
            [
                "score",
                "k2",
                "5",
                "harika",
                "iş",
                "--worker",
                "codex/gpt-6.1-sol/high",
                "--role",
                "gelistirici",
                "--field",
                "py",
                "--difficulty",
                "O",
                "--quota",
                "12",
                "--duration",
                "100",
                "--fixes",
                "1",
            ],
            gunluk=self.gunluk,
            defter=self.defter,
        )
        self.assertEqual(r.returncode, 0)
        self.assertTrue(self.gunluk.exists())
        self.assertTrue(self.defter.exists())

        with open(self.gunluk, encoding="utf-8") as f:
            o_satirlar = [json.loads(s) for s in f]
        with open(self.defter, encoding="utf-8") as f:
            d_satirlar = [json.loads(s) for s in f]

        self.assertEqual(len(o_satirlar), 1)
        self.assertEqual(len(d_satirlar), 1)

        d = d_satirlar[0]
        self.assertEqual(d["id"], "k2")
        self.assertEqual(d["not"], 5)
        self.assertEqual(d["gerekce"], "harika iş")
        self.assertEqual(d["isci"], "codex/gpt-6.1-sol/high")
        self.assertEqual(d["rol"], "gelistirici")
        self.assertEqual(d["alan"], "py")
        self.assertEqual(d["zorluk"], "O")
        self.assertEqual(d["kota"], 12)
        self.assertEqual(d["sure"], 100)
        self.assertEqual(d["duzeltme"], 1)
        self.assertIn("proje", d)
        self.assertIn("ts", d)

        # kadro.py ekle aracılığıyla da deneme
        r2 = calistir_kadro(
            [
                "add",
                "k3",
                "4",
                "sanat",
                "--worker",
                "claude/sanatci/opus",
                "--role",
                "sanatci",
                "--field",
                "sanat",
            ],
            defter=self.defter,
            gunluk=self.gunluk,
        )
        self.assertEqual(r2.returncode, 0)
        with open(self.defter, encoding="utf-8") as f:
            d_satirlar_yeni = [json.loads(s) for s in f]
        self.assertEqual(len(d_satirlar_yeni), 2)
        self.assertEqual(d_satirlar_yeni[1]["isci"], "claude/sanatci/opus")

    def test_duzeltilmis_puan_formulu(self):
        # (önsel * k + toplam) / (k + n) (önsel 3.5, k = 2)
        self.assertAlmostEqual(kadro.duzeltilmis_puan([]), 3.5)
        self.assertAlmostEqual(kadro.duzeltilmis_puan([5.0]), (7.0 + 5.0) / 3.0)  # 4.0
        self.assertAlmostEqual(kadro.duzeltilmis_puan([4.0, 4.0]), (7.0 + 8.0) / 4.0)  # 3.75
        self.assertAlmostEqual(kadro.duzeltilmis_puan([5.0, 5.0, 5.0]), (7.0 + 15.0) / 5.0)  # 4.4

    def test_filtreler_ve_oneri(self):
        kayitlar = [
            {"isci": "isci-A", "rol": "gelistirici", "alan": "py", "zorluk": "O", "not": 5, "ts": 1000},
            {"isci": "isci-B", "rol": "gelistirici", "alan": "js", "zorluk": "O", "not": 3, "ts": 1000},
            {"isci": "isci-C", "rol": "gozden-gecirici", "alan": "py", "zorluk": "Z", "not": 4, "ts": 1000},
        ]
        with open(self.defter, "w", encoding="utf-8") as f:
            for k in kayitlar:
                f.write(json.dumps(k) + "\n")

        # 1. Rol filtresi
        r1 = calistir_kadro(["suggest", "--role", "gelistirici", "--no-seed"], defter=self.defter)
        self.assertIn("isci-A", r1.stdout)
        self.assertIn("isci-B", r1.stdout)
        self.assertNotIn("isci-C", r1.stdout)

        # 2. Alan filtresi
        r2 = calistir_kadro(["suggest", "--field", "py", "--no-seed"], defter=self.defter)
        self.assertIn("isci-A", r2.stdout)
        self.assertNotIn("isci-B", r2.stdout)
        self.assertIn("isci-C", r2.stdout)

        # 3. Zorluk filtresi
        r3 = calistir_kadro(["suggest", "--difficulty", "Z", "--no-seed"], defter=self.defter)
        self.assertNotIn("isci-A", r3.stdout)
        self.assertNotIn("isci-B", r3.stdout)
        self.assertIn("isci-C", r3.stdout)

        # 4. Filtresiz rol x alan kırılımı
        r4 = calistir_kadro(["suggest", "--no-seed"], defter=self.defter)
        self.assertIn("developer", r4.stdout)
        self.assertIn("reviewer", r4.stdout)
        self.assertIn("py", r4.stdout)
        self.assertIn("js", r4.stdout)

    def test_kadro_oneri_tohumlu_varsayilan_cikti(self):
        r = calistir_kadro(["suggest"], defter=self.defter)
        self.assertEqual(r.returncode, 0)
        self.assertIn("| Role | Field | Best worker |", r.stdout)
        self.assertIn("claude/developer/sonnet", r.stdout)
        self.assertIn("codex/gpt-6.1-sol/high", r.stdout)
        self.assertIn("claude/artist/opus", r.stdout)

    def test_bozuk_satir_atlanir(self):
        with open(self.defter, "w", encoding="utf-8") as f:
            f.write("bozuk bir json satiri\n")
            f.write("{}\n")
            f.write('{"not": 4}\n')  # isci yok
            f.write('{"isci": "temiz/isci", "not": 5, "rol": "sanatci", "alan": "sanat", "ts": 1000}\n')

        r = calistir_kadro(["suggest", "--no-seed"], defter=self.defter)
        self.assertEqual(r.returncode, 0)
        self.assertIn("temiz/isci", r.stdout)

    def test_bos_defter_anlamli_mesaj(self):
        r = calistir_kadro(["suggest", "--no-seed"], defter=self.defter)
        self.assertEqual(r.returncode, 0)
        self.assertIn("No score records found", r.stdout)

    def test_tohum_dosyasi_zorunlu_alanlari_tasir(self):
        tohum_yolu = kadro.tohum_dosyasi()
        self.assertTrue(tohum_yolu.exists())

        zorunlu = {"ts", "proje", "id", "isci", "rol", "alan", "zorluk", "not", "kota", "sure", "gerekce", "kaynak"}
        satir_sayisi = 0
        with open(tohum_yolu, "r", encoding="utf-8") as f:
            for satir in f:
                satir = satir.strip()
                if not satir:
                    continue
                satir_sayisi += 1
                veri = json.loads(satir)
                self.assertTrue(zorunlu.issubset(veri.keys()), f"Eksik alan: {zorunlu - set(veri.keys())} satır: {veri}")
                self.assertEqual(veri["proje"], "Pixlender")
                self.assertEqual(veri["kaynak"], "tohum")
                self.assertIsInstance(veri["not"], (int, float))
                self.assertGreaterEqual(veri["not"], 0)
                self.assertLessEqual(veri["not"], 5)

        self.assertGreaterEqual(satir_sayisi, 10)

    def test_ozet_bos_defter(self):
        r = calistir_kadro(["summary", "--half-life", "0", "--no-seed"], defter=self.defter)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "No records.")

    def test_ozet_pencere_suzmesi_ve_simdi(self):
        # simdi = 1_000_000. 7 gun = 604_800 sn. Esik = 395_200.
        kayitlar = [
            # Pencere ici (ts: 500_000 >= 395_200)
            {"isci": "yeni-isci", "rol": "gelistirici", "alan": "py", "not": 5, "ts": 500_000},
            # Pencere disi / eski (ts: 200_000 < 395_200)
            {"isci": "eski-isci", "rol": "gelistirici", "alan": "py", "not": 5, "ts": 200_000},
            # Gelecek kayit (ts: 1_200_000 > 1_000_000)
            {"isci": "gelecek-isci", "rol": "gelistirici", "alan": "py", "not": 5, "ts": 1_200_000},
        ]
        with open(self.defter, "w", encoding="utf-8") as f:
            for k in kayitlar:
                f.write(json.dumps(k) + "\n")

        r = calistir_kadro(
            ["summary", "--half-life", "0", "--now", "1000000", "--days", "7", "--no-seed"],
            defter=self.defter,
        )
        self.assertEqual(r.returncode, 0)
        # 1970-01-12 UTC
        self.assertIn("Roster summary: last 7 days, 1 records (generated: 1970-01-12)", r.stdout)
        # 0014: sıralama bütün geçmişten; eşit puanda son puanı yeni olan önde, pencere dışı yedek olabilir.
        self.assertIn("| developer | py | yeni-isci | 4.00 | 1 | eski-isci | 4.00 | window, little data |", r.stdout)
        self.assertNotIn("gelecek-isci", r.stdout)  # gelecek tarihli kayıt hiçbir sütunda yok

    def test_ozet_tek_yeni_puan_kadroyu_cevirmez(self):
        # 0014 (Pixlender, 2026-10-19): 11 puanlı eski işçi, pencerede tek puan alan yeniye yer vermez.
        kayitlar = [{"isci": "emektar", "rol": "developer", "alan": "py", "not": 4.5, "ts": 100_000 + i}
                    for i in range(11)]
        kayitlar.append({"isci": "yeni", "rol": "developer", "alan": "py", "not": 4, "ts": 990_000})
        with open(self.defter, "w", encoding="utf-8") as f:
            for k in kayitlar:
                f.write(json.dumps(k) + "\n")
        r = calistir_kadro(["summary", "--half-life", "0", "--now", "1000000", "--days", "7", "--no-seed"],
                           defter=self.defter)
        self.assertIn("| developer | py | emektar | 4.35 | 11 | yeni | 3.67 | stale |", r.stdout)

    def test_ozet_esitlik_kurali(self):
        # 1. Puan esitliginde n'si buyuk olan kazanir
        kayitlar_n = [
            {"isci": "z-isci", "rol": "gelistirici", "alan": "py", "not": 3, "ts": 900_000},
            {"isci": "z-isci", "rol": "gelistirici", "alan": "py", "not": 4, "ts": 900_000},
            {"isci": "z-isci", "rol": "gelistirici", "alan": "py", "not": 3, "ts": 900_000},
            {"isci": "z-isci", "rol": "gelistirici", "alan": "py", "not": 4, "ts": 900_000},
            {"isci": "a-isci", "rol": "gelistirici", "alan": "py", "not": 3, "ts": 900_000},
            {"isci": "a-isci", "rol": "gelistirici", "alan": "py", "not": 4, "ts": 900_000},
        ]
        with open(self.defter, "w", encoding="utf-8") as f:
            for k in kayitlar_n:
                f.write(json.dumps(k) + "\n")

        r1 = calistir_kadro(
            ["summary", "--half-life", "0", "--now", "1000000", "--days", "7", "--no-seed"],
            defter=self.defter,
        )
        self.assertEqual(r1.returncode, 0)
        # z-isci (n=4) Kadro, a-isci (n=2) Yedek
        self.assertIn("| developer | py | z-isci | 3.50 | 4 | a-isci | 3.50 | window |", r1.stdout)

        # 2. Puan ve n esitliginde alfabetik once gelen kazanir
        kayitlar_alfa = [
            {"isci": "b-isci", "rol": "gelistirici", "alan": "py", "not": 5, "ts": 900_000},
            {"isci": "b-isci", "rol": "gelistirici", "alan": "py", "not": 5, "ts": 900_000},
            {"isci": "a-isci", "rol": "gelistirici", "alan": "py", "not": 5, "ts": 900_000},
            {"isci": "a-isci", "rol": "gelistirici", "alan": "py", "not": 5, "ts": 900_000},
        ]
        with open(self.defter, "w", encoding="utf-8") as f:
            for k in kayitlar_alfa:
                f.write(json.dumps(k) + "\n")

        r2 = calistir_kadro(
            ["summary", "--half-life", "0", "--now", "1000000", "--days", "7", "--no-seed"],
            defter=self.defter,
        )
        self.assertEqual(r2.returncode, 0)
        # a-isci Kadro, b-isci Yedek
        self.assertIn("| developer | py | a-isci | 4.25 | 2 | b-isci | 4.25 | window, little data |", r2.stdout)

    def test_ozet_eski_dayanagi(self):
        # Pencerede kayit yok (ts: 100_000 < 395_200, simdi: 1_000_000)
        kayitlar = [
            {"isci": "vefakar-kodcu", "rol": "gelistirici", "alan": "py", "not": 4, "ts": 100_000},
        ]
        with open(self.defter, "w", encoding="utf-8") as f:
            for k in kayitlar:
                f.write(json.dumps(k) + "\n")

        r = calistir_kadro(
            ["summary", "--half-life", "0", "--now", "1000000", "--days", "7", "--no-seed"],
            defter=self.defter,
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("Roster summary: last 7 days, 0 records", r.stdout)
        self.assertIn("| developer | py | vefakar-kodcu | 3.67 | 1 | — | — | stale |", r.stdout)

    def test_ozet_veri_az_ve_pencere_dayanagi(self):
        # n < 3 -> "pencere, veri az", n >= 3 -> "pencere"
        kayitlar = [
            # az-veri: n = 2 (< 3)
            {"isci": "az-kodcu", "rol": "gelistirici", "alan": "js", "not": 5, "ts": 900_000},
            {"isci": "az-kodcu", "rol": "gelistirici", "alan": "js", "not": 5, "ts": 900_000},
            # cok-veri: n = 3 (>= 3)
            {"isci": "cok-kodcu", "rol": "gelistirici", "alan": "py", "not": 5, "ts": 900_000},
            {"isci": "cok-kodcu", "rol": "gelistirici", "alan": "py", "not": 5, "ts": 900_000},
            {"isci": "cok-kodcu", "rol": "gelistirici", "alan": "py", "not": 5, "ts": 900_000},
        ]
        with open(self.defter, "w", encoding="utf-8") as f:
            for k in kayitlar:
                f.write(json.dumps(k) + "\n")

        r = calistir_kadro(
            ["summary", "--half-life", "0", "--now", "1000000", "--days", "7", "--no-seed"],
            defter=self.defter,
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("| developer | js | az-kodcu | 4.25 | 2 | — | — | window, little data |", r.stdout)
        self.assertIn("| developer | py | cok-kodcu | 4.40 | 3 | — | — | window |", r.stdout)

    def test_ozet_yedek_durumlari(self):
        # Iki isci varsa yedek ve puani gorunur, tek isci varsa "—"
        kayitlar = [
            {"isci": "as-isci", "rol": "sanatci", "alan": "sanat", "not": 5, "ts": 900_000},
            {"isci": "yedek-isci", "rol": "sanatci", "alan": "sanat", "not": 4, "ts": 900_000},
            {"isci": "tek-isci", "rol": "gelistirici", "alan": "py", "not": 5, "ts": 900_000},
        ]
        with open(self.defter, "w", encoding="utf-8") as f:
            for k in kayitlar:
                f.write(json.dumps(k) + "\n")

        r = calistir_kadro(
            ["summary", "--half-life", "0", "--now", "1000000", "--days", "7", "--no-seed"],
            defter=self.defter,
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("| artist | art | as-isci | 4.00 | 1 | yedek-isci | 3.67 | window, little data |", r.stdout)
        self.assertIn("| developer | py | tek-isci | 4.00 | 1 | — | — | window, little data |", r.stdout)

    def test_ozet_siralama_rol_sonra_alan(self):
        kayitlar = [
            {"isci": "isci-3", "rol": "sanatci", "alan": "sanat", "not": 5, "ts": 900_000},
            {"isci": "isci-2", "rol": "gelistirici", "alan": "py", "not": 5, "ts": 900_000},
            {"isci": "isci-1", "rol": "gelistirici", "alan": "js", "not": 5, "ts": 900_000},
        ]
        with open(self.defter, "w", encoding="utf-8") as f:
            for k in kayitlar:
                f.write(json.dumps(k) + "\n")

        r = calistir_kadro(
            ["summary", "--half-life", "0", "--now", "1000000", "--days", "7", "--no-seed"],
            defter=self.defter,
        )
        self.assertEqual(r.returncode, 0)
        satirlar = [s for s in r.stdout.splitlines() if s.startswith("|") and not s.startswith("| Role") and not s.startswith("|---")]
        self.assertEqual(len(satirlar), 3)
        self.assertIn("| artist | art |", satirlar[0])
        self.assertIn("| developer | js |", satirlar[1])
        self.assertIn("| developer | py |", satirlar[2])

    def test_eski_ve_yeni_adlar_ayni_kovada(self):
        """0007: 0.5.0 öncesinin rol, alan, zorluk ve işçi adları okurken yeni ada çevrilir."""
        kayitlar = [
            {"isci": "claude/gelistirici/sonnet", "rol": "polycrew:gelistirici", "alan": "py", "zorluk": "Z", "not": 4, "ts": 900_000},
            {"isci": "claude/developer/sonnet", "rol": "developer", "alan": "py", "zorluk": "H", "not": 5, "ts": 900_001},
            {"isci": "codex/x", "rol": "gozden-gecirici", "alan": "inceleme", "zorluk": "orta", "not": 5, "ts": 900_002},
        ]
        with open(self.defter, "w", encoding="utf-8") as f:
            for k in kayitlar:
                f.write(json.dumps(k) + "\n")
        onceki = self.defter.read_text(encoding="utf-8")

        for filtre in (["--role", "developer", "--field", "py", "--difficulty", "H"],
                       ["--role", "gelistirici", "--difficulty", "Z"]):
            r = calistir_kadro(["suggest", *filtre, "--no-seed", "--half-life", "0"], defter=self.defter)
            self.assertEqual(r.returncode, 0)
            self.assertIn("| claude/developer/sonnet-5-5 | 2 |", r.stdout)  # sürümsüz eski satır (0008)
            self.assertNotIn("gelistirici", r.stdout)

        r = calistir_kadro(["summary", "--half-life", "0", "--now", "1000000", "--no-seed"], defter=self.defter)
        self.assertIn("| reviewer | review | codex/x |", r.stdout)
        self.assertEqual(self.defter.read_text(encoding="utf-8"), onceki)  # dosya değişmez

    # ---- 0008: zaman ağırlığı, sürümlü işçi adı, "dene" önerisi

    def _defter(self, kayitlar):
        with open(self.defter, "w", encoding="utf-8") as f:
            for k in kayitlar:
                f.write(json.dumps(k) + "\n")

    def test_agirlik_yari_omur(self):
        gun = 86400
        self.assertAlmostEqual(kadro.agirlik(0, 30 * gun, 30), 0.5)
        self.assertAlmostEqual(kadro.agirlik(0, 60 * gun, 30), 0.25)
        self.assertEqual(kadro.agirlik(0, 60 * gun, 0), 1.0)  # 0 soldurmayı kapatır
        self.assertEqual(kadro.agirlik(None, 60 * gun, 30), 1.0)  # ts yoksa tam ağırlık
        self.assertEqual(kadro.agirlik(90 * gun, 60 * gun, 30), 1.0)  # gelecekteki ts
        # Ağırlıksız çağrı eski sonucu verir; yarım ağırlıklı tek 5 puan önsele daha yakın kalır.
        self.assertAlmostEqual(kadro.duzeltilmis_puan([5.0]), 4.0)
        self.assertAlmostEqual(kadro.duzeltilmis_puan([5.0], agirliklar=[0.5]), (7.0 + 2.5) / 2.5)

    def test_eski_iyi_puan_yeni_puanin_altina_duser(self):
        gun, simdi = 86400, 400 * 86400
        self._defter(
            [{"isci": "eski-usta", "rol": "developer", "alan": "py", "not": 5, "ts": simdi - 200 * gun}] * 4
            + [{"isci": "yeni-isci", "rol": "developer", "alan": "py", "not": 4, "ts": simdi - gun}] * 4
        )
        ortak = ["suggest", "--role", "developer", "--no-seed", "--now", str(simdi)]
        solmayan = calistir_kadro([*ortak, "--half-life", "0"], defter=self.defter).stdout.splitlines()
        solan = calistir_kadro(ortak, defter=self.defter).stdout.splitlines()
        self.assertIn("eski-usta", solmayan[2])
        self.assertIn("yeni-isci", solan[2])
        eski = next(s for s in solan if "eski-usta" in s)
        self.assertIn("| 4 | 0.0 |", eski)  # ham n 4, etkin n ~0
        self.assertIn("little data", eski)
        self.assertNotIn("little data", solan[2])

    def test_surumsuz_eski_claude_satiri_bugunku_surum_okunur(self):
        sinir = olay.SURUM_SINIRI
        once = olay.kayit_adlari({"isci": "claude/gelistirici/sonnet", "ts": sinir - 1})
        sonra = olay.kayit_adlari({"isci": "claude/developer/sonnet", "ts": sinir + 1})
        self.assertEqual(once["isci"], "claude/developer/sonnet-5-5")
        self.assertEqual(sonra["isci"], "claude/developer/sonnet")
        self.assertEqual(olay.kayit_adlari({"isci": "claude/artist/opus", "ts": 1})["isci"], "claude/artist/opus-5-5")
        self.assertEqual(olay.kayit_adlari({"isci": "codex/gpt-6.1-sol/high", "ts": 1})["isci"], "codex/gpt-6.1-sol/high")

    def test_puan_claude_iscisine_surumu_ekler(self):
        transkript = self.gunluk.parent / "agent.jsonl"
        transkript.write_text(
            json.dumps({"message": {"model": "<synthetic>"}}) + "\n"
            + json.dumps({"message": {"model": "claude-sonnet-9-1"}}) + "\n", encoding="utf-8")
        with open(self.gunluk, "w", encoding="utf-8") as f:
            f.write(json.dumps({"tur": "agent_bitti", "ts": 5, "id": "ag7", "rol": "polycrew:developer",
                                "kaynak": "claude", "transkript": str(transkript)}) + "\n")
        r = calistir_olay(["score", "ag7", "4", "--worker", "claude/developer/sonnet", "--role", "developer"],
                          gunluk=self.gunluk, defter=self.defter)
        self.assertEqual((r.returncode, r.stderr), (0, ""))
        d = json.loads(self.defter.read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(d["isci"], "claude/developer/sonnet-9-1")

        # İş bulunamazsa ad değişmez ve uyarı çıkar; dış işçiye ve sürümlü ada dokunulmaz.
        r = calistir_olay(["score", "yok", "4", "--worker", "claude/developer/sonnet"],
                          gunluk=self.gunluk, defter=self.defter)
        self.assertEqual(r.returncode, 0)
        self.assertIn("model version not found", r.stderr)
        r = calistir_olay(["score", "ag7", "4", "--worker", "claude/developer/opus-7"],
                          gunluk=self.gunluk, defter=self.defter)
        self.assertEqual(r.stderr, "")
        satirlar = [json.loads(s)["isci"] for s in self.defter.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(satirlar[-2:], ["claude/developer/sonnet", "claude/developer/opus-7"])
        self.assertEqual(olay.surumlu_isci("claude/developer/opus", "claude-sonnet-9-1"), "claude/developer/opus")

    def test_kanca_biten_agentin_modelini_yazar(self):
        transkript = self.gunluk.parent / "t.jsonl"
        transkript.write_text(json.dumps({"message": {"model": "claude-opus-9-9"}}) + "\n", encoding="utf-8")
        yuk = {"hook_event_name": "SubagentStop", "agent_id": "a1", "agent_type": "polycrew:artist",
               "agent_transcript_path": str(transkript)}
        self.assertEqual(olay.kancadan(yuk)["model"], "claude-opus-9-9")
        self.assertNotIn("model", olay.kancadan({**yuk, "agent_transcript_path": "/yok/yok.jsonl"}))
        self.assertNotIn("model", olay.kancadan({**yuk, "hook_event_name": "SubagentStart"}))

    def test_ozet_dene_sutunu(self):
        simdi = 1_000_000
        self._defter(
            [{"isci": "usta", "rol": "developer", "alan": "py", "not": 5, "ts": simdi - 10}] * 4
            + [{"isci": "yedek", "rol": "developer", "alan": "py", "not": 4, "ts": simdi - 10}] * 4
            + [{"isci": "cirak", "rol": "developer", "alan": "js", "not": 4, "ts": simdi - 10}] * 4
            + [{"isci": "ressam", "rol": "artist", "alan": "art", "not": 5, "ts": simdi - 10}] * 4
            + [{"isci": "kotu", "rol": "developer", "alan": "js", "not": 1, "ts": simdi - 10}]
        )
        r = calistir_kadro(["summary", "--now", str(simdi), "--no-seed"], defter=self.defter)
        satir = {tuple(h.strip() for h in s.split("|")[1:3]): [h.strip() for h in s.split("|")] for s in r.stdout.splitlines() if s.startswith("| ")}
        self.assertEqual(satir[("Role", "Field")][-2], "Try")
        self.assertEqual(satir[("developer", "py")][-2], "cirak")  # aynı rolde, bu alanda verisi yok
        self.assertEqual(satir[("developer", "js")][-2], "usta")  # adaylardan rolde en iyisi
        self.assertNotIn("kotu", [v[-2] for v in satir.values()])  # önselin altına düşen aday olmaz
        self.assertEqual(satir[("artist", "art")][-2], "—")  # rolde başka işçi yok

    # ---- 0009: yeniden puanlama, maliyet eşitlik bozucu, kurulu olmayan araç

    def test_ayni_isin_sonraki_puani_oncekinin_yerine_gecer(self):
        self._defter([
            {"isci": "w", "rol": "developer", "alan": "py", "proje": "P", "id": "is1", "not": 2, "ts": 10},
            {"isci": "w", "rol": "developer", "alan": "py", "proje": "P", "id": "is1", "not": 5, "ts": 20},
            {"isci": "w", "rol": "developer", "alan": "py", "proje": "Q", "id": "is1", "not": 3, "ts": 30},  # başka proje
            {"isci": "w", "rol": "developer", "alan": "py", "not": 4, "ts": 40},  # id yok
            {"isci": "w", "rol": "developer", "alan": "py", "not": 4, "ts": 50},
        ])
        onceki = self.defter.read_text(encoding="utf-8")
        r = calistir_kadro(["suggest", "--role", "developer", "--no-seed", "--half-life", "0"], defter=self.defter)
        self.assertIn("| w | 4 | 4.0 | 4.0 |", r.stdout)  # 5, 3, 4, 4: eski 2 sayılmaz
        self.assertEqual(self.defter.read_text(encoding="utf-8"), onceki)

    def _maliyet(self, ust, alt, *ek):
        self._defter(
            [{"isci": "pahali", "rol": "developer", "alan": "py", "not": ust["not"], "ts": 1, **ust["ek"]}] * 4
            + [{"isci": "ucuz", "rol": "developer", "alan": "py", "not": alt["not"], "ts": 1, **alt["ek"]}] * 4
        )
        r = calistir_kadro(["suggest", "--role", "developer", "--no-seed", "--half-life", "0", *ek], defter=self.defter)
        return [s for s in r.stdout.splitlines() if s.startswith("| pahali") or s.startswith("| ucuz")]

    def test_yakin_puanda_ucuz_olan_one_gecer(self):
        # 4 kayıtta 4,1 ile 4,0 ortalaması düzeltilmiş puanda 0,07 fark eder (yakın).
        hizli = self._maliyet({"not": 4.1, "ek": {"sure": 1000}}, {"not": 4.0, "ek": {"sure": 600}})
        self.assertTrue(hizli[0].startswith("| ucuz"))
        self.assertIn("faster", hizli[0])
        kapali = self._maliyet({"not": 4.1, "ek": {"sure": 1000}}, {"not": 4.0, "ek": {"sure": 600}}, "--no-cost")
        self.assertTrue(kapali[0].startswith("| pahali"))
        uzak = self._maliyet({"not": 4.6, "ek": {"sure": 1000}}, {"not": 4.0, "ek": {"sure": 600}})
        self.assertTrue(uzak[0].startswith("| pahali"))  # fark 0,10'dan büyük
        az_fark = self._maliyet({"not": 4.1, "ek": {"sure": 1000}}, {"not": 4.0, "ek": {"sure": 900}})
        self.assertTrue(az_fark[0].startswith("| pahali"))  # %20'den az kısa
        verisiz = self._maliyet({"not": 4.1, "ek": {}}, {"not": 4.0, "ek": {"sure": 600}})
        self.assertTrue(verisiz[0].startswith("| pahali"))
        # Kota ikisinde de varsa süreye değil kotaya bakılır.
        kota = self._maliyet({"not": 4.1, "ek": {"sure": 600, "kota": 30}}, {"not": 4.0, "ek": {"sure": 1000, "kota": 10}})
        self.assertTrue(kota[0].startswith("| ucuz"))
        self.assertIn("cheaper", kota[0])

    def test_kurulu_olmayan_aracin_iscileri_onerilmez(self):
        self._defter(
            [{"isci": "codex/gpt/high", "rol": "developer", "alan": "py", "not": 5, "ts": 1}] * 4
            + [{"isci": "agy/gemini", "rol": "developer", "alan": "py", "not": 5, "ts": 1}] * 4
            + [{"isci": "claude/developer/sonnet-9", "rol": "developer", "alan": "py", "not": 4, "ts": 1}] * 4
            + [{"isci": "oneksiz", "rol": "developer", "alan": "py", "not": 3, "ts": 1}]
        )
        for komut in (["suggest", "--role", "developer"], ["summary", "--now", "100"]):
            r = calistir_kadro([*komut, "--no-seed", "--half-life", "0"], defter=self.defter, saglayicilar="claude")
            self.assertNotIn("codex/", r.stdout)
            self.assertNotIn("agy/", r.stdout)
            self.assertIn("claude/developer/sonnet-9", r.stdout)
            self.assertIn("Left out (not installed): agy, codex", r.stdout)
        r = calistir_kadro(["suggest", "--role", "developer", "--no-seed", "--providers", "codex"], defter=self.defter)
        self.assertIn("codex/gpt/high", r.stdout)
        self.assertIn("oneksiz", r.stdout)
        self.assertIn("Left out (not installed): agy", r.stdout)

    # ---- 0011: takım yapısı önerisi

    def test_yapi_onerisi(self):
        def k(isci, rol, puan, adet=4):
            return [{"isci": isci, "rol": rol, "alan": "x", "not": puan, "ts": 1}] * adet
        self._defter(
            k("claude/developer/sonnet-9", "developer", 5) + k("codex/g/high", "developer", 3.6)
            + k("claude/reviewer/sonnet-9", "reviewer", 4) + k("codex/g/high", "reviewer", 4.2)
            + k("claude/artist/opus-9", "artist", 5)
            + k("agy/gem", "researcher", 4)
            + k("claude/designer/opus-9", "designer", 5, adet=1) + k("codex/g/high", "designer", 5, adet=1)
            + k("agy/kotu", "developer", 1, adet=3)
        )
        with open(self.gunluk, "w", encoding="utf-8") as f:
            for e in ({"tur": "agent_basladi", "ts": 100, "id": "a", "rol": "polycrew:developer", "kaynak": "claude"},
                      {"tur": "agent_basladi", "ts": 110, "id": "b", "rol": "polycrew:reviewer", "kaynak": "claude"},
                      {"tur": "agent_bitti", "ts": 150, "id": "a", "rol": "polycrew:developer", "kaynak": "claude"},
                      {"tur": "agent_bitti", "ts": 160, "id": "b", "rol": "polycrew:reviewer", "kaynak": "claude"},
                      {"tur": "agent_basladi", "ts": 200, "id": "c", "rol": "polycrew:artist", "kaynak": "claude"},
                      {"tur": "agent_bitti", "ts": 210, "id": "c", "rol": "polycrew:artist", "kaynak": "claude"}):
                f.write(json.dumps(e) + "\n")
        ortak = ["structure", "--no-seed", "--half-life", "0", "--now", "1000"]
        r = calistir_kadro(ortak, defter=self.defter, gunluk=self.gunluk)
        self.assertEqual(r.returncode, 0, r.stderr)
        oneri = {s.split("|")[1].strip(): s.split("|")[-2].strip() for s in r.stdout.splitlines() if s.startswith("| ")}
        self.assertEqual(oneri["developer"], "prefer Claude")
        self.assertEqual(oneri["reviewer"], "equal: external first, keep Claude quota")
        self.assertEqual(oneri["artist"], "only Claude measured")
        self.assertEqual(oneri["researcher"], "only external measured")
        self.assertEqual(oneri["designer"], "not enough data")
        self.assertIn("Avoid: agy/kotu as developer", r.stdout)
        self.assertNotIn("Avoid: codex", r.stdout)
        self.assertIn("3 jobs in the last 30 days, at most 2 running at once, 0 lead(s) started", r.stdout)
        self.assertIn("a lead is not needed at this size", r.stdout)
        self.assertIn("the user decides", r.stdout)

        # Lider başlatıldıysa "gerek yok" cümlesi çıkmaz (eski rol adı da sayılır).
        with open(self.gunluk, "a", encoding="utf-8") as f:
            f.write(json.dumps({"tur": "agent_basladi", "ts": 300, "id": "l", "rol": "polycrew:lider", "kaynak": "claude"}) + "\n")
            f.write(json.dumps({"tur": "agent_bitti", "ts": 310, "id": "l", "rol": "polycrew:lider", "kaynak": "claude"}) + "\n")
        r = calistir_kadro(ortak, defter=self.defter, gunluk=self.gunluk)
        self.assertIn("1 lead(s) started", r.stdout)
        self.assertNotIn("not needed", r.stdout)

        # Dış araç kurulu değilse yalnız Claude tarafı kalır.
        r = calistir_kadro(ortak, defter=self.defter, gunluk=self.gunluk, saglayicilar="claude")
        oneri = {s.split("|")[1].strip(): s.split("|")[-2].strip() for s in r.stdout.splitlines() if s.startswith("| ")}
        self.assertEqual(oneri["developer"], "only Claude measured")
        self.assertNotIn("researcher", oneri)
        self.assertNotIn("Avoid", r.stdout)

    # ---- 0014 C listesi

    def test_puan_tek_satir_onay_yazar(self):
        r = calistir_olay(["score", "k7", "4", "iyi", "--worker", "codex/g/high"], gunluk=self.gunluk, defter=self.defter)
        self.assertEqual((r.returncode, r.stdout), (0, "Scored k7: 4 (worker codex/g/high)\n"))
        r = calistir_olay(["score", "k8", "3"], gunluk=self.gunluk, defter=self.defter)
        self.assertEqual(r.stdout, "Scored k8: 3 (worker -)\n")

    def test_yardim_cikis_kodu_sifir(self):
        for bayrak in ("--help", "-h"):
            r = calistir_kadro([bayrak])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Usage:", r.stdout)
        self.assertEqual(calistir_kadro([]).returncode, 2)  # argümansız hâlâ hata
        self.assertEqual(calistir_kadro(["yok"]).returncode, 2)

    def _kota_olayi(self, ts, *kovalar):
        with open(self.gunluk, "a", encoding="utf-8") as f:
            f.write(json.dumps({"tur": "kota", "ts": ts, "kovalar": list(kovalar)}) + "\n")

    def test_yapi_az_veri_claude_ve_kalan_kota(self):
        def k(isci, rol, puan, adet):
            return [{"isci": isci, "rol": rol, "alan": "x", "not": puan, "ts": 1}] * adet
        self._defter(k("claude/developer/sonnet-9", "developer", 5, 1) + k("codex/g/high", "developer", 4, 4)
                     + k("codex/g/high", "reviewer", 4, 4))
        simdi = 100000
        self._kota_olayi(simdi - 1000,
                         {"saglayici": "codex", "grup": "Codex", "pencere": "5 saat", "kullanilan": 81.0},
                         {"saglayici": "codex", "grup": "Codex", "pencere": "hafta", "kullanilan": 23.0},
                         {"saglayici": "agy", "grup": "agy: Gemini", "pencere": "5 saat", "kullanilan": 0})
        self._kota_olayi(simdi - 6 * 3600,
                         {"saglayici": "claude", "grup": "Claude", "pencere": "5 saat", "kullanilan": 60.0},
                         {"saglayici": "claude", "grup": "Claude", "pencere": "bağlam", "kullanilan": 90.0, "token": 1})
        ortak = ["structure", "--no-seed", "--half-life", "0", "--now", str(simdi)]
        r = calistir_kadro(ortak, defter=self.defter, gunluk=self.gunluk)
        self.assertEqual(r.returncode, 0, r.stderr)
        oneri = {s.split("|")[1].strip(): s.split("|")[-2].strip() for s in r.stdout.splitlines() if s.startswith("| ")}
        self.assertEqual(oneri["developer"], "Claude: little data")
        self.assertEqual(oneri["reviewer"], "only external measured")  # Claude hiç yok
        self.assertIn("- codex: 5 hours 19% left (low), week 77% left", r.stdout)
        self.assertIn("- agy: Gemini: 5 hours 100% left", r.stdout)
        self.assertIn("- claude: 5 hours 40% left (stale: older than 5 hours)", r.stdout)
        self.assertNotIn("bağlam", r.stdout)  # bağlam doluluğu kota değildir
        # Okuması olmayan sağlayıcı ve kapatma.
        r = calistir_kadro(ortak, defter=self.defter, gunluk=self.gunluk, saglayicilar="claude,agy")
        self.assertNotIn("- codex", r.stdout)
        self.assertIn("- agy: Gemini", r.stdout)
        r = calistir_kadro([*ortak, "--no-quota"], defter=self.defter, gunluk=self.gunluk)
        self.assertNotIn("Quota left", r.stdout)

    def test_eski_ortam_degiskeni_yedek_olarak_okunur(self):
        env = {k: v for k, v in os.environ.items() if k not in ("POLYCREW_EVENTS", "POLYCREW_SCORES")}
        env.update(POLYCREW_OLAYLAR=str(self.gunluk), POLYCREW_PUANLAR=str(self.defter))
        r = subprocess.run([sys.executable, str(KOK / "hooks" / "events.py"), "score", "k9", "3", "--worker", "w/x"],
                           capture_output=True, text=True, env=env, check=False)
        self.assertEqual(r.returncode, 0)
        self.assertTrue(self.gunluk.exists() and self.defter.exists())


SIMDI = 100000  # kota testlerinde --now; okumalar bundan 1000 sn önce (taze) ya da saatler önce (bayat)


def codex_kovalari(bes_saat_kullanilan, hafta_kullanilan, **ek):
    return [{"saglayici": "codex", "grup": "Codex", "pencere": "5 saat", "kullanilan": bes_saat_kullanilan, **ek},
            {"saglayici": "codex", "grup": "Codex", "pencere": "hafta", "kullanilan": hafta_kullanilan, **ek}]


class KotaSiralamaTesti(unittest.TestCase):
    """Az kotası kalan işçi satırda alta iner ve "low quota" yazılır; okuma yok ya da bayatsa sıra aynı kalır."""

    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.gunluk = Path(self.d.name) / "olaylar.jsonl"
        self.defter = Path(self.d.name) / "puanlar.jsonl"
        self.defter_yaz(("codex/gpt-x/high", 5), ("claude/developer/sonnet-9", 4),
                        ("agy/gemini-x-high", 3.2), ("agy/claude-opus-x", 3))

    def tearDown(self):
        self.d.cleanup()

    def defter_yaz(self, *isciler):
        with open(self.defter, "w", encoding="utf-8") as f:
            for isci, puan in isciler:
                for _ in range(4):
                    f.write(json.dumps({"isci": isci, "rol": "developer", "alan": "py", "not": puan,
                                        "ts": SIMDI - 100}) + "\n")

    def kota(self, ts, kovalar):
        with open(self.gunluk, "a", encoding="utf-8") as f:
            f.write(json.dumps({"tur": "kota", "ts": ts, "kovalar": kovalar}) + "\n")

    def kos(self, *argv):
        r = calistir_kadro([*argv, "--no-seed", "--half-life", "0", "--now", str(SIMDI)],
                           defter=self.defter, gunluk=self.gunluk)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def siralama(self, *ek):
        """suggest tablosunun (işçi, durum) sırası ve bütün çıktı."""
        cikti = self.kos("suggest", "--role", "developer", *ek)
        satirlar = [[h.strip() for h in s.split("|")[1:-1]] for s in cikti.splitlines()
                    if s.startswith("| ") and not s.startswith("| Worker")]
        return [(s[0], s[-1]) for s in satirlar], cikti

    def ozet_satiri(self):
        satir = [s for s in self.kos("summary", "--days", "7").splitlines() if s.startswith("| developer | py")][0]
        return [h.strip() for h in satir.split("|")[1:-1]]  # rol, alan, kadro, puan, n, yedek, yedek puanı, dayanak, dene

    def test_az_kalan_isci_alta_iner_ve_isaretlenir(self):
        self.kota(SIMDI - 1000, codex_kovalari(85, 30))  # 5 saatte %15 kaldı
        sira, _ = self.siralama()
        self.assertEqual([i for i, _ in sira][:2], ["claude/developer/sonnet-9", "agy/gemini-x-high"])
        self.assertEqual(sira[-1], ("codex/gpt-x/high", "low quota"))
        # Eşik kesin "altı": tam %20 kalan düşmez; haftalıkta %10'dan az kalan düşer.
        self.kota(SIMDI - 900, codex_kovalari(80, 30))
        self.assertEqual(self.siralama()[0][0], ("codex/gpt-x/high", ""))
        self.kota(SIMDI - 800, codex_kovalari(10, 91))
        self.assertEqual(self.siralama()[0][-1], ("codex/gpt-x/high", "low quota"))

    def test_esik_bayragi(self):
        self.kota(SIMDI - 1000, codex_kovalari(85, 30))
        self.assertEqual(self.siralama("--quota-low-5h", "10")[0][0][0], "codex/gpt-x/high")
        self.assertEqual(self.siralama("--quota-low-5h", "16")[0][-1][0], "codex/gpt-x/high")
        self.kota(SIMDI - 900, codex_kovalari(10, 91))
        self.assertEqual(self.siralama("--quota-low-week", "5")[0][0][0], "codex/gpt-x/high")

    def test_no_quota_sirayi_degistirmez(self):
        self.kota(SIMDI - 1000, codex_kovalari(99, 99))
        sira, cikti = self.siralama("--no-quota")
        self.assertEqual(sira[0], ("codex/gpt-x/high", ""))
        self.assertNotIn("Quota:", cikti)

    def test_okuma_yoksa_ya_da_bayatsa_sira_ayni_not_var(self):
        sira, cikti = self.siralama()  # günlük boş
        self.assertEqual(sira[0], ("codex/gpt-x/high", ""))
        self.assertIn("Quota: no quota reading for agy, codex;", cikti)
        # 6 saat önceki okumada 5 saatlik kova bayat, haftalık taze ve yeterli: sıra aynı, Codex için not yok.
        self.kota(SIMDI - 6 * 3600, codex_kovalari(99, 30))
        sira, cikti = self.siralama()
        self.assertEqual(sira[0], ("codex/gpt-x/high", ""))
        self.assertNotIn("codex", cikti.split("Quota:")[1])
        # Bir günden eski haftalık da bayat: Codex'in iki kovası da bayatsa not "stale" der.
        self.gunluk.unlink()
        self.kota(SIMDI - 30 * 3600, codex_kovalari(99, 99))
        sira, cikti = self.siralama()
        self.assertEqual(sira[0], ("codex/gpt-x/high", ""))
        self.assertIn("stale quota reading for codex", cikti)

    def test_sifirlanma_gecmisse_bayat(self):
        # Ölçümden sonra penceresi yenilenmiş: %99 dolu görünse de sayılmaz.
        self.kota(SIMDI - 1000, codex_kovalari(99, 99, yenilenir_epoch=SIMDI - 500))
        sira, cikti = self.siralama()
        self.assertEqual(sira[0], ("codex/gpt-x/high", ""))
        self.assertIn("stale quota reading for codex", cikti)
        # Sıfırlanma gelecekteyse sayılır.
        self.kota(SIMDI - 400, codex_kovalari(99, 99, yenilenir_epoch=SIMDI + 500))
        self.assertEqual(self.siralama()[0][-1], ("codex/gpt-x/high", "low quota"))

    def test_agy_modelin_grubuna_bakar(self):
        self.kota(SIMDI - 1000, [
            {"saglayici": "agy", "grup": "agy: Claude/GPT", "pencere": "5 saat", "kullanilan": 100},
            {"saglayici": "agy", "grup": "agy: Gemini", "pencere": "5 saat", "kullanilan": 0}])
        durum = dict(self.siralama()[0])
        self.assertEqual((durum["agy/claude-opus-x"], durum["agy/gemini-x-high"]), ("low quota", ""))
        self.kota(SIMDI - 900, [{"saglayici": "agy", "grup": "agy: Gemini", "pencere": "5 saat", "kullanilan": 100}])
        self.assertEqual(dict(self.siralama()[0])["agy/gemini-x-high"], "low quota")
        self.assertEqual(kadro.isci_kota_grubu("agy/gemini-4-argon-high/-"), ("agy", "Gemini 4 Argon"))
        self.assertEqual(kadro.isci_kota_grubu("agy/gpt-oss-120b"), ("agy", "agy: Claude/GPT"))
        self.assertEqual(kadro.isci_kota_grubu("codex/gpt-x/high"), ("codex", "Codex"))
        self.assertIsNone(kadro.isci_kota_grubu("pahali"))

    def test_claude_okumasi_varsa_kullanilir_yoksa_dokunulmaz(self):
        sira, cikti = self.siralama()
        self.assertEqual(dict(sira)["claude/developer/sonnet-9"], "")
        self.assertNotIn("claude", cikti.split("Quota:")[1])  # Claude için "okuma yok" notu yazılmaz
        self.kota(SIMDI - 1000, [
            {"saglayici": "claude", "grup": "Claude", "pencere": "5 saat", "kullanilan": 95},
            {"saglayici": "claude", "grup": "Claude", "pencere": "bağlam", "kullanilan": 5, "token": 1}])
        self.assertEqual(dict(self.siralama()[0])["claude/developer/sonnet-9"], "low quota")

    def test_ozet_kadro_sonrakine_gecer_dusen_yedege_iner(self):
        self.kota(SIMDI - 1000, codex_kovalari(85, 30) + [
            {"saglayici": "agy", "grup": "agy: Gemini", "pencere": "5 saat", "kullanilan": 0}])
        hucre = self.ozet_satiri()
        self.assertEqual((hucre[2], hucre[5]), ("claude/developer/sonnet-9", "agy/gemini-x-high"))
        # Düşen işçi kadrodan gider ama tablodan silinmez: yedeğe iner (iki işçi kalınca).
        self.defter_yaz(("codex/gpt-x/high", 5), ("claude/developer/sonnet-9", 4))
        hucre = self.ozet_satiri()
        self.assertEqual((hucre[2], hucre[5], hucre[7]),
                         ("claude/developer/sonnet-9", "codex/gpt-x/high", "window, backup low quota"))
        # İkisi de az: sıra puana göre kalır, kadro işçisi işaretlenir.
        self.kota(SIMDI - 500, [{"saglayici": "claude", "grup": "Claude", "pencere": "5 saat", "kullanilan": 95}])
        hucre = self.ozet_satiri()
        self.assertEqual((hucre[2], hucre[5], hucre[7]),
                         ("codex/gpt-x/high", "claude/developer/sonnet-9", "window, low quota"))
        # --no-quota hepsini kapatır.
        satir = [s for s in self.kos("summary", "--days", "7", "--no-quota").splitlines() if s.startswith("| developer | py")][0]
        self.assertIn("| codex/gpt-x/high | 4.50 | 4 | claude/developer/sonnet-9 |", satir)
        self.assertNotIn("low quota", satir)

    def test_ucuz_ve_az_kotali_isaretleri_birlikte(self):
        with open(self.defter, "w", encoding="utf-8") as f:
            for isci, puan, sure in (("pahali/x/high", 4.1, 1000), ("codex/ucuz/high", 4.0, 600)):
                for _ in range(4):
                    f.write(json.dumps({"isci": isci, "rol": "developer", "alan": "py", "not": puan, "sure": sure,
                                        "ts": SIMDI - 100}) + "\n")
        self.assertEqual(self.siralama()[0][0], ("codex/ucuz/high", "faster"))
        self.kota(SIMDI - 1000, codex_kovalari(95, 10))
        self.assertEqual(self.siralama()[0], [("pahali/x/high", ""), ("codex/ucuz/high", "faster, low quota")])

    def test_yenilenme_metni_eski_olaylarda_cozulur(self):
        olcum = 1794400000.0  # 2026-11-12 UTC
        agy = kadro._kota_yenilenme({"saglayici": "agy", "yenilenir": "11-12T16:07"}, olcum)
        self.assertEqual(agy, datetime(2026, 11, 12, 16, 7, tzinfo=timezone.utc).timestamp())
        codex = kadro._kota_yenilenme({"saglayici": "codex", "yenilenir": "11-16 15:43"}, olcum)
        self.assertEqual(codex, datetime(2026, 11, 16, 15, 43).timestamp())  # yerel saat
        self.assertEqual(kadro._kota_yenilenme({"yenilenir_epoch": 5.0, "yenilenir": "11-16 15:43"}, olcum), 5.0)
        self.assertIsNone(kadro._kota_yenilenme({"yenilenir": "?"}, olcum))
        # Yıl dönümü: aralıkta ölçülen, ocakta sıfırlanan.
        aralik = datetime(2026, 12, 31, 22, 0, tzinfo=timezone.utc).timestamp()
        ocak = kadro._kota_yenilenme({"saglayici": "agy", "yenilenir": "01-02T10:00"}, aralik)
        self.assertEqual(ocak, datetime(2027, 1, 2, 10, 0, tzinfo=timezone.utc).timestamp())


if __name__ == "__main__":
    unittest.main()
