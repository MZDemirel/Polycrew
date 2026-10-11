"""Oturum başlangıcı kancası: iki dosya adı, başlık dilinden bağımsız (0007)."""

import os
import pathlib
import subprocess
import tempfile
import unittest

KOK = pathlib.Path(__file__).resolve().parent.parent
KANCA = KOK / "hooks" / "session_start.sh"

EN = """# Next session

Last updated: **2026-10-11**.

## Where we left off

- Did the first thing.

## Next

### 1. Second thing
- detail

### 2. Third thing

## Questions for the user

### not a next item
"""
TR = EN.replace("Where we left off", "Nerede kaldık").replace("## Next", "## Sıradaki").replace(
    "Did the first thing", "İlk iş yapıldı")


def calistir(klasor):
    return subprocess.run(["bash", str(KANCA)], capture_output=True, text=True, check=False,
                          env={**os.environ, "CLAUDE_PROJECT_DIR": str(klasor)})


class KancaTesti(unittest.TestCase):
    def setUp(self):
        self.gecici = tempfile.TemporaryDirectory()
        self.klasor = pathlib.Path(self.gecici.name)

    def tearDown(self):
        self.gecici.cleanup()

    def test_dosya_yoksa_sessiz(self):
        r = calistir(self.klasor)
        self.assertEqual((r.returncode, r.stdout), (0, ""))

    def test_yeni_ad_ingilizce_basliklar(self):
        (self.klasor / "NEXT_SESSION.md").write_text(EN, encoding="utf-8")
        r = calistir(self.klasor)
        self.assertEqual(r.returncode, 0)
        self.assertIn("/session-start", r.stdout)
        self.assertIn("notes: NEXT_SESSION.md", r.stdout)
        self.assertIn("- Did the first thing.", r.stdout)
        self.assertIn("### 1. Second thing", r.stdout)
        self.assertIn("### 2. Third thing", r.stdout)
        self.assertNotIn("- detail", r.stdout)
        self.assertNotIn("not a next item", r.stdout)

    def test_eski_ad_turkce_basliklar(self):
        (self.klasor / "SONRAKI_OTURUM.md").write_text(TR, encoding="utf-8")
        r = calistir(self.klasor)
        self.assertIn("notes: SONRAKI_OTURUM.md", r.stdout)
        self.assertIn("- İlk iş yapıldı.", r.stdout)
        self.assertIn("### 1. Second thing", r.stdout)

    def test_ikisi_de_varsa_yeni_ad(self):
        (self.klasor / "NEXT_SESSION.md").write_text(EN, encoding="utf-8")
        (self.klasor / "SONRAKI_OTURUM.md").write_text(TR, encoding="utf-8")
        self.assertIn("notes: NEXT_SESSION.md", calistir(self.klasor).stdout)


if __name__ == "__main__":
    unittest.main()
