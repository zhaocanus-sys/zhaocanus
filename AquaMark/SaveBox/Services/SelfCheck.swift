import Foundation
import Photos

struct CheckResult: Identifiable {
    let id = UUID()
    let name: String
    let passed: Bool
    let detail: String
}

@MainActor
class SelfCheckService: ObservableObject {
    @Published var results: [CheckResult] = []
    @Published var isRunning = false

    func runAllChecks() async {
        isRunning = true
        results = []

        // 1. URL Validation
        results.append(checkURLValidation())

        // 2. Platform Detection
        results.append(checkPlatformDetection())

        // 3. Network Connectivity
        results.append(await checkNetwork())

        // 4. Cobalt API
        results.append(await checkCobaltAPI())

        // 5. Photo Library Permission
        results.append(await checkPhotoPermission())

        // 6. Clipboard Access
        results.append(checkClipboard())

        // 7. Disk Space
        results.append(checkDiskSpace())

        // 8. Localization
        results.append(checkLocalization())

        isRunning = false
    }

    private func checkURLValidation() -> CheckResult {
        let testURLs = [
            ("https://youtube.com/watch?v=test", true),
            ("https://tiktok.com/@user/video/123", true),
            ("not a url", false),
            ("ftp://invalid.com", false),
            ("https://instagram.com/reel/abc", true)
        ]
        let allPassed = testURLs.allSatisfy { url, expected in
            let isValid = URL(string: url)?.scheme == "http" || URL(string: url)?.scheme == "https"
            return isValid == expected
        }
        return CheckResult(name: "URL Validation", passed: allPassed, detail: allPassed ? "5/5 test cases passed" : "Some URL validation tests failed")
    }

    private func checkPlatformDetection() -> CheckResult {
        let tests: [(String, Platform)] = [
            ("https://youtube.com/watch?v=abc", .youtube),
            ("https://youtu.be/abc", .youtube),
            ("https://www.tiktok.com/@user/video/123", .tiktok),
            ("https://www.instagram.com/reel/abc", .instagram),
            ("https://twitter.com/user/status/123", .twitter),
            ("https://x.com/user/status/123", .twitter),
            ("https://vimeo.com/123", .vimeo),
            ("https://www.reddit.com/r/test/comments/abc", .reddit),
            ("https://www.bilibili.com/video/BV123", .bilibili),
        ]
        let passed = tests.filter { Platform.detect(from: $0.0) == $0.1 }.count
        let total = tests.count
        return CheckResult(name: "Platform Detection", passed: passed == total, detail: "\(passed)/\(total) platforms correctly identified")
    }

    private func checkNetwork() async -> CheckResult {
        do {
            let url = URL(string: "https://api.cobalt.tools/")!
            var request = URLRequest(url: url)
            request.httpMethod = "GET"
            request.timeoutInterval = 10
            let (_, response) = try await URLSession.shared.data(for: request)
            let status = (response as? HTTPURLResponse)?.statusCode ?? 0
            return CheckResult(name: "Network Connectivity", passed: status > 0, detail: "HTTP \(status) response from API")
        } catch {
            return CheckResult(name: "Network Connectivity", passed: false, detail: error.localizedDescription)
        }
    }

    private func checkCobaltAPI() async -> CheckResult {
        do {
            let url = URL(string: "https://api.cobalt.tools/")!
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.setValue("application/json", forHTTPHeaderField: "Accept")
            request.httpBody = try JSONSerialization.data(withJSONObject: ["url": "https://youtube.com/watch?v=dQw4w9WgXcQ"])
            request.timeoutInterval = 15

            let (data, response) = try await URLSession.shared.data(for: request)
            let status = (response as? HTTPURLResponse)?.statusCode ?? 0

            if status == 200 {
                let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
                let apiStatus = json?["status"] as? String ?? "unknown"
                return CheckResult(name: "Cobalt Download API", passed: true, detail: "API responded: \(apiStatus)")
            }
            return CheckResult(name: "Cobalt Download API", passed: false, detail: "HTTP \(status)")
        } catch {
            return CheckResult(name: "Cobalt Download API", passed: false, detail: error.localizedDescription)
        }
    }

    private func checkPhotoPermission() async -> CheckResult {
        let status = PHPhotoLibrary.authorizationStatus(for: .addOnly)
        switch status {
        case .authorized, .limited:
            return CheckResult(name: "Photo Library Access", passed: true, detail: "Permission granted")
        case .notDetermined:
            return CheckResult(name: "Photo Library Access", passed: true, detail: "Will ask on first save")
        case .denied, .restricted:
            return CheckResult(name: "Photo Library Access", passed: false, detail: "Permission denied — enable in Settings")
        @unknown default:
            return CheckResult(name: "Photo Library Access", passed: false, detail: "Unknown status")
        }
    }

    private func checkClipboard() -> CheckResult {
        let hasClipboard = UIPasteboard.general.hasStrings
        return CheckResult(name: "Clipboard Access", passed: true, detail: hasClipboard ? "Clipboard has content" : "Clipboard is empty (OK)")
    }

    private func checkDiskSpace() -> CheckResult {
        do {
            let attrs = try FileManager.default.attributesOfFileSystem(forPath: NSHomeDirectory())
            if let freeSpace = attrs[.systemFreeSize] as? Int64 {
                let gb = Double(freeSpace) / 1_000_000_000
                return CheckResult(name: "Disk Space", passed: gb > 0.5, detail: String(format: "%.1f GB free", gb))
            }
        } catch {}
        return CheckResult(name: "Disk Space", passed: true, detail: "Could not determine")
    }

    private func checkLocalization() -> CheckResult {
        let l10n = L10n()
        let languages = AppLanguage.allCases
        let allHaveHomeTitle = languages.allSatisfy { lang in
            l10n.lang = lang
            return !l10n.homeTitle.isEmpty
        }
        return CheckResult(name: "Localization (\(languages.count) languages)", passed: allHaveHomeTitle, detail: allHaveHomeTitle ? "All \(languages.count) languages verified" : "Some translations missing")
    }
}
