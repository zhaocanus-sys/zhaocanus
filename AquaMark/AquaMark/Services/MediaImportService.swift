import SwiftUI
import PhotosUI
import AVFoundation
import UniformTypeIdentifiers

@MainActor
class MediaImportService: ObservableObject {
    @Published var selectedImage: UIImage?
    @Published var selectedVideoURL: URL?
    @Published var selectedImages: [UIImage] = []
    @Published var isLoading = false
    @Published var error: String?

    func loadImage(from item: PhotosPickerItem) async {
        isLoading = true
        defer { isLoading = false }

        do {
            if let data = try await item.loadTransferable(type: Data.self),
               let image = UIImage(data: data) {
                selectedImage = image
            }
        } catch {
            self.error = "Failed to load image: \(error.localizedDescription)"
        }
    }

    func loadImages(from items: [PhotosPickerItem]) async {
        isLoading = true
        defer { isLoading = false }

        var images: [UIImage] = []
        for item in items {
            do {
                if let data = try await item.loadTransferable(type: Data.self),
                   let image = UIImage(data: data) {
                    images.append(image)
                }
            } catch {
                continue
            }
        }
        selectedImages = images
    }

    func loadVideo(from item: PhotosPickerItem) async {
        isLoading = true
        defer { isLoading = false }

        do {
            if let movie = try await item.loadTransferable(type: VideoTransferable.self) {
                selectedVideoURL = movie.url
            }
        } catch {
            self.error = "Failed to load video: \(error.localizedDescription)"
        }
    }

    func reset() {
        selectedImage = nil
        selectedVideoURL = nil
        selectedImages = []
        error = nil
    }
}

struct VideoTransferable: Transferable {
    let url: URL

    static var transferRepresentation: some TransferRepresentation {
        FileRepresentation(contentType: .movie) { movie in
            SentTransferredFile(movie.url)
        } importing: { received in
            let tempURL = FileManager.default.temporaryDirectory
                .appendingPathComponent("video_\(UUID().uuidString).mp4")
            try FileManager.default.copyItem(at: received.file, to: tempURL)
            return Self(url: tempURL)
        }
    }
}
