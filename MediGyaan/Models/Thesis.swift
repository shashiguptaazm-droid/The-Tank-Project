import Foundation

/// A thesis workspace session (`thesis_session_backend.php`).
///
/// Ports the data the Android `ThesisModels.kt` / `ThesisSharedState.kt` pair
/// kept in memory and in `SharedPreferences`.
struct ThesisSession: Decodable, Identifiable, Hashable {
    let id: String
    let userId: Int
    let title: String
    let topic: String
    let speciality: String
    let studyType: String
    let createdAt: Date
    let updatedAt: Date
    let chapters: [ThesisChapter]

    var completedChapters: Int {
        chapters.filter(\.isComplete).count
    }

    var progress: Double {
        guard !chapters.isEmpty else { return 0 }
        return Double(completedChapters) / Double(chapters.count)
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.flexibleContainer()
        let rawId = container.flexString("session_id", "id")
        id = rawId.isEmpty ? UUID().uuidString : rawId
        userId = container.flexInt("user_id", "userId")
        title = container.flexString("title", "thesis_title", "name")
        topic = container.flexString("topic", "research_topic")
        speciality = container.flexString("speciality", "specialty", "department")
        studyType = container.flexString("study_type", "design")
        createdAt = DateFormatter.backend.date(from: container.flexString("created_at")) ?? Date()
        updatedAt = DateFormatter.backend.date(from: container.flexString("updated_at")) ?? Date()
        chapters = container.flexArray("chapters", "sections")
    }

    init(
        id: String = UUID().uuidString,
        userId: Int,
        title: String,
        topic: String = "",
        speciality: String = "",
        studyType: String = "",
        createdAt: Date = Date(),
        updatedAt: Date = Date(),
        chapters: [ThesisChapter] = []
    ) {
        self.id = id
        self.userId = userId
        self.title = title
        self.topic = topic
        self.speciality = speciality
        self.studyType = studyType
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.chapters = chapters
    }
}

/// One chapter of a thesis.
struct ThesisChapter: Decodable, Identifiable, Hashable {
    let id: String
    let index: Int
    let title: String
    let content: String
    let wordCount: Int
    let isComplete: Bool
    let updatedAt: Date

    init(from decoder: Decoder) throws {
        let container = try decoder.flexibleContainer()
        let rawId = container.flexString("chapter_id", "id")
        title = container.flexString("title", "chapter_title", "name")
        id = rawId.isEmpty ? title : rawId
        index = container.flexInt("chapter_no", "index", "order", "chapter_index")
        content = container.flexString("content", "body", "text")
        wordCount = container.flexInt("word_count", "words")
        isComplete = container.flexBool("complete", "is_complete", "done")
        updatedAt = DateFormatter.backend.date(from: container.flexString("updated_at")) ?? Date()
    }

    init(
        id: String = UUID().uuidString,
        index: Int,
        title: String,
        content: String = "",
        wordCount: Int = 0,
        isComplete: Bool = false,
        updatedAt: Date = Date()
    ) {
        self.id = id
        self.index = index
        self.title = title
        self.content = content
        self.wordCount = wordCount
        self.isComplete = isComplete
        self.updatedAt = updatedAt
    }

    /// Chapters the backend is known to generate, in order.
    static let defaultTitles = [
        "Introduction",
        "Aim and Objectives",
        "Review of Literature",
        "Materials and Methods",
        "Results",
        "Discussion",
        "Conclusion",
        "Summary",
        "References",
        "Annexures",
    ]
}

/// A bibliographic reference from `reference_cache_backend.php`.
struct ThesisReference: Decodable, Identifiable, Hashable {
    let id: String
    let title: String
    let authors: String
    let journal: String
    let year: String
    let doi: String
    let pubmedId: String
    let abstract: String
    let url: URL?

    /// Vancouver-style citation preview, matching the Android exporter.
    var citation: String {
        var parts: [String] = []
        if !authors.isEmpty { parts.append(authors) }
        if !title.isEmpty { parts.append(title) }
        var tail: [String] = []
        if !journal.isEmpty { tail.append(journal) }
        if !year.isEmpty { tail.append(year) }
        if !tail.isEmpty { parts.append(tail.joined(separator: ". ")) }
        if !doi.isEmpty { parts.append("doi:\(doi)") }
        return parts.joined(separator: ". ") + "."
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.flexibleContainer()
        let rawId = container.flexString("reference_id", "pmid", "id")
        title = container.flexString("title", "article_title")
        id = rawId.isEmpty ? title : rawId
        authors = container.flexString("authors", "author", "author_list")
        journal = container.flexString("journal", "source", "publication")
        year = container.flexString("year", "published_year", "pub_year")
        doi = container.flexString("doi")
        pubmedId = container.flexString("pmid", "pubmed_id")
        abstract = container.flexString("abstract", "summary")
        let link = container.flexString("url", "link")
        url = link.isEmpty ? nil : URL(string: link)
    }

    init(
        id: String,
        title: String,
        authors: String = "",
        journal: String = "",
        year: String = "",
        doi: String = "",
        pubmedId: String = "",
        abstract: String = "",
        url: URL? = nil
    ) {
        self.id = id
        self.title = title
        self.authors = authors
        self.journal = journal
        self.year = year
        self.doi = doi
        self.pubmedId = pubmedId
        self.abstract = abstract
        self.url = url
    }
}

/// PRISMA flow-diagram counts used by `thesis_prisma.php`.
struct PrismaCounts: Codable, Hashable {
    var identified: Int
    var screened: Int
    var eligible: Int
    var included: Int
    var excluded: Int

    static let empty = PrismaCounts(identified: 0, screened: 0, eligible: 0, included: 0, excluded: 0)
}

/// A checklist row from `thesis_checklist.php`.
struct ThesisChecklistItem: Decodable, Identifiable, Hashable {
    let id: String
    let title: String
    let isDone: Bool
    let chapterIndex: Int

    init(from decoder: Decoder) throws {
        let container = try decoder.flexibleContainer()
        let rawId = container.flexString("id", "item_id")
        title = container.flexString("title", "item", "text", "label")
        id = rawId.isEmpty ? title : rawId
        isDone = container.flexBool("done", "is_done", "complete", "checked")
        chapterIndex = container.flexInt("chapter_no", "chapter_index", "index")
    }
}
