import SwiftUI
import Photos
import AVFoundation

@MainActor
class ExportService: ObservableObject {
    @Published var isExporting = false
    @Published var exportProgress: Double = 0
    @Published var exportResult: ExportResult?
    @Published var showShareSheet = false
    @Published var shareItems: [Any] = []

    enum ExportResult: Equatable {
        case success(String)
        case failure(String)
    }

    func saveImageToLibrary(_ image: UIImage) async {
        isExporting = true
        exportProgress = 0.5

        let status = await PHPhotoLibrary.requestAuthorization(for: .addOnly)
        guard status == .authorized || status == .limited else {
            exportResult = .failure("Photo library access denied. Please enable in Settings.")
            isExporting = false
            return
        }

        do {
            try await PHPhotoLibrary.shared().performChanges {
                PHAssetChangeRequest.creationRequestForAsset(from: image)
            }
            exportProgress = 1.0
            exportResult = .success("Photo saved to library")
        } catch {
            exportResult = .failure("Failed to save: \(error.localizedDescription)")
        }

        isExporting = false
    }

    func saveVideoToLibrary(url: URL) async {
        isExporting = true
        exportProgress = 0.3

        let status = await PHPhotoLibrary.requestAuthorization(for: .addOnly)
        guard status == .authorized || status == .limited else {
            exportResult = .failure("Photo library access denied. Please enable in Settings.")
            isExporting = false
            return
        }

        do {
            try await PHPhotoLibrary.shared().performChanges {
                PHAssetChangeRequest.creationRequestForAssetFromVideo(atFileURL: url)
            }
            exportProgress = 1.0
            exportResult = .success("Video saved to library")
        } catch {
            exportResult = .failure("Failed to save: \(error.localizedDescription)")
        }

        isExporting = false
    }

    func shareImage(_ image: UIImage) {
        shareItems = [image]
        showShareSheet = true
    }

    func shareVideo(url: URL) {
        shareItems = [url]
        showShareSheet = true
    }

    func reset() {
        isExporting = false
        exportProgress = 0
        exportResult = nil
        showShareSheet = false
        shareItems = []
    }
}

struct ShareSheet: UIViewControllerRepresentable {
    let items: [Any]

    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: items, applicationActivities: nil)
    }

    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
}

struct ExportOverlay: View {
    let progress: Double
    let result: ExportService.ExportResult?
    let onDismiss: () -> Void

    var body: some View {
        ZStack {
            Color.black.opacity(0.75)
                .ignoresSafeArea()

            VStack(spacing: AppTheme.Spacing.lg) {
                if let result = result {
                    resultView(result)
                } else {
                    progressView
                }
            }
            .padding(AppTheme.Spacing.xl)
            .background(
                RoundedRectangle(cornerRadius: AppTheme.Radius.xl)
                    .fill(.ultraThinMaterial)
                    .overlay(
                        RoundedRectangle(cornerRadius: AppTheme.Radius.xl)
                            .fill(Color.white.opacity(0.05))
                    )
            )
            .padding(.horizontal, 48)
        }
    }

    private var progressView: some View {
        VStack(spacing: AppTheme.Spacing.md) {
            ZStack {
                Circle()
                    .stroke(Color.white.opacity(0.08), lineWidth: 4)
                    .frame(width: 64, height: 64)
                Circle()
                    .trim(from: 0, to: progress)
                    .stroke(
                        LinearGradient(
                            colors: [Color(hex: "7C3AED"), Color(hex: "A78BFA")],
                            startPoint: .topLeading,
                            endPoint: .bottomTrailing
                        ),
                        style: StrokeStyle(lineWidth: 4, lineCap: .round)
                    )
                    .frame(width: 64, height: 64)
                    .rotationEffect(.degrees(-90))

                Text("\(Int(progress * 100))%")
                    .font(.system(size: 16, weight: .bold, design: .rounded))
                    .foregroundColor(.white)
            }

            Text("Exporting...")
                .font(AppTheme.Typography.headline)
                .foregroundColor(.white)
        }
    }

    private func resultView(_ result: ExportService.ExportResult) -> some View {
        VStack(spacing: AppTheme.Spacing.md) {
            ZStack {
                Circle()
                    .fill(result == .success("") ? Color(hex: "4ADE80").opacity(0.15) : Color(hex: "EF4444").opacity(0.15))
                    .frame(width: 64, height: 64)
                Image(systemName: isSuccess(result) ? "checkmark" : "xmark")
                    .font(.system(size: 28, weight: .bold))
                    .foregroundColor(isSuccess(result) ? Color(hex: "4ADE80") : Color(hex: "EF4444"))
            }

            Text(message(result))
                .font(AppTheme.Typography.headline)
                .foregroundColor(.white)
                .multilineTextAlignment(.center)

            Button(action: onDismiss) {
                Text("Done")
                    .font(AppTheme.Typography.headline)
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                    .background(AppTheme.Colors.gradientPrimary)
                    .clipShape(RoundedRectangle(cornerRadius: AppTheme.Radius.md))
            }
            .buttonStyle(ScaleButtonStyle())
        }
    }

    private func isSuccess(_ result: ExportService.ExportResult) -> Bool {
        if case .success = result { return true }
        return false
    }

    private func message(_ result: ExportService.ExportResult) -> String {
        switch result {
        case .success(let msg): return msg
        case .failure(let msg): return msg
        }
    }
}
