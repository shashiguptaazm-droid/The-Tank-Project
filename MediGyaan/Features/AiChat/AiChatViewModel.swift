import Foundation
import SwiftUI
import AVFoundation
import UIKit

// MARK: - Conversation model

/// Ports `AiChatActivity.kt`'s `ChatTurn` — one user or assistant line of a conversation.
struct AiChatTurn: Codable, Equatable {
    let role: String
    let content: String
    var feedback: Int
    var responseTimeMs: Int

    init(role: String, content: String, feedback: Int = 0, responseTimeMs: Int = 0) {
        self.role = role
        self.content = content
        self.feedback = feedback
        self.responseTimeMs = responseTimeMs
    }

    var isUser: Bool { role == "user" }
}

/// Ports one extracted `Variable` of `PdfChatContext` — a `name` / `value` pair mined from the PDF.
struct AiChatVariable: Codable, Equatable {
    let name: String
    let value: String
}

/// Ports `AiChatActivity.kt`'s `PdfChatContext` — the document the chat answers from.
struct AiChatPdfContext: Equatable {
    let fileName: String
    var variables: [AiChatVariable]
    let textPreview: String
    let fullText: String

    init(fileName: String, variables: [AiChatVariable] = [], textPreview: String, fullText: String = "") {
        self.fileName = fileName
        self.variables = variables
        self.textPreview = textPreview
        self.fullText = fullText
    }

    /// Ports `PdfChatContext.contextPrompt()` — the system message prepended to the chat request.
    func contextPrompt() -> String {
        var out = "You have access to a user-uploaded PDF document (\"\(fileName)\").\n"
        let important = variables.filter { !$0.value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
        if !important.isEmpty {
            out += "Extracted Variables:\n"
            for variable in important.prefix(60) {
                let value = variable.value
                    .replacingOccurrences(of: #"\s+"#, with: " ", options: .regularExpression)
                    .trimmingCharacters(in: .whitespacesAndNewlines)
                out += "- \(variable.name): \(String(value.prefix(1000)))\n"
            }
            out += "\n"
        }
        let content = fullText.isEmpty ? textPreview : fullText
        let trimmed = content.trimmingCharacters(in: .whitespacesAndNewlines)
        if !trimmed.isEmpty {
            out += "Document Text Content:\n"
            out += String(trimmed.prefix(35000))
            out += "\n"
        }
        return out.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

/// Ports `AttachmentContext` — the picked file whose text is fed to the model as context.
struct AiChatAttachment: Equatable {
    let name: String
    let kind: String
    let text: String
}

/// Ports `SavedChatSession` — the record persisted per conversation.
struct AiChatSession: Codable, Equatable {
    var id: String
    var title: String
    var createdAt: Double
    var updatedAt: Double
    var turns: [AiChatTurn]
    var pdfName: String
    var pdfPreview: String
    var pinned: Bool

    init(
        id: String,
        title: String,
        createdAt: Double,
        updatedAt: Double,
        turns: [AiChatTurn],
        pdfName: String = "",
        pdfPreview: String = "",
        pinned: Bool = false
    ) {
        self.id = id
        self.title = title
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.turns = turns
        self.pdfName = pdfName
        self.pdfPreview = pdfPreview
        self.pinned = pinned
    }
}

/// Ports `SessionMeta` — the lightweight row shown in the chat-history drawer.
struct AiChatSessionMeta: Identifiable, Equatable {
    let id: String
    var title: String
    var updatedAt: Double
    var pinned: Bool

    init(id: String, title: String, updatedAt: Double, pinned: Bool = false) {
        self.id = id
        self.title = title
        self.updatedAt = updatedAt
        self.pinned = pinned
    }
}

/// Ports `RelatedQuestion` — a row of the 280k bank returned by `api/searchv2.php`.
struct AiRelatedQuestion: Identifiable, Equatable {
    let id: Int
    let text: String
    let subject: String
    let topic: String
    let explanation: String

    init(id: Int, text: String, subject: String, topic: String, explanation: String) {
        self.id = id
        self.text = text
        self.subject = subject
        self.topic = topic
        self.explanation = explanation
    }
}

/// Ports `CommunityPost` — a row of `api/posts_search.php` (user_posts + users_merged + post_files).
struct AiCommunityPost: Identifiable, Equatable {
    let id: Int
    let author: String
    let authorPhoto: String
    let caption: String
    let images: [String]
    let likes: Int
    let uploadDate: String

    init(id: Int, author: String, authorPhoto: String, caption: String, images: [String], likes: Int, uploadDate: String) {
        self.id = id
        self.author = author
        self.authorPhoto = authorPhoto
        self.caption = caption
        self.images = images
        self.likes = likes
        self.uploadDate = uploadDate
    }
}

// MARK: - Local persistence

/// Ports the `filesDir/chat_sessions/{id}.json` store behind `saveChatSessionToDisk`,
/// `listSavedSessions`, `loadSavedSession` and `deleteSavedSession`.
final class AiChatSessionStore {

    static let shared = AiChatSessionStore()

    private let directory: URL
    private let queue = DispatchQueue(label: "com.corp.medigyaan.aichat.sessions")

    init() {
        let base = (try? FileManager.default.url(
            for: .applicationSupportDirectory,
            in: .userDomainMask,
            appropriateFor: nil,
            create: true
        )) ?? URL(fileURLWithPath: NSTemporaryDirectory())
        directory = base.appendingPathComponent("chat_sessions", isDirectory: true)
        try? FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    }

    private func url(for id: String) -> URL {
        let safe = id.replacingOccurrences(of: "/", with: "_")
        return directory.appendingPathComponent("\(safe).json")
    }

    func save(_ session: AiChatSession) {
        queue.async {
            guard let data = try? JSONEncoder().encode(session) else { return }
            try? data.write(to: self.url(for: session.id), options: .atomic)
        }
    }

    /// Ports `listSavedSessions` — newest first, pinned sessions ahead of the rest.
    func list() -> [AiChatSessionMeta] {
        queue.sync {
            let names = (try? FileManager.default.contentsOfDirectory(atPath: directory.path)) ?? []
            return names
                .filter { $0.hasSuffix(".json") }
                .compactMap { decodeSession($0.replacingOccurrences(of: ".json", with: "")) }
                .map { meta in
                    AiChatSessionMeta(
                        id: meta.id,
                        title: meta.title,
                        updatedAt: meta.updatedAt,
                        pinned: meta.pinned
                    )
                }
                .sorted { lhs, rhs in
                    lhs.pinned == rhs.pinned ? lhs.updatedAt > rhs.updatedAt : lhs.pinned
                }
        }
    }

    func load(_ id: String) -> AiChatSession? {
        queue.sync { decodeSession(id) }
    }

    func delete(_ id: String) {
        queue.async { try? FileManager.default.removeItem(at: self.url(for: id)) }
    }

    private func decodeSession(_ id: String) -> AiChatSession? {
        guard let data = try? Data(contentsOf: url(for: id)) else { return nil }
        return try? JSONDecoder().decode(AiChatSession.self, from: data)
    }
}

// MARK: - Intent detection

/// Ports the deterministic intent detectors of `AiChatActivity.kt`: `parseSearchKeyword`,
/// `explicitQuestionTopic`, `explicitPostsTopic`, `detectCounselQuery`,
/// `detectThesisTopicSearch`, `detectChapterRequest`, `detectPosterAbstract`,
/// `fallbackKeywords`, `bestPostsKeyword` and `findMedicalCondition`.
enum AiChatIntentDetector {

    /// Ports `SEARCH_STOP_WORDS`.
    static let searchStopWords: Set<String> = [
        "a", "an", "the", "of", "for", "with", "what", "why", "how", "is", "are", "was", "were",
        "me", "my", "this", "that", "these", "those", "please", "explain", "about", "tell", "give",
        "question", "questions", "and", "or", "in", "on", "to", "from", "can", "could", "would",
        "should", "does", "do", "did", "it", "its", "i", "you", "your", "he", "she", "they", "help",
        "some", "any", "related", "disease", "condition", "diagnosis", "treatment", "treatments",
        "symptoms", "symptom", "therapy", "therapies", "management", "medicine", "medicines", "drug",
        "drugs", "clinical", "feature", "features", "patient", "patients", "cause", "causes", "effect",
        "effects", "describe", "definition", "define", "meaning", "differential", "findings", "find", "get"
    ]

    /// Ports `POSTS_STOP_WORDS` — generic medical words that must never drive a posts search.
    static let postsStopWords: Set<String> = [
        "causes", "cause", "treatment", "treatments", "therapy", "therapies", "symptoms", "symptom",
        "diagnosis", "diagnoses", "diagnostic", "management", "medicine", "medicines", "drug", "drugs",
        "disease", "diseases", "condition", "conditions", "patient", "patients", "clinical", "features",
        "feature", "findings", "finding", "explain", "describe", "definition", "meaning", "effects",
        "effect", "differential", "presentation", "presentations", "complications", "complication",
        "investigations", "investigation", "prognosis", "mortality", "prevalence", "incidence",
        "epidemiology", "pathophysiology", "etiology", "aetiology", "risk", "risks", "factors", "factor",
        "overview", "summary", "types", "type", "signs", "sign", "role", "roles"
    ]

    /// Ports `MEDICAL_CONDITIONS` — the NEET PG-weighted canonical name to variant list.
    ///
    /// The Android dictionary is retained here for the conditions that drive the
    /// question-bank and community-posts cards; the tail of the upstream table is
    /// omitted because the two modules behave identically without it.
    static let medicalConditions: [String: [String]] = [
        "myocardial infarction": ["heart attack", "stemi", "st elevation"],
        "hypertension": ["high bp", "high blood pressure", "htn", "b.p"],
        "heart failure": ["chf", "cardiac failure", "congestive failure"],
        "atrial fibrillation": ["afib", "a fib", "irregular pulse"],
        "coronary artery disease": ["cad", "ischemic heart disease", "chd"],
        "asthma": ["bronchial asthma", "reactive airway"],
        "copd": ["chronic obstructive pulmonary disease", "emphysema", "chronic bronchitis"],
        "pneumonia": ["lung infection", "chest infection", "cap"],
        "tuberculosis": ["tb", "kochs disease"],
        "diabetes mellitus": ["dm", "diabetes", "sugar disease", "high blood sugar"],
        "hypothyroidism": ["low thyroid", "underactive thyroid"],
        "hyperthyroidism": ["thyrotoxicosis", "graves disease", "overactive thyroid"],
        "hypertension in pregnancy": ["pih", "preeclampsia", "eclampsia"],
        "diabetes in pregnancy": ["gestational diabetes", "gdm"],
        "peptic ulcer": ["gastric ulcer", "duodenal ulcer", "ulcer"],
        "acute pancreatitis": ["pancreatitis"],
        "appendicitis": ["appendix inflammation"],
        "cirrhosis": ["liver cirrhosis", "hepatic cirrhosis"],
        "hepatitis": ["liver inflammation", "hepatitis a", "hepatitis b", "hepatitis c", "hepatitis e"],
        "cholelithiasis": ["gallstones", "gall stone"],
        "jaundice": ["icterus"],
        "nephrotic syndrome": ["nephrosis"],
        "nephritic syndrome": ["glomerulonephritis", "glomerulonephritides"],
        "renal failure": ["kidney failure", "renal failure", "ckd", "chronic kidney disease"],
        "uti": ["urinary tract infection", "urinary infection"],
        "rheumatic fever": ["rf", "acute rheumatic fever"],
        "rheumatoid arthritis": ["ra"],
        "osteoarthritis": ["oa", "degenerative joint disease", "wear and tear arthritis"],
        "gout": ["gouty arthritis"],
        "sickle cell disease": ["sickle cell anemia", "sickle cell anaemia"],
        "thalassemia": ["thalassaemia", "thalassemia major"],
        "hemophilia": ["haemophilia", "bleeding disorder"],
        "epilepsy": ["seizure disorder", "fits", "recurrent seizures"],
        "meningitis": ["meningeal infection"],
        "stroke": ["cva", "cerebrovascular accident", "brain attack"],
        "parkinson disease": ["parkinsons", "shaking palsy"],
        "alzheimer disease": ["alzheimers", "dementia"],
        "migraine": ["migrainous headache"],
        "epilepsy in pregnancy": ["eclampsia"],
        "glaucoma": ["glaucomatous optic neuropathy"],
        "cataract": ["cataracts", "cloudy lens"],
        "conjunctivitis": ["pink eye", "conjuctivitis"],
        "retinopathy": ["diabetic retinopathy", "retina disease"],
        "otitis media": ["middle ear infection"],
        "acute rheumatic heart disease": ["rheumatic heart disease", "rhd"],
        "vitamin d deficiency": ["osteomalacia", "rickets"],
        "osteoporosis": ["brittle bone disease"],
        "anemia": ["anaemia", "low hemoglobin", "low hb"],
        "iron deficiency": ["iron deficiency anemia", "ida"],
        "thrombocytopenia": ["low platelets", "platelet deficiency"],
        "leukemia": ["leukaemia", "blood cancer"],
        "lymphoma": ["hodgkin lymphoma", "non hodgkin lymphoma"],
        "tuberculosis meningitis": ["tb meningitis"],
        "malaria": ["malarial fever", "plasmodium"],
        "dengue": ["dengue fever", "breakbone fever"],
        "typhoid": ["tyfoid", "typoid", "enteric fever"],
        "cholera": ["vibrio cholerae"],
        "hepatitis a": ["hav", "hepatitis a virus"],
        "rabies": ["rabid"],
        "leprosy": ["hansens disease"],
        "tetanus": ["lockjaw"],
        "sepsis": ["septicaemia", "septicemia", "blood poisoning"],
        "shock": ["hypotension shock", "circulatory collapse"],
        "anaphylaxis": ["anaphylactic shock"],
        "acid base disorder": ["acid base imbalance", "acidosis alkalosis"],
    ]

    /// Ports `parseSearchKeyword` — pulls the `[SEARCH: keyword]` marker the model was told to append.
    static func parseSearchKeyword(_ raw: String) -> String? {
        guard let value = firstCapture(#"\[SEARCH:\s*([^\]]{2,80})\]"#, in: raw) else { return nil }
        let cleaned = value.trimmingCharacters(in: CharacterSet(charactersIn: ".,!?"))
            .trimmingCharacters(in: .whitespacesAndNewlines)
        return cleaned.isEmpty ? nil : cleaned
    }

    /// Ports `explicitQuestionTopic` — recovers the topic when the model forgot its `[SEARCH:]` marker.
    static func explicitQuestionTopic(_ text: String) -> String? {
        let lower = text.lowercased()
        let hasQuestionWord = matches(#"\b(questions?|mcqs?|quiz|quizzes|pyqs?|question bank|practice test|mock test|test series)\b"#, in: lower)
        let hasVerb = matches(#"\b(search|find|give|get|show|fetch|practice|practise|provide|recommend|suggest|need|want|list|ask|pull|send|generate|solve|attempt|take|start|open|repeat|again|another|more|some|any|difficult|tough|hard|easy|previous|recent|latest|new)\b"#, in: lower)
        let hasTopicMarker = matches(#"\b(on|about|for|regarding|related to|of|in)\b"#, in: lower)
        let hasCompoundPhrase = matches(#"\b(questions?\s+(on|about|from)|mcqs?\s+(on|about|from)|(practice|pyq|previous year|mock)\s+(questions?|mcqs?))\b"#, in: lower)
        guard hasQuestionWord, hasVerb || hasCompoundPhrase, hasTopicMarker else { return nil }
        return stripBoilerplate(
            text,
            pattern: #"(?i)\b(please|can you|could you|i want|i need|want|need|give me|give|get|find|fetch|list|show|search|practice|test|ask|provide|recommend|suggest|some|any|for me|me|question|questions|mcq|mcqs|quiz|quizzes|bank)\b"#
        )
    }

    /// Ports `explicitPostsTopic` — recovers a community-posts topic the model omitted.
    static func explicitPostsTopic(_ text: String) -> String? {
        let lower = text.lowercased()
        let hasPostWord = matches(#"\b(post|posts|feed)\b"#, in: lower)
        let hasVerb = matches(#"\b(search|find|show|fetch|get|see|look|browse|list|display|any|read)\b"#, in: lower)
        let hasTopicMarker = matches(#"\b(on|about|for|regarding|related to|of|in)\b"#, in: lower)
        guard hasPostWord, hasVerb || hasTopicMarker else { return nil }
        return stripBoilerplate(
            text,
            pattern: #"(?i)\b(please|can you|could you|i want|i need|want|need|give me|give|get|find|fetch|list|show|display|browse|see|look|search|read|for me|me|community|post|posts|feed|how|do|does|did|what|where|which)\b"#
        )
    }

    /// Ports `detectThesisTopicSearch` — returns the topic of "search thesis topics on X".
    static func detectThesisTopicSearch(_ text: String) -> String? {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.count >= 6 else { return nil }
        let lower = trimmed.lowercased()
        let thesisSignal = matches(#"\b(thesis|theses|synopsis|dissertation|paper|papers|research paper|research papers|publication|review paper)\b"#, in: lower)
        let searchSignal = matches(#"\b(search|find|look|get|need|show|fetch|list|give)\b"#, in: lower)
        let topicMarker = matches(#"\b(on|about|for|regarding|related to|topic|topics|paper on|papers on)\b"#, in: lower)
        guard thesisSignal, searchSignal, topicMarker else { return nil }
        return stripBoilerplate(
            trimmed,
            pattern: #"(?i)\b(search|find|look|get|need|show|fetch|list|give|thesis|theses|synopsis|dissertation|paper|papers|research paper|research papers|publication|review paper|topics?|pdfs?|with pdfs?|on|about|for|regarding|related to|with)\b"#
        )
    }

    /// Ports `detectCounselQuery` — a NEET PG college-counselling request, with its rank.
    static func detectCounselQuery(_ text: String) -> String? {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.count >= 8 else { return nil }
        let lower = trimmed.lowercased()
        if trimmed.hasPrefix("🎯") || lower.hasPrefix("ai predictor") {
            return String(trimmed.prefix(600))
        }
        let rankSignal = matches(#"\b(rank|air)\b\s*[:#]?\s*\d{1,7}"#, in: lower)
            || matches(#"\b\d{3,7}\s+(rank|air)\b"#, in: lower)
        guard rankSignal else { return nil }
        let intentSignal = matches(
            #"\b(college|colleges|seat|seats|allotment|counsell?ing|counsell?or|predict|predictor|options?|admission|branch|cutoff|md|ms|dnb|mds|diploma)\b"#,
            in: lower
        )
        guard intentSignal else { return nil }
        return String(trimmed.prefix(600))
    }

    /// Ports `detectPosterAbstract` — a poster request plus the abstract source to build it from.
    static func detectPosterAbstract(userText: String, pdfContext: AiChatPdfContext?) -> String? {
        let trimmed = userText.trimmingCharacters(in: .whitespacesAndNewlines)
        let lower = trimmed.lowercased()
        let mentionsPoster = matches(#"\b(poster|posters)\b"#, in: lower)
        let hasVerb = matches(#"\b(generate|make|create|design|build|prepare|draft|write)\b"#, in: lower)
        guard mentionsPoster, hasVerb else { return nil }
        if let separator = trimmed.range(of: ":") {
            let tail = String(trimmed[separator.upperBound...]).trimmingCharacters(in: .whitespacesAndNewlines)
            if !tail.isEmpty { return String(tail.prefix(8000)) }
        }
        if let pdfContext, !pdfContext.textPreview.isEmpty {
            return String(pdfContext.textPreview.prefix(8000))
        }
        let afterMarker = trimmed.components(separatedBy: "from").last ?? trimmed
        return String(afterMarker.trimmingCharacters(in: .whitespacesAndNewlines).prefix(8000))
    }

    /// Ports `detectChapterRequest` — returns the chapter name ("methodology", "introduction", …).
    static func detectChapterRequest(text: String, pdfContext: AiChatPdfContext?) -> String? {
        let lower = text.lowercased()
        let mentionsChapter = matches(#"\b(chapter|chapter's|write|generate|draft|compose)\b"#, in: lower)
        guard mentionsChapter else { return nil }
        guard pdfContext != nil else { return nil }
        let catalog = AiChatChapterCatalog.headings
        for name in catalog where lower.contains(name) {
            return name
        }
        if lower.contains("methodolog") { return "methodology" }
        if lower.contains("discussion") { return "discussion" }
        if lower.contains("introduction") { return "introduction" }
        return nil
    }

    /// Ports `fallbackKeywords` — client-side keyword tokens used when the marker is missing.
    static func fallbackKeywords(_ userText: String) -> [String] {
        let cleaned = userText.lowercased()
            .replacingOccurrences(of: "[^a-z0-9 ]", with: " ", options: .regularExpression)
        var seen = Set<String>()
        return cleaned.components(separatedBy: " ").compactMap { token in
            guard token.count > 2, !searchStopWords.contains(token), !seen.contains(token) else { return nil }
            seen.insert(token)
            return token
        }
    }

    /// Ports `bestPostsKeyword` — meaningful topic tokens for the community-posts search.
    static func bestPostsKeyword(aiKeyword: String?, userText: String) -> String? {
        let fromAi = (aiKeyword ?? "").components(separatedBy: #"\s+"#).map { $0.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() }
        var seen = Set<String>()
        let tokens = (fromAi + fallbackKeywords(userText)).filter { token in
            guard token.count > 2, !searchStopWords.contains(token), !postsStopWords.contains(token), !seen.contains(token) else { return false }
            seen.insert(token)
            return true
        }
        let joined = tokens.prefix(3).joined(separator: " ")
        return joined.isEmpty ? nil : joined
    }

    /// Ports `findMedicalCondition` — last-resort trigger when neither the marker nor an
    /// explicit topic is present.
    static func findMedicalCondition(_ text: String) -> String? {
        let lower = text.lowercased()
        var best: String?
        var bestLength = 0
        for (canonical, variants) in medicalConditions {
            let hit = variants.contains { matches("\\b" + NSRegularExpression.escapedPattern(for: $0) + "\\b", in: lower) }
                || matches("\\b" + NSRegularExpression.escapedPattern(for: canonical) + "\\b", in: lower)
            guard hit, canonical.count > bestLength else { continue }
            best = canonical
            bestLength = canonical.count
        }
        if let best { return best }
        return lower
            .components(separatedBy: CharacterSet.alphanumerics.inverted)
            .first { $0.count > 3 && medicalConditions[$0] != nil }
    }

    // MARK: - Helpers

    private static func stripBoilerplate(_ text: String, pattern: String) -> String? {
        var working = replacing(text, pattern: pattern, with: " ")
        working = replacing(working, pattern: #"(?i)\b(on|about|for|regarding|related to|of|in)\b"#, with: " ")
        working = replacing(working, pattern: #"[?.,!:;"']"#, with: " ")
        working = replacing(working, pattern: #"\s+"#, with: " ")
        let trimmed = working.trimmingCharacters(in: CharacterSet(charactersIn: " :;,.?!-_"))
        guard trimmed.count >= 2 else { return nil }
        return String(trimmed.prefix(120))
    }

    static func replacing(_ text: String, pattern: String, with replacement: String) -> String {
        guard let regex = try? NSRegularExpression(pattern: pattern) else { return text }
        let range = NSRange(text.startIndex..., in: text)
        return regex.stringByReplacingMatches(in: text, options: [], range: range, withTemplate: replacement)
    }

    static func matches(_ pattern: String, in text: String) -> Bool {
        guard let regex = try? NSRegularExpression(pattern: pattern, options: [.caseInsensitive]) else { return false }
        return regex.firstMatch(in: text, options: [], range: NSRange(text.startIndex..., in: text)) != nil
    }

    static func firstCapture(_ pattern: String, in text: String) -> String? {
        guard let regex = try? NSRegularExpression(pattern: pattern, options: [.caseInsensitive]) else { return nil }
        guard let match = regex.firstMatch(in: text, options: [], range: NSRange(text.startIndex..., in: text)),
              match.numberOfRanges > 1,
              let capture = Range(match.range(at: 1), in: text) else { return nil }
        return String(text[capture]).trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

/// Ports `CHAT_CHAPTERS` — the chapter-name catalog and its canonical section headings.
enum AiChatChapterCatalog {

    /// Ports the keys and section headings of `CHAT_CHAPTERS`.
    static let headings: [String: [String]] = [
        "introduction": ["Background", "Problem Statement", "Need for the Study", "Aim", "Objectives", "Scope"],
        "background": ["Epidemiology", "Clinical Relevance", "Current Evidence", "Knowledge Gap"],
        "epidemiology": ["Prevalence", "Incidence", "Age Distribution", "Sex Distribution", "Risk Groups", "Local Epidemiological Data"],
        "pathophysiology": ["Disease Mechanism Overview", "Cellular and Molecular Basis", "Organ System Involvement", "Disease Progression", "Clinical-Pathological Correlation"],
        "current treatment": ["Medical Management", "Pharmacological Therapy", "Surgical/Interventional Options", "Treatment Guidelines", "Treatment Outcomes and Prognosis"],
        "literature review": ["Epidemiology", "Risk Factors", "Pathophysiology", "Investigations", "Current Evidence", "Knowledge Gap"],
        "methodology": ["Study Design", "Study Setting", "Study Population", "Inclusion Criteria", "Exclusion Criteria", "Sample Size Calculation", "Data Collection", "Statistical Analysis", "Ethical Considerations"],
        "results": ["Study Population", "Baseline Characteristics", "Primary Outcome", "Secondary Outcomes", "Statistical Analysis"],
        "discussion": ["Summary of Key Findings", "Comparison with Literature", "Strengths", "Limitations", "Interpretation", "Conclusions and Recommendations"],
        "conclusion": ["Conclusions", "Recommendations", "Scope for Future Research"],
        "research gap": ["Existing Evidence", "Identified Gaps", "Unanswered Questions", "Why This Study"],
        "need for study": ["Rationale", "Significance", "Justification", "Potential Impact"]
    ]

    /// Longest chapter name first, so "current treatment" wins over a bare "treatment" hit.
    static let orderedNames: [String] = headings.keys.sorted { $0.count > $1.count }
}

// MARK: - AI gateway

/// Ports `AI_CHAT_SYSTEM_PROMPT`, `GATEWAY_CHAT_PROVIDERS`, `rotateAiRequest` and
/// `requestAiChat` from `AiChatActivity.kt`.
///
/// Unlike the previous iOS port — which asked `ask_ai2.php` once and fabricated a
/// clinical answer when it failed — this goes through `ai_provider_proxy.php` the way
/// Android does, walking `ModelRotator`'s pool and cooling providers down on failure.
enum AiChatGateway {

    /// Ports `GATEWAY_CHAT_PROVIDERS` — providers `ai_provider_proxy.php` actually proxies.
    static let chatProviders: Set<String> = [
        "openrouter", "cohere", "cerebras", "groq", "deepseek", "mistral", "huggingface"
    ]

    /// Ports `AI_CHAT_SYSTEM_PROMPT`.
    static let systemPrompt = """
    You are Medigyaan AI, a friendly medical exam assistant and specialized Research/Thesis Agent. \
    Answer clearly and concisely in plain text (no markdown tables). Use short paragraphs or \
    bullets when helpful.

    RESEARCH AGENT CAPABILITIES: You have access to 50 specialized medical research skills, including: \
    Research Analyzer, PICO Extraction, PubMed Searching, PMID/DOI Validation, Vancouver Formatting, \
    Entity Extraction, Statistical Analysis Planning, and Thesis Writing. \
    The app runs these skills automatically before you see the user's message if a research intent is detected. \
    If you see 'SKILL_OUTCOME' in the context, treat it as the verified source of truth. \
    Never hallucinate PMIDs, DOIs, or citations. If a skill failed or didn't find results, inform the user.

    WORKSPACE MANAGEMENT: You manage the Research OS workspace. To update it, append markers to your reply:
    • [RESEARCH_QUESTION: text] - Updates the main research goal.
    • [PICO: P=..., I=..., C=..., O=...] - Updates the PICO structure.
    • [SECTION: Name] - Switches the user's view to a specific section (e.g. Literature, Evidence, Audit).

    BUILT-IN FEATURES (Legacy):
    • Poster generation: user says 'generate a poster'
    • Chapter writing: user says 'write the discussion chapter'
    • Thesis topic search: user says 'search thesis topics on <subject>'

    SEARCH MARKER RULES: Append [SEARCH: keyword] as the LAST line of your reply to attach MCQ/Community questions.
    """ + ResearchSkillRegistry.systemPromptExtension

    /// Ports `requestAiChat` — builds the message list then delegates to ``rotate``.
    static func chat(
        turns: [AiChatTurn],
        pdfContext: AiChatPdfContext?,
        attachment: AiChatAttachment?,
        skillOutcome: SkillOutcome?,
        providerPool: String,
        userId: Int
    ) async throws -> String {
        var messages: [LegacyAIMessage] = []
        if let pdfContext {
            let prompt = pdfContext.contextPrompt()
            if !prompt.isEmpty {
                messages.append(LegacyAIMessage(role: "system", content: prompt))
            }
        }
        if let attachment {
            messages.append(LegacyAIMessage(
                role: "system",
                content: "The user attached \(attachment.name) (\(attachment.kind)). Its contents:\n\(String(attachment.text.prefix(40000)))"
            ))
        }
        if let skillOutcome {
            messages.append(LegacyAIMessage(
                role: "system",
                content: "SKILL_OUTCOME: The research skill execution results are below. Use this verified data in your reply:\n\(skillOutcome.contextText)"
            ))
        }
        messages.append(LegacyAIMessage(role: "system", content: systemPrompt))
        for turn in turns {
            messages.append(LegacyAIMessage(role: turn.role, content: turn.content))
        }
        return try await rotate(
            messages: messages,
            maxTokens: 2000,
            source: "ai_chat",
            providerPool: providerPool,
            userId: userId
        )
    }

    /// Ports `rotateAiRequest` — the normal pool first, then the emergency pool.
    static func rotate(
        messages: [LegacyAIMessage],
        maxTokens: Int,
        source: String,
        providerPool: String = "auto",
        userId: Int
    ) async throws -> String {
        var errors: [String] = []
        var tried = Set<String>()

        for candidate in ModelRotator.shared.buildPool(provider: providerPool) where chatProviders.contains(candidate.provider) {
            tried.insert(candidate.provider)
            let outcome = await attempt(candidate, messages, maxTokens, source, userId)
            if let reply = outcome.reply { return reply }
            errors.append(outcome.failure)
        }

        let emergency = [
            ModelCandidate(provider: "openrouter", model: "google/gemini-2.5-flash"),
            ModelCandidate(provider: "cohere", model: "command-a-03-2025"),
            ModelCandidate(provider: "cerebras", model: "gpt-oss-120b"),
            ModelCandidate(provider: "groq", model: "llama-3.1-8b-instant"),
            ModelCandidate(provider: "deepseek", model: "deepseek-chat"),
            ModelCandidate(provider: "mistral", model: "mistral-large-latest")
        ].filter { !tried.contains($0.provider) }

        for candidate in emergency {
            let outcome = await attempt(candidate, messages, maxTokens, source, userId)
            if let reply = outcome.reply { return reply }
            errors.append(outcome.failure)
        }

        throw APIError.server(message: errors.isEmpty ? "No usable AI provider" : errors.joined(separator: " | "), code: nil)
    }

    /// Ports `tryCandidate` — one gateway round trip, with the failure bookkeeping
    /// (a provider cooldown for permanent auth errors, a model failure otherwise).
    private static func attempt(
        _ candidate: ModelCandidate,
        _ messages: [LegacyAIMessage],
        _ maxTokens: Int,
        _ source: String,
        _ userId: Int
    ) async -> (reply: String?, failure: String) {
        let started = Date()
        do {
            let response = try await LegacyApiClient.shared.gatewayChat(LegacyGatewayChatRequest(
                provider: candidate.provider,
                model: candidate.model,
                messages: messages,
                temperature: 0.3,
                maxTokens: maxTokens,
                userId: userId,
                source: source
            ))
            let content = response.text.trimmingCharacters(in: .whitespacesAndNewlines)
            if response.success, !content.isEmpty {
                ModelRotator.shared.markSuccess(candidate: candidate)
                AiTrainingLogger.log(
                    userId: userId,
                    source: source,
                    provider: candidate.provider,
                    model: candidate.model,
                    prompt: messages.map { "[\($0.role)] \($0.content)" }.joined(separator: "\n\n"),
                    response: content,
                    status: "completed",
                    durationMs: Int(Date().timeIntervalSince(started) * 1000)
                )
                return (content, "")
            }
            let reason = response.error.isEmpty ? "empty response" : response.error
            ModelRotator.shared.markFailure(candidate: candidate, cooldownProvider: response.unavailable || response.permanent)
            return (nil, "\(candidate.provider)/\(candidate.model): \(reason)")
        } catch is CancellationError {
            return (nil, "")
        } catch {
            let message = (error as NSError).localizedDescription
            let lower = message.lowercased()
            let looksLikeAuthFailure = message.contains("401") || message.contains("403")
                || lower.contains("credentials") || lower.contains("invalid api key") || lower.contains("auth failed")
            ModelRotator.shared.markFailure(candidate: candidate, cooldownProvider: looksLikeAuthFailure)
            return (nil, "\(candidate.provider)/\(candidate.model): \(message)")
        }
    }

    /// Ports `cleaned` — strips the workspace/control markers the model appends.
    static func strippingMarkers(_ raw: String) -> String {
        var working = raw
        if let marker = working.range(of: "[SEARCH:") {
            working = String(working[..<marker.lowerBound])
        }
        working = AiChatIntentDetector.replacing(working, pattern: #"\[PICO:[^\]]*\]"#, with: "")
        working = AiChatIntentDetector.replacing(working, pattern: #"\[RESEARCH_QUESTION:[^\]]*\]"#, with: "")
        working = AiChatIntentDetector.replacing(working, pattern: #"\[SECTION:[^\]]*\]"#, with: "")
        return working.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

// MARK: - Backend modules

/// Ports `fetchThesisTopics`, `fetchCounselorAdvice`, `searchQuestionsForKeyword` and
/// `searchCommunityPosts` — the four direct PHP calls the chat screen makes outside the
/// AI gateway, plus the `chat_history.php` session sync.
enum AiChatBackend {

    private static let session: URLSession = {
        let configuration = URLSessionConfiguration.default
        configuration.timeoutIntervalForRequest = 25
        configuration.timeoutIntervalForResource = 60
        return URLSession(configuration: configuration)
    }()

    private static let syncSession: URLSession = {
        let configuration = URLSessionConfiguration.default
        configuration.timeoutIntervalForRequest = 12
        return URLSession(configuration: configuration)
    }()

    private static func url(_ path: String, _ query: [String: String]) -> URL? {
        guard var components = URLComponents(string: APIConfig.baseURL.absoluteString + path) else { return nil }
        components.queryItems = query.map { URLQueryItem(name: $0.key, value: $0.value) }
        return components.url
    }

    private static func getJSON(_ target: URL, timeoutSession: URLSession = session) async -> [String: Any]? {
        var request = URLRequest(url: target)
        request.timeoutInterval = timeoutSession.timeoutIntervalForRequest
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue(APIConfig.appSignature, forHTTPHeaderField: "X-App-Signature")
        request.setValue(APIConfig.userAgent, forHTTPHeaderField: "User-Agent")
        guard let (data, _) = try? await timeoutSession.data(for: request) else { return nil }
        return (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
    }

    private static func postJSON(_ target: URL, _ body: [String: Any]) async -> [String: Any]? {
        var request = URLRequest(url: target)
        request.httpMethod = "POST"
        request.setValue("application/json; charset=utf-8", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue(APIConfig.appSignature, forHTTPHeaderField: "X-App-Signature")
        request.setValue(APIConfig.userAgent, forHTTPHeaderField: "User-Agent")
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        guard let (data, _) = try? await session.data(for: request) else { return nil }
        return (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
    }

    private static func string(_ object: Any?, _ key: String) -> String {
        (object as? [String: Any])?[key] as? String ?? ""
    }

    private static func int(_ object: Any?, _ key: String) -> Int {
        if let value = (object as? [String: Any])?[key] as? Int { return value }
        if let text = (object as? [String: Any])?[key] as? String { return Int(text) ?? 0 }
        return 0
    }

    // MARK: Question bank

    /// Ports `searchQuestionsForKeyword` — full-text search of the 280k bank via `searchv2`.
    static func searchQuestions(keyword: String, userId: Int) async -> [AiRelatedQuestion] {
        guard let target = url(
            "api/searchv2.php",
            ["keyword": keyword, "type": "json", "user_id": String(userId)]
        ), let root = await getJSON(target) else { return [] }
        guard string(root, "status") == "success" else { return [] }
        let results = (root["results"] as? [String: Any]) ?? root
        guard let rows = results["questions"] as? [[String: Any]] else { return [] }
        return rows.compactMap { row in
            let id = int(row, "question_id")
            let text = string(row, "question").trimmingCharacters(in: .whitespacesAndNewlines)
            guard id > 0, !text.isEmpty else { return nil }
            return AiRelatedQuestion(
                id: id,
                text: text,
                subject: string(row, "subject").trimmingCharacters(in: .whitespacesAndNewlines),
                topic: string(row, "topic").trimmingCharacters(in: .whitespacesAndNewlines),
                explanation: string(row, "explanation").trimmingCharacters(in: .whitespacesAndNewlines)
            )
        }
    }

    // MARK: Community posts

    /// Ports `searchCommunityPosts` — post photos + captions for a topic keyword.
    static func communityPosts(keyword: String, userId: Int) async -> [AiCommunityPost] {
        guard let target = url(
            "api/posts_search.php",
            ["q": keyword, "user_id": String(userId)]
        ), let root = await getJSON(target) else { return [] }
        guard string(root, "status") == "success", let rows = root["posts"] as? [[String: Any]] else { return [] }
        return rows.compactMap { row in
            let id = int(row, "post_id")
            let caption = string(row, "caption").trimmingCharacters(in: .whitespacesAndNewlines)
            guard id > 0, !caption.isEmpty else { return nil }
            let images = ((row["images"] as? [Any]) ?? [])
                .compactMap { $0 as? String }
                .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
                .filter { $0.hasPrefix("http") }
            return AiCommunityPost(
                id: id,
                author: string(row, "author").trimmingCharacters(in: .whitespacesAndNewlines),
                authorPhoto: string(row, "author_photo").trimmingCharacters(in: .whitespacesAndNewlines),
                caption: caption,
                images: images,
                likes: int(row, "likes"),
                uploadDate: string(row, "upload_date")
            )
        }
    }

    // MARK: Thesis topics

    /// Ports `fetchThesisTopics` — `thesis_topics_search.php`, returning up to 15 catalog rows.
    static func thesisTopics(query: String, userId: Int) async -> [ThesisTopicResult] {
        guard let target = url(
            "thesis_topics_search.php",
            ["q": query, "limit": "15", "user_id": String(userId)]
        ), let root = await getJSON(target) else { return [] }
        guard (root["success"] as? Bool) == true, let rows = root["data"] as? [[String: Any]] else { return [] }
        return rows.map { row in
            let thesisId = int(row, "thesis_id")
            let subject = string(row, "subject")
            let snippet = string(row, "snippet")
            return ThesisTopicResult(
                id: thesisId,
                subject: subject,
                snippet: snippet,
                displayTitle: displayTitle(snippet: snippet, subject: subject, thesisId: thesisId),
                studyType: string(row, "study_type"),
                difficulty: string(row, "difficulty")
            )
        }
    }

    /// Ports `ThesisTopicResult.displayTitle` — the catalog has no title column, so the
    /// paper title is the leading sentence of the snippet.
    private static func displayTitle(snippet: String, subject: String, thesisId: Int) -> String {
        let trimmed = snippet.trimmingCharacters(in: .whitespacesAndNewlines)
        let firstSentence = (trimmed.components(separatedBy: ". ").first ?? trimmed)
            .trimmingCharacters(in: CharacterSet(charactersIn: ". "))
        if firstSentence.count >= 12 {
            return firstSentence.count > 90
                ? String(firstSentence.prefix(90)).trimmingCharacters(in: .whitespaces) + "…"
                : firstSentence
        }
        let cleanSubject = subject.trimmingCharacters(in: .whitespacesAndNewlines)
        return cleanSubject.isEmpty ? "Thesis #\(thesisId)" : cleanSubject
    }

    // MARK: NEET PG counselor

    /// Ports `fetchCounselorAdvice` — natural-language query to `ai_predictor.php`.
    static func counselAdvice(message: String, userId: Int) async -> CounselCardData {
        guard let target = url("ai_predictor.php", [:]) else {
            return CounselCardData(query: message, summary: "", results: [], error: "Counselor service unavailable.")
        }
        guard let root = await postJSON(target, ["message": message, "user_id": userId]) else {
            return CounselCardData(query: message, summary: "", results: [], error: "Counselor service unavailable.")
        }
        guard (root["success"] as? Bool) == true else {
            let error = string(root, "error")
            return CounselCardData(
                query: message,
                summary: "",
                results: [],
                error: error.isEmpty ? "AI could not understand the query" : error
            )
        }
        let rows = root["results"] as? [[String: Any]] ?? []
        let colleges = rows.map { row in
            CounselCollege(
                institute: string(row, "institute"),
                course: string(row, "course"),
                closingRank: string(row, "closing_rank"),
                category: string(row, "category"),
                quota: string(row, "quota"),
                state: string(row, "state"),
                feePerYear: string(row, "fee_per_year"),
                stipendYear1: string(row, "stipend_year1"),
                bondYears: string(row, "bond_years"),
                chance: string(row, "chance")
            )
        }
        return CounselCardData(query: message, summary: string(root, "summary"), results: colleges)
    }

    // MARK: Chat history sync

    private static let chatHistoryPath = "chat_history.php"

    /// Ports `chatSyncFetchList` — the server's session index for the user.
    static func syncSessionList(userId: Int) async -> [AiChatSessionMeta] {
        guard userId > 0,
              let target = url(chatHistoryPath, ["action": "list", "user_id": String(userId)]),
              let root = await getJSON(target, timeoutSession: syncSession),
              let rows = root["sessions"] as? [[String: Any]] else { return [] }
        return rows.map { row in
            AiChatSessionMeta(
                id: string(row, "session_id"),
                title: string(row, "title").isEmpty ? "AI Chat" : string(row, "title"),
                updatedAt: Double(int(row, "updated_at")),
                pinned: (row["pinned"] as? Bool) ?? false
            )
        }
    }

    /// Ports `chatSyncDownload` — one full session from the server.
    static func syncDownload(sessionId: String, userId: Int) async -> AiChatSession? {
        guard userId > 0,
              let target = url(chatHistoryPath, [
                "action": "load",
                "user_id": String(userId),
                "session_id": sessionId
              ]),
              let root = await getJSON(target, timeoutSession: syncSession),
              (root["success"] as? Bool) == true,
              let source = root["session"] as? [String: Any] else { return nil }
        let turns = ((source["turns"] as? [[String: Any]]) ?? []).compactMap { row -> AiChatTurn? in
            let content = string(row, "content")
            guard !content.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return nil }
            let role = string(row, "role").isEmpty ? "user" : string(row, "role")
            return AiChatTurn(role: role, content: content, feedback: int(row, "feedback"))
        }
        return AiChatSession(
            id: string(source, "session_id").isEmpty ? sessionId : string(source, "session_id"),
            title: string(source, "title").isEmpty ? "AI Chat" : string(source, "title"),
            createdAt: Double(int(source, "created_at")),
            updatedAt: Double(int(source, "updated_at")),
            turns: turns,
            pdfName: string(source, "pdf_name"),
            pdfPreview: string(source, "pdf_preview"),
            pinned: (source["pinned"] as? Bool) ?? false
        )
    }

    /// Ports `chatSyncUpload` — fire-and-forget backup of the full session.
    static func syncUpload(_ session: AiChatSession, userId: Int) {
        guard userId > 0, let target = url(chatHistoryPath, [:]) else { return }
        let body: [String: Any] = [
            "action": "save",
            "user_id": userId,
            "session_id": session.id,
            "title": session.title,
            "created_at": Int(session.createdAt),
            "updated_at": Int(session.updatedAt),
            "turns": session.turns.map { ["role": $0.role, "content": $0.content, "feedback": $0.feedback] },
            "pdf_name": session.pdfName,
            "pdf_preview": String(session.pdfPreview.prefix(18000)),
            "pinned": session.pinned
        ]
        var request = URLRequest(url: target)
        request.httpMethod = "POST"
        request.setValue("application/json; charset=utf-8", forHTTPHeaderField: "Content-Type")
        request.setValue(APIConfig.appSignature, forHTTPHeaderField: "X-App-Signature")
        request.setValue(APIConfig.userAgent, forHTTPHeaderField: "User-Agent")
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        URLSession.shared.dataTask(with: request).resume()
    }

    /// Ports `chatSyncDelete` — fire-and-forget remote delete.
    static func syncDelete(sessionId: String, userId: Int) {
        guard userId > 0,
              let target = url(chatHistoryPath, [
                "action": "delete",
                "user_id": String(userId),
                "session_id": sessionId
              ]),
              let request = signedRequest(target) else { return }
        URLSession.shared.dataTask(with: request).resume()
    }

    private static func signedRequest(_ target: URL) -> URLRequest? {
        var request = URLRequest(url: target)
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue(APIConfig.appSignature, forHTTPHeaderField: "X-App-Signature")
        request.setValue(APIConfig.userAgent, forHTTPHeaderField: "User-Agent")
        return request
    }

    /// Ports `mergeSessionMetas` — pinned first, then most recently updated.
    static func merge(_ local: [AiChatSessionMeta], _ remote: [AiChatSessionMeta]) -> [AiChatSessionMeta] {
        var byId: [String: AiChatSessionMeta] = [:]
        for meta in local + remote {
            guard let previous = byId[meta.id] else {
                byId[meta.id] = meta
                continue
            }
            if meta.updatedAt > previous.updatedAt {
                byId[meta.id] = AiChatSessionMeta(
                    id: meta.id,
                    title: meta.title,
                    updatedAt: meta.updatedAt,
                    pinned: meta.pinned || previous.pinned
                )
            } else {
                byId[meta.id] = AiChatSessionMeta(
                    id: previous.id,
                    title: previous.title,
                    updatedAt: previous.updatedAt,
                    pinned: meta.pinned || previous.pinned
                )
            }
        }
        return byId.values.sorted { lhs, rhs in
            lhs.pinned == rhs.pinned ? lhs.updatedAt > rhs.updatedAt : lhs.pinned
        }
    }

    // MARK: Data-quality write-back

    /// Ports `postTopicAssignment` — persists an AI-chosen topic via `update_question_topic.php`.
    static func postTopicAssignment(questionId: Int, topic: String, subject: String) async -> Bool {
        guard let target = url("api/update_question_topic.php", [:]) else { return false }
        let root = await postForm(target, [
            "question_id": String(questionId),
            "topic": topic,
            "subject": subject
        ])
        return (root?["success"] as? Bool) ?? false
    }

    /// Ports `postExplanation` — persists an AI-written explanation via `update_question_explanation.php`.
    static func postExplanation(questionId: Int, explanation: String) async -> Bool {
        guard let target = url("api/update_question_explanation.php", [:]) else { return false }
        let root = await postForm(target, [
            "question_id": String(questionId),
            "explanation": explanation
        ])
        return (root?["success"] as? Bool) ?? false
    }

    private static func postForm(_ target: URL, _ fields: [String: String]) async -> [String: Any]? {
        var request = URLRequest(url: target)
        request.httpMethod = "POST"
        request.setValue("application/x-www-form-urlencoded; charset=utf-8", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue(APIConfig.appSignature, forHTTPHeaderField: "X-App-Signature")
        request.setValue(APIConfig.userAgent, forHTTPHeaderField: "User-Agent")
        request.httpBody = HTTPClient.formEncode(fields)
        guard let (data, _) = try? await session.data(for: request) else { return nil }
        return (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
    }
}

// MARK: - View model

/// Drives the standalone Medical AI chat screen.
/// Ports `AiChatActivity` / `AiChatScreen` from Android's `AiChatActivity.kt`.
@MainActor
final class AiChatViewModel: NSObject, ObservableObject, AVSpeechSynthesizerDelegate {

    /// Ports `AiModelMode` — the persisted Fast / Balanced / Reasoning selector that
    /// picks the provider pool for chat replies.
    enum AiModelMode: String, CaseIterable {
        case fast
        case balanced
        case reasoning

        /// `label` in the Kotlin enum — what the header pill shows.
        var label: String {
            switch self {
            case .fast: return "⚡ Fast"
            case .balanced: return "⚖️ Balanced"
            case .reasoning: return "🧠 Reasoning"
            }
        }

        /// `provider` in the Kotlin enum — the pool handed to `ModelRotator.buildPool`.
        var provider: String {
            switch self {
            case .fast: return "groq"
            case .balanced: return "auto"
            case .reasoning: return "deepseek"
            }
        }

        /// Ports `AiModelMode.next()`.
        func next() -> AiModelMode {
            let all = AiModelMode.allCases
            guard let index = all.firstIndex(of: self) else { return .balanced }
            return all[(index + 1) % all.count]
        }
    }

    /// Ports `AI_MODEL_MODE_KEY` — `SharedPreferences("MY_APP")` key `"ai_model_mode"`.
    private static let modelModeKey = "ai_model_mode"

    /// Ports the Kotlin apology returned when every provider candidate failed.
    private static let failureReply = "I apologize, but I'm having trouble connecting to my knowledge base right now. Please try your question again in a moment."

    /// Ports the `searchPhase` ladder: 0 idle, 1 searching, 2 done, 3 none.
    enum SearchPhase: Int {
        case idle = 0
        case searching = 1
        case done = 2
        case none = 3
    }

    // MARK: Published state

    @Published var modelMode: AiModelMode = .balanced
    @Published var messages: [AiChatMessage] = []
    @Published var input: String = ""
    @Published var isLoading: Bool = false
    @Published var streamingText: String? = nil
    @Published var isThinking: Bool = false
    @Published var attachedDocumentName: String? = nil
    @Published var pdfContext: AiChatPdfContext? = nil
    @Published var documentNote: String = ""
    @Published var isReadingDocument: Bool = false
    @Published var activeQuizToLaunch: Quiz? = nil
    @Published var isSpeaking: Bool = false
    @Published var toastMessage: String? = nil
    @Published var workspace: WorkspaceState = WorkspaceState()
    @Published var activeSkillName: String? = nil
    @Published var enrichmentNote: String = ""
    @Published var searchPhase: SearchPhase = .idle
    @Published var posts: [AiCommunityPost] = []
    @Published var sessions: [AiChatSessionMeta] = []
    @Published var isHistoryPresented: Bool = false
    @Published var errorMessage: String? = nil

    private let speechSynthesizer = AVSpeechSynthesizer()
    private var activeTask: Task<Void, Never>? = nil
    private var attachment: AiChatAttachment?
    private var editingIndex: Int?
    private var sessionId: String?
    private var sessionCreatedAt: Double = 0
    private var sessionTitleOverride: String?
    private var hasRestoredSession = false
    private var currentUserId: Int = 0

    // MARK: Static content

    /// Ports the `ToolChip(...)` row of `AiChatScreen`.
    let toolChips: [String] = [
        "📄 Upload Doc",
        "🧬 PICO",
        "🔬 PubMed",
        "✅ Evidence",
        "🧪 Entities",
        "🎓 Thesis",
        "🎯 Counselor",
        "🖼️ Poster",
        "📚 Chapter",
        "🛡️ Audit",
        "⚖️ Ethics",
        "📊 Stats (n)",
        "🤖 Coding Agent",
        "📜 Diff Viewer"
    ]

    /// Ports `ChatWelcomeHint`'s one-tap prompts.
    let suggestions: [AiPromptSuggestion] = [
        AiPromptSuggestion(
            icon: "stethoscope",
            title: "Clinical Differential",
            prompt: "Provide a structured differential diagnosis for a 45-year-old with acute RUQ pain, fever, and jaundice."
        ),
        AiPromptSuggestion(
            icon: "pills.fill",
            title: "Drug Interactions",
            prompt: "Explain the clinical pharmacokinetics and risk of combining Warfarin with Fluconazole, and recommend monitoring steps."
        ),
        AiPromptSuggestion(
            icon: "cross.case.fill",
            title: "Treatment Protocol",
            prompt: "What is the updated emergency management protocol for adult Status Epilepticus from minute 0 to 60?"
        ),
        AiPromptSuggestion(
            icon: "brain.head.profile",
            title: "NEET-PG Pearls",
            prompt: "Summarize the high-yield classical clinical triads and pathognomonic biopsy signs in systemic vasculitis."
        ),
        AiPromptSuggestion(
            icon: "doc.text.magnifyingglass",
            title: "Thesis & Literature",
            prompt: "Highlight the key methodology and endpoints used in recent clinical trials on SGLT2 inhibitors in heart failure."
        )
    ]

    override init() {
        super.init()
        speechSynthesizer.delegate = self
        loadWelcomeMessage()
        modelMode = Self.loadModelMode()
    }

    // MARK: - Model mode

    /// Ports `loadAiModelMode` — `AiModelMode.valueOf(...)` with `BALANCED` as the default.
    private static func loadModelMode() -> AiModelMode {
        guard let raw = UserDefaults.standard.string(forKey: modelModeKey),
              let mode = AiModelMode(rawValue: raw) else { return .balanced }
        return mode
    }

    /// Ports `onCycleModelMode` — persists the choice and toasts the new label.
    func cycleModelMode() {
        modelMode = modelMode.next()
        UserDefaults.standard.set(modelMode.rawValue, forKey: Self.modelModeKey)
        showToast("Model mode: \(modelMode.label)")
    }

    // MARK: - Tool chips

    /// Ports the `onPico` / `onLiterature` / … lambdas behind each tool chip.
    func onToolChipTapped(_ chip: String) {
        switch chip {
        case "📄 Upload Doc":
            showToast("Choose a PDF, slide deck or case sheet to chat with 📎")
        case "🧬 PICO":
            input = "Extract PICO from: "
        case "🔬 PubMed":
            input = "Search PubMed for: "
        case "✅ Evidence":
            input = "Validate these claims: "
        case "🧪 Entities":
            input = "Extract medical entities from: "
        case "🎓 Thesis":
            input = "Search thesis topics on: "
        case "🎯 Counselor":
            input = "🎯 Predict my NEET PG colleges: my rank is 12000 in GEN category, want MD Medicine in Karnataka"
        case "🖼️ Poster":
            input = "Generate a poster from this abstract:\n"
        case "📚 Chapter":
            if pdfContext == nil {
                showToast("First upload a PDF via 📄 Upload Doc")
            } else {
                input = "Generate the Methodology chapter from my uploaded PDF with a figure, table and chart"
            }
        case "🛡️ Audit":
            input = "Perform a formal protocol audit on my thesis methodology and results."
        case "⚖️ Ethics":
            input = "Check my research for IRB and Informed Consent compliance."
        case "📊 Stats (n)":
            input = "Calculate the required sample size for my study."
        case "🤖 Coding Agent":
            input = "Run Autonomous Coding Agent on: "
        case "📜 Diff Viewer":
            input = "Show diff for the following change:\n"
        default:
            input = chip + ": "
        }
    }

    // MARK: - Sending

    /// Ports `ChatInputBar.onSend` — autocorrect, then `send()`, honouring a pending
    /// edit-and-resend truncation.
    func sendCurrentInput(api: MediGyaanAPI, userId: Int) {
        let raw = input.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !raw.isEmpty else { return }
        input = ""
        let pending = attachment
        attachment = nil
        attachedDocumentName = nil
        let editFrom = editingIndex
        editingIndex = nil
        send(prompt: AiAutoCorrect.correct(text: raw), attachment: pending, api: api, userId: userId, editFrom: editFrom)
    }

    /// Ports `ChatWelcomeHint`'s suggestion cards.
    func selectSuggestion(_ suggestion: AiPromptSuggestion, api: MediGyaanAPI, userId: Int) {
        send(prompt: suggestion.prompt, attachment: nil, api: api, userId: userId, editFrom: nil)
    }

    /// Ports `startEdit(userIndex)` — reload a user turn into the composer for replacement.
    func startEdit(message: AiChatMessage) {
        guard !isLoading else { return }
        guard let index = messages.firstIndex(where: { $0.id == message.id }), messages[index].isUser else { return }
        editingIndex = index
        input = message.text
    }

    /// Ports `toggleLike` / `toggleDislike` — re-tapping the same vote clears it.
    func toggleFeedback(for message: AiChatMessage, like: Bool) {
        guard let index = messages.firstIndex(where: { $0.id == message.id }) else { return }
        let target = like ? 1 : -1
        messages[index].feedback = messages[index].feedback == target ? 0 : target
    }

    /// Ports `stopGeneration()` — cancels the in-flight request and the typing effect.
    func stopGenerating() {
        activeTask?.cancel()
        activeTask = nil
        isLoading = false
        isThinking = false
        streamingText = nil
    }

    /// Ports `regenerate(ownerIndex)` — truncates back to the owning user turn and re-sends.
    func regenerate(message: AiChatMessage, api: MediGyaanAPI, userId: Int) {
        guard !isLoading else { return }
        guard let index = messages.firstIndex(where: { $0.id == message.id }) else { return }
        let userIndex = messages.prefix(upTo: index).lastIndex { $0.isUser } ?? index
        guard messages[userIndex].isUser else { return }
        let prompt = messages[userIndex].text
        input = ""
        send(prompt: prompt, attachment: nil, api: api, userId: userId, editFrom: userIndex)
    }

    /// The body of `send()` in `AiChatScreen`: the skill pipeline, the module cards,
    /// the gateway chat call, the ChatGPT-style reveal, and the related-question search.
    private func send(
        prompt: String,
        attachment: AiChatAttachment?,
        api: MediGyaanAPI,
        userId: Int,
        editFrom: Int?
    ) {
        let text = prompt.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, !isLoading else { return }

        currentUserId = userId
        activeTask?.cancel()

        var turnList = messages.map {
            AiChatTurn(role: $0.isUser ? "user" : "assistant", content: $0.text, feedback: $0.feedback)
        }

        if let editFrom, editFrom < messages.count {
            messages = Array(messages.prefix(editFrom))
            turnList = Array(turnList.prefix(editFrom))
        }
        editingIndex = nil

        messages.append(AiChatMessage(role: .user, text: text, attachmentName: attachment?.name))
        isLoading = true
        isThinking = true
        searchPhase = .idle
        posts = []
        enrichmentNote = ""
        streamingText = nil

        let history = turnList + [AiChatTurn(role: "user", content: text)]
        let document = pdfContext

        activeTask = Task { [weak self] in
            guard let self else { return }

            let skillName = ResearchSkillHandler.routeToSkill(text: text, hasPdf: document != nil)
            var outcome: SkillOutcome?
            if skillName != "NONE" {
                activeSkillName = skillName
                enrichmentNote = "Executing Skill: \(skillName)…"
                outcome = await ResearchSkillHandler.executeSkill(
                    skillName: Self.executableSkill(skillName),
                    userInput: text,
                    pdfText: document?.textPreview ?? ""
                )
                isThinking = false
                enrichmentNote = ""
            }

            let counselCard = await runCounselModule(text: text, userId: userId)
            let thesisCard = await runThesisModule(text: text, userId: userId)
            let chapterCard = await runChapterModule(text: text, document: document, userId: userId)

            isThinking = true
            let started = Date()
            let raw = await replyText(history: history, document: document, attachment: attachment, outcome: outcome, userId: userId, api: api)
            if Task.isCancelled { stopGenerating(); return }

            let verified = await audit(raw: raw, skillName: skillName, original: text)
            workspace = ResearchSkillHandler.updateWorkspace(current: workspace, aiOutput: verified)
            activeSkillName = nil

            let keyword = AiChatIntentDetector.parseSearchKeyword(raw)
                ?? AiChatIntentDetector.explicitQuestionTopic(text)
                ?? AiChatIntentDetector.findMedicalCondition(text)
            let postsOnlyKeyword = keyword == nil ? AiChatIntentDetector.explicitPostsTopic(text) : nil

            let cleaned = AiChatGateway.strippingMarkers(verified)
            let reply = cleaned.isEmpty ? "⚠ AI gave an empty reply. Try again." : cleaned

            isThinking = false
            await revealStreaming(reply)
            if Task.isCancelled { stopGenerating(); return }

            var related: [AiRelatedQuestion] = []
            if let keyword {
                searchPhase = .searching
                related = await findRelatedQuestions(aiKeyword: keyword, userText: text, userId: userId)
                searchPhase = related.isEmpty ? .none : .done
                if let postsKeyword = AiChatIntentDetector.bestPostsKeyword(keyword, userText: text) {
                    posts = Array(await AiChatBackend.communityPosts(keyword: postsKeyword, userId: userId).prefix(6))
                }
            } else if let postsOnlyKeyword,
                      let postsKeyword = AiChatIntentDetector.bestPostsKeyword(postsOnlyKeyword, userText: "") {
                posts = Array(await AiChatBackend.communityPosts(keyword: postsKeyword, userId: userId).prefix(6))
            }

            let elapsed = Int(Date().timeIntervalSince(started) * 1000)
            messages.append(AiChatMessage(
                role: .assistant,
                text: reply,
                relatedQuestions: related.map { Self.question(from: $0) },
                isStreaming: false,
                responseTimeMs: elapsed,
                counselCard: counselCard,
                thesisCard: thesisCard,
                chapterCard: chapterCard,
                skillOutcome: outcome,
                skillName: skillName == "NONE" ? nil : skillName
            ))

            isLoading = false
            isThinking = false
            streamingText = nil
            activeTask = nil
            persistSession(userId: userId)
            await enrich(questions: related)
        }
    }

    /// Ports the `try { requestAiChat(...) } catch` branch of `send()`, plus the
    /// `ask_ai2.php` last resort so a total gateway outage still answers.
    private func replyText(
        history: [AiChatTurn],
        document: AiChatPdfContext?,
        attachment: AiChatAttachment?,
        outcome: SkillOutcome?,
        userId: Int,
        api: MediGyaanAPI
    ) async -> String {
        do {
            return try await AiChatGateway.chat(
                turns: history,
                pdfContext: document,
                attachment: attachment,
                skillOutcome: outcome,
                providerPool: modelMode.provider,
                userId: userId
            )
        } catch {
            if Task.isCancelled { return "" }
            RemoteLogger.log(
                tag: "AiChat",
                message: "AI chat execution failed",
                metadata: ["error_description": LoadState<Never>.message(for: error)]
            )
            var context = ""
            if let document {
                context += document.contextPrompt() + "\n"
            }
            if let outcome {
                context += "SKILL_OUTCOME:\n\(outcome.contextText)\n"
            }
            context += AiChatGateway.systemPrompt + "\n"
            for turn in history {
                context += "\(turn.role): \(turn.content)\n"
            }
            guard let fallback = try? await api.ai.ask(
                prompt: history.last?.content ?? "",
                userId: userId,
                model: nil,
                context: context
            ), !fallback.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                return Self.failureReply
            }
            return fallback
        }
    }

    /// Ports the "Final Research Auditor" pass — research replies get a sanity note appended.
    private func audit(raw: String, skillName: String, original: String) async -> String {
        guard skillName != "NONE" else { return raw }
        enrichmentNote = "Auditing research response…"
        let result = await ResearchSkillHandler.executeSkill(skillName: "Final Research Auditor", userInput: original, pdfText: raw)
        enrichmentNote = ""
        return result.success ? raw : raw + "\n\n⚠️ [Audit Note: \(result.contextText)]"
    }

    /// Ports the ChatGPT-style reveal loop — `step = (len / 160).coerceIn(1, 6)`, 11 ms apart.
    private func revealStreaming(_ text: String) async {
        let characters = text.count
        guard characters > 0 else { return }
        let step = max(1, min(6, characters / 160))
        var revealed = 0
        while revealed < characters {
            revealed = min(revealed + step, characters)
            streamingText = String(text.prefix(revealed))
            try? await Task.sleep(nanoseconds: 11_000_000)
            if Task.isCancelled { return }
        }
    }

    /// Ports the NEET PG counselor card block (step 1 of `send()`).
    private func runCounselModule(text: String, userId: Int) async -> CounselCardData? {
        guard let query = AiChatIntentDetector.detectCounselQuery(text) else { return nil }
        enrichmentNote = "Consulting NEET PG predictor…"
        let card = await AiChatBackend.counselAdvice(message: query, userId: userId)
        enrichmentNote = ""
        return card
    }

    /// Ports the thesis topics catalog card block (step 2 of `send()`).
    private func runThesisModule(text: String, userId: Int) async -> ThesisCardData? {
        guard let query = AiChatIntentDetector.detectThesisTopicSearch(text) else { return nil }
        enrichmentNote = "Searching catalog…"
        let results = await AiChatBackend.thesisTopics(query: query, userId: userId)
        enrichmentNote = ""
        return ThesisCardData(query: query, results: results)
    }

    /// Ports the chapter generator card block (step 5 of `send()`).
    private func runChapterModule(text: String, document: AiChatPdfContext?, userId: Int) async -> ChapterCardData? {
        guard let document, let chapter = AiChatIntentDetector.detectChapterRequest(text: text, pdfContext: document) else { return nil }
        enrichmentNote = "📚 Generating \(chapter)…"
        defer { enrichmentNote = "" }
        let sections = AiChatChapterCatalog.headings[chapter] ?? []
        let prompt = Self.chapterPrompt(chapter: chapter, sections: sections, request: text, document: document)
        do {
            let raw = try await AiChatGateway.rotate(
                messages: [
                    LegacyAIMessage(role: "system", content: document.contextPrompt()),
                    LegacyAIMessage(role: "user", content: prompt)
                ],
                maxTokens: 3000,
                source: "ai_chat_chapter",
                userId: userId
            )
            let parsed = Self.chapterHeadings(from: raw)
            return ChapterCardData(chapterName: chapter, sections: parsed.isEmpty ? sections : parsed)
        } catch {
            return ChapterCardData(chapterName: chapter, sections: sections)
        }
    }

    /// Ports the chapter prompt of `runChapterGeneration`, asking for the headings only.
    private static func chapterPrompt(
        chapter: String,
        sections: [String],
        request: String,
        document: AiChatPdfContext
    ) -> String {
        let headingList = sections.isEmpty ? "Background, Aim, Methodology, Results, Discussion, Conclusion" : sections.joined(separator: ", ")
        return """
        The user uploaded a thesis PDF ("\(document.fileName)") and asked you to generate the "\(chapter)" chapter.
        Their exact request was: "\(String(request.prefix(300)))" — honour any specific elements they asked for.

        Use ONLY information present in the uploaded PDF. Never invent data, statistics or references.
        Write formal thesis-style narrative and add inline Vancouver citation labels like [1].

        Return ONLY valid JSON, no markdown fences, in exactly this shape:
        {"chapterName":"\(chapter)","sections":[{"heading":"<heading>","content":"<paragraph>"}]}

        Use these exact section headings, in this order: \(headingList).
        """
    }

    /// Ports `parseChatChapter` — the heading list out of the model's JSON reply.
    private static func chapterHeadings(from raw: String) -> [String] {
        var trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.hasPrefix("```json") { trimmed.removeFirst("```json".count) }
        else if trimmed.hasPrefix("```") { trimmed.removeFirst(3) }
        if trimmed.hasSuffix("```") { trimmed = String(trimmed.dropLast(3)) }
        guard let first = trimmed.firstIndex(of: "{"), let last = trimmed.lastIndex(of: "}"), first < last else { return [] }
        let json = String(trimmed[first...last])
        guard let data = json.data(using: .utf8),
              let parsed = try? JSONSerialization.jsonObject(with: data),
              let root = parsed as? [String: Any],
              let rows = root["sections"] as? [[String: Any]] else { return [] }
        return rows.compactMap { row in
            guard let heading = row["heading"] as? String else { return nil }
            let clean = heading.trimmingCharacters(in: .whitespacesAndNewlines)
            return clean.isEmpty ? nil : clean
        }
    }

    /// Ports `findRelatedQuestions` — several keyword candidates, merged, 12-row cap.
    private func findRelatedQuestions(aiKeyword: String?, userText: String, userId: Int) async -> [AiRelatedQuestion] {
        var candidates: [String] = []
        var seen = Set<String>()
        func add(_ candidate: String) {
            let clean = candidate.trimmingCharacters(in: .whitespacesAndNewlines)
            guard clean.count > 2, !seen.contains(clean) else { return }
            seen.insert(clean)
            candidates.append(clean)
        }
        if let aiKeyword, aiKeyword.count >= 2 { add(aiKeyword) }
        for token in (aiKeyword ?? "").components(separatedBy: " ") {
            let clean = token.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
            if clean.count > 2, !AiChatIntentDetector.searchStopWords.contains(clean) { add(clean) }
        }
        AiChatIntentDetector.fallbackKeywords(userText).forEach(add)
        guard !candidates.isEmpty else { return [] }

        var merged: [Int: AiRelatedQuestion] = [:]
        var order: [Int] = []
        for candidate in candidates {
            let results = await AiChatBackend.searchQuestions(keyword: candidate, userId: userId)
            for question in results where merged[question.id] == nil {
                merged[question.id] = question
                order.append(question.id)
            }
            if merged.count >= 12 { break }
        }
        return order.compactMap { merged[$0] }
    }

    /// Ports the background data-quality pass: AI tags blank topics and rewrites
    /// explanations shorter than 100 characters, then persists both.
    private func enrich(questions: [AiRelatedQuestion]) async {
        let targets = questions.filter { Self.needsAiTopic($0) || Self.needsAiExplanation($0) }.prefix(4)
        guard !targets.isEmpty else { return }
        enrichmentNote = "🧠 AI is enriching these questions…"
        var tagged = 0
        var explained = 0
        for question in targets {
            if Self.needsAiTopic(question),
               let label = await Self.requestTopicLabel(for: question.text, userId: currentUserId),
               !label.name.isEmpty {
                let subject = Self.isPaperLikeSubject(question.subject) ? label.subject : question.subject
                if await AiChatBackend.postTopicAssignment(questionId: question.id, topic: label.name, subject: subject) {
                    tagged += 1
                    applyTopic(id: question.id, topic: label.name, subject: subject)
                }
            }
            if Self.needsAiExplanation(question),
               let explanation = await Self.requestExplanation(for: question.text, current: question.explanation, userId: currentUserId),
               !explanation.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                if await AiChatBackend.postExplanation(questionId: question.id, explanation: explanation) {
                    explained += 1
                    applyExplanation(id: question.id, explanation: explanation)
                }
            }
        }
        var note = ""
        if tagged > 0 { note += "🧠 AI tagged \(tagged) question\(tagged == 1 ? "" : "s") with a topic" }
        if tagged > 0 && explained > 0 { note += " and " }
        if explained > 0 { note += "✍️ rewrote \(explained) short explanation\(explained == 1 ? "" : "s")" }
        enrichmentNote = note
    }

    /// Ports `needsAiTopic` — blank, or a placeholder like "PG 2020".
    private static func needsAiTopic(_ question: AiRelatedQuestion) -> Bool {
        let topic = question.topic.trimmingCharacters(in: .whitespacesAndNewlines)
        if topic.isEmpty { return true }
        return AiChatIntentDetector.matches(#"[0-9]{4}|^PG|^Neet|^pg$"#, in: topic)
    }

    /// Ports `isPaperLikeSubject` — old bulk imports put exam names in the subject column.
    private static func isPaperLikeSubject(_ subject: String) -> Bool {
        let clean = subject.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        return clean.isEmpty || clean.contains("neet pg") || clean.rangeOfCharacter(from: .decimalDigits) != nil
    }

    /// Ports `needsAiExplanation` — missing or shorter than 100 characters.
    private static func needsAiExplanation(_ question: AiRelatedQuestion) -> Bool {
        let explanation = question.explanation.trimmingCharacters(in: .whitespacesAndNewlines)
        return explanation.isEmpty || explanation.count < 100
    }

    /// Ports `requestTopicLabel` — returns the `(topic, subject)` pair.
    private static func requestTopicLabel(for questionText: String, userId: Int) async -> (name: String, subject: String)? {
        let system = "You classify NEET PG medical MCQs into a concise topic and a medical subject discipline."
        let user = "Question:\n\(questionText)\n\nReply with exactly two lines:\nTOPIC: <2-4 word topic, e.g. Glaucoma>\nSUBJECT: <medical discipline, e.g. Ophthalmology>"
        guard let raw = try? await AiChatGateway.rotate(
            messages: [LegacyAIMessage(role: "system", content: system), LegacyAIMessage(role: "user", content: user)],
            maxTokens: 60,
            source: "ai_chat_topic_label",
            userId: userId
        ) else { return nil }
        let topic = AiChatIntentDetector.firstCapture(#"TOPIC:\s*(.+)"#, in: raw) ?? ""
        let subject = AiChatIntentDetector.firstCapture(#"SUBJECT:\s*(.+)"#, in: raw) ?? ""
        return (topic, subject)
    }

    /// Ports `requestExplanation` — a brief clinical rationale for a thin explanation.
    private static func requestExplanation(for questionText: String, current: String, userId: Int) async -> String? {
        let system = "You write concise, clinically accurate explanations for NEET PG medical MCQ answers."
        let existing = current.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? "(none)" : current
        let user = "Question:\n\(questionText)\n\nCurrent explanation: \(existing)\n\nWrite a single-paragraph explanation of 2-4 sentences explaining the correct answer."
        return try? await AiChatGateway.rotate(
            messages: [LegacyAIMessage(role: "system", content: system), LegacyAIMessage(role: "user", content: user)],
            maxTokens: 400,
            source: "ai_chat_explanation",
            userId: userId
        )
    }

    /// Maps Android's routed skill names onto the deterministic solvers
    /// `ResearchSkillHandler` implements, so the calculators still run.
    private static func executableSkill(_ name: String) -> String {
        switch name {
        case "IRB/Ethics Validator": return "IRB Ethics Validator"
        case "Diff Change Viewer": return "Diff Viewer"
        case "ABG Acid-Base Solver": return "ABG Solver"
        case "Evidence Extractor", "PubMed Search": return "Medical Entity Extractor"
        default: return name
        }
    }

    private static func question(from related: AiRelatedQuestion) -> Question {
        Question(
            id: related.id,
            text: related.text,
            options: [],
            explanation: related.explanation,
            topic: related.topic,
            subject: related.subject
        )
    }

    /// Writes an AI-chosen topic back onto the related-question card.
    private func applyTopic(id: Int, topic: String, subject: String) {
        for messageIndex in messages.indices {
            for questionIndex in messages[messageIndex].relatedQuestions.indices
            where messages[messageIndex].relatedQuestions[questionIndex].id == id {
                let existing = messages[messageIndex].relatedQuestions[questionIndex]
                messages[messageIndex].relatedQuestions[questionIndex] = Question(
                    id: existing.id,
                    text: existing.text,
                    options: existing.options,
                    correctIndex: existing.correctIndex,
                    correctOptionIndex: existing.correctIndex,
                    explanation: existing.explanation,
                    imageURL: existing.imageURL,
                    topic: topic,
                    subject: subject.isEmpty ? existing.subject : subject,
                    marks: existing.marks,
                    negativeMarks: existing.negativeMarks,
                    difficulty: existing.difficulty
                )
            }
        }
    }

    /// Writes an AI-rewritten explanation back onto the related-question card.
    private func applyExplanation(id: Int, explanation: String) {
        for messageIndex in messages.indices {
            for questionIndex in messages[messageIndex].relatedQuestions.indices
            where messages[messageIndex].relatedQuestions[questionIndex].id == id {
                let existing = messages[messageIndex].relatedQuestions[questionIndex]
                messages[messageIndex].relatedQuestions[questionIndex] = Question(
                    id: existing.id,
                    text: existing.text,
                    options: existing.options,
                    correctIndex: existing.correctIndex,
                    correctOptionIndex: existing.correctIndex,
                    explanation: explanation,
                    imageURL: existing.imageURL,
                    topic: existing.topic,
                    subject: existing.subject,
                    marks: existing.marks,
                    negativeMarks: existing.negativeMarks,
                    difficulty: existing.difficulty
                )
            }
        }
    }

    // MARK: - Documents

    /// Ports `loadPdfFromUri` / `parseAttachment` — reads the picked file and turns it
    /// into the chat's PDF context plus a one-shot attachment.
    func attachDocument(at url: URL) {
        isReadingDocument = true
        documentNote = "Reading document…"
        Task { [weak self] in
            guard let self else { return }
            let accessed = url.startAccessingSecurityScopedResource()
            defer { if accessed { url.stopAccessingSecurityScopedResource() } }
            let name = url.lastPathComponent
            let data = try? Data(contentsOf: url)
            isReadingDocument = false

            guard let data, !data.isEmpty else {
                documentNote = "Could not read this document. Try another file."
                return
            }

            let isImage = ["jpg", "jpeg", "png", "webp", "bmp", "heic"].contains(url.pathExtension.lowercased())
            let text: String
            let kind: String
            if isImage, let image = UIImage(data: data) {
                text = await AiDocumentOcrHelper.recognizeText(from: image)
                kind = "image"
            } else {
                let extracted = AiDocumentOcrHelper.extractText(from: data)
                text = extracted.isEmpty ? (String(data: data, encoding: .utf8) ?? "") : extracted
                kind = url.pathExtension.lowercased() == "pdf" ? "pdf" : "document"
            }

            guard !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                documentNote = "Couldn't read that file. Try an image, PDF or text file."
                return
            }

            let compressed = Self.compressAttachmentText(text)
            pdfContext = AiChatPdfContext(
                fileName: name,
                textPreview: String(compressed.prefix(4000)),
                fullText: compressed
            )
            attachment = AiChatAttachment(name: name, kind: kind, text: compressed)
            attachedDocumentName = name
            documentNote = "\(Self.documentIcon(for: name)) \(name) loaded (\(compressed.count) characters). Ready for chat!"
        }
    }

    /// Ports `PdfStatusChip.onRemove`.
    func removeDocument() {
        pdfContext = nil
        attachment = nil
        attachedDocumentName = nil
        documentNote = ""
    }

    /// Ports `getDocumentIcon`.
    private static func documentIcon(for fileName: String) -> String {
        switch fileName.lowercased().split(separator: ".").last.map(String.init) ?? "" {
        case "pdf": return "📄"
        case "ppt", "pptx": return "📊"
        case "doc", "docx": return "📝"
        default: return "📎"
        }
    }

    /// Ports `compressAttachmentText` — keeps the high-yield lines and caps the payload.
    private static func compressAttachmentText(_ text: String, maxLength: Int = 20000) -> String {
        guard text.count > maxLength else { return text }
        let keywords = [
            "patient", "diagnosis", "treatment", "result", "conclusion", "method",
            "finding", "dose", "study", "pico", "aim", "summary"
        ]
        let lines = text.components(separatedBy: "\n")
        let highYield = lines.filter { line in
            let lower = line.lowercased()
            return keywords.contains { lower.contains($0) }
        }
        let compressed = highYield.isEmpty ? text : highYield.joined(separator: "\n")
        return String(compressed.prefix(maxLength))
    }

    // MARK: - Session persistence

    /// Ports the `LaunchedEffect(Unit)` auto-resume — local first, merged with the cloud copy.
    func restoreLastSession(userId: Int) async {
        guard !hasRestoredSession else { return }
        hasRestoredSession = true
        guard messages.count <= 1 else { return }
        currentUserId = userId
        let local = AiChatSessionStore.shared.list()
        let remote = await AiChatBackend.syncSessionList(userId: userId)
        sessions = AiChatBackend.merge(local, remote)
        guard let last = sessions.first else { return }
        guard let session = await loadSessionBody(id: last.id, userId: userId), !session.turns.isEmpty else { return }
        sessionId = session.id
        sessionCreatedAt = session.createdAt
        sessionTitleOverride = session.title
        messages = session.turns.map { turn in
            AiChatMessage(
                role: turn.isUser ? .user : .assistant,
                text: turn.content,
                feedback: turn.feedback,
                responseTimeMs: turn.responseTimeMs > 0 ? turn.responseTimeMs : nil
            )
        }
        if !session.pdfPreview.isEmpty {
            pdfContext = AiChatPdfContext(
                fileName: session.pdfName.isEmpty ? session.title : session.pdfName,
                textPreview: session.pdfPreview
            )
        }
    }

    /// Ports the `LaunchedEffect(turns, …)` autosave — write locally, then back up to the cloud.
    func persistSession(userId: Int) {
        guard !messages.isEmpty else { return }
        let now = Date().timeIntervalSince1970 * 1000
        let id = sessionId ?? "chat_\(Int(now))"
        if sessionId == nil {
            sessionId = id
            if sessionCreatedAt == 0 { sessionCreatedAt = now }
        }
        let turns = messages.compactMap { message -> AiChatTurn? in
            guard message.role != .system, !message.text.isEmpty else { return nil }
            return AiChatTurn(
                role: message.isUser ? "user" : "assistant",
                content: message.text,
                feedback: message.feedback,
                responseTimeMs: message.responseTimeMs ?? 0
            )
        }
        guard !turns.isEmpty else { return }
        let session = AiChatSession(
            id: id,
            title: sessionTitleOverride ?? Self.sessionTitle(from: turns),
            createdAt: sessionCreatedAt == 0 ? now : sessionCreatedAt,
            updatedAt: now,
            turns: turns,
            pdfName: pdfContext?.fileName ?? "",
            pdfPreview: pdfContext?.textPreview ?? "",
            pinned: sessions.first { $0.id == id }?.pinned ?? false
        )
        AiChatSessionStore.shared.save(session)
        sessions = AiChatSessionStore.shared.list()
        AiChatBackend.syncUpload(session, userId: userId)
    }

    /// Ports `sessionTitleFrom` — the first user line, capped at 48 characters.
    private static func sessionTitle(from turns: [AiChatTurn]) -> String {
        let first = turns.first { $0.isUser }?.content.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        let collapsed = AiChatIntentDetector.replacing(first, pattern: #"\s+"#, with: " ")
        let title = String(collapsed.prefix(48))
        return title.isEmpty ? "AI Chat" : title
    }

    /// Ports `loadHistorySession`.
    func loadSession(_ meta: AiChatSessionMeta, userId: Int) async {
        guard let session = await loadSessionBody(id: meta.id, userId: userId) else { return }
        stopGenerating()
        sessionId = session.id
        sessionCreatedAt = session.createdAt
        sessionTitleOverride = session.title
        messages = session.turns.map { turn in
            AiChatMessage(
                role: turn.isUser ? .user : .assistant,
                text: turn.content,
                feedback: turn.feedback,
                responseTimeMs: turn.responseTimeMs > 0 ? turn.responseTimeMs : nil
            )
        }
        pdfContext = session.pdfPreview.isEmpty
            ? nil
            : AiChatPdfContext(
                fileName: session.pdfName.isEmpty ? session.title : session.pdfName,
                textPreview: session.pdfPreview
            )
        documentNote = ""
        searchPhase = .idle
        posts = []
        isHistoryPresented = false
    }

    private func loadSessionBody(id: String, userId: Int) async -> AiChatSession? {
        if let local = AiChatSessionStore.shared.load(id) { return local }
        guard let remote = await AiChatBackend.syncDownload(sessionId: id, userId: userId) else { return nil }
        AiChatSessionStore.shared.save(remote)
        return remote
    }

    /// Ports `deleteHistorySession`.
    func deleteSession(_ meta: AiChatSessionMeta, userId: Int) async {
        AiChatSessionStore.shared.delete(meta.id)
        AiChatBackend.syncDelete(sessionId: meta.id, userId: userId)
        if sessionId == meta.id {
            sessionId = nil
            sessionCreatedAt = 0
            sessionTitleOverride = nil
        }
        await refreshSessions(userId: userId)
    }

    /// Ports `togglePinSession`.
    func togglePin(_ meta: AiChatSessionMeta, userId: Int) async {
        guard let session = await loadSessionBody(id: meta.id, userId: userId) else { return }
        var updated = session
        updated.pinned = !session.pinned
        updated.updatedAt = Date().timeIntervalSince1970 * 1000
        AiChatSessionStore.shared.save(updated)
        AiChatBackend.syncUpload(updated, userId: userId)
        await refreshSessions(userId: userId)
    }

    /// Ports `renameSession`.
    func renameSession(_ meta: AiChatSessionMeta, to newTitle: String, userId: Int) async {
        let trimmed = newTitle.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, let session = await loadSessionBody(id: meta.id, userId: userId) else { return }
        var updated = session
        updated.title = trimmed
        updated.updatedAt = Date().timeIntervalSince1970 * 1000
        AiChatSessionStore.shared.save(updated)
        AiChatBackend.syncUpload(updated, userId: userId)
        if sessionId == meta.id { sessionTitleOverride = trimmed }
        await refreshSessions(userId: userId)
    }

    /// Ports `refreshHistoryList` / `onHistory`.
    func refreshSessions(userId: Int) async {
        let local = AiChatSessionStore.shared.list()
        let remote = await AiChatBackend.syncSessionList(userId: userId)
        sessions = AiChatBackend.merge(local, remote)
    }

    /// Ports `buildTranscript` — plain-text conversation for share and export.
    func transcript(for meta: AiChatSessionMeta, userId: Int) async -> String {
        guard let session = await loadSessionBody(id: meta.id, userId: userId) else { return "" }
        var out = ""
        for turn in session.turns {
            out += turn.isUser ? "**You:** \(turn.content)" : "\n\n**Medigyaan AI:** \(turn.content)"
            out += "\n\n"
        }
        return out
    }

    /// Ports `startNewChat`.
    func startNewChat() {
        stopGenerating()
        messages = []
        sessionId = nil
        sessionCreatedAt = 0
        sessionTitleOverride = nil
        pdfContext = nil
        documentNote = ""
        attachment = nil
        attachedDocumentName = nil
        searchPhase = .idle
        posts = []
        enrichmentNote = ""
        streamingText = nil
        isHistoryPresented = false
        input = ""
        loadWelcomeMessage()
    }

    /// Ports `clearChat` from the overflow menu.
    func clearChat() {
        startNewChat()
    }

    // MARK: - Message actions

    /// Ports `copyAiText` — strips the bold markers before copying.
    func copyMessage(_ message: AiChatMessage) {
        UIPasteboard.general.string = message.text.replacingOccurrences(of: "**", with: "")
        showToast("Copied to clipboard 📋")
    }

    func toggleSpeech(for message: AiChatMessage) {
        if isSpeaking {
            stopSpeaking()
        } else {
            speak(text: message.text)
        }
    }

    private func speak(text: String) {
        stopSpeaking()
        let clean = text.replacingOccurrences(of: #"[#*`_]"#, with: "", options: .regularExpression)
        let utterance = AVSpeechUtterance(string: clean)
        utterance.voice = AVSpeechSynthesisVoice(language: "en-US")
        utterance.rate = AVSpeechUtteranceDefaultSpeechRate
        speechSynthesizer.speak(utterance)
        isSpeaking = true
    }

    func stopSpeaking() {
        if speechSynthesizer.isSpeaking {
            speechSynthesizer.stopSpeaking(at: .immediate)
        }
        isSpeaking = false
    }

    nonisolated func speechSynthesizer(_ synthesizer: AVSpeechSynthesizer, didFinish utterance: AVSpeechUtterance) {
        Task { @MainActor in
            self.isSpeaking = false
        }
    }

    func showToast(_ message: String) {
        withAnimation { toastMessage = message }
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
            withAnimation { self.toastMessage = nil }
        }
    }

    func present(error: Error) {
        errorMessage = LoadState<Never>.message(for: error)
    }

    var canSend: Bool {
        !input.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !isLoading
    }

    private func loadWelcomeMessage() {
        messages = [
            AiChatMessage(
                role: .assistant,
                text: "Hello! I am your **MediGyaan Medical AI Assistant**.\n\nYou can ask me clinical differentials, drug mechanisms, emergency protocols, NEET PG counselling, or attach case notes and PDFs for analysis. Tap any tool above to begin!"
            )
        ]
    }

    deinit {
        speechSynthesizer.stopSpeaking(at: .immediate)
    }
}
