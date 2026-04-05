import Foundation
import Photos
import UIKit

@MainActor
class VideoDownloadEngine: ObservableObject {
    @Published var state: DownloadState = .idle
    @Published var downloadProgress: Double = 0
    @Published var currentVideoInfo: VideoInfo?

    private var downloadTask: URLSessionDownloadTask?

    func parseURL(_ urlString: String) async {
        guard isValidURL(urlString) else {
            state = .failed("Invalid URL")
            return
        }

        state = .fetching
        let platform = Platform.detect(from: urlString)

        // Use yt-dlp compatible API or direct extraction
        do {
            let info = try await fetchVideoInfo(url: urlString, platform: platform)
            currentVideoInfo = info
            state = .ready(info)
        } catch {
            state = .failed(error.localizedDescription)
        }
    }

    func download(quality: VideoQuality, autoSave: Bool = true) async {
        guard let url = URL(string: quality.downloadURL) else {
            state = .failed("Invalid download URL")
            return
        }

        state = .downloading(progress: 0)
        downloadProgress = 0

        do {
            let (tempURL, _) = try await downloadFile(from: url)

            if autoSave {
                state = .saving
                try await saveToPhotos(fileURL: tempURL)
            }

            if let info = currentVideoInfo {
                saveRecord(info: info, quality: quality)
            }

            state = .completed
        } catch {
            state = .failed(error.localizedDescription)
        }
    }

    func reset() {
        downloadTask?.cancel()
        state = .idle
        downloadProgress = 0
        currentVideoInfo = nil
    }

    // MARK: - Private

    private func isValidURL(_ str: String) -> Bool {
        guard let url = URL(string: str) else { return false }
        return url.scheme == "http" || url.scheme == "https"
    }

    private func fetchVideoInfo(url: String, platform: Platform) async throws -> VideoInfo {
        // Cobalt.tools API — open-source video download service
        // https://github.com/imputnet/cobalt
        let apiURL = URL(string: "https://api.cobalt.tools/")!
        var request = URLRequest(url: apiURL)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        let body: [String: Any] = [
            "url": url,
            "videoQuality": "1080",
            "filenameStyle": "pretty"
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        request.timeoutInterval = 15

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw DownloadError.networkError
        }

        if httpResponse.statusCode == 200 {
            let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? [:]

            let status = json["status"] as? String ?? ""

            if status == "tunnel" || status == "redirect" {
                let downloadURL = json["url"] as? String ?? url
                let filename = json["filename"] as? String ?? "video"

                return VideoInfo(
                    id: UUID().uuidString,
                    title: filename,
                    thumbnail: nil,
                    duration: nil,
                    platform: platform,
                    qualities: [
                        VideoQuality(resolution: "Best", format: "mp4", fileSize: nil, downloadURL: downloadURL)
                    ],
                    sourceURL: url
                )
            }

            if status == "picker", let picker = json["picker"] as? [[String: Any]] {
                let qualities = picker.compactMap { item -> VideoQuality? in
                    guard let dlURL = item["url"] as? String else { return nil }
                    let type = item["type"] as? String ?? "video"
                    return VideoQuality(resolution: type == "video" ? "Video" : "Photo", format: "mp4", fileSize: nil, downloadURL: dlURL)
                }
                return VideoInfo(
                    id: UUID().uuidString,
                    title: "Media from \(platform.rawValue)",
                    thumbnail: nil,
                    duration: nil,
                    platform: platform,
                    qualities: qualities.isEmpty ? [VideoQuality(resolution: "Best", format: "mp4", fileSize: nil, downloadURL: url)] : qualities,
                    sourceURL: url
                )
            }
        }

        // Fallback: try direct download
        return VideoInfo(
            id: UUID().uuidString,
            title: "Video from \(platform.rawValue)",
            thumbnail: nil,
            duration: nil,
            platform: platform,
            qualities: [
                VideoQuality(resolution: "Best", format: "mp4", fileSize: nil, downloadURL: url)
            ],
            sourceURL: url
        )
    }

    private func downloadFile(from url: URL) async throws -> (URL, URLResponse) {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForResource = 600
        let session = URLSession(configuration: config, delegate: ProgressDelegate { [weak self] p in
            Task { @MainActor in
                self?.downloadProgress = p
                self?.state = .downloading(progress: p)
            }
        }, delegateQueue: nil)

        let (tempURL, response) = try await session.download(from: url)

        let permanentURL = FileManager.default.temporaryDirectory
            .appendingPathComponent("savebox_\(UUID().uuidString).mp4")
        try? FileManager.default.removeItem(at: permanentURL)
        try FileManager.default.moveItem(at: tempURL, to: permanentURL)

        return (permanentURL, response)
    }

    private func saveToPhotos(fileURL: URL) async throws {
        let status = await PHPhotoLibrary.requestAuthorization(for: .addOnly)
        guard status == .authorized || status == .limited else {
            throw DownloadError.photoAccessDenied
        }

        try await PHPhotoLibrary.shared().performChanges {
            PHAssetChangeRequest.creationRequestForAssetFromVideo(atFileURL: fileURL)
        }
    }

    private func saveRecord(info: VideoInfo, quality: VideoQuality) {
        var records = loadRecords()
        let record = DownloadRecord(
            id: UUID().uuidString,
            title: info.title,
            platform: info.platform,
            quality: quality.resolution,
            fileSize: quality.fileSize,
            thumbnailURL: info.thumbnail,
            localPath: nil,
            timestamp: Date()
        )
        records.insert(record, at: 0)
        if records.count > 200 { records = Array(records.prefix(200)) }

        if let data = try? JSONEncoder().encode(records) {
            UserDefaults.standard.set(data, forKey: "download_records")
        }
    }

    func loadRecords() -> [DownloadRecord] {
        guard let data = UserDefaults.standard.data(forKey: "download_records"),
              let records = try? JSONDecoder().decode([DownloadRecord].self, from: data) else {
            return []
        }
        return records
    }

    func clearRecords() {
        UserDefaults.standard.removeObject(forKey: "download_records")
    }
}

class ProgressDelegate: NSObject, URLSessionDownloadDelegate {
    let onProgress: (Double) -> Void

    init(onProgress: @escaping (Double) -> Void) {
        self.onProgress = onProgress
    }

    func urlSession(_ session: URLSession, downloadTask: URLSessionDownloadTask, didWriteData bytesWritten: Int64, totalBytesWritten: Int64, totalBytesExpectedToWrite: Int64) {
        if totalBytesExpectedToWrite > 0 {
            let progress = Double(totalBytesWritten) / Double(totalBytesExpectedToWrite)
            onProgress(progress)
        }
    }

    func urlSession(_ session: URLSession, downloadTask: URLSessionDownloadTask, didFinishDownloadingTo location: URL) {}
}

enum DownloadError: LocalizedError {
    case networkError
    case parseError
    case photoAccessDenied
    case unsupportedPlatform

    var errorDescription: String? {
        switch self {
        case .networkError: return "Network connection failed"
        case .parseError: return "Could not parse video URL"
        case .photoAccessDenied: return "Photo library access denied"
        case .unsupportedPlatform: return "Platform not supported"
        }
    }
}
