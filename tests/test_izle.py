"""polycrew izle: olay günlüğü ve birleştirme (python3 -m unittest discover tests)."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "skills" / "izle"))
sys.path.insert(0, str(KOK / "hooks"))
import izle  # noqa: E402
import olay  # noqa: E402


def calistir(argv, stdin=None, gunluk=None):
    env = {**os.environ, "POLYCREW_OLAYLAR": str(gunluk)}
    return subprocess.run(
        [sys.executable, str(KOK / "hooks" / "olay.py"), *argv],
        input=stdin, capture_output=True, text=True, env=env, check=False,
    )


class Kanca(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.gunluk = Path(self.d.name) / "o.jsonl"

    def tearDown(self):
        self.d.cleanup()

    def test_agent_launch_and_stop_are_logged(self):
        yuk = {"hook_event_name": "PreToolUse", "session_id": "s1", "tool_name": "Agent",
               "tool_use_id": "tu1", "tool_input": {"subagent_type": "polycrew:sanatci",
               "description": "B2 sanat", "prompt": "x" * 1000}}
        r = calistir([], json.dumps(yuk), self.gunluk)
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        calistir([], json.dumps({"hook_event_name": "SubagentStop", "session_id": "s1",
                                 "agent_id": "a1", "agent_type": "polycrew:sanatci"}), self.gunluk)
        olaylar = izle.oku(self.gunluk)
        self.assertEqual([e["tur"] for e in olaylar], ["agent_baslatildi", "agent_bitti"])
        self.assertLessEqual(len(olaylar[0]["istem"]), olay.KISA + 1)

    def test_other_tools_and_bad_input_are_ignored_silently(self):
        r1 = calistir([], json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash"}), self.gunluk)
        r2 = calistir([], "bozuk", self.gunluk)
        self.assertEqual((r1.returncode, r2.returncode, r1.stdout, r2.stdout), (0, 0, "", ""))
        self.assertFalse(self.gunluk.exists())

    def test_command_writes_events_and_scores(self):
        calistir(["yaz", "isci_basladi", "id=k1", "kaynak=codex", "cikis=0"], gunluk=self.gunluk)
        calistir(["puan", "k1", "4", "iyi", "iş"], gunluk=self.gunluk)
        e1, e2 = izle.oku(self.gunluk)
        self.assertEqual((e1["kaynak"], e1["cikis"]), ("codex", 0))
        self.assertEqual((e2["tur"], e2["not"], e2["gerekce"]), ("puan", 4, "iyi iş"))


class Birlestir(unittest.TestCase):
    def test_launch_start_stop_become_one_job(self):
        o = [
            {"tur": "agent_baslatildi", "ts": 100, "id": "tu1", "rol": "polycrew:sanatci", "aciklama": "a"},
            {"tur": "agent_basladi", "ts": 101, "id": "ag1", "rol": "polycrew:sanatci"},
            {"tur": "agent_bitti", "ts": 160, "id": "ag1", "rol": "polycrew:sanatci"},
            {"tur": "puan", "ts": 170, "id": "ag1", "not": 5, "gerekce": "ölçtü"},
        ]
        [i] = izle.birlestir(o, simdi=200)["isler"]
        self.assertEqual((i["id"], i["durum"], i["sure"], i["saglayici"]), ("tu1", "bitti", 60, "claude"))
        self.assertEqual(i["puan"]["not"], 5)

    def test_workers_running_failed_and_stale(self):
        o = [
            {"tur": "isci_basladi", "ts": 0, "id": "eski", "kaynak": "agy", "model": "gemini-3.1-pro-high"},
            {"tur": "isci_basladi", "ts": 100, "id": "k1", "kaynak": "codex", "model": "gpt-6.1-sol"},
            {"tur": "isci_bitti", "ts": 150, "id": "k1", "cikis": 1, "kullanim": {"input_tokens": 10, "output_tokens": 5}},
            {"tur": "isci_basladi", "ts": izle.ESKI + 50, "id": "k2", "kaynak": "agy", "model": "claude-opus-4-6"},
        ]
        isler = {i["id"]: i for i in izle.birlestir(o, simdi=izle.ESKI + 100)["isler"]}
        self.assertEqual(isler["eski"]["durum"], "bilinmiyor")
        self.assertEqual((isler["k1"]["durum"], isler["k1"]["token"], isler["k1"]["saglayici"]), ("hata", 15, "codex"))
        self.assertEqual((isler["k2"]["durum"], isler["k2"]["saglayici"]), ("calisiyor", "claude"))

    def test_a_stop_without_a_subagent_start_closes_its_launch(self):
        o = [
            {"tur": "agent_baslatildi", "ts": 10, "id": "tu1", "rol": "polycrew:sanatci"},
            {"tur": "agent_baslatildi", "ts": 20, "id": "tu2", "rol": "polycrew:gelistirici"},
            {"tur": "agent_bitti", "ts": 50, "id": "ag9", "rol": "polycrew:sanatci"},
            {"tur": "agent_bitti", "ts": 60, "id": "tu2"},
        ]
        isler = {i["id"]: i for i in izle.birlestir(o, simdi=100)["isler"]}
        self.assertEqual(set(isler), {"tu1", "tu2"})
        self.assertEqual((isler["tu1"]["durum"], isler["tu1"]["sure"]), ("bitti", 40))
        self.assertEqual((isler["tu2"]["durum"], isler["tu2"]["sure"]), ("bitti", 40))

    def test_a_stop_without_a_start_is_still_shown(self):
        [i] = izle.birlestir([{"tur": "agent_bitti", "ts": 5, "id": "x"}], simdi=10)["isler"]
        self.assertEqual((i["durum"], i["sure"]), ("bitti", None))

    def test_window_and_last_quota(self):
        o = [{"tur": "isci_basladi", "ts": 0, "id": "a"}, {"tur": "isci_bitti", "ts": 10, "id": "a", "cikis": 0},
             {"tur": "kota", "ts": 1, "kovalar": [1]}, {"tur": "kota", "ts": 2, "kovalar": [2]}]
        v = izle.birlestir(o, simdi=10 * 3600)
        self.assertEqual(v["kota"]["kovalar"], [2])
        self.assertEqual(izle.suz(v, 1)["isler"], [])
        self.assertEqual(len(izle.suz(v, None)["isler"]), 1)


class Rapor(unittest.TestCase):
    def test_static_report_embeds_data_and_reports(self):
        with tempfile.TemporaryDirectory() as d:
            kayit = Path(d) / "k1"
            kayit.mkdir()
            (kayit / "rapor.md").write_text("Bulgular </script> bitti")
            g = Path(d) / "o.jsonl"
            os.environ["POLYCREW_OLAYLAR"] = str(g)
            try:
                olay.yaz({"tur": "isci_basladi", "id": "k1", "kaynak": "codex", "kayit": str(kayit)})
                html = izle.rapor_html(None)
            finally:
                del os.environ["POLYCREW_OLAYLAR"]
        self.assertNotIn("/*VERI*/null", html)
        self.assertIn("Bulgular <\\/script> bitti", html)
        self.assertEqual(html.count("</script>"), 1)


if __name__ == "__main__":
    unittest.main()
