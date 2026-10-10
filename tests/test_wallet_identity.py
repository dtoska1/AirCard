import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import aircard_backend
import apply_card_skin
from wallet_identity import valid_card_id, require_card_id, wallet_directory


class WalletIdentityTests(unittest.TestCase):
    def test_supported_grammar(self):
        for value in ('A' * 27 + '=', 'aB0_+-=' * 4, 'x' * 20, 'x' * 64):
            self.assertTrue(valid_card_id(value))
            self.assertEqual(wallet_directory(value, '.pkpass'),
                             '/var/mobile/Library/Passes/Cards/' + value + '.pkpass')

    def test_rejects_paths_syntax_and_invalid_lengths_at_backend_boundary(self):
        for value in ('../' + 'a' * 24, 'a' * 20 + '/b', 'a' * 20 + '\\b',
                      'a' * 20 + '..', 'a' * 19, 'a' * 65, 'a' * 20 + '\n',
                      'a' * 20 + ' b', 'a' * 20 + ';id', '$(touch unwanted)', None):
            with self.subTest(value=value), patch.object(aircard_backend, 'write_files_batch') as write, \
                 patch.object(aircard_backend, 'remove_files') as remove, redirect_stdout(io.StringIO()) as output:
                self.assertFalse(aircard_backend.cmd_flash('synthetic-device', value, '/not-read'))
                write.assert_not_called()
                remove.assert_not_called()
                self.assertIn('Invalid Wallet card ID', output.getvalue())
                with self.assertRaises(ValueError):
                    require_card_id(value)
                with self.assertRaises(ValueError):
                    apply_card_skin.invalidate_cache('synthetic-device', value)

    def test_valid_manual_id_reaches_flash_workflow(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.png'
            path.write_bytes(b'test-artwork')
            identifier = 'M' * 27 + '='
            with patch.object(aircard_backend, 'build_card_assets', return_value=[('cardBackgroundCombined@3x.png', b'test')]), \
                 patch.object(aircard_backend, 'write_files_batch', return_value=True) as write, \
                 patch.object(aircard_backend, 'remove_files', return_value=True), redirect_stdout(io.StringIO()):
                self.assertTrue(aircard_backend.cmd_flash('synthetic-device', identifier, str(path)))
                self.assertEqual(write.call_args.args[1], wallet_directory(identifier, '.pkpass'))
