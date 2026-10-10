import Foundation

// No card IDs or artwork URLs in this result; the probe only checks local Mac files.
struct WalletArtworkLocalProbe: Decodable {
    let scope: String
    let status: String
    let passesChecked: Int
    let referenceFiles: Int
    let plausibleUrlFiles: Int
    let errors: Int
    let limited: Bool
    let note: String
}

struct WalletCachedCard: Codable, Identifiable {
    let id: String
    let name: String
    let source: String
    let activationID: String?

    init(id: String, name: String, source: String, activationID: String? = nil) {
        self.id = id
        self.name = name
        self.source = source
        self.activationID = activationID
    }
}

struct WalletCatalog: Codable {
    var paymentStatus: String
    var payments: [WalletCachedCard]
    var memberships: [WalletCachedCard]
    var warnings: [String]
    var cacheUpdatedAt: String?

    static let empty = WalletCatalog(paymentStatus: "unavailable", payments: [], memberships: [], warnings: [], cacheUpdatedAt: nil)

    func name(for id: String) -> String? {
        (payments + memberships).first(where: { $0.id == id })?.name
    }

    func payment(forActivationID id: String) -> WalletCachedCard? {
        guard paymentStatus == "matched" else { return nil }
        let matches = payments.filter { $0.activationID?.caseInsensitiveCompare(id) == .orderedSame }
        guard Set(matches.map(\.id)).count == 1 else { return nil }
        return matches.first
    }

    func pending(confirmedIDs: Set<String>, source: String) -> [WalletCachedCard] {
        let entries = source == "payment" ? payments : memberships
        var seen = Set<String>()
        return entries.filter { !confirmedIDs.contains($0.id) && seen.insert($0.id).inserted }
    }
}

struct WalletSavedCard: Codable, Equatable {
    let id: String
    var confirmed: Bool = false
    var imagePath: String? = nil
    var selected: Bool = true
    // User-supplied alias for a specific pass ID, never bank-verified metadata.
    var customLabel: String? = nil

    static func unique(_ entries: [WalletSavedCard]) -> [WalletSavedCard] {
        var result: [WalletSavedCard] = []
        var indices: [String: Int] = [:]
        for entry in entries where WalletScanParser.isValidCardID(entry.id) {
            if let index = indices[entry.id] {
                result[index].confirmed = result[index].confirmed || entry.confirmed
                if result[index].imagePath == nil { result[index].imagePath = entry.imagePath }
                if result[index].customLabel == nil { result[index].customLabel = entry.customLabel }
            } else {
                indices[entry.id] = result.count
                result.append(entry)
            }
        }
        return result
    }
}

// A bare base64-like token in a Wallet log is not proof of a card by itself.
// Prefer structured pass/cache/dashboard paths, with fallback extraction for Wallet events.
enum WalletScanParser {
    static func isValidCardID(_ id: String) -> Bool {
        id.range(of: #"\A[-A-Za-z0-9_+=]{20,64}\z"#, options: .regularExpression) != nil
    }

    static let cardReferences = [
        try! NSRegularExpression(pattern: #"/([-A-Za-z0-9_+=]{20,64})\.(?:pkpass|cache|pkcache)(?=[/\s\"'\),]|$)"#),
        try! NSRegularExpression(pattern: #"/(?:Cards|Passes/Cards)/([-A-Za-z0-9_+=]{20,64})(?=[/\s\"'\),]|$)"#, options: .caseInsensitive),
        try! NSRegularExpression(pattern: #"PDCardFileManager:\s*writing card\s+([-A-Za-z0-9_+=]{20,64})(?=[\s\"'\),]|$)"#, options: .caseInsensitive),
        try! NSRegularExpression(pattern: #"PDPassLibrary:\s*wrote pass\s+([-A-Za-z0-9_+=]{20,64})(?=[\s\"'\),]|$)"#, options: .caseInsensitive),
        try! NSRegularExpression(pattern: #"VerificationCheck\.([-A-Za-z0-9_+=]{20,64})(?=[\s\"'\),]|$)"#, options: .caseInsensitive),
        try! NSRegularExpression(pattern: #"selected pass uniqueID\s*:\s*\"?([-A-Za-z0-9_+=]{20,64})(?=[\s\"\'\),]|$)"#, options: .caseInsensitive),
        try! NSRegularExpression(pattern: #"Dashboard loading[^:]*:\s*for\s+([-A-Za-z0-9_+=]{20,80})(?=[,\s\"'\)]|$)"#, options: .caseInsensitive),
        try! NSRegularExpression(pattern: #"Dashboard loading[^:]*:\s+([-A-Za-z0-9_+=]{20,80})\s+-"#, options: .caseInsensitive),
    ]
    static let inSessionList = try! NSRegularExpression(
        pattern: #"passIDs\[(?:InSession|global)\]\s*:\s*(?:\{\s*)?\(([^)]*)\)"#,
        options: .caseInsensitive
    )
    static let cardID = try! NSRegularExpression(pattern: #"(?<![-A-Za-z0-9_+=])[-A-Za-z0-9_+=]{20,64}(?![-A-Za-z0-9_+=])"#)
    // A dedicated selection signal. Do NOT treat passIDs[global], Dashboard
    // preloads or bare fallback tokens as evidence of one chosen card.
    static let selectedPass = try! NSRegularExpression(
        pattern: #"(?:updated\s+)?selected pass uniqueID\s*:\s*"?([-A-Za-z0-9_+=]{20,64})(?=[\s"'\),]|$)"#,
        options: .caseInsensitive
    )
    static func selectedPassIDs(in line: String) -> [String] {
        var seen = Set<String>()
        return selectedPass.matches(in: line, range: NSRange(line.startIndex..., in: line)).compactMap { match in
            guard let range = Range(match.range(at: 1), in: line) else { return nil }
            let id = String(line[range])
            guard isValidCardID(id), !placeholders.contains(id), seen.insert(id).inserted else { return nil }
            return id
        }
    }
    // Only category counts are surfaced to the UI; never raw Wallet log lines.
    // An explicit selection may be absent or redacted on newer iOS releases.
    static func selectionEvidence(in line: String) -> [String] {
        let lower = line.lowercased()
        var events: [String] = []
        if lower.contains("selected pass uniqueid") {
            if !selectedPassIDs(in: line).isEmpty {
                events.append("selected")
            } else if lower.contains("<private>") || lower.contains("<redacted>") {
                events.append("redacted")
            } else {
                events.append("unrecognized")
            }
        }
        if lower.contains("passids[insession]") { events.append("inSession") }
        if lower.contains("passids[global]") { events.append("global") }
        if lower.contains("dashboard loading") { events.append("dashboard") }
        if lower.contains("setactivepaymentapplet") { events.append("activation") }
        return events
    }

    static let activation = try! NSRegularExpression(
        pattern: #"setActivePaymentApplet.{0,4096}?requestedApplet\s*:.{0,4096}?(?:identifier\s*=\s*|\"identifier\"\s*:\s*\")([A-Fa-f0-9]{10,64})\b"#,
        options: [.caseInsensitive, .dotMatchesLineSeparators]
    )
    static let fallbackToken = try! NSRegularExpression(
        pattern: #"(?<![-A-Za-z0-9+/=])([A-Za-z0-9+/_-]{27}=)(?![-A-Za-z0-9+/=])"#
    )
    static let placeholders: Set<String> = ["OM6NYhwXMZrAw0sRUjR62wmF4ZQ=", "M6nDwZrkYbFlsodLgCbvyFZQ1cc=", "kJL-D0rr-SZhbj2c8nK-OQ9hCMY=", "hwAtAmHKYwsQrJbT5cTNDsaxVME="]

    static func cardIDs(in line: String) -> [String] {
        let lineRange = NSRange(line.startIndex..., in: line)
        var candidates = cardReferences.flatMap { regex in
            regex.matches(in: line, range: lineRange).compactMap { match -> (Int, String)? in
                guard let range = Range(match.range(at: 1), in: line) else { return nil }
                return (match.range.location, String(line[range]))
            }
        }
        for listMatch in inSessionList.matches(in: line, range: lineRange) {
            let listRange = listMatch.range(at: 1)
            candidates += cardID.matches(in: line, range: listRange).compactMap { match in
                guard let range = Range(match.range, in: line) else { return nil }
                return (match.range.location, String(line[range]))
            }
        }
        candidates.sort { $0.0 < $1.0 }
        var seen = Set<String>()
        return candidates.compactMap { _, id in
            guard isValidCardID(id), !placeholders.contains(id), seen.insert(id).inserted else { return nil }
            return id
        }
    }

    static func fallbackCardIDs(in line: String) -> [String] {
        let lineRange = NSRange(line.startIndex..., in: line)
        var seen = Set<String>()
        return fallbackToken.matches(in: line, range: lineRange).compactMap { match in
            guard let range = Range(match.range(at: 1), in: line) else { return nil }
            let id = String(line[range])
            guard isValidCardID(id), !placeholders.contains(id), seen.insert(id).inserted else { return nil }
            return id
        }
    }

    static func activationIDs(in line: String) -> [String] {
        activation.matches(in: line, range: NSRange(line.startIndex..., in: line)).compactMap { match in
            guard let range = Range(match.range(at: 1), in: line) else { return nil }
            return String(line[range]).uppercased()
        }
    }
}

// Opt-in read-only A→B→A correlation. Captured IDs are transient in memory only.
// This is NOT an identity oracle: background Wallet prefetching can mimic a match.
struct WalletABACorrelation {
    enum Step: Int {
        case idle, firstTarget, switchToExpress, express, switchToTarget, secondTarget, finished
    }

    private(set) var step: Step = .idle
    private(set) var phaseIDs: [Set<String>] = [[], [], []]
    private(set) var eventCounts: [Int] = [0, 0, 0]
    private(set) var expressGlobalEvents = 0
    private(set) var dashboardEvents = 0

    var isRunning: Bool {
        step != .idle && step != .finished
    }
    var isCapturing: Bool {
        step == .firstTarget || step == .express || step == .secondTarget
    }

    var buttonTitle: String {
        switch step {
        case .idle: return "Begin Target A"
        case .firstTarget: return "End Target A"
        case .switchToExpress: return "Begin Express B"
        case .express: return "End Express B"
        case .switchToTarget: return "Begin Target A Again"
        case .secondTarget: return "Finish Comparison"
        case .finished: return "Finished"
        }
    }

    var instruction: String {
        switch step {
        case .idle:
            return "Read-only comparison. First open the rarely used card you WANT to skin, not the Express card."
        case .firstTarget:
            return "Capturing A1: keep your intended non-Express card open. Then click End Target A."
        case .switchToExpress:
            return "Paused. Switch to your Express card B; after it is open, click Begin Express B."
        case .express:
            return "Capturing B: keep the Express card open. Then click End Express B."
        case .switchToTarget:
            return "Paused. Switch back to the intended card A; after it is open, click Begin Target A Again."
        case .secondTarget:
            return "Capturing A2: keep the intended card open. Then click Finish Comparison."
        case .finished:
            return "Comparison complete. Overlaps are NOT proof of which card is selected; do not flash from this result."
        }
    }

    mutating func begin() {
        self = Self()
        step = .firstTarget
    }

    mutating func advance() {
        switch step {
        case .firstTarget: step = .switchToExpress
        case .switchToExpress: step = .express
        case .express: step = .switchToTarget
        case .switchToTarget: step = .secondTarget
        case .secondTarget: step = .finished
        case .idle, .finished: break
        }
    }

    mutating func cancel() {
        self = Self()
    }

    // Accept ONLY context-derived IDs; never bare fallback tokens or activation AIDs.
    // Prevent unlimited growth if an unexpected stream emits many distinct strings.
    mutating func observe(line: String, structuredIDs: [String]) {
        guard isCapturing else { return }
        let slot: Int
        switch step {
        case .firstTarget: slot = 0
        case .express: slot = 1
        case .secondTarget: slot = 2
        default: return
        }
        let lower = line.lowercased()
        if lower.contains("passids[global]") { expressGlobalEvents += 1 }
        if lower.contains("dashboard loading") { dashboardEvents += 1 }
        guard !structuredIDs.isEmpty else { return }
        eventCounts[slot] += 1
        for id in structuredIDs where WalletScanParser.isValidCardID(id) && !WalletScanParser.placeholders.contains(id) {
            guard phaseIDs[slot].count < 128 || phaseIDs[slot].contains(id) else { break }
            phaseIDs[slot].insert(id)
        }
    }

    var repeatedInTarget: Set<String> { phaseIDs[0].intersection(phaseIDs[2]) }
    var targetOnlyCoincidences: Set<String> { repeatedInTarget.subtracting(phaseIDs[1]) }

    // These are observed event patterns, NOT verified bank-card identities.
    // Return nothing before completion or for IDs absent from all windows.
    enum Pattern: Equatable {
        case repeatedTargetOnly
        case expressWindowOnly
        case ambiguous
    }

    func pattern(for id: String) -> Pattern? {
        guard step == .finished else { return nil }
        let inA1 = phaseIDs[0].contains(id)
        let inB = phaseIDs[1].contains(id)
        let inA2 = phaseIDs[2].contains(id)
        if inA1 && inA2 && !inB { return .repeatedTargetOnly }
        if inB && !inA1 && !inA2 { return .expressWindowOnly }
        if inA1 || inB || inA2 { return .ambiguous }
        return nil
    }

    func unverifiedHint(for id: String) -> String? {
        switch pattern(for: id) {
        case .repeatedTargetOnly:
            return "Possible target A: seen in A1 and A2, not B · UNVERIFIED"
        case .expressWindowOnly:
            return "B-window only: could be Express or background · UNVERIFIED"
        case .ambiguous:
            return "Mixed/background event pattern · UNVERIFIED"
        case nil:
            return nil
        }
    }

    var summary: String {
        let counts = phaseIDs.map { String($0.count) }
        return "Distinct structured IDs A1/B/A2: \(counts.joined(separator: "/")) · A repeat: \(repeatedInTarget.count) · A repeat absent in B: \(targetOnlyCoincidences.count) · Global events: \(expressGlobalEvents) · Dashboard events: \(dashboardEvents). Unverified correlations only."
    }
}

// Normal diagnostic text must not reveal full pass identifiers or device UDIDs.
enum WalletDiagnostics {
    static func redacted(_ message: String) -> String {
        let pattern = #"(?<![-A-Za-z0-9_+=])[-A-Za-z0-9_+=]{20,}(?![-A-Za-z0-9_+=])"#
        let regex = try! NSRegularExpression(pattern: pattern)
        var result = message
        for match in regex.matches(in: message, range: NSRange(message.startIndex..., in: message)).reversed() {
            if let range = Range(match.range, in: result) {
                result.replaceSubrange(range, with: "[identifier hidden]")
            }
        }
        return result
    }
}
