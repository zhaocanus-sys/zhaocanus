import SwiftUI
import AVKit

// MARK: - Video Crop View

struct VideoCropView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var selectedRatio = "Free"
    @State private var cropRect = CGRect(x: 0.1, y: 0.1, width: 0.8, height: 0.8)

    private let ratios = ["Free", "1:1", "4:3", "16:9", "9:16", "3:4"]

    var body: some View {
        NavigationStack {
            ZStack {
                AppTheme.Colors.gradientDark.ignoresSafeArea()

                VStack(spacing: AppTheme.Spacing.md) {
                    toolbar(title: "Crop Video")

                    Spacer()

                    ZStack {
                        RoundedRectangle(cornerRadius: AppTheme.Radius.lg)
                            .fill(Color.black.opacity(0.3))
                            .overlay(
                                VStack {
                                    Image(systemName: "crop")
                                        .font(.system(size: 48))
                                        .foregroundStyle(AppTheme.Colors.gradientPrimary)
                                    Text("Select a video to crop")
                                        .font(AppTheme.Typography.headline)
                                        .foregroundColor(AppTheme.Colors.textSecondary)
                                }
                            )
                    }
                    .padding(.horizontal, AppTheme.Spacing.md)

                    Spacer()

                    ratioSelector

                    GlassButton(title: "Apply Crop", icon: "crop", action: {})
                        .padding(.horizontal, AppTheme.Spacing.md)
                        .padding(.bottom, AppTheme.Spacing.xl)
                }
            }
            .navigationBarHidden(true)
        }
    }

    private var ratioSelector: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(ratios, id: \.self) { ratio in
                    Button {
                        selectedRatio = ratio
                    } label: {
                        Text(ratio)
                            .font(AppTheme.Typography.subheadline)
                            .foregroundColor(selectedRatio == ratio ? .white : AppTheme.Colors.textSecondary)
                            .padding(.horizontal, 20)
                            .padding(.vertical, 10)
                            .background(
                                Capsule()
                                    .fill(selectedRatio == ratio ? AppTheme.Colors.primary : Color.white.opacity(0.08))
                            )
                    }
                }
            }
            .padding(.horizontal, AppTheme.Spacing.md)
        }
    }

    private func toolbar(title: String) -> some View {
        HStack {
            Button { dismiss() } label: {
                Image(systemName: "xmark.circle.fill")
                    .font(.system(size: 28))
                    .foregroundStyle(.white.opacity(0.6))
            }
            Spacer()
            Text(title)
                .font(AppTheme.Typography.headline)
                .foregroundColor(AppTheme.Colors.textPrimary)
            Spacer()
            Color.clear.frame(width: 28, height: 28)
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.vertical, AppTheme.Spacing.xs)
    }
}

// MARK: - Video Compress View

struct VideoCompressView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var quality: Double = 0.7
    @State private var resolution = "1080p"

    private let resolutions = ["480p", "720p", "1080p", "2K", "4K"]

    var body: some View {
        NavigationStack {
            ZStack {
                AppTheme.Colors.gradientDark.ignoresSafeArea()

                VStack(spacing: AppTheme.Spacing.lg) {
                    compressToolbar

                    Spacer()

                    compressionInfo

                    Spacer()

                    controlsSection

                    GlassButton(title: "Compress Video", icon: "arrow.down.right.and.arrow.up.left", action: {})
                        .padding(.horizontal, AppTheme.Spacing.md)
                        .padding(.bottom, AppTheme.Spacing.xl)
                }
            }
            .navigationBarHidden(true)
        }
    }

    private var compressToolbar: some View {
        HStack {
            Button { dismiss() } label: {
                Image(systemName: "xmark.circle.fill")
                    .font(.system(size: 28))
                    .foregroundStyle(.white.opacity(0.6))
            }
            Spacer()
            Text("Compress")
                .font(AppTheme.Typography.headline)
                .foregroundColor(AppTheme.Colors.textPrimary)
            Spacer()
            Color.clear.frame(width: 28, height: 28)
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.vertical, AppTheme.Spacing.xs)
    }

    private var compressionInfo: some View {
        GlassCard {
            VStack(spacing: AppTheme.Spacing.md) {
                Image(systemName: "arrow.down.right.and.arrow.up.left")
                    .font(.system(size: 40))
                    .foregroundStyle(AppTheme.Colors.gradientPrimary)

                Text("Select a video to compress")
                    .font(AppTheme.Typography.headline)
                    .foregroundColor(AppTheme.Colors.textSecondary)

                HStack(spacing: AppTheme.Spacing.xl) {
                    VStack {
                        Text("Original")
                            .font(AppTheme.Typography.caption)
                            .foregroundColor(AppTheme.Colors.textTertiary)
                        Text("-- MB")
                            .font(AppTheme.Typography.title3)
                            .foregroundColor(.white)
                    }

                    Image(systemName: "arrow.right")
                        .foregroundColor(AppTheme.Colors.primary)

                    VStack {
                        Text("Compressed")
                            .font(AppTheme.Typography.caption)
                            .foregroundColor(AppTheme.Colors.textTertiary)
                        Text("-- MB")
                            .font(AppTheme.Typography.title3)
                            .foregroundColor(AppTheme.Colors.success)
                    }
                }
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, AppTheme.Spacing.lg)
        }
        .padding(.horizontal, AppTheme.Spacing.md)
    }

    private var controlsSection: some View {
        VStack(spacing: AppTheme.Spacing.md) {
            GlassCard {
                VStack(spacing: AppTheme.Spacing.sm) {
                    HStack {
                        Text("Quality")
                            .font(AppTheme.Typography.subheadline)
                            .foregroundColor(AppTheme.Colors.textPrimary)
                        Spacer()
                        Text("\(Int(quality * 100))%")
                            .font(AppTheme.Typography.headline)
                            .foregroundColor(AppTheme.Colors.primary)
                    }
                    Slider(value: $quality, in: 0.1...1.0, step: 0.05)
                        .tint(AppTheme.Colors.primary)
                }
            }
            .padding(.horizontal, AppTheme.Spacing.md)

            GlassCard {
                VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
                    Text("Resolution")
                        .font(AppTheme.Typography.subheadline)
                        .foregroundColor(AppTheme.Colors.textPrimary)

                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 8) {
                            ForEach(resolutions, id: \.self) { res in
                                Button {
                                    resolution = res
                                } label: {
                                    Text(res)
                                        .font(AppTheme.Typography.caption)
                                        .foregroundColor(resolution == res ? .white : AppTheme.Colors.textSecondary)
                                        .padding(.horizontal, 16)
                                        .padding(.vertical, 8)
                                        .background(
                                            Capsule()
                                                .fill(resolution == res ? AppTheme.Colors.primary : Color.white.opacity(0.08))
                                        )
                                }
                            }
                        }
                    }
                }
            }
            .padding(.horizontal, AppTheme.Spacing.md)
        }
    }
}

// MARK: - MD5 Modifier View

struct MD5ModifierView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var originalMD5 = ""
    @State private var newMD5 = ""
    @State private var isProcessing = false

    var body: some View {
        NavigationStack {
            ZStack {
                AppTheme.Colors.gradientDark.ignoresSafeArea()

                VStack(spacing: AppTheme.Spacing.lg) {
                    md5Toolbar

                    Spacer()

                    md5InfoCard

                    Spacer()

                    GlassButton(title: "Modify MD5 Hash", icon: "arrow.triangle.2.circlepath", action: {
                        isProcessing = true
                        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                            isProcessing = false
                            newMD5 = UUID().uuidString.lowercased().replacingOccurrences(of: "-", with: "")
                        }
                    })
                    .padding(.horizontal, AppTheme.Spacing.md)
                    .padding(.bottom, AppTheme.Spacing.xl)
                }
            }
            .navigationBarHidden(true)
        }
    }

    private var md5Toolbar: some View {
        HStack {
            Button { dismiss() } label: {
                Image(systemName: "xmark.circle.fill")
                    .font(.system(size: 28))
                    .foregroundStyle(.white.opacity(0.6))
            }
            Spacer()
            Text("MD5 Modifier")
                .font(AppTheme.Typography.headline)
                .foregroundColor(AppTheme.Colors.textPrimary)
            Spacer()
            Color.clear.frame(width: 28, height: 28)
        }
        .padding(.horizontal, AppTheme.Spacing.md)
        .padding(.vertical, AppTheme.Spacing.xs)
    }

    private var md5InfoCard: some View {
        GlassCard {
            VStack(spacing: AppTheme.Spacing.lg) {
                Image(systemName: "number.circle.fill")
                    .font(.system(size: 48))
                    .foregroundStyle(AppTheme.Colors.gradientAccent)

                if isProcessing {
                    ProgressView()
                        .scaleEffect(1.2)
                        .tint(AppTheme.Colors.primary)
                } else {
                    VStack(spacing: AppTheme.Spacing.md) {
                        md5Row(label: "Original", value: originalMD5.isEmpty ? "Select a file" : originalMD5)
                        if !newMD5.isEmpty {
                            Image(systemName: "arrow.down")
                                .foregroundColor(AppTheme.Colors.primary)
                            md5Row(label: "Modified", value: newMD5)
                        }
                    }
                }

                Text("Appends random bytes to change the file's MD5 hash without affecting playback quality.")
                    .font(AppTheme.Typography.footnote)
                    .foregroundColor(AppTheme.Colors.textTertiary)
                    .multilineTextAlignment(.center)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, AppTheme.Spacing.md)
        }
        .padding(.horizontal, AppTheme.Spacing.md)
    }

    private func md5Row(label: String, value: String) -> some View {
        VStack(spacing: 4) {
            Text(label)
                .font(AppTheme.Typography.caption)
                .foregroundColor(AppTheme.Colors.textTertiary)
            Text(value)
                .font(.system(size: 11, weight: .medium, design: .monospaced))
                .foregroundColor(AppTheme.Colors.textSecondary)
                .lineLimit(1)
                .truncationMode(.middle)
        }
    }
}
