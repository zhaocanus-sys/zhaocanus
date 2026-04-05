import SwiftUI

struct ProBadge: View {
    var size: BadgeSize = .regular

    enum BadgeSize {
        case small, regular, large
    }

    private var fontSize: CGFloat {
        switch size {
        case .small: return 9
        case .regular: return 11
        case .large: return 14
        }
    }

    private var hPadding: CGFloat {
        switch size {
        case .small: return 6
        case .regular: return 10
        case .large: return 14
        }
    }

    private var vPadding: CGFloat {
        switch size {
        case .small: return 2
        case .regular: return 4
        case .large: return 6
        }
    }

    var body: some View {
        HStack(spacing: 4) {
            Image(systemName: "crown.fill")
                .font(.system(size: fontSize))
            Text("PRO")
                .font(.system(size: fontSize, weight: .bold, design: .rounded))
        }
        .foregroundColor(.white)
        .padding(.horizontal, hPadding)
        .padding(.vertical, vPadding)
        .background(
            Capsule()
                .fill(AppTheme.Colors.gradientAccent)
        )
        .shadow(color: AppTheme.Colors.accent.opacity(0.3), radius: 8, x: 0, y: 4)
    }
}
