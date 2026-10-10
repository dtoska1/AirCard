#!/usr/bin/env bash
# Inspect the local bundle. Never starts the GUI, discovers a phone, or sends
# device commands. Helpers run with NO arguments, returning before discovery.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/build_support.sh"
[ "$(uname -s)" = Darwin ] || { echo "ERROR: Run this on macOS." >&2; exit 1; }
APP_INPUT="${1:-$ROOT_DIR/build/AirCard.app}"
APP_DIR="$(cd "$APP_INPUT" && pwd)"
RESOURCES_DIR="$APP_DIR/Contents/Resources"
DMG_PATH="${2:-$ROOT_DIR/build/AirCard.dmg}"

sw_vers
xcode-select -p
codesign --verify --deep --strict --verbose=4 "$APP_DIR"
codesign -dv --verbose=4 "$APP_DIR"
xattr -lr "$APP_DIR"
/usr/libexec/PlistBuddy -c 'Print :LSMinimumSystemVersion' "$APP_DIR/Contents/Info.plist"

for binary in "$APP_DIR/Contents/MacOS/AirCard" \
              "$RESOURCES_DIR/bin/device_helper" "$RESOURCES_DIR/bin/airtraffic_host"; do
    [ -x "$binary" ] || { echo "ERROR: Not executable: $binary" >&2; exit 1; }
    codesign --verify --strict --verbose=4 "$binary"
    codesign -dv --verbose=4 "$binary"
    file "$binary"
    lipo -info "$binary"
    lipo -verify_arch arm64 x86_64 "$binary"
    otool -L "$binary"
    for arch in arm64 x86_64; do
        actual="$(otool -arch "$arch" -l "$binary" | awk '/minos/ {print $2; exit} /LC_VERSION_MIN_MACOSX/ {legacy=1} legacy && /version / {print $2; exit}')"
        case "$actual" in
            14.0|14.0.0) ;;
            *) echo "ERROR: Unexpected minimum macOS for $arch in $binary: $actual" >&2; exit 1 ;;
        esac
    done
done

aircard_check_python "$RESOURCES_DIR"
for candidate in /usr/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do
    if [ -x "$candidate" ]; then AIRCARD_VERIFY_PYTHON="$candidate"; break; fi
done
# Test real sips PNG-to-PDF conversion using a synthetic pixel, outside the app.
PYTHONDONTWRITEBYTECODE=1 "$AIRCARD_VERIFY_PYTHON" -I -B - "$RESOURCES_DIR" <<'PY'
import struct, sys, zlib
sys.path.insert(0, sys.argv[1])
from card_assets import build_card_assets, PNG_ASSET_NAMES, PDF_ASSET_NAME

def chunk(kind, data):
    return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data))

png = b'\x89PNG\r\n\x1a\n'
png += chunk(b'IHDR', struct.pack('!2I5B', 1, 1, 8, 2, 0, 0, 0))
png += chunk(b'IDAT', zlib.compress(b'\0\xff\0\0')) + chunk(b'IEND', b'')
assets = dict(build_card_assets(png))
assert all(assets[name] == png for name in PNG_ASSET_NAMES)
assert assets[PDF_ASSET_NAME].startswith(b'%PDF-')
print('Real PNG/PDF asset preparation OK')
PY

# Loading the host architecture tests dyld/framework availability; argc guards
# precede device discovery in both main functions. Expected usage exit is 64.
for helper in device_helper airtraffic_host; do
    status=0
    "$RESOURCES_DIR/bin/$helper" || status=$?
    [ "$status" -eq 64 ] || { echo "ERROR: $helper failed load/usage check (exit $status)." >&2; exit 1; }
done
codesign --verify --deep --strict --verbose=4 "$APP_DIR"
if spctl --assess --type execute --verbose=4 "$APP_DIR"; then
    echo "Gatekeeper assessment accepted. This is not a device-functionality test."
else
    echo "Gatekeeper assessment did not accept this app. Expected for ad-hoc/unnotarized code; inspect the reason. This alone is not evidence of malware."
fi
if [ -f "$DMG_PATH" ]; then
    hdiutil verify "$DMG_PATH"
    xattr -l "$DMG_PATH"
    if codesign -dv --verbose=4 "$DMG_PATH"; then
        codesign --verify --strict --verbose=4 "$DMG_PATH"
    else
        echo "DMG has no signature (expected in default ad-hoc build mode)."
    fi
fi
echo "Bundle checks completed. No GUI launch or iPhone operation was performed. Review Gatekeeper output separately."
