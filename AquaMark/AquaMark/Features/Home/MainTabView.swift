import SwiftUI

struct MainTabView: View {
    @State private var selectedTab: Tab = .home
    @EnvironmentObject var subscriptionManager: SubscriptionManager

    enum Tab: String, CaseIterable {
        case home = "Home"
        case create = "Create"
        case settings = "Settings"

        var icon: String {
            switch self {
            case .home: return "house.fill"
            case .create: return "plus.circle.fill"
            case .settings: return "gearshape.fill"
            }
        }
    }

    var body: some View {
        ZStack(alignment: .bottom) {
            Group {
                switch selectedTab {
                case .home:
                    HomeView()
                case .create:
                    CreateView()
                case .settings:
                    SettingsView()
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)

            customTabBar
        }
        .background(AppTheme.Colors.gradientDark.ignoresSafeArea())
    }

    private var customTabBar: some View {
        HStack(spacing: 0) {
            ForEach(Tab.allCases, id: \.self) { tab in
                Button {
                    withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                        selectedTab = tab
                    }
                } label: {
                    VStack(spacing: 4) {
                        Image(systemName: tab.icon)
                            .font(.system(size: tab == .create ? 28 : 22, weight: .semibold))
                            .foregroundColor(selectedTab == tab ? AppTheme.Colors.primary : AppTheme.Colors.textTertiary)
                            .scaleEffect(selectedTab == tab ? 1.1 : 1.0)

                        if tab != .create {
                            Text(tab.rawValue)
                                .font(.system(size: 10, weight: .medium, design: .rounded))
                                .foregroundColor(selectedTab == tab ? AppTheme.Colors.primary : AppTheme.Colors.textTertiary)
                        }
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.top, 10)
                    .padding(.bottom, 4)
                }
            }
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.bottom, 20)
        .background(
            Rectangle()
                .fill(.ultraThinMaterial)
                .overlay(
                    Rectangle()
                        .fill(Color.black.opacity(0.4))
                )
                .overlay(
                    Rectangle()
                        .frame(height: 0.5)
                        .foregroundColor(AppTheme.Colors.glassBorder),
                    alignment: .top
                )
                .ignoresSafeArea(edges: .bottom)
        )
    }
}
