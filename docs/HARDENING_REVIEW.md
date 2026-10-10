# AirCard hardening review — 10 October 2026

Follow-up: [Final pre-Mac validation](PRE_MAC_VALIDATION.md) records the later runtime trace, recovery fix, build/signing changes, current test results and Mac verification script. The results below describe the original hardening review.


Repository: `dtoska1/AirCard`, branch `hardening`.
Audited baseline: `52ba05dca4bdc590672c19d554701f4438e20338`.
Implementation reviewed through `c66593ecb5c6ede54b059a27dc99c9a3607fd4f1`.

**Status: ready for macOS compilation and regression checks, not yet cleared for a real-device write.** The source changes are published, but this Linux workspace cannot compile SwiftUI/Objective-C against Apple's frameworks. No iPhone was attached or modified. Successful tests are not a guarantee of security or compatibility.

## Verified, corrected, newly found

| Finding | Assessment and action |
| --- | --- |
| Branch baseline and upstream | Fork main, hardening, and upstream main initially all matched `52ba05d`. No newer upstream main commits to import. Only this fork's hardening branch was updated. |
| Loose manual IDs | Verified. GUI accepted lengths 16–64 and stripped dots; backend interpolated identifiers into paths. Added shared Python grammar and Swift validation at entry points. |
| Identifier format | Retained the existing catalog grammar `[-A-Za-z0-9_+=]{20,64}`. Repository fixtures predominantly use 27 characters followed by `=` (28 total), not a universally verified 27-character ID. No real device identifiers were collected to establish new lengths. |
| Discovery formats | Dashboard, passIDs lists, old/new activation syntax and fallback extraction already existed. Preserved them; added validation and provenance handling instead of duplicating parsers. |
| Activation ambiguity | Verified first-match lookup. A unique distinct ID is now required within a matched catalog. Duplicates with different IDs remain unresolved. Live structured discovery remains available; explicit manual approval is the alternative. |
| Cache and fallback promotion | Verified that both could become ready targets without adequate provenance. Cache-only entries and generic fallback tokens are now unverified suggestions. Manual approval is available and visibly labelled. Current-session eligibility is checked when flashing, including saved rows. |
| Timeout | Verified blocking readline before the timeout. Replaced with monotonic deadlines, simultaneous stdout/stderr draining, terminate/kill/reap, final JSON without newline support, and bounded output. |
| Recovery | Newly verified skipped cleanup on exceptions and deletion of the recovered original after failed write-back. Added guaranteed write cleanup, conservative read recovery, retained snapshots on detected recovery failures, and stop-on-timeout behavior. Native `cleanupAuthorized=false` is respected so a rejected preflight does not restore over externally changed Books state. |
| AFC read | Only the read-recovery primitive calls it. Restricted to `airlift-recovered-` plus exactly 20 lowercase hex characters. |
| Native cleanup scope | Newly found missing generated-name validation in finish-write. Added matching-token and valid-snapshot checks before cleanup. |
| Device selection | Explicitly requesting a missing device previously selected another phone. Backend/CLI now fail that selection; GUI keeps available devices visible for deliberate selection. |
| Theme boundaries | Preserved passcode themes and generic primitives. Constrained TelephonyUI directory and language parameters, rejecting path injection. |
| CLI reporting | Invalid bulk-selection text previously defaulted to all cards; failed writes could still print complete success. Both corrected. Success copy now asks for visual confirmation in Wallet. |
| Runtime packaging | No executable download in Makefile/build.sh. Native helpers are compiled locally. Python itself is **not bundled**: GUI searches installed `/usr/bin/python3`, Homebrew, and `/usr/local/bin/python3`. The unconditional zero-prerequisites wording was misleading. |

A read-only upstream issue search found reports consistent with the risks: [#114, waiting for ReadyForSync](https://github.com/Mak5er/AirCard/issues/114) and [#168, cache-only IDs presented as live matches](https://github.com/Mak5er/AirCard/issues/168). These are reports, not independently reproduced hardware evidence. No issue, comment, PR or message was sent upstream.

## Network and payment-data assessment

The shipping Swift, Python, Objective-C/header sources and build scripts were searched for the requested networking, analytics, update, download and dynamic-execution patterns. Relevant matches were reviewed. No obvious silent Internet upload, telemetry client, remote-code download or updater was found. Existing GitHub/X/PayPal URLs are deliberate UI links. Native socket handling uses Apple's device-service connections; this is not evidence of an Internet upload.

`wallet_catalog.py` still reads the Mac Wallet archive for compatibility. It exports an explicit card-field allowlist: ID, display name, source and optional activation ID. Tests check that synthetic account identifiers, authentication tokens and account/CVV-like metadata fields do not escape into catalog output. Raw archive data necessarily exists temporarily inside its parser; this is not a claim that the process cannot read sensitive local data.

No PAN/CVV, payment-key, cryptogram, Secure Element or bank-login extraction functionality was added. Normal GUI logs redact long identifiers and withhold raw backend stderr/output. Full identifiers remain in necessary internal IPC, per-device local matching state and deliberate copy-ID functionality. Source-policy tests catch common networking additions; they are review tripwires, not an exhaustive proof against obfuscated code or a runtime network audit.

## Published implementation commits

| Commit | Change |
| --- | --- |
| `5ab759fc2063d7bd516356660b04ed4be1025b96` | Validate Wallet identifiers at GUI, backend and CLI boundaries |
| `ad08793d49615a270d2a34e3bc406d1bc4984362` | Separate live discovery from cache candidates and explicit manual overrides |
| `784d22b7d79a6634f56f0b6941af7f2c8e6c8530` | Enforce helper deadlines and restore Books on write failures |
| `7ff92cd4abf11addffd6dc82c3fb53a0d56e0153` | Limit AFC reads to exact generated recovery objects |
| `63a19181476b8a2fefb85651d93c35fb988941a8` | Preserve read recovery on exceptions and honor native cleanup authorization |
| `e60bd68cb679fbf0af90a0cd850cde2a561134ae` | Redact diagnostics, prevent device substitution and constrain theme targets |
| `c66593ecb5c6ede54b059a27dc99c9a3607fd4f1` | Report CLI failures honestly and reject invalid bulk selections |

The final documentation commit adds this report and corrects the runtime requirements. Its hash is available in branch history. Published Git blob/tree hashes were compared with the locally tested versions. No main merge or force push was performed.

## Exact changed files

Implementation:

- `AirCardApp.swift`
- `Sources/WalletDiscovery.swift`
- `Sources/WalletDiagnosticsView.swift`
- `Sources/device_helper.m`
- `aircard.py`
- `aircard_backend.py`
- `apply_card_skin.py`
- `wallet_catalog.py`
- `wallet_identity.py` (new)
- `build.sh`

Tests:

- `tests/test_afc_read_scope.py` (new)
- `tests/test_backend_passthm.py`
- `tests/test_card_flash.py`
- `tests/test_cli_failures.py` (new)
- `tests/test_device_selection.py`
- `tests/test_read_file.py`
- `tests/test_source_policy.py` (new)
- `tests/test_subprocess_timeout.py` (new)
- `tests/test_wallet_catalog.py`
- `tests/test_wallet_discovery.swift`
- `tests/test_wallet_identity.py` (new)
- `tests/test_wallet_viewmodel.swift`

Documentation:

- `README.md`
- `docs/guides/README.en.md`
- `docs/HARDENING_REVIEW.md` (new)

## Tests and build results

`python3 -m unittest discover -s tests -v`: **62 tests discovered, 55 passed, 7 skipped, zero failures**, on Linux. Relevant tests were rerun between meaningful changes.

Coverage includes malformed and valid manual IDs, backend rejection before writes, artwork batch/fallback flow, cache invalidation, explicit device selection, Wallet metadata filtering, read recovery, timeout cleanup, callback exceptions, no-newline output, stderr backpressure, native preflight cleanup authorization, networking tripwires and CLI failure reporting. A silent child, a partial-line child and a child ignoring SIGTERM were each given a 0.15-second deadline; tests require each to finish in less than 2.5 seconds including termination grace.

The existing passcode-theme script depended on files in the upstream author's Downloads folder and was not discovered by unittest. It now uses synthetic ten-key ZIP fixtures and exposes its eight checks to unittest. Batch and fallback behavior remain covered. No real user card IDs, credentials or device logs were introduced in new fixtures.

Three baseline card-flash tests failed on Linux because `/usr/bin/sips` is absent. Tests now substitute only that OS image-conversion command on Linux; the real asset assembly/flash logic still executes. On macOS the actual sips integration is retained. Passing Linux tests therefore do not verify actual PDF conversion.

Seven skipped checks require macOS: native activity-stream protocol, resource-path scanner integration, native discovery options, Swift model/parser tests, Swift view-model tests, SwiftUI binding safety, and the new native recovery-name validator. Swift regression additions cover duplicate activation IDs, manual eligibility, malformed IDs, provenance, clear/relaunch behavior and identifier redaction, but were **not compiled here**.

`python3 -m compileall -q aircard.py aircard_backend.py apply_card_skin.py card_assets.py wallet_catalog.py wallet_identity.py`: passed.

`bash -n build.sh`: passed. `git diff --check`: passed.

`bash build.sh`: **blocked at the first native compile**. `make` reported `xcrun: No such file or directory` and exited 2. No app, DMG, signature validation, notarization, Intel/ARM compilation or GUI visual test is claimed.

Makefile still builds both native helpers from source and ad-hoc signs them. build.sh retains the ad-hoc default and inside-out Developer ID signing option. No SIP changes, profiles, extensions, daemons, launch agents, runtime downloads or updater were introduced.

## Remaining limitations and first-device gate

- Apple private frameworks and the AirLift mechanism remain essential. Static review and mocked tests cannot prove exploit compatibility, correct artwork rendering, exact card identity, cache behavior or restoration after disconnects. Documentation's iOS compatibility ranges are claims; the native tested-build table covers fewer builds. Untested builds remain allowed and are labelled accordingly.
- A syntactically valid manual ID is not proof that it belongs to the selected phone/card. Mac metadata can be stale, including a unique same-model cache. Live evidence and on-phone visual checking are still necessary.
- The low-level write/read primitives remain generic for legitimate features. High-level Wallet and theme boundaries are constrained; this is not a sandbox for arbitrary code running as the same macOS user.
- GUI saved-card and flashed-skin records remain per-device. Clear All removes current-device rows, current-session eligibility and flashed-skin records. The legacy CLI JSON store remains global and is not encrypted; treat its entries as manually selected IDs, not verified current-device inventory. Legacy files are still supported for migration.
- Detected cleanup failures retain private Books snapshots under `~/.aircard-recovery`. Failed read recovery preserves phone-side recovery data. Manual inspection/recovery may be needed; no recovery UI was added. Forced app termination, host power loss or a disconnected phone can still prevent restoration. Do not retry a write automatically after a recovery error.
- Theme ZIP size limits, all possible local-file races, all native helper internals and Swift subprocess lifecycles were not comprehensively hardened. The GUI changes need compilation and visual review before device use.
- No real iPhone detection, artwork transfer, Books restoration or Apple Pay transaction was tested.

On a Mac checkout of `hardening`, run:

```sh
python3 -m unittest discover -s tests -v
bash build.sh
```

All macOS regression tests and the source build must pass before the first controlled write. Review any build or test failure rather than bypassing it.

Before device testing, collect only: iPhone model, exact iOS version/build, Mac model/chip and macOS version. No serial number, UDID, full card ID, card number, CVV or bank login is needed in chat.

Then use USB with the iPhone unlocked and trusted, one clearly identified card and one test image. Verify detection, target identification, artwork transfer, cache invalidation, Books restoration and the intended card's new art in Wallet. Confirm ordinary Apple Pay behavior on the device without extracting or sharing credentials. Mac Internet access can be disabled for this USB test if that does not disrupt the required Apple device service.
