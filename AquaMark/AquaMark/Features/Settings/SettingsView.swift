import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var subscriptionManager: SubscriptionManager
    @State private var showSubscription = false
    @State private var showAbout = false
    @State private var exportQuality: ExportQuality = .high
    @State private var autoSaveEnabled = true
    @State private var hapticFeedback = true

    var body: some View {
        NavigationStack {
            ScrollView(.vertical, showsIndicators: false) {
                VStack(spacing: AppTheme.Spacing.lg) {
                    headerSection

                    if !subscriptionManager.isPro {
                        upgradeCard
                    }

                    generalSection
                    exportSection
                    supportSection
                    aboutSection
                }
                .padding(.horizontal, AppTheme.Spacing.md)
                .padding(.bottom, 100)
            }
            .background(AppTheme.Colors.gradientDark.ignoresSafeArea())
            .navigationBarHidden(true)
            .sheet(isPresented: $showSubscription) {
                SubscriptionView()
            }
        }
    }

    private var headerSection: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text("Settings")
                    .font(AppTheme.Typography.title)
                    .foregroundColor(AppTheme.Colors.textPrimary)

                if subscriptionManager.isPro {
                    HStack(spacing: 4) {
                        ProBadge(size: .small)
                        Text("Active")
                            .font(AppTheme.Typography.caption)
                            .foregroundColor(AppTheme.Colors.success)
                    }
                }
            }
            Spacer()
        }
        .padding(.top, AppTheme.Spacing.md)
    }

    private var upgradeCard: some View {
        Button { showSubscription = true } label: {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Upgrade to Pro")
                        .font(AppTheme.Typography.headline)
                        .foregroundColor(.white)
                    Text("Unlock all features")
                        .font(AppTheme.Typography.footnote)
                        .foregroundColor(.white.opacity(0.7))
                }
                Spacer()
                Image(systemName: "crown.fill")
                    .font(.system(size: 24))
                    .foregroundColor(Color(hex: "FDCB6E"))
            }
            .padding(AppTheme.Spacing.md)
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.lg)
                    .fill(AppTheme.Colors.gradientPrimary)
            )
        }
        .buttonStyle(ScaleButtonStyle())
    }

    private var generalSection: some View {
        settingsSection(title: "General") {
            settingsToggle(icon: "square.and.arrow.down", title: "Auto Save", isOn: $autoSaveEnabled)
            settingsToggle(icon: "iphone.radiowaves.left.and.right", title: "Haptic Feedback", isOn: $hapticFeedback)
        }
    }

    private var exportSection: some View {
        settingsSection(title: "Export") {
            VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                Text("Default Quality")
                    .font(AppTheme.Typography.subheadline)
                    .foregroundColor(AppTheme.Colors.textPrimary)

                ForEach(ExportQuality.allCases) { quality in
                    Button {
                        if quality.isPro && !subscriptionManager.isPro {
                            showSubscription = true
                        } else {
                            exportQuality = quality
                        }
                    } label: {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                HStack(spacing: 4) {
                                    Text(quality.rawValue)
                                        .font(AppTheme.Typography.subheadline)
                                        .foregroundColor(AppTheme.Colors.textPrimary)
                                    if quality.isPro {
                                        ProBadge(size: .small)
                                    }
                                }
                                Text(quality.description)
                                    .font(AppTheme.Typography.caption)
                                    .foregroundColor(AppTheme.Colors.textTertiary)
                            }
                            Spacer()
                            if exportQuality == quality {
                                Image(systemName: "checkmark.circle.fill")
                                    .foregroundColor(AppTheme.Colors.primary)
                            }
                        }
                        .padding(.vertical, 6)
                    }
                }
            }
        }
    }

    private var supportSection: some View {
        settingsSection(title: "Support") {
            settingsRow(icon: "envelope", title: "Contact Us", action: {})
            settingsRow(icon: "star", title: "Rate App", action: {})
            settingsRow(icon: "square.and.arrow.up", title: "Share App", action: {})
            settingsRow(icon: "arrow.clockwise", title: "Restore Purchases") {
                Task { await subscriptionManager.restorePurchases() }
            }
        }
    }

    private var aboutSection: some View {
        settingsSection(title: "About") {
            settingsRow(icon: "doc.text", title: "Privacy Policy", action: {})
            settingsRow(icon: "doc.plaintext", title: "Terms of Use", action: {})

            HStack {
                Text("Version")
                    .font(AppTheme.Typography.subheadline)
                    .foregroundColor(AppTheme.Colors.textPrimary)
                Spacer()
                Text("1.0.0")
                    .font(AppTheme.Typography.subheadline)
                    .foregroundColor(AppTheme.Colors.textTertiary)
            }
            .padding(.vertical, 4)
        }
    }

    private func settingsSection(title: String, @ViewBuilder content: () -> some View) -> some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            Text(title)
                .font(AppTheme.Typography.caption)
                .foregroundColor(AppTheme.Colors.textTertiary)
                .textCase(.uppercase)

            GlassCard {
                VStack(spacing: AppTheme.Spacing.sm) {
                    content()
                }
            }
        }
    }

    private func settingsRow(icon: String, title: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack(spacing: AppTheme.Spacing.sm) {
                Image(systemName: icon)
                    .font(.system(size: 16))
                    .foregroundColor(AppTheme.Colors.primary)
                    .frame(width: 24)
                Text(title)
                    .font(AppTheme.Typography.subheadline)
                    .foregroundColor(AppTheme.Colors.textPrimary)
                Spacer()
                Image(systemName: "chevron.right")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundColor(AppTheme.Colors.textTertiary)
            }
            .padding(.vertical, 4)
        }
    }

    private func settingsToggle(icon: String, title: String, isOn: Binding<Bool>) -> some View {
        HStack(spacing: AppTheme.Spacing.sm) {
            Image(systemName: icon)
                .font(.system(size: 16))
                .foregroundColor(AppTheme.Colors.primary)
                .frame(width: 24)
            Text(title)
                .font(AppTheme.Typography.subheadline)
                .foregroundColor(AppTheme.Colors.textPrimary)
            Spacer()
            Toggle("", isOn: isOn)
                .tint(AppTheme.Colors.primary)
                .labelsHidden()
        }
        .padding(.vertical, 2)
    }
}
