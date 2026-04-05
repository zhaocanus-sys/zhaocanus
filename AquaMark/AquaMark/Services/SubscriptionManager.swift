import SwiftUI
import StoreKit

class SubscriptionManager: ObservableObject {
    @Published var isPro: Bool = false
    @Published var products: [Product] = []
    @Published var purchaseState: PurchaseState = .idle

    enum PurchaseState {
        case idle, loading, purchased, failed(String)
    }

    static let weeklyID = "com.aquamark.pro.weekly"
    static let monthlyID = "com.aquamark.pro.monthly"
    static let yearlyID = "com.aquamark.pro.yearly"
    static let lifetimeID = "com.aquamark.pro.lifetime"

    static let allProductIDs: Set<String> = [
        weeklyID, monthlyID, yearlyID, lifetimeID
    ]

    init() {
        Task {
            await loadProducts()
            await checkEntitlements()
        }
        listenForTransactions()
    }

    @MainActor
    func loadProducts() async {
        do {
            let storeProducts = try await Product.products(for: Self.allProductIDs)
            products = storeProducts.sorted { $0.price < $1.price }
        } catch {
            print("Failed to load products: \(error)")
        }
    }

    @MainActor
    func purchase(_ product: Product) async {
        purchaseState = .loading
        do {
            let result = try await product.purchase()
            switch result {
            case .success(let verification):
                let transaction = try checkVerified(verification)
                await transaction.finish()
                isPro = true
                purchaseState = .purchased
            case .userCancelled:
                purchaseState = .idle
            case .pending:
                purchaseState = .idle
            @unknown default:
                purchaseState = .idle
            }
        } catch {
            purchaseState = .failed(error.localizedDescription)
        }
    }

    @MainActor
    func restorePurchases() async {
        do {
            try await AppStore.sync()
            await checkEntitlements()
        } catch {
            purchaseState = .failed("Restore failed: \(error.localizedDescription)")
        }
    }

    @MainActor
    func checkEntitlements() async {
        for await result in Transaction.currentEntitlements {
            if let transaction = try? checkVerified(result) {
                if Self.allProductIDs.contains(transaction.productID) {
                    isPro = true
                    return
                }
            }
        }
    }

    private func checkVerified<T>(_ result: VerificationResult<T>) throws -> T {
        switch result {
        case .verified(let safe):
            return safe
        case .unverified(_, let error):
            throw error
        }
    }

    private func listenForTransactions() {
        Task {
            for await result in Transaction.updates {
                if let transaction = try? checkVerified(result) {
                    await transaction.finish()
                    await MainActor.run {
                        if Self.allProductIDs.contains(transaction.productID) {
                            isPro = true
                        }
                    }
                }
            }
        }
    }

    func priceString(for productID: String) -> String {
        guard let product = products.first(where: { $0.id == productID }) else {
            return fallbackPrice(for: productID)
        }
        return product.displayPrice
    }

    private func fallbackPrice(for productID: String) -> String {
        switch productID {
        case Self.weeklyID: return "$3.99"
        case Self.monthlyID: return "$7.99"
        case Self.yearlyID: return "$29.99"
        case Self.lifetimeID: return "$49.99"
        default: return "--"
        }
    }

    func product(for id: String) -> Product? {
        products.first(where: { $0.id == id })
    }
}
