import Foundation

/// A message in the medical AI chat thread.
/// Ports the multi-turn chat and related-question model from Android's `AiChatActivity.kt`.
struct AiChatMessage: Identifiable, Equatable {
    let id: UUID
    let role: MessageRole
    var text: String
    let timestamp: Date
    var attachmentName: String?
    var relatedQuestions: [Question]
    var isStreaming: Bool
    var responseTimeMs: Int?
    var feedback: Int // -1: dislike, 0: neutral, 1: like
    var counselCard: CounselCardData?
    var thesisCard: ThesisCardData?
    var chapterCard: ChapterCardData?
    var chapterDetails: ChatChapterJson?
    var citationCard: CitationValidationState?
    var posterCard: PosterGenState?
    var similarArticlesCard: SimilarArticlesState?
    var pdfAbstractsCard: PdfAbstractsState?
    var skillOutcome: SkillOutcome?
    var skillName: String?

    enum MessageRole: String, Codable {
        case user
        case assistant
        case system
    }

    init(
        id: UUID = UUID(),
        role: MessageRole,
        text: String,
        timestamp: Date = Date(),
        attachmentName: String? = nil,
        relatedQuestions: [Question] = [],
        isStreaming: Bool = false,
        responseTimeMs: Int? = nil,
        feedback: Int = 0,
        counselCard: CounselCardData? = nil,
        thesisCard: ThesisCardData? = nil,
        chapterCard: ChapterCardData? = nil,
        chapterDetails: ChatChapterJson? = nil,
        citationCard: CitationValidationState? = nil,
        posterCard: PosterGenState? = nil,
        similarArticlesCard: SimilarArticlesState? = nil,
        pdfAbstractsCard: PdfAbstractsState? = nil,
        skillOutcome: SkillOutcome? = nil,
        skillName: String? = nil
    ) {
        self.id = id
        self.role = role
        self.text = text
        self.timestamp = timestamp
        self.attachmentName = attachmentName
        self.relatedQuestions = relatedQuestions
        self.isStreaming = isStreaming
        self.responseTimeMs = responseTimeMs
        self.feedback = feedback
        self.counselCard = counselCard
        self.thesisCard = thesisCard
        self.chapterCard = chapterCard
        self.chapterDetails = chapterDetails
        self.citationCard = citationCard
        self.posterCard = posterCard
        self.similarArticlesCard = similarArticlesCard
        self.pdfAbstractsCard = pdfAbstractsCard
        self.skillOutcome = skillOutcome
        self.skillName = skillName
    }

    var isUser: Bool { role == .user }
}

/// Medical clinical prompt suggestions for quick one-tap inquiries.
struct AiPromptSuggestion: Identifiable, Hashable {
    let id = UUID()
    let icon: String
    let title: String
    let prompt: String
}

// MARK: - NEET PG AI Counselor Card Data

struct CounselCollege: Identifiable, Equatable, Hashable {
    let id = UUID()
    let institute: String
    let course: String
    let closingRank: String
    let category: String
    let quota: String
    let state: String
    let feePerYear: String
    let stipendYear1: String
    let bondYears: String
    let chance: String // "Dream", "Target", "Safe"
}

struct CounselCardData: Equatable {
    var query: String
    var summary: String
    var results: [CounselCollege]
    var error: String = ""
    var isExpanded: Bool = true
}

// MARK: - Thesis Topic Card Data

struct ThesisTopicResult: Identifiable, Equatable, Hashable {
    let id: Int
    let subject: String
    let snippet: String
    let displayTitle: String
    let studyType: String
    let difficulty: String
}

struct ThesisCardData: Equatable {
    var query: String
    var results: [ThesisTopicResult]
    var isExpanded: Bool = true
}

// MARK: - Chapter Generator Card Data

struct ChapterCardData: Equatable {
    var chapterName: String
    var sections: [String]
    var isExpanded: Bool = true
}

// MARK: - Export Formats

public enum AiExportFormat: String, CaseIterable, Identifiable {
    case pdf = "pdf"
    case docx = "docx"
    case pptx = "pptx"

    public var id: String { rawValue }

    public var label: String {
        switch self {
        case .pdf: return "PDF"
        case .docx: return "Word"
        case .pptx: return "PowerPoint"
        }
    }

    public var mimeType: String {
        switch self {
        case .pdf: return "application/pdf"
        case .docx: return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        case .pptx: return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        }
    }

    public var fileExtension: String {
        rawValue
    }
}

// MARK: - PubMed Citation Validation

struct PubMedCitationEntry: Identifiable, Equatable, Hashable {
    var id: String { text }
    var text: String
    var startsWithNumber: Bool = false
}

struct PubMedValidationResult: Identifiable, Equatable, Hashable {
    var id: String { "\(index)-\(pmid)-\(originalText)" }
    var index: Int
    var originalText: String
    var found: Bool
    var pmid: String = ""
    var doi: String? = nil
    var articleTitle: String = ""
    var canonicalReference: String = ""
}

struct CitationValidationState: Equatable {
    var ownerTurn: Int = -1
    var detected: [PubMedCitationEntry] = []
    var intentRequested: Bool = false
    var running: Bool = false
    var note: String = ""
    var current: Int = 0
    var total: Int = 0
    var results: [PubMedValidationResult]? = nil
}

// MARK: - Poster Generation

struct PosterGenState: Equatable {
    var ownerTurn: Int = -1
    var source: String = ""
    var phase: Int = 0 // 1: analyzing, 2: rendering, 3: done, 4: error
    var note: String = ""
    var data: PosterAnalysisData? = nil
    var imageUrl: String? = nil
    var imageFile: String? = nil
    var error: String = ""
}

// MARK: - Chapter Generator Structured Schema

struct ChatChapterJson: Codable, Equatable {
    var chapterName: String = ""
    var chapterType: String = ""
    var sections: [ChatSectionJson] = []
    var tables: [ChatTableJson] = []
    var figures: [ChatFigureJson] = []
    var charts: [ChatChartJson] = []
    var abbreviations: [ChatAbbreviationJson] = []
    var references: [ChatReferenceJson] = []
}

struct ChatSectionJson: Codable, Equatable, Identifiable {
    var id: String { heading + (paragraphs.first ?? "") }
    var heading: String = ""
    var content: String = ""
    var paragraphs: [String] = []
    var bullets: [String] = []
    var numberedPoints: [String] = []
    var subsections: [ChatSubsectionJson] = []
    var table: ChatTableJson? = nil
    var figures: [ChatFigureJson] = []
    var references: [ChatReferenceJson] = []
}

struct ChatSubsectionJson: Codable, Equatable, Identifiable {
    var id: String { heading + (paragraphs.first ?? "") }
    var heading: String = ""
    var content: String = ""
    var paragraphs: [String] = []
}

struct ChatTableJson: Codable, Equatable, Identifiable {
    var id: String { tableNumber + title }
    var tableNumber: String = ""
    var title: String = ""
    var headers: [String] = []
    var rows: [[String]] = []
    var footnote: String = ""
}

struct ChatFigureJson: Codable, Equatable, Identifiable {
    var id: String { figureNumber + title }
    var figureNumber: String = ""
    var title: String = ""
    var caption: String = ""
    var imageSearchQuery: String = ""
}

struct ChatChartPointJson: Codable, Equatable, Identifiable {
    var id: String { label }
    var label: String = ""
    var value: Double = 0.0
}

struct ChatChartJson: Codable, Equatable, Identifiable {
    var id: String { chartId.isEmpty ? title : chartId }
    var chartId: String = ""
    var title: String = ""
    var type: String = "" // bar | line | pie | column | doughnut
    var labels: [String] = []
    var values: [Double] = []
    var data: [ChatChartPointJson] = []
}

struct ChatAbbreviationJson: Codable, Equatable, Identifiable {
    var id: String { short }
    var short: String = ""
    var full: String = ""
}

struct ChatReferenceJson: Codable, Equatable, Identifiable {
    var id: String { pmid.isEmpty ? citation : pmid }
    var citation: String = ""
    var referenceText: String = ""
    var pmid: String = ""
    var doi: String = ""
}

// MARK: - PDF Abstracts & Discovery

struct PdfAbstractSectionJson: Codable, Equatable, Identifiable, Hashable {
    var id: String { label }
    var label: String = ""
    var text: String = ""
}

struct PdfAbstractEntry: Identifiable, Equatable, Hashable {
    var id: String { pmid.isEmpty ? title : pmid }
    var pmid: String = ""
    var doi: String = ""
    var citationLabel: String = ""
    var title: String = ""
    var citation: String = ""
    var text: String = ""
    var compactedText: String = ""
    var sections: [PdfAbstractSectionJson] = []
    var sourceType: String = "validated_reference"
    var parentPmid: String = ""
    var parentCitation: String = ""
}

struct PdfAbstractsState: Equatable {
    var running: Bool = false
    var phase: Int = 0 // 1: Reading PDF, 2: Extracting Vars, 3: Extracting Refs, 4: Verifying, 5: Downloading, 6: Similar, 7: Compacting, 8: Ready
    var progressCurrent: Int = 0
    var progressTotal: Int = 0
    var note: String = ""
    var currentCitation: String = ""
    var verifiedCitationsPreview: [String] = []
    var extractedVarCount: Int = 0
    var fromCache: Bool = false
    var entries: [PdfAbstractEntry] = []
}

struct SimilarArticlesState: Equatable {
    var ownerTurn: Int = -1
    var running: Bool = false
    var phase: Int = 0 // 1 finding, 2 downloading, 3 merging, 4 ready
    var note: String = ""
    var entries: [PdfAbstractEntry] = []
}


