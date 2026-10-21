import SwiftUI
import WebKit

/// 1:1 SwiftUI WebKit Bridge for Android's `dota_hero_showcase.html`.
///
/// Powers the 3D Hero Showcase for all 19 MBBS Specialty Heroes:
/// - Renders the 3D `.glb` character model (`char01_axiom.glb` ... `char19_somnus.glb`).
/// - Renders each hero's unique procedural 3D environment meshes & diorama props
///   (Gothic cathedral arches, cardio ECG ribbons, benzene rings, pharmacy capsules, biohazard virions, etc.).
/// - Renders the glowing concentric runic pedestal dais with rotating glyph rings.
/// - Full interactive 360° touch orbit controls, pinch zoom, and turntable rotation.
struct DotaHeroShowcaseWebView: UIViewRepresentable {

    let avatarIndex: Int
    var autoRotate: Bool = true
    var onShowcaseReady: (() -> Void)? = nil

    func makeCoordinator() -> Coordinator {
        Coordinator(parent: self)
    }

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.allowsInlineMediaPlayback = true
        config.preferences.setValue(true, forKey: "allowFileAccessFromFileURLs")

        let webView = WKWebView(frame: .zero, configuration: config)
        webView.isOpaque = false
        webView.backgroundColor = .clear
        webView.scrollView.isScrollEnabled = false
        webView.scrollView.bounces = false
        webView.navigationDelegate = context.coordinator

        context.coordinator.webView = webView

        // Load dota_hero_showcase.html from bundle
        if let htmlUrl = Bundle.main.url(forResource: "dota_hero_showcase", withExtension: "html") {
            webView.loadFileURL(htmlUrl, allowingReadAccessTo: Bundle.main.bundleURL)
        } else if let resourcePath = Bundle.main.resourcePath,
                  let htmlData = try? Data(contentsOf: URL(fileURLWithPath: "\(resourcePath)/dota_hero_showcase.html")),
                  let htmlString = String(data: htmlData, encoding: .utf8) {
            webView.loadHTMLString(htmlString, baseURL: Bundle.main.resourceURL ?? Bundle.main.bundleURL)
        } else if let localUrl = Bundle.main.url(forResource: "dota_hero_showcase", withExtension: "html", subdirectory: "Resources") {
            webView.loadFileURL(localUrl, allowingReadAccessTo: Bundle.main.bundleURL)
        }

        RemoteLogger.log(
            tag: "HeroShowcase_Init",
            message: "DotaHeroShowcaseWebView initialized for avatarIndex #\(avatarIndex)"
        )

        return webView
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {
        if context.coordinator.lastAvatarIndex != avatarIndex && context.coordinator.isPageLoaded {
            context.coordinator.lastAvatarIndex = avatarIndex
            dispatchGuardianToWebView(uiView, avatarIndex: avatarIndex)
        }

        if context.coordinator.lastAutoRotate != autoRotate && context.coordinator.isPageLoaded {
            context.coordinator.lastAutoRotate = autoRotate
            uiView.evaluateJavaScript("if (window.toggleTurntable) { window.toggleTurntable(\(autoRotate)); }", completionHandler: nil)
        }
    }

    private func dispatchGuardianToWebView(_ webView: WKWebView, avatarIndex: Int) {
        let heroKit = GuardianRegistry.getHeroKit(avatarIndex)
        let modelGlbName = getGlbModelName(avatarIndex)
        let resolvedModelUrl = resolveGlbUrl(modelGlbName)

        let payload: [String: Any] = [
            "avatarIndex": avatarIndex,
            "name": heroKit?.championName ?? "Hero #\(avatarIndex)",
            "animal": getAnimalName(avatarIndex),
            "powerCategory": heroKit?.defensePower.powerCategory.displayName ?? "ELITE",
            "powerId": heroKit?.defensePower.powerId ?? "UNKNOWN",
            "imageAssetPath": "avatars/char\(String(format: "%02d", avatarIndex - 1000)).png",
            "renderConfig": [
                "modelGlbUrl": resolvedModelUrl,
                "rimColorHex": heroKit?.defensePower.renderConfig?.rimColorHex ?? 0x00E5FF,
                "cameraDistance": 3.4,
                "cameraHeight": 1.45
            ]
        ]

        guard let jsonData = try? JSONSerialization.data(withJSONObject: payload),
              let jsonString = String(data: jsonData, encoding: .utf8) else {
            return
        }

        let escaped = jsonString
            .replacingOccurrences(of: "\\", with: "\\\\")
            .replacingOccurrences(of: "'", with: "\\'")

        let script = "if (window.loadGuardian) { window.loadGuardian('\(escaped)'); }"
        webView.evaluateJavaScript(script) { _, err in
            if let err = err {
                RemoteLogger.log(tag: "HeroShowcase_JS_Error", message: "Failed evaluating loadGuardian: \(err.localizedDescription)")
            } else {
                RemoteLogger.log(tag: "HeroShowcase_Loaded", message: "Dispatched avatar #\(avatarIndex) to 3D showcase engine")
            }
        }
    }

    private func resolveGlbUrl(_ modelName: String) -> String {
        // First try direct local file URL in Bundle
        let baseName = modelName.replacingOccurrences(of: ".glb", with: "")
        if let fileUrl = Bundle.main.url(forResource: baseName, withExtension: "glb") {
            return fileUrl.absoluteString
        }
        if let modelsUrl = Bundle.main.url(forResource: baseName, withExtension: "glb", subdirectory: "Resources/Models") {
            return modelsUrl.absoluteString
        }
        if let flatModelsUrl = Bundle.main.url(forResource: baseName, withExtension: "glb", subdirectory: "Models") {
            return flatModelsUrl.absoluteString
        }
        // Fallback to relative path from dota_hero_showcase.html
        return "Models/\(modelName)"
    }

    private func getGlbModelName(_ avatarIndex: Int) -> String {
        let num = avatarIndex - 1000
        let tag = getAnimalTag(avatarIndex)
        return "char\(String(format: "%02d", num))_\(tag).glb"
    }

    private func getAnimalTag(_ avatarIndex: Int) -> String {
        switch avatarIndex {
        case 1001: return "axiom"
        case 1002: return "pulse"
        case 1003: return "catalyst"
        case 1004: return "necros"
        case 1005: return "pharma"
        case 1006: return "microx"
        case 1007: return "verdict"
        case 1008: return "cura"
        case 1009: return "medicus"
        case 1010: return "surgon"
        case 1011: return "vita"
        case 1012: return "pedia"
        case 1013: return "osteon"
        case 1014: return "optix"
        case 1015: return "resona"
        case 1016: return "derma"
        case 1017: return "synapse"
        case 1018: return "rayne"
        case 1019: return "somnus"
        default: return "axiom"
        }
    }

    private func getAnimalName(_ avatarIndex: Int) -> String {
        switch avatarIndex {
        case 1001: return "The Owl"
        case 1002: return "The Cheetah"
        case 1003: return "The Fox"
        case 1004: return "The Vulture"
        case 1005: return "The Snake"
        case 1006: return "The Spider"
        case 1007: return "The Jackal"
        case 1008: return "The Elephant"
        case 1009: return "The Lion"
        case 1010: return "The Falcon"
        case 1011: return "The Swan"
        case 1012: return "The Kangaroo"
        case 1013: return "The Rhino"
        case 1014: return "The Eagle"
        case 1015: return "The Bat"
        case 1016: return "The Chameleon"
        case 1017: return "The Wolf"
        case 1018: return "The Mantis"
        case 1019: return "The Sloth"
        default: return "The Guardian"
        }
    }

    class Coordinator: NSObject, WKNavigationDelegate {
        var parent: DotaHeroShowcaseWebView
        var lastAvatarIndex: Int = -1
        var lastAutoRotate: Bool = true
        var isPageLoaded: Bool = false
        weak var webView: WKWebView?

        init(parent: DotaHeroShowcaseWebView) {
            self.parent = parent
        }

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            isPageLoaded = true
            lastAvatarIndex = parent.avatarIndex
            lastAutoRotate = parent.autoRotate

            parent.dispatchGuardianToWebView(webView, avatarIndex: parent.avatarIndex)
            parent.onShowcaseReady?()
        }
    }
}
