import SwiftUI

struct PhotoWatermarkView: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject var subscriptionManager: SubscriptionManager
    @StateObject private var viewModel = PhotoWatermarkViewModel()
    @State private var selectedTool: WatermarkToolTab = .text
    @State private var showExport = false

    enum WatermarkToolTab: String, CaseIterable {
        case text = "Text"
        case image = "Image"
        case timestamp = "Time"
        case style = "Style"
        case position = "Position"

        var icon: String {
            switch self {
            case .text: return "textformat"
            case .image: return "photo"
            case .timestamp: return "clock"
            case .style: return "paintbrush"
            case .position: return "move.3d"
            }
        }
    }

    var body: some View {
        NavigationStack {
            ZStack {
                AppTheme.Colors.gradientDark.ignoresSafeArea()

                VStack(spacing: 0) {
                    toolbar
                    canvasArea
                    toolSelector
                    toolPanel
                }
            }
            .navigationBarHidden(true)
        }
    }

    // MARK: - Toolbar

    private var toolbar: some View {
        HStack {
            Button {
                dismiss()
            } label: {
                Image(systemName: "xmark.circle.fill")
                    .font(.system(size: 28))
                    .foregroundStyle(.white.opacity(0.6))
            }

            Spacer()

            Text("Photo Watermark")
                .font(AppTheme.Typography.headline)
                .foregroundColor(AppTheme.Colors.textPrimary)

            Spacer()

            Button {
                showExport = true
            } label: {
                HStack(spacing: 4) {
                    Image(systemName: "square.and.arrow.up")
                    Text("Export")
                }
                .font(AppTheme.Typography.subheadline)
                .foregroundColor(.white)
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(AppTheme.Colors.gradientPrimary)
                .clipShape(Capsule())
            }
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.vertical, AppTheme.Spacing.xs)
    }

    // MARK: - Canvas

    private var canvasArea: some View {
        GeometryReader { geometry in
            ZStack {
                RoundedRectangle(cornerRadius: AppTheme.Radius.lg)
                    .fill(Color.black.opacity(0.3))
                    .overlay(
                        RoundedRectangle(cornerRadius: AppTheme.Radius.lg)
                            .stroke(AppTheme.Colors.glassBorder, lineWidth: 1)
                    )

                if viewModel.sourceImage != nil {
                    Image(uiImage: viewModel.sourceImage!)
                        .resizable()
                        .scaledToFit()
                        .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.md))
                        .overlay(
                            watermarkOverlay
                        )
                } else {
                    placeholderCanvas
                }
            }
            .padding(AppTheme.Spacing.md)
        }
        .frame(maxHeight: .infinity)
    }

    private var placeholderCanvas: some View {
        VStack(spacing: AppTheme.Spacing.md) {
            Image(systemName: "photo.badge.plus")
                .font(.system(size: 48))
                .foregroundStyle(AppTheme.Colors.gradientPrimary)

            Text("Tap to select a photo")
                .font(AppTheme.Typography.headline)
                .foregroundColor(AppTheme.Colors.textSecondary)

            Text("or drag & drop an image here")
                .font(AppTheme.Typography.caption)
                .foregroundColor(AppTheme.Colors.textTertiary)
        }
    }

    private var watermarkOverlay: some View {
        GeometryReader { geo in
            ForEach(viewModel.watermarks) { watermark in
                WatermarkItemView(item: watermark)
                    .position(
                        x: watermark.position.x * geo.size.width,
                        y: watermark.position.y * geo.size.height
                    )
            }
        }
    }

    // MARK: - Tool Selector

    private var toolSelector: some View {
        HStack(spacing: 0) {
            ForEach(WatermarkToolTab.allCases, id: \.self) { tab in
                Button {
                    withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                        selectedTool = tab
                    }
                } label: {
                    VStack(spacing: 4) {
                        Image(systemName: tab.icon)
                            .font(.system(size: 18, weight: .medium))
                        Text(tab.rawValue)
                            .font(.system(size: 10, weight: .medium, design: .rounded))
                    }
                    .foregroundColor(selectedTool == tab ? AppTheme.Colors.primary : AppTheme.Colors.textTertiary)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 10)
                    .background(
                        selectedTool == tab
                            ? RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                                .fill(AppTheme.Colors.primary.opacity(0.15))
                            : nil
                    )
                }
            }
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.vertical, AppTheme.Spacing.xs)
        .background(
            Rectangle()
                .fill(.ultraThinMaterial)
                .overlay(Rectangle().fill(Color.black.opacity(0.3)))
        )
    }

    // MARK: - Tool Panel

    private var toolPanel: some View {
        GlassCard(padding: AppTheme.Spacing.md, cornerRadius: 0) {
            VStack(spacing: AppTheme.Spacing.sm) {
                switch selectedTool {
                case .text:
                    textToolPanel
                case .image:
                    imageToolPanel
                case .timestamp:
                    timestampToolPanel
                case .style:
                    styleToolPanel
                case .position:
                    positionToolPanel
                }
            }
        }
        .frame(height: 160)
    }

    private var textToolPanel: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            HStack {
                Text("Text")
                    .font(AppTheme.Typography.caption)
                    .foregroundColor(AppTheme.Colors.textTertiary)
                Spacer()
            }

            TextField("Enter watermark text...", text: $viewModel.currentText)
                .font(AppTheme.Typography.body)
                .foregroundColor(.white)
                .padding(AppTheme.Spacing.sm)
                .background(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                        .fill(Color.white.opacity(0.08))
                )

            HStack(spacing: AppTheme.Spacing.sm) {
                fontSizeSlider
                addButton(title: "Add Text", icon: "plus.circle.fill") {
                    viewModel.addTextWatermark()
                }
            }
        }
    }

    private var fontSizeSlider: some View {
        HStack(spacing: 8) {
            Image(systemName: "textformat.size.smaller")
                .font(.system(size: 12))
                .foregroundColor(AppTheme.Colors.textTertiary)
            Slider(value: $viewModel.fontSize, in: 12...72, step: 1)
                .tint(AppTheme.Colors.primary)
            Image(systemName: "textformat.size.larger")
                .font(.system(size: 14))
                .foregroundColor(AppTheme.Colors.textTertiary)
        }
    }

    private var imageToolPanel: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            Text("Logo / Image Watermark")
                .font(AppTheme.Typography.caption)
                .foregroundColor(AppTheme.Colors.textTertiary)
                .frame(maxWidth: .infinity, alignment: .leading)

            GlassButton(title: "Choose Logo", icon: "photo.on.rectangle", action: {})
        }
    }

    private var timestampToolPanel: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            Text("Timestamp Format")
                .font(AppTheme.Typography.caption)
                .foregroundColor(AppTheme.Colors.textTertiary)
                .frame(maxWidth: .infinity, alignment: .leading)

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(["yyyy-MM-dd", "MM/dd/yyyy", "dd.MM.yyyy", "yyyy-MM-dd HH:mm"], id: \.self) { format in
                        Button {
                            viewModel.dateFormat = format
                        } label: {
                            Text(format)
                                .font(AppTheme.Typography.caption)
                                .foregroundColor(viewModel.dateFormat == format ? .white : AppTheme.Colors.textSecondary)
                                .padding(.horizontal, 12)
                                .padding(.vertical, 8)
                                .background(
                                    Capsule()
                                        .fill(viewModel.dateFormat == format ? AppTheme.Colors.primary : Color.white.opacity(0.08))
                                )
                        }
                    }
                }
            }

            addButton(title: "Add Timestamp", icon: "clock.badge.checkmark") {
                viewModel.addTimestampWatermark()
            }
        }
    }

    private var styleToolPanel: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            HStack {
                Text("Opacity")
                    .font(AppTheme.Typography.caption)
                    .foregroundColor(AppTheme.Colors.textTertiary)
                Spacer()
                Text("\(Int(viewModel.opacity * 100))%")
                    .font(AppTheme.Typography.caption)
                    .foregroundColor(AppTheme.Colors.textSecondary)
            }
            Slider(value: $viewModel.opacity, in: 0.1...1.0, step: 0.05)
                .tint(AppTheme.Colors.primary)

            colorPicker
        }
    }

    private var colorPicker: some View {
        HStack(spacing: 8) {
            Text("Color")
                .font(AppTheme.Typography.caption)
                .foregroundColor(AppTheme.Colors.textTertiary)
            Spacer()
            ForEach([Color.white, Color.black, AppTheme.Colors.primary, AppTheme.Colors.accent, Color(hex: "FDCB6E")], id: \.self) { color in
                Button {
                    viewModel.textColor = color
                } label: {
                    Circle()
                        .fill(color)
                        .frame(width: 28, height: 28)
                        .overlay(
                            Circle()
                                .stroke(viewModel.textColor == color ? AppTheme.Colors.primary : Color.clear, lineWidth: 2)
                                .padding(1)
                        )
                }
            }
        }
    }

    private var positionToolPanel: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            Text("Position Presets")
                .font(AppTheme.Typography.caption)
                .foregroundColor(AppTheme.Colors.textTertiary)
                .frame(maxWidth: .infinity, alignment: .leading)

            LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 8), count: 3), spacing: 8) {
                ForEach(PositionPreset.allCases) { preset in
                    Button {
                        viewModel.applyPositionPreset(preset)
                    } label: {
                        Text(preset.label)
                            .font(.system(size: 11, weight: .medium, design: .rounded))
                            .foregroundColor(AppTheme.Colors.textSecondary)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 8)
                            .background(
                                RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                                    .fill(Color.white.opacity(0.06))
                            )
                    }
                }
            }
        }
    }

    private func addButton(title: String, icon: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                Text(title)
            }
            .font(AppTheme.Typography.subheadline)
            .foregroundColor(.white)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 10)
            .background(AppTheme.Colors.gradientPrimary)
            .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.sm))
        }
        .buttonStyle(ScaleButtonStyle())
    }
}

// MARK: - Watermark Item View

struct WatermarkItemView: View {
    let item: WatermarkItem

    var body: some View {
        Group {
            switch item.type {
            case .text, .timestamp:
                Text(displayText)
                    .font(.system(size: item.fontSize, weight: .semibold, design: .rounded))
                    .foregroundColor(item.textColor)
                    .shadow(color: .black.opacity(item.textShadow ? 0.5 : 0), radius: 2, x: 1, y: 1)
            case .image:
                if let data = item.imageData, let uiImage = UIImage(data: data) {
                    Image(uiImage: uiImage)
                        .resizable()
                        .scaledToFit()
                        .frame(width: 80, height: 80)
                }
            case .signature:
                Text(item.text)
                    .font(.system(size: item.fontSize, design: .serif))
                    .italic()
                    .foregroundColor(item.textColor)
            }
        }
        .opacity(item.opacity)
        .rotationEffect(item.rotation)
        .scaleEffect(item.scale)
    }

    private var displayText: String {
        if item.type == .timestamp {
            let formatter = DateFormatter()
            formatter.dateFormat = item.dateFormat
            return formatter.string(from: Date())
        }
        return item.text
    }
}

// MARK: - Position Presets

enum PositionPreset: String, CaseIterable, Identifiable {
    case topLeft = "Top Left"
    case topCenter = "Top Center"
    case topRight = "Top Right"
    case centerLeft = "Center Left"
    case center = "Center"
    case centerRight = "Center Right"
    case bottomLeft = "Bottom Left"
    case bottomCenter = "Bottom Center"
    case bottomRight = "Bottom Right"

    var id: String { rawValue }
    var label: String { rawValue }

    var point: CGPoint {
        switch self {
        case .topLeft: return CGPoint(x: 0.15, y: 0.1)
        case .topCenter: return CGPoint(x: 0.5, y: 0.1)
        case .topRight: return CGPoint(x: 0.85, y: 0.1)
        case .centerLeft: return CGPoint(x: 0.15, y: 0.5)
        case .center: return CGPoint(x: 0.5, y: 0.5)
        case .centerRight: return CGPoint(x: 0.85, y: 0.5)
        case .bottomLeft: return CGPoint(x: 0.15, y: 0.9)
        case .bottomCenter: return CGPoint(x: 0.5, y: 0.9)
        case .bottomRight: return CGPoint(x: 0.85, y: 0.9)
        }
    }
}
