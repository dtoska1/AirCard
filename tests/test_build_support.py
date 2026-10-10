import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SUPPORT = ROOT / 'scripts' / 'build_support.sh'


class BuildSupportTests(unittest.TestCase):
    def shell(self, code, *args, env=None):
        return subprocess.run(['bash', '-c', 'source "$1"; shift; ' + code,
                               'test', str(SUPPORT), *map(str, args)],
                              text=True, capture_output=True, env=env)

    def test_python_imports_packaged_modules_without_writing_bytecode(self):
        with tempfile.TemporaryDirectory() as temp:
            for name in ('wallet_identity', 'card_assets', 'apply_card_skin',
                         'aircard', 'aircard_backend', 'wallet_catalog'):
                shutil.copy(ROOT / (name + '.py'), temp)
            result = self.shell('aircard_check_python "$@"', temp, sys.executable)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(list(Path(temp).rglob('__pycache__')))
            Path(temp, 'wallet_identity.py').unlink()
            result = self.shell('aircard_check_python "$@"', temp, sys.executable)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('cannot import the backend', result.stderr)

    def test_broken_first_python_does_not_hide_gui_selection_failure(self):
        result = self.shell('aircard_check_python "$@"', ROOT, '/bin/false', sys.executable)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('GUI selects /bin/false', result.stderr)

    def test_signatures_are_created_inside_out_in_both_modes(self):
        for identity in ('-', 'Developer ID Application: Test'):
            with self.subTest(identity=identity), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                signer = root / 'codesign'
                signer.write_text('#!/bin/bash\nprintf "%s\\n" "$*" >> "$SIGN_LOG"\n')
                signer.chmod(0o755)
                env = dict(os.environ, PATH=temp + os.pathsep + os.environ['PATH'],
                           SIGN_LOG=str(root / 'sign.log'))
                result = self.shell('aircard_sign_app "$@"', '/test/AirCard.app', identity, env=env)
                self.assertEqual(result.returncode, 0, result.stderr)
                calls = (root / 'sign.log').read_text().splitlines()
                self.assertEqual(len(calls), 6)
                self.assertTrue(calls[0].endswith('/bin/device_helper'))
                self.assertTrue(calls[2].endswith('/bin/airtraffic_host'))
                self.assertTrue(calls[4].endswith('/test/AirCard.app'))
                self.assertNotIn('--deep', calls[4])
                self.assertIn('--verify --deep --strict', calls[5])
                for index in (0, 2, 4):
                    self.assertEqual('--options runtime --timestamp' in calls[index], identity != '-')

    def test_invalid_helper_signature_stops_before_sealing_app(self):
        result = self.shell('codesign() { if [ "$1" = --verify ]; then return 9; fi; }; aircard_sign_app "$@"', '/test/AirCard.app', '-')
        self.assertEqual(result.returncode, 9)
