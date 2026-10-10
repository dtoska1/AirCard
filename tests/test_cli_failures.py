import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import aircard


class CLIFailureTests(unittest.TestCase):
    def run_cli(self, answers, write_ok):
        device = {'udid': 'synthetic-device', 'name': 'Test phone', 'product': 'iPhone00,0', 'version': '0.0'}
        with patch.object(aircard.sys, 'argv', ['aircard.py']), \
             patch.object(aircard, 'get_all_connected_devices', return_value=[device]), \
             patch.object(aircard, 'native', return_value={'exitCode': 0, 'targetGatePassed': True, 'operation': {'ok': True}}), \
             patch.object(aircard, 'load_saved_cards', return_value=['A'*27+'=']), \
             patch('builtins.input', side_effect=answers), \
             patch.object(aircard, 'prepare_card_image', return_value=b'synthetic-image'), \
             patch.object(aircard, 'write_file', return_value=write_ok) as write, \
             patch.object(aircard, 'invalidate_cache', return_value=True), \
             redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(SystemExit) as error:
                aircard.main()
        return error.exception.code, write.call_count, output.getvalue()

    def test_invalid_selection_never_defaults_to_every_card(self):
        code, writes, _ = self.run_cli(['', 'invalid'], True)
        self.assertEqual(code, 2)
        self.assertEqual(writes, 0)

    def test_failed_write_is_not_reported_as_success(self):
        code, writes, output = self.run_cli(['', 'all', 'synthetic.png'], False)
        self.assertEqual(code, 1)
        self.assertGreater(writes, 0)
        self.assertNotIn('successfully updated', output)
