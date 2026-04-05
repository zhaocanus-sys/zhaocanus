import SwiftUI

struct DS {
    // WhatsApp/Discord-inspired clean color palette
    struct Colors {
        // Backgrounds — Discord style deep but not pure black
        static let bg = Color(hex: "1E1F22")
        static let bgSecondary = Color(hex: "2B2D31")
        static let bgTertiary = Color(hex: "313338")
        static let bgFloat = Color(hex: "383A40")

        // Accent — WhatsApp teal-green as primary
        static let accent = Color(hex: "00A884")
        static let accentLight = Color(hex: "25D366")
        static let accentDark = Color(hex: "008069")

        // Secondary accent — Discord blurple
        static let secondary = Color(hex: "5865F2")

        // Text
        static let textPrimary = Color(hex: "F2F3F5")
        static let textSecondary = Color(hex: "B5BAC1")
        static let textMuted = Color(hex: "6D6F78")

        // Status
        static let success = Color(hex: "23A559")
        static let warning = Color(hex: "F0B232")
        static let error = Color(hex: "DA373C")
        static let info = Color(hex: "5865F2")

        // Surface
        static let card = Color(hex: "2B2D31")
        static let cardHover = Color(hex: "36373D")
        static let divider = Color.white.opacity(0.06)

        // Input
        static let inputBg = Color(hex: "1E1F22")
        static let inputBorder = Color(hex: "3F4147")
    }

    struct Fonts {
        static let largeTitle = Font.system(size: 28, weight: .bold, design: .default)
        static let title = Font.system(size: 22, weight: .bold, design: .default)
        static let title2 = Font.system(size: 18, weight: .semibold, design: .default)
        static let headline = Font.system(size: 16, weight: .semibold, design: .default)
        static let body = Font.system(size: 16, weight: .regular, design: .default)
        static let callout = Font.system(size: 14, weight: .regular, design: .default)
        static let footnote = Font.system(size: 13, weight: .regular, design: .default)
        static let caption = Font.system(size: 12, weight: .medium, design: .default)
        static let mono = Font.system(size: 13, weight: .medium, design: .monospaced)
    }

    struct Spacing {
        static let xxs: CGFloat = 2
        static let xs: CGFloat = 4
        static let sm: CGFloat = 8
        static let md: CGFloat = 12
        static let lg: CGFloat = 16
        static let xl: CGFloat = 20
        static let xxl: CGFloat = 28
        static let xxxl: CGFloat = 40
    }

    struct Radius {
        static let xs: CGFloat = 4
        static let sm: CGFloat = 8
        static let md: CGFloat = 12
        static let lg: CGFloat = 16
        static let xl: CGFloat = 20
        static let pill: CGFloat = 999
    }
}

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3: (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6: (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8: (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default: (a, r, g, b) = (255, 0, 0, 0)
        }
        self.init(.sRGB, red: Double(r) / 255, green: Double(g) / 255, blue: Double(b) / 255, opacity: Double(a) / 255)
    }
}
