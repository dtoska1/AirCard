import json
import plistlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
        self.assertEqual(result["status"], "empty")

    def test_missing_and_inaccessible_cache_are_not_reported_as_empty(self):
        (self.root / "Cards").rmdir()
        missing = probe_local_cache(self.root)
        self.assertEqual(missing["status"], "unavailable")
        outside = self.root / "outside"
        outside.mkdir()
        (self.root / "Cards").symlink_to(outside, target_is_directory=True)
        blocked = probe_local_cache(self.root)
        self.assertEqual(blocked["status"], "inaccessible")
        self.assertGreater(blocked["errors"], 0)

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
        self.assertEqual(report["status"], "complete")
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
        self.assertEqual(report["status"], "partial")

    def test_limits_number_of_passes_without_materializing_directory(self):
        for identifier in (A, B, "C" * 27 + "="):
            self.pass_dir(identifier)
        with patch("artwork_recovery_probe.MAX_PASS_FOLDERS", 2):
            report = probe_local_cache(self.root)
        self.assertEqual(report["passesChecked"], 2)
        self.assertTrue(report["limited"])
        self.assertEqual(report["status"], "partial")

    def test_limits_reference_file_count_and_marks_partial(self):
        a = self.pass_dir()
        for index in range(4):
            (a / ("cardBackgroundCombined%d.urls" % index)).write_text("https://example.invalid/")
        with patch("artwork_recovery_probe.MAX_PASS_ENTRIES", 2):
            report = probe_local_cache(self.root)
        self.assertTrue(report["limited"])
        self.assertEqual(report["status"], "partial")
        self.assertLessEqual(report["referenceFiles"], 2)

    def test_malformed_input_is_not_plist_parsed_or_exported(self):
        a = self.pass_dir()
        (a / "cardBackgroundCombined@2x.urls").write_bytes(b"bplist00\\xff" * 100)
        report = probe_local_cache(self.root)
        self.assertEqual(report["plausibleUrlFiles"], 0)
        self.assertNotIn("bplist", json.dumps(report))

    def test_oversized_file_is_not_interpreted(self):
        a = self.pass_dir()
        (a / "cardBackgroundCombined@2x.urls").write_bytes(b"https://example.invalid/" + b"A" * (257 * 1024))
        report = probe_local_cache(self.root)
        self.assertEqual(report["referenceFiles"], 1)
        self.assertEqual(report["plausibleUrlFiles"], 0)
        self.assertEqual(report["status"], "partial")


if __name__ == "__main__":
    unittest.main()
