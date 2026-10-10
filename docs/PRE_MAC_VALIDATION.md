# AirCard: final pre-Mac validation

Review date: 2026-10-10. Repository: **dtoska1/AirCard**, branch **hardening**. Baseline: `52ba05dca4bdc590672c19d554701f4438e20338`. Fetched starting HEAD: `2d6d27dec43e94ecb5348d518d1da14b25ba3606`. This is a focused runtime/build review, not a second broad security audit.

**The normal GUI skinning mechanism remains intact. Use a local ad-hoc build for the first personal test. Mac compilation, signatures, launch and actual USB functionality remain unverified here.** No iPhone was connected or modified. No upstream issue, PR or comment was created, and main was not merged or changed.

## Seven decisions

| Question | Verdict | Basis and limit |
| --- | --- | --- |
| 1. Static functionality | **READY** for Mac validation | The same three artwork assets, protected pass destination, AirLift staging, AirTraffic sequence, two cache directories and Books restoration remain. Native success is not proof of on-phone rendering. |
| 2. Hardening regression | **READY**, within the documented ID grammar | No confirmed blocker for the normal GUI flow with a valid 20–64-character ID. A CLI recovery-exception propagation bug was fixed. Longer Dashboard IDs remain an unverified compatibility edge; see below. Swift changes still need compilation. |
| 3. Build coherence | **READY** for a Mac build attempt | Preflight, bundled modules, architecture targets and explicit inside-out signing are coherent by inspection. A successful native build is **UNKNOWN** until the Mac gates pass. |
| 4. Local Gatekeeper behavior | **READY WITH EXPECTED WARNING** | Normally no download warning for a fresh local build without quarantine. Explicit `spctl` assessment may reject ad-hoc code. Actual launch policy, managed-Mac controls and attributes must be checked. |
| 5. Malware classification | **BLOCKED / UNKNOWN** as a runtime prediction | No substantiated evidence found that XProtect identifies this source-built hardening version as malware. This is not a malware clearance or proof of future acceptance. |
| 6. First-test signing choice | **READY — A: default ad-hoc** | Matches local-development needs and upstream default without adding a new runtime policy variable. Developer ID/notarization is useful for distribution; it is not needed merely to attempt this personal build. |
| 7. First controlled USB test | **READY only after all Mac gates pass** | Until then, **BLOCKED**. Use one identified card and image, verify Books restoration and actual Wallet appearance; stop on uncertain recovery. No hardware success is claimed. |

## Changes made during this validation

| Published commit | Change | Regression evidence |
| --- | --- | --- |
| `e3332ea3f130b8771c8c459634082fcb5cf39b32` | Propagate `AirliftOperationError` out of CLI cache invalidation; replace GUI's unconditional retry advice with a recovery stop instruction | Fatal cleanup failure now calls only the first cache directory; ordinary failure still checks both. This closes a gap in the earlier hardening, rather than changing successful writes. |
| `9a4b2abb7ad68eac5bec8a058844ab8f6736f108` | Check Mac/toolchain/Python before cleaning/building; probe bundled imports; explicitly sign and verify each helper then app in both signing modes; preserve extended attributes | Portable tests exercise broken-first-Python selection, missing bundled module rejection, no bytecode writes, signing order/options and helper verification failure. These mock signing commands; they do not validate an Apple signature. |

Documentation and `scripts/verify_mac.sh` are in the subsequent documentation/checklist commit. GitHub blob/tree hashes were checked against the locally tested content. The build change does not install software, add entitlements, disable security settings or change device-service calls.

## A. Complete GUI execution path

Source anchors are `AirCardApp.swift`, `Sources/WalletDiscovery.swift`, `aircard_backend.py`, `card_assets.py`, `apply_card_skin.py`, `Sources/device_helper.m`, and `Sources/airtraffic_host.m`.

In the commands below, `D` is the deliberately selected device UDID, `I` the validated pass ID, `S/L/R` the generated source/link/recovery names with one shared random token, and `SNAP` a private temporary Books snapshot directory. These placeholders are explanatory, not commands to paste.

| Stage | Input and validation | Command/action | Success / failure and cleanup |
| --- | --- | --- | --- |
| Select phone and card | GUI device choice; IDs use `[-A-Za-z0-9_+=]{20,64}` with full-string matching | Discovery/probe through `aircard_backend.py --devices` and native helper; scan runs `device_helper syslog D` | A missing explicitly selected device is not replaced by another. Discovery/probe success does not prove an exploit write. Scanner uses the selected process/UDID and rejects events after that process is replaced. |
| Establish eligibility | Live structured ID, unique activation-to-matched-cache mapping, or explicit session manual approval | `recordScannedCard`, `recordActivatedPaymentCard`, `approveManualCard` | Saved/cache-only/fallback candidates remain visible but cannot write automatically. ID syntax is rechecked in backend. |
| Select artwork / Flash Skins | Selected rows with artwork; **all requested rows must be eligible** | `applySkin()` snapshots selected cards and UDID. Changed skins are selected first; if none changed, all selected skinned cards are reflashed | Any unverified requested row blocks the bulk action rather than silently skipping it. Successful per-device skin signatures avoid unnecessary repeat writes. |
| Prepare PNG | Local image URL; Swift `NSImage` decode | Swift rasterization to 1536×969 in a fresh per-card temporary directory; fallback `python aircard_backend.py --prepare-image INPUT OUTPUT` | Nonempty output required. Failure skips that card and makes the run fail. Temporary directory is removed on scope exit. Python fallback tries Pillow if installed, otherwise `sips`; Pillow is not required. |
| Start backend | `D`, `I`, prepared PNG path; valid ID and existing image | Selected Python runs `aircard_backend.py --flash D I PNG` from the resource directory | Import/launch/argument/preparation failure is nonzero or false; GUI stops the card loop on backend nonzero exit. stderr is drained but withheld from normal logs. |
| Generate assets | PNG bytes | `build_card_assets`; `/usr/bin/sips -s format pdf INPUT --out OUTPUT` | Same PNG bytes go to `cardBackgroundCombined@3x.png` and `cardBackgroundCombined@2x.png`; PDF to `cardBackgroundCombined.pdf`. Conversion failure aborts before device writes. Asset temporary directory is cleaned. |
| Construct batch | Validated `/var/mobile/Library/Passes/Cards/I.pkpass`, three `(leaf, bytes)` pairs | `build_archive_multi` retains nested symlink and companion payload layout; `build_books` lists relocated link then payload identifiers | Local archive/Books plist and random generated paths are created. This preserves the exploit's relative identifiers; validation does not strip them. |
| Snapshot Books | New empty `SNAP`; selected phone, paired session/AFC and native target gate | `device_helper snapshot-books D SNAP` | Python requires exit 0, `targetGatePassed`, `operation.ok`. Native captures tracked Books files/existence and directory preimage with size/type limits. Failure prevents staging. Snapshot/restore scope is tracked Books metadata, not an entire Books library backup. |
| Stage AirLift | Archive, generated plist, `SNAP`, matching S/L/R tokens | `device_helper stage D S L R ZIP PLIST SNAP`; starts `com.apple.streaming_zip_conduit`, sends `MediaSubdir=S` and ZIP, writes `Books/Sync/Books.plist` through AFC | Checks readable inputs, fresh generated paths and unchanged Books preimage before mutation. Preflight rejection reports `cleanupAuthorized=false`: no restoration over someone else's changed state. Partial stage/error otherwise enters cleanup. Service response status is diagnostic; source objects and Books write are part of the actual success predicate, unchanged from baseline. |
| AirTraffic transfer | Generated link identifier then each payload identifier/destination pair | `airtraffic_host D ID DEST [ID DEST ...]` | Same `AirTrafficHost.framework` calls: connection → `SyncAllowed` → host info/Book sync request → `ReadyForSync` → metadata finished → `AssetManifest` checks → link and payload completion messages. Nonzero codes 2–5 indicate connection/handshake/manifest failure; native alarm exits 124. Progress reports payload sends. |
| Finish artwork batch | AirTraffic result plus generated names/snapshot | `device_helper finish-write D S L R SNAP` in `staged_write`'s `finally` | Removes generated link/recovery/tree, restores tracked Books preimage and verifies cleanup. Only then does Python return AirTraffic exit-0/`ok` success. No post-write artwork readback exists: helper success means protocol completion, not a verified screenshot or byte-for-byte pass readback. |
| Single-file fallback | Ordinary batch false result | `write_file` repeats snapshot/stage/AirTraffic/finish for each of the same three assets | Preserved. Each operation can retry ordinary failures up to three times, after its cleanup. Fatal timeout/restoration exception bypasses this fallback and stops the backend. |
| Invalidate both caches | `I.cache`, then `I.pkcache`; leaves `FrontFace`, `PlaceHolder`, `Preview` | `remove_files` → batch AirLift link relocation and protected-leaf move to `S/removed-N` → `device_helper finish-moved-removal D S L R SNAP COUNT` | Same real move/unlink technique, not corrupt-byte overwriting. Native deletes generated staging and restores Books. Missing moved objects are treated as already absent, as upstream. Ordinary failed batch can fall back to individual leaves; any successful individual removal makes that wrapper true, also upstream behavior. This is not a rigorous per-leaf absence proof. |
| Error/recovery boundary | Any helper operation | Native helper deadline 60 seconds; AirTraffic deadline `max(120, files×2)` for batch, 120 for single/cache | Both output streams are drained without blocking on newlines. Timed-out child is terminated/killed/reaped before cleanup. Cleanup uncertainty retains `~/.aircard-recovery/<token>` and raises fatal error; GUI stops subsequent cards. No transaction rolls back already written artwork. |
| Finish / Wallet refresh | Backend all-assets/all-cache result | Backend exits 0 only when `cmd_flash` returns true. GUI marks that card's skin and asks for on-phone verification | Nonzero is not marked flashed. Success does not automatically restart Wallet. Force-close/reopen Wallet to inspect the intended card; reboot only if needed after completed recovery. |

Books restoration happens **after each batch/single/cache operation**, not just once at the end. All upstream operations needed for a normal GUI skin remain reachable. The native AirTraffic implementation, PNG/PDF asset generation and snapshot/restore implementation are unchanged from baseline; the native hardening diff concerns recovery-name/cleanup authorization boundaries.

## B. Behavior comparison against 52ba05d

| Behavior | Classification | Consequence / investigation |
| --- | --- | --- |
| Structured pass/cache/path/writing/selected-ID patterns | **INTENTIONALLY HARDENED BUT FUNCTIONALLY PRESERVED** | Same valid IDs; full validation and token boundary reject path fragments or truncated overlong tokens. |
| `passIDs[InSession]`, every ID in a list | **SAME AS UPSTREAM** | Order/deduplication and all matches remain, including a twelve-card fixture. |
| `passIDs[global]` | **SAME AS UPSTREAM** | Preserved following upstream hotfix history and issue #109; see C. |
| Dashboard IDs up to 64 characters | **INTENTIONALLY HARDENED BUT FUNCTIONALLY PRESERVED** | Both `for ID,` and `ID -` formats remain. |
| Dashboard IDs of 65–80 characters | **POSSIBLE REGRESSION** | Upstream Dashboard regex permits 80; hardening's common validator caps 64. Prior handoff explicitly prescribed the 20–64 grammar. Issue #102 redacts example IDs and supplies no evidence of a real >64 ID; current fixtures are shorter. Do not claim universal compatibility or widen the boundary on a guess. A genuine non-sensitive length/format reproduction is needed if such a card fails. |
| Old/JSON activation parsing | **SAME AS UPSTREAM** | Both formats retained; activation AID is not itself a pass ID. |
| Activation mapping / duplicate AIDs | **INTENTIONALLY HARDENED BUT FUNCTIONALLY PRESERVED** | One distinct pass in a matched cache can map; shared AID across distinct cached cards no longer picks the first. A live pass ID or explicit manual approval remains available. A stale/incomplete unique cache can still be wrong. |
| Mac cache matching | **SAME AS UPSTREAM** for matching; **INTENTIONALLY HARDENED BUT FUNCTIONALLY PRESERVED** for eligibility | Model/overlap matching and unique same-model bootstrap remain. One overlap no longer makes every cached card writable automatically. |
| Fallback bare identifiers | **INTENTIONALLY HARDENED BUT FUNCTIONALLY PRESERVED** | Valid candidates remain visible; manual approval required. Slash-containing base64 cannot be a safe single directory component and is rejected. |
| Manual IDs | **INTENTIONALLY HARDENED BUT FUNCTIONALLY PRESERVED** | Explicit approval enables valid IDs for this session. Invalid paths/short/overlong strings cannot reach the writer. |
| Previously saved rows | **INTENTIONALLY HARDENED BUT FUNCTIONALLY PRESERVED** | Rows/artwork retained per device, but saved confirmation does not substitute for current eligibility. Rescan or approve; clearing resets current-device flash history. CLI's legacy store remains global/manual. |
| Multiple cards / changed-skin selection | **INTENTIONALLY HARDENED BUT FUNCTIONALLY PRESERVED** | Valid selected cards use the same sequential flow. Unverified selections are rejected together; backend failure stops later cards. |
| PNG/PDF and exact artwork leaf names | **SAME AS UPSTREAM** | Two PNG names plus PDF, same `sips` conversion. Standalone CLI historically writes two PNGs rather than the GUI's three assets; this review did not unify it. |
| Batch and ordinary single-file fallback | **SAME AS UPSTREAM** on success/ordinary failure | Same archive layout, link relocation, targets, assets and fallback. |
| `.cache`/`.pkcache` and three leaf removals | **SAME AS UPSTREAM** on normal flow | Same two directories and move-based invalidation. Inherited missing-file/partial fallback success semantics limit confidence. |
| Books snapshot/preimage/restore | **INTENTIONALLY HARDENED BUT FUNCTIONALLY PRESERVED** | Successful lifecycle unchanged. Exceptions now invoke cleanup; native no-mutation rejection is honored; invalid generated cleanup names rejected. |
| AirTraffic timeout / retry | **INTENTIONALLY HARDENED BUT FUNCTIONALLY PRESERVED**, with a timing limit | Non-streaming paths already requested 120 seconds. Streaming had a blocking-read loophole that could wait for the native 300-second alarm. Hardening enforces the intended 120-second GUI card deadline and stops rather than retrying timeout uncertainty. A legitimate unusually slow sync could now fail earlier; no evidence establishes it is needed for a normal USB card write. |
| Read recovery and AFC scope | **INTENTIONALLY HARDENED BUT FUNCTIONALLY PRESERVED** | Recovered original is retained when write-back is uncertain; arbitrary AFC reads disallowed. `read_file` is not in the GUI flash path. It can return captured bytes despite restoration failure, so bytes must never be treated as recovery success. |
| CLI fatal cache error catch | **CONFIRMED REGRESSION / FIXED** | Earlier hardening introduced a fatal error class but the outer cache catch swallowed it. Now it propagates and stops before the next cache/card. |
| Runtime packaging/signing | **INTENTIONALLY HARDENED BUT FUNCTIONALLY PRESERVED** | wallet_identity is bundled; no bytecode writes in normal GUI launches; preflight/sign verification now fail early rather than shipping a known-broken local build. |

## C. What `global` establishes—and what it does not

Upstream commits `42eaec2` and `6c1f040` added/refined in-session detection; `1e281a462e84ebedfc92cff27e1b7b0d192e89cb` broadened it to global lists and Dashboard formats. Current Swift parser tests deliberately accept both, including a global-only line. Tests establish parser behavior, not Apple's log contract.

[Upstream #109](https://github.com/Mak5er/AirCard/issues/109) reports nfcd `NFExpressModeManager` global pass IDs on one iOS 27 setup while the in-session field was null during browsing. The report associates the visible IDs with Express-capable cards. This is empirical user evidence, not an Apple guarantee of lifetime, completeness or selected-card identity. [#102](https://github.com/Mak5er/AirCard/issues/102) supports retaining Dashboard parsing for cards absent from the other formats.

The names suggest session state versus broader manager state, but no authoritative public definition or raw capture was available to prove exact semantics. **There is no evidence here that “global” means all iCloud phones or arbitrary Mac cache entries.** It is observed in the selected phone's live log stream. Conversely, neither list proves which card the user currently intends to change, and historical/stale manager state cannot be ruled out.

**Recommendation: retain global-only IDs as live observed, flash-eligible IDs, with deliberate per-card selection/artwork and on-phone identity verification.** Do not demote all global IDs merely because the field is called global: it would remove a documented detection route. This is a compatibility judgment backed by upstream evidence, not cryptographic proof of current pass existence. Neither a global ID nor one overlapping cache ID should promote the entire Mac catalog. The branch already avoids that catalog-wide promotion. Cache names are advisory; do not bulk-assign artwork to unidentified rows.

## D. Host, compiler and Python requirements

Deployment target and generated `Info.plist` both specify **macOS 14.0**. Makefile compiles each helper with `-arch arm64 -arch x86_64 -mmacosx-version-min=14.0`; Swift is compiled separately for both `*-apple-macosx14.0` targets then combined with `lipo`. Either host architecture can cross-build both if its SDK/linker/private-framework inputs support them. This is an intended universal build, not proof that both architectures execute successfully.

Required: compatible selected Apple developer tools, `xcrun`, `clang`, `swiftc`, macOS SDK/SwiftUI, `make`, `xcode-select`, `lipo`, `codesign`, `otool`, `hdiutil`, `sips`, and Python 3.9+ with its standard library. `create-dmg` only styles packaging; without it, `hdiutil` creates the DMG. Nothing is downloaded by the build. Private frameworks are linked from the host system paths in Makefile; public SDK installation alone cannot promise those private symbols/link inputs exist on every OS.

Full Xcode is the recommended first environment, with first-launch components completed and its developer directory selected. CLT can provide compilers and an SDK, but not every compiler/SDK combination is interchangeable. The build retains the upstream CLT `MacOSX26.sdk` preference when present; `SWIFT_SDK` can explicitly select a matching SDK. macOS 14 is a deployment minimum, not a tested claim that every old CLT can compile this current Swift source. There is no evidence justifying an invented exact minimum Xcode version; the native build and seven Mac-only tests decide compatibility. See [Apple's CLT documentation](https://developer.apple.com/documentation/xcode/installing-the-command-line-tools).

Python is **not bundled**. GUI selection is the first executable at `/usr/bin/python3`, `/opt/homebrew/bin/python3`, `/usr/local/bin/python3`; an executable shim can win over a working later interpreter. A clean Mac is not guaranteed a usable interpreter just because that pathname exists. Without working selected developer tools the shim can request their installation or exit with a developer-tools error, leaving the GUI unable to run its backend. Exact dialog text depends on macOS/setup. [CPython's macOS documentation](https://docs.python.org/3.13/using/mac.html) describes Apple's path as developer-tools Python, not a general runtime guarantee.

New preflight executes the same first-selected interpreter, checks Python >=3.9 and imports every application module. It deliberately fails rather than silently validating a later interpreter the GUI would not choose. It repeats the import check against bundle Resources using isolated mode so the source checkout cannot hide a missing bundled file. This validates the build Mac, not another recipient's Mac or a later removed runtime. Repair/select the developer tools or selected Python installation manually; no Homebrew/network installation is performed.

## E. Signatures and hardened runtime

| Object | Default `-` | Developer ID mode |
| --- | --- | --- |
| Makefile's two helper outputs | Ad-hoc | Initially ad-hoc, then explicitly re-signed in bundle |
| Bundled device_helper / airtraffic_host | Each explicitly ad-hoc signed and strictly verified | Each identity-signed with runtime + timestamp, then strictly verified |
| GUI Mach-O and enclosing app | App signing signs main executable and seals resources; deep/strict verification | Same, with identity/runtime/timestamp |
| DMG | Unsigned container holding signed app | Separately identity-signed with timestamp |
| Notarization | Not eligible with ad-hoc identity | Separate manual submit/staple step; signing alone is not notarization |

Previously default app signing used `--deep --sign -`; helper signatures already came from Makefile, so there is **no demonstrated broken-signature regression** from that command alone. But deep signing is not a reliable way to manage nonstandard nested helpers, and can replace options on nested code it does find. Resources/bin is resource-sealed rather than a conventional nested-code location. Apple recommends signing inside out; new code explicitly signs/verifies both helpers and reserves `--deep` for verification. Changing a helper afterward would invalidate the enclosing resource seal. The former comment claiming deep walks *only* Frameworks and PlugIns was inaccurate. [Apple signing guidance](https://developer.apple.com/library/archive/documentation/Security/Conceptual/CodeSigningGuide/Procedures/Procedures.html), [TN2206](https://developer.apple.com/library/archive/technotes/tn2206/).

Ad-hoc signing supplies a local integrity signature without developer identity or notarization trust. No source entitlement or signature requirement was found demanding Developer ID merely to call these private frameworks. It cannot guarantee that a given OS still exports/allows their APIs or that phone services accept the workflow.

Hardened runtime is **not App Sandbox** and does not generally prohibit launching Python/subprocesses. Framework library validation allows Apple-signed libraries, so MobileDevice/AirTrafficHost are not categorically excluded because they are private. Runtime policy can restrict DYLD variables/injection. Here `Resources/lib` is empty and linkage uses system frameworks; the core flow does not rely on loading a custom dylib through `DYLD_LIBRARY_PATH`. No evidence shows that enabling runtime itself breaks this checked-in USB flow, but no signed native run was performed. Do not add library-validation/DYLD exceptions without an observed need. A third-party interposition workaround, such as that discussed for Wi-Fi in upstream #62, is a different configuration and is not part of this branch. [Library validation](https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.security.cs.disable-library-validation?language=objc), [DYLD policy](https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.security.cs.allow-dyld-environment-variables).

For a first personal test choose **ad-hoc** to keep the default runtime behavior. Developer ID + runtime + notarization should be separately validated if distributing. Notarization checks the submitted build; no acceptance is promised. [Apple notarization requirements](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution).

## F–H. Gatekeeper, quarantine and malware evidence

| Case | Likely behavior / meaning |
| --- | --- |
| Valid Developer ID + notarized | Ordinarily accepted, subject to intact signature, trust/revocation and current policy; a downloaded-app confirmation may still appear. |
| Valid Developer ID, not notarized | Quarantined distribution may be blocked because Apple cannot check it; identity signing alone is insufficient for normal distribution approval. |
| Fresh local ad-hoc build | Normally runs without a download warning if not quarantined and signature is valid. Explicit policy assessment can reject it despite local execution being possible. |
| Browser-downloaded ad-hoc DMG/app | Download provenance/quarantine normally triggers unidentified-developer or cannot-check wording. This is not automatically malware detection. |
| Unsigned / broken signature | Unsigned code lacks identity/integrity guarantees; broken signed bundles may produce damaged/cannot-open errors or execution denial. Diagnose and rebuild; do not erase metadata to “repair” signatures. |
| Actual known-malware/XProtect block | Separate detection requiring investigation. Stop; capture exact alert/detection details. Developer ID or notarization does not override malware revocation/detection. |

Wording and override availability vary with macOS and management policy. For an inspected build blocked **only** on developer/notarization trust, Apple's per-app **Privacy & Security → Open Anyway** flow, when offered, is distinct from globally disabling protection. This report does not recommend overriding a malware alert. [Apple launch warning guidance](https://support.apple.com/en-us/102445).

A normal command-line git clone followed by local compilation does not ordinarily attach browser download quarantine to the new app/DMG. This is an expectation, not a filesystem guarantee: source acquisition, copied assets and local tooling can affect attributes. Browser downloads ordinarily carry quarantine and that provenance can affect contained apps. Inspect both artifacts with `xattr`; do not infer their state from how you intended to build. [Gatekeeper platform guidance](https://support.apple.com/guide/security/gatekeeper-and-runtime-protection-sec5599b66df/web).

Old `xattr -cr "$APP_DIR"` meant **clear all extended attributes recursively**, not just quarantine. It could remove provenance, Finder/resource-fork metadata and information useful for diagnosis. It is not normally needed on this fresh build and was removed. If signing reports disallowed resource-fork/Finder metadata, inspect the named file and regenerate a clean input; do not blanket-delete attributes. The README no longer recommends recursive attribute stripping. No global Gatekeeper, SIP or XProtect change is needed.

Private Apple frameworks and device services are unusual, but their use alone is not evidence of a Gatekeeper/XProtect block. Gatekeeper distribution trust and code integrity, notarization analysis and malware signatures/behavior are different mechanisms. No Apple rule or tested result was found proving this exact build would be rejected merely for MobileDevice, AirTrafficHost, os_trace_relay, AFC or streaming_zip_conduit use. The exploit-like behavior might attract a third-party heuristic, but likelihood and classification are unknown without a named product and actual detection evidence. No disguising, evasion or exclusions are proposed. Apple's XProtect documentation describes both known-malware signatures and behavioral defenses; lack of download quarantine is not a blanket exemption from malware checks. [Apple malware protection](https://support.apple.com/guide/security/protecting-against-malware-sec469d47bd8/web).

Read-only upstream issue inspection:

| Report | Actual evidence reviewed | Classification |
| --- | --- | --- |
| [#94](https://github.com/Mak5er/AirCard/issues/94) | Title says malware; no body/alert/detection details. Maintainer suggests allowing in settings. | **UNKNOWN**. Suggestion is consistent with a trust warning, but does not prove what the alert was. |
| [#99](https://github.com/Mak5er/AirCard/issues/99), [#120](https://github.com/Mak5er/AirCard/issues/120) | Quoted AirCard “could not run its device tools” text; maintainer explains developer-tool diagnostics. | Application/backend launch failure, not evidence of an OS malware detection. Exact underlying failure varies. |
| [#137](https://github.com/Mak5er/AirCard/issues/137) | Same in-app tool error after settings approval; two comments report success after Xcode component setup. | Supports a toolchain/runtime explanation for those users, not proof of malware or a universal cure. |
| [#62](https://github.com/Mak5er/AirCard/issues/62) | Reported Wi-Fi initial SyncAllowed stall and an experimental discovery interposition workaround. | Device handshake limitation; not signing or malware evidence. Supports starting with USB. |

These reports concern upstream release environments, not a compiled copy of this hardening HEAD. There is no basis to label this build malware, or certify it malware-free, from them.

## I–K. Exact Mac verification and bundle integrity

Run from your `hardening` checkout with **no device test in progress**:

```sh
git status --short --branch
git rev-parse HEAD
python3 -m unittest discover -s tests -v
bash build.sh
bash scripts/verify_mac.sh
```

All tests must pass on Mac, including the seven skipped here. If choosing a specific SDK, use a compiler-compatible SDK and check the test command output: some older test wrappers have their own CLT SDK preference. Do not interpret a compiler/SDK mismatch as a device failure or waive a test without diagnosis.

The verification script performs these requested checks, explicitly checks both helper signatures, verifies both slices' minimum deployment version, imports packaged modules, runs real `sips` on a synthetic PNG, and starts helpers with **no arguments**. Both main functions return usage code 64 before discovery/session calls. It never starts the GUI, lists/probes a phone or invokes AirLift. Helper loading tests only the host's native architecture; the other architecture is inspected, not executed.

Core equivalent commands:

```sh
codesign --verify --deep --strict --verbose=4 build/AirCard.app
codesign -dv --verbose=4 build/AirCard.app
codesign -dv --verbose=4 build/AirCard.app/Contents/MacOS/AirCard
codesign --verify --strict --verbose=4 build/AirCard.app/Contents/Resources/bin/device_helper
codesign --verify --strict --verbose=4 build/AirCard.app/Contents/Resources/bin/airtraffic_host
codesign -dv --verbose=4 build/AirCard.app/Contents/Resources/bin/device_helper
codesign -dv --verbose=4 build/AirCard.app/Contents/Resources/bin/airtraffic_host
spctl --assess --type execute --verbose=4 build/AirCard.app
xattr -l build/AirCard.app
xattr -lr build/AirCard.app
xattr -l build/AirCard.dmg
file build/AirCard.app/Contents/MacOS/AirCard
lipo -info build/AirCard.app/Contents/MacOS/AirCard
otool -L build/AirCard.app/Contents/Resources/bin/device_helper
otool -L build/AirCard.app/Contents/Resources/bin/airtraffic_host
hdiutil verify build/AirCard.dmg
```

Expected: strict signature checks exit 0 in both modes. Ad-hoc metadata contains `Signature=adhoc`, no Developer ID authority/team; DMG unsigned is expected. Developer ID app/helpers show the chosen authority/team, runtime flag and timestamp; DMG has identity/timestamp but is not an executable needing runtime. Before notarization, `spctl` can still reject Developer ID code. After successful notarization/stapling and intact distribution, acceptance is expected subject to current policy. A nonzero `spctl` is recorded separately by the script; it is not by itself malware evidence or a reason to ignore a broken signature.

`file`/`lipo` should show arm64 and x86_64 for **all three** binaries. The two helpers should reference their respective Apple private frameworks plus expected system dependencies. Missing-library/symbol/architecture failures must be resolved before any phone operation. The old build-time `otool` check looks at only the first `minos`; the verification script covers both slices and refuses missing/unexpected minima.

Bundled modules are `aircard_backend.py`, `aircard.py`, `apply_card_skin.py`, `card_assets.py`, `wallet_catalog.py`, **`wallet_identity.py`**. Their other required imports are standard-library modules. Pillow is optional in image fallback. Build support and verification shell scripts are build/inspection tools, not GUI runtime imports. Both helpers are copied and executable-checked. Bundle Resources is selected before checkout/current-directory fallback, and Python runs with that working directory; helpers resolve relative to their module's own Resources path. This supports an installation at `/Applications/AirCard.app` independently of shell cwd.

Every GUI backend/catalog Python `Process` receives `PYTHONDONTWRITEBYTECODE=1`; Python children inherit it. This prevents normal import-generated `__pycache__` additions inside the sealed bundle. It does not protect against explicit `compileall`, resource edits or unrelated writes. The new smoke test copies just bundled modules and verifies no bytecode directories appear. Temporary artwork/PDF/snapshots live outside the app.

After copying through Finder into Applications, inspect that installed copy:

```sh
bash scripts/verify_mac.sh /Applications/AirCard.app
```

Then, with no iPhone connected or reachable for automatic discovery, manually launch the app and confirm UI startup, absence of tool/Python errors, and intact signature afterward. The GUI starts discovery on launch, so it is intentionally not launched by the verification script. The GUI resource-path/launch test cannot be substituted by import tests. No `/Applications` installation or GUI launch was performed here.

Observed in this Linux environment: **68 tests, 61 passed, 7 skipped, zero failures**. Python compile checks, shell syntax and whitespace checks pass. `bash build.sh` now exits at the explicit macOS preflight; it does not compile native code. No app/DMG, real Apple signatures, notarization, native helper loading or real `sips` conversion was validated here. Portable signing tests are command-contract tests only.

## L. First-launch / first-test failure matrix

| Scenario | Visible symptom | Likely cause | Safe next action |
| --- | --- | --- | --- |
| App launches normally | UI appears; no tool error | Host launch prerequisites work | Finish signature/import/helper checks before planning USB testing. Launch alone proves no skinning capability. |
| Gatekeeper block | Cannot verify developer / cannot check app | Quarantine/distribution trust or management policy | Inspect exact alert, provenance and signatures. Use per-app Open Anyway only for a reviewed trust-only warning if offered. |
| Python missing/unusable | Developer Tools prompt, backend fails/no device results | GUI-selected shim/runtime cannot execute/import | Run build preflight/import check; repair selected developer tools/Python, rebuild. |
| Helper signature invalid | Strict verification fails, process killed/cannot execute | Modified or incompletely signed helper | Rebuild from reviewed source and reverify helpers plus app. Do not re-sign an unexplained downloaded binary just to bypass the failure. |
| MobileDevice fails to load | dyld missing framework/symbol or wrong architecture | Host framework/toolchain incompatibility | Run no-argument helper check and inspect `otool -L`, architecture, OS and Xcode setup. No phone writes. |
| AirTrafficHost fails to load | Same loader failure for airtraffic_host | Missing/private ABI mismatch | Same host checks; signing cannot supply missing symbols. |
| Phone not trusted | Locked/unpaired or no usable device | USB/pairing/trust state | Later device phase: unlock, use a data cable, pair/trust through Finder; retry discovery, not flashing. |
| Device found, AirLift probe fails | Incompatible/probe failure | Required service/AFC/session unavailable or unsupported environment | Record model/OS/build and probe outcome. Do not infer a signing cure or proceed to write. |
| Scanner connected, no IDs | Log stream active, no eligible rows | Redaction or unsupported card/log shape | Open the intended card; for supported transit cards consider Wallet's documented Service Mode. Keep scanning/manual-known-ID route; don't disable privacy protections or share raw logs. |
| Candidate not eligible | Unverified row / Flash rejected | Fallback, saved or cache-only provenance | Obtain a live pass ID, or deliberately approve a known correct ID. Do not mass-approve a cache list. |
| Waiting for SyncAllowed | Progress stays at first artwork batch | AirTraffic device handshake blocked | Let the deadline/cleanup complete. Inspect recovery outcome and USB/service state before considering another run. Do not launch concurrent flashes. |
| Artwork write fails | Backend error/nonzero; run stops | Stage/transfer/asset failure | Check whether any artwork was written and whether Books cleanup succeeded. Fix the observed cause before another attempt. |
| Cache invalidation fails | Cache error; no overall success | Relocation/unlink/cleanup failure | Do not assume Wallet will refresh or that all leaves were removed. Verify recovery first; preserve logs without exposing IDs. |
| Books restoration unverified | Stop/recovery snapshot message | Disconnect, helper failure or changed/unrestorable state | **Stop all writes. Retain `~/.aircard-recovery` and phone-side recovery objects; inspect/recover before retry.** Do not repeat flashing as a recovery strategy. |

After the Mac gates, one controlled USB test should record: Mac chip/macOS, iPhone model/iOS build, identification of the intended card without sharing secrets, transfer/cache/Books outcomes, and whether only that card's artwork changed. A current backup is prudent because partial artwork writes are not transactional. No full card ID, UDID, PAN, CVV or bank login is needed in a shared report.
