import SwiftUI
import Combine

class PhotoWatermarkViewModel: ObservableObject {
    @Published var sourceImage: UIImage?
    @Published var watermarks: [WatermarkItem] = []
    @Published var selectedWatermarkId: UUID?

    @Published var currentText: String = "AquaMark"
    @Published var fontSize: CGFloat = 24
    @Published var textColor: Color = .white
    @Published var opacity: Double = 1.0
    @Published var dateFormat: String = "yyyy-MM-dd HH:mm"

    func addTextWatermark() {
        guard !currentText.isEmpty else { return }
        var item = WatermarkItem(type: .text)
        item.text = currentText
        item.fontSize = fontSize
        item.textColor = textColor
        item.opacity = opacity
        item.position = CGPoint(x: 0.5, y: 0.5)
        watermarks.append(item)
        selectedWatermarkId = item.id
    }

    func addTimestampWatermark() {
        var item = WatermarkItem(type: .timestamp)
        item.dateFormat = dateFormat
        item.fontSize = fontSize
        item.textColor = textColor
        item.opacity = opacity
        item.position = CGPoint(x: 0.85, y: 0.9)
        watermarks.append(item)
        selectedWatermarkId = item.id
    }

    func addImageWatermark(data: Data) {
        var item = WatermarkItem(type: .image)
        item.imageData = data
        item.opacity = opacity
        item.position = CGPoint(x: 0.5, y: 0.5)
        watermarks.append(item)
        selectedWatermarkId = item.id
    }

    func removeWatermark(id: UUID) {
        watermarks.removeAll { $0.id == id }
        if selectedWatermarkId == id {
            selectedWatermarkId = watermarks.last?.id
        }
    }

    func applyPositionPreset(_ preset: PositionPreset) {
        guard let index = watermarks.firstIndex(where: { $0.id == selectedWatermarkId }) else { return }
        watermarks[index].position = preset.point
    }

    func updateSelectedWatermark(_ transform: (inout WatermarkItem) -> Void) {
        guard let index = watermarks.firstIndex(where: { $0.id == selectedWatermarkId }) else { return }
        transform(&watermarks[index])
    }

    func exportImage(quality: ExportQuality = .high) -> UIImage? {
        guard let source = sourceImage else { return nil }
        let renderer = UIGraphicsImageRenderer(size: source.size)
        return renderer.image { ctx in
            source.draw(at: .zero)
            // Render watermarks onto the image
            for watermark in watermarks {
                renderWatermark(watermark, in: source.size, context: ctx.cgContext)
            }
        }
    }

    private func renderWatermark(_ item: WatermarkItem, in size: CGSize, context: CGContext) {
        let x = item.position.x * size.width
        let y = item.position.y * size.height

        switch item.type {
        case .text, .timestamp:
            let text: String
            if item.type == .timestamp {
                let formatter = DateFormatter()
                formatter.dateFormat = item.dateFormat
                text = formatter.string(from: Date())
            } else {
                text = item.text
            }

            let attributes: [NSAttributedString.Key: Any] = [
                .font: UIFont.systemFont(ofSize: item.fontSize * item.scale, weight: .semibold),
                .foregroundColor: UIColor(item.textColor).withAlphaComponent(item.opacity)
            ]

            let nsText = text as NSString
            let textSize = nsText.size(withAttributes: attributes)
            let drawPoint = CGPoint(x: x - textSize.width / 2, y: y - textSize.height / 2)

            context.saveGState()
            context.translateBy(x: x, y: y)
            context.rotate(by: CGFloat(item.rotation.radians))
            context.translateBy(x: -x, y: -y)
            nsText.draw(at: drawPoint, withAttributes: attributes)
            context.restoreGState()

        case .image:
            if let data = item.imageData, let img = UIImage(data: data) {
                let drawSize = CGSize(width: 80 * item.scale, height: 80 * item.scale)
                let rect = CGRect(
                    x: x - drawSize.width / 2,
                    y: y - drawSize.height / 2,
                    width: drawSize.width,
                    height: drawSize.height
                )
                context.saveGState()
                context.setAlpha(item.opacity)
                img.draw(in: rect)
                context.restoreGState()
            }

        case .signature:
            let attributes: [NSAttributedString.Key: Any] = [
                .font: UIFont.italicSystemFont(ofSize: item.fontSize * item.scale),
                .foregroundColor: UIColor(item.textColor).withAlphaComponent(item.opacity)
            ]
            let nsText = item.text as NSString
            let textSize = nsText.size(withAttributes: attributes)
            let drawPoint = CGPoint(x: x - textSize.width / 2, y: y - textSize.height / 2)
            nsText.draw(at: drawPoint, withAttributes: attributes)
        }
    }
}
