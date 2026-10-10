import Foundation

@main
struct WalletViewModelTests {
    @MainActor
    static func main() {
        let suite = "AirCardWalletTests." + UUID().uuidString
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        let a = String(repeating: "A", count: 27) + "="
        let b = String(repeating: "B", count: 27) + "="
        let c = String(repeating: "C", count: 27) + "="
        defaults.set([b, a, b], forKey: "mak5er.aircard.savedCards")
        let vm = AppViewModel(cardDefaults: defaults, connectOnLaunch: false)
        precondition(vm.cards.map(\.id) == [b, a])
        precondition(vm.currentVerifiedCards.isEmpty) // Saved records stay hidden until this scan sees them.
        precondition(vm.confirmedCardIDs.isEmpty) // Legacy IDs have no device provenance.
        vm.activateCardDevice("first-phone")
        vm.isScanningCards = true
        vm.walletCatalog = WalletCatalog(paymentStatus: "matched", payments: [
            .init(id: a, name: "Active A", source: "payment"),
            .init(id: b, name: "Active B", source: "payment")
        ], memberships: [], warnings: [], cacheUpdatedAt: nil)
        vm.reconcileMatchedPaymentCards()
        precondition(vm.currentVerifiedCards.isEmpty) // A cache alone is not enough.
        vm.recordScannedCard(a)
        vm.recordScannedCard(a)
        precondition(vm.currentScanIDs == [a] && vm.confirmedCardIDs == [a])
        precondition(vm.currentVerifiedCardIDs == [a])
        precondition(vm.cards.count == 2)
        // Missing Mac cache must not prevent a user-confirmed local nickname.
        // A global ID list by itself must NEVER identify the card just opened.
        vm.device = DeviceInfo(
            udid: "first-phone", name: "Test iPhone", version: "27.0.1",
            product: "iPhone16,2", language: nil, locale: nil, bold_text: nil,
            airlift_compatible: nil, airlift_tested: nil, connected: true, error: nil
        )
        vm.beginCardIdentification()
        precondition(vm.isIdentifyingCard)
        vm.observeSelectedPassEvent("nfcd: passIDs[global]: {(\"\(b)\")}")
        precondition(vm.isIdentifyingCard && vm.pendingIdentifiedCardID == nil)
        vm.observeSelectedPassEvent("passd: updated selected pass uniqueID: \(a)")
        precondition(!vm.isIdentifyingCard && vm.pendingIdentifiedCardID == a && vm.showCardNamingSheet)
        precondition(!vm.confirmIdentifiedCardName(""))
        precondition(vm.confirmIdentifiedCardName("Daily Visa"))
        precondition(vm.cards.first(where: { $0.id == a })?.customLabel == "Daily Visa")
        precondition(vm.cards.first(where: { $0.id == a })?.isSelected == false)
        vm.isScanningCards = false
        let activation = "A00000000310100100000020"
        precondition(!vm.recordActivatedPaymentCard(activation))
        vm.walletCatalog = WalletCatalog(paymentStatus: "matched", payments: [.init(id: b, name: "Active B", source: "payment", activationID: activation)], memberships: [], warnings: [], cacheUpdatedAt: nil)
        vm.reconcilePendingPaymentActivations()
        precondition(vm.cards.first(where: { $0.id == b })?.displayName == "Active B")
        vm.cards[0].customImageURL = URL(fileURLWithPath: "/skin-b.png")
        vm.cards[1].customImageURL = URL(fileURLWithPath: "/skin-a.png")
        vm.cards.reverse()
        vm.activateCardDevice("second-phone")
        precondition(vm.confirmedCardIDs.isEmpty)
        precondition(vm.cards.allSatisfy { $0.customImageURL == nil })
        vm.recordScannedCard(b)
        vm.activateCardDevice("first-phone")
        precondition(vm.cards.map(\.id) == [a, b])
        precondition(vm.confirmedCardIDs == [a, b])
        precondition(vm.cards.first(where: { $0.id == a })?.customLabel == "Daily Visa")
        precondition(vm.cards.first(where: { $0.id == a })?.displayName == "Daily Visa")
        precondition(vm.cards[0].customImageURL?.path == "/skin-a.png")
        precondition(vm.cards[1].customImageURL?.path == "/skin-b.png")
        vm.flashedSkins = ["first-phone|" + a: "first", "second-phone|" + b: "second"]
        vm.log("Card " + a + " on 00000000-0000000000000000")
        precondition(!vm.logs.last!.contains(a))
        precondition(!vm.logs.last!.contains("00000000-0000000000000000"))
        vm.clearAllCards()
        precondition(vm.flashedSkins == ["second-phone|" + b: "second"])
        precondition(vm.currentVerifiedCardIDs.isEmpty)
        vm.activateCardDevice("second-phone")
        precondition(vm.confirmedCardIDs == [b])
        vm.activateCardDevice("first-phone")
        precondition(vm.cards.isEmpty) // Clear must not resurrect legacy JSON/defaults.
        let relaunched = AppViewModel(cardDefaults: defaults, connectOnLaunch: false)
        relaunched.activateCardDevice("first-phone")
        precondition(relaunched.cards.isEmpty)
        relaunched.activateCardDevice("second-phone")
        precondition(relaunched.confirmedCardIDs == [b])
        let countBeforePreload = relaunched.cards.count
        relaunched.recordPreloadedCard(c)
        relaunched.recordPreloadedCard(c)
        precondition(relaunched.cards.count == countBeforePreload + 1)
        precondition(relaunched.cards.first(where: { $0.id == c })?.confirmed == true)
        precondition(relaunched.currentVerifiedCards.map(\.id) == [c])
        relaunched.clearAllCards()
        precondition(relaunched.flashEligibleIDs.isEmpty)
        relaunched.recordCandidateCard(a)
        precondition(relaunched.flashEligibleIDs.isEmpty)
        relaunched.addCardHash(a)
        precondition(relaunched.flashEligibleIDs == [a])
        precondition(relaunched.currentVerifiedCardIDs.isEmpty)
        precondition(relaunched.cards.first?.confirmed == false)
        relaunched.deleteCard(id: a)
        precondition(relaunched.flashEligibleIDs.isEmpty)
        relaunched.addCardHash("../" + b)
        precondition(relaunched.cards.isEmpty)
        relaunched.walletCatalog = WalletCatalog(paymentStatus: "matched", payments: [
            .init(id: a, name: "A", source: "payment", activationID: activation),
            .init(id: b, name: "B", source: "payment", activationID: activation)
        ], memberships: [], warnings: [], cacheUpdatedAt: nil)
        precondition(!relaunched.recordActivatedPaymentCard(activation, refreshIfNeeded: false))
        precondition(relaunched.flashEligibleIDs.isEmpty)
        print("Wallet view model migration, device isolation, repeat scans, skin identity and clear/relaunch passed")
    }
}
