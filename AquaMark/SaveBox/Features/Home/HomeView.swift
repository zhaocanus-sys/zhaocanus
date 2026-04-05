import SwiftUI

struct HomeView: View {
    @EnvironmentObject var l10n: L10n
    @EnvironmentObject var engine: VideoDownloadEngine
    @State private var inputURL = ""
    @State private var showQualityPicker = false
    @FocusState private var isInputFocused: Bool

    var body: some View {
        NavigationStack {
            ZStack {
                DS.Colors.bg.ignoresSafeArea()

                ScrollView(.vertical, showsIndicators: false) {
                    VStack(spacing: DS.Spacing.xl) {
                        headerSection
                        inputSection
                        statusSection
                        platformsSection
                    }
                    .padding(.horizontal, DS.Spacing.lg)
                    .padding(.bottom, 40)
                }
            }
            .navigationBarHidden(true)
            .onAppear(perform: checkClipboard)
            .sheet(isPresented: $showQualityPicker) {
                if let info = engine.currentVideoInfo {
                    QualityPickerSheet(info: info)
                }
            }
        }
    }

    // MARK: - Header
    private var headerSection: some View {
        VStack(spacing: DS.Spacing.sm) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(l10n.homeTitle)
                        .font(DS.Fonts.largeTitle)
                        .foregroundColor(DS.Colors.textPrimary)
                    Text(l10n.homeSubtitle)
                        .font(DS.Fonts.callout)
                        .foregroundColor(DS.Colors.textMuted)
                }
                Spacer()
                // Logo circle
                ZStack {
                    Circle()
                        .fill(DS.Colors.accent.opacity(0.15))
                        .frame(width: 44, height: 44)
                    Image(systemName: "arrow.down.to.line.compact")
                        .font(.system(size: 20, weight: .bold))
                        .foregroundColor(DS.Colors.accent)
                }
            }
        }
        .padding(.top, 60)
    }

    // MARK: - Input
    private var inputSection: some View {
        VStack(spacing: DS.Spacing.md) {
            // URL Input field
            HStack(spacing: DS.Spacing.sm) {
                Image(systemName: "link")
                    .font(.system(size: 16, weight: .medium))
                    .foregroundColor(DS.Colors.textMuted)

                TextField(l10n.homePaste, text: $inputURL)
                    .font(DS.Fonts.body)
                    .foregroundColor(DS.Colors.textPrimary)
                    .autocapitalization(.none)
                    .autocorrectionDisabled()
                    .keyboardType(.URL)
                    .focused($isInputFocused)

                if !inputURL.isEmpty {
                    Button {
                        inputURL = ""
                        engine.reset()
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.system(size: 18))
                            .foregroundColor(DS.Colors.textMuted)
                    }
                }
            }
            .padding(.horizontal, DS.Spacing.lg)
            .padding(.vertical, 14)
            .background(DS.Colors.bgTertiary)
            .clipShape(RoundedRectangle(cornerRadius: DS.Radius.md))
            .overlay(
                RoundedRectangle(cornerRadius: DS.Radius.md)
                    .stroke(
                        isInputFocused ? DS.Colors.accent : DS.Colors.inputBorder,
                        lineWidth: isInputFocused ? 2 : 1
                    )
            )

            // Action buttons
            HStack(spacing: DS.Spacing.sm) {
                // Paste button
                Button {
                    if let clip = UIPasteboard.general.string {
                        inputURL = clip
                        startFetch()
                    }
                } label: {
                    HStack(spacing: 6) {
                        Image(systemName: "doc.on.clipboard")
                            .font(.system(size: 14, weight: .semibold))
                        Text(l10n.homePasteClipboard)
                            .font(DS.Fonts.headline)
                    }
                    .foregroundColor(DS.Colors.textPrimary)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .background(DS.Colors.bgTertiary)
                    .clipShape(RoundedRectangle(cornerRadius: DS.Radius.md))
                    .overlay(
                        RoundedRectangle(cornerRadius: DS.Radius.md)
                            .stroke(DS.Colors.inputBorder, lineWidth: 1)
                    )
                }

                // Download button
                Button {
                    startFetch()
                } label: {
                    HStack(spacing: 6) {
                        Image(systemName: "arrow.down.circle.fill")
                            .font(.system(size: 14, weight: .semibold))
                        Text(l10n.homeDownload)
                            .font(DS.Fonts.headline)
                    }
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .background(
                        inputURL.isEmpty ? DS.Colors.accent.opacity(0.4) : DS.Colors.accent
                    )
                    .clipShape(RoundedRectangle(cornerRadius: DS.Radius.md))
                }
                .disabled(inputURL.isEmpty)
            }
        }
    }

    // MARK: - Status
    @ViewBuilder
    private var statusSection: some View {
        switch engine.state {
        case .idle:
            EmptyView()

        case .fetching:
            StatusCard(
                icon: "magnifyingglass",
                iconColor: DS.Colors.info,
                text: l10n.downloadFetching,
                showSpinner: true
            )

        case .ready(let info):
            VideoInfoCard(info: info, onDownload: {
                if info.qualities.count > 1 {
                    showQualityPicker = true
                } else if let q = info.qualities.first {
                    Task { await engine.download(quality: q) }
                }
            })

        case .downloading(let progress):
            DownloadProgressCard(progress: progress, text: l10n.downloadProgress)

        case .saving:
            StatusCard(
                icon: "photo.on.rectangle",
                iconColor: DS.Colors.accent,
                text: "Saving to Photos...",
                showSpinner: true
            )

        case .completed:
            StatusCard(
                icon: "checkmark.circle.fill",
                iconColor: DS.Colors.success,
                text: l10n.downloadSaved,
                showSpinner: false
            )

        case .failed(let msg):
            StatusCard(
                icon: "exclamationmark.triangle.fill",
                iconColor: DS.Colors.error,
                text: "\(l10n.downloadFailed): \(msg)",
                showSpinner: false
            )
        }
    }

    // MARK: - Platforms
    private var platformsSection: some View {
        VStack(alignment: .leading, spacing: DS.Spacing.md) {
            Text(l10n.homeSupported)
                .font(DS.Fonts.caption)
                .foregroundColor(DS.Colors.textMuted)
                .textCase(.uppercase)
                .tracking(1)

            LazyVGrid(columns: Array(repeating: GridItem(.flexible(), spacing: 8), count: 5), spacing: 8) {
                ForEach(Platform.allCases.filter { $0 != .other }, id: \.self) { platform in
                    VStack(spacing: 6) {
                        ZStack {
                            RoundedRectangle(cornerRadius: DS.Radius.sm)
                                .fill(Color(hex: platform.color).opacity(0.12))
                                .frame(width: 48, height: 48)
                            Image(systemName: platform.icon)
                                .font(.system(size: 18, weight: .medium))
                                .foregroundColor(Color(hex: platform.color))
                        }
                        Text(platform.rawValue)
                            .font(.system(size: 9, weight: .medium))
                            .foregroundColor(DS.Colors.textSecondary)
                            .lineLimit(1)
                    }
                }
            }
        }
    }

    // MARK: - Actions
    private func startFetch() {
        guard !inputURL.isEmpty else { return }
        isInputFocused = false
        Task { await engine.parseURL(inputURL) }
    }

    private func checkClipboard() {
        if let clip = UIPasteboard.general.string,
           clip.hasPrefix("http"),
           (clip.contains("youtube") || clip.contains("tiktok") || clip.contains("instagram") || clip.contains("twitter") || clip.contains("x.com") || clip.contains("facebook") || clip.contains("vimeo") || clip.contains("reddit") || clip.contains("bilibili")) {
            inputURL = clip
        }
    }
}

// MARK: - Sub Components

struct StatusCard: View {
    let icon: String
    let iconColor: Color
    let text: String
    var showSpinner: Bool = false

    var body: some View {
        HStack(spacing: DS.Spacing.md) {
            if showSpinner {
                ProgressView()
                    .tint(iconColor)
            } else {
                Image(systemName: icon)
                    .font(.system(size: 20, weight: .medium))
                    .foregroundColor(iconColor)
            }
            Text(text)
                .font(DS.Fonts.callout)
                .foregroundColor(DS.Colors.textSecondary)
                .lineLimit(2)
            Spacer()
        }
        .padding(DS.Spacing.lg)
        .background(DS.Colors.card)
        .clipShape(RoundedRectangle(cornerRadius: DS.Radius.md))
    }
}

struct VideoInfoCard: View {
    let info: VideoInfo
    let onDownload: () -> Void

    var body: some View {
        VStack(spacing: DS.Spacing.md) {
            HStack(spacing: DS.Spacing.md) {
                ZStack {
                    RoundedRectangle(cornerRadius: DS.Radius.sm)
                        .fill(Color(hex: info.platform.color).opacity(0.15))
                        .frame(width: 52, height: 52)
                    Image(systemName: info.platform.icon)
                        .font(.system(size: 22, weight: .medium))
                        .foregroundColor(Color(hex: info.platform.color))
                }

                VStack(alignment: .leading, spacing: 4) {
                    Text(info.title)
                        .font(DS.Fonts.headline)
                        .foregroundColor(DS.Colors.textPrimary)
                        .lineLimit(2)

                    HStack(spacing: 8) {
                        Text(info.platform.rawValue)
                            .font(DS.Fonts.caption)
                            .foregroundColor(Color(hex: info.platform.color))
                        if !info.durationText.isEmpty {
                            Text("·")
                                .foregroundColor(DS.Colors.textMuted)
                            Text(info.durationText)
                                .font(DS.Fonts.caption)
                                .foregroundColor(DS.Colors.textMuted)
                        }
                    }
                }
                Spacer()
            }

            Button(action: onDownload) {
                HStack(spacing: 8) {
                    Image(systemName: "arrow.down.circle.fill")
                        .font(.system(size: 16, weight: .bold))
                    Text("Download Now")
                        .font(DS.Fonts.headline)
                }
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 14)
                .background(DS.Colors.accent)
                .clipShape(RoundedRectangle(cornerRadius: DS.Radius.md))
            }
        }
        .padding(DS.Spacing.lg)
        .background(DS.Colors.card)
        .clipShape(RoundedRectangle(cornerRadius: DS.Radius.md))
    }
}

struct DownloadProgressCard: View {
    let progress: Double
    let text: String

    var body: some View {
        VStack(spacing: DS.Spacing.md) {
            HStack {
                Text(text)
                    .font(DS.Fonts.headline)
                    .foregroundColor(DS.Colors.textPrimary)
                Spacer()
                Text("\(Int(progress * 100))%")
                    .font(DS.Fonts.mono)
                    .foregroundColor(DS.Colors.accent)
            }

            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    RoundedRectangle(cornerRadius: 4)
                        .fill(DS.Colors.bgTertiary)
                    RoundedRectangle(cornerRadius: 4)
                        .fill(DS.Colors.accent)
                        .frame(width: geo.size.width * progress)
                        .animation(.easeInOut(duration: 0.3), value: progress)
                }
            }
            .frame(height: 8)
        }
        .padding(DS.Spacing.lg)
        .background(DS.Colors.card)
        .clipShape(RoundedRectangle(cornerRadius: DS.Radius.md))
    }
}

struct QualityPickerSheet: View {
    @EnvironmentObject var engine: VideoDownloadEngine
    @Environment(\.dismiss) var dismiss
    let info: VideoInfo

    var body: some View {
        NavigationStack {
            List(info.qualities) { quality in
                Button {
                    dismiss()
                    Task { await engine.download(quality: quality) }
                } label: {
                    HStack {
                        Text(quality.label)
                            .font(DS.Fonts.headline)
                            .foregroundColor(DS.Colors.textPrimary)
                        Spacer()
                        if !quality.fileSizeText.isEmpty {
                            Text(quality.fileSizeText)
                                .font(DS.Fonts.caption)
                                .foregroundColor(DS.Colors.textMuted)
                        }
                        Image(systemName: "arrow.down.circle")
                            .foregroundColor(DS.Colors.accent)
                    }
                    .padding(.vertical, 4)
                }
                .listRowBackground(DS.Colors.card)
            }
            .scrollContentBackground(.hidden)
            .background(DS.Colors.bg)
            .navigationTitle("Select Quality")
            .navigationBarTitleDisplayMode(.inline)
        }
        .presentationDetents([.medium])
    }
}
