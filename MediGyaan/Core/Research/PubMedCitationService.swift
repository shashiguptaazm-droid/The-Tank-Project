import Foundation

/// Network half of the PubMed citation validator, ported from the Android
/// `model/PubMedCitationValidator.kt`.
///
/// Talks to NCBI E-utilities directly rather than through the app's own backend:
/// `esearch` and `esummary` are public, unauthenticated and key-free, so there
/// is nothing to proxy and no credential to protect. The text rules and scoring
/// live in ``PubMedCitationValidator``; this type owns the caches, the rate
/// limiter and the HTTP calls.
///
/// An `actor` because Android shares one process-wide mutable state (two
/// `ConcurrentHashMap` caches plus `lastRequestAt`) between concurrent
/// coroutines. The serialised access here is the equivalent guarantee.
///
/// ## Rate limiting
/// NCBI allows 3 requests/second without an API key. Exceeding it earns an
/// HTTP 429 and, if sustained, an IP block — so requests are spaced by
/// ``minimumIntervalMilliseconds`` rather than relying on retries.
actor PubMedCitationService {

    static let shared = PubMedCitationService()

    /// NCBI's unauthenticated ceiling is 3 req/s; Android spaces requests 180ms
    /// apart, which sits just inside it.
    private static let minimumIntervalMilliseconds = 180.0

    private static let eutilsBase = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

    private var pmidCache: [String: PubMedMatch] = [:]
    private var searchCache: [String: PubMedMatch] = [:]
    private var lastRequestAt = Date.distantPast

    // MARK: - Public API

    /// Validates each citation against PubMed, reporting progress as it goes.
    ///
    /// Sequential rather than concurrent on purpose: parallel lookups would trip
    /// NCBI's rate limit, and the progress callback implies one-at-a-time
    /// reporting anyway.
    func validate(
        _ entries: [CitationEntry],
        onProgress: @Sendable (ValidationProgress) -> Void = { _ in }
    ) async -> [ValidationResult] {
        guard !entries.isEmpty else { return [] }

        var results: [ValidationResult] = []
        let total = entries.count

        for (index, entry) in entries.enumerated() {
            let label = "\(index + 1)/\(total)"
            onProgress(
                ValidationProgress(
                    status: "Verifying PubMed reference \(label)",
                    current: index,
                    total: total
                )
            )
            let result = await resolve(entry, index: index)
            results.append(result)
            onProgress(
                ValidationProgress(
                    status: result.found
                        ? "PubMed reference found \(label)"
                        : "No PubMed match \(label)",
                    current: index + 1,
                    total: total
                )
            )
        }

        return results
    }

    /// Looks up a single PMID, verifying it exists rather than trusting it.
    ///
    /// Used by the Thesis tools, which have a PMID but still need the canonical
    /// citation and DOI.
    func fetchByPmid(_ pmid: String) async -> PubMedMatch? {
        let trimmed = pmid.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        if let cached = pmidCache[trimmed] { return cached }
        return await fetchByPmids([trimmed])[trimmed]
    }

    /// Clears both caches. Exposed for tests and for a manual refresh.
    func clearCaches() {
        pmidCache.removeAll()
        searchCache.removeAll()
    }

    // MARK: - Resolution

    private func resolve(_ entry: CitationEntry, index: Int) async -> ValidationResult {
        let raw = entry.text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !raw.isEmpty else {
            return ValidationResult(index: index, originalText: raw, found: false)
        }

        let stripped = PubMedCitationValidator.stripReferenceMetadata(raw)
        let cleanedForLookup = stripped.isEmpty ? raw : stripped

        // A supplied PMID is authoritative: verify it directly instead of
        // searching, so a correct PMID is never "lost" to a scoring miss.
        let suppliedPmid = PubMedCitationValidator.extractPmid(raw)
        if !suppliedPmid.isEmpty {
            guard let match = await fetchByPmid(suppliedPmid) else {
                return ValidationResult(index: index, originalText: raw, found: false)
            }
            return ValidationResult(
                index: index,
                originalText: raw,
                found: true,
                pmid: match.pmid,
                doi: match.doi,
                articleTitle: match.articleTitle,
                canonicalReference: canonicalReference(
                    cleanedForLookup: cleanedForLookup,
                    match: match
                )
            )
        }

        var match = await searchReference(cleanedForLookup)

        if match == nil {
            // The text search can miss even when the DOI is present verbatim, so
            // retry with the DOI alone — and only accept a hit that agrees with
            // the DOI we started from.
            let doi = PubMedCitationValidator.extractDoi(raw)
                ?? PubMedCitationValidator.extractDoi(stripped)
            if let doi, !doi.isEmpty,
               let doiMatch = await searchReference(doi),
               doiMatch.doi?.caseInsensitiveCompare(doi) == .orderedSame {
                match = doiMatch
            }
        }

        guard let match else {
            return ValidationResult(index: index, originalText: raw, found: false)
        }
        return ValidationResult(
            index: index,
            originalText: raw,
            found: true,
            pmid: match.pmid,
            doi: match.doi,
            articleTitle: match.articleTitle,
            canonicalReference: match.canonicalReference
        )
    }

    /// Rebuilds the user's own citation with a confirmed PMID appended, so the
    /// output stays recognisable as *their* reference rather than being replaced
    /// wholesale by PubMed's formatting.
    private func canonicalReference(cleanedForLookup: String, match: PubMedMatch) -> String {
        var value = cleanedForLookup.trimmingCharacters(in: .whitespacesAndNewlines)
        if value.isEmpty {
            value = match.canonicalReference
        }
        value = replacingAll(PubMedCitationValidator.Pattern.stripPMID, with: "", in: value)
        value = replacingAll(PubMedCitationValidator.Pattern.whitespace, with: " ", in: value)
        value = value.trimmingCharacters(in: .whitespacesAndNewlines)
        // Trims '.', ';', ',' but not whitespace, so a citation ending
        // `"Title ;"` yields `"Title . PMID: …"`. Android behaves the same way;
        // the extra trim that would fix it is deliberately not added.
        value = value.trimmingCharacters(in: CharacterSet(charactersIn: ".,;"))

        if value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            return match.canonicalReference
        }
        return "\(value). PMID: \(match.pmid)"
    }

    // MARK: - Searching

    private func searchReference(_ referenceText: String) async -> PubMedMatch? {
        let hints = PubMedCitationValidator.buildHints(referenceText)
        let cacheKey = String(PubMedCitationValidator.normalise(hints.cleanedText).prefix(240))
        if let cached = searchCache[cacheKey] { return cached }

        var candidates: [PubMedMatch] = []

        for query in PubMedCitationValidator.buildQueries(hints) {
            candidates.append(contentsOf: await searchMatches(query, hints: hints))

            if let best = bestCandidate(candidates, hints: hints),
               PubMedCitationValidator.score(best, hints: hints) >= PubMedCitationValidator.exactMatchScore {
                searchCache[cacheKey] = best
                return best
            }
        }

        guard let best = bestCandidate(candidates, hints: hints),
              PubMedCitationValidator.acceptableMatch(best, hints: hints) else {
            return nil
        }
        searchCache[cacheKey] = best
        return best
    }

    /// Highest-scoring candidate, keeping the first on ties as Kotlin does.
    private func bestCandidate(_ candidates: [PubMedMatch], hints: SearchHints) -> PubMedMatch? {
        kotlinMax(candidates) { left, right in
            PubMedCitationValidator.score(left, hints: hints)
                < PubMedCitationValidator.score(right, hints: hints)
        }
    }

    private func searchMatches(
        _ query: String,
        hints: SearchHints,
        limit: Int = PubMedCitationValidator.searchResultLimit
    ) async -> [PubMedMatch] {
        // `hints` is unused here on purpose: Android passes it for symmetry with
        // the thesis analyzer, and keeping the parameter documents that the two
        // implementations were compared line by line.
        _ = hints

        await throttle()
        guard let url = Self.esearchURL(query: query, limit: limit) else { return [] }
        guard let json = try? await HTTPClient.shared.getObject(toAbsolute: url) else { return [] }
        guard let searchResult = json["esearchresult"] as? [String: Any],
              let rawIdentifiers = searchResult["idlist"] as? [Any] else {
            return []
        }

        var seen = Set<String>()
        var identifiers: [String] = []
        for element in rawIdentifiers {
            guard let identifier = element as? String,
                  !identifier.isEmpty,
                  !seen.contains(identifier) else {
                continue
            }
            seen.insert(identifier)
            identifiers.append(identifier)
        }
        guard !identifiers.isEmpty else { return [] }

        let resolved = await fetchByPmids(identifiers)
        return identifiers.compactMap { resolved[$0] }
    }

    // MARK: - Summaries

    private func fetchByPmids(_ pmids: [String]) async -> [String: PubMedMatch] {
        var seen = Set<String>()
        var unique: [String] = []
        for pmid in pmids {
            let trimmed = pmid.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !trimmed.isEmpty, !seen.contains(trimmed) else { continue }
            seen.insert(trimmed)
            unique.append(trimmed)
        }
        guard !unique.isEmpty else { return [:] }

        var found: [String: PubMedMatch] = [:]
        for pmid in unique {
            if let cached = pmidCache[pmid] { found[pmid] = cached }
        }

        let missing = unique.filter { found[$0] == nil }
        guard !missing.isEmpty else { return found }

        for chunk in missing.chunked(into: PubMedCitationValidator.summaryBatchSize) {
            await throttle()
            guard let url = Self.esummaryURL(pmids: chunk) else { continue }
            guard let json = try? await HTTPClient.shared.getObject(toAbsolute: url),
                  let result = json["result"] as? [String: Any] else {
                continue
            }
            for pmid in chunk {
                guard let item = result[pmid] as? [String: Any],
                      let match = Self.parseSummaryItem(pmid: pmid, item: item) else {
                    continue
                }
                pmidCache[pmid] = match
                found[pmid] = match
            }
        }

        return found
    }

    /// Turns one `esummary` record into a match with a Vancouver-style
    /// canonical citation.
    ///
    /// Parsed by hand rather than through `Codable` because `esummary` returns
    /// a dynamic object whose keys *are* the PMIDs, and whose `articleids`
    /// entries vary by article type — a throw-on-mismatch decode would discard
    /// a valid record because one optional field was absent.
    private static func parseSummaryItem(pmid: String, item: [String: Any]) -> PubMedMatch? {
        let title = item["title"] as? String ?? ""
        let source = item["source"] as? String ?? ""
        let publicationDate = item["pubdate"] as? String ?? ""

        var doi: String?
        if let identifiers = item["articleids"] as? [Any] {
            for element in identifiers {
                guard let entry = element as? [String: Any] else { continue }
                let type = (entry["idtype"] as? String ?? "").lowercased()
                let value = entry["value"] as? String ?? ""
                if type == "doi", !value.isEmpty {
                    doi = value
                    break
                }
            }
        }

        var authors: [String] = []
        if let rawAuthors = item["authors"] as? [Any] {
            for element in rawAuthors {
                guard let entry = element as? [String: Any],
                      let name = entry["name"] as? String else {
                    continue
                }
                let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
                if !trimmed.isEmpty { authors.append(trimmed) }
                if authors.count == 3 { break }
            }
        }

        var canonical = ""
        if !authors.isEmpty {
            canonical += authors.joined(separator: ", ") + ". "
        }
        if !title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            canonical += title + ". "
        }
        canonical += source.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "PubMed" : source
        if !publicationDate.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            canonical += ". " + publicationDate
        }
        canonical += ". PMID: " + pmid
        if let doi, !doi.isEmpty {
            canonical += ". DOI: " + doi
        }

        return PubMedMatch(
            pmid: pmid,
            doi: doi,
            articleTitle: title,
            canonicalReference: canonical.trimmingCharacters(in: .whitespacesAndNewlines)
        )
    }

    // MARK: - Transport

    private func throttle() async {
        let elapsed = Date().timeIntervalSince(lastRequestAt) * 1000
        let wait = Self.minimumIntervalMilliseconds - elapsed
        if wait > 0 {
            try? await Task.sleep(nanoseconds: UInt64(wait * 1_000_000))
        }
        lastRequestAt = Date()
    }

    private static func esearchURL(query: String, limit: Int) -> URL? {
        var components = URLComponents(string: eutilsBase + "esearch.fcgi")
        components?.queryItems = [
            URLQueryItem(name: "db", value: "pubmed"),
            URLQueryItem(name: "retmode", value: "json"),
            URLQueryItem(name: "retmax", value: String(limit)),
            URLQueryItem(name: "term", value: query),
        ]
        return components?.url
    }

    private static func esummaryURL(pmids: [String]) -> URL? {
        var components = URLComponents(string: eutilsBase + "esummary.fcgi")
        components?.queryItems = [
            URLQueryItem(name: "db", value: "pubmed"),
            URLQueryItem(name: "retmode", value: "json"),
            URLQueryItem(name: "id", value: pmids.joined(separator: ",")),
        ]
        return components?.url
    }
}

extension Array {
    /// Splits into fixed-size chunks. The last chunk may be shorter.
    func chunked(into size: Int) -> [[Element]] {
        guard size > 0, !isEmpty else { return [] }
        return stride(from: 0, to: count, by: size).map { start in
            Array(self[start ..< Swift.min(start + size, count)])
        }
    }
}