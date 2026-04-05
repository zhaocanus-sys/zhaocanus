import SwiftUI
import PhotosUI

struct CreateView: View {
    @EnvironmentObject var subscriptionManager: SubscriptionManager
    @State private var showPhotoPicker = false
    @State private var showVideoPicker = false
    @State private var selectedPhotoItem: PhotosPickerItem?
    @State private var showSubscription = false

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
            .sheet(isPresented: $showSubscription) {
                SubscriptionView()
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
                gradient: [Color(hex: "6C5CE7"), Color(hex: "A29BFE")],
                action: { showPhotoPicker = true }
            )

            importCard(
                icon: "video.badge.plus",
                title: "Import Video",
                subtitle: "Watermark, crop, compress",
                gradient: [Color(hex: "00CEC9"), Color(hex: "81ECEC")],
                action: { showVideoPicker = true }
            )

            importCard(
                icon: "camera.fill",
                title: "Take Photo",
                subtitle: "Capture & watermark instantly",
                gradient: [Color(hex: "FD79A8"), Color(hex: "FDCB6E")],
                action: {}
            )
        }
    }

    private func importCard(
        icon: String,
        title: String,
        subtitle: String,
        gradient: [Color],
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
                    Text(title)
                        .font(AppTheme.Typography.headline)
                        .foregroundColor(AppTheme.Colors.textPrimary)
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
                columns: [
                    GridItem(.flexible(), spacing: AppTheme.Spacing.sm),
                    GridItem(.flexible(), spacing: AppTheme.Spacing.sm),
                    GridItem(.flexible(), spacing: AppTheme.Spacing.sm)
                ],
                spacing: AppTheme.Spacing.sm
            ) {
                quickActionItem(icon: "crop", title: "Crop", color: Color(hex: "55E6C1"))
                quickActionItem(icon: "arrow.down.right.and.arrow.up.left", title: "Compress", color: Color(hex: "25CCF7"))
                quickActionItem(icon: "number.circle", title: "MD5", color: Color(hex: "F8A5C2"))
                quickActionItem(icon: "square.stack.3d.up", title: "Batch", color: Color(hex: "D980FA"), isPro: true)
                quickActionItem(icon: "signature", title: "Sign", color: Color(hex: "FD79A8"))
                quickActionItem(icon: "clock.arrow.circlepath", title: "Timestamp", color: Color(hex: "FDCB6E"))
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
                            .fill(AppTheme.Colors.accent)
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
