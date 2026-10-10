# AirCard 🎴

> **Apple Wallet Card Skinner & Lockscreen Passcode Themer (No Jailbreak Required)**  
> **Supports iOS 18.0 – 27.0.1 & iOS 27.2 beta 1–2** (iOS 27.2 beta 3+ patched)  
> Powered by the `airlift` AirTraffic sync exploit.

<p align="left">
  <a href="https://www.paypal.com/donate/?hosted_button_id=98QRTC2HFRA4Y"><img src="https://img.shields.io/badge/Donate-PayPal-00457C?style=flat-square&logo=paypal" alt="Donate with PayPal" /></a>
</p>

---

## Compatibility

| iOS Version | Status | Notes |
| :--- | :--- | :--- |
| **iOS 18.0 – 27.0.1** | ✅ Supported | Full support for Wallet skins and Lockscreen passcode themes |
| **iOS 27.2 beta 1 – beta 2** | ✅ Supported | Working |
| **iOS 27.2 beta 3+** | ❌ Patched | Apple patched the underlying `airlift` exploit. Flashing will not work. |

> [!IMPORTANT]
> Do not update to **iOS 27.2 beta 3 or newer** if you want to continue using AirCard. The underlying AirTraffic sync exploit was patched by Apple in beta 3.

---

## Features
- 🎨 **Custom Card Skins:** Assign custom artwork, textures, or bank logos to Apple Pay and Wallet cards.
- 🔢 **Lock Screen Passcode Themes (.passthm):** Apply custom keypad button artwork from popular `.passthm` themes directly to iOS 18+ lockscreen.
- 🧩 **Passcode Theme Creator:** Create custom themes from a single wallpaper (Seamless Poster Slicing) or build key-by-key (Individual Keys).
- 🔍 **Interactive Photo Framing:** Pan and zoom artwork directly inside keypad buttons with real-time iPhone preview.
- ✏️ **Edit Existing .passthm Themes:** Open any Cowabunga or Nugget theme package directly in the creator, tweak button artwork, reposition photos, and re-export or flash.
- ⚡ **Per-Card & Bulk Customization:** Set unique artwork for each card or apply one design across all cards with a single click.
- 📱 **Zero-Hassle Card Detection:** Tap any card in your iPhone's Wallet app to detect its hash in real-time.
- 🚀 **100% Standalone (Universal):** Native support for both **Apple Silicon** and **Intel (x86)** Macs. All required device-communication utilities and image engines are pre-bundled inside the app.
- 📦 **Runtime Requirements:** Uses an installed Python 3 runtime and Apple device frameworks. Python is not bundled; macOS may require Developer Tools. No third-party Python packages are required for the core GUI workflow.

---

## Guides and sample artwork

Wallet setup, detailed troubleshooting, multi-card workflows, theme creation, compatibility reporting, and local artwork preparation:

- [简体中文使用指南](docs/guides/README.zh-CN.md)
- [English getting-started guide](docs/guides/README.en.md)
- [Card artwork and source notes](assets/skins/README.md)
- [Offline card artwork editor](tools/card-artwork/README.md) — download a single HTML file, frame an image locally, and export a 1536 × 969 PNG

---

## Installation

### macOS (Universal DMG)
1. Download **`AirCard.dmg`** from [Releases](https://github.com/mak5er/AirCard/releases).
2. Open `AirCard.dmg` and drag **`AirCard.app`** into your **Applications** folder.
3. Fully compatible with both **Apple Silicon** and **Intel (x86)** Macs.

> [!NOTE]
> **First Launch on macOS (Gatekeeper):**
> A valid signature, notarization, and malware detection are different checks. For a reviewed app blocked only because its developer/notarization cannot be verified, use **System Settings → Privacy & Security → Open Anyway** after attempting launch, if macOS offers it. Do not override an actual malware warning or repair a damaged signature by stripping attributes. See [Mac validation](docs/PRE_MAC_VALIDATION.md).

> [!TIP]
> **Python / Developer Tools:**
> Python is not bundled. The GUI chooses the first executable at `/usr/bin/python3`, `/opt/homebrew/bin/python3`, then `/usr/local/bin/python3`. The Apple path may be a Developer Tools launcher; its existence does not prove Python works. Python **3.9+** and the standard library are required. `build.sh` now probes the same selected interpreter and all backend imports before building. Install/select compatible Xcode or Command Line Tools yourself if needed; the build installs nothing. For full Xcode, finish its first-launch component/license setup.

> [!NOTE]
> **Windows users:** an unofficial Windows port is available at [**AirCard-Windows**](https://github.com/Lumid-Off/AirCard-Windows).

---

## How to Customize Apple Wallet Cards
1. Connect your iPhone to your Mac via USB cable and ensure it is unlocked and trusted.
2. In AirCard, stay on the **Wallet Cards** tab and click **Scan Cards**.
3. On your iPhone:
   - **Double-click the Side (Power) button** to open Apple Pay.
   - Authenticate with **Face ID**.
   - **Tap your card** (or tap it once more) to trigger instant detection!
4. Click on any card mockup or drag & drop an image directly onto the card.
5. Click **Flash Skins**.
6. Force-close the **Wallet** app on your iPhone from the App Switcher (or reboot) to see your new custom card design!

> [!NOTE]
> **Apple Card:**
> The Apple Card (titanium/digital card) uses dynamic vector rendering based on your spending categories instead of static cached card skins. Custom skins apply to standard debit/credit cards, transit cards, and passes.

### Card names and missing-card checks

Scanned cards can now display names from this Mac's Wallet cache. Open **Check
missing cards** to distinguish current-scan matches from membership entries and
payment caches that still need confirmation. Use **Reconnect** for connection
problems and **Read Cache** to reread local metadata.

For payment cards, AirCard uses the NFC activation event for the card you
actually open. Wallet may also request artwork for several cards; IDs observed
in those current iPhone log paths can appear in a batch. Once a live ID matches
one specific remote-device cache, the remaining payment IDs from that same
cache are included so cards omitted by iOS logging still appear. Saved IDs from
an earlier run remain hidden until the current scan matches them again.

Cards and skin file paths are saved by ID separately for each iPhone, in stable
local discovery order. Only IDs matched during the current scan, either live or
through the live-ID-matched device cache, are shown or eligible to flash; saved
records only restore their skin after revalidation.
Cache counts are not the phone's total, and phone Wallet order is not synchronized. See
[card identification and diagnostics](docs/wallet-discovery.md).
### Naming cards without a Mac Wallet archive (experimental)

On some Macs, `~/Library/Passes/RemoteDevices.archive` does not exist. **Read Cache**
cannot provide bank/card names there, even when scanning successfully discovers
multiple IDs. You do not need to recreate or download that archive.

For a more cautious, local identification workflow:

1. Connect and unlock the iPhone, select **Identify Card** in the Wallet tab.
   The scanner starts automatically if necessary.
2. **After** clicking Identify Card, open **one** specific card on the iPhone.
3. AirCard waits for a log event explicitly saying `selected pass uniqueID`.
   Lists like `passIDs[global]`, Dashboard preload logs and generic tokens
   are never used to label a supposedly selected card.
4. If that event appears, verify the iPhone was showing the card you intended,
   then enter a **friendly nickname only**. Do not enter a card number.
   If unsure, cancel; the nickname is not proof of issuer identity.
5. The label stays in your local, **per-device** saved-card records. It does
   not change or transmit banking data, and labeling never auto-selects a card
   for flashing. Re-check the card on the phone before any eventual write.

**Limitation:** iOS may redact or omit explicit selection events, including on
iOS 27.0.1. In that case Identify Card remains waiting; use Cancel Identify.
The app deliberately does not guess which of several global pass IDs was
opened. This workflow has not yet been compiled or tested on real iOS 27.0.1
hardware. Rebuild the `hardening` branch and run its Mac tests before using it.

### Experimental A → Express B → A comparison (read-only)

If the Mac payment cache is absent and iOS redacts the currently selected pass
ID, **Identify Card** may remain waiting indefinitely. The optional
**A/B/A Study** tool compares structured Wallet events in three explicitly
separated capture windows, without writing anything to the phone.

**For this iPhone setup, A means the rarely used card you actually want to
reskin; B means the already-working Express card, only as a control.** Being
listed by `passIDs[global]` does **not** identify B as the selected card.

1. Open the **target card A** in Wallet, then click **A/B/A Study**. The app
   deselects all cards and starts read-only scanning if needed.
2. Leave A open for a short capture window, then click **End Target A**.
3. While the study is **paused**, switch to the **Express card B**. Once it is
   fully open, click **Begin Express B**. Capture briefly and end B.
4. While paused, switch back to **target card A**, click **Begin Target A Again**,
   capture briefly, and click **Finish Comparison**.
5. Review the *temporary* orange labels on the matching card rows:
   **Possible target A** means the ID appeared in both target windows but not B;
   **B-window only** means it appeared during B but not either A window;
   **Mixed/background** means the pattern was ambiguous. All three are
   **UNVERIFIED**, even if only one row matches. A repeated A-only event can be
   unrelated prefetching and does not prove which Wallet card is selected.

The diagnostic uses in-memory sets of context-derived IDs and shows **counts
only** (no full identifiers, card details or raw log export). It does not
rename/approve/select cards, and keeps flashing and manual selection
disabled while the study panel is visible, even after it finishes. The scanner
stops when comparison finishes. Close the panel to discard all temporary
results and labels. If all stages show the same IDs, the logs cannot
distinguish the cards and no assignment should be inferred.

This experimental change requires a fresh local Mac build and testing; it has
not been validated with a real iPhone 15 Pro Max on iOS 27.0.1. Do not use its
results alone to authorize an artwork write.

### Original artwork recovery check (Mac-only, experimental)

The **Recovery Check** button runs `artwork_recovery_probe.py` locally and
checks only existing `~/Library/Passes/Cards/*.pkpass` folders on the Mac for
`cardBackgroundCombined*.urls` reference files. It shows **counts only**:
folders examined, reference files present and files containing a plausible
HTTP(S) artwork URL. It does not reveal URLs, card identifiers, authentication
tokens or the file contents. There are no network requests, iPhone reads,
AirLift operations, artwork writes or cache removals.

**A zero result does not imply the iPhone has no original artwork references.**
Some Macs (including Macs without a Wallet payment cache) have no local payment
pass folders, even if the iPhone's Wallet cards are present and working.

The iPhone's protected Wallet pass folders are **outside this first-stage
diagnostic**. The existing `read_file` helper is *not* a pure read: it
temporarily relocates a protected file and attempts to put it back. We must
review and test recovery from timeouts, disconnects and restore failures before
exposing any diagnostic that touches protected Wallet files. Do not treat this
check as an artwork recovery tool, and do not use the Clear Image button to
try to undo a flash. The app has no verified byte-for-byte undo for artwork
that was already overwritten, and cannot guarantee removal of historical logs.

### If scanning finds no cards

The scanner uses the iPhone's unified log service, including Info/Debug events.
On iOS 18.6.2, the legacy log service can show Wallet activity while omitting the
resource lookup messages that contain card identifiers.

Open **Log** and check for `Connected to the unified device log stream`, then
double-click the side button, authenticate, and tap or switch cards. If the log
reader stops, reconnect and unlock the iPhone, then start another scan. Values
that iOS replaces with `<private>` cannot be recovered by the scanner.

If your device previously connected but scanning found zero cards, please try
this build and report whether it helps. Include your iPhone model, iOS version,
macOS version, and the AirCard version or commit tested. Avoid posting full
device logs or card identifiers. See [scanner validation](docs/wallet-card-detection.md)
for the verified environment and remaining coverage.

---

## How to Apply Lockscreen Passcode Themes (.passthm)
1. Switch to the **Passcode Themes** tab at the top of AirCard.
2. Drag & drop any `.passthm` file into the app (or click **Choose .passthm File**).
3. AirCard will inspect the theme and display an interactive preview on the numeric keypad (0–9, *, #).
4. Click **Apply Passcode Theme**.
5. Restart your iPhone to reload the lock screen cache and see your custom passcode buttons!

> [!TIP]
> **Universal Language & Bold Text Support:**  
> AirCard automatically expands and flashes custom keypad assets for all system locales (English, Ukrainian, Russian, Spanish, German, French, etc.) and generates both standard and **Bold Text** cache bitmaps (`--white` and `--white-bold`), ensuring your theme works regardless of your iOS language or accessibility display settings!

---

## Community Resources

- [AirCards](https://aircards.org/) — A free, independently maintained
  card artwork catalog and sharing community. Browse, filter, and
  preview designs, download PNG artwork to use with AirCard, or
  publish your own creations for others to discover and use.

These resources are maintained by the community and are not affiliated
with the AirCard project.

---

## Building from Source

Use macOS **14 or later**, a compatible Apple SDK/toolchain with `xcrun clang` and `xcrun swiftc`, and installed Python 3.9+. Full Xcode is the recommended first-test environment; Command Line Tools may suffice if the SwiftUI SDK and private-framework link inputs are usable. Neither setup has been compiled in this Linux review. Required tools are `make`, `xcode-select`, `lipo`, `codesign`, `otool`, `hdiutil`, and `sips`; `create-dmg` is optional. No third-party Python package is required for the core GUI path.

For this fork:

```sh
git clone --branch hardening https://github.com/dtoska1/AirCard.git
cd AirCard
git status --short --branch
git rev-parse HEAD
python3 -m unittest discover -s tests -v
bash build.sh
bash scripts/verify_mac.sh
```

The build targets both `arm64` and `x86_64` with a minimum deployment version of 14.0, creates `build/AirCard.app` and `build/AirCard.dmg`, and defaults to ad-hoc signatures. Python remains an external runtime. The verification script checks signatures, both architecture slices, backend imports, real PNG/PDF preparation, and helper loading without contacting a phone or launching the GUI. Run it again with `/Applications/AirCard.app` as the first argument after copying the app there.

For the first personal test, use the default ad-hoc build. A local build normally has no download quarantine, but inspect the actual attributes; an explicit `spctl` rejection is expected for ad-hoc code. Developer ID signing is optional via `CODESIGN_IDENTITY="Developer ID Application: …" bash build.sh`; this adds hardened runtime and a timestamp. Notarization is a separate step, never performed automatically. See the [complete trace, failure matrix and Mac checklist](docs/PRE_MAC_VALIDATION.md) before any device write.

---

## Contributors
- **[@mak5er](https://github.com/mak5er)** (Developer) — [GitHub](https://github.com/mak5er) · [Twitter / X](https://x.com/mak5er)
- **[@Lumid-Off](https://github.com/Lumid-Off)** (Contributor & Developer) — [GitHub](https://github.com/Lumid-Off) · [Twitter / X](https://x.com/LumidOff)
- **[AirLift](https://github.com/0xjohnnydev/airlift)** by **[0xjohnny (@0xjohnnydev)](https://github.com/0xjohnnydev)**: Original AirTraffic/ATAirlock sandbox escape and proof of concept underlying `AirliftFFI`.

## Credits
- Core exploit based on `airlift` (AirTraffic sync escape).

---

## Support

If you find AirCard useful, you can support future development:

- **PayPal**: [Donate via PayPal](https://www.paypal.com/donate/?hosted_button_id=98QRTC2HFRA4Y)
- **TON**: `UQBm9KPhtMw-XVVjirUoa09wzrlyWsbeZhKfefl1Uw-qNZ-r`
- **USDT (TRC20)**: `TDkDMCyjYxgvkWUnQiF5Erk2RyPQMT6G1n`
- **USDT / BNB (BEP20)**: `0x0954dc491c502849d04956ef74634aa5931a08e8`


For this fork’s audited changes, test results and remaining macOS/device gates, see [Hardening review](docs/HARDENING_REVIEW.md).
