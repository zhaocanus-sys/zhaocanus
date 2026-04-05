import SwiftUI

class ThemeManager: ObservableObject {
    @Published var colorScheme: ColorScheme = .dark
    @AppStorage("userColorScheme") var storedScheme: String = "dark"

    init() {
        colorScheme = storedScheme == "light" ? .light : .dark
    }

    func toggle() {
        withAnimation(.easeInOut(duration: 0.3)) {
            colorScheme = colorScheme == .dark ? .light : .dark
            storedScheme = colorScheme == .dark ? "dark" : "light"
        }
    }
}
