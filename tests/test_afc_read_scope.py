"""Compile the production recovery-name validator on macOS."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class AFCReadScopeTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == 'darwin', 'Objective-C Foundation requires macOS')
    def test_exact_generated_recovery_names(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / 'Sources/device_helper.m').read_text()
        predicate = source[source.index('static BOOL IsLowercaseHex('):source.index('static BOOL GeneratedNamesMatch(')]
        self.assertIn('if (!GeneratedToken(mediaPath, AIRLIFT_RECOVERED_PREFIX))', source)
        main = r'''
int main(void) { @autoreleasepool {
    assert(GeneratedToken(@"airlift-recovered-0123456789abcdef0123", @"airlift-recovered-"));
    for (NSString *bad in @[@"Books/Books.plist", @"../private", @"airlift-recovered-0123456789abcdef0123/file", @"airlift-recovered-0123456789ABCDEF0123", @"airlift-recovered-short", @"airlift-src-0123456789abcdef0123"]) {
        assert(!GeneratedToken(bad, @"airlift-recovered-"));
    }
} return 0; }
'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'recovery.m'
            path.write_text('#import <Foundation/Foundation.h>\n#include <assert.h>\n' + predicate + main)
            binary = Path(directory) / 'recovery'
            subprocess.run(['xcrun', 'clang', '-fobjc-arc', '-framework', 'Foundation', str(path), '-o', str(binary)], check=True, capture_output=True)
            subprocess.run([str(binary)], check=True)
