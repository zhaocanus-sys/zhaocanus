import SwiftUI
import PhotosUI

struct BatchProcessingView: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject var subscriptionManager: SubscriptionManager
    @StateObject private var importService = MediaImportService()
    @StateObject private var exportService = ExportService()

    @State private var photoItems: [PhotosPickerItem] = []
    @State private var showPicker = false
    @State private var watermarkText = "AquaMark"
    @State private var fontSize: CGFloat = 24
    @State private var textColor: Color = .white
    @State private var opacity: Double = 0.8
    @State private var position: PositionPreset = .bottomRight
    @State private var isProcessing = false
    @State private var processedCount = 0

    var body: some View {
        NavigationStack {
            ZStack {
                AppTheme.Colors.gradientDark.ignoresSafeArea()

                VStack(spacing: 0) {
                    toolbar
                    ScrollView(.vertical, showsIndicators: false) {
                        VStack(spacing: AppTheme.Spacing.lg) {
                            importSection
                            if !importService.selectedImages.isEmpty {
                                previewGrid
                                settingsSection
                                processButton
                            }
                        }
                        .padding(.horizontal, AppTheme.Spacing.md)
                        .padding(.bottom, AppTheme.Spacing.xxl)
                    }
                }

                if isProcessing {
                    processingOverlay
                }
            }
            .navigationBarHidden(true)
            .photosPicker(
                isPresented: $showPicker,
                selection: $photoItems,
                maxSelectionCount: 100,
                matching: .images
            )
            .onChange(of: photoItems) { newItems in
                Task {
                    await importService.loadImages(from: newItems)
                }
            }
        }
    }

    private var toolbar: some View {
        HStack {
            Button { dismiss() } label: {
                ZStack {
                    Circle()
                        .fill(Color.white.opacity(0.08))
                        .frame(width: 32, height: 32)
                    Image(systemName: "xmark")
                        .font(.system(size: 12, weight: .bold))
                        .foregroundColor(.white.opacity(0.6))
                }
            }
            Spacer()
            Text("Batch Process")
                .font(AppTheme.Typography.headline)
                .foregroundColor(.white)
            Spacer()
            ProBadge(size: .small)
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.vertical, AppTheme.Spacing.xs)
        .padding(.top, 44)
    }

    private var importSection: some View {
        Button { showPicker = true } label: {
            VStack(spacing: AppTheme.Spacing.md) {
                ZStack {
                    Circle()
                        .fill(
                            LinearGradient(
                                colors: [Color(hex: "7C3AED").opacity(0.2), Color(hex: "C084FC").opacity(0.1)],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                        .frame(width: 72, height: 72)

                    Image(systemName: "square.stack.3d.up.fill")
                        .font(.system(size: 30))
                        .foregroundStyle(
                            LinearGradient(colors: [Color(hex: "A78BFA"), Color(hex: "C084FC")], startPoint: .top, endPoint: .bottom)
                        )
                }

                Text(importService.selectedImages.isEmpty ? "Select Photos" : "\(importService.selectedImages.count) photos selected")
                    .font(AppTheme.Typography.headline)
                    .foregroundColor(.white)

                Text("Tap to choose up to 100 photos")
                    .font(AppTheme.Typography.caption)
                    .foregroundColor(AppTheme.Colors.textTertiary)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, AppTheme.Spacing.xl)
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.xl)
                    .fill(.ultraThinMaterial)
                    .overlay(
                        RoundedRectangle(cornerRadius: AppTheme.Radius.xl)
                            .fill(Color.white.opacity(0.04))
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: AppTheme.Radius.xl)
                            .stroke(Color.white.opacity(0.08), lineWidth: 1)
                    )
            )
        }
        .buttonStyle(ScaleButtonStyle())
    }

    private var previewGrid: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            Text("Preview")
                .font(AppTheme.Typography.caption)
                .foregroundColor(AppTheme.Colors.textTertiary)
                .textCase(.uppercase)

            LazyVGrid(
                columns: Array(repeating: GridItem(.flexible(), spacing: 6), count: 4),
                spacing: 6
            ) {
                ForEach(0..<min(importService.selectedImages.count, 8), id: \.self) { index in
                    Image(uiImage: importService.selectedImages[index])
                        .resizable()
                        .scaledToFill()
                        .frame(height: 72)
                        .clipShape(RoundedRectangle(cornerRadius: 10))
                        .overlay(
                            RoundedRectangle(cornerRadius: 10)
                                .stroke(Color.white.opacity(0.08), lineWidth: 1)
                        )
                }
                if importService.selectedImages.count > 8 {
                    ZStack {
                        RoundedRectangle(cornerRadius: 10)
                            .fill(Color.white.opacity(0.06))
                            .frame(height: 72)
                        Text("+\(importService.selectedImages.count - 8)")
                            .font(.system(size: 16, weight: .bold, design: .rounded))
                            .foregroundColor(AppTheme.Colors.textSecondary)
                    }
                }
            }
        }
    }

    private var settingsSection: some View {
        GlassCard {
            VStack(spacing: AppTheme.Spacing.md) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Watermark Text")
                        .font(AppTheme.Typography.caption)
                        .foregroundColor(AppTheme.Colors.textTertiary)
                    TextField("Enter text...", text: $watermarkText)
                        .font(AppTheme.Typography.body)
                        .foregroundColor(.white)
                        .padding(AppTheme.Spacing.sm)
                        .background(
                            RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                                .fill(Color.white.opacity(0.06))
                        )
                }

                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Size: \(Int(fontSize))pt")
                            .font(AppTheme.Typography.caption)
                            .foregroundColor(AppTheme.Colors.textTertiary)
                        Slider(value: $fontSize, in: 12...60, step: 1)
                            .tint(Color(hex: "7C3AED"))
                    }

                    VStack(alignment: .leading, spacing: 4) {
                        Text("Opacity: \(Int(opacity * 100))%")
                            .font(AppTheme.Typography.caption)
                            .foregroundColor(AppTheme.Colors.textTertiary)
                        Slider(value: $opacity, in: 0.1...1.0, step: 0.05)
                            .tint(Color(hex: "06B6D4"))
                    }
                }

                VStack(alignment: .leading, spacing: 6) {
                    Text("Position")
                        .font(AppTheme.Typography.caption)
                        .foregroundColor(AppTheme.Colors.textTertiary)

                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 6) {
                            ForEach([PositionPreset.bottomRight, .bottomLeft, .bottomCenter, .center, .topRight], id: \.self) { preset in
                                Button { position = preset } label: {
                                    Text(preset.label)
                                        .font(.system(size: 11, weight: .medium, design: .rounded))
                                        .foregroundColor(position == preset ? .white : AppTheme.Colors.textSecondary)
                                        .padding(.horizontal, 12)
                                        .padding(.vertical, 7)
                                        .background(
                                            Capsule()
                                                .fill(position == preset ? Color(hex: "7C3AED") : Color.white.opacity(0.06))
                                        )
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    private var processButton: some View {
        Button {
            processAll()
        } label: {
            HStack(spacing: 8) {
                Image(systemName: "bolt.fill")
                    .font(.system(size: 16, weight: .bold))
                Text("Process \(importService.selectedImages.count) Photos")
                    .font(.system(size: 17, weight: .bold, design: .rounded))
            }
            .foregroundColor(.white)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 16)
            .background(
                LinearGradient(colors: [Color(hex: "7C3AED"), Color(hex: "8B7CF6")], startPoint: .topLeading, endPoint: .bottomTrailing)
            )
            .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.md))
            .shadow(color: Color(hex: "7C3AED").opacity(0.35), radius: 12, x: 0, y: 6)
        }
        .buttonStyle(ScaleButtonStyle())
    }

    private var processingOverlay: some View {
        ZStack {
            Color.black.opacity(0.75).ignoresSafeArea()
            VStack(spacing: AppTheme.Spacing.lg) {
                ZStack {
                    Circle()
                        .stroke(Color.white.opacity(0.08), lineWidth: 4)
                        .frame(width: 80, height: 80)
                    Circle()
                        .trim(from: 0, to: Double(processedCount) / Double(max(importService.selectedImages.count, 1)))
                        .stroke(
                            LinearGradient(colors: [Color(hex: "7C3AED"), Color(hex: "A78BFA")], startPoint: .topLeading, endPoint: .bottomTrailing),
                            style: StrokeStyle(lineWidth: 4, lineCap: .round)
                        )
                        .frame(width: 80, height: 80)
                        .rotationEffect(.degrees(-90))

                    Text("\(processedCount)/\(importService.selectedImages.count)")
                        .font(.system(size: 16, weight: .bold, design: .rounded))
                        .foregroundColor(.white)
                }

                Text("Processing...")
                    .font(AppTheme.Typography.headline)
                    .foregroundColor(.white)
            }
            .padding(AppTheme.Spacing.xl)
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.xl)
                    .fill(.ultraThinMaterial)
            )
        }
    }

    private func processAll() {
        guard !importService.selectedImages.isEmpty else { return }
        isProcessing = true
        processedCount = 0

        Task {
            for (index, image) in importService.selectedImages.enumerated() {
                let watermarked = applyWatermark(to: image)
                UIImageWriteToSavedPhotosAlbum(watermarked, nil, nil, nil)
                await MainActor.run {
                    processedCount = index + 1
                }
                try? await Task.sleep(nanoseconds: 100_000_000)
            }
            await MainActor.run {
                isProcessing = false
            }
        }
    }

    private func applyWatermark(to source: UIImage) -> UIImage {
        let renderer = UIGraphicsImageRenderer(size: source.size)
        return renderer.image { ctx in
            source.draw(at: .zero)

            let pos = position.point
            let x = pos.x * source.size.width
            let y = pos.y * source.size.height

            let attributes: [NSAttributedString.Key: Any] = [
                .font: UIFont.systemFont(ofSize: fontSize * 2, weight: .bold),
                .foregroundColor: UIColor(textColor).withAlphaComponent(opacity)
            ]

            let nsText = watermarkText as NSString
            let textSize = nsText.size(withAttributes: attributes)
            let drawPoint = CGPoint(x: x - textSize.width / 2, y: y - textSize.height / 2)
            nsText.draw(at: drawPoint, withAttributes: attributes)
        }
    }
}
