import Foundation

/// Medical subject and topic icon registry.
/// 1:1 port of Android `MedigyaanMetadata.kt`.
public enum MedigyaanMetadata {

    public static let subjectIcons: [String: String] = [
        "NEET PG": "🩺",
        "NEET UG": "🧬",
        "FMGE": "🌍",
        "USMLE": "⭐",
        "Law": "⚖️",
        "Commerce": "📊",
        "UPSC": "🏛️",
        "CAT": "📈",
        "Software": "💻"
    ]

    public static let topicIcons: [String: String] = [
        // NEET PG
        "Pathology": "🔬",
        "Microbiology": "🦠",
        "Anatomy": "🫀",
        "Physiology": "🧠",
        "Biochemistry": "🧪",
        "Medicine": "💊",
        "Pharmacology": "💉",
        "Surgery": "🔪",
        "Ophthalmology": "👁️",
        "Otolaryngology": "👂",
        "Pediatrics": "👶",
        "Dermatology": "🧴",
        "Obstetrics": "🤰",
        "Gynaecology": "🌸",
        "Psychiatry": "🧘",
        "Radiology": "☢️",
        "Anaesthesia": "💤",
        "Orthopaedics": "🦴",
        "Forensic medicine": "🔍",
        "Psm": "🏥",
        "Image Based Questions": "🖼️",

        // NEET UG & Sciences
        "Biology": "🌱",
        "Physics": "⚛️",
        "Chemistry": "⚗️",

        // High yield clinical sub-specialties
        "General medicine": "🩺",
        "Ent": "👂",
        "Orthopedics": "🦴",
        "Gcs score": "📋",
        "Abg analysis": "🩸",
        "Neonatology": "👶",
        "Hematology": "🩸",
        "Genetics": "🧬",
        "Infectious diseases": "🦠"
    ]

    public static func getIcon(forSubject subject: String) -> String {
        subjectIcons[subject] ?? "📚"
    }

    public static func getIcon(forTopic topic: String) -> String {
        if let match = topicIcons.first(where: { topic.localizedCaseInsensitiveContains($0.key) }) {
            return match.value
        }
        return "📖"
    }

    public static func iconify(_ text: String) -> String {
        let icon = getIcon(forTopic: text)
        return "\(icon) \(text)"
    }
}
