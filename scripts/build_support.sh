#!/usr/bin/env bash
# Sourced by build.sh and the read-only Mac verification script.

# Match the GUI's first-executable selection exactly. Do not silently choose a
# later Python when the GUI would still launch a broken /usr/bin/python3 shim.
aircard_check_python() {
    local resources="$1"
    shift
    local candidate selected=""
    if [ "$#" -eq 0 ]; then
        set -- /usr/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3
    fi
    for candidate in "$@"; do
        if [ -x "$candidate" ]; then
            selected="$candidate"
            break
        fi
    done
    if [ -z "$selected" ]; then
        echo "ERROR: AirCard requires installed Python 3.9+; Python is not bundled." >&2
        return 1
    fi
    if ! PYTHONDONTWRITEBYTECODE=1 "$selected" -I -B -c '
import sys
assert sys.version_info >= (3, 9), "Python 3.9+ required"
sys.path.insert(0, sys.argv[1])
import wallet_identity, card_assets, apply_card_skin, aircard, aircard_backend, wallet_catalog
print("Python runtime and backend imports OK:", sys.executable, sys.version.split()[0])
' "$resources"; then
        echo "ERROR: The GUI selects $selected, but it cannot import the backend." >&2
        echo "Repair/select usable Apple Developer Tools or this Python installation, then retry. Nothing was installed automatically." >&2
        return 1
    fi
}

# Helpers live in Resources/bin, outside conventional nested-code locations.
# Sign and verify each explicitly before sealing the enclosing app.
aircard_sign_app() {
    local app="$1" identity="$2" tool
    local options=()
    if [ "$identity" != "-" ]; then
        options=(--options runtime --timestamp)
    fi
    for tool in device_helper airtraffic_host; do
        codesign --force "${options[@]}" --sign "$identity" \
            "$app/Contents/Resources/bin/$tool" || return
        codesign --verify --strict --verbose=4 \
            "$app/Contents/Resources/bin/$tool" || return
    done
    codesign --force "${options[@]}" --sign "$identity" "$app" || return
    codesign --verify --deep --strict --verbose=4 "$app"
}
