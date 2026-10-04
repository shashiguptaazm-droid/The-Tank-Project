import Foundation

/// College HTML repository and caching service.
///
/// 1:1 port of Android `CollegeHtmlRepository.kt` & `CollegeDetailCache.kt`.
/// Fetches detailed college information from `https://medigyaan.com/colleges.html`
/// and individual college microsites, parsing HTML stats, fee tables, stipends,
/// officials, and caching locally in `UserDefaults`.
public struct CollegeDetailData: Codable, Identifiable, Hashable {
    public var id: String { collegeName }
    public let collegeName: String
    public let detailUrl: String
    public let address: String
    public let state: String
    public let pinCode: String
    public let annualFee: String
    public let nriFee: String
    public let stipend1: String
    public let stipend2: String
    public let stipend3: String
    public let dean: String
    public let nodalOfficer: String
    public let website: String
    public let allFields: [String: String]
    public let rawHtml: String
    public let dataInReview: Bool
    public let reviewMessage: String

    public init(
        collegeName: String,
        detailUrl: String = "",
        address: String = "",
        state: String = "",
        pinCode: String = "",
        annualFee: String = "",
        nriFee: String = "",
        stipend1: String = "",
        stipend2: String = "",
        stipend3: String = "",
        dean: String = "",
        nodalOfficer: String = "",
        website: String = "",
        allFields: [String: String] = [:],
        rawHtml: String = "",
        dataInReview: Bool = false,
        reviewMessage: String = ""
    ) {
        self.collegeName = collegeName
        self.detailUrl = detailUrl
        self.address = address
        self.state = state
        self.pinCode = pinCode
        self.annualFee = annualFee
        self.nriFee = nriFee
        self.stipend1 = stipend1
        self.stipend2 = stipend2
        self.stipend3 = stipend3
        self.dean = dean
        self.nodalOfficer = nodalOfficer
        self.website = website
        self.allFields = allFields
        self.rawHtml = rawHtml
        self.dataInReview = dataInReview
        self.reviewMessage = reviewMessage
    }
}

/// Local disk cache matching Android `CollegeDetailCache`.
public final class CollegeDetailCache {
    public static let shared = CollegeDetailCache()
    private let userDefaultsKey = "college_detail_cache_v1"

    private init() {}

    private func normalizeKey(_ name: String) -> String {
        "college_" + name.lowercased().trimmingCharacters(in: .whitespacesAndNewlines)
    }

    public func save(data: CollegeDetailData) {
        let key = normalizeKey(data.collegeName)
        if let encoded = try? JSONEncoder().encode(data) {
            UserDefaults.standard.set(encoded, forKey: key)
        }
    }

    public func load(collegeName: String) -> CollegeDetailData? {
        let key = normalizeKey(collegeName)
        guard let data = UserDefaults.standard.data(forKey: key) else { return nil }
        return try? JSONDecoder().decode(CollegeDetailData.self, from: data)
    }
}

/// Repository for downloading and parsing college microsites.
public final class CollegeHtmlRepository {
    public static let shared = CollegeHtmlRepository()

    private let session: URLSession

    public init(session: URLSession = .shared) {
        self.session = session
    }

    /// Fetches college detail with local cache fallback and live HTML parsing.
    public func loadCollege(
        listUrl: String = "https://medigyaan.com/colleges.html",
        collegeName: String
    ) async -> CollegeDetailData {
        if let cached = CollegeDetailCache.shared.load(collegeName: collegeName) {
            return cached
        }

        guard let listURL = URL(string: listUrl) else {
            return reviewFallback(name: collegeName, msg: "Invalid college directory URL")
        }

        do {
            let (listData, listResp) = try await session.data(from: listURL)
            guard (listResp as? HTTPURLResponse)?.statusCode == 200,
                  let listHtml = String(data: listData, encoding: .utf8),
                  !listHtml.isEmpty else {
                return reviewFallback(name: collegeName, msg: "Unable to load college directory")
            }

            let detailHref = findCollegeHref(listHtml: listHtml, targetName: collegeName)
            if detailHref.isEmpty {
                return reviewFallback(name: collegeName, msg: "Data about the college is in review")
            }

            guard let detailURL = URL(string: detailHref, relativeTo: listURL)?.absoluteURL else {
                return reviewFallback(name: collegeName, msg: "Data about the college is in review")
            }

            let (detailData, detailResp) = try await session.data(from: detailURL)
            guard (detailResp as? HTTPURLResponse)?.statusCode == 200,
                  let detailHtml = String(data: detailData, encoding: .utf8),
                  !detailHtml.isEmpty else {
                return reviewFallback(name: collegeName, msg: "Data about the college is in review", detailUrl: detailURL.absoluteString)
            }

            let parsed = parseDetailHtml(
                collegeName: collegeName,
                detailUrl: detailURL.absoluteString,
                html: detailHtml
            )

            CollegeDetailCache.shared.save(data: parsed)
            return parsed

        } catch {
            return reviewFallback(name: collegeName, msg: "Data about the college is in review")
        }
    }

    private func reviewFallback(name: String, msg: String, detailUrl: String = "") -> CollegeDetailData {
        CollegeDetailData(
            collegeName: name,
            detailUrl: detailUrl,
            dataInReview: true,
            reviewMessage: msg
        )
    }

    /// Searches `<a class="college-card" href="..."><h3>College Name</h3></a>`
    private func findCollegeHref(listHtml: String, targetName: String) -> String {
        let pattern = #"(?i)<a[^>]+class=[\"'][^\"']*college-card[^\"']*[\"'][^>]*href=[\"']([^\"']+)[\"'][^>]*>[\s\S]*?<h3>([^<]+)</h3>"#
        guard let regex = try? NSRegularExpression(pattern: pattern) else { return "" }

        let nsRange = NSRange(listHtml.startIndex..<listHtml.endIndex, in: listHtml)
        let matches = regex.matches(in: listHtml, range: nsRange)

        let targetNorm = targetName.lowercased().trimmingCharacters(in: .whitespacesAndNewlines)
        var fallbackHref = ""

        for match in matches {
            guard match.numberOfRanges >= 3,
                  let hrefRange = Range(match.range(at: 1), in: listHtml),
                  let nameRange = Range(match.range(at: 2), in: listHtml) else { continue }

            let href = String(listHtml[hrefRange]).trimmingCharacters(in: .whitespacesAndNewlines)
            let name = String(listHtml[nameRange]).lowercased().trimmingCharacters(in: .whitespacesAndNewlines)

            if name == targetNorm {
                return href
            }
            if fallbackHref.isEmpty && (name.contains(targetNorm) || targetNorm.contains(name)) {
                fallbackHref = href
            }
        }

        return fallbackHref
    }

    /// Fast HTML regex extractor for detail items without bulky heavy DOM libraries.
    private func parseDetailHtml(collegeName: String, detailUrl: String, html: String) -> CollegeDetailData {
        func extractFirst(pattern: String) -> String {
            guard let regex = try? NSRegularExpression(pattern: pattern, options: [.caseInsensitive, .dotMatchesLineSeparators]) else { return "" }
            let range = NSRange(html.startIndex..<html.endIndex, in: html)
            if let match = regex.firstMatch(in: html, range: range), match.numberOfRanges > 1,
               let r = Range(match.range(at: 1), in: html) {
                return String(html[r])
                    .replacingOccurrences(of: "<[^>]+>", with: "", options: .regularExpression)
                    .trimmingCharacters(in: .whitespacesAndNewlines)
            }
            return ""
        }

        let address = extractFirst(pattern: #"class=[\"']address[\"'][^>]*>([^<]+)<"#)
        let annualFee = extractFirst(pattern: #"<h3>Annual Fee</h3>\s*<p>([^<]+)</p>"#)
        let nriFee = extractFirst(pattern: #"<h3>NRI Fee</h3>\s*<p>([^<]+)</p>"#)
        let stipend1 = extractFirst(pattern: #"<h3>1st Year[^<]*</h3>\s*<p>([^<]+)</p>"#)
        let stipend2 = extractFirst(pattern: #"<h3>2nd Year[^<]*</h3>\s*<p>([^<]+)</p>"#)
        let stipend3 = extractFirst(pattern: #"<h3>3rd Year[^<]*</h3>\s*<p>([^<]+)</p>"#)
        let dean = extractFirst(pattern: #"(?:Dean|Principal)[^<]*</h3>\s*<p>([^<]+)</p>"#)
        let nodal = extractFirst(pattern: #"Nodal Officer[^<]*</h3>\s*<p>([^<]+)</p>"#)
        let website = extractFirst(pattern: #"href=[\"'](https?://[^\"']+)[\"'][^>]*>(?:Official Website|Website)</a>"#)

        var allFields: [String: String] = [:]
        if !annualFee.isEmpty { allFields["Annual Fee"] = annualFee }
        if !nriFee.isEmpty { allFields["NRI Fee"] = nriFee }
        if !stipend1.isEmpty { allFields["Stipend (1st Year)"] = stipend1 }
        if !stipend2.isEmpty { allFields["Stipend (2nd Year)"] = stipend2 }
        if !stipend3.isEmpty { allFields["Stipend (3rd Year)"] = stipend3 }
        if !dean.isEmpty { allFields["Dean / Principal"] = dean }
        if !nodal.isEmpty { allFields["Nodal Officer"] = nodal }

        return CollegeDetailData(
            collegeName: collegeName,
            detailUrl: detailUrl,
            address: address,
            state: "",
            pinCode: "",
            annualFee: annualFee,
            nriFee: nriFee,
            stipend1: stipend1,
            stipend2: stipend2,
            stipend3: stipend3,
            dean: dean,
            nodalOfficer: nodal,
            website: website,
            allFields: allFields,
            rawHtml: html,
            dataInReview: false,
            reviewMessage: ""
        )
    }
}
