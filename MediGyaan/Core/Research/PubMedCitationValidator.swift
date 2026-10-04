import Foundation

// MARK: - Regex support

/// Small cache around `NSRegularExpression`.
///
/// Android recompiles each `Regex(...)` literal at every call site. In Swift the
/// patterns are runtime string literals, so they are compiled once and reused.
/// `NSRegularExpression` matching is thread-safe and every helper below is a
/// pure function of its input, so caching cannot change any result.
private final class RegexCache: @unchecked Sendable {
    static let shared = RegexCache()

    private var cache: [String: NSRegularExpression] = [:]
    private let lock = NSLock()

    func regex(_ pattern: String, options: NSRegularExpression.Options = []) -> NSRegularExpression? {
        let key = "\(options.rawValue)\u{0}\(pattern)"
        lock.lock()
        defer { lock.unlock() }
        if let cached = cache[key] { return cached }
        guard let compiled = try? NSRegularExpression(pattern: pattern, options: options) else {
            return nil
        }
        cache[key] = compiled
        return compiled
    }
}

/// First match of `pattern` in `text`, or `nil`.
func firstMatch(
    _ pattern: String,
    in text: String,
    options: NSRegularExpression.Options = []
) -> NSTextCheckingResult? {
    let range = NSRange(text.startIndex..., in: text)
    return RegexCache.shared.regex(pattern, options: options)?.firstMatch(in: text, range: range)
}

/// Whether `pattern` matches anywhere in `text`. Mirrors Kotlin's
/// `Regex.containsMatchIn`.
func matchesAnywhere(
    _ pattern: String,
    in text: String,
    options: NSRegularExpression.Options = []
) -> Bool {
    firstMatch(pattern, in: text, options: options) != nil
}

/// Substitutes every occurrence of `pattern` in `text`. Mirrors Kotlin's
/// `String.replace(Regex, String)`.
func replacingAll(
    _ pattern: String,
    with replacement: String,
    in text: String,
    options: NSRegularExpression.Options = []
) -> String {
    guard let regex = RegexCache.shared.regex(pattern, options: options) else { return text }
    let range = NSRange(text.startIndex..., in: text)
    return regex.stringByReplacingMatches(in: text, range: range, withTemplate: replacement)
}

extension String {
    /// `components(separatedBy:)` for a regex delimiter.
    ///
    /// Kotlin's `String.split(Regex)` discards empty fields and treats a
    /// multi-character pattern as one delimiter, so `.split(Regex("\\s+"))`
    /// collapses runs of whitespace. `components(separatedBy:)` does neither,
    /// which would change every token count and query built from it — so the
    /// regex form is used throughout the validator instead.
    func components(separatedByPattern pattern: String) -> [String] {
        guard let regex = RegexCache.shared.regex(pattern) else { return [self] }
        let matches = regex.matches(in: self, range: NSRange(startIndex..., in: self))
        guard !matches.isEmpty else { return [self] }

        var pieces: [String] = []
        var cursor = startIndex
        for match in matches {
            guard let matched = Range(match.range, in: self) else { continue }
            pieces.append(String(self[cursor ..< matched.lowerBound]))
            cursor = matched.upperBound
        }
        pieces.append(String(self[cursor...]))
        return pieces.filter { !$0.isEmpty }
    }
}

/// Kotlin's `maxByOrNull`, which returns the **first** of several equal maxima.
///
/// Swift's `Sequence.max(by:)` does not promise which tied element it returns,
/// so the tie-break is written out rather than inherited.
func kotlinMax<T: Sequence>(_ elements: T, by areInIncreasingOrder: (T.Element, T.Element) -> Bool) -> T.Element? {
    var best: T.Element?
    for element in elements {
        guard let current = best else {
            best = element
            continue
        }
        if areInIncreasingOrder(current, element) {
            best = element
        }
    }
    return best
}

// MARK: - Models

/// A single line the detector believes might be a citation.
struct CitationEntry: Hashable, Sendable {
    let text: String
    /// Retained for parity with Android, where nothing in the validator sets it
    /// either — the detector derives the same information from the line itself.
    let startsWithNumber: Bool

    init(_ text: String, startsWithNumber: Bool = false) {
        self.text = text
        self.startsWithNumber = startsWithNumber
    }
}

/// One reference after validation.
///
/// `found == false` means PubMed could not match the reference. That is not the
/// same as the reference being wrong: paywalled, non-indexed and badly typed
/// citations all land here.
struct ValidationResult: Sendable {
    let index: Int
    let originalText: String
    let found: Bool
    let pmid: String
    let doi: String?
    let articleTitle: String
    let canonicalReference: String

    init(
        index: Int,
        originalText: String,
        found: Bool,
        pmid: String = "",
        doi: String? = nil,
        articleTitle: String = "",
        canonicalReference: String = ""
    ) {
        self.index = index
        self.originalText = originalText
        self.found = found
        self.pmid = pmid
        self.doi = doi
        self.articleTitle = articleTitle
        self.canonicalReference = canonicalReference
    }
}

/// Live progress of a validation run.
struct ValidationProgress: Sendable {
    let status: String
    let current: Int
    let total: Int
}

/// A resolved PubMed record.
struct PubMedMatch: Sendable {
    let pmid: String
    let doi: String?
    let articleTitle: String
    let canonicalReference: String
}

/// Clues harvested from a raw citation line, used to build search queries and to
/// score candidates.
struct SearchHints: Sendable {
    var doi: String?
    var year: String?
    var titleHint: String?
    var titleCandidates: [String] = []
    var authorHint: String?
    var cleanedText: String = ""
}

// MARK: - Text analysis

/// Pure citation parsing, hint extraction and scoring, ported from the Android
/// `model/PubMedCitationValidator.kt`.
///
/// Deliberately free of I/O and shared state so the detection rules stay
/// unit-testable, matching the split in the Kotlin object between its text
/// helpers and its `suspend` functions. ``PubMedCitationService`` owns the
/// network half.
///
/// ## Score thresholds
/// These are the Thesis Analyzer's thresholds, kept identical on purpose so the
/// two platforms accept and reject the same references:
///
/// | Constant | Value | Meaning |
/// | --- | --- | --- |
/// | `exactMatchScore` | 90 | accept immediately and stop querying |
/// | `minimumSearchScore` | 45 | floor for a text-search match |
/// | `minimumTitleTokenOverlap` | 15 | floor for short titles |
enum PubMedCitationValidator {

    // MARK: Thresholds

    static let exactMatchScore = 90
    static let minimumSearchScore = 45
    static let minimumTitleTokenOverlap = 15

    /// Points awarded per shared significant token.
    private static let tokenWeight = 5
    /// Only tokens at least this long count towards overlap — shorter words are
    /// too common to be evidence.
    private static let minimumTokenLength = 4
    /// Cap on contributing source tokens, matching Android's `.take(20)`: stops
    /// one very long reference from matching everything.
    private static let maximumSourceTokens = 20
    /// Cap on retained title candidates.
    private static let maximumTitleCandidates = 5
    /// Cap on articles requested per query.
    static let searchResultLimit = 10
    /// PMIDs per `esummary` request. NCBI caps this server-side.
    static let summaryBatchSize = 80

    // MARK: Patterns

    enum Pattern {
        static let bracketedNumber = #"^\s*\[\d+]\s*"#
        static let numberedMarker = #"^\s*\d+\s*[.)-]\s*"#
        static let bulletMarker = #"^\s*[-•*]\s+"#
        static let anyLeadingMarker = #"^\s*\[?\d+]?\s*[.)-]?\s*"#
        static let startsNumbered = #"^\s*\[?\d+]?\s*[.)-]\s*"#
        static let wrappedContinuation = #"^\s*\(?\d{2,4}[;,:.)-]"#
        static let bareNumberedMarker = #"^\s*\d+[.)]\s*"#
        static let pmidMarker = #"(?i)\bPMID\s*:?\s*\d{4,12}\b"#
        static let pmidCapture = #"(?i)\bPMID\s*:?\s*(\d{4,12})\b"#
        static let stripPMID = #"(?i)\bPMID\s*:?\s*\d{4,12}\b\.?"#
        static let doiMarker = #"\b10\.\d{4,9}/\S+"#
        static let doiCapture = #"(?i)10\.\d{4,9}/[^\s<>"']+"#
        static let stripDOI = #"(?i)\bDOI\s*:?\s*10\.\d{4,9}/[^\s<>"']+\.?"#
        static let year = #"\b(19|20)\d{2}\b"#
        static let yearLoose = #"\b(19|20)\d{2}"#
        static let etAl = #"(?i)et al\."#
        static let whitespace = #"\s+"#
        static let digitsOnly = #"^\d{4,12}$"#
        static let sentenceBreak = #"\.\s+"#
        static let dotOrSemicolon = #"[.;]"#
    }

    private static let terminalPunctuation = CharacterSet(charactersIn: ".,;")
    private static let wrappingPunctuation = CharacterSet(charactersIn: ".,;:()[]")

    // MARK: - Detection

    /// Splits multi-line text into citation candidates, merging wrapped
    /// continuation lines back into the citation they belong to.
    ///
    /// - Returns: `[]` unless there are at least two candidate lines. A lone
    ///   line is never treated as a reference list.
    static func extractCitationEntries(_ text: String) -> [CitationEntry] {
        let cleanedLines = normaliseNewlines(text)
            .components(separatedBy: "\n")
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
            .filter { line in
                // Drop a trailing "References:" heading before parsing.
                let heading = line
                    .trimmingCharacters(in: .whitespacesAndNewlines)
                    .lowercased()
                    .trimmingCharacters(in: CharacterSet(charactersIn: ":."))
                return !["references", "citations", "bibliography", "sources"].contains(heading)
            }

        guard cleanedLines.count >= 2 else { return [] }

        var entries: [CitationEntry] = []
        var pending = ""

        func flush() {
            let trimmed = pending.trimmingCharacters(in: .whitespacesAndNewlines)
            if !trimmed.isEmpty {
                entries.append(CitationEntry(trimmed))
            }
            pending = ""
        }

        for line in cleanedLines {
            // Android applies these anchored patterns in sequence to the result
            // of the previous one, so "[1] 2. Doe" loses both markers.
            var stripped = replacingAll(Pattern.bracketedNumber, with: "", in: line)
            stripped = replacingAll(Pattern.numberedMarker, with: "", in: stripped)
            stripped = replacingAll(Pattern.bulletMarker, with: "", in: stripped)
            stripped = stripped.trimmingCharacters(in: .whitespacesAndNewlines)

            if stripped.isEmpty { continue }

            if !pending.isEmpty {
                // A fresh physical line either continues the pending citation
                // (wrapped text) or begins a new one. Wrapped continuations
                // almost always start lowercase, or with a bare year or page.
                let startsNumbered = matchesAnywhere(Pattern.startsNumbered, in: line)
                let looksWrapped = startsWithLowercase(stripped)
                    || matchesAnywhere(Pattern.wrappedContinuation, in: stripped)
                    || stripped.count <= 2
                if startsNumbered || !looksWrapped {
                    flush()
                }
            }

            if !pending.isEmpty {
                pending.append(" ")
            }
            pending.append(stripped)
        }
        flush()

        return entries
    }

    /// Whether `text` looks like a pasted reference list — the trigger the chat
    /// uses to offer validation.
    ///
    /// Conservative by design: an explicit PMID or DOI anywhere, several
    /// numbered lines, or a mix of long lines carrying years plus an "et al.".
    static func looksLikeReferenceBlock(_ text: String) -> Bool {
        if text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty { return false }

        let lines = normaliseNewlines(text)
            .components(separatedBy: "\n")
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }

        guard lines.count >= 2 else { return false }

        var numbered = 0
        var explicitMarker = false
        var withYear = 0
        var withEtAl = 0

        for line in lines {
            if matchesAnywhere(Pattern.bracketedNumber, in: line)
                || matchesAnywhere(Pattern.bareNumberedMarker, in: line) {
                numbered += 1
            }
            if matchesAnywhere(Pattern.pmidMarker, in: line) { explicitMarker = true }
            if matchesAnywhere(Pattern.doiMarker, in: line) { explicitMarker = true }
            if matchesAnywhere(Pattern.yearLoose, in: line) && line.count >= 30 { withYear += 1 }
            if matchesAnywhere(Pattern.etAl, in: line) { withEtAl += 1 }
        }

        return explicitMarker
            || numbered >= 2
            || (withYear >= 2 && withEtAl >= 1)
            || withYear >= 3
    }

    // MARK: - Reference text helpers

    /// Removes `PMID:`/`DOI:` annotations, collapses whitespace and trims
    /// trailing punctuation.
    static func stripReferenceMetadata(_ text: String) -> String {
        var result = replacingAll(Pattern.stripPMID, with: "", in: text)
        result = replacingAll(Pattern.stripDOI, with: "", in: result)
        result = replacingAll(Pattern.whitespace, with: " ", in: result)
        result = result.trimmingCharacters(in: .whitespacesAndNewlines)
        result = result.trimmingCharacters(in: terminalPunctuation)
        return result.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    /// The PMID carried by `text`, or `""`.
    ///
    /// Falls back to treating the whole string as a PMID when it is nothing but
    /// 4–12 digits, which is how a bare identifier pasted into the chat is
    /// handled.
    static func extractPmid(_ text: String) -> String {
        if let match = firstMatch(Pattern.pmidCapture, in: text),
           let range = Range(match.range(at: 1), in: text) {
            return String(text[range])
        }
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        if matchesAnywhere(Pattern.digitsOnly, in: trimmed) {
            return trimmed
        }
        return ""
    }

    /// The first DOI in `text` with trailing punctuation trimmed, or `nil`.
    static func extractDoi(_ text: String) -> String? {
        guard let match = firstMatch(Pattern.doiCapture, in: text),
              let range = Range(match.range, in: text) else {
            return nil
        }
        let value = String(text[range]).trimmingCharacters(in: terminalPunctuation)
        return value.isEmpty ? nil : value
    }

    // MARK: - Scoring

    /// Heuristic score for a candidate against the clues in a citation.
    static func score(_ match: PubMedMatch, hints: SearchHints) -> Int {
        var total = 0

        let canonical = normalise(match.canonicalReference)
        let articleTitle = normalise(match.articleTitle)
        let titleHint = normalise(hints.titleHint ?? "")
        let cleaned = normalise(hints.cleanedText)
        let year = hints.year ?? ""

        if let hintDOI = hints.doi,
           let matchDOI = match.doi,
           normalise(hintDOI) == normalise(matchDOI) {
            total += 100
        }
        if !year.isEmpty && canonical.contains(year) {
            total += 20
        }

        // Best overlap across every candidate title, falling back to the primary
        // title hint when no candidate survived filtering.
        let overlaps = hints.titleCandidates.map { candidate -> Int in
            let normalisedCandidate = normalise(candidate)
            return max(
                tokenOverlap(normalisedCandidate, articleTitle),
                tokenOverlap(normalisedCandidate, canonical)
            )
        }
        let bestTitleOverlap = overlaps.max() ?? tokenOverlap(titleHint, articleTitle)

        total += bestTitleOverlap * 2
        total += tokenOverlap(cleaned, articleTitle)
        total += tokenOverlap(cleaned, canonical) / 2

        // A 30-character verbatim run is strong evidence of the right article.
        if hints.titleCandidates.contains(where: { candidate in
            let normalisedCandidate = normalise(candidate)
            return normalisedCandidate.count >= 30
                && articleTitle.contains(String(normalisedCandidate.prefix(30)))
        }) {
            total += 30
        }
        if !titleHint.isEmpty && canonical.contains(String(titleHint.prefix(40))) {
            total += 10
        }
        if !cleaned.isEmpty && canonical.contains(String(cleaned.prefix(40))) {
            total += 10
        }

        return total
    }

    /// Whether a candidate is good enough to report as found.
    ///
    /// The required overlap scales with title length: a short title cannot
    /// produce many overlapping tokens, so a flat threshold would reject
    /// everything.
    static func acceptableMatch(_ match: PubMedMatch, hints: SearchHints) -> Bool {
        let canonical = normalise(match.canonicalReference)
        let articleTitle = normalise(match.articleTitle)
        let titleHint = normalise(hints.titleHint ?? "")
        let cleaned = normalise(hints.cleanedText)
        let candidateScore = score(match, hints: hints)

        // An exact DOI match is proof on its own.
        if let hintDOI = hints.doi,
           let matchDOI = match.doi,
           normalise(hintDOI) == normalise(matchDOI) {
            return true
        }

        let longestCandidate = kotlinMax(hints.titleCandidates) {
            searchableTokenCount($0) < searchableTokenCount($1)
        }
        let bestTitle = longestCandidate ?? hints.titleHint ?? ""
        let normalisedBest = normalise(bestTitle)

        if !normalisedBest.isEmpty {
            let titleOverlap = max(
                tokenOverlap(normalisedBest, articleTitle),
                tokenOverlap(normalisedBest, canonical)
            )
            let tokenCount = searchableTokenCount(normalisedBest)
            let required: Int
            if tokenCount <= 3 {
                required = 10
            } else if tokenCount <= 6 {
                required = minimumTitleTokenOverlap
            } else {
                required = 20
            }
            let hasPhrase = normalisedBest.count >= 30
                && (articleTitle.contains(String(normalisedBest.prefix(30)))
                    || canonical.contains(String(normalisedBest.prefix(30))))
            return candidateScore >= minimumSearchScore && (titleOverlap >= required || hasPhrase)
        }

        return candidateScore >= exactMatchScore
            && tokenOverlap(cleaned, canonical) >= minimumTitleTokenOverlap
    }

    // MARK: - Shared primitives

    /// Number of significant tokens (length >= 4) in `text`.
    static func searchableTokenCount(_ text: String) -> Int {
        text.components(separatedByPattern: Pattern.whitespace)
            .filter { $0.count >= minimumTokenLength }
            .count
    }

    /// Whitespace-collapsed, lowercased form used for every comparison.
    static func normalise(_ text: String) -> String {
        replacingAll(Pattern.whitespace, with: " ", in: text)
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .lowercased()
    }

    /// ``tokenWeight`` points per significant token present on both sides.
    static func tokenOverlap(_ source: String, _ target: String) -> Int {
        if source.isEmpty || target.isEmpty { return 0 }

        let sourceTokens = Set(
            source.components(separatedByPattern: Pattern.whitespace)
                .filter { $0.count >= minimumTokenLength }
                .prefix(maximumSourceTokens)
        )
        let targetTokens = Set(
            target.components(separatedByPattern: Pattern.whitespace)
                .filter { $0.count >= minimumTokenLength }
        )

        if sourceTokens.isEmpty || targetTokens.isEmpty { return 0 }
        return sourceTokens.intersection(targetTokens).count * tokenWeight
    }

    // MARK: - Hints

    /// Harvests DOI, year, author fragment and candidate titles from a citation.
    static func buildHints(_ referenceText: String) -> SearchHints {
        var cleaned = replacingAll(Pattern.anyLeadingMarker, with: "", in: referenceText)
        cleaned = replacingAll(Pattern.whitespace, with: " ", in: cleaned)
        cleaned = cleaned.trimmingCharacters(in: .whitespacesAndNewlines)

        let doi = substring(Pattern.doiCapture, in: cleaned)
        let year = substring(Pattern.year, in: cleaned)

        // In a Vancouver-style reference the authors sit before the first period.
        let authorFragment = cleaned.prefix(while: { $0 != "." })
        let trimmedAuthor = authorFragment.trimmingCharacters(in: .whitespacesAndNewlines)

        let titleCandidates = extractTitleCandidates(cleaned)

        return SearchHints(
            doi: doi,
            year: year,
            titleHint: titleCandidates.first,
            titleCandidates: titleCandidates,
            authorHint: trimmedAuthor.isEmpty ? nil : trimmedAuthor,
            cleanedText: cleaned
        )
    }

    /// Guesses which segments of a reference are the article title.
    ///
    /// A title candidate is a run of at least three words containing letters,
    /// with no four-digit year and no "doi"/"pmid". Candidates are gathered from
    /// the segments *after* the first (skipping the author block) and then from
    /// all segments, so a reference without a clean author/title split still
    /// yields something.
    static func extractTitleCandidates(_ referenceText: String) -> [String] {
        var cleaned = replacingAll(Pattern.stripPMID, with: "", in: referenceText)
        cleaned = replacingAll(Pattern.stripDOI, with: "", in: cleaned)
        cleaned = replacingAll(Pattern.whitespace, with: " ", in: cleaned)
        cleaned = cleaned.trimmingCharacters(in: .whitespacesAndNewlines)
        cleaned = cleaned.trimmingCharacters(in: terminalPunctuation)

        let segments = cleaned
            .components(separatedByPattern: Pattern.sentenceBreak)
            .map { segment -> String in
                var value = segment.trimmingCharacters(in: .whitespacesAndNewlines)
                while let last = value.last, terminalPunctuation.contains(last) {
                    value.removeLast()
                }
                return value
            }
            .filter { !$0.isEmpty }

        // Insertion-ordered set: a segment is kept the first time it qualifies.
        var candidates: [String] = []
        var seen = Set<String>()
        func append(_ segment: String) {
            guard looksLikeTitle(segment), !seen.contains(segment) else { return }
            seen.insert(segment)
            candidates.append(segment)
        }

        for segment in segments.dropFirst() { append(segment) }
        for segment in segments { append(segment) }

        // Fallback: the most word-rich semicolon-delimited segment.
        let bySemicolon = cleaned
            .components(separatedByPattern: Pattern.dotOrSemicolon)
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { looksLikeTitle($0) }
        if let longest = kotlinMax(bySemicolon, by: { searchableTokenCount($0) < searchableTokenCount($1) }),
           !longest.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            append(longest)
        }

        var normalised: [String] = []
        var finalSeen = Set<String>()
        for candidate in candidates {
            var value = replacingAll(Pattern.whitespace, with: " ", in: candidate)
            value = value.trimmingCharacters(in: .whitespacesAndNewlines)
            value = value.trimmingCharacters(in: terminalPunctuation)
            guard searchableTokenCount(value) >= 3 || value.count >= 20 else { continue }
            guard !finalSeen.contains(value) else { continue }
            finalSeen.insert(value)
            normalised.append(value)
        }
        return Array(normalised.prefix(maximumTitleCandidates))
    }

    /// Whether a segment could plausibly be an article title.
    static func looksLikeTitle(_ segment: String) -> Bool {
        let normalised = normalise(segment)
        if normalised.isEmpty { return false }
        // A year means this is the journal/date clause rather than the title.
        if matchesAnywhere(Pattern.year, in: segment) { return false }
        if normalised.contains("doi") || normalised.contains("pmid") { return false }
        let wordTokens = segment
            .components(separatedByPattern: Pattern.whitespace)
            .filter { $0.contains(where: { $0.isLetter }) }
        return wordTokens.count >= 3
    }

    /// Ordered, de-duplicated queries derived from the hints.
    ///
    /// Most confident first — a quoted exact title runs before a bare author
    /// string — so the query that can short-circuit on ``exactMatchScore`` is the
    /// one attempted first.
    static func buildQueries(_ hints: SearchHints) -> [String] {
        var queries: [String] = []
        var seen = Set<String>()
        func append(_ query: String) {
            guard !query.isEmpty, !seen.contains(query) else { return }
            seen.insert(query)
            queries.append(query)
        }

        if let doi = hints.doi, !doi.isEmpty {
            append("\"\(doi)\"")
            append(doi)
        }

        for title in hints.titleCandidates {
            let cleanTitle = String(title.prefix(220))
            append("\"\(cleanTitle.prefix(160))\"")
            if let year = hints.year, !year.isEmpty {
                append("\"\(cleanTitle.prefix(140))\" AND \(year)[dp]")
            }
            append(cleanTitle)
            if let author = hints.authorHint, !author.isEmpty {
                append("\(author.prefix(80)) \(cleanTitle.prefix(120))")
            }
        }

        if let author = hints.authorHint, !author.isEmpty {
            append(String(author.prefix(180)))
        }

        let source = hints.titleHint ?? hints.cleanedText
        let words = source
            .components(separatedByPattern: Pattern.whitespace)
            .map { $0.trimmingCharacters(in: wrappingPunctuation) }
            .filter { $0.count >= 4 && !$0.allSatisfy(\.isNumber) }
            .prefix(10)
            .map { $0 }

        if !words.isEmpty {
            let joined = words.joined(separator: " ")
            append(joined)
            if let year = hints.year, !year.isEmpty {
                append("\(joined) AND \(year)[dp]")
            }
            append(words.prefix(6).joined(separator: " "))
        }

        let compact = String(hints.cleanedText.prefix(220))
        if !compact.isEmpty {
            append(compact)
        }

        return queries
    }

    // MARK: - Private helpers

    private static func substring(_ pattern: String, in text: String) -> String? {
        guard let match = firstMatch(pattern, in: text),
              let range = Range(match.range, in: text) else {
            return nil
        }
        return String(text[range])
    }

    private static func normaliseNewlines(_ text: String) -> String {
        text.replacingOccurrences(of: "\r\n", with: "\n")
    }

    private static func startsWithLowercase(_ text: String) -> Bool {
        guard let first = text.first else { return false }
        return first.isLowercase || first == "(" || first == "["
    }
}