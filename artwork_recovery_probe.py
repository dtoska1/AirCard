"""Offline, non-mutating check for surviving Wallet artwork URL references.

Scope: local Mac Wallet pass folders only. Never touches an iPhone, downloads
artwork, exports a tokenized URL or invokes AirLift. A negative result does NOT
prove that the references are absent from an iPhone's protected pass folder.
"""
from __future__ import annotations

import json
import os
import plistlib
import re
from pathlib import Path

from wallet_identity import CARD_ID

MAX_ENTRIES = 512
MAX_REFERENCE_BYTES = 256 * 1024
REFERENCE_NAME = re.compile(r"\AcardBackgroundCombined[A-Za-z0-9@._-]*\.urls\Z")
URL_SCHEME = re.compile(rb"https?://", re.IGNORECASE)


def contains_url(value, depth=0) -> bool:
    if depth > 12:
        return False
    if isinstance(value, str):
        return value.startswith(("https://", "http://"))
    if isinstance(value, (bytes, bytearray)):
        return bool(URL_SCHEME.search(value))
    if isinstance(value, dict):
        return any(contains_url(v, depth + 1) for v in value.values())
    if isinstance(value, (tuple, list)):
        return any(contains_url(v, depth + 1) for v in value)
    return False


def inspect_reference(path: Path) -> bool:
    # Do not follow symlinks even if a file was replaced after enumeration.
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as stream:
        payload = stream.read(MAX_REFERENCE_BYTES + 1)
    if len(payload) > MAX_REFERENCE_BYTES:
        return False
    try:
        parsed = plistlib.loads(payload)
    except (ValueError, TypeError, OverflowError, plistlib.InvalidFileException, OSError):
        parsed = payload
    return contains_url(parsed)


def probe_local_cache(root: Path) -> dict:
    result = {
        "scope": "Mac-only; no iPhone access",
        "passesChecked": 0,
        "referenceFiles": 0,
        "plausibleUrlFiles": 0,
        "limited": False,
        "note": "No artwork is downloaded or restored. An empty result does not rule out surviving references on the iPhone.",
    }
    cards_root = root / "Cards"
    if cards_root.is_symlink() or not cards_root.is_dir():
        return result
    try:
        directories = sorted(cards_root.iterdir(), key=lambda p: p.name)
    except OSError:
        return result
    for entry in directories:
        if result["passesChecked"] >= MAX_ENTRIES:
            result["limited"] = True
            break
        if entry.is_symlink() or entry.suffix != ".pkpass" or not CARD_ID.fullmatch(entry.stem):
            continue
        if not entry.is_dir():
            continue
        result["passesChecked"] += 1
        try:
            leaves = sorted(entry.iterdir(), key=lambda p: p.name)
        except OSError:
            continue
        for leaf in leaves:
            if not REFERENCE_NAME.fullmatch(leaf.name) or leaf.is_symlink() or not leaf.is_file():
                continue
            result["referenceFiles"] += 1
            try:
                if inspect_reference(leaf):
                    result["plausibleUrlFiles"] += 1
            except OSError:
                continue
    return result


def main() -> None:
    print(json.dumps(probe_local_cache(Path.home() / "Library" / "Passes")))


if __name__ == "__main__":
    main()
