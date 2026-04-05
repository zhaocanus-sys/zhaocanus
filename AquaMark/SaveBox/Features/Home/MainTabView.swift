import SwiftUI

struct MainTabView: View {
    @EnvironmentObject var l10n: L10n
    @State private var selectedTab = 0

    var body: some View {
        TabView(selection: $selectedTab) {
            HomeView()
                .tabItem {
                    Image(systemName: selectedTab == 0 ? "arrow.down.circle.fill" : "arrow.down.circle")
                    Text(l10n.tabHome)
                }
                .tag(0)

            LibraryView()
                .tabItem {
                    Image(systemName: selectedTab == 1 ? "folder.fill" : "folder")
                    Text(l10n.tabLibrary)
                }
                .tag(1)

            SettingsView()
                .tabItem {
                    Image(systemName: selectedTab == 2 ? "gearshape.fill" : "gearshape")
                    Text(l10n.tabSettings)
                }
                .tag(2)
        }
        .tint(DS.Colors.accent)
        .onAppear {
            let appearance = UITabBarAppearance()
            appearance.configureWithOpaqueBackground()
            appearance.backgroundColor = UIColor(DS.Colors.bg)
            UITabBar.appearance().standardAppearance = appearance
            UITabBar.appearance().scrollEdgeAppearance = appearance
        }
    }
}
