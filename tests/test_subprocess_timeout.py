import io
import subprocess
import sys
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import apply_card_skin as skin
import aircard_backend as backend

OK = {'exitCode': 0, 'targetGatePassed': True, 'operation': {'ok': True}}


class StreamingTimeoutTests(unittest.TestCase):
    def test_silent_and_unterminated_output_obey_deadline(self):
        for program in ('import time; time.sleep(30)',
                        'import os,time; os.write(1,b"partial"); time.sleep(30)',
                        'import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(30)'):
            started = time.monotonic()
            with self.subTest(program=program), self.assertRaises(TimeoutError):
                skin.run_json_streaming([sys.executable, '-c', program], .15)
            self.assertLess(time.monotonic() - started, 2.5)

    def test_stderr_flood_does_not_deadlock_and_json_without_newline_works(self):
        events = []
        program = 'import os; os.write(2,b"x"*200000); print(\'{"type":"atc_progress","index":1}\',flush=True); os.write(1,b\'{"ok":true}\')'
        result = skin.run_json_streaming([sys.executable, '-c', program], 3, events.append)
        self.assertTrue(result['ok'])
        self.assertEqual(result['exitCode'], 0)
        self.assertEqual(len(events), 1)

    def test_callback_error_reaps_child(self):
        children = []
        real_popen = subprocess.Popen
        def spawn(*args, **kwargs):
            child = real_popen(*args, **kwargs)
            children.append(child)
            return child
        def fail(_):
            raise ValueError('callback failed')
        with patch.object(skin.subprocess, 'Popen', side_effect=spawn), self.assertRaises(ValueError):
            skin.run_json_streaming([sys.executable, '-c', 'import time; print(\'{"type":"atc_progress"}\',flush=True); time.sleep(30)'], 3, fail)
        self.assertIsNotNone(children[0].poll())

    def test_raw_stderr_is_not_exposed(self):
        with self.assertRaises(RuntimeError) as error:
            skin.run_json_streaming([sys.executable, '-c', 'import sys; sys.stderr.write("private-fixture")'], 3)
        self.assertNotIn('private-fixture', str(error.exception))

    def test_timeout_restores_books_and_does_not_retry(self):
        for operation in ('write_file', 'write_files_batch', 'remove_files_batch'):
            args = ('synthetic-device', '/synthetic-target')
            args += ('leaf', b'art') if operation == 'write_file' else ([('leaf', b'art')],) if operation == 'write_files_batch' else (['FrontFace'],)
            with self.subTest(operation=operation), patch.object(skin, 'native', return_value=OK) as native, \
                 patch.object(skin, 'run_json', side_effect=TimeoutError('sync deadline')), self.assertRaises(skin.AirliftOperationError):
                getattr(skin, operation)(*args)
            self.assertEqual([call.args[0] for call in native.call_args_list], ['snapshot-books', 'stage', 'finish-write'])

    def test_failed_stage_still_cleans_up(self):
        responses = [OK, {'exitCode': 1}, OK]
        with patch.object(skin, 'native', side_effect=responses) as native, patch.object(skin, 'run_json') as transfer:
            self.assertFalse(skin.write_file('synthetic-device', '/synthetic', 'leaf', b'x', retries=1))
        transfer.assert_not_called()
        self.assertEqual(native.call_args_list[-1].args[0], 'finish-write')

    def test_failed_cleanup_preserves_snapshot_and_aborts(self):
        with patch.object(skin, 'native', side_effect=[OK, OK, {'exitCode': 1}]), \
             patch.object(skin, 'run_json', return_value={'exitCode': 0, 'ok': True}), \
             patch.object(skin, 'preserve_books_snapshot', return_value=Path('/synthetic/recovery')) as preserve, \
             self.assertRaises(skin.AirliftOperationError):
            skin.write_file('synthetic-device', '/synthetic', 'leaf', b'x')
        preserve.assert_called_once()

    def test_backend_timeout_never_runs_fallback(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'image.png'
            path.write_bytes(b'x')
            with patch.object(backend, 'build_card_assets', return_value=[('leaf', b'x')]), \
                 patch.object(backend, 'write_files_batch', side_effect=skin.AirliftOperationError('sync deadline')), \
                 patch.object(backend, 'write_file') as single, patch.object(backend, 'remove_files') as remove, \
                 redirect_stdout(io.StringIO()) as output:
                self.assertFalse(backend.cmd_flash('synthetic-device', 'A'*27+'=', str(path)))
            single.assert_not_called()
            remove.assert_not_called()
            self.assertIn('sync deadline', output.getvalue())
