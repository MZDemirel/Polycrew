"""Sabit git kuralları tek dosyada durur; skill'ler ve roller ona işaret eder (0006)."""

import pathlib
import re
import unittest

KOK = pathlib.Path(__file__).resolve().parent.parent
ATIF = "${CLAUDE_PLUGIN_ROOT}/rules/git.md"
ATIF_YAPANLAR = (
    "skills/project-setup/SKILL.md",
    "skills/team/SKILL.md",
    "skills/session-end/SKILL.md",
    "skills/external-agent/SKILL.md",
    "agents/developer.md",
)
DIS_AJAN = "skills/external-agent/external-agent.sh"


def oku(yol):
    return (KOK / yol).read_text(encoding="utf-8")


class KurallarTesti(unittest.TestCase):
    def test_kural_dosyasi_dort_kurali_icerir(self):
        metin = oku("rules/git.md")
        for parca in ("Co-Authored-By", "Generated with", "branches are not deleted", "do not push", "--no-verify"):
            self.assertIn(parca, metin)

    def test_proje_blogu_sabit_kurallari_tasir(self):
        blok = re.search(r"```markdown\n(.*?)```", oku("rules/git.md"), re.S).group(1)
        for parca in ("Co-Authored-By", "Generated with", "not deleted", "do not push", "override"):
            self.assertIn(parca, blok)

    def test_skill_ve_roller_atif_yapar(self):
        for yol in ATIF_YAPANLAR:
            self.assertIn(ATIF, oku(yol), yol)

    def test_dal_silen_komut_yok(self):
        dosyalar = [*KOK.glob("skills/**/*"), *KOK.glob("agents/*"), KOK / "CLAUDE.md"]
        for dosya in dosyalar:
            if dosya.suffix not in (".md", ".sh", ".py"):
                continue
            metin = dosya.read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"branch\s+(-D|-d|--delete)\b", metin), dosya)
            self.assertNotIn("push --delete", metin, dosya)

    def test_proje_kur_imzayi_sormaz(self):
        soru = next(s for s in oku("skills/project-setup/SKILL.md").splitlines() if s.startswith("- Commit:"))
        self.assertNotIn("signature", soru.lower())
        self.assertNotIn("co-authored", soru.lower())

    def test_dis_isci_kural_satiri(self):
        satir = next(s for s in oku(DIS_AJAN).splitlines() if s.startswith("kural="))
        for parca in ("do not git push", "--no-verify", "Co-Authored-By", "Do not delete branches"):
            self.assertIn(parca, satir)


ESKI_ADLAR = re.compile(
    r"oturum-ac|oturum-kapat|proje-kur|/takim|/karar|/izle(?![-\w])|dis-ajan\.sh|(?<![-\w])kadro\.(py|md)|izle\.py|olay\.py|"
    r"claude-kota|nerede_kaldik|polycrew:(lider|gelistirici|gozden-gecirici|sanatci|tasarimci|arastirmaci)|"
    r"agents/(lider|gelistirici|gozden-gecirici|sanatci|tasarimci|arastirmaci)\.md"
)


class IngilizceYuzeyTesti(unittest.TestCase):
    """0007: kullanıcının gördüğü adlar İngilizce; eski ad skill, rol, kural ve kanca metninde kalmaz."""

    def test_skill_ve_rol_adlari(self):
        skiller = sorted(p.parent.name for p in KOK.glob("skills/*/SKILL.md"))
        self.assertEqual(skiller, ["decision", "external-agent", "project-setup", "session-end",
                                   "session-start", "team", "watch"])
        roller = sorted(p.stem for p in KOK.glob("agents/*.md"))
        self.assertEqual(roller, ["artist", "designer", "developer", "lead", "researcher", "reviewer"])
        for p in [*KOK.glob("skills/*/SKILL.md"), *KOK.glob("agents/*.md")]:
            ad = re.search(r"^name: (.+)$", p.read_text(encoding="utf-8"), re.M).group(1)
            self.assertEqual(ad, p.parent.name if p.name == "SKILL.md" else p.stem)

    def test_eski_ad_kalmadi(self):
        dosyalar = [*KOK.glob("skills/*/SKILL.md"), *KOK.glob("skills/team/roster.md"), *KOK.glob("agents/*.md"),
                    *KOK.glob("rules/*.md"), *KOK.glob("hooks/*.sh"), KOK / "hooks" / "hooks.json", KOK / "README.md"]
        for dosya in dosyalar:
            bulunan = ESKI_ADLAR.search(dosya.read_text(encoding="utf-8"))
            self.assertIsNone(bulunan, f"{dosya.relative_to(KOK)}: {bulunan and bulunan.group(0)}")

    def test_dis_isci_betigi_argumanlari(self):
        import subprocess
        betik = str(KOK / "skills/external-agent/external-agent.sh")
        r = subprocess.run(["bash", betik], capture_output=True, text=True, check=False)
        self.assertEqual(r.returncode, 2)
        self.assertIn("<read|write>", r.stderr)
        r = subprocess.run(["bash", betik, "codex", "m", "-", "okur", str(KOK), str(KOK / "README.md")],
                           capture_output=True, text=True, check=False)
        self.assertEqual(r.returncode, 2)
        self.assertIn("mode must be read or write", r.stderr)
        # write kipi ana çalışma ağacını ya da worktree olmayan klasörü reddeder (hiçbir CLI çağrılmaz).
        r = subprocess.run(["bash", betik, "codex", "m", "-", "write", "/tmp", str(KOK / "README.md")],
                           capture_output=True, text=True, check=False)
        self.assertEqual(r.returncode, 3)

    def test_dis_isci_araci_kurulu_degilse(self):
        """0009: araç PATH'te yoksa çıkış 4, anlaşılır ileti, kayıt klasörü açılmaz."""
        import os
        import shutil
        import subprocess
        import tempfile
        betik = str(KOK / "skills/external-agent/external-agent.sh")
        with tempfile.TemporaryDirectory() as d:
            kutu = pathlib.Path(d) / "bin"
            kutu.mkdir()
            for ad in ("realpath", "dirname", "sed", "python3", "mktemp", "cat", "rm", "date"):
                os.symlink(shutil.which(ad), kutu / ad)
            kayit = pathlib.Path(d) / "kayit"
            env = {"PATH": str(kutu), "HOME": d, "EXTERNAL_AGENT_LOG": str(kayit),
                   "POLYCREW_EVENTS": str(pathlib.Path(d) / "olay.jsonl")}
            for arac in ("codex", "agy"):
                r = subprocess.run([shutil.which("bash"), betik, arac, "m", "-", "read", str(KOK), str(KOK / "README.md")],
                                   capture_output=True, text=True, check=False, env=env)
                self.assertEqual(r.returncode, 4, r.stderr)
                self.assertIn(f"{arac} is not installed", r.stderr)
            self.assertFalse(kayit.exists())
            r = subprocess.run([shutil.which("bash"), betik, "quota"], capture_output=True, text=True, check=False, env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("codex   not installed", r.stdout)
            self.assertIn("agy     not installed", r.stdout)


if __name__ == "__main__":
    unittest.main()
