import Foundation

/// PICO clinical research framework data.
public struct PicoData: Codable, Hashable {
    public var population: String
    public var intervention: String
    public var comparison: String
    public var outcome: String

    public init(
        population: String = "",
        intervention: String = "",
        comparison: String = "",
        outcome: String = ""
    ) {
        self.population = population
        self.intervention = intervention
        self.comparison = comparison
        self.outcome = outcome
    }
}

/// A scientific literature paper candidate discovered during research workspace discovery.
public struct ResearchPaperItem: Identifiable, Codable, Hashable {
    public var id: String { pmid.isEmpty ? title : pmid }
    public let title: String
    public let authors: String
    public let pmid: String
    public let relevance: Int
    public let evidenceLevel: String

    public init(
        title: String = "",
        authors: String = "",
        pmid: String = "",
        relevance: Int = 0,
        evidenceLevel: String = "Level II"
    ) {
        self.title = title
        self.authors = authors
        self.pmid = pmid
        self.relevance = relevance
        self.evidenceLevel = evidenceLevel
    }
}

/// Dynamic medical research workspace state.
/// 1:1 port of Android `WorkspaceModels.kt` and `ResearchSharedState.kt`.
public struct WorkspaceState: Codable, Hashable {
    public var researchQuestion: String
    public var pico: PicoData
    public var objectives: [String]
    public var hypothesis: String
    public var studyType: String
    public var literatureResults: [ResearchPaperItem]
    public var validatedCitations: [String]
    public var dataset: [String: String]
    public var auditScore: Int
    public var currentSection: String

    public init(
        researchQuestion: String = "",
        pico: PicoData = PicoData(),
        objectives: [String] = [],
        hypothesis: String = "",
        studyType: String = "",
        literatureResults: [ResearchPaperItem] = [],
        validatedCitations: [String] = [],
        dataset: [String: String] = [:],
        auditScore: Int = 0,
        currentSection: String = "Dashboard"
    ) {
        self.researchQuestion = researchQuestion
        self.pico = pico
        self.objectives = objectives
        self.hypothesis = hypothesis
        self.studyType = studyType
        self.literatureResults = literatureResults
        self.validatedCitations = validatedCitations
        self.dataset = dataset
        self.auditScore = auditScore
        self.currentSection = currentSection
    }
}
