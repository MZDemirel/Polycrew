"""polycrew izle: olay günlüğü ve birleştirme (python3 -m unittest discover tests)."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

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

    def test_hook_preserves_caller_for_nested_agent_tree(self):
        yukler = [
            {"hook_event_name": "SubagentStart", "session_id": "pm", "agent_id": "lider", "agent_type": "polycrew:lider"},
            {"hook_event_name": "PreToolUse", "session_id": "pm", "tool_name": "Agent", "tool_use_id": "tu-isci",
             "agent_id": "lider", "tool_input": {"subagent_type": "polycrew:gelistirici", "model": "sonnet"}},
            {"hook_event_name": "SubagentStart", "session_id": "pm", "agent_id": "isci", "agent_type": "polycrew:gelistirici"},
        ]
        for yuk in yukler:
            r = calistir([], json.dumps(yuk), self.gunluk)
            self.assertEqual(r.returncode, 0, r.stderr)
        o = izle.oku(self.gunluk)
        self.assertEqual(o[1]["ham"]["agent_id"], "lider")
        h = izle.birlestir(o)["harita"]
        [lider] = h["cocuklar"]
        [isci] = lider["cocuklar"]
        self.assertEqual((lider["id"], isci["id"], isci["model"]), ("lider", "tu-isci", "sonnet"))
        self.assertEqual(isci["ust_kaynak"], "ham.agent_id")

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
        k = {"saglayici": "codex", "grup": "Codex", "pencere": "5 saat"}
        o = [{"tur": "isci_basladi", "ts": 0, "id": "a"}, {"tur": "isci_bitti", "ts": 10, "id": "a", "cikis": 0},
             {"tur": "kota", "ts": 1, "kovalar": [{**k, "kullanilan": 1}]},
             {"tur": "kota", "ts": 2, "kovalar": [{**k, "kullanilan": 2}]}]
        v = izle.birlestir(o, simdi=10 * 3600)
        self.assertEqual(v["kota"]["kovalar"][0]["kullanilan"], 2)
        self.assertEqual(izle.suz(v, 1)["isler"], [])
        self.assertEqual(len(izle.suz(v, None)["isler"]), 1)

    def test_quota_merges_each_provider_group_and_window(self):
        claude = {"saglayici": "claude", "grup": "Claude", "pencere": "hafta", "kullanilan": 71}
        codex = {"saglayici": "codex", "grup": "Codex", "pencere": "5 saat", "kullanilan": 20,
                 "olcum": "2026-10-01T12:00:00+03:00"}
        agy = {"saglayici": "agy", "grup": "agy: Gemini", "pencere": "5 saat", "kullanilan": 30}
        o = [{"tur": "kota", "ts": 10, "kovalar": [claude]},
             {"tur": "kota", "ts": 20, "kovalar": [codex, agy]},
             {"tur": "kota", "ts": 30, "kovalar": [{**agy, "grup": "agy: Claude/GPT"}]},
             {"tur": "kota", "ts": 40, "kovalar": [{**codex, "kullanilan": 25}]},
             {"tur": "kota", "ts": 50, "kovalar": []}]
        v = izle.birlestir(list(reversed(o)), simdi=100)
        k = {(k["saglayici"], k["grup"], k["pencere"]): k for k in v["kota"]["kovalar"]}
        self.assertEqual(len(k), 4)
        self.assertEqual(k["claude", "Claude", "hafta"]["olcum_ts"], 10)
        self.assertEqual(k["codex", "Codex", "5 saat"]["kullanilan"], 25)
        self.assertEqual(k["codex", "Codex", "5 saat"]["olcum"], codex["olcum"])

    def test_stale_quota_both_reset_formats_and_boundaries(self):
        olcum = datetime(2026, 10, 1, 12).astimezone()
        reset = datetime(2026, 10, 2, 12).timestamp()
        for bicim in ("10-02 12:00", "10-02T12:00"):
            with self.subTest(bicim=bicim):
                k = {"olcum": olcum.isoformat(), "yenilenir": bicim}
                self.assertFalse(izle.kota_kovasi(k, 0, reset - 1)["eski"])
                self.assertTrue(izle.kota_kovasi(k, 0, reset)["eski"])
                k["olcum"] = datetime.fromtimestamp(reset).astimezone().isoformat()
                self.assertFalse(izle.kota_kovasi(k, 0, reset + 1)["eski"])
        self.assertFalse(izle.kota_kovasi({"yenilenir": "bozuk"}, reset, reset + 1)["eski"])
        self.assertFalse(izle.kota_kovasi({"pencere": "bağlam"}, reset, reset + 1)["eski"])
        self.assertEqual(izle.kota_kovasi({}, reset, reset)["olcum_ts"], reset)

    def test_agent_tree_parent_agent_and_external_workers(self):
        o = [
            {"tur": "agent_baslatildi", "ts": 10, "id": "tu1", "rol": "lider", "oturum": "pm"},
            {"tur": "agent_basladi", "ts": 11, "id": "a1", "rol": "lider", "oturum": "pm"},
            {"tur": "agent_baslatildi", "ts": 20, "id": "tu2", "rol": "isci", "oturum": "pm",
             "ham": {"parent_agent_id": "a1"}},
            {"tur": "agent_basladi", "ts": 21, "id": "a2", "rol": "isci", "oturum": "pm"},
            {"tur": "isci_basladi", "ts": 30, "id": "codex", "kaynak": "codex"},
            {"tur": "isci_basladi", "ts": 31, "id": "agy", "kaynak": "agy"},
            {"tur": "agent_bitti", "ts": 40, "id": "a2", "oturum": "pm"},
            {"tur": "puan", "ts": 41, "id": "a2", "not": 5},
        ]
        v = izle.birlestir(o, simdi=50)
        h = v["harita"]
        self.assertEqual(h["rol"], "PM")
        self.assertEqual([i["id"] for i in h["cocuklar"]], ["tu1", "codex", "agy"])
        [isci] = h["cocuklar"][0]["cocuklar"]
        self.assertEqual((isci["id"], isci["ust_id"], isci["ust_kaynak"]), ("tu2", "tu1", "ham.parent_agent_id"))
        self.assertEqual((isci["durum"], isci["sure"], isci["puan"]["not"]), ("bitti", 20, 5))

    def test_parent_session_transcript_and_missing_parent(self):
        o = [
            {"tur": "agent_basladi", "ts": 1, "id": "a1", "rol": "lider",
             "ham": {"agent_session_id": "s-lider", "session_id": "pm"}},
            {"tur": "agent_basladi", "ts": 2, "id": "a2", "ham": {"parent_session_id": "s-lider"}},
            {"tur": "agent_basladi", "ts": 3, "id": "a3",
             "ham": {"transcript_path": "/tmp/pm/subagents/agent-a1.jsonl"}},
            {"tur": "agent_baslatildi", "ts": 4, "id": "a4", "rol": "sanatci", "ham": {"agent_id": "a1"}},
            {"tur": "agent_basladi", "ts": 5, "id": "a5", "rol": "arastirmaci", "ham": {"session_id": "a1"}},
            {"tur": "agent_basladi", "ts": 6, "id": "a6", "ham": {"parent_agent_id": "missing"}},
        ]
        h = izle.birlestir(o, simdi=10)["harita"]
        self.assertEqual([i["id"] for i in h["cocuklar"]], ["a1", "a6"])
        self.assertEqual([i["ust_kaynak"] for i in h["cocuklar"][0]["cocuklar"]],
                         ["ham.parent_session_id", "ham.transcript_path", "ham.agent_id", "ham.session_id"])

    def test_tree_window_and_cycles(self):
        o = [{"tur": "agent_basladi", "ts": 1, "id": "a", "ham": {"parent_agent_id": "b"}},
             {"tur": "agent_bitti", "ts": 2, "id": "a"},
             {"tur": "agent_basladi", "ts": 3, "id": "b", "ham": {"parent_agent_id": "a"}}]
        v = izle.birlestir(o, simdi=7200)
        self.assertEqual(len(v["harita"]["cocuklar"]), 2)
        h = izle.suz(v, 1)["harita"]
        self.assertEqual([i["id"] for i in h["cocuklar"]], ["b"])

    def test_same_role_launches_in_different_sessions_do_not_merge(self):
        o = [{"tur": "agent_baslatildi", "ts": 1, "id": "t1", "oturum": "pm1", "rol": "lider"},
             {"tur": "agent_baslatildi", "ts": 2, "id": "t2", "oturum": "pm2", "rol": "lider"},
             {"tur": "agent_basladi", "ts": 3, "id": "a1", "oturum": "pm1", "rol": "lider"}]
        isler = {i["id"]: i for i in izle.birlestir(o, simdi=5)["isler"]}
        self.assertEqual(isler["t1"]["agent_id"], "a1")
        self.assertNotIn("agent_id", isler["t2"])


class ClaudeKota(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.g = Path(self.d.name) / "olaylar.jsonl"

    def tearDown(self):
        self.d.cleanup()

    def calistir(self, args):
        return subprocess.run([sys.executable, str(KOK / "skills/izle/claude-kota.py"), *args],
                              env={**os.environ, "POLYCREW_OLAYLAR": str(self.g)},
                              capture_output=True, text=True)

    def args(self, bes="80", hafta="70"):
        reset = (datetime.now().astimezone() + timedelta(hours=2)).isoformat()
        return ["--bes-saat", bes, "--bes-saat-yenilenir", reset,
                "--hafta", hafta, "--hafta-yenilenir", reset]

    def test_writes_claude_event_and_read_only_summary(self):
        args = self.args() + ["--plan", "Max", "--baglam", "42", "--baglam-token", "84000"]
        r = self.calistir(args)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Claude işlerini dış işçiye kaydır", r.stdout)
        [e] = izle.oku(self.g)
        self.assertEqual((e["tur"], e["kaynak"]), ("kota", "claude"))
        self.assertEqual([k["pencere"] for k in e["kovalar"]], ["5 saat", "hafta", "bağlam"])
        for k in e["kovalar"]:
            self.assertEqual((k["saglayici"], k["grup"], k["plan"]), ("claude", "Claude", "Max"))
            self.assertIsNotNone(izle.zaman(k["olcum"]))
        self.assertRegex(e["kovalar"][0]["yenilenir"], r"^\d{2}-\d{2} \d{2}:\d{2}$")
        self.assertNotIn("yenilenir", e["kovalar"][2])
        self.assertEqual(e["kovalar"][2]["token"], 84000)
        once = self.g.read_bytes()
        r = self.calistir([])
        self.assertIn("yaş", r.stdout)
        self.assertIn("84000 token", r.stdout)
        self.assertEqual(self.g.read_bytes(), once)

    def test_empty_read_and_thresholds(self):
        self.assertIn("Claude: ölçüm yok", self.calistir([]).stdout)
        self.assertFalse(self.g.exists())
        for bes, hafta, uyari in (("79", "69", False), ("80", "0", True), ("0", "70", True)):
            r = self.calistir(self.args(bes, hafta))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual("Claude işlerini dış işçiye kaydır" in r.stdout, uyari)

    def test_iso_reset_is_converted_to_local_time(self):
        iso = "2026-10-12T10:30:00Z"
        r = self.calistir(self.args("5", "10") + ["--bes-saat-yenilenir", iso])
        self.assertEqual(r.returncode, 0, r.stderr)
        [e] = izle.oku(self.g)
        beklenen = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone().strftime("%m-%d %H:%M")
        self.assertEqual(e["kovalar"][0]["yenilenir"], beklenen)

    def test_invalid_arguments_never_write(self):
        for args in (self.args("101"), self.args("nan"), self.args("-1"),
                     self.args() + ["--baglam-token", "4"],
                     self.args() + ["--baglam", "10", "--baglam-token", "-1"],
                     ["--bes-saat", "10"],
                     self.args() + ["--hafta-yenilenir", "2026-10-07"]):
            with self.subTest(args=args):
                self.assertEqual(self.calistir(args).returncode, 2)
                self.assertFalse(self.g.exists())


class Rapor(unittest.TestCase):
    def test_report_command_embeds_claude_and_agent_tree(self):
        with tempfile.TemporaryDirectory() as d:
            g = Path(d) / "o.jsonl"
            cikti = Path(d) / "rapor.html"
            with patch.dict(os.environ, {"POLYCREW_OLAYLAR": str(g)}):
                olay.yaz({"tur": "agent_basladi", "id": "lider", "rol": "lider"})
                olay.yaz({"tur": "agent_basladi", "id": "isci", "rol": "isci",
                          "ham": {"parent_agent_id": "lider"}})
                olay.yaz({"tur": "kota", "kovalar": [{"saglayici": "claude", "grup": "Claude",
                           "pencere": "hafta", "kullanilan": 70}]})
                olay.yaz({"tur": "kota", "kovalar": [{"saglayici": "codex", "grup": "Codex",
                           "pencere": "hafta", "kullanilan": 10}]})
                once = g.read_bytes()
                r = subprocess.run([sys.executable, str(KOK / "skills/izle/izle.py"), "rapor",
                                    "--saat", "5", "--dil", "tr", "--cikti", str(cikti)],
                                   capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(g.read_bytes(), once)
            html = cikti.read_text()
            gomulu = html.split("const GOMULU = ", 1)[1].split(";\nconst METIN", 1)[0]
            veri = json.loads(gomulu)
            self.assertEqual(veri["dil"], "tr")
            self.assertEqual([k["grup"] for k in veri["kota"]["kovalar"]], ["Claude", "Codex"])
            self.assertEqual(veri["harita"]["cocuklar"][0]["cocuklar"][0]["id"], "isci")
            self.assertIn('id="harita"', html)

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
