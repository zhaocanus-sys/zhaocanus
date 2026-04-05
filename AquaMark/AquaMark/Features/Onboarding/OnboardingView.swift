import SwiftUI

struct OnboardingView: View {
    @Binding var hasCompletedOnboarding: Bool
    @EnvironmentObject var subscriptionManager: SubscriptionManager
    @State private var currentPage = 0
    @State private var showSubscription = false

    private let pages: [(icon: String, title: String, subtitle: String, gradient: [Color])] = [
        (
            "drop.fill",
            "AquaMark",
            "Professional watermark studio for creators.\nProtect your content with beautiful marks.",
            [Color(hex: "6C5CE7"), Color(hex: "A29BFE")]
        ),
        (
            "photo.badge.plus",
            "Photos & Videos",
            "Add text, logos, timestamps, and signatures\nto any media with precision controls.",
            [Color(hex: "00CEC9"), Color(hex: "81ECEC")]
        ),
        (
            "wand.and.stars",
            "Smart Tools",
            "Crop, compress, modify fingerprints.\nEverything you need in one app.",
            [Color(hex: "FD79A8"), Color(hex: "FDCB6E")]
        ),
        (
            "crown.fill",
            "Go Pro",
            "Unlock 4K exports, batch processing,\nand unlimited creative power.",
            [Color(hex: "D980FA"), Color(hex: "F8A5C2")]
        )
    ]

    var body: some View {
        ZStack {
            AppTheme.Colors.gradientDark.ignoresSafeArea()

            VStack(spacing: 0) {
                TabView(selection: $currentPage) {
                    ForEach(0..<pages.count, id: \.self) { index in
                        onboardingPage(pages[index])
                            .tag(index)
                    }
                }
                .tabViewStyle(.page(indexDisplayMode: .never))

                bottomSection
            }
        }
        .sheet(isPresented: $showSubscription) {
            SubscriptionView()
        }
    }

    private func onboardingPage(_ page: (icon: String, title: String, subtitle: String, gradient: [Color])) -> some View {
        VStack(spacing: AppTheme.Spacing.xl) {
            Spacer()

            ZStack {
                Circle()
                    .fill(
                        LinearGradient(
                            colors: page.gradient,
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
                    .frame(width: 120, height: 120)
                    .shadow(color: page.gradient[0].opacity(0.4), radius: 30)
                    .blur(radius: 1)

                Image(systemName: page.icon)
                    .font(.system(size: 50, weight: .medium))
                    .foregroundColor(.white)
            }

            VStack(spacing: AppTheme.Spacing.sm) {
                Text(page.title)
                    .font(AppTheme.Typography.largeTitle)
                    .foregroundColor(.white)

                Text(page.subtitle)
                    .font(AppTheme.Typography.body)
                    .foregroundColor(AppTheme.Colors.textSecondary)
                    .multilineTextAlignment(.center)
                    .lineSpacing(4)
            }

            Spacer()
            Spacer()
        }
        .padding(.horizontal, AppTheme.Spacing.xl)
    }

    private var bottomSection: some View {
        VStack(spacing: AppTheme.Spacing.md) {
            pageIndicator

            if currentPage == pages.count - 1 {
                VStack(spacing: AppTheme.Spacing.sm) {
                    Button {
                        showSubscription = true
                    } label: {
                        HStack(spacing: 8) {
                            Image(systemName: "crown.fill")
                            Text("Start Free Trial")
                                .font(.system(size: 18, weight: .bold, design: .rounded))
                        }
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 16)
                        .background(AppTheme.Colors.gradientPrimary)
                        .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.md))
                        .shadow(color: AppTheme.Colors.primary.opacity(0.4), radius: 12)
                    }
                    .buttonStyle(ScaleButtonStyle())

                    Button {
                        withAnimation {
                            hasCompletedOnboarding = true
                        }
                    } label: {
                        Text("Continue with Free")
                            .font(AppTheme.Typography.subheadline)
                            .foregroundColor(AppTheme.Colors.textTertiary)
                    }
                }
            } else {
                Button {
                    withAnimation(.spring(response: 0.4, dampingFraction: 0.8)) {
                        currentPage += 1
                    }
                } label: {
                    HStack(spacing: 8) {
                        Text("Continue")
                            .font(.system(size: 18, weight: .bold, design: .rounded))
                        Image(systemName: "arrow.right")
                            .font(.system(size: 16, weight: .bold))
                    }
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 16)
                    .background(AppTheme.Colors.gradientPrimary)
                    .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.md))
                }
                .buttonStyle(ScaleButtonStyle())
            }
        }
        .padding(.horizontal, AppTheme.Spacing.xl)
        .padding(.bottom, AppTheme.Spacing.xxl)
    }

    private var pageIndicator: some View {
        HStack(spacing: 8) {
            ForEach(0..<pages.count, id: \.self) { index in
                Capsule()
                    .fill(index == currentPage ? AppTheme.Colors.primary : AppTheme.Colors.textTertiary)
                    .frame(width: index == currentPage ? 24 : 8, height: 8)
                    .animation(.spring(response: 0.3, dampingFraction: 0.7), value: currentPage)
            }
        }
    }
}
