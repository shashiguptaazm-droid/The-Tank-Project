import Foundation

/// Parsed metadata for rich chat link previews.
public struct LinkPreviewData: Identifiable, Codable, Hashable {
    public var id: String { url }
    public let url: String
    public let title: String
    public let description: String
    public let imageUrl: String?
    public let domain: String

    public init(
        url: String,
        title: String,
        description: String,
        imageUrl: String?,
        domain: String
    ) {
        self.url = url
        self.title = title
        self.description = description
        self.imageUrl = imageUrl
        self.domain = domain
    }
}

/// Link extractor and HTML metadata scraper for messenger and forum posts.
/// 1:1 port of Android `LinkPreviewHelper.kt`.
public final class LinkPreviewHelper {

    public static let shared = LinkPreviewHelper()

    private let cache = NSCache<NSString, LinkPreviewWrapper>()

    private final class LinkPreviewWrapper {
        let value: LinkPreviewData
        init(_ value: LinkPreviewData) { self.value = value }
    }

    private init() {
        cache.countLimit = 100
    }

    /// Extract the first valid HTTP/HTTPS URL from user input string.
    public static func extractFirstUrl(from text: String) -> String? {
        guard !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return nil }
        let pattern = #"\b(https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/[^\s<>"]*)?)"#
        guard let regex = try? NSRegularExpression(pattern: pattern, options: .caseInsensitive) else { return nil }
        let range = NSRange(location: 0, length: text.utf16.count)
        guard let match = regex.firstMatch(in: text, options: [], range: range) else { return nil }
        guard let swiftRange = Range(match.range, in: text) else { return nil }
        return String(text[swiftRange])
    }

    public func getCachedPreview(for url: String) -> LinkPreviewData? {
        cache.object(forKey: url as NSString)?.value
    }

    /// Asynchronously fetch OpenGraph and Twitter card metadata for a link.
    public func fetchPreview(for urlString: String) async -> LinkPreviewData? {
        if let cached = getCachedPreview(for: urlString) {
            return cached
        }

        guard let url = URL(string: urlString) else { return nil }

        do {
            var request = URLRequest(url: url)
            request.timeoutInterval = 4.0
            request.setValue(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
                forHTTPHeaderField: "User-Agent"
            )

            let (data, response) = try await URLSession.shared.data(for: request)
            guard let html = String(data: data, encoding: .utf8) ?? String(data: data, encoding: .ascii) else {
                return nil
            }

            let host = url.host?.replacingOccurrences(of: "www.", with: "") ?? "link"

            let ogTitle = extractMetaContent(html: html, property: "og:title")
            let twitterTitle = extractMetaContent(html: html, name: "twitter:title")
            let docTitle = extractTagContent(html: html, tag: "title")
            let title = ogTitle ?? twitterTitle ?? docTitle ?? host

            let ogDesc = extractMetaContent(html: html, property: "og:description")
            let twitterDesc = extractMetaContent(html: html, name: "twitter:description")
            let metaDesc = extractMetaContent(html: html, name: "description")
            let description = ogDesc ?? twitterDesc ?? metaDesc ?? ""

            let ogImage = extractMetaContent(html: html, property: "og:image") ?? extractMetaContent(html: html, name: "twitter:image")
            let siteName = extractMetaContent(html: html, property: "og:site_name") ?? host

            let preview = LinkPreviewData(
                url: urlString,
                title: title,
                description: description,
                imageUrl: ogImage,
                domain: siteName
            )

            cache.setObject(LinkPreviewWrapper(preview), forKey: urlString as NSString)
            return preview
        } catch {
            return nil
        }
    }

    private func extractMetaContent(html: String, property: String? = nil, name: String? = nil) -> String? {
        let attr = property != nil ? "property=\"\(property!)\"" : "name=\"\(name!)\""
        let pattern = #"<meta[^>]*"# + attr + #"[^>]*content="([^"]*)""#
        guard let regex = try? NSRegularExpression(pattern: pattern, options: .caseInsensitive) else { return nil }
        let range = NSRange(location: 0, length: html.utf16.count)
        guard let match = regex.firstMatch(in: html, range: range), match.numberOfRanges > 1 else { return nil }
        guard let valRange = Range(match.range(at: 1), in: html) else { return nil }
        let val = String(html[valRange]).trimmingCharacters(in: .whitespacesAndNewlines)
        return val.isEmpty ? nil : val
    }

    private func extractTagContent(html: String, tag: String) -> String? {
        let pattern = #"<\#(tag)[^>]*>(.*?)</\#(tag)>"#
        guard let regex = try? NSRegularExpression(pattern: pattern, options: [.caseInsensitive, .dotMatchesLineSeparators]) else { return nil }
        let range = NSRange(location: 0, length: html.utf16.count)
        guard let match = regex.firstMatch(in: html, range: range), match.numberOfRanges > 1 else { return nil }
        guard let valRange = Range(match.range(at: 1), in: html) else { return nil }
        let val = String(html[valRange]).trimmingCharacters(in: .whitespacesAndNewlines)
        return val.isEmpty ? nil : val
    }
}
