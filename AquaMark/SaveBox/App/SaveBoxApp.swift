import SwiftUI

@main
struct SaveBoxApp: App {
    @StateObject private var l10n = L10n()
    @StateObject private var engine = VideoDownloadEngine()

    var body: some Scene {
        WindowGroup {
            MainTabView()
                .environmentObject(l10n)
                .environmentObject(engine)
                .preferredColorScheme(.dark)
        }
    }
}
