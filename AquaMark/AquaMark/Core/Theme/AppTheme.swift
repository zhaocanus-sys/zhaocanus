import SwiftUI

// MARK: - Design System (International A-tier standard)

struct AppTheme {
    // MARK: Colors
    struct Colors {
        static let background = Color("Background")
        static let surface = Color("Surface")
        static let surfaceElevated = Color("SurfaceElevated")

        static let primary = Color(hex: "6C5CE7")
        static let primaryLight = Color(hex: "A29BFE")
        static let secondary = Color(hex: "00CEC9")
        static let accent = Color(hex: "FD79A8")

        static let textPrimary = Color.white
        static let textSecondary = Color.white.opacity(0.7)
        static let textTertiary = Color.white.opacity(0.45)

        static let destructive = Color(hex: "FF6B6B")
        static let success = Color(hex: "51CF66")
        static let warning = Color(hex: "FFD43B")

        static let gradientPrimary = LinearGradient(
            colors: [Color(hex: "6C5CE7"), Color(hex: "A29BFE")],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
        static let gradientAccent = LinearGradient(
            colors: [Color(hex: "FD79A8"), Color(hex: "FDCB6E")],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
        static let gradientDark = LinearGradient(
            colors: [Color(hex: "0A0A0F"), Color(hex: "1A1A2E")],
            startPoint: .top,
            endPoint: .bottom
        )

        static let glassFill = Color.white.opacity(0.08)
        static let glassBorder = Color.white.opacity(0.12)
    }

    // MARK: Typography
    struct Typography {
        static let largeTitle = Font.system(size: 34, weight: .bold, design: .rounded)
        static let title = Font.system(size: 28, weight: .bold, design: .rounded)
        static let title2 = Font.system(size: 22, weight: .semibold, design: .rounded)
        static let title3 = Font.system(size: 20, weight: .semibold, design: .rounded)
        static let headline = Font.system(size: 17, weight: .semibold, design: .rounded)
        static let body = Font.system(size: 17, weight: .regular, design: .rounded)
        static let callout = Font.system(size: 16, weight: .regular, design: .rounded)
        static let subheadline = Font.system(size: 15, weight: .regular, design: .rounded)
        static let footnote = Font.system(size: 13, weight: .regular, design: .rounded)
        static let caption = Font.system(size: 12, weight: .medium, design: .rounded)
    }

    // MARK: Spacing
    struct Spacing {
        static let xxs: CGFloat = 4
        static let xs: CGFloat = 8
        static let sm: CGFloat = 12
        static let md: CGFloat = 16
        static let lg: CGFloat = 24
        static let xl: CGFloat = 32
        static let xxl: CGFloat = 48
    }

    // MARK: Radius
    struct Radius {
        static let sm: CGFloat = 8
        static let md: CGFloat = 12
        static let lg: CGFloat = 16
        static let xl: CGFloat = 24
        static let full: CGFloat = 999
    }

    // MARK: Shadows
    struct Shadows {
        static let small = Shadow(color: .black.opacity(0.15), radius: 4, x: 0, y: 2)
        static let medium = Shadow(color: .black.opacity(0.2), radius: 8, x: 0, y: 4)
        static let large = Shadow(color: .black.opacity(0.3), radius: 16, x: 0, y: 8)
        static let glow = Shadow(color: Colors.primary.opacity(0.3), radius: 20, x: 0, y: 0)
    }

    struct Shadow {
        let color: Color
        let radius: CGFloat
        let x: CGFloat
        let y: CGFloat
    }
}

// MARK: - Color Hex Extension

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3:
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6:
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8:
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (255, 0, 0, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue: Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}
