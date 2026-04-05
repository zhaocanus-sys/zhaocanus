import SwiftUI
import PhotosUI

struct CreateView: View {
    @EnvironmentObject var subscriptionManager: SubscriptionManager
    @StateObject private var importService = MediaImportService()

    @State private var showPhotoPicker = false
    @State private var showVideoPicker = false
    @State private var photoItem: PhotosPickerItem?
    @State private var videoItem: PhotosPickerItem?
    @State private var showPhotoEditor = false
    @State private var showVideoEditor = false
    @State private var showSubscription = false
    @State private var showBatchProcess = false

    var body: some View {
        NavigationStack {
            ScrollView(.vertical, showsIndicators: false) {
                VStack(spacing: AppTheme.Spacing.xl) {
                    headerSection
                    importSection
                    quickActions
                }
                .padding(.horizontal, AppTheme.Spacing.md)
                .padding(.bottom, 100)
            }
            .background(AppTheme.Colors.gradientDark.ignoresSafeArea())
            .navigationBarHidden(true)
            .photosPicker(isPresented: $showPhotoPicker, selection: $photoItem, matching: .images)
            .photosPicker(isPresented: $showVideoPicker, selection: $videoItem, matching: .videos)
            .sheet(isPresented: $showSubscription) { SubscriptionView() }
            .fullScreenCover(isPresented: $showPhotoEditor) { PhotoWatermarkView() }
            .fullScreenCover(isPresented: $showVideoEditor) { VideoWatermarkView() }
            .fullScreenCover(isPresented: $showBatchProcess) { BatchProcessingView() }
            .onChange(of: photoItem) { newItem in
                guard newItem != nil else { return }
                showPhotoEditor = true
            }
            .onChange(of: videoItem) { newItem in
                guard newItem != nil else { return }
                showVideoEditor = true
            }
        }
    }

    private var headerSection: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Create")
                .font(AppTheme.Typography.title)
                .foregroundColor(AppTheme.Colors.textPrimary)
            Text("Choose a media to start")
                .font(AppTheme.Typography.subheadline)
                .foregroundColor(AppTheme.Colors.textSecondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.top, AppTheme.Spacing.md)
    }

    private var importSection: some View {
        VStack(spacing: AppTheme.Spacing.sm) {
            importCard(
                icon: "photo.on.rectangle.angled",
                title: "Import Photo",
                subtitle: "Add watermarks, text, logos",
                gradient: [Color(hex: "7C3AED"), Color(hex: "A78BFA")],
                action: { showPhotoPicker = true }
            )
            importCard(
                icon: "video.badge.plus",
                title: "Import Video",
                subtitle: "Watermark, crop, compress",
                gradient: [Color(hex: "06B6D4"), Color(hex: "67E8F9")],
                action: { showVideoPicker = true }
            )
            importCard(
                icon: "square.stack.3d.up.fill",
                title: "Batch Process",
                subtitle: "Watermark multiple photos at once",
                gradient: [Color(hex: "C084FC"), Color(hex: "8B5CF6")],
                isPro: true,
                action: {
                    if subscriptionManager.isPro {
                        showBatchProcess = true
                    } else {
                        showSubscription = true
                    }
                }
            )
        }
    }

    private func importCard(
        icon: String, title: String, subtitle: String,
        gradient: [Color], isPro: Bool = false,
        action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            HStack(spacing: AppTheme.Spacing.md) {
                ZStack {
                    RoundedRectangle(cornerRadius: AppTheme.Radius.md)
                        .fill(LinearGradient(colors: gradient, startPoint: .topLeading, endPoint: .bottomTrailing))
                        .frame(width: 56, height: 56)
                    Image(systemName: icon)
                        .font(.system(size: 24, weight: .semibold))
                        .foregroundColor(.white)
                }
                VStack(alignment: .leading, spacing: 4) {
                    HStack(spacing: 6) {
                        Text(title)
                            .font(AppTheme.Typography.headline)
                            .foregroundColor(AppTheme.Colors.textPrimary)
                        if isPro { ProBadge(size: .small) }
                    }
                    Text(subtitle)
                        .font(AppTheme.Typography.footnote)
                        .foregroundColor(AppTheme.Colors.textTertiary)
                }
                Spacer()
                Image(systemName: "chevron.right")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundColor(AppTheme.Colors.textTertiary)
            }
            .padding(AppTheme.Spacing.md)
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.lg)
                    .fill(.ultraThinMaterial)
                    .overlay(
                        RoundedRectangle(cornerRadius: AppTheme.Radius.lg)
                            .fill(AppTheme.Colors.glassFill)
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: AppTheme.Radius.lg)
                            .stroke(AppTheme.Colors.glassBorder, lineWidth: 1)
                    )
            )
        }
        .buttonStyle(ScaleButtonStyle())
    }

    private var quickActions: some View {
        VStack(alignment: .leading, spacing: AppTheme.Spacing.sm) {
            Text("Quick Actions")
                .font(AppTheme.Typography.title2)
                .foregroundColor(AppTheme.Colors.textPrimary)

            LazyVGrid(
                columns: Array(repeating: GridItem(.flexible(), spacing: 10), count: 3),
                spacing: 10
            ) {
                quickActionItem(icon: "crop", title: "Crop", color: Color(hex: "34D399"))
                quickActionItem(icon: "arrow.down.right.and.arrow.up.left", title: "Compress", color: Color(hex: "38BDF8"))
                quickActionItem(icon: "number.circle", title: "MD5", color: Color(hex: "F9A8D4"))
                quickActionItem(icon: "square.stack.3d.up", title: "Batch", color: Color(hex: "C084FC"), isPro: true)
                quickActionItem(icon: "signature", title: "Sign", color: Color(hex: "F472B6"))
                quickActionItem(icon: "clock.arrow.circlepath", title: "Timestamp", color: Color(hex: "FBBF24"))
            }
        }
    }

    private func quickActionItem(icon: String, title: String, color: Color, isPro: Bool = false) -> some View {
        Button {
            if isPro && !subscriptionManager.isPro {
                showSubscription = true
            }
        } label: {
            VStack(spacing: 8) {
                ZStack(alignment: .topTrailing) {
                    Image(systemName: icon)
                        .font(.system(size: 24, weight: .medium))
                        .foregroundColor(color)
                        .frame(width: 50, height: 50)
                    if isPro {
                        Circle()
                            .fill(Color(hex: "F472B6"))
                            .frame(width: 8, height: 8)
                            .offset(x: 4, y: -4)
                    }
                }
                Text(title)
                    .font(AppTheme.Typography.caption)
                    .foregroundColor(AppTheme.Colors.textSecondary)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, AppTheme.Spacing.sm)
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.md)
                    .fill(.ultraThinMaterial)
                    .overlay(
                        RoundedRectangle(cornerRadius: AppTheme.Radius.md)
                            .fill(AppTheme.Colors.glassFill)
                    )
            )
        }
        .buttonStyle(ScaleButtonStyle())
    }
}
