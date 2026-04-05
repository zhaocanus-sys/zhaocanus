import SwiftUI
import StoreKit

struct SubscriptionView: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject var subscriptionManager: SubscriptionManager
    @State private var selectedPlan: String = SubscriptionManager.yearlyID
    @State private var showRestoreAlert = false

    private let features = [
        ("checkmark.seal.fill", "Unlimited Exports", "Export without watermarks or limits"),
        ("4k.tv.fill", "4K Ultra HD", "Maximum quality output"),
        ("square.stack.3d.up.fill", "Batch Processing", "Process multiple files at once"),
        ("video.fill", "Video Watermark", "Add watermarks to any video"),
        ("number.circle.fill", "MD5 Modifier", "Change file fingerprints"),
        ("crown.fill", "Priority Support", "Get help when you need it")
    ]

    var body: some View {
        ZStack {
            backgroundGradient
            ScrollView(.vertical, showsIndicators: false) {
                VStack(spacing: AppTheme.Spacing.lg) {
                    closeButton
                    heroSection
                    featuresSection
                    plansSection
                    ctaButton
                    legalSection
                }
                .padding(.horizontal, AppTheme.Spacing.md)
                .padding(.bottom, AppTheme.Spacing.xxl)
            }
        }
    }

    private var backgroundGradient: some View {
        ZStack {
            AppTheme.Colors.gradientDark.ignoresSafeArea()

            Circle()
                .fill(AppTheme.Colors.primary.opacity(0.15))
                .frame(width: 300, height: 300)
                .blur(radius: 80)
                .offset(x: -100, y: -200)

            Circle()
                .fill(AppTheme.Colors.accent.opacity(0.1))
                .frame(width: 250, height: 250)
                .blur(radius: 60)
                .offset(x: 120, y: -100)
        }
    }

    private var closeButton: some View {
        HStack {
            Spacer()
            Button { dismiss() } label: {
                Image(systemName: "xmark.circle.fill")
                    .font(.system(size: 30))
                    .foregroundStyle(.white.opacity(0.5))
            }
        }
        .padding(.top, AppTheme.Spacing.sm)
    }

    private var heroSection: some View {
        VStack(spacing: AppTheme.Spacing.md) {
            ZStack {
                Circle()
                    .fill(
                        LinearGradient(
                            colors: [Color(hex: "6C5CE7"), Color(hex: "FD79A8")],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(width: 80, height: 80)
                    .shadow(color: AppTheme.Colors.primary.opacity(0.4), radius: 20)

                Image(systemName: "crown.fill")
                    .font(.system(size: 36))
                    .foregroundColor(.white)
            }

            Text("Upgrade to Pro")
                .font(AppTheme.Typography.largeTitle)
                .foregroundColor(.white)

            Text("Unlock the full creative power of AquaMark")
                .font(AppTheme.Typography.subheadline)
                .foregroundColor(AppTheme.Colors.textSecondary)
                .multilineTextAlignment(.center)
        }
    }

    private var featuresSection: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            ForEach(features, id: \.0) { icon, title, subtitle in
                HStack(spacing: AppTheme.Spacing.md) {
                    Image(systemName: icon)
                        .font(.system(size: 20))
                        .foregroundStyle(AppTheme.Colors.gradientPrimary)
                        .frame(width: 32)

                    VStack(alignment: .leading, spacing: 2) {
                        Text(title)
                            .font(AppTheme.Typography.headline)
                            .foregroundColor(.white)
                        Text(subtitle)
                            .font(AppTheme.Typography.footnote)
                            .foregroundColor(AppTheme.Colors.textTertiary)
                    }
                    Spacer()
                }
                .padding(.vertical, 6)
            }
        }
        .padding(AppTheme.Spacing.md)
        .background(
            RoundedRectangle(cornerRadius: AppTheme.Radius.lg)
                .fill(.ultraThinMaterial)
                .overlay(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.lg)
                        .fill(AppTheme.Colors.glassFill)
                )
        )
    }

    private var plansSection: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            planCard(
                id: SubscriptionManager.yearlyID,
                title: "Annual",
                price: subscriptionManager.priceString(for: SubscriptionManager.yearlyID),
                period: "/year",
                badge: "Best Value",
                savings: "Save 69%"
            )

            planCard(
                id: SubscriptionManager.monthlyID,
                title: "Monthly",
                price: subscriptionManager.priceString(for: SubscriptionManager.monthlyID),
                period: "/month"
            )

            planCard(
                id: SubscriptionManager.weeklyID,
                title: "Weekly",
                price: subscriptionManager.priceString(for: SubscriptionManager.weeklyID),
                period: "/week"
            )

            planCard(
                id: SubscriptionManager.lifetimeID,
                title: "Lifetime",
                price: subscriptionManager.priceString(for: SubscriptionManager.lifetimeID),
                period: "one-time",
                badge: "Forever"
            )
        }
    }

    private func planCard(
        id: String,
        title: String,
        price: String,
        period: String,
        badge: String? = nil,
        savings: String? = nil
    ) -> some View {
        Button {
            withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                selectedPlan = id
            }
        } label: {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 6) {
                        Text(title)
                            .font(AppTheme.Typography.headline)
                            .foregroundColor(.white)

                        if let badge = badge {
                            Text(badge)
                                .font(.system(size: 9, weight: .bold, design: .rounded))
                                .foregroundColor(.white)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(
                                    Capsule()
                                        .fill(AppTheme.Colors.gradientAccent)
                                )
                        }
                    }

                    if let savings = savings {
                        Text(savings)
                            .font(AppTheme.Typography.caption)
                            .foregroundColor(AppTheme.Colors.success)
                    }
                }

                Spacer()

                HStack(spacing: 2) {
                    Text(price)
                        .font(.system(size: 20, weight: .bold, design: .rounded))
                        .foregroundColor(.white)
                    Text(period)
                        .font(AppTheme.Typography.caption)
                        .foregroundColor(AppTheme.Colors.textTertiary)
                }
            }
            .padding(AppTheme.Spacing.md)
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.md)
                    .fill(selectedPlan == id ? AppTheme.Colors.primary.opacity(0.2) : AppTheme.Colors.glassFill)
                    .overlay(
                        RoundedRectangle(cornerRadius: AppTheme.Radius.md)
                            .stroke(
                                selectedPlan == id ? AppTheme.Colors.primary : AppTheme.Colors.glassBorder,
                                lineWidth: selectedPlan == id ? 2 : 1
                            )
                    )
            )
        }
        .buttonStyle(ScaleButtonStyle())
    }

    private var ctaButton: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            Button {
                Task {
                    if let product = subscriptionManager.product(for: selectedPlan) {
                        await subscriptionManager.purchase(product)
                    }
                }
            } label: {
                HStack(spacing: 8) {
                    Image(systemName: "crown.fill")
                    Text("Start Pro Now")
                        .font(.system(size: 18, weight: .bold, design: .rounded))
                }
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 16)
                .background(
                    AppTheme.Colors.gradientPrimary
                )
                .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.md))
                .shadow(color: AppTheme.Colors.primary.opacity(0.4), radius: 12, x: 0, y: 6)
            }
            .buttonStyle(ScaleButtonStyle())

            Button {
                Task {
                    await subscriptionManager.restorePurchases()
                }
            } label: {
                Text("Restore Purchases")
                    .font(AppTheme.Typography.subheadline)
                    .foregroundColor(AppTheme.Colors.textTertiary)
            }
        }
    }

    private var legalSection: some View {
        VStack(spacing: 4) {
            Text("Payment will be charged to your Apple ID account at confirmation of purchase. Subscription automatically renews unless auto-renew is turned off at least 24 hours before the end of the current period.")
                .font(.system(size: 10))
                .foregroundColor(AppTheme.Colors.textTertiary)
                .multilineTextAlignment(.center)

            HStack(spacing: AppTheme.Spacing.md) {
                Link("Terms of Use", destination: URL(string: "https://aquamark.app/terms")!)
                    .font(.system(size: 10, weight: .medium))
                    .foregroundColor(AppTheme.Colors.primary)
                Link("Privacy Policy", destination: URL(string: "https://aquamark.app/privacy")!)
                    .font(.system(size: 10, weight: .medium))
                    .foregroundColor(AppTheme.Colors.primary)
            }
        }
        .padding(.top, AppTheme.Spacing.sm)
    }
}
