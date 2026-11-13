"""polycrew izle: olay günlüğü ve birleştirme (python3 -m unittest discover tests)."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "skills" / "watch"))
sys.path.insert(0, str(KOK / "hooks"))
import watch as izle  # noqa: E402
import events as olay  # noqa: E402
# 0019: testler masaüstü uygulamasının gerçek kota dosyasını okumasın.
os.environ.setdefault("POLYCREW_DESKTOP_USAGE", "/nonexistent/polycrew-test")


# 0013: kanca yalnız not dosyası olan projede yazar; testlerin kancası bu sahte projeden çağrılır.
PROJE = tempfile.TemporaryDirectory()
(Path(PROJE.name) / "NEXT_SESSION.md").write_text("# Next session\n", encoding="utf-8")


def calistir(argv, stdin=None, gunluk=None, proje=PROJE.name, **ekenv):
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_PROJECT_DIR", "POLYCREW_WATCH_ALL")}
    env.update({"POLYCREW_EVENTS": str(gunluk), **ekenv})
    if proje:
        env["CLAUDE_PROJECT_DIR"] = str(proje)
    return subprocess.run(
        [sys.executable, str(KOK / "hooks" / "events.py"), *argv],
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

    def test_hook_writes_only_in_polycrew_projects(self):
        yuk = {"hook_event_name": "SubagentStart", "session_id": "s", "agent_id": "a", "agent_type": "x"}
        with tempfile.TemporaryDirectory() as bos:
            alt = Path(PROJE.name) / "src" / "derin"
            alt.mkdir(parents=True, exist_ok=True)
            calistir([], json.dumps({**yuk, "cwd": bos}), self.gunluk, proje=None)
            calistir([], json.dumps(yuk), self.gunluk, proje=bos)
            self.assertFalse(self.gunluk.exists())
            calistir([], json.dumps({**yuk, "cwd": str(alt)}), self.gunluk, proje=None)
            bag = Path(PROJE.name) / "bag"
            if not bag.exists():
                bag.symlink_to(bos)  # proje içinde, dışarıya giden sembolik bağ
            calistir([], json.dumps({**yuk, "cwd": str(bag)}), self.gunluk, proje=None)
            calistir([], json.dumps(yuk), self.gunluk, proje=bos, POLYCREW_WATCH_ALL="1")
            (Path(bos) / "SONRAKI_OTURUM.md").write_text("# Sonraki oturum\n", encoding="utf-8")
            calistir([], json.dumps(yuk), self.gunluk, proje=bos)
        self.assertEqual(len(izle.oku(self.gunluk)), 4)
        calistir(["write", "isci_basladi", "id=k1"], gunluk=self.gunluk, proje=None)
        self.assertEqual(len(izle.oku(self.gunluk)), 5)

    def test_log_is_trimmed_to_the_newest_half(self):
        satir = json.dumps({"ts": 1, "tur": "x", "dolgu": "a" * 1000}) + "\n"
        self.gunluk.write_text(satir * 1100, encoding="utf-8")
        calistir(["write", "son", "id=z"], gunluk=self.gunluk, POLYCREW_EVENTS_MAX_MB="1")
        olaylar = izle.oku(self.gunluk)
        self.assertLessEqual(self.gunluk.stat().st_size, 512 * 1024)
        self.assertGreater(len(olaylar), 400)
        self.assertEqual(olaylar[-1]["tur"], "son")
        self.assertFalse(self.gunluk.with_name(self.gunluk.name + ".kirp").exists())
        self.assertEqual(list(self.gunluk.parent.glob("*.kirp")), [])
        # 0 kapatır: varsayılan sınırın (10 MB) üstündeki günlük de olduğu gibi kalır.
        self.gunluk.write_text(satir * 10600, encoding="utf-8")
        once = self.gunluk.stat().st_size
        calistir(["write", "yine", "id=y"], gunluk=self.gunluk, POLYCREW_EVENTS_MAX_MB="0")
        self.assertGreater(self.gunluk.stat().st_size, once)
        self.assertEqual(izle.oku(self.gunluk)[-1]["tur"], "yine")

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
        calistir(["write", "isci_basladi", "id=k1", "kaynak=codex", "cikis=0"], gunluk=self.gunluk)
        calistir(["score", "k1", "4", "iyi", "iş"], gunluk=self.gunluk)
        e1, e2 = izle.oku(self.gunluk)
        self.assertEqual((e1["kaynak"], e1["cikis"]), ("codex", 0))
        self.assertEqual((e2["tur"], e2["not"], e2["gerekce"]), ("puan", 4, "iyi iş"))
        # 0014: --worker'sız puan da projeyi taşır; worktree'de ana projenin adı.
        agac = Path(self.d.name) / "oyun" / ".claude" / "worktrees" / "w1"
        agac.mkdir(parents=True)
        subprocess.run([sys.executable, str(KOK / "hooks" / "events.py"), "score", "k1", "5"], cwd=str(agac),
                       env={**os.environ, "POLYCREW_EVENTS": str(self.gunluk)}, check=True)
        self.assertEqual(izle.oku(self.gunluk)[-1]["proje"], "oyun")


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
        # agy'deki Claude da dış işçi rengindedir (0014).
        self.assertEqual((isler["k2"]["durum"], isler["k2"]["saglayici"]), ("calisiyor", "gemini"))

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
        o = [{"tur": "agent_bitti", "ts": 5, "id": "x", "rol": "gelistirici"}]
        [i] = izle.birlestir(o, simdi=10)["isler"]
        self.assertEqual((i["durum"], i["sure"]), ("bitti", None))

    def test_a_roleless_stop_without_a_start_is_not_a_job(self):
        o = [{"tur": "agent_bitti", "ts": 5, "id": "x", "rol": ""}]
        self.assertEqual(izle.birlestir(o, simdi=10)["isler"], [])

    def test_parallel_launches_start_in_launch_order_and_resume(self):
        o = [{"tur": "agent_baslatildi", "ts": 0, "id": "tu1", "rol": "g", "aciklama": "ilk"},
             {"tur": "agent_baslatildi", "ts": 1, "id": "tu2", "rol": "g", "aciklama": "ikinci"},
             {"tur": "agent_basladi", "ts": 2, "id": "a1", "rol": "g"},
             {"tur": "agent_basladi", "ts": 2.1, "id": "a2", "rol": "g"},
             {"tur": "agent_bitti", "ts": 9, "id": "a1", "rol": "g"},
             {"tur": "puan", "ts": 10, "id": "a1", "not": 4},
             {"tur": "agent_basladi", "ts": 11, "id": "a1", "rol": "g"}]
        isler = {i["id"]: i for i in izle.birlestir(o, simdi=20)["isler"]}
        self.assertEqual(isler["tu1"]["agent_id"], "a1")
        self.assertEqual(isler["tu1"]["puan"]["not"], 4)
        self.assertEqual(isler["tu1"]["durum"], "calisiyor")
        self.assertIsNone(isler["tu2"]["puan"])

    def test_project_name_and_filter(self):
        self.assertEqual(izle.proje_adi("/a/Pixlender/.claude/worktrees/dis-yaka-22"), "Pixlender")
        self.assertEqual(izle.proje_adi("/a/polycrew/"), "polycrew")
        self.assertIsNone(izle.proje_adi(None))
        o = [
            {"tur": "agent_baslatildi", "ts": 1, "id": "a", "rol": "x", "cwd": "/p/oyun"},
            {"tur": "isci_basladi", "ts": 2, "id": "b", "kaynak": "codex", "klasor": "/p/oyun/.claude/worktrees/b"},
            {"tur": "isci_basladi", "ts": 3, "id": "c", "kaynak": "codex", "klasor": "/p/eklenti"},
            {"tur": "isci_basladi", "ts": 4, "id": "d", "kaynak": "codex"},
            {"tur": "puan", "ts": 5, "id": "yok", "not": 4, "proje": "eklenti"},
        ]
        v = izle.birlestir(o, simdi=10)
        s = izle.suz(v, None, "oyun")
        self.assertEqual([i["id"] for i in s["isler"]], ["a", "b"])
        self.assertEqual((s["projeler"], s["proje"], s["puanlar"]), (["eklenti", "oyun"], "oyun", []))
        self.assertEqual([i["id"] for i in s["harita"]["cocuklar"]], ["a", "b"])
        self.assertEqual(len(izle.suz(v, None)["isler"]), 4)
        self.assertEqual(len(izle.suz(v, None, "eklenti")["puanlar"]), 1)

    def test_unknown_job_enters_the_window_by_its_start(self):
        # Bitişi gelmemiş eski iş (bilinmiyor) 12 saatlik pencereyi günlere yaymasın (0014).
        simdi = 10 * 86400
        o = [{"tur": "isci_basladi", "ts": simdi - 3 * 86400, "id": "eski", "kaynak": "codex"},
             {"tur": "isci_basladi", "ts": simdi - 60, "id": "yeni", "kaynak": "codex"}]
        v = izle.birlestir(o, simdi=simdi)
        self.assertEqual({i["id"]: i["durum"] for i in v["isler"]}, {"eski": "bilinmiyor", "yeni": "calisiyor"})
        self.assertEqual([i["id"] for i in izle.suz(v, 12)["isler"]], ["yeni"])

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
                k = {"olcum": olcum.isoformat(), "yenilenir": bicim, "pencere": "hafta"}
                self.assertFalse(izle.kota_kovasi(k, 0, reset - 1)["eski"])
                self.assertTrue(izle.kota_kovasi(k, 0, reset)["eski"])
                # 0018: sıfırlanma geçtiyse ölçüm ondan sonra olsa da eski (roster.py ile aynı kural, 0017).
                k["olcum"] = datetime.fromtimestamp(reset).astimezone().isoformat()
                self.assertTrue(izle.kota_kovasi(k, 0, reset + 1)["eski"])
        self.assertFalse(izle.kota_kovasi({"yenilenir": "bozuk"}, reset, reset + 1)["eski"])
        # 0017: kesin sıfırlanma anı varsa metin (agy'de UTC) çözülmez.
        k = izle.kota_kovasi({"yenilenir": "01-01T00:00", "yenilenir_epoch": reset + 7200}, reset, reset + 3600)
        self.assertEqual(k["yenilenir_ts"], reset + 7200)
        self.assertFalse(k["eski"])
        self.assertTrue(izle.kota_kovasi({"yenilenir_epoch": reset + 7200}, reset, reset + 7201)["eski"])
        self.assertFalse(izle.kota_kovasi({"pencere": "bağlam"}, reset, reset + 1)["eski"])
        self.assertEqual(izle.kota_kovasi({}, reset, reset)["olcum_ts"], reset)

    def test_stale_quota_by_age_and_reason(self):
        # 0018: 4 günlük haftalık okuma, sıfırlanması gelecekte olsa da eskidir; neden sayfaya gider.
        simdi = 1_800_000_000.0
        hafta = {"saglayici": "claude", "grup": "Claude", "pencere": "hafta", "kullanilan": 5,
                 "yenilenir_epoch": simdi + 3 * 86400}
        k = izle.kota_kovasi(hafta, simdi - 4 * 86400, simdi)
        self.assertTrue(k["eski"])
        self.assertEqual(k["eski_neden"], "older than a day")
        self.assertFalse(izle.kota_kovasi(hafta, simdi - 3600, simdi)["eski"])
        bes = {**hafta, "pencere": "5 saat", "yenilenir_epoch": simdi + 3600}
        self.assertEqual(izle.kota_kovasi(bes, simdi - 6 * 3600, simdi)["eski_neden"], "older than 5 hours")
        self.assertEqual(izle.kota_kovasi({**bes, "yenilenir_epoch": simdi - 1}, simdi - 60, simdi)["eski_neden"],
                         "reset passed")

    def test_legacy_agy_reset_text_is_utc(self):
        # 0018: 0.12.0 öncesi agy metni UTC'ydi; sayfa onu yerel sanıyordu.
        olcum = datetime(2026, 11, 13, 9, 0, tzinfo=timezone.utc).timestamp()
        k = izle.kota_kovasi({"saglayici": "agy", "grup": "Gemini Models", "pencere": "weekly",
                              "yenilenir": "11-13T16:46"}, olcum, olcum)
        self.assertEqual(k["yenilenir_ts"], datetime(2026, 11, 13, 16, 46, tzinfo=timezone.utc).timestamp())
        self.assertEqual((k["grup"], k["pencere"]), ("agy: Gemini", "hafta"))
        argon = izle.kota_kovasi({"saglayici": "agy", "grup": "Gemini 4 Argon", "pencere": "weekly"}, olcum, olcum)
        self.assertEqual(argon["grup"], "agy: Argon")

    def test_newest_measurement_wins_over_log_order(self):
        # 0019: masaüstü, statusline ve PM aynı kovaya yazar; günlükteki sıra değil ölçüm zamanı kazanır.
        yeni = {"saglayici": "claude", "grup": "Claude", "pencere": "hafta", "kullanilan": 40,
                "olcum": datetime.fromtimestamp(100, timezone.utc).isoformat()}
        eski = {**yeni, "kullanilan": 30, "olcum": datetime.fromtimestamp(50, timezone.utc).isoformat()}
        v = izle.birlestir([{"tur": "kota", "ts": 101, "kovalar": [yeni]}, {"tur": "kota", "ts": 102, "kovalar": [eski]}],
                           simdi=110)
        self.assertEqual(v["kota"]["kovalar"][0]["kullanilan"], 40)

    def test_broken_quota_event_does_not_crash(self):
        v = izle.birlestir([{"tur": "kota", "ts": 10, "kovalar": 5},
                            {"tur": "kota", "ts": 11, "kovalar": [{"saglayici": "codex", "grup": "Codex",
                                                                    "pencere": "5 saat", "kullanilan": 3}]}],
                           simdi=20)
        self.assertEqual(len(v["kota"]["kovalar"]), 1)

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
        return subprocess.run([sys.executable, str(KOK / "skills/watch/claude-quota.py"), *args],
                              env={**os.environ, "POLYCREW_EVENTS": str(self.g)},
                              capture_output=True, text=True)

    def args(self, bes="80", hafta="70"):
        reset = (datetime.now().astimezone() + timedelta(hours=2)).isoformat()
        return ["--five-hour", bes, "--five-hour-resets", reset,
                "--week", hafta, "--week-resets", reset]

    def test_writes_claude_event_and_read_only_summary(self):
        args = self.args() + ["--plan", "Max", "--context", "42", "--context-tokens", "84000"]
        r = self.calistir(args)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("shift Claude's jobs to external workers", r.stdout)
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
        self.assertIn("age", r.stdout)
        self.assertIn("84000 token", r.stdout)
        self.assertEqual(self.g.read_bytes(), once)

    def test_empty_read_and_thresholds(self):
        self.assertIn("Claude: no reading yet", self.calistir([]).stdout)
        self.assertFalse(self.g.exists())
        for bes, hafta, uyari in (("79", "69", False), ("80", "0", True), ("0", "70", True)):
            r = self.calistir(self.args(bes, hafta))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual("shift Claude's jobs to external workers" in r.stdout, uyari)

    def test_iso_reset_is_converted_to_local_time(self):
        an = (datetime.now(timezone.utc) + timedelta(hours=3)).replace(second=0, microsecond=0)
        iso = an.strftime("%Y-%m-%dT%H:%M:%SZ")
        r = self.calistir(self.args("5", "10") + ["--five-hour-resets", iso])
        self.assertEqual(r.returncode, 0, r.stderr)
        [e] = izle.oku(self.g)
        beklenen = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone().strftime("%m-%d %H:%M")
        self.assertEqual(e["kovalar"][0]["yenilenir"], beklenen)
        self.assertEqual(e["kovalar"][0]["yenilenir_epoch"], an.timestamp())

    def test_model_week_and_reset_bounds(self):
        # 0018: model başına haftalık sınır kendi grubunda; sıfırlanma ileride ve pencere boyunda olmalı.
        ileride = (datetime.now().astimezone() + timedelta(days=2)).isoformat()
        r = self.calistir(self.args("5", "10") + ["--model-week", "Fable", "23", ileride])
        self.assertEqual(r.returncode, 0, r.stderr)
        [e] = izle.oku(self.g)
        fable = e["kovalar"][-1]
        self.assertEqual((fable["grup"], fable["pencere"], fable["kullanilan"]), ("Claude: Fable", "hafta", 23))
        self.assertIn("week (Fable): 23%", r.stdout)
        self.g.unlink()
        gecmis = (datetime.now().astimezone() - timedelta(minutes=1)).isoformat()
        uzak = (datetime.now().astimezone() + timedelta(hours=6)).isoformat()
        for args in (self.args() + ["--five-hour-resets", gecmis], self.args() + ["--five-hour-resets", uzak],
                     self.args() + ["--week-resets", (datetime.now().astimezone() + timedelta(days=8)).isoformat()],
                     self.args() + ["--model-week", "Fable", "101", ileride],
                     self.args() + ["--model-week", "Fable", "x", ileride],
                     self.args() + ["--model-week", "Fable", "5", gecmis]):
            with self.subTest(args=args[-3:]):
                self.assertEqual(self.calistir(args).returncode, 2)
                self.assertFalse(self.g.exists())

    def test_invalid_arguments_never_write(self):
        for args in (self.args("101"), self.args("nan"), self.args("-1"),
                     self.args() + ["--context-tokens", "4"],
                     self.args() + ["--context", "10", "--context-tokens", "-1"],
                     ["--five-hour", "10"],
                     self.args() + ["--week-resets", "2026-10-07"]):
            with self.subTest(args=args):
                self.assertEqual(self.calistir(args).returncode, 2)
                self.assertFalse(self.g.exists())


class Rapor(unittest.TestCase):
    def test_report_command_embeds_claude_and_agent_tree(self):
        with tempfile.TemporaryDirectory() as d:
            g = Path(d) / "o.jsonl"
            cikti = Path(d) / "rapor.html"
            with patch.dict(os.environ, {"POLYCREW_EVENTS": str(g)}):
                olay.yaz({"tur": "agent_basladi", "id": "lider", "rol": "lider", "cwd": "/p/oyun"})
                olay.yaz({"tur": "agent_basladi", "id": "isci", "rol": "isci", "cwd": "/p/oyun/.claude/worktrees/w1",
                          "ham": {"parent_agent_id": "lider"}})
                olay.yaz({"tur": "isci_basladi", "id": "gizli", "kaynak": "codex", "klasor": "/p/baska",
                          "aciklama": "başka projenin işi"})
                olay.yaz({"tur": "kota", "kovalar": [{"saglayici": "claude", "grup": "Claude",
                           "pencere": "hafta", "kullanilan": 70}]})
                olay.yaz({"tur": "kota", "kovalar": [{"saglayici": "codex", "grup": "Codex",
                           "pencere": "hafta", "kullanilan": 10}]})
                once = g.read_bytes()
                r = subprocess.run([sys.executable, str(KOK / "skills/watch/watch.py"), "report",
                                    "--hours", "5", "--lang", "tr", "--out", str(cikti)],
                                   capture_output=True, text=True, cwd=str(Path(d)))
                self.assertEqual(r.returncode, 0, r.stderr)
                bos = json.loads(cikti.read_text().split("const GOMULU = ", 1)[1].split(";\nconst METIN", 1)[0])
                self.assertEqual(bos["isler"], [])  # varsayılan proje: çalıştırılan klasör
                r = subprocess.run([sys.executable, str(KOK / "skills/watch/watch.py"), "report",
                                    "--hours", "5", "--lang", "tr", "--project", "oyun", "--out", str(cikti)],
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
            # 0014: başka projenin işi ve adı rapora girmez; başlık ve dil raporunki.
            self.assertNotIn("başka projenin işi", html)
            self.assertNotIn("projeler", veri)
            self.assertEqual(veri["proje"], "oyun")
            self.assertIn('<html lang="tr">', html)
            self.assertRegex(html, r"<title>Polycrew · oyun · \d{4}-\d{2}-\d{2}</title>")

    def test_static_report_embeds_data_and_reports(self):
        with tempfile.TemporaryDirectory() as d:
            kayit = Path(d) / "k1"
            kayit.mkdir()
            (kayit / "rapor.md").write_text("Bulgular </script> bitti")
            g = Path(d) / "o.jsonl"
            os.environ["POLYCREW_EVENTS"] = str(g)
            try:
                olay.yaz({"tur": "isci_basladi", "id": "k1", "kaynak": "codex", "kayit": str(kayit)})
                html = izle.rapor_html(None)
            finally:
                del os.environ["POLYCREW_EVENTS"]
        self.assertNotIn("/*VERI*/null", html)
        self.assertIn("Bulgular <\\/script> bitti", html)
        self.assertEqual(html.count("</script>"), 1)


if __name__ == "__main__":
    unittest.main()


import re  # noqa: E402
import shutil  # noqa: E402

NODE = shutil.which("node")


@unittest.skipUnless(NODE, "node yok: ofis yerleşim mantığı Node ile sınanır")
class OfisYerlesim(unittest.TestCase):
    """0012: ofis görünümünün saf yerleşim mantığı (sayfadaki OFIS-MANTIK bloğu)."""

    def yerlesim(self, isler):
        sayfa = (KOK / "skills" / "watch" / "page.html").read_text(encoding="utf-8")
        mantik = re.search(r"/\*OFIS-MANTIK\*/(.*?)/\*OFIS-MANTIK-SON\*/", sayfa, re.S).group(1)
        betik = mantik + "\nconst y = ofisYerlesim(JSON.parse(process.argv.at(-1)));\n" \
            "const sade = (l) => l.map((k) => ({id: k.id, x: k.x, y: k.y, oturuyor: k.oturuyor, durum: k.durum, rol: k.rol, tohum: k.tohum}));\n" \
            "console.log(JSON.stringify({claude: sade(y.claude), dis: sade(y.dis), mola: sade(y.mola), tasan: y.tasan, calisan: y.calisan, biten: y.biten, ofis: OFIS}));\n"
        r = subprocess.run([NODE, "-e", betik, "--", json.dumps(isler)], capture_output=True, text=True, check=False)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    @staticmethod
    def i(kimlik, kaynak="claude", durum="calisiyor", rol="polycrew:developer", bas=0, bit=None):
        return {"id": kimlik, "kaynak": kaynak, "saglayici": "claude" if kaynak == "claude" else kaynak,
                "durum": durum, "rol": rol, "baslangic": bas, "bitis": bit}

    def test_calisan_odasinda_biten_dinlenme_kosesinde(self):
        y = self.yerlesim([
            self.i("c1", bas=2), self.i("c0", bas=1), self.i("x1", kaynak="codex", rol=None),
            self.i("g1", kaynak="agy", rol=None),
            self.i("b1", durum="bitti", bit=50), self.i("h1", durum="hata", bit=60),
            self.i("u1", durum="bilinmiyor", rol="polycrew:artist", bas=5),
        ])
        self.assertEqual([k["id"] for k in y["claude"]], ["c0", "c1"])  # başlangıç sırasıyla
        self.assertEqual({k["id"] for k in y["dis"]}, {"x1", "g1"})  # agy de dış işçi odasında
        self.assertEqual([k["id"] for k in y["mola"]], ["h1", "b1", "u1"])  # en son biten önce
        self.assertTrue(all(k["oturuyor"] for k in y["claude"] + y["dis"]))
        self.assertFalse(any(k["oturuyor"] for k in y["mola"]))
        self.assertEqual((y["calisan"], y["biten"]), (4, 3))
        self.assertEqual(y["claude"][0]["rol"], "developer")  # önek atılır
        self.assertEqual({k["durum"] for k in y["mola"]}, {"hata", "bitti", "bilinmiyor"})

    def test_sigmayan_sayiyla_gosterilir_ve_herkes_odasinin_icinde(self):
        y = self.yerlesim([self.i(f"c{n}", bas=n) for n in range(11)]
                          + [self.i(f"b{n}", durum="bitti", bit=n) for n in range(13)])
        self.assertEqual((len(y["claude"]), y["tasan"]["claude"]), (8, 3))
        self.assertEqual((len(y["mola"]), y["tasan"]["mola"]), (8, 5))
        self.assertEqual(y["mola"][0]["id"], "b12")
        for oda, kisiler in (("claude", y["claude"]), ("mola", y["mola"])):
            o = y["ofis"][oda]
            for k in kisiler:
                self.assertGreaterEqual(k["x"] - 3, o["x"], (oda, k))
                self.assertLessEqual(k["x"] + 15, o["x"] + o["w"], (oda, k))
                self.assertGreaterEqual(k["y"], o["y"], (oda, k))
                self.assertLessEqual(k["y"] + 26 if k["oturuyor"] else k["y"] + 16, o["y"] + o["h"], (oda, k))
        yerler = [(k["x"], k["y"]) for k in y["claude"]]
        self.assertEqual(len(set(yerler)), len(yerler))  # iki kişi aynı masada değil

    def test_ayni_kimlik_ayni_gorunum(self):
        a = self.yerlesim([self.i("ayni"), self.i("baska")])["claude"]
        b = self.yerlesim([self.i("baska", bas=9), self.i("ayni", bas=1)])["claude"]
        tohum = {k["id"]: k["tohum"] for k in a}
        self.assertEqual(tohum, {k["id"]: k["tohum"] for k in b})
        self.assertNotEqual(tohum["ayni"], tohum["baska"])

    def test_rapor_ofisi_tasir(self):
        with tempfile.TemporaryDirectory() as d:
            g = Path(d) / "o.jsonl"
            g.write_text(json.dumps({"tur": "isci_basladi", "ts": 1, "id": "k1", "kaynak": "codex"}) + "\n", encoding="utf-8")
            with patch.dict(os.environ, {"POLYCREW_EVENTS": str(g)}):
                html = izle.rapor_html(None, "en")
        self.assertIn('<canvas id="ofis"', html)
        self.assertIn("function ofisYerlesim", html)
        self.assertIn('"id": "k1"', html)


@unittest.skipUnless(NODE, "node yok: ofis etiketleri Node ile sınanır")
class OfisEtiket(unittest.TestCase):
    """0015: masadaki işçinin kısa etiketi (model kısaltması; aynısı birden çoksa numara)."""

    def etiketler(self, isler):
        sayfa = (KOK / "skills" / "watch" / "page.html").read_text(encoding="utf-8")
        mantik = re.search(r"/\*OFIS-MANTIK\*/(.*?)/\*OFIS-MANTIK-SON\*/", sayfa, re.S).group(1)
        betik = mantik + "\nconst y = ofisYerlesim(JSON.parse(process.argv.at(-1)));\n" \
            "console.log(JSON.stringify({claude: y.claude.map((k) => k.etiket), dis: y.dis.map((k) => k.etiket)," \
            " kisa: ['gpt-6.1-sol', 'gemini-3.8-flash-high', 'claude-opus-5-5-high', 'sonnet', '', null].map(ofisKisaltma)}));\n"
        r = subprocess.run([NODE, "-e", betik, "--", json.dumps(isler)], capture_output=True, text=True, check=False)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_ayni_model_numarayla_ayrilir(self):
        def i(kimlik, kaynak, model, bas):
            return {"id": kimlik, "kaynak": kaynak, "saglayici": kaynak, "durum": "calisiyor", "rol": "yazar",
                    "model": model, "baslangic": bas}
        y = self.etiketler([i("a", "codex", "gpt-6.1-sol", 1), i("b", "codex", "gpt-6.1-sol", 2),
                            i("c", "codex", "gpt-6-astra", 3), i("d", "codex", "gpt-6.1-sol", 4),
                            i("e", "claude", "claude-sonnet-5-5", 5), i("f", "claude", None, 6)])
        self.assertEqual(y["dis"], ["sol1", "sol2", "astra", "sol3"])
        self.assertEqual(y["claude"], ["sonnet", ""])
        self.assertEqual(y["kisa"], ["sol", "flash", "opus", "sonnet", "", ""])


@unittest.skipUnless(NODE, "node yok: çizelge mantığı Node ile sınanır")
class Cizelge(unittest.TestCase):
    """0015: işçi başına şerit ve genişliğe göre eksen (sayfadaki CIZELGE-MANTIK bloğu)."""

    def kos(self, ifade, veri):
        sayfa = (KOK / "skills" / "watch" / "page.html").read_text(encoding="utf-8")
        mantik = re.search(r"/\*CIZELGE-MANTIK\*/(.*?)/\*CIZELGE-MANTIK-SON\*/", sayfa, re.S).group(1)
        betik = mantik + "\nconst v = JSON.parse(process.argv.at(-1));\nconsole.log(JSON.stringify(" + ifade + "));\n"
        r = subprocess.run([NODE, "-e", betik, "--", json.dumps(veri)], capture_output=True, text=True, check=False)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def seritler(self, isler, simdi=1000):
        return self.kos("cizelgeSeritler(v.isler, v.simdi, (i) => i.model).map((s) => ({ad: s.ad, satir: s.satir, "
                        "calisan: s.calisan, cubuklar: s.cubuklar.map((c) => [c.id, c.b, c.e, c.satir])}))",
                        {"isler": isler, "simdi": simdi})

    @staticmethod
    def i(kimlik, model, bas, bit=None, durum="bitti"):
        return {"id": kimlik, "model": model, "saglayici": "codex", "baslangic": bas, "bitis": bit, "durum": durum}

    def test_ayni_iscinin_isleri_tek_seritte_cakisan_alt_satirda(self):
        s = self.seritler([self.i("a", "sol", 0, 100), self.i("b", "sol", 50, 150), self.i("c", "sol", 100, 200),
                           self.i("d", "astra", 10, 20)])
        sol = next(x for x in s if x["ad"] == "sol")
        self.assertEqual(len(s), 2)
        self.assertEqual(sol["satir"], 2)
        # a ve c üst üste gelmez (a 100'de biter, c 100'de başlar): aynı alt satır; b ikisiyle de çakışır.
        self.assertEqual({c[0]: c[3] for c in sol["cubuklar"]}, {"a": 0, "b": 1, "c": 0})

    def test_calisani_olan_serit_once_ve_calisan_simdiye_uzar(self):
        s = self.seritler([self.i("eski", "astra", 900, 990), self.i("yeni", "sol", 100, None, "calisiyor"),
                           self.i("yarim", "flash", 500, None, "bilinmiyor")], simdi=1000)
        self.assertEqual([x["ad"] for x in s], ["sol", "astra", "flash"])
        self.assertEqual(s[0]["cubuklar"][0][1:3], [100, 1000])
        self.assertEqual(s[2]["cubuklar"][0][1:3], [500, 500])  # bitişi bilinmeyen iş uzamaz

    def eksen(self, bas, bit, genislik, kayma=0):
        return self.kos("cizelgeEksen(v.bas, v.bit, v.genislik, v.kayma)",
                        {"bas": bas, "bit": bit, "genislik": genislik, "kayma": kayma})

    def test_eksen_dar_genislikte_seyrelir_tasmaz_ve_ust_uste_binmez(self):
        gun = 86400
        for genislik in (120, 240, 380, 520, 820):
            for aralik in (1800, 4 * 3600, 30 * 3600, 38 * gun):
                e = self.eksen(1_000_000, 1_000_000 + aralik, genislik)
                et = e["etiketler"]
                with self.subTest(genislik=genislik, aralik=aralik):
                    self.assertTrue(et)
                    self.assertLessEqual(len(et), 8)
                    self.assertTrue(all(x["sol"] >= 0 and x["sag"] <= genislik for x in et))
                    self.assertTrue(all(b["sol"] >= a["sag"] + 6 for a, b in zip(et, et[1:])))
        dar, genis = self.eksen(0, 38 * gun, 240), self.eksen(0, 38 * gun, 820)
        self.assertLess(len(dar["etiketler"]), len(genis["etiketler"]))

    def test_eksen_kenardaki_etiket_kenara_yaslanir(self):
        # 0. saniyede başlayan bir saatlik aralık: ilk etiket tam sol kenarda, son etiket tam sağ kenarda.
        e = self.eksen(0, 3600, 400)
        self.assertEqual(e["etiketler"][0]["hiza"], "sol")
        self.assertEqual(e["etiketler"][-1]["hiza"], "sag")
        self.assertEqual(e["etiketler"][-1]["sag"], 400)

    def test_eksen_turu_ve_yerel_saat(self):
        gun = 86400
        self.assertEqual(self.eksen(0, 3 * 3600, 600)["tur"], "saat")
        self.assertEqual(self.eksen(0, 30 * 3600, 900)["tur"], "gunsaat")  # 0014: bir günden uzun aralıkta gün de yazılır
        uzun = self.eksen(1000, 38 * gun, 600, kayma=-3 * 3600)        # UTC+3
        self.assertEqual(uzun["tur"], "gun")
        # Günlük adımda etiket yerel gece yarısına düşer (0014'te UTC gece yarısı yerelde 03:00 görünüyordu).
        self.assertTrue(all((x["x"] + 3 * 3600) % gun == 0 for x in uzun["etiketler"]))
