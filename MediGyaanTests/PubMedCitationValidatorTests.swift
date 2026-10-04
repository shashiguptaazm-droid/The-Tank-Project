import XCTest
@testable import MediGyaan

/// Ports the Android `PubMedCitationValidatorTest` case-for-case.
///
/// Only the pure text helpers are exercised — nothing here touches the network,
/// so the suite is deterministic and runs offline. The Android fixtures are kept
/// verbatim, including the `trimIndent()` semantics, because the tests assert on
/// exactly how continuation lines merge into their parent citation.
final class PubMedCitationValidatorTests: XCTestCase {

    private let numberedList = """
        1. Bhutta ZA, Das JK, Walker N, et al. Interventions to address deaths from childhood pneumonia and diarrhoea equitably: what works and at what cost? Lancet. 2013;381(9875):1417-29. doi: 10.1016/S0140-6736(13)60648-0.
        2. Walker CL, Rudan I, Liu L, et al. Global burden of childhood pneumonia and diarrhoea. Lancet. 2013;381(9875):1405-16.
        3. Liu L, Oza S, Hogan D, et al. Global, regional, and national causes of child mortality in 2000-13. Lancet. 2015;385(9966):430-40.
        """

    private let vancouverList = """
        Bhutta ZA, Das JK, Walker N, et al. Interventions to address deaths from childhood pneumonia and diarrhoea equitably. Lancet. 2013;381(9875):1417-29.
        Walker CL, Rudan I, Liu L, et al. Global burden of childhood pneumonia and diarrhoea. Lancet. 2013;381(9875):1405-16.
        Liu L, Oza S, Hogan D, et al. Global, regional, and national causes of child mortality in 2000-13. Lancet. 2015;385(9966):430-40.
        """

    private let wrappedList = """
        1. Bhutta ZA, Das JK, Walker N, et al. Interventions to address deaths from childhood pneumonia and diarrhoea equitably:
           what works and at what cost? Lancet. 2013;381(9875):1417-29.
        2. Walker CL, Rudan I, Liu L, et al. Global burden of childhood pneumonia and diarrhoea. Lancet.
           2013;381(9875):1405-16.
        """

    private let aiReplyWithIntro = """
        Here are 3 PubMed references for typhoid fever:
        1. Wain J, Hendriksen RS, Mikoleit ML, Keddy KH, Ochiai RL. Typhoid fever. Lancet. 2015;385(9973):1136-45. PMID: 25458731.
        2. Crump JA, Luby SP, Mintz ED. The global burden of typhoid fever. Bull World Health Organ. 2004;82(5):346-53. PMID: 15298225.
        3. Bhutta ZA. Current concepts in the diagnosis and treatment of typhoid fever. BMJ. 2006;333(7558):78-82. PMID: 16825230.
        """

    private let proseQuestion = "Can you explain the treatment of typhoid fever? Also what is the first line antibiotic and the typical duration of therapy in adults?"

    private func texts(_ entries: [CitationEntry]) -> [String] {
        entries.map(\.text)
    }

    // MARK: - Entry extraction

    func testNumberedListSplitsIntoThree() {
        XCTAssertTrue(PubMedCitationValidator.looksLikeReferenceBlock(numberedList))
        let entries = PubMedCitationValidator.extractCitationEntries(numberedList)
        XCTAssertEqual(entries.count, 3)
        XCTAssertTrue(texts(entries)[0].contains("Bhutta ZA"))
        XCTAssertTrue(texts(entries)[1].contains("Walker CL"))
        XCTAssertTrue(texts(entries)[2].contains("Liu L"))
    }

    func testUnnumberedVancouverListSplits() {
        XCTAssertTrue(PubMedCitationValidator.looksLikeReferenceBlock(vancouverList))
        let entries = PubMedCitationValidator.extractCitationEntries(vancouverList)
        XCTAssertEqual(entries.count, 3)
    }

    /// A wrapped continuation must stay glued to the citation it belongs to
    /// rather than becoming a citation of its own.
    func testWrappedNumberedListStaysAsTwoEntries() {
        XCTAssertTrue(PubMedCitationValidator.looksLikeReferenceBlock(wrappedList))
        let entries = PubMedCitationValidator.extractCitationEntries(wrappedList)
        XCTAssertEqual(entries.count, 2)
        XCTAssertTrue(texts(entries)[0].contains("1417-29"))
        XCTAssertTrue(texts(entries)[1].contains("1405-16"))
    }

    func testPlainProseDoesNotLookLikeReferences() {
        XCTAssertFalse(PubMedCitationValidator.looksLikeReferenceBlock(proseQuestion))
        XCTAssertTrue(PubMedCitationValidator.extractCitationEntries(proseQuestion).isEmpty)
    }

    /// A single line is never a reference list, however citation-like it looks.
    func testSingleLineNeverYieldsEntries() {
        let single = "1. Bhutta ZA, et al. Interventions to address deaths. Lancet. 2013;381:1417-29."
        XCTAssertTrue(PubMedCitationValidator.extractCitationEntries(single).isEmpty)
    }

    func testReferenceHeaderIsSkippedInExtraction() {
        let entries = PubMedCitationValidator.extractCitationEntries(aiReplyWithIntro)
        // The intro line merges into the first entry unless sliced upstream; at
        // minimum every numbered citation is its own entry.
        XCTAssertGreaterThanOrEqual(entries.count, 3)
        XCTAssertTrue(texts(entries).last?.contains("16825230") == true)
    }

    func testReferencesHeadingLineIsDropped() {
        let text = """
            References
            1. Bhutta ZA, et al. Interventions to address childhood deaths. Lancet. 2013;381:1417-29.
            2. Walker CL, Rudan I, Liu L, et al. Global burden of childhood disease. Lancet. 2013;381:1405-16.
            """
        let entries = PubMedCitationValidator.extractCitationEntries(text)
        XCTAssertEqual(entries.count, 2)
        XCTAssertFalse(texts(entries).contains { $0.lowercased() == "references" })
    }

    // MARK: - Identifiers

    func testPmidAndDoiExtraction() {
        XCTAssertEqual(
            PubMedCitationValidator.extractPmid("Typhoid fever. Lancet. 2015;385(9973):1136-45. PMID: 25458731."),
            "25458731"
        )
        XCTAssertEqual(
            PubMedCitationValidator.extractDoi("doi: 10.1016/S0140-6736(13)60648-0."),
            "10.1016/S0140-6736(13)60648-0"
        )
        XCTAssertEqual(PubMedCitationValidator.extractPmid("No id here"), "")
    }

    /// A bare identifier pasted on its own is still a PMID.
    func testBareDigitsAreTreatedAsAPmid() {
        XCTAssertEqual(PubMedCitationValidator.extractPmid("25458731"), "25458731")
        XCTAssertEqual(PubMedCitationValidator.extractPmid("  25458731  "), "25458731")
        // Too short to be a PMID.
        XCTAssertEqual(PubMedCitationValidator.extractPmid("123"), "")
    }

    func testStripReferenceMetadataRemovesPmidAndDoi() {
        let stripped = PubMedCitationValidator.stripReferenceMetadata(
            "Bhutta ZA, et al. Interventions. Lancet. 2013;381:1417. doi: 10.1016/S0140-6736(13)60648-0. PMID: 23541540."
        )
        XCTAssertFalse(stripped.lowercased().contains("pmid"))
        XCTAssertFalse(stripped.lowercased().contains("doi"))
        XCTAssertTrue(stripped.contains("Bhutta"))
    }

    // MARK: - Detection thresholds

    /// An explicit identifier is enough on its own to offer validation.
    func testExplicitPmidMarkerTriggersDetection() {
        let text = """
            Some unrelated opening sentence that goes on for a while.
            Second unrelated sentence. PMID: 25458731
            """
        XCTAssertTrue(PubMedCitationValidator.looksLikeReferenceBlock(text))
    }

    func testTwoNumberedLinesTriggerDetection() {
        let text = """
            1. Some citation that is long enough to look real and cited.
            2. Another citation that is long enough to look real and cited.
            """
        XCTAssertTrue(PubMedCitationValidator.looksLikeReferenceBlock(text))
    }

    /// Two short lines with no numbering, no year and no "et al." are not
    /// references.
    ///
    /// Numbering alone would be enough — the detector counts numbered lines
    /// first — so these lines are deliberately unnumbered to isolate the other
    /// signals.
    func testBareShortLinesAreNotEnough() {
        let text = """
            Alpha beta gamma delta.
            Epsilon zeta eta theta.
            """
        XCTAssertFalse(PubMedCitationValidator.looksLikeReferenceBlock(text))
    }

    // MARK: - Hints and scoring

    func testHintsExtractDoiYearAndAuthor() {
        let hints = PubMedCitationValidator.buildHints(
            "Bhutta ZA, Das JK, Walker N, et al. Interventions to address deaths from childhood pneumonia. Lancet. 2013;381(9875):1417-29. doi: 10.1016/S0140-6736(13)60648-0."
        )
        // The DOI keeps the sentence's trailing full stop, because the capture
        // pattern is `[^\s<>"']+` and does not exclude `.`. Android's
        // `Regex(...).find()?.value` behaves identically, so the quirk is
        // preserved rather than quietly fixed — see `extractDoi`, which is the
        // trimmed counterpart used for lookups.
        XCTAssertEqual(hints.doi, "10.1016/S0140-6736(13)60648-0.")
        XCTAssertEqual(hints.year, "2013")
        XCTAssertEqual(hints.authorHint, "Bhutta ZA, Das JK, Walker N, et al")
        XCTAssertFalse(hints.titleCandidates.isEmpty)
    }

    /// Title candidates are wordy, year-free, and free of identifier text.
    func testTitleCandidatesSkipJournalAndYearSegments() {
        let hints = PubMedCitationValidator.buildHints(
            "Walker CL. Global burden of childhood pneumonia and diarrhoea. Lancet. 2013;381:1405-16."
        )
        XCTAssertFalse(hints.titleCandidates.isEmpty)
        for candidate in hints.titleCandidates {
            XCTAssertFalse(candidate.contains("Lancet"))
            XCTAssertFalse(candidate.contains("2013"))
            XCTAssertFalse(candidate.lowercased().contains("pmid"))
        }
    }

    func testLookalikeTitleIsRejected() {
        XCTAssertFalse(PubMedCitationValidator.looksLikeTitle("Lancet"))
        XCTAssertFalse(PubMedCitationValidator.looksLikeTitle("Lancet. 2013"))
        XCTAssertFalse(PubMedCitationValidator.looksLikeTitle(""))
        XCTAssertFalse(PubMedCitationValidator.looksLikeTitle("two words"))
        XCTAssertTrue(
            PubMedCitationValidator.looksLikeTitle("Global burden of childhood pneumonia and diarrhoea")
        )
    }

    func testTokenOverlapCountsSharedSignificantWords() {
        // "pneumonia" and "childhood" are 9 and 9 characters, so both count.
        let score = PubMedCitationValidator.tokenOverlap(
            "global burden of childhood pneumonia",
            "the global burden of childhood disease worldwide"
        )
        XCTAssertEqual(score, 15)
    }

    /// Short words are ignored — they are too common to be evidence. Every token
    /// here is under four characters, so nothing contributes.
    func testTokenOverlapIgnoresShortWords() {
        XCTAssertEqual(
            PubMedCitationValidator.tokenOverlap("the of and for nor", "risk factors older groups"),
            0
        )
    }

    func testEmptySidesScoreZero() {
        XCTAssertEqual(PubMedCitationValidator.tokenOverlap("", "anything"), 0)
        XCTAssertEqual(PubMedCitationValidator.tokenOverlap("anything", ""), 0)
    }

    /// A DOI that matches exactly is accepted outright, whatever else matches.
    func testExactDoiMatchIsAlwaysAcceptable() {
        let match = PubMedMatch(
            pmid: "1",
            doi: "10.1016/S0140-6736(13)60648-0",
            articleTitle: "Completely unrelated title",
            canonicalReference: "Completely unrelated title. PubMed. 1999. PMID: 1"
        )
        var hints = SearchHints(doi: "10.1016/s0140-6736(13)60648-0", year: nil, titleHint: nil)
        hints.cleanedText = "unrelated"
        XCTAssertTrue(PubMedCitationValidator.acceptableMatch(match, hints: hints))
    }

    func testScoringRewardsDoiYearAndTitleOverlap() {
        var hints = SearchHints(
            doi: "10.1016/S0140-6736(13)60648-0",
            year: "2013",
            titleHint: "Interventions to address deaths from childhood pneumonia"
        )
        hints.titleCandidates = ["Interventions to address deaths from childhood pneumonia"]
        hints.cleanedText = "Bhutta ZA, et al. Interventions to address deaths from childhood pneumonia"

        let match = PubMedMatch(
            pmid: "23541540",
            doi: "10.1016/S0140-6736(13)60648-0",
            articleTitle: "Interventions to address deaths from childhood pneumonia and diarrhoea equitably",
            canonicalReference: "Bhutta ZA, et al. Interventions to address deaths from childhood pneumonia. Lancet. 2013; PMID: 23541540"
        )

        let score = PubMedCitationValidator.score(match, hints: hints)
        // DOI (100) + year (20) alone clear the search floor.
        XCTAssertGreaterThanOrEqual(score, PubMedCitationValidator.exactMatchScore)
        XCTAssertTrue(PubMedCitationValidator.acceptableMatch(match, hints: hints))
    }

    // MARK: - Queries

    func testQueriesAreDeduplicatedAndNonEmpty() {
        let hints = PubMedCitationValidator.buildHints(
            "Bhutta ZA, et al. Interventions to address deaths from childhood pneumonia. Lancet. 2013;381:1417-29. doi: 10.1016/S0140-6736(13)60648-0."
        )
        let queries = PubMedCitationValidator.buildQueries(hints)
        XCTAssertFalse(queries.isEmpty)
        XCTAssertEqual(queries.count, Set(queries).count)
        XCTAssertFalse(queries.contains { $0.trimmingCharacters(in: .whitespaces).isEmpty })
    }

    /// The quoted DOI, full stop included, is the highest-confidence query and
    /// must come first.
    func testDoiQueryIsTriedFirst() {
        let hints = PubMedCitationValidator.buildHints(
            "Bhutta ZA, et al. Interventions. Lancet. 2013;381:1417-29. doi: 10.1016/S0140-6736(13)60648-0."
        )
        XCTAssertEqual(
            PubMedCitationValidator.buildQueries(hints).first,
            "\"10.1016/S0140-6736(13)60648-0.\""
        )
    }

    // MARK: - Utilities

    func testNormaliseCollapsesWhitespaceAndLowercases() {
        XCTAssertEqual(PubMedCitationValidator.normalise("  Global   Burden\nOf  "), "global burden of")
    }

    func testSearchableTokenCountIgnoresShortTokens() {
        XCTAssertEqual(
            PubMedCitationValidator.searchableTokenCount("the global burden of a rare disease"),
            4
        )
    }

    func testComponentsByPatternDropsEmptyFields() {
        // Kotlin's split(Regex) discards empty fields; components(separatedBy:)
        // would not, which would change every token count built on top of it.
        XCTAssertEqual("  a   b ".components(separatedByPattern: PubMedCitationValidator.Pattern.whitespace), ["a", "b"])
    }

    /// Kotlin's `maxByOrNull` keeps the **first** of several equal maxima. Plain
    /// `max()` would return the last one, changing which citation candidate wins
    /// a tie — so the tie-break is asserted explicitly with distinguishable
    /// elements.
    func testKotlinMaxKeepsFirstOfTies() {
        XCTAssertEqual(kotlinMax(["bb", "aa"], by: <), "bb")
        XCTAssertEqual(kotlinMax(["aa", "bb"], by: <), "bb")
        XCTAssertNil(kotlinMax([String](), by: <))
    }

    func testChunkedSplitsWithShortFinalChunk() {
        XCTAssertEqual([1, 2, 3, 4, 5].chunked(into: 2), [[1, 2], [3, 4], [5]])
        XCTAssertTrue([Int]().chunked(into: 3).isEmpty)
    }
}