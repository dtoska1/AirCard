#!/usr/bin/env python3
"""Apply custom card skins to Apple Wallet passes using airlift exploit."""

import io
import json
import os
import plistlib
import posixpath
import secrets
import selectors
import shutil
from contextlib import contextmanager
import stat
import struct
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from wallet_identity import require_card_id, wallet_directory

ROOT = Path(__file__).resolve().parent
DEVICE_HELPER = ROOT / "bin" / "device_helper" if (ROOT / "bin" / "device_helper").is_file() else ROOT / "build" / "device_helper"
AIRTRAFFIC_HOST = ROOT / "bin" / "airtraffic_host" if (ROOT / "bin" / "airtraffic_host").is_file() else ROOT / "build" / "airtraffic_host"
AIRLOCK_ROOT = "/var/mobile/Media/Airlock/Book"
SOURCE_PREFIX = "airlift-src-"
LINK_PREFIX = "airlift-link-"
RECOVERED_PREFIX = "airlift-recovered-"
SZ_EXTRA_ID = 0x5A53


def zip_info(name: str, mode: int) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(2026, 9, 14, 5, 0, 0))
    info.create_system = 3
    info.compress_type = zipfile.ZIP_STORED
    info.external_attr = (mode & 0xFFFF) << 16
    info.extra = struct.pack("<HHH", SZ_EXTRA_ID, 2, mode & 0xFFFF)
    return info


def build_archive(target: str, payload: bytes) -> bytes:
    target_tail = target[1:]
    metadata = plistlib.dumps(
        {"Version": 2}, fmt=plistlib.FMT_BINARY, sort_keys=True
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", allowZip64=False) as archive:
        archive.writestr(zip_info("META-INF/", stat.S_IFDIR | 0o755), b"")
        archive.writestr(
            zip_info(
                "META-INF/com.apple.ZipMetadata.plist", stat.S_IFREG | 0o600
            ),
            metadata,
        )
        for directory in ("p0/", "p0/p1/", "p0/p1/p2/"):
            archive.writestr(zip_info(directory, stat.S_IFDIR | 0o755), b"")
        archive.writestr(
            zip_info("p0/p1/p2/link", stat.S_IFLNK | 0o777),
            f"../../../{target_tail}".encode(),
        )
        cursor = ""
        for component in target_tail.split("/"):
            cursor += component + "/"
            archive.writestr(zip_info(cursor, stat.S_IFDIR | 0o755), b"")
        archive.writestr(zip_info("payload", stat.S_IFREG | 0o600), payload)
    return output.getvalue()


def build_archive_multi(target: str, files: list[tuple[str, bytes]]) -> bytes:
    target_tail = target.lstrip("/")
    metadata = plistlib.dumps(
        {"Version": 2}, fmt=plistlib.FMT_BINARY, sort_keys=True
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", allowZip64=False) as archive:
        archive.writestr(zip_info("META-INF/", stat.S_IFDIR | 0o755), b"")
        archive.writestr(
            zip_info(
                "META-INF/com.apple.ZipMetadata.plist", stat.S_IFREG | 0o600
            ),
            metadata,
        )
        for directory in ("p0/", "p0/p1/", "p0/p1/p2/"):
            archive.writestr(zip_info(directory, stat.S_IFDIR | 0o755), b"")
        archive.writestr(
            zip_info("p0/p1/p2/link", stat.S_IFLNK | 0o777),
            f"../../../{target_tail}".encode(),
        )
        cursor = ""
        for component in target_tail.split("/"):
            if not component:
                continue
            cursor += component + "/"
            archive.writestr(zip_info(cursor, stat.S_IFDIR | 0o755), b"")
        for idx, (_leaf, payload) in enumerate(files):
            archive.writestr(zip_info(f"payload_{idx}", stat.S_IFREG | 0o600), payload)
        if files:
            archive.writestr(zip_info("payload", stat.S_IFREG | 0o600), files[0][1])
    return output.getvalue()


def build_books(identifiers: list[str]) -> bytes:
    rows = [
        {"Persistent ID": identifier, "Item ID": str(index), "DSID": "1"}
        for index, identifier in enumerate(identifiers, 1)
    ]
    return plistlib.dumps({"Books": rows}, fmt=plistlib.FMT_BINARY, sort_keys=True)


def run_json(command: list[str], timeout: int) -> dict:
    return run_json_streaming(command, timeout)


def run_json_streaming(command: list[str], timeout: float, on_progress=None) -> dict:
    """Drain both pipes without blocking on a newline; enforce a monotonic deadline."""
    deadline = time.monotonic() + timeout
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = None
    pending = b""
    stderr_tail = b""
    limit = 16 * 1024 * 1024
    stderr_limit = 64 * 1024

    def consume(line):
        nonlocal result
        try:
            value = json.loads(line)
        except (ValueError, UnicodeDecodeError):
            return
        if isinstance(value, dict):
            if value.get("type") == "atc_progress" and on_progress:
                on_progress(value)
            result = value

    try:
        with selectors.DefaultSelector() as selector:
            for stream in (proc.stdout, proc.stderr):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ)
            while selector.get_map() or proc.poll() is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(f"{Path(command[0]).name}: AirTraffic deadline exceeded after {timeout}s; sync/transfer did not finish")
                for key, _ in selector.select(min(remaining, 0.1)):
                    chunk = os.read(key.fileobj.fileno(), 8192)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    if key.fileobj is proc.stderr:
                        stderr_tail = (stderr_tail + chunk)[-stderr_limit:]
                    else:
                        pending += chunk
                        while b"\n" in pending:
                            line, pending = pending.split(b"\n", 1)
                            consume(line)
                        if len(pending) > limit:
                            raise RuntimeError("AirTraffic output exceeded the maximum line length")
            if pending:
                consume(pending)
        proc.wait(timeout=max(0.001, deadline - time.monotonic()))
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=1)
        proc.stdout.close()
        proc.stderr.close()
    if result is None:
        # Native stderr can contain device IDs/paths. Drain it, but never echo it.
        raise RuntimeError(f"{Path(command[0]).name} returned no JSON result (exit {proc.returncode}; {len(stderr_tail)} diagnostic bytes withheld)")
    result["exitCode"] = proc.returncode
    return result


class AirliftOperationError(RuntimeError):
    """Stop high-level fallback after a timeout or uncertain restoration."""


def preserve_books_snapshot(snapshot_root):
    recovery_root = Path.home() / ".aircard-recovery"
    recovery_root.mkdir(mode=0o700, exist_ok=True)
    destination = recovery_root / secrets.token_hex(10)
    shutil.copytree(snapshot_root, destination)
    for directory, _, files in os.walk(destination):
        os.chmod(directory, 0o700)
        for name in files:
            os.chmod(Path(directory) / name, 0o600)
    return destination


def retain_read_recovery(udid, snapshot_root):
    # Persist first: disconnected devices can make restore-books itself raise.
    location = preserve_books_snapshot(snapshot_root)
    try:
        native("restore-books", udid, os.fspath(snapshot_root))
    except Exception:
        pass
    print(f"AirLift read needs recovery; original staging retained, Books snapshot: {location}", file=sys.stderr)


@contextmanager
def staged_write(udid, source, link, recovered, archive_path, books_path, snapshot_root):
    """Restore Books even if staging or AirTraffic raises before returning JSON."""
    cleanup = {"done": False}
    try:
        stage = native("stage", udid, source, link, recovered,
                       os.fspath(archive_path), os.fspath(books_path), os.fspath(snapshot_root))
        if not operation_ok(stage):
            raise RuntimeError("Could not stage AirLift write")
        yield cleanup
    finally:
        if not cleanup["done"]:
            try:
                finish = native("finish-write", udid, source, link, recovered, os.fspath(snapshot_root))
                restored = operation_ok(finish)
            except Exception:
                restored = False
            if not restored:
                try:
                    location = preserve_books_snapshot(snapshot_root)
                except OSError as error:
                    raise AirliftOperationError("Books restoration failed and its snapshot could not be retained; stop and inspect the device") from error
                raise AirliftOperationError(f"Books restoration/cleanup could not be verified. Stop; recovery snapshot retained at {location}")



def native(command: str, udid: str, *arguments: str) -> dict:
    return run_json(
        [os.fspath(DEVICE_HELPER), command, udid, *arguments], timeout=60
    )


def operation_ok(result: dict) -> bool:
    return bool(
        result.get("exitCode") == 0
        and result.get("targetGatePassed")
        and result.get("operation", {}).get("ok")
    )


def read_file(udid: str, target: str, leaf: str, retries: int = 1) -> "bytes | None":
    """Exports a file outside Media into Media, reads it via AFC, restores it.

    Move semantics: the AirTraffic sync MOVES target/leaf to Media/recovered.
    The original is written back immediately with write_file, then the export
    staging is cleaned and Books preimage restored. Returns file bytes, or
    None on failure. Test only on disposable paths before Wallet data.
    """
    if "/" in leaf or leaf in ("", ".", ".."):
        raise ValueError("leaf must be a plain file name")
    for attempt in range(1, max(1, retries) + 1):
        try:
            token = secrets.token_hex(10)
            source = f"{SOURCE_PREFIX}{token}"
            link_destination = f"{LINK_PREFIX}{token}"
            recovered = f"{RECOVERED_PREFIX}{token}"

            link_identifier = f"../../{source}/p0/p1/p2/link"
            target_path = posixpath.join(target, leaf)
            target_identifier = posixpath.relpath(target_path, AIRLOCK_ROOT)

            identifiers = [link_identifier, target_identifier]
            destinations = [link_destination, recovered]

            with tempfile.TemporaryDirectory(prefix="airlift-read-") as temporary:
                work = Path(temporary)
                archive_path = work / "payload.zip"
                books_path = work / "Books.plist"
                local_out = work / "recovered.bin"
                snapshot_root = work / "books-snapshot"
                snapshot_root.mkdir()

                archive_path.write_bytes(build_archive(target, b"aircard-backup-staging"))
                books_path.write_bytes(build_books(identifiers))

                snapshot = native("snapshot-books", udid, os.fspath(snapshot_root))
                if not operation_ok(snapshot):
                    if attempt < retries:
                        time.sleep(0.3 * attempt)
                        continue
                    return None

                stage = native(
                    "stage",
                    udid,
                    source,
                    link_destination,
                    recovered,
                    os.fspath(archive_path),
                    os.fspath(books_path),
                    os.fspath(snapshot_root),
                )
                if not operation_ok(stage):
                    try:
                        native("finish-write", udid, source, link_destination,
                               recovered, os.fspath(snapshot_root))
                    except Exception:
                        pass
                    if attempt < retries:
                        time.sleep(0.3 * attempt)
                        continue
                    return None

                atc_cmd = [os.fspath(AIRTRAFFIC_HOST), udid]
                for identifier, destination in zip(identifiers, destinations):
                    atc_cmd.extend((identifier, destination))
                try:
                    atc = run_json(atc_cmd, timeout=120)
                except Exception:
                    # Transfer may have moved the original before failing. Keep
                    # generated recovery data, restore Books only, retain snapshot.
                    retain_read_recovery(udid, snapshot_root)
                    return None
                if not (atc.get("exitCode") == 0 and atc.get("ok")):
                    retain_read_recovery(udid, snapshot_root)
                    return None

                rd = native("afc-read", udid, recovered, os.fspath(local_out))
                if not operation_ok(rd) or not local_out.is_file():
                    # Original is sitting in Media/recovered; do NOT delete it.
                    # Leave staging for manual recovery, report failure.
                    retain_read_recovery(udid, snapshot_root)
                    return None
                data = local_out.read_bytes()

                try:
                    restored = write_file(udid, target, leaf, data, retries=3)
                except Exception:
                    restored = False
                if not restored:
                    # The recovered file may now be the ONLY original. Do not
                    # call finish-write: it deletes recovered unconditionally.
                    retain_read_recovery(udid, snapshot_root)
                    return data

                finish = native(
                    "finish-write",
                    udid,
                    source,
                    link_destination,
                    recovered,
                    os.fspath(snapshot_root),
                )
                if restored and operation_ok(finish):
                    return data
                # Bytes were still captured; return them so caller can save
                # a backup copy even if cleanup reported incomplete.
                if data:
                    return data
                return None
        except Exception:
            pass
        if attempt < retries:
            time.sleep(0.3 * attempt)
    return None


def write_file(udid: str, target: str, leaf: str, payload: bytes, retries: int = 3) -> bool:
    for attempt in range(1, max(1, retries) + 1):
        try:
            token = secrets.token_hex(10)
            source = f"{SOURCE_PREFIX}{token}"
            link_destination = f"{LINK_PREFIX}{token}"
            recovered = f"{RECOVERED_PREFIX}{token}"

            link_identifier = f"../../{source}/p0/p1/p2/link"
            payload_identifier = f"../../{source}/payload"

            # Step 1: move link to media
            # Step 2: move new payload into link/leaf (atomically creates or overwrites target)
            identifiers = [link_identifier, payload_identifier]
            destinations = [
                link_destination,
                posixpath.join(link_destination, leaf),
            ]

            with tempfile.TemporaryDirectory(prefix="airlift-write-") as temporary:
                work = Path(temporary)
                archive_path = work / "payload.zip"
                books_path = work / "Books.plist"
                snapshot_root = work / "books-snapshot"
                snapshot_root.mkdir()

                archive_path.write_bytes(build_archive(target, payload))
                books_path.write_bytes(build_books(identifiers))

                snapshot = native("snapshot-books", udid, os.fspath(snapshot_root))
                if not operation_ok(snapshot):
                    if attempt < retries:
                        time.sleep(0.3 * attempt)
                        continue
                    return False

                with staged_write(udid, source, link_destination, recovered,
                                  archive_path, books_path, snapshot_root):
                    atc_cmd = [os.fspath(AIRTRAFFIC_HOST), udid]
                    for identifier, destination in zip(identifiers, destinations):
                        atc_cmd.extend((identifier, destination))
                    atc = run_json(atc_cmd, timeout=120)


            ok = bool(atc.get("exitCode") == 0 and atc.get("ok"))
            if ok:
                return True
        except AirliftOperationError:
            raise
        except TimeoutError as error:
            raise AirliftOperationError(str(error) + "; operation stopped") from error
        except Exception:
            pass

        if attempt < retries:
            time.sleep(0.3 * attempt)

    return False


def write_files_batch(
    udid: str,
    target: str,
    files: list[tuple[str, bytes]],
    retries: int = 3,
    progress_callback=None,
) -> bool:
    if not files:
        return True

    for attempt in range(1, max(1, retries) + 1):
        try:
            token = secrets.token_hex(10)
            source = f"{SOURCE_PREFIX}{token}"
            link_destination = f"{LINK_PREFIX}{token}"
            recovered = f"{RECOVERED_PREFIX}{token}"

            link_identifier = f"../../{source}/p0/p1/p2/link"
            identifiers = [link_identifier]
            destinations = [link_destination]

            for idx, (leaf, _) in enumerate(files):
                identifiers.append(f"../../{source}/payload_{idx}")
                destinations.append(posixpath.join(link_destination, leaf))

            with tempfile.TemporaryDirectory(prefix="airlift-batch-") as temporary:
                work = Path(temporary)
                archive_path = work / "payload.zip"
                books_path = work / "Books.plist"
                snapshot_root = work / "books-snapshot"
                snapshot_root.mkdir()

                archive_path.write_bytes(build_archive_multi(target, files))
                books_path.write_bytes(build_books(identifiers))

                snapshot = native("snapshot-books", udid, os.fspath(snapshot_root))
                if not operation_ok(snapshot):
                    if attempt < retries:
                        time.sleep(0.4 * attempt)
                        continue
                    return False

                with staged_write(udid, source, link_destination, recovered,
                                  archive_path, books_path, snapshot_root):
                    atc_cmd = [os.fspath(AIRTRAFFIC_HOST), udid]
                    for identifier, destination in zip(identifiers, destinations):
                        atc_cmd.extend((identifier, destination))

                    timeout = max(120, len(files) * 2)
                    if progress_callback:
                        atc = run_json_streaming(atc_cmd, timeout=timeout, on_progress=progress_callback)
                    else:
                        atc = run_json(atc_cmd, timeout=timeout)


            ok = bool(atc.get("exitCode") == 0 and atc.get("ok"))
            if ok:
                return True
        except AirliftOperationError:
            raise
        except TimeoutError as error:
            raise AirliftOperationError(str(error) + "; operation stopped") from error
        except Exception:
            pass

        if attempt < retries:
            time.sleep(0.4 * attempt)

    return False


def remove_files_batch(udid: str, target: str, leaves: list[str], retries: int = 3) -> bool:
    """Remove specific files through the relocated Airlift symlink in a single batch."""
    if not leaves:
        return True
    if any(not leaf or "/" in leaf or leaf in {".", ".."} for leaf in leaves):
        raise ValueError("cache leaves must be plain file names")

    for attempt in range(1, max(1, retries) + 1):
        try:
            token = secrets.token_hex(10)
            source = f"{SOURCE_PREFIX}{token}"
            link_destination = f"{LINK_PREFIX}{token}"
            recovered = f"{RECOVERED_PREFIX}{token}"
            link_identifier = f"../../{source}/p0/p1/p2/link"
            protected_identifiers = [
                f"../../{link_destination}/{leaf}" for leaf in leaves
            ]
            removed_destinations = [
                f"{source}/removed-{index}" for index in range(len(leaves))
            ]

            with tempfile.TemporaryDirectory(prefix="airlift-remove-") as temporary:
                work = Path(temporary)
                archive_path = work / "payload.zip"
                books_path = work / "Books.plist"
                snapshot_root = work / "books-snapshot"
                snapshot_root.mkdir()

                # Relocate the symlink first, then have AirTraffic move each
                # protected cache file out through it. This is a real unlink;
                # AFCRemovePath cannot traverse the protected link on iOS 27.
                archive_path.write_bytes(build_archive(target, b"aircard-v2"))
                books_path.write_bytes(build_books(
                    [link_identifier, *protected_identifiers]
                ))

                snapshot = native("snapshot-books", udid, os.fspath(snapshot_root))
                if not operation_ok(snapshot):
                    raise RuntimeError("could not snapshot Books state")
                with staged_write(udid, source, link_destination, recovered,
                                  archive_path, books_path, snapshot_root) as cleanup:
                    atc = run_json(
                        [os.fspath(AIRTRAFFIC_HOST), udid,
                         link_identifier, link_destination,
                         *[part for pair in zip(protected_identifiers, removed_destinations)
                           for part in pair]],
                        timeout=120,
                    )
                    if atc.get("exitCode") != 0 or not atc.get("ok"):
                        raise RuntimeError("Could not relocate cache link")
                    finish = native("finish-moved-removal", udid, source, link_destination,
                                    recovered, os.fspath(snapshot_root), str(len(leaves)))
                    removed = operation_ok(finish)
                    cleanup["done"] = removed
                if removed:
                    return True
        except AirliftOperationError:
            raise
        except TimeoutError as error:
            raise AirliftOperationError(str(error) + "; operation stopped") from error
        except Exception:
            pass
        if attempt < retries:
            time.sleep(0.4 * attempt)
    return False


def remove_files(udid: str, target: str, leaves: list[str], retries: int = 3) -> bool:
    """Remove specific files through the relocated Airlift symlink.

    Wallet only rebuilds its rendered card faces when the old cache entries are
    absent. Overwriting them with arbitrary bytes leaves stale artwork active on
    recent iOS releases, so cache invalidation must be a real unlink operation.
    """
    if not leaves:
        return True

    # 1. Try removing all requested leaves in a fast single batch
    if remove_files_batch(udid, target, leaves, retries=retries):
        return True

    # 2. If the combined batch fails (e.g. PlaceHolder or Preview does not exist
    # on this device/card), remove present leaves individually.
    if len(leaves) > 1:
        removed_any = False
        for leaf in leaves:
            if remove_files_batch(udid, target, [leaf], retries=1):
                removed_any = True
        if removed_any:
            return True

    return False


def invalidate_cache(udid: str, card_hash: str) -> bool:
    """Remove every rendered card face so Wallet must rebuild from the pass."""
    require_card_id(card_hash)
    all_ok = True
    cache_leaves = ["FrontFace", "PlaceHolder", "Preview"]
    for ext in [".cache", ".pkcache"]:
        cache_dir = wallet_directory(card_hash, ext)
        try:
            all_ok = remove_files(udid, cache_dir, cache_leaves) and all_ok
        except Exception:
            all_ok = False
    return all_ok


def main():
    if len(sys.argv) < 3:
        print("Usage: apply_card_skin.py <udid> <image_path> [card_hash ...]")
        return
    udid = sys.argv[1]
    img_path = Path(sys.argv[2])
    if not img_path.is_file():
        print(f"Error: {img_path} not found")
        sys.exit(1)
    img_data = img_path.read_bytes()
    hashes = [require_card_id(value) for value in sys.argv[3:]]

    print(f"Loaded image from batter: {len(img_data)} bytes")
    print(f"Targeting {len(hashes)} cards on device {udid}...")

    for index, h in enumerate(hashes, 1):
        target_dir = wallet_directory(h, ".pkpass")
        print(f"\n[{index}/{len(hashes)}] Processing card: {h}")

        print("  -> Writing card artwork (fast batch)...")
        card_assets = [
            ("cardBackgroundCombined@3x.png", img_data),
            ("cardBackgroundCombined@2x.png", img_data),
        ]
        ok_batch = write_files_batch(udid, target_dir, card_assets)
        if not ok_batch:
            ok3x = write_file(udid, target_dir, "cardBackgroundCombined@3x.png", img_data)
            ok2x = write_file(udid, target_dir, "cardBackgroundCombined@2x.png", img_data)
            ok_batch = ok3x and ok2x
        print(f"     Result: {'SUCCESS' if ok_batch else 'FAILED'}")

        print("  -> Invalidating pass cache...")
        ok_cache = invalidate_cache(udid, h)
        print(f"     Result: {'SUCCESS' if ok_cache else 'FAILED (or cache already empty)'}")

    print("\nAll done! Please force close Wallet on your iPhone and reopen it.")


if __name__ == "__main__":
    main()
