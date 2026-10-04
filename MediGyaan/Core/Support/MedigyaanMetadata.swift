import Foundation

/// Subject and topic → emoji lookups, ported 1:1 from the Android
/// `utils/MedigyaanMetadata.kt`.
///
/// `iconify(_:)` is what `AiRichText` applies to every AI reply, so this is
/// presentation, not data modelling.
///
/// ## Why ordered arrays and not dictionaries
///
/// Android's `mapOf` returns a `LinkedHashMap`, so `firstOrNull { … }`
/// iterates in **declaration order** — and declaration order is load-bearing
/// here, because several keys overlap:
///
/// | Input | Matching keys | Android result |
/// | --- | --- | --- |
/// | `General medicine` | `Medicine` (#6) **and** `General medicine` (#26) | 💊 — the broader key is declared first and wins |
/// | `Forensic medicine` | `Medicine` (#6), `Forensic medicine` (#19), `Forensic Medicine` (#29) | 💊 |
/// | `Neonatology` | `Neonatology` (#32) only | 👶 |
///
/// A Swift `Dictionary` has no defined iteration order, so a dictionary port
/// would pick a different emoji run-to-run. The declaration order is therefore
/// preserved explicitly, which keeps the two platforms showing the same glyph.
enum MedigyaanMetadata {

    /// Used when a subject has no mapped icon — Android's `?:` default.
    static let fallbackSubjectIcon = "📚"

    /// Used when no topic key is contained in the input — Android's `?:` default.
    static let fallbackTopicIcon = "📝"

    /// Order-sensitive: see the note on ``topicIcons``.
    private static let subjectIcons: [(key: String, icon: String)] = [
        ("NEET PG", "🩺"),
        ("NEET UG", "🧠"),
        ("Law", "⚖️"),
        ("Commerce", "💼"),
        ("UPSC", "🏛️"),
        ("CAT", "📈"),
        ("Software", "💻"),
    ]

    /// Order-sensitive: see the note at the top of this type.
    private static let topicIcons: [(key: String, icon: String)] = [
        // NEET PG
        ("Pathology", "🔬"),
        ("Microbiology", "🧫"),
        ("Anatomy", "💀"),
        ("Physiology", "🫀"),
        ("Biochemistry", "🧪"),
        ("Medicine", "💊"),
        ("Pharmacology", "💉"),
        ("Surgery", "🔪"),
        ("Ophthalmology", "👁️"),
        ("Otolaryngology", "👂"),
        ("Pediatrics", "👶"),
        ("Dermatology", "🧴"),
        ("Obstetrics", "🤰"),
        ("Gynaecology", "🚺"),
        ("Psychiatry", "🗣️"),
        ("Radiology", "☢️"),
        ("Anaesthesia", "💤"),
        ("Orthopaedics", "🦴"),
        ("Forensic medicine", "🔍"),
        ("Psm", "🏘️"),
        ("Image Based Questions", "🖼️"),
        ("Uncategorized NEET Questions", "❓"),

        // NEET UG
        ("Biology", "🌿"),
        ("Physics", "⚡"),
        ("Chemistry", "🧪"),

        // Others
        ("General medicine", "🏥"),
        ("Ent", "👃"),
        ("Orthopedics", "🦿"),
        ("Forensic Medicine", "🔍"),
        ("Social And Preventive Medicine", "🏘️"),
        ("Gcs score", "🧠"),
        ("Abg analysis", "🩸"),
        ("Neonatology", "👶"),
        ("Hematology", "🩸"),
        ("Genetics", "🧬"),
        ("Infectious diseases", "🦠"),
    ]

    /// Exact, case-insensitive subject match.
    static func icon(forSubject subject: String) -> String {
        guard let match = subjectIcons.first(where: {
            subject.caseInsensitiveCompare($0.key) == .orderedSame
        }) else {
            return fallbackSubjectIcon
        }
        return match.icon
    }

    /// First topic key **contained** in `topic`, case-insensitively.
    ///
    /// This is a substring test, not an equality test, matching Android's
    /// `topic.contains(it.key, ignoreCase = true)`. See the table in the type
    /// documentation for how the overlaps resolve.
    static func icon(forTopic topic: String) -> String {
        guard let match = topicIcons.first(where: {
            topic.range(of: $0.key, options: .caseInsensitive) != nil
        }) else {
            return fallbackTopicIcon
        }
        return match.icon
    }

    /// Returns `text` with an emoji prepended when it names a known topic or
    /// subject, otherwise `text` unchanged.
    ///
    /// Topic keys are consulted before subject keys, and the topic test also
    /// accepts a `"<Topic>:"` prefix so an AI reply opening with
    /// `"Pathology: …"` gets the 🔬 without matching on the whole sentence.
    ///
    /// The case handling is deliberately **asymmetric**, exactly as upstream:
    /// the equality test is case-insensitive but the `"<Topic>:"` prefix test
    /// is case-**sensitive**, because Kotlin's `String.startsWith` defaults to
    /// `ignoreCase = false`. Making both insensitive would change which glyph
    /// appears for mixed-case prefixed replies.
    static func iconify(_ text: String) -> String {
        if let match = topicIcons.first(where: {
            text.caseInsensitiveCompare($0.key) == .orderedSame
                || text.hasPrefix("\($0.key):")
        }) {
            return "\(match.icon) \(text)"
        }

        if let match = subjectIcons.first(where: {
            text.caseInsensitiveCompare($0.key) == .orderedSame
        }) {
            return "\(match.icon) \(text)"
        }

        return text
    }
}