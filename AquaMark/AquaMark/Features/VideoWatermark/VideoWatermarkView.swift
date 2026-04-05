import SwiftUI
import AVKit

struct VideoWatermarkView: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject var subscriptionManager: SubscriptionManager
    @StateObject private var viewModel = VideoWatermarkViewModel()
    @State private var selectedTool: VideoToolTab = .watermark
    @State private var isExporting = false

    enum VideoToolTab: String, CaseIterable {
        case watermark = "Watermark"
        case crop = "Crop"
        case compress = "Compress"
        case md5 = "MD5"

        var icon: String {
            switch self {
            case .watermark: return "textformat"
            case .crop: return "crop"
            case .compress: return "arrow.down.right.and.arrow.up.left"
            case .md5: return "number.circle"
            }
        }
    }

    var body: some View {
        NavigationStack {
            ZStack {
                AppTheme.Colors.gradientDark.ignoresSafeArea()

                VStack(spacing: 0) {
                    toolbar
                    videoPreview
                    timelineBar
                    toolSelector
                    toolPanel
                }

                if isExporting {
                    exportOverlay
                }
            }
            .navigationBarHidden(true)
        }
    }

    private var toolbar: some View {
        HStack {
            Button { dismiss() } label: {
                Image(systemName: "xmark.circle.fill")
                    .font(.system(size: 28))
                    .foregroundStyle(.white.opacity(0.6))
            }

            Spacer()

            Text("Video Editor")
                .font(AppTheme.Typography.headline)
                .foregroundColor(AppTheme.Colors.textPrimary)

            Spacer()

            Button {
                isExporting = true
                viewModel.exportVideo { _ in
                    isExporting = false
                }
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

    private var videoPreview: some View {
        ZStack {
            RoundedRectangle(cornerRadius: AppTheme.Radius.lg)
                .fill(Color.black.opacity(0.4))
                .overlay(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.lg)
                        .stroke(AppTheme.Colors.glassBorder, lineWidth: 1)
                )

            if viewModel.videoURL != nil {
                VideoPlayer(player: viewModel.player)
                    .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.md))
            } else {
                VStack(spacing: AppTheme.Spacing.md) {
                    Image(systemName: "video.badge.plus")
                        .font(.system(size: 48))
                        .foregroundStyle(AppTheme.Colors.gradientPrimary)
                    Text("Tap to select a video")
                        .font(AppTheme.Typography.headline)
                        .foregroundColor(AppTheme.Colors.textSecondary)
                }
            }
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .frame(maxHeight: .infinity)
    }

    private var timelineBar: some View {
        VStack(spacing: 8) {
            HStack {
                Text(viewModel.formattedCurrentTime)
                    .font(.system(size: 12, weight: .medium, design: .monospaced))
                    .foregroundColor(AppTheme.Colors.textSecondary)
                Spacer()
                Text(viewModel.formattedDuration)
                    .font(.system(size: 12, weight: .medium, design: .monospaced))
                    .foregroundColor(AppTheme.Colors.textSecondary)
            }
            .padding(.horizontal, AppTheme.Spacing.md)

            Slider(value: $viewModel.currentProgress, in: 0...1)
                .tint(AppTheme.Colors.primary)
                .padding(.horizontal, AppTheme.Spacing.md)

            HStack(spacing: AppTheme.Spacing.xl) {
                playbackButton(icon: "gobackward.10", action: viewModel.seekBackward)
                playbackButton(
                    icon: viewModel.isPlaying ? "pause.fill" : "play.fill",
                    size: 22,
                    action: viewModel.togglePlayPause
                )
                playbackButton(icon: "goforward.10", action: viewModel.seekForward)
            }
            .padding(.vertical, 4)
        }
    }

    private func playbackButton(icon: String, size: CGFloat = 16, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: icon)
                .font(.system(size: size, weight: .semibold))
                .foregroundColor(AppTheme.Colors.textPrimary)
                .frame(width: 44, height: 44)
        }
    }

    private var toolSelector: some View {
        HStack(spacing: 0) {
            ForEach(VideoToolTab.allCases, id: \.self) { tab in
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
                }
            }
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .background(
            Rectangle()
                .fill(.ultraThinMaterial)
                .overlay(Rectangle().fill(Color.black.opacity(0.3)))
        )
    }

    private var toolPanel: some View {
        GlassCard(padding: AppTheme.Spacing.md, cornerRadius: 0) {
            switch selectedTool {
            case .watermark:
                watermarkPanel
            case .crop:
                cropPanel
            case .compress:
                compressPanel
            case .md5:
                md5Panel
            }
        }
        .frame(height: 140)
    }

    private var watermarkPanel: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            TextField("Watermark text...", text: $viewModel.watermarkText)
                .font(AppTheme.Typography.body)
                .foregroundColor(.white)
                .padding(AppTheme.Spacing.sm)
                .background(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                        .fill(Color.white.opacity(0.08))
                )

            HStack(spacing: AppTheme.Spacing.sm) {
                HStack(spacing: 8) {
                    Text("Size")
                        .font(AppTheme.Typography.caption)
                        .foregroundColor(AppTheme.Colors.textTertiary)
                    Slider(value: $viewModel.watermarkFontSize, in: 12...60, step: 1)
                        .tint(AppTheme.Colors.primary)
                }

                HStack(spacing: 8) {
                    Text("Opacity")
                        .font(AppTheme.Typography.caption)
                        .foregroundColor(AppTheme.Colors.textTertiary)
                    Slider(value: $viewModel.watermarkOpacity, in: 0.1...1, step: 0.05)
                        .tint(AppTheme.Colors.secondary)
                }
            }
        }
    }

    private var cropPanel: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            Text("Aspect Ratio")
                .font(AppTheme.Typography.caption)
                .foregroundColor(AppTheme.Colors.textTertiary)
                .frame(maxWidth: .infinity, alignment: .leading)

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(["Free", "1:1", "4:3", "16:9", "9:16", "3:4"], id: \.self) { ratio in
                        Button {
                            viewModel.selectedAspectRatio = ratio
                        } label: {
                            Text(ratio)
                                .font(AppTheme.Typography.caption)
                                .foregroundColor(viewModel.selectedAspectRatio == ratio ? .white : AppTheme.Colors.textSecondary)
                                .padding(.horizontal, 16)
                                .padding(.vertical, 8)
                                .background(
                                    Capsule()
                                        .fill(viewModel.selectedAspectRatio == ratio ? AppTheme.Colors.primary : Color.white.opacity(0.08))
                                )
                        }
                    }
                }
            }
        }
    }

    private var compressPanel: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            HStack {
                Text("Quality")
                    .font(AppTheme.Typography.caption)
                    .foregroundColor(AppTheme.Colors.textTertiary)
                Spacer()
                Text("\(Int(viewModel.compressionQuality * 100))%")
                    .font(AppTheme.Typography.caption)
                    .foregroundColor(AppTheme.Colors.primary)
            }
            Slider(value: $viewModel.compressionQuality, in: 0.1...1.0, step: 0.05)
                .tint(AppTheme.Colors.primary)

            HStack {
                Label("Estimated size: \(viewModel.estimatedFileSize)", systemImage: "internaldrive")
                    .font(AppTheme.Typography.caption)
                    .foregroundColor(AppTheme.Colors.textSecondary)
                Spacer()
            }
        }
    }

    private var md5Panel: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            HStack {
                Text("Current MD5")
                    .font(AppTheme.Typography.caption)
                    .foregroundColor(AppTheme.Colors.textTertiary)
                Spacer()
            }

            Text(viewModel.currentMD5.isEmpty ? "No video loaded" : viewModel.currentMD5)
                .font(.system(size: 12, weight: .medium, design: .monospaced))
                .foregroundColor(AppTheme.Colors.textSecondary)
                .padding(AppTheme.Spacing.xs)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(
                    RoundedRectangle(cornerRadius: AppTheme.Radius.sm)
                        .fill(Color.white.opacity(0.05))
                )

            GlassButton(title: "Modify MD5", icon: "arrow.triangle.2.circlepath", action: {
                viewModel.modifyMD5()
            })
        }
    }

    private var exportOverlay: some View {
        ZStack {
            Color.black.opacity(0.7)
                .ignoresSafeArea()

            VStack(spacing: AppTheme.Spacing.lg) {
                ProgressView()
                    .scaleEffect(1.5)
                    .tint(AppTheme.Colors.primary)

                Text("Exporting...")
                    .font(AppTheme.Typography.headline)
                    .foregroundColor(.white)

                Text("\(Int(viewModel.exportProgress * 100))%")
                    .font(.system(size: 32, weight: .bold, design: .rounded))
                    .foregroundColor(AppTheme.Colors.primary)
            }
            .padding(AppTheme.Spacing.xl)
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.xl)
                    .fill(.ultraThinMaterial)
            )
        }
    }
}
