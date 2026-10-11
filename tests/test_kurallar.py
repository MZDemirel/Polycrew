"""Sabit git kuralları tek dosyada durur; skill'ler ve roller ona işaret eder (0006)."""

import pathlib
import re
import unittest

KOK = pathlib.Path(__file__).resolve().parent.parent
ATIF = "${CLAUDE_PLUGIN_ROOT}/kurallar/git.md"
ATIF_YAPANLAR = (
    "skills/proje-kur/SKILL.md",
    "skills/takim/SKILL.md",
    "skills/oturum-kapat/SKILL.md",
    "skills/dis-ajan/SKILL.md",
    "agents/gelistirici.md",
)


def oku(yol):
    return (KOK / yol).read_text(encoding="utf-8")


class KurallarTesti(unittest.TestCase):
    def test_kural_dosyasi_dort_kurali_icerir(self):
        metin = oku("kurallar/git.md")
        for parca in ("Co-Authored-By", "Generated with", "dallar silinmez", "push etmez", "--no-verify"):
            self.assertIn(parca, metin)

    def test_proje_blogu_sabit_kurallari_tasir(self):
        blok = re.search(r"```markdown\n(.*?)```", oku("kurallar/git.md"), re.S).group(1)
        for parca in ("Co-Authored-By", "Generated with", "silinmez", "push etmez", "geçersiz kılar"):
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
        soru = next(s for s in oku("skills/proje-kur/SKILL.md").splitlines() if s.startswith("- Commit:"))
        self.assertNotIn("imza", soru)

    def test_dis_isci_kural_satiri(self):
        satir = next(s for s in oku("skills/dis-ajan/dis-ajan.sh").splitlines() if s.startswith("kural="))
        for parca in ("git push yapma", "--no-verify", "Co-Authored-By", "Dal silme"):
            self.assertIn(parca, satir)


if __name__ == "__main__":
    unittest.main()
