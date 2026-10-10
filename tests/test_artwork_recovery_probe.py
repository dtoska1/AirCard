import json
import plistlib
import tempfile
import unittest
from pathlib import Path

from artwork_recovery_probe import probe_local_cache

A = "A" * 27 + "="
B = "B" * 27 + "="


class ArtworkRecoveryProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "Cards").mkdir()

    def pass_dir(self, identifier=A):
        path = self.root / "Cards" / (identifier + ".pkpass")
        path.mkdir(exist_ok=True)
        return path

    def test_no_local_cache_does_not_claim_no_iphone_artwork(self):
        result = probe_local_cache(self.root)
        self.assertEqual(result["scope"], "Mac-only; no iPhone access")
        self.assertEqual(result["referenceFiles"], 0)
        self.assertIn("does not rule out", result["note"])
        self.assertFalse(result["limited"])

    def test_plist_and_plain_urls_only_report_counts_without_leaking_tokens(self):
        a = self.pass_dir()
        token = "DO-NOT-PRINT-TOKEN"
        (a / "cardBackgroundCombined@2x.urls").write_bytes(
            plistlib.dumps({"download": "https://example.invalid/image?token=" + token})
        )
        (a / "cardBackgroundCombined@3x.png.urls").write_text(
            "https://example.invalid/artwork?token=" + token
        )
        b = self.pass_dir(B)
        (b / "cardBackgroundCombined.pdf.urls").write_bytes(b"not a URL")
        report = probe_local_cache(self.root)
        self.assertEqual(report["passesChecked"], 2)
        self.assertEqual(report["referenceFiles"], 3)
        self.assertEqual(report["plausibleUrlFiles"], 2)
        exported = json.dumps(report)
        self.assertNotIn(token, exported)
        self.assertNotIn("example.invalid", exported)
        self.assertNotIn(A, exported)
        self.assertNotIn(B, exported)

    def test_never_follows_symlinks_and_rejects_unrelated_files(self):
        outside = self.root / "outside.urls"
        outside.write_text("https://example.invalid/private-token")
        a = self.pass_dir()
        (a / "cardBackgroundCombined@2x.urls").symlink_to(outside)
        (a / "pass.json").write_text('{"cvv":"private"}')
        (self.root / "Cards" / (B + ".pkpass")).symlink_to(a, target_is_directory=True)
        report = probe_local_cache(self.root)
        self.assertEqual(report["passesChecked"], 1)
        self.assertEqual(report["referenceFiles"], 0)

    def test_oversized_file_is_not_interpreted(self):
        a = self.pass_dir()
        (a / "cardBackgroundCombined@2x.urls").write_bytes(b"https://example.invalid/" + b"A" * (257 * 1024))
        report = probe_local_cache(self.root)
        self.assertEqual(report["referenceFiles"], 1)
        self.assertEqual(report["plausibleUrlFiles"], 0)


if __name__ == "__main__":
    unittest.main()
