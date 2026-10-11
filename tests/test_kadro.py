"""polycrew dinamik kadro ve puan defteri testleri (python3 -m unittest discover tests)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "skills" / "team"))
sys.path.insert(0, str(KOK / "hooks"))
import kadro  # noqa: E402
import olay  # noqa: E402


def calistir_olay(argv: list[str], gunluk: Path | None = None, defter: Path | None = None):
    env = {**os.environ}
    if gunluk:
        env["POLYCREW_OLAYLAR"] = str(gunluk)
    if defter:
        env["POLYCREW_PUANLAR"] = str(defter)
    return subprocess.run(
        [sys.executable, str(KOK / "hooks" / "olay.py"), *argv],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def calistir_kadro(argv: list[str], defter: Path | None = None, gunluk: Path | None = None):
    env = {**os.environ}
    if defter:
        env["POLYCREW_PUANLAR"] = str(defter)
    if gunluk:
        env["POLYCREW_OLAYLAR"] = str(gunluk)
    return subprocess.run(
        [sys.executable, str(KOK / "skills" / "team" / "kadro.py"), *argv],
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
        r = calistir_olay(["puan", "k1", "4", "eski", "gerekce"], gunluk=self.gunluk, defter=self.defter)
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
                "puan",
                "k2",
                "5",
                "harika",
                "iş",
                "--isci",
                "codex/gpt-6.1-sol/high",
                "--rol",
                "gelistirici",
                "--alan",
                "py",
                "--zorluk",
                "O",
                "--kota",
                "12",
                "--sure",
                "100",
                "--duzeltme",
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
                "ekle",
                "k3",
                "4",
                "sanat",
                "--isci",
                "claude/sanatci/opus",
                "--rol",
                "sanatci",
                "--alan",
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
        r1 = calistir_kadro(["oneri", "--rol", "gelistirici", "--tohumsuz"], defter=self.defter)
        self.assertIn("isci-A", r1.stdout)
        self.assertIn("isci-B", r1.stdout)
        self.assertNotIn("isci-C", r1.stdout)

        # 2. Alan filtresi
        r2 = calistir_kadro(["oneri", "--alan", "py", "--tohumsuz"], defter=self.defter)
        self.assertIn("isci-A", r2.stdout)
        self.assertNotIn("isci-B", r2.stdout)
        self.assertIn("isci-C", r2.stdout)

        # 3. Zorluk filtresi
        r3 = calistir_kadro(["oneri", "--zorluk", "Z", "--tohumsuz"], defter=self.defter)
        self.assertNotIn("isci-A", r3.stdout)
        self.assertNotIn("isci-B", r3.stdout)
        self.assertIn("isci-C", r3.stdout)

        # 4. Filtresiz rol x alan kırılımı
        r4 = calistir_kadro(["oneri", "--tohumsuz"], defter=self.defter)
        self.assertIn("gelistirici", r4.stdout)
        self.assertIn("gozden-gecirici", r4.stdout)
        self.assertIn("py", r4.stdout)
        self.assertIn("js", r4.stdout)

    def test_kadro_oneri_tohumlu_varsayilan_cikti(self):
        r = calistir_kadro(["oneri"], defter=self.defter)
        self.assertEqual(r.returncode, 0)
        self.assertIn("| Rol | Alan | En İyi İşçi |", r.stdout)
        self.assertIn("claude/gelistirici/sonnet", r.stdout)
        self.assertIn("codex/gpt-6.1-sol/high", r.stdout)
        self.assertIn("claude/sanatci/opus", r.stdout)

    def test_bozuk_satir_atlanir(self):
        with open(self.defter, "w", encoding="utf-8") as f:
            f.write("bozuk bir json satiri\n")
            f.write("{}\n")
            f.write('{"not": 4}\n')  # isci yok
            f.write('{"isci": "temiz/isci", "not": 5, "rol": "sanatci", "alan": "sanat", "ts": 1000}\n')

        r = calistir_kadro(["oneri", "--tohumsuz"], defter=self.defter)
        self.assertEqual(r.returncode, 0)
        self.assertIn("temiz/isci", r.stdout)

    def test_bos_defter_anlamli_mesaj(self):
        r = calistir_kadro(["oneri", "--tohumsuz"], defter=self.defter)
        self.assertEqual(r.returncode, 0)
        self.assertIn("Puan kaydı bulunamadı", r.stdout)

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
        r = calistir_kadro(["ozet", "--tohumsuz"], defter=self.defter)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "Kayıt yok.")

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
            ["ozet", "--simdi", "1000000", "--gun", "7", "--tohumsuz"],
            defter=self.defter,
        )
        self.assertEqual(r.returncode, 0)
        # 1970-01-12 UTC
        self.assertIn("Kadro özeti: son 7 gün, 1 kayıt (üretildi: 1970-01-12)", r.stdout)
        self.assertIn("yeni-isci", r.stdout)
        self.assertNotIn("eski-isci", r.stdout)
        self.assertNotIn("gelecek-isci", r.stdout)

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
            ["ozet", "--simdi", "1000000", "--gun", "7", "--tohumsuz"],
            defter=self.defter,
        )
        self.assertEqual(r1.returncode, 0)
        # z-isci (n=4) Kadro, a-isci (n=2) Yedek
        self.assertIn("| gelistirici | py | z-isci | 3,50 | 4 | a-isci | 3,50 | pencere |", r1.stdout)

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
            ["ozet", "--simdi", "1000000", "--gun", "7", "--tohumsuz"],
            defter=self.defter,
        )
        self.assertEqual(r2.returncode, 0)
        # a-isci Kadro, b-isci Yedek
        self.assertIn("| gelistirici | py | a-isci | 4,25 | 2 | b-isci | 4,25 | pencere, veri az |", r2.stdout)

    def test_ozet_eski_dayanagi(self):
        # Pencerede kayit yok (ts: 100_000 < 395_200, simdi: 1_000_000)
        kayitlar = [
            {"isci": "vefakar-kodcu", "rol": "gelistirici", "alan": "py", "not": 4, "ts": 100_000},
        ]
        with open(self.defter, "w", encoding="utf-8") as f:
            for k in kayitlar:
                f.write(json.dumps(k) + "\n")

        r = calistir_kadro(
            ["ozet", "--simdi", "1000000", "--gun", "7", "--tohumsuz"],
            defter=self.defter,
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("Kadro özeti: son 7 gün, 0 kayıt", r.stdout)
        self.assertIn("| gelistirici | py | vefakar-kodcu | 3,67 | 1 | — | — | eski |", r.stdout)

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
            ["ozet", "--simdi", "1000000", "--gun", "7", "--tohumsuz"],
            defter=self.defter,
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("| gelistirici | js | az-kodcu | 4,25 | 2 | — | — | pencere, veri az |", r.stdout)
        self.assertIn("| gelistirici | py | cok-kodcu | 4,40 | 3 | — | — | pencere |", r.stdout)

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
            ["ozet", "--simdi", "1000000", "--gun", "7", "--tohumsuz"],
            defter=self.defter,
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("| sanatci | sanat | as-isci | 4,00 | 1 | yedek-isci | 3,67 | pencere, veri az |", r.stdout)
        self.assertIn("| gelistirici | py | tek-isci | 4,00 | 1 | — | — | pencere, veri az |", r.stdout)

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
            ["ozet", "--simdi", "1000000", "--gun", "7", "--tohumsuz"],
            defter=self.defter,
        )
        self.assertEqual(r.returncode, 0)
        satirlar = [s for s in r.stdout.splitlines() if s.startswith("|") and not s.startswith("| Rol") and not s.startswith("|---")]
        self.assertEqual(len(satirlar), 3)
        self.assertIn("| gelistirici | js |", satirlar[0])
        self.assertIn("| gelistirici | py |", satirlar[1])
        self.assertIn("| sanatci | sanat |", satirlar[2])


if __name__ == "__main__":
    unittest.main()
