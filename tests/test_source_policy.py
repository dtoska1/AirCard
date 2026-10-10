"""Review tripwires for obvious networking additions, not proof of non-exfiltration."""
import ast
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SourcePolicyTests(unittest.TestCase):
    def test_python_has_no_internet_clients_or_dynamic_execution(self):
        blocked = {'requests', 'urllib', 'http', 'httpx', 'aiohttp', 'socket', 'ftplib', 'smtplib', 'websocket', 'websockets', 'dns'}
        for path in ROOT.glob('*.py'):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                imports = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module or ''] if isinstance(node, ast.ImportFrom) else []
                for name in imports:
                    self.assertNotIn(name.split('.')[0], blocked, path.name)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, {'eval', 'exec', '__import__'}, path.name)

    def test_native_source_and_build_have_no_internet_client_additions(self):
        paths = [ROOT / 'AirCardApp.swift', ROOT / 'build.sh', ROOT / 'Makefile', * (ROOT / 'Sources').glob('*')]
        blocked = r'\b(?:URLSession|NWConnection|CFHTTPMessageCreateRequest|CFSocketConnectToAddress|curl|wget|SFSafariViewController)\b|Network\.framework'
        for path in paths:
            if path.is_file():
                self.assertIsNone(re.search(blocked, path.read_text()), path.name)
        # sys/socket.h and setsockopt in device_helper configure Apple's local
        # service socket. Reject introducing independently opened Internet sockets.
        native = (ROOT / 'Sources/device_helper.m').read_text()
        self.assertIsNone(re.search(r'\b(?:socket|connect|getaddrinfo)\s*\(', native))

    def test_ui_url_literals_remain_reviewed_clickable_links(self):
        source = (ROOT / 'AirCardApp.swift').read_text()
        urls = set(re.findall(r'URL\(string: "(https?://[^\"]+)"', source))
        self.assertEqual(urls, {
            'https://github.com/mak5er', 'https://github.com/Lumid-Off',
            'https://x.com/mak5er', 'https://x.com/LumidOff',
            'https://www.paypal.com/donate/?hosted_button_id=98QRTC2HFRA4Y',
        })
