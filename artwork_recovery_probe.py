"""Offline, non-mutating existence check for local Mac Wallet artwork links.

Only the Mac's ~/Library/Passes/Cards is examined. No iPhone helper, AirLift,
network client, raw URL, card identifier, or artwork bytes are exposed.
A negative result is INCONCLUSIVE about the iPhone's protected Wallet files.
"""
from __future__ import annotations

import json
import os
import re
import stat
from pathlib import Path

from wallet_identity import CARD_ID

MAX_PASS_FOLDERS = 512
MAX_CARD_ENTRIES = 4096
MAX_PASS_ENTRIES = 128
MAX_REFERENCE_BYTES = 256 * 1024

REFERENCE_NAME = re.compile(r"\AcardBackgroundCombined[A-Za-z0-9@._-]*\.urls\Z")
DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW

# A bounded syntactic hint, not an authenticated URL or proof of artwork.
URL_MARKERS = (
    b"https://", b"http://",
    "https://".encode("utf-16-le"), "http://".encode("utf-16-le"),
    "https://".encode("utf-16-be"), "http://".encode("utf-16-be"),
)


def _open_directory(parent_fd: int, leaf: str) -> int:
    fd = os.open(leaf, DIR_FLAGS, dir_fd=parent_fd)
    try:
        if not stat.S_ISDIR(os.fstat(fd).st_mode):
            raise OSError("Not a directory")
        return fd
    except BaseException:
        os.close(fd)
        raise


def inspect_reference(parent_fd: int, leaf: str) -> tuple[bool, bool]:
    """Return (plausible_url, fully_checked); never return URL contents."""
    fd = os.open(leaf, FILE_FLAGS, dir_fd=parent_fd)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            return False, False
        payload = os.read(fd, MAX_REFERENCE_BYTES + 1)
        if len(payload) > MAX_REFERENCE_BYTES:
            return False, False
        lowered = payload.lower()
        return any(marker in lowered for marker in URL_MARKERS), True
    finally:
        os.close(fd)


def probe_local_cache(root: Path) -> dict:
    report = {
        "scope": "Mac-only; no iPhone access",
        "status": "unavailable",
        "passesChecked": 0,
        "referenceFiles": 0,
        "plausibleUrlFiles": 0,
        "errors": 0,
        "limited": False,
        "note": "URL counts are only hints. Empty or unavailable Mac cache does not rule out references on the iPhone.",
    }

    try:
        root_fd = os.open(root, DIR_FLAGS)
    except FileNotFoundError:
        return report
    except OSError:
        report["status"] = "inaccessible"
        report["errors"] += 1
        return report

    try:
        try:
            cards_fd = _open_directory(root_fd, "Cards")
        except FileNotFoundError:
            return report
        except OSError:
            report["status"] = "inaccessible"
            report["errors"] += 1
            return report

        try:
            report["status"] = "empty"
            try:
                with os.scandir(cards_fd) as entries:
                    for index, entry in enumerate(entries):
                        if index >= MAX_CARD_ENTRIES or report["passesChecked"] >= MAX_PASS_FOLDERS:
                            report["limited"] = True
                            break
                        if not entry.name.endswith(".pkpass"):
                            continue
                        identifier = entry.name[:-len(".pkpass")]
                        if CARD_ID.fullmatch(identifier) is None:
                            continue
                        try:
                            pass_fd = _open_directory(cards_fd, entry.name)
                        except OSError:
                            report["errors"] += 1
                            continue
                        try:
                            report["passesChecked"] += 1
                            with os.scandir(pass_fd) as leaves:
                                for leaf_index, leaf in enumerate(leaves):
                                    if leaf_index >= MAX_PASS_ENTRIES:
                                        report["limited"] = True
                                        break
                                    if REFERENCE_NAME.fullmatch(leaf.name) is None:
                                        continue
                                    # Skip obvious symlinks; O_NOFOLLOW also prevents
                                    # following one swapped into place after this check.
                                    if leaf.is_symlink():
                                        report["errors"] += 1
                                        continue
                                    report["referenceFiles"] += 1
                                    try:
                                        plausible, complete = inspect_reference(pass_fd, leaf.name)
                                        if plausible:
                                            report["plausibleUrlFiles"] += 1
                                        if not complete:
                                            report["errors"] += 1
                                    except OSError:
                                        report["errors"] += 1
                        except OSError:
                            report["errors"] += 1
                        finally:
                            os.close(pass_fd)
            except OSError:
                report["errors"] += 1
        finally:
            os.close(cards_fd)
    finally:
        os.close(root_fd)

    if report["limited"] or report["errors"]:
        report["status"] = "partial"
    elif report["passesChecked"]:
        report["status"] = "complete"
    return report


def main() -> None:
    print(json.dumps(probe_local_cache(Path.home() / "Library" / "Passes")))


if __name__ == "__main__":
    main()
