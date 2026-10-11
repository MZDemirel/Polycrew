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
    "agents/gelistirici.md",
)
DIS_AJAN = "skills/external-agent/dis-ajan.sh"


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


if __name__ == "__main__":
    unittest.main()
