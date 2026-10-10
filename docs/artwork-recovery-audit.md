# Original Wallet artwork recovery — independent safety audit brief

## User objective and hard constraints

Restore the genuine issuer-provided **Revolut and Wise** artwork on the
user's existing iPhone Wallet payment cards without deleting or re-provisioning
the cards, contacting the banks or using a guessed replacement image.
The original artwork was already overwritten by earlier AirCard flashes.
There is no pre-change backup and no unaffected second device.

Do **not** claim that historical Wallet/system records of modification can
be erased; byte-identical artwork does not prove a history-free phone.

## Repository / scope

- Repository: `dtoska1/AirCard`
- Branch: `hardening`; `main` must remain unchanged.
- New safe first-stage diagnostic:
  - `artwork_recovery_probe.py`
  - `tests/test_artwork_recovery_probe.py`
  - `AirCardApp.swift` (Recovery Check button, local result)
  - `Sources/WalletDiscovery.swift` (typed diagnostic result)
  - `build.sh`
- Existing high-risk protected-file transfer code:
  - `apply_card_skin.py`, especially `read_file`, `staged_write`,
    `retain_read_recovery`, `write_file`, `remove_files_batch`
  - `Sources/device_helper.m`
  - `aircard_backend.py`

## Confirmed code properties

The initial Recovery Check only scans this Mac's
`~/Library/Passes/Cards/*.pkpass/cardBackgroundCombined*.urls` files.
No device connection is used, no URLs/card IDs/tokens are printed, no
network requests are made, and no originals are exported or written.
The result is **Mac-local only**, and a zero result is inconclusive about
the iPhone. This user's Mac previously lacked a usable payment-card cache.

The original AirCard flash replaced:
`cardBackgroundCombined@3x.png`,
`cardBackgroundCombined@2x.png`,
`cardBackgroundCombined.pdf`, then removed derived Wallet caches.
It did not deliberately target `cardBackgroundCombined*.urls` files.

Independent technical documentation suggests these `.urls` files **may**
exist inside the protected on-device `*.pkpass` directories and may
contain issuer artwork URLs. Presence on this user's iPhone, URL validity,
auth requirements, and whether such URLs return the exact original files
are **unverified**.

## Safety questions for the reviewer

1. Is the Mac-only diagnostic actually free of iPhone reads/writes and
   network activity, free of symlink traversal, safe for a hostile plist,
   and free of raw identifier/URL disclosure?
2. Is the current `read_file` routine suitable for reading protected
   iPhone `.urls` files? It **moves** the source via AirTraffic and then
   writes it back; do not call this purely read-only. Audit every return,
   error, timeout and disconnect path, including crash/power loss.
3. Does `read_file` verify restored bytes, metadata, paths, cleanup and
   original Books state? If restoration fails, is recovery persisted and
   is any retry or next card prevented?
4. Recommend a safer way to establish whether the files exist *without*
   manipulating payment card files. No unrestricted file explorer, no
   broad on-device deletion or automatic website access.
5. If a safe future step is possible, design a **dry-run plan by default**
   with exact file allowlists, strict bound sizes, device and card
   identity gating, explicit user approval, privacy-safe local result,
   before/after byte verification, durable journal and an actually
   tested recovery procedure.
6. Explain why issuer artwork URLs might be expired, scoped, private or
   otherwise unsuitable for unauthenticated download. Never send full
   URL strings to a third-party reviewer or telemetry service.
7. For restoring original assets, require independent proof they are the
   correct issuer-provided versions. Preserve all existing cards,
   payment provisioning and unrelated Wallet contents.
8. Recommend an explicit **NO-GO** if iOS 27.0.1 operations cannot be
   shown reliably recoverable, or if the original assets are unavailable.

## Expected review output

An evidence-linked, file/line-specific safety audit and phased architecture.
Classify **GO / NO-GO** separately for:
- Mac-only diagnostic (safe to run after local compilation/testing);
- any protected iPhone file read;
- artwork URL retrieval;
- actual restored-artwork writes.

**Review only: do not push commits, modify `main`, deploy, or call private
on-device helpers on behalf of the user.**
