import SwiftUI
import WebKit

/// Reusable web view component and modal wrapper.
/// 1:1 port of Android `WebViewActivity.kt`.
public struct AppWebView: UIViewRepresentable {
    public let url: URL

    public init(url: URL) {
        self.url = url
    }

    public func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        let webView = WKWebView(frame: .zero, configuration: configuration)
        webView.allowsBackForwardNavigationGestures = true
        let request = URLRequest(url: url)
        webView.load(request)
        return webView
    }

    public func updateUIView(_ uiView: WKWebView, context: Context) {
        // No-op for static URL loading
    }
}

/// Standalone full-screen web sheet with dismiss toolbar.
public struct WebBrowserSheet: View {
    public let title: String
    public let url: URL
    @Environment(\.dismiss) private var dismiss

    public init(title: String, url: URL) {
        self.title = title
        self.url = url
    }

    public var body: some View {
        NavigationStack {
            AppWebView(url: url)
                .navigationTitle(title)
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .cancellationAction) {
                        Button("Done") { dismiss() }
                    }
                }
        }
    }
}
