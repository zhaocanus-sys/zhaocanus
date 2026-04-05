import SwiftUI
import AVFoundation
import Combine

class VideoWatermarkViewModel: ObservableObject {
    @Published var videoURL: URL?
    @Published var player: AVPlayer?
    @Published var isPlaying = false
    @Published var currentProgress: Double = 0
    @Published var duration: Double = 0

    @Published var watermarkText: String = "AquaMark"
    @Published var watermarkFontSize: CGFloat = 24
    @Published var watermarkOpacity: Double = 1.0
    @Published var watermarkPosition: CGPoint = CGPoint(x: 0.85, y: 0.9)

    @Published var selectedAspectRatio: String = "Free"
    @Published var compressionQuality: Double = 0.7
    @Published var currentMD5: String = ""
    @Published var exportProgress: Double = 0

    private var timeObserver: Any?

    var formattedCurrentTime: String {
        formatTime(currentProgress * duration)
    }

    var formattedDuration: String {
        formatTime(duration)
    }

    var estimatedFileSize: String {
        let baseMB = 50.0
        let estimated = baseMB * compressionQuality
        if estimated < 1 {
            return "\(Int(estimated * 1024)) KB"
        }
        return String(format: "%.1f MB", estimated)
    }

    func loadVideo(url: URL) {
        videoURL = url
        let asset = AVAsset(url: url)
        let playerItem = AVPlayerItem(asset: asset)
        player = AVPlayer(playerItem: playerItem)

        Task { @MainActor in
            if let dur = try? await asset.load(.duration) {
                duration = CMTimeGetSeconds(dur)
            }
        }

        computeMD5(for: url)
    }

    func togglePlayPause() {
        guard let player = player else { return }
        if isPlaying {
            player.pause()
        } else {
            player.play()
        }
        isPlaying.toggle()
    }

    func seekForward() {
        guard let player = player else { return }
        let newTime = CMTimeGetSeconds(player.currentTime()) + 10
        player.seek(to: CMTime(seconds: min(newTime, duration), preferredTimescale: 600))
    }

    func seekBackward() {
        guard let player = player else { return }
        let newTime = CMTimeGetSeconds(player.currentTime()) - 10
        player.seek(to: CMTime(seconds: max(newTime, 0), preferredTimescale: 600))
    }

    func exportVideo(completion: @escaping (URL?) -> Void) {
        guard let videoURL = videoURL else {
            completion(nil)
            return
        }

        let asset = AVAsset(url: videoURL)
        let composition = AVMutableComposition()

        guard let videoTrack = composition.addMutableTrack(
            withMediaType: .video,
            preferredTrackID: kCMPersistentTrackID_Invalid
        ) else {
            completion(nil)
            return
        }

        Task {
            do {
                let tracks = try await asset.loadTracks(withMediaType: .video)
                guard let sourceTrack = tracks.first else {
                    await MainActor.run { completion(nil) }
                    return
                }

                let timeRange = try await CMTimeRange(
                    start: .zero,
                    duration: asset.load(.duration)
                )
                try videoTrack.insertTimeRange(timeRange, of: sourceTrack, at: .zero)

                let videoComposition = AVMutableVideoComposition()
                let naturalSize = try await sourceTrack.load(.naturalSize)
                videoComposition.renderSize = naturalSize
                videoComposition.frameDuration = CMTime(value: 1, timescale: 30)

                let instruction = AVMutableVideoCompositionInstruction()
                instruction.timeRange = timeRange

                let layerInstruction = AVMutableVideoCompositionLayerInstruction(assetTrack: videoTrack)
                instruction.layerInstructions = [layerInstruction]
                videoComposition.instructions = [instruction]

                let watermarkLayer = CATextLayer()
                watermarkLayer.string = watermarkText
                watermarkLayer.fontSize = watermarkFontSize * 2
                watermarkLayer.foregroundColor = UIColor.white.withAlphaComponent(watermarkOpacity).cgColor
                watermarkLayer.alignmentMode = .right
                watermarkLayer.frame = CGRect(
                    x: naturalSize.width * 0.6,
                    y: naturalSize.height * 0.02,
                    width: naturalSize.width * 0.38,
                    height: watermarkFontSize * 3
                )

                let parentLayer = CALayer()
                let videoLayer = CALayer()
                parentLayer.frame = CGRect(origin: .zero, size: naturalSize)
                videoLayer.frame = CGRect(origin: .zero, size: naturalSize)
                parentLayer.addSublayer(videoLayer)
                parentLayer.addSublayer(watermarkLayer)

                videoComposition.animationTool = AVVideoCompositionCoreAnimationTool(
                    postProcessingAsVideoLayer: videoLayer,
                    in: parentLayer
                )

                let outputURL = FileManager.default.temporaryDirectory
                    .appendingPathComponent("aquamark_\(UUID().uuidString).mp4")

                guard let exporter = AVAssetExportSession(
                    asset: composition,
                    presetName: AVAssetExportPresetHighestQuality
                ) else {
                    await MainActor.run { completion(nil) }
                    return
                }

                exporter.outputURL = outputURL
                exporter.outputFileType = .mp4
                exporter.videoComposition = videoComposition

                await exporter.export()

                await MainActor.run {
                    exportProgress = 1.0
                    completion(outputURL)
                }
            } catch {
                await MainActor.run { completion(nil) }
            }
        }
    }

    func modifyMD5() {
        guard let videoURL = videoURL else { return }

        do {
            var data = try Data(contentsOf: videoURL)
            let randomBytes = (0..<16).map { _ in UInt8.random(in: 0...255) }
            data.append(contentsOf: randomBytes)

            let newURL = FileManager.default.temporaryDirectory
                .appendingPathComponent("md5_\(UUID().uuidString).mp4")
            try data.write(to: newURL)

            self.videoURL = newURL
            computeMD5(for: newURL)
        } catch {}
    }

    private func computeMD5(for url: URL) {
        guard let data = try? Data(contentsOf: url) else { return }
        let hash = data.withUnsafeBytes { bytes -> String in
            var hash = [UInt8](repeating: 0, count: 16)
            // Simplified hash computation placeholder
            for (i, byte) in bytes.enumerated() {
                hash[i % 16] ^= byte
            }
            return hash.map { String(format: "%02x", $0) }.joined()
        }
        currentMD5 = hash
    }

    private func formatTime(_ seconds: Double) -> String {
        let mins = Int(seconds) / 60
        let secs = Int(seconds) % 60
        return String(format: "%02d:%02d", mins, secs)
    }
}
