import XCTest
@testable import MediGyaan

/// Tests the emoji maps ported from the Android `utils/MedigyaanMetadata.kt`.
///
/// The emphasis is on **ordering**. Android's `mapOf` returns a `LinkedHashMap`,
/// so `firstOrNull` matches in declaration order, and several keys overlap —
/// which is exactly what a naive `Dictionary` port would get wrong, silently and
/// non-deterministically.
final class MedigyaanMetadataTests: XCTestCase {

    // MARK: - Subjects

    func testSubjectLookupIsExactAndCaseInsensitive() {
        XCTAssertEqual(MedigyaanMetadata.icon(forSubject: "NEET PG"), "🩺")
        XCTAssertEqual(MedigyaanMetadata.icon(forSubject: "neet pg"), "🩺")
        XCTAssertEqual(MedigyaanMetadata.icon(forSubject: "UPSC"), "🏛️")
    }

    func testUnknownSubjectFallsBack() {
        XCTAssertEqual(MedigyaanMetadata.icon(forSubject: "Underwater Basket Weaving"), "📚")
    }

    // MARK: - Topics

    func testTopicLookupUsesSubstringMatch() {
        // A longer label containing a known topic key still matches.
        XCTAssertEqual(MedigyaanMetadata.icon(forTopic: "Renal Pathology"), "🔬")
        XCTAssertEqual(MedigyaanMetadata.icon(forTopic: "Anatomy of the Thorax"), "💀")
    }

    func testUnknownTopicFallsBack() {
        XCTAssertEqual(MedigyaanMetadata.icon(forTopic: "Underwater Basket Weaving"), "📝")
    }

    /// The load-bearing case. `Medicine` is declared before `General medicine`,
    /// so Android returns the general 💊 for `"General medicine"` — the broader
    /// key wins because it comes first, not because it is more specific.
    func testOverlappingTopicKeysResolveInDeclarationOrder() {
        XCTAssertEqual(MedigyaanMetadata.icon(forTopic: "General medicine"), "💊")
        XCTAssertEqual(MedigyaanMetadata.icon(forTopic: "Forensic medicine"), "💊")
    }

    /// The duplicate spelling of "Forensic Medicine" is unreachable for that
    /// input, because `Medicine` shadows it. Both spellings map to 🔍 anyway, so
    /// the shadowing is invisible here — the point is that it must not make the
    /// lookup flaky.
    func testDuplicateCasedKeysAreStable() {
        let first = MedigyaanMetadata.icon(forTopic: "Forensic Medicine")
        for _ in 0 ..< 50 {
            XCTAssertEqual(MedigyaanMetadata.icon(forTopic: "Forensic Medicine"), first)
        }
    }

    func testTopicLookupIsStableAcrossRepeatedCalls() {
        // Guards against a Dictionary-backed implementation, whose iteration
        // order can change between runs.
        let expected = MedigyaanMetadata.icon(forTopic: "General medicine")
        for _ in 0 ..< 50 {
            XCTAssertEqual(MedigyaanMetadata.icon(forTopic: "General medicine"), expected)
        }
    }

    // MARK: - iconify

    func testIconifyPrefixesKnownTopic() {
        XCTAssertEqual(MedigyaanMetadata.iconify("Pathology"), "🔬 Pathology")
    }

    /// A reply opening `"Pathology: the answer is…"` gets the emoji without the
    /// whole sentence matching.
    func testIconifyHandlesTopicPrefixedReply() {
        XCTAssertEqual(
            MedigyaanMetadata.iconify("Pathology: amyloid deposits are seen in the spleen"),
            "🔬 Pathology: amyloid deposits are seen in the spleen"
        )
    }

    func testIconifyFallsBackToSubject() {
        XCTAssertEqual(MedigyaanMetadata.iconify("NEET PG"), "🩺 NEET PG")
    }

    /// Topics are consulted before subjects, so a string that matches neither
    /// rule is returned untouched.
    func testIconifyLeavesUnmatchedTextAlone() {
        let sentence = "The patient requires urgent attention."
        XCTAssertEqual(MedigyaanMetadata.iconify(sentence), sentence)
    }

    func testIconifyDoesNotMatchTopicAnywhereInASentence() {
        // Substring matching applies to `icon(forTopic:)`, but `iconify` requires
        // an exact name or a "Topic:" prefix — otherwise every sentence
        // mentioning a topic would gain an emoji.
        let sentence = "You asked about pathology earlier."
        XCTAssertEqual(MedigyaanMetadata.iconify(sentence), sentence)
    }

    /// Android's case handling is asymmetric on purpose: the equality test is
    /// case-insensitive but the `"<Topic>:"` prefix test is case-**sensitive**,
    /// because `String.startsWith` defaults to `ignoreCase = false`.
    ///
    /// Making the prefix test insensitive as well would look tidier, but it would
    /// change which glyph appears for mixed-case replies, so the asymmetry is
    /// preserved and pinned by this test.
    func testTopicPrefixIsCaseSensitiveLikeAndroid() {
        // Exact-case prefix matches.
        XCTAssertEqual(MedigyaanMetadata.iconify("Pathology: x"), "🔬 Pathology: x")
        // Lowercase prefix does not match the case-sensitive prefix rule, and the
        // case-insensitive equality rule cannot match either, so nothing is added.
        XCTAssertEqual(MedigyaanMetadata.iconify("pathology: x"), "pathology: x")
        XCTAssertEqual(MedigyaanMetadata.iconify("PATHOLOGY: x"), "PATHOLOGY: x")
        // A bare name, however cased, goes through the case-insensitive equality
        // rule and does match.
        XCTAssertEqual(MedigyaanMetadata.iconify("pathology"), "🔬 pathology")
        XCTAssertEqual(MedigyaanMetadata.iconify("PATHOLOGY"), "🔬 PATHOLOGY")
    }
}