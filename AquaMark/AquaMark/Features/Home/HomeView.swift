import SwiftUI

struct HomeView: View {
    @EnvironmentObject var subscriptionManager: SubscriptionManager
    @State private var showSubscription = false
    @Namespace private var heroAnimation

    private let columns = [
        GridItem(.flexible(), spacing: AppTheme.Spacing.sm),
        GridItem(.flexible(), spacing: AppTheme.Spacing.sm)
    ]

    var body: some View {
        NavigationStack {
            ScrollView(.vertical, showsIndicators: false) {
                VStack(spacing: AppTheme.Spacing.lg) {
                    headerSection
                    if !subscriptionManager.isPro {
                        proPromoBanner
                    }
                    toolsGrid
                    recentSection
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

    // MARK: - Header

    private var headerSection: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text("AquaMark")
                    .font(AppTheme.Typography.title)
                    .foregroundColor(AppTheme.Colors.textPrimary)

                Text("Professional Watermark Studio")
                    .font(AppTheme.Typography.subheadline)
                    .foregroundColor(AppTheme.Colors.textSecondary)
            }

            Spacer()

            if subscriptionManager.isPro {
                ProBadge(size: .regular)
            }
        }
        .padding(.top, AppTheme.Spacing.md)
    }

    // MARK: - Pro Banner

    private var proPromoBanner: some View {
        Button {
            showSubscription = true
        } label: {
            HStack(spacing: AppTheme.Spacing.md) {
                VStack(alignment: .leading, spacing: 6) {
                    HStack(spacing: 6) {
                        Image(systemName: "crown.fill")
                            .foregroundColor(Color(hex: "FDCB6E"))
                        Text("Unlock Pro")
                            .font(AppTheme.Typography.headline)
                            .foregroundColor(.white)
                    }

                    Text("Unlimited exports, 4K quality, batch processing & more")
                        .font(AppTheme.Typography.caption)
                        .foregroundColor(.white.opacity(0.7))
                        .lineLimit(2)
                }

                Spacer()

                Image(systemName: "chevron.right.circle.fill")
                    .font(.system(size: 24))
                    .foregroundColor(.white.opacity(0.8))
            }
            .padding(AppTheme.Spacing.md)
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.lg)
                    .fill(
                        LinearGradient(
                            colors: [
                                Color(hex: "6C5CE7"),
                                Color(hex: "A29BFE"),
                                Color(hex: "FD79A8")
                            ],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
            )
            .overlay(
                RoundedRectangle(cornerRadius: AppTheme.Radius.lg)
                    .stroke(Color.white.opacity(0.2), lineWidth: 1)
            )
        }
        .buttonStyle(ScaleButtonStyle())
    }

    // MARK: - Tools Grid

    private var toolsGrid: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            Text("Tools")
                .font(AppTheme.Typography.title2)
                .foregroundColor(AppTheme.Colors.textPrimary)

            LazyVGrid(columns: columns, spacing: AppTheme.Spacing.sm) {
                ForEach(ToolType.allCases) { tool in
                    ToolCard(
                        icon: tool.icon,
                        title: tool.rawValue,
                        subtitle: tool.subtitle,
                        gradient: tool.gradientColors,
                        action: {
                            if tool.isPro && !subscriptionManager.isPro {
                                showSubscription = true
                            }
                        },
                        isPro: tool.isPro
                    )
                }
            }
        }
    }

    // MARK: - Recent Projects

    private var recentSection: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            HStack {
                Text("Recent")
                    .font(AppTheme.Typography.title2)
                    .foregroundColor(AppTheme.Colors.textPrimary)
                Spacer()
                Button("See All") {}
                    .font(AppTheme.Typography.subheadline)
                    .foregroundColor(AppTheme.Colors.primary)
            }

            emptyRecentState
        }
    }

    private var emptyRecentState: some View {
        GlassCard {
            VStack(spacing: AppTheme.Spacing.md) {
                Image(systemName: "sparkles")
                    .font(.system(size: 40))
                    .foregroundStyle(AppTheme.Colors.gradientPrimary)

                Text("No recent projects")
                    .font(AppTheme.Typography.headline)
                    .foregroundColor(AppTheme.Colors.textSecondary)

                Text("Start creating to see your work here")
                    .font(AppTheme.Typography.footnote)
                    .foregroundColor(AppTheme.Colors.textTertiary)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, AppTheme.Spacing.xl)
        }
    }
}
