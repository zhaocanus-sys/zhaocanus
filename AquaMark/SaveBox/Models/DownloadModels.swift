import Foundation

struct VideoInfo: Identifiable, Codable {
    let id: String
    let title: String
    let thumbnail: String?
    let duration: Int?
    let platform: Platform
    let qualities: [VideoQuality]
    let sourceURL: String

    var durationText: String {
        guard let d = duration else { return "" }
        let m = d / 60, s = d % 60
        return String(format: "%d:%02d", m, s)
    }
}

struct VideoQuality: Identifiable, Codable, Hashable {
    var id: String { "\(resolution)_\(format)" }
    let resolution: String
    let format: String
    let fileSize: Int?
    let downloadURL: String

    var label: String { resolution }

    var fileSizeText: String {
        guard let size = fileSize else { return "" }
        if size > 1_000_000_000 {
            return String(format: "%.1f GB", Double(size) / 1_000_000_000)
        } else if size > 1_000_000 {
            return String(format: "%.1f MB", Double(size) / 1_000_000)
        }
        return String(format: "%.0f KB", Double(size) / 1_000)
    }
}

enum Platform: String, Codable, CaseIterable {
    case youtube = "YouTube"
    case tiktok = "TikTok"
    case instagram = "Instagram"
    case twitter = "X (Twitter)"
    case facebook = "Facebook"
    case vimeo = "Vimeo"
    case reddit = "Reddit"
    case pinterest = "Pinterest"
    case bilibili = "Bilibili"
    case other = "Other"

    var icon: String {
        switch self {
        case .youtube: return "play.rectangle.fill"
        case .tiktok: return "music.note"
        case .instagram: return "camera.fill"
        case .twitter: return "bubble.left.fill"
        case .facebook: return "person.2.fill"
        case .vimeo: return "video.fill"
        case .reddit: return "text.bubble.fill"
        case .pinterest: return "pin.fill"
        case .bilibili: return "tv.fill"
        case .other: return "globe"
        }
    }

    var color: String {
        switch self {
        case .youtube: return "FF0000"
        case .tiktok: return "00F2EA"
        case .instagram: return "E1306C"
        case .twitter: return "1DA1F2"
        case .facebook: return "1877F2"
        case .vimeo: return "1AB7EA"
        case .reddit: return "FF4500"
        case .pinterest: return "E60023"
        case .bilibili: return "00A1D6"
        case .other: return "6D6F78"
        }
    }

    static func detect(from url: String) -> Platform {
        let u = url.lowercased()
        if u.contains("youtube.com") || u.contains("youtu.be") { return .youtube }
        if u.contains("tiktok.com") { return .tiktok }
        if u.contains("instagram.com") { return .instagram }
        if u.contains("twitter.com") || u.contains("x.com") { return .twitter }
        if u.contains("facebook.com") || u.contains("fb.watch") { return .facebook }
        if u.contains("vimeo.com") { return .vimeo }
        if u.contains("reddit.com") { return .reddit }
        if u.contains("pinterest.com") || u.contains("pin.it") { return .pinterest }
        if u.contains("bilibili.com") || u.contains("b23.tv") { return .bilibili }
        return .other
    }
}

enum DownloadState: Equatable {
    case idle
    case fetching
    case ready(VideoInfo)
    case downloading(progress: Double)
    case saving
    case completed
    case failed(String)
}

struct DownloadRecord: Identifiable, Codable {
    let id: String
    let title: String
    let platform: Platform
    let quality: String
    let fileSize: Int?
    let thumbnailURL: String?
    let localPath: String?
    let timestamp: Date

    var timeAgo: String {
        let interval = Date().timeIntervalSince(timestamp)
        if interval < 60 { return "just now" }
        if interval < 3600 { return "\(Int(interval / 60))m ago" }
        if interval < 86400 { return "\(Int(interval / 3600))h ago" }
        return "\(Int(interval / 86400))d ago"
    }
}
