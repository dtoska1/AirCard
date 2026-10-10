import Foundation

@main
struct WalletDiscoveryTests {
    static func main() throws {
        let a = String(repeating: "A", count: 27) + "="
        let b = String(repeating: "B", count: 27) + "="
        let c = String(repeating: "C", count: 27) + "="
        for id in [a, String(repeating: "x", count: 20), String(repeating: "x", count: 64)] {
            precondition(WalletScanParser.isValidCardID(id))
        }
        for id in ["../" + a, a + "/b", a + "\\b", a + "..", a + "\n", "short", String(repeating: "x", count: 65)] {
            precondition(!WalletScanParser.isValidCardID(id))
        }
        precondition(!WalletDiagnostics.redacted("Card " + a).contains(a))
        precondition(!WalletDiagnostics.redacted("Device 00000000-0000000000000000").contains("00000000-0000000000000000"))
        let line = "Wallet /Cards/\(b).cache/Preview /Cards/\(a).pkpass/en.lproj /Cards/\(b).pkcache/FrontFace"
        precondition(WalletScanParser.cardIDs(in: line) == [b, a])
        precondition(WalletScanParser.cardIDs(in: "passd identifier \(a)").isEmpty)
        precondition(WalletScanParser.cardIDs(in: "/Cards/<private>.pkpass").isEmpty)
        let ios27Line = "nfcd: passIDs[InSession]: {(\"\(c)\")} passIDs[global]: {(\"\(a)\")}"
        precondition(WalletScanParser.cardIDs(in: ios27Line) == [c, a])
        let sessionCards = (0..<12).map { String(format: "%020dAAAAAAA=", $0) }
        let sessionList = sessionCards.map { "\"\($0)\"" }.joined(separator: ", ")
        let batchedIOS27Line = "nfcd: passIDs[InSession]: {(\(sessionList))} passIDs[global]: {(\"\(a)\")}"
        precondition(WalletScanParser.cardIDs(in: batchedIOS27Line) == sessionCards + [a])
        precondition(WalletScanParser.cardIDs(in: "nfcd: passIDs[global]: {(\"\(a)\")}") == [a])
        let dashboardLine1 = "Passbook(PassKitUI): Dashboard loading (...): for \(a), pass feature unknown"
        let dashboardLine2 = "Passbook(PassKitUI): Dashboard loading (...): \(b) - m:NO, sm:NO"
        precondition(WalletScanParser.cardIDs(in: dashboardLine1) == [a])
        precondition(WalletScanParser.cardIDs(in: dashboardLine2) == [b])
        precondition(WalletScanParser.cardIDs(in: "Wallet /Passes/Cards/\(a)/FrontFace") == [a])
        precondition(WalletScanParser.cardIDs(in: "PDCardFileManager: writing card \(b)") == [b])
        precondition(WalletScanParser.cardIDs(in: "PDPassLibrary: wrote pass \(a)") == [a])
        precondition(WalletScanParser.cardIDs(in: "VerificationCheck.\(c)") == [c])
        precondition(WalletScanParser.cardIDs(in: "updated selected pass uniqueID: \(b)") == [b])
        precondition(WalletScanParser.cardIDs(in: "updated selected pass uniqueID: <private>").isEmpty)
        precondition(WalletScanParser.selectedPassIDs(in: "updated selected pass uniqueID: \(b)") == [b])
        precondition(WalletScanParser.selectedPassIDs(in: "selected pass uniqueID: \"\(a)\"") == [a])
        precondition(WalletScanParser.selectedPassIDs(in: ios27Line).isEmpty)
        precondition(WalletScanParser.selectedPassIDs(in: dashboardLine1).isEmpty)
        precondition(WalletScanParser.selectedPassIDs(in: "selected pass uniqueID: <private>").isEmpty)
        precondition(WalletScanParser.selectionEvidence(in: "nfcd passIDs[global]: {(\"\(a)\")} passIDs[InSession]: {(\"\(b)\")}") == ["inSession", "global"])
        precondition(WalletScanParser.selectionEvidence(in: "passd updated selected pass uniqueID: \(a)") == ["selected"])
        precondition(WalletScanParser.selectionEvidence(in: "passd updated selected pass uniqueID: <private>") == ["redacted"])
        precondition(WalletScanParser.selectionEvidence(in: "passd updated selected pass uniqueID: UNKNOWN") == ["unrecognized"])
        precondition(WalletScanParser.selectionEvidence(in: "passd something unrelated").isEmpty)

        // Opt-in read-only A / Express B / A correlation.
        // Neither global lists nor Dashboard preloads prove selection.
        var correlation = WalletABACorrelation()
        precondition(!correlation.isRunning)
        correlation.begin()
        precondition(correlation.step == .firstTarget && correlation.isCapturing)
        correlation.observe(line: dashboardLine1, structuredIDs: [a])
        correlation.observe(line: "Wallet /Cards/\(c).cache", structuredIDs: [c])
        correlation.advance()
        precondition(correlation.step == .switchToExpress && !correlation.isCapturing)
        correlation.observe(line: dashboardLine1, structuredIDs: [a]) // excluded while switching
        correlation.advance()
        precondition(correlation.step == .express)
        correlation.observe(line: "nfcd passIDs[global]: {(\\\"\(b)\\\")}", structuredIDs: [b])
        correlation.observe(line: "Wallet /Cards/\(c).cache", structuredIDs: [c])
        correlation.advance()
        correlation.observe(line: dashboardLine1, structuredIDs: [a]) // paused, excluded
        correlation.advance()
        precondition(correlation.step == .secondTarget)
        correlation.observe(line: dashboardLine1, structuredIDs: [a])
        correlation.observe(line: "Wallet /Cards/\(c).cache", structuredIDs: [c])
        correlation.advance()
        precondition(correlation.step == .finished && !correlation.isRunning)
        precondition(correlation.phaseIDs[0] == Set([a, c]))
        precondition(correlation.phaseIDs[1] == Set([b, c]))
        precondition(correlation.phaseIDs[2] == Set([a, c]))
        precondition(correlation.repeatedInTarget == Set([a, c]))
        precondition(correlation.targetOnlyCoincidences == Set([a]))
        precondition(correlation.expressGlobalEvents == 1)
        precondition(!correlation.summary.contains(a)) // never show full identifiers
        correlation.cancel()
        precondition(correlation.step == .idle && correlation.phaseIDs.allSatisfy(\.isEmpty))

        let activation = "A00000000310100100000020"
        let activeLine = "setActivePaymentApplet: x requestedApplet: <NFApplet> { identifier=\(activation) family=0x0 }"
        precondition(WalletScanParser.activationIDs(in: activeLine) == [activation])
        let multilineActivation = "setActivePaymentApplet: x requestedApplet:\n<NFApplet> { identifier = \(activation) family=0x0 }"
        precondition(WalletScanParser.activationIDs(in: multilineActivation) == [activation])
        let jsonActivation = "setActivePaymentApplet: x requestedApplet: {\"identifier\":\"\(activation)\",\"family\":0}"
        precondition(WalletScanParser.activationIDs(in: jsonActivation) == [activation])
        let fallbackLine = "passd: some unusual event \(c) without explicit path"
        precondition(WalletScanParser.fallbackCardIDs(in: fallbackLine) == [c])
        let cards = [WalletSavedCard(id: b, confirmed: true, imagePath: "/skin-b.png", selected: false),
                     WalletSavedCard(id: a, imagePath: "/skin-a.png"),
                     WalletSavedCard(id: b), WalletSavedCard(id: a, confirmed: true)]
        let unique = WalletSavedCard.unique(cards)
        precondition(unique.map(\.id) == [b, a])
        precondition(unique[0].imagePath == "/skin-b.png" && !unique[0].selected)
        precondition(unique[1].imagePath == "/skin-a.png" && unique[1].confirmed)
        let restored = try JSONDecoder().decode([WalletSavedCard].self, from: JSONEncoder().encode(unique))
        precondition(restored == unique)
        var named = restored
        named[0].customLabel = "Personal card"
        let namedRoundTrip = try JSONDecoder().decode([WalletSavedCard].self, from: JSONEncoder().encode(named))
        precondition(namedRoundTrip[0].customLabel == "Personal card")
        let oldRecord = #"{"id":"AAAAAAAAAAAAAAAAAAAAAAAAAAA=","confirmed":true,"selected":true}"#
        let decodedOld = try JSONDecoder().decode(WalletSavedCard.self, from: Data(oldRecord.utf8))
        precondition(decodedOld.customLabel == nil)
        let catalog = WalletCatalog(paymentStatus: "matched", payments: [
            WalletCachedCard(id: a, name: "Same bank", source: "payment", activationID: activation),
            WalletCachedCard(id: b, name: "Same bank", source: "payment")
        ], memberships: [WalletCachedCard(id: c, name: "Membership", source: "membership")], warnings: [], cacheUpdatedAt: nil)
        precondition(catalog.pending(confirmedIDs: [a], source: "payment").map(\.id) == [b])
        precondition(catalog.pending(confirmedIDs: [a], source: "membership").map(\.id) == [c])
        precondition(catalog.name(for: a) == "Same bank")
        precondition(catalog.payment(forActivationID: activation)?.id == a)
        var ambiguous = catalog
        ambiguous.payments.append(WalletCachedCard(id: b, name: "Other", source: "payment", activationID: activation.lowercased()))
        precondition(ambiguous.payment(forActivationID: activation) == nil)
        precondition(catalog.payment(forActivationID: "F0000000000") == nil)
        precondition(WalletScanParser.fallbackCardIDs(in: "passd " + String(repeating: "A", count: 26) + "/=").isEmpty)
        precondition(WalletScanParser.cardIDs(in: "selected pass uniqueID: " + String(repeating: "A", count: 70)).isEmpty)
        precondition(catalog.name(for: "missing") == nil)
        // A view reorder must still attach skin B to ID B, never its old offset.
        let skins = Dictionary(uniqueKeysWithValues: restored.map { ($0.id, $0.imagePath) })
        let reordered = [a, b].map { skins[$0]!! }
        precondition(reordered == ["/skin-a.png", "/skin-b.png"])
        print("Wallet identity, pending counts, deduplication, persistence and path parsing passed")
    }
}
