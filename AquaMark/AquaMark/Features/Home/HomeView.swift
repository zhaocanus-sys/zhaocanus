import SwiftUI
import PhotosUI

struct HomeView: View {
    @EnvironmentObject var subscriptionManager: SubscriptionManager
    @State private var showSubscription = false
    @State private var showPhotoEditor = false
    @State private var showVideoEditor = false
    @State private var showVideoCrop = false
    @State private var showVideoCompress = false
    @State private var showMD5Modifier = false
    @State private var showBatchProcess = false

    @State private var photoPickerItem: PhotosPickerItem?
    @State private var showPhotoPicker = false
    @State private var showVideoPicker = false
    @State private var videoPickerItem: PhotosPickerItem?

    @StateObject private var importService = MediaImportService()

    private let columns = [
        GridItem(.flexible(), spacing: 10),
        GridItem(.flexible(), spacing: 10)
    ]

    var body: some View {
        NavigationStack {
            ScrollView(.vertical, showsIndicators: false) {
                VStack(spacing: AppTheme.Spacing.lg) {
                    headerSection
                    if !subscriptionManager.isPro {
                        proPromoBanner
                    }
                    toolsGrid
                    recentSection
                }
                .padding(.horizontal, AppTheme.Spacing.md)
                .padding(.bottom, 100)
            }
            .background(AppTheme.Colors.gradientDark.ignoresSafeArea())
            .navigationBarHidden(true)
            .sheet(isPresented: $showSubscription) { SubscriptionView() }
            .fullScreenCover(isPresented: $showPhotoEditor) { PhotoWatermarkView() }
            .fullScreenCover(isPresented: $showVideoEditor) { VideoWatermarkView() }
            .fullScreenCover(isPresented: $showVideoCrop) { VideoCropView() }
            .fullScreenCover(isPresented: $showVideoCompress) { VideoCompressView() }
            .fullScreenCover(isPresented: $showMD5Modifier) { MD5ModifierView() }
            .fullScreenCover(isPresented: $showBatchProcess) { BatchProcessingView() }
        }
    }

    private var headerSection: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text("AquaMark")
                    .font(AppTheme.Typography.title)
                    .foregroundColor(AppTheme.Colors.textPrimary)
                Text("Professional Watermark Studio")
                    .font(AppTheme.Typography.subheadline)
                    .foregroundColor(AppTheme.Colors.textSecondary)
            }
            Spacer()
            if subscriptionManager.isPro {
                ProBadge(size: .regular)
            }
        }
        .padding(.top, AppTheme.Spacing.md)
    }

    private var proPromoBanner: some View {
        Button { showSubscription = true } label: {
            HStack(spacing: AppTheme.Spacing.md) {
                VStack(alignment: .leading, spacing: 6) {
                    HStack(spacing: 6) {
                        Image(systemName: "crown.fill")
                            .foregroundColor(Color(hex: "FDE68A"))
                        Text("Unlock Pro")
                            .font(AppTheme.Typography.headline)
                            .foregroundColor(.white)
                    }
                    Text("Unlimited exports, 4K quality, batch processing & more")
                        .font(AppTheme.Typography.caption)
                        .foregroundColor(.white.opacity(0.7))
                        .lineLimit(2)
                }
                Spacer()
                Image(systemName: "chevron.right.circle.fill")
                    .font(.system(size: 24))
                    .foregroundColor(.white.opacity(0.8))
            }
            .padding(AppTheme.Spacing.md)
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.lg)
                    .fill(
                        LinearGradient(
                            colors: [Color(hex: "7C3AED"), Color(hex: "8B5CF6"), Color(hex: "C084FC"), Color(hex: "F472B6")],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        )
                    )
            )
        }
        .buttonStyle(ScaleButtonStyle())
    }

    private var toolsGrid: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            Text("Tools")
                .font(AppTheme.Typography.title2)
                .foregroundColor(AppTheme.Colors.textPrimary)

            LazyVGrid(columns: columns, spacing: 10) {
                ForEach(ToolType.allCases) { tool in
                    ToolCard(
                        icon: tool.icon,
                        title: tool.rawValue,
                        subtitle: tool.subtitle,
                        gradient: tool.gradientColors,
                        action: { handleToolTap(tool) },
                        isPro: tool.isPro
                    )
                }
            }
        }
    }

    private func handleToolTap(_ tool: ToolType) {
        if tool.isPro && !subscriptionManager.isPro {
            showSubscription = true
            return
        }
        switch tool {
        case .photoWatermark: showPhotoEditor = true
        case .videoWatermark: showVideoEditor = true
        case .videoCrop: showVideoCrop = true
        case .videoCompress: showVideoCompress = true
        case .videoMD5: showMD5Modifier = true
        case .batchProcess: showBatchProcess = true
        }
    }

    private var recentSection: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            HStack {
                Text("Recent")
                    .font(AppTheme.Typography.title2)
                    .foregroundColor(AppTheme.Colors.textPrimary)
                Spacer()
                Button("See All") {}
                    .font(AppTheme.Typography.subheadline)
                    .foregroundColor(AppTheme.Colors.primary)
            }
            emptyRecentState
        }
    }

    private var emptyRecentState: some View {
        GlassCard {
            VStack(spacing: AppTheme.Spacing.md) {
                Image(systemName: "sparkles")
                    .font(.system(size: 40))
                    .foregroundStyle(AppTheme.Colors.gradientPrimary)
                Text("No recent projects")
                    .font(AppTheme.Typography.headline)
                    .foregroundColor(AppTheme.Colors.textSecondary)
                Text("Start creating to see your work here")
                    .font(AppTheme.Typography.footnote)
                    .foregroundColor(AppTheme.Colors.textTertiary)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, AppTheme.Spacing.xl)
        }
    }
}
