import SwiftUI
import Foundation

// MARK: - Watermark Item

struct WatermarkItem: Identifiable, Equatable {
    let id = UUID()
    var type: WatermarkType
    var position: CGPoint = CGPoint(x: 0.5, y: 0.5)
    var scale: CGFloat = 1.0
    var rotation: Angle = .zero
    var opacity: Double = 1.0

    // Text properties
    var text: String = "AquaMark"
    var fontName: String = "SF Pro Rounded"
    var fontSize: CGFloat = 24
    var textColor: Color = .white
    var textShadow: Bool = true

    // Image properties
    var imageData: Data?

    // Timestamp properties
    var dateFormat: String = "yyyy-MM-dd HH:mm"

    static func == (lhs: WatermarkItem, rhs: WatermarkItem) -> Bool {
        lhs.id == rhs.id
    }
}

enum WatermarkType: String, CaseIterable, Identifiable {
    case text = "Text"
    case image = "Image"
    case timestamp = "Timestamp"
    case signature = "Signature"

    var id: String { rawValue }

    var icon: String {
        switch self {
        case .text: return "textformat"
        case .image: return "photo"
        case .timestamp: return "clock"
        case .signature: return "signature"
        }
    }
}

// MARK: - Tool Types

enum ToolType: String, CaseIterable, Identifiable {
    case photoWatermark = "Photo Watermark"
    case videoWatermark = "Video Watermark"
    case videoCrop = "Video Crop"
    case videoCompress = "Video Compress"
    case videoMD5 = "MD5 Modifier"
    case batchProcess = "Batch Process"

    var id: String { rawValue }

    var icon: String {
        switch self {
        case .photoWatermark: return "photo.badge.plus"
        case .videoWatermark: return "video.badge.plus"
        case .videoCrop: return "crop"
        case .videoCompress: return "arrow.down.right.and.arrow.up.left"
        case .videoMD5: return "number.circle"
        case .batchProcess: return "square.stack.3d.up"
        }
    }

    var subtitle: String {
        switch self {
        case .photoWatermark: return "Add text, logo & timestamp"
        case .videoWatermark: return "Brand your video content"
        case .videoCrop: return "Trim & resize freely"
        case .videoCompress: return "Reduce file size smartly"
        case .videoMD5: return "Modify file fingerprint"
        case .batchProcess: return "Process multiple files"
        }
    }

    var gradientColors: [Color] {
        switch self {
        case .photoWatermark: return [Color(hex: "6C5CE7"), Color(hex: "A29BFE")]
        case .videoWatermark: return [Color(hex: "00CEC9"), Color(hex: "81ECEC")]
        case .videoCrop: return [Color(hex: "FD79A8"), Color(hex: "FDCB6E")]
        case .videoCompress: return [Color(hex: "55E6C1"), Color(hex: "25CCF7")]
        case .videoMD5: return [Color(hex: "F8A5C2"), Color(hex: "F78FB3")]
        case .batchProcess: return [Color(hex: "D980FA"), Color(hex: "9B59B6")]
        }
    }

    var isPro: Bool {
        switch self {
        case .photoWatermark, .videoCrop: return false
        default: return true
        }
    }
}

// MARK: - Export Quality

enum ExportQuality: String, CaseIterable, Identifiable {
    case low = "Draft"
    case medium = "Standard"
    case high = "High"
    case ultra = "Ultra HD"

    var id: String { rawValue }

    var description: String {
        switch self {
        case .low: return "720p · Fast export"
        case .medium: return "1080p · Balanced"
        case .high: return "2K · High quality"
        case .ultra: return "4K · Maximum quality"
        }
    }

    var isPro: Bool {
        self == .high || self == .ultra
    }
}
