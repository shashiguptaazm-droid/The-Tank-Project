import Foundation

/// Ports Android's `RagChunk` from `RagHelper.kt`.
public struct RagChunk: Codable, Equatable, Hashable {
    public let book: String
    public let bookId: String
    public let page: String
    public let section: String
    public let chunkId: String
    public let text: String
    public let pages: Int

    public init(
        book: String,
        bookId: String,
        page: String,
        section: String,
        chunkId: String,
        text: String,
        pages: Int = 0
    ) {
        self.book = book
        self.bookId = bookId
        self.page = page
        self.section = section
        self.chunkId = chunkId
        self.text = text
        self.pages = pages
    }

    enum CodingKeys: String, CodingKey {
        case book
        case bookId = "book_id"
        case page
        case section
        case chunkId = "chunk_id"
        case text
        case pages
    }
}

/// Ports Android's `RagFigure` from `RagHelper.kt`.
public struct RagFigure: Codable, Equatable, Hashable {
    public let figureId: String
    public let book: String
    public let bookId: String
    public let page: Int
    public let label: String
    public let caption: String
    public let path: String

    public init(
        figureId: String,
        book: String,
        bookId: String,
        page: Int,
        label: String = "Figure",
        caption: String = "",
        path: String = ""
    ) {
        self.figureId = figureId
        self.book = book
        self.bookId = bookId
        self.page = page
        self.label = label
        self.caption = caption
        self.path = path
    }

    enum CodingKeys: String, CodingKey {
        case figureId = "figure_id"
        case book
        case bookId = "book_id"
        case page
        case label
        case caption
        case path
    }
}

/// Ports Android's `RagSearchResult` from `RagHelper.kt`.
public struct RagSearchResult: Equatable {
    public let results: [RagChunk]
    public let figures: [RagFigure]

    public init(results: [RagChunk] = [], figures: [RagFigure] = []) {
        self.results = results
        self.figures = figures
    }
}

/// 1:1 Swift port of Android's `RagHelper.kt`.
/// Connects to VPS RAG search endpoint at `https://medigyaan.com/webai/ragpage/search`.
public final class RagHelper {
    public static let shared = RagHelper()

    private let ragSearchURL = URL(string: "https://medigyaan.com/webai/ragpage/search")!
    private let maxContextChars = 6500
    private let maxFigures = 24

    private init() {}

    /// Searches the MediGyaan textbook corpus for excerpts and figures matching the query.
    public func search(query: String, k: Int = 8) async -> RagSearchResult {
        let cleanQuery = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !cleanQuery.isEmpty else {
            return RagSearchResult()
        }

        var request = URLRequest(url: ragSearchURL)
        request.httpMethod = "POST"
        request.setValue("application/json; charset=utf-8", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 8.0

        let payload: [String: Any] = [
            "query": cleanQuery,
            "k": k
        ]

        do {
            request.httpBody = try JSONSerialization.data(withJSONObject: payload)
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
                return RagSearchResult()
            }

            guard let root = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                return RagSearchResult()
            }

            var chunks: [RagChunk] = []
            if let resultsArr = root["results"] as? [[String: Any]] {
                for obj in resultsArr {
                    let book = obj["book"] as? String ?? "Unknown book"
                    let bookId = obj["book_id"] as? String ?? ""
                    let page = obj["page"] as? String ?? ""
                    let section = obj["section"] as? String ?? ""
                    let chunkId = obj["chunk_id"] as? String ?? ""
                    let text = obj["text"] as? String ?? ""
                    let pages = obj["pages"] as? Int ?? 0
                    chunks.append(RagChunk(
                        book: book,
                        bookId: bookId,
                        page: page,
                        section: section,
                        chunkId: chunkId,
                        text: text,
                        pages: pages
                    ))
                }
            }

            var figures: [RagFigure] = []
            if let figuresArr = root["figures"] as? [[String: Any]] {
                for obj in figuresArr {
                    let figureId = obj["figure_id"] as? String ?? ""
                    let book = obj["book"] as? String ?? ""
                    let bookId = obj["book_id"] as? String ?? ""
                    let page = obj["page"] as? Int ?? 0
                    let label = obj["label"] as? String ?? "Figure"
                    let caption = obj["caption"] as? String ?? ""
                    let path = obj["path"] as? String ?? ""
                    figures.append(RagFigure(
                        figureId: figureId,
                        book: book,
                        bookId: bookId,
                        page: page,
                        label: label,
                        caption: caption,
                        path: path
                    ))
                    if figures.count >= maxFigures { break }
                }
            }

            return RagSearchResult(results: chunks, figures: figures)
        } catch {
            return RagSearchResult()
        }
    }

    /// Formats the textbook excerpts into system prompt context.
    public func buildContext(results: [RagChunk], figures: [RagFigure] = []) -> String {
        guard !results.isEmpty else { return "" }
        var out = "BOOK LIBRARY EXCERPTS (MediGyaan ingestion corpus — treat as your primary source):\n\n"
        var len = out.count
        var count = 0

        for r in results {
            let text = r.text.trimmingCharacters(in: .whitespacesAndNewlines)
            if text.isEmpty { continue }
            count += 1
            let sectionStr = r.section.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "" : " | section: \(r.section)"
            let header = "[\(count)] \(r.book) — \(r.page)\(sectionStr)\n"
            let block = "\(header)\(text)\n\n"
            if len + block.count > maxContextChars { break }
            out += block
            len += block.count
        }
        if count == 0 { return "" }

        out += "Cite sources inline as (Book Title, p. X) exactly as given above. Use these excerpts together "
        out += "with your own medical knowledge; when an excerpt directly answers the question, prefer it and "
        out += "name its book and page. Keep every inline citation's book title spelled exactly as in the excerpt."

        if !figures.isEmpty {
            out += "\n\nFIGURES AVAILABLE FOR THIS ANSWER (a gallery of these is shown automatically below your reply):\n"
            for (i, f) in figures.enumerated() {
                let cap = f.caption.trimmingCharacters(in: .whitespacesAndNewlines)
                let label = f.label.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "Figure" : f.label
                let captionStr = cap.isEmpty ? "Medical Illustration" : cap
                out += "[\(i + 1)] \(label) — \(captionStr) (p. \(f.page))\n"
            }
        }
        return out
    }

    /// Replaces inline `(Book Title, p. X)` citations with clickable marker tokens `[RAGLINK:bookId:page:pages|label]`.
    public func linkifyCitations(reply: String, results: [RagChunk]) -> String {
        var text = reply
        guard !text.isEmpty, !results.isEmpty else { return text }

        for r in results {
            let book = r.book.trimmingCharacters(in: .whitespacesAndNewlines)
            let page = r.page.trimmingCharacters(in: .whitespacesAndNewlines)
            let bid = r.bookId.trimmingCharacters(in: .whitespacesAndNewlines)
            if book.isEmpty || bid.isEmpty { continue }

            let digits = page.components(separatedBy: CharacterSet.decimalDigits.inverted).filter { !$0.isEmpty }
            guard let firstDigits = digits.first, let p1 = Int(firstDigits) else { continue }
            let pages = r.pages

            let escapedBook = NSRegularExpression.escapedPattern(for: book)
            let pattern = "(?i)(?:\\(\\s*)?\(escapedBook)\\s*,\\s*p\\.?\\s*\(p1)(?:\\s*[-–]\\s*\\d+)?(?:\\s*\\))?"
            let label = "\(book), p. \(p1)"
            let marker = citeMarker(bookId: bid, label: label, page: p1, pages: pages)

            if let regex = try? NSRegularExpression(pattern: pattern, options: []) {
                text = regex.stringByReplacingMatches(
                    in: text,
                    options: [],
                    range: NSRange(text.startIndex..., in: text),
                    withTemplate: NSRegularExpression.escapedTemplate(for: marker)
                )
            }
        }
        return text
    }

    private func citeMarker(bookId: String, label: String, page: Int, pages: Int) -> String {
        let cleanLabel = label.replacingOccurrences(of: "[", with: "").replacingOccurrences(of: "]", with: "")
        let cleanBid = bookId.lowercased().filter { ("0"..."9").contains($0) || ("a"..."f").contains($0) }
        return "[RAGLINK:\(cleanBid):\(page):\(pages)|\(cleanLabel)]"
    }

    /// Generates a "**Sources:** ..." footer from the results.
    public func sourcesFooter(results: [RagChunk]) -> String {
        var seen = Set<String>()
        var lines: [String] = []

        for r in results {
            let book = r.book.trimmingCharacters(in: .whitespacesAndNewlines)
            let page = r.page.trimmingCharacters(in: .whitespacesAndNewlines)
            if book.isEmpty { continue }
            let key = "\(book)|\(page)"
            if seen.contains(key) { continue }
            seen.insert(key)

            let digits = page.components(separatedBy: CharacterSet.decimalDigits.inverted).filter { !$0.isEmpty }
            let p1 = Int(digits.first ?? "1") ?? 1
            let label = book + (page.isEmpty ? "" : ", \(page)")
            lines.append(citeMarker(bookId: r.bookId, label: label, page: p1, pages: r.pages))
        }
        if lines.isEmpty { return "" }
        return "**Sources:** " + lines.prefix(6).joined(separator: "  •  ")
    }

    /// Appends `[RAGFIG:...]` markers to the reply text for downstream extraction and UI display.
    public func figureMarkers(figures: [RagFigure]) -> String {
        guard !figures.isEmpty else { return "" }
        let clean: (String) -> String = { s in
            s.trimmingCharacters(in: .whitespacesAndNewlines)
                .replacingOccurrences(of: #"\s+"#, with: " ", options: .regularExpression)
                .replacingOccurrences(of: "[", with: "")
                .replacingOccurrences(of: "]", with: "")
                .replacingOccurrences(of: "|", with: "")
        }

        var lines: [String] = []
        for f in figures.prefix(maxFigures) {
            let bid = f.bookId.lowercased().filter { ("0"..."9").contains($0) || ("a"..."f").contains($0) }
            guard !bid.isEmpty, f.page > 0 else { continue }
            let label = clean(f.label.isEmpty ? "Figure" : f.label)
            let cap = clean(f.caption.isEmpty ? "Medical Illustration" : f.caption)
            let path = f.path.trimmingCharacters(in: .whitespacesAndNewlines)
            let book = clean(f.book)
            lines.append("[RAGFIG:\(bid):\(f.page)|\(label)|\(cap)|\(path)|\(book)]")
        }
        return lines.isEmpty ? "" : "\n\n" + lines.joined(separator: "\n")
    }

    /// Extracts RAG book sources, links, and figures for UI card rendering.
    /// Ports Android's `extractRagBookSources` from `AiChatActivity.kt`.
    public static func extractRagBookSources(ownerTurn: Int, content: String) -> [RagBookSource] {
        guard !content.isEmpty else { return [] }

        // [RAGFIG:bid:page|label|caption|path|book]
        let figPattern = #"\b?\[RAGFIG:([^:]+):(\d+)\|([^|]*)\|([^|]*)\|([^|]*)\|([^\]]*)\]"#
        var figures: [ChatFigureJson] = []
        if let figRegex = try? NSRegularExpression(pattern: figPattern, options: []) {
            let nsContent = content as NSString
            let matches = figRegex.matches(in: content, options: [], range: NSRange(location: 0, length: nsContent.length))
            for m in matches {
                guard m.numberOfRanges >= 7 else { continue }
                let bid = nsContent.substring(with: m.range(at: 1))
                let page = nsContent.substring(with: m.range(at: 2))
                let label = nsContent.substring(with: m.range(at: 3))
                let caption = nsContent.substring(with: m.range(at: 4))
                let path = nsContent.substring(with: m.range(at: 5))
                let book = nsContent.substring(with: m.range(at: 6))
                figures.append(ChatFigureJson(
                    figureNumber: label,
                    title: label,
                    caption: caption,
                    imageSearchQuery: "",
                    imageUrl: path,
                    bookReference: book,
                    pages: page,
                    sourceUrl: bid
                ))
            }
        }

        // [RAGLINK:bid:page:pages|label]
        let linkPattern = #"\b?\[RAGLINK:([^:]+):(\d+):(\d+)\|([^\]]+)\]"#
        var links: [(bid: String, page: String, pages: String, label: String)] = []
        if let linkRegex = try? NSRegularExpression(pattern: linkPattern, options: []) {
            let nsContent = content as NSString
            let matches = linkRegex.matches(in: content, options: [], range: NSRange(location: 0, length: nsContent.length))
            for m in matches {
                guard m.numberOfRanges >= 5 else { continue }
                let bid = nsContent.substring(with: m.range(at: 1))
                let page = nsContent.substring(with: m.range(at: 2))
                let pages = nsContent.substring(with: m.range(at: 3))
                let label = nsContent.substring(with: m.range(at: 4))
                links.append((bid: bid, page: page, pages: pages, label: label))
            }
        }

        if figures.isEmpty && links.isEmpty { return [] }

        var linksByBook: [String: [(bid: String, page: String, pages: String, label: String)]] = [:]
        for l in links {
            linksByBook[l.bid, default: []].append(l)
        }

        var figuresByBook: [String: [ChatFigureJson]] = [:]
        for f in figures {
            figuresByBook[f.sourceUrl, default: []].append(f)
        }

        let allBookIds = Array(Set(Array(linksByBook.keys) + Array(figuresByBook.keys)))
        var bookSources: [RagBookSource] = []
        for bid in allBookIds {
            let bLinks = linksByBook[bid] ?? []
            let bFigures = figuresByBook[bid] ?? []
            let rawTitle = bLinks.first?.label.components(separatedBy: ",").first ?? bFigures.first?.bookReference ?? "Medical Textbook"
            let bookTitle = rawTitle.trimmingCharacters(in: .whitespacesAndNewlines)
            let pageNum = bLinks.first?.page ?? bFigures.first?.pages ?? "1"

            bookSources.append(
                RagBookSource(
                    ownerTurn: ownerTurn,
                    bookId: bid,
                    bookTitle: bookTitle,
                    pageNumber: pageNum,
                    subject: "NEET PG High-Yield Reference",
                    authors: "Standard Medical Textbook",
                    publisher: "MediGyaan Library",
                    extractedText: bid,
                    figures: bFigures
                )
            )
        }
        return bookSources
    }
}
