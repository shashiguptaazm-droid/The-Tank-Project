import Foundation

/// Medical & Research Skill model strictly conforming to Android's `ResearchSkillRegistry.kt`.
public struct ResearchSkill: Identifiable, Hashable {
    public let id: Int
    public let name: String
    public let description: String
    public let category: String
    public let isDeterministic: Bool

    public init(id: Int, name: String, description: String, category: String, isDeterministic: Bool = false) {
        self.id = id
        self.name = name
        self.description = description
        self.category = category
        self.isDeterministic = isDeterministic
    }
}

/// Registry of 125+ specialized AI & clinical reasoning skills from `ResearchSkillRegistry.kt`.
public enum ResearchSkillRegistry {

    public static let skills: [ResearchSkill] = [
        // 🔎 Research & Question Skills (1-10)
        ResearchSkill(id: 1, name: "Research Question Analyzer", description: "Understands the user's research question.", category: "Research"),
        ResearchSkill(id: 2, name: "PICO/PECO Extractor", description: "Extracts Population, Intervention/Exposure, Comparison and Outcome.", category: "Research"),
        ResearchSkill(id: 3, name: "Research Type Classifier", description: "Identifies RCT, cohort, case-control, systematic review, thesis, etc.", category: "Research"),
        ResearchSkill(id: 4, name: "Objective Generator", description: "Creates primary and secondary objectives.", category: "Research"),
        ResearchSkill(id: 5, name: "Hypothesis Generator", description: "Generates null/alternative hypotheses.", category: "Research"),
        ResearchSkill(id: 6, name: "Variable Extractor", description: "Identifies independent, dependent and confounding variables.", category: "Research"),
        ResearchSkill(id: 7, name: "Outcome Definition", description: "Converts outcomes into measurable endpoints.", category: "Research"),
        ResearchSkill(id: 8, name: "Eligibility Criteria Builder", description: "Creates inclusion/exclusion criteria.", category: "Research"),
        ResearchSkill(id: 9, name: "Study Design Advisor", description: "Suggests appropriate study design.", category: "Research"),
        ResearchSkill(id: 10, name: "Research Gap Finder", description: "Finds unanswered questions in existing literature.", category: "Research"),

        // 📚 Literature Search Skills (11-20)
        ResearchSkill(id: 11, name: "PubMed Search Builder", description: "Creates optimized PubMed/MeSH/Boolean queries.", category: "Search"),
        ResearchSkill(id: 12, name: "PubMed Search", description: "Retrieves relevant publications.", category: "Search", isDeterministic: true),
        ResearchSkill(id: 13, name: "MeSH Mapper", description: "Maps medical concepts to MeSH terms.", category: "Search"),
        ResearchSkill(id: 14, name: "Synonym Generator", description: "Expands terminology and abbreviations.", category: "Search"),
        ResearchSkill(id: 15, name: "Article Deduplicator", description: "Removes duplicate papers.", category: "Search", isDeterministic: true),
        ResearchSkill(id: 16, name: "Article Relevance Ranker", description: "Scores papers against the research question.", category: "Search"),
        ResearchSkill(id: 17, name: "Citation Chaining", description: "Finds references and citing papers.", category: "Search"),
        ResearchSkill(id: 18, name: "Similar Article Finder", description: "Finds related research.", category: "Search", isDeterministic: true),
        ResearchSkill(id: 19, name: "Full-Text Retriever", description: "Retrieves available article content.", category: "Search", isDeterministic: true),
        ResearchSkill(id: 20, name: "Literature Timeline", description: "Organizes research chronologically.", category: "Search"),

        // ✅ Validation Skills (21-30) - Deterministic
        ResearchSkill(id: 21, name: "PMID Validator", description: "Confirms PMID and article identity.", category: "Validation", isDeterministic: true),
        ResearchSkill(id: 22, name: "DOI Validator", description: "Verifies DOI and metadata.", category: "Validation", isDeterministic: true),
        ResearchSkill(id: 23, name: "Citation Validator", description: "Checks authors, title, journal, year, pages, etc.", category: "Validation", isDeterministic: true),
        ResearchSkill(id: 24, name: "Vancouver Formatter", description: "Generates validated Vancouver references.", category: "Validation", isDeterministic: true),
        ResearchSkill(id: 25, name: "Reference Consistency Checker", description: "Checks in-text citations vs bibliography.", category: "Validation", isDeterministic: true),
        ResearchSkill(id: 26, name: "Source Provenance Tracker", description: "Records where every claim came from.", category: "Validation", isDeterministic: true),
        ResearchSkill(id: 27, name: "Evidence Extractor", description: "Extracts evidence supporting claims.", category: "Validation", isDeterministic: true),
        ResearchSkill(id: 28, name: "Claim Verification", description: "Checks claim ↔ source correspondence.", category: "Validation", isDeterministic: true),
        ResearchSkill(id: 29, name: "Evidence-Level Classifier", description: "Classifies strength/type of evidence.", category: "Validation", isDeterministic: true),
        ResearchSkill(id: 30, name: "Conflicting Evidence Detector", description: "Finds contradictory study results.", category: "Validation", isDeterministic: true),

        // 🧬 Medical Data Skills (31-40)
        ResearchSkill(id: 31, name: "Medical Entity Extractor", description: "Extracts diseases, drugs, anatomy, procedures, etc.", category: "Data"),
        ResearchSkill(id: 32, name: "Clinical Fact Extractor", description: "Extracts symptoms, signs, diagnosis and treatment facts.", category: "Data"),
        ResearchSkill(id: 33, name: "Study Metadata Extractor", description: "Extracts design, sample size, population, duration, location.", category: "Data"),
        ResearchSkill(id: 34, name: "Numerical Data Extractor", description: "Extracts OR, RR, HR, CI, p-values, means, percentages.", category: "Data"),
        ResearchSkill(id: 35, name: "Table Extraction", description: "Converts research tables into structured data.", category: "Data"),
        ResearchSkill(id: 36, name: "Outcome Extractor", description: "Identifies primary and secondary outcomes.", category: "Data"),
        ResearchSkill(id: 37, name: "Intervention Extractor", description: "Extracts treatments, doses and protocols.", category: "Data"),
        ResearchSkill(id: 38, name: "Adverse Event Extractor", description: "Extracts complications and adverse effects.", category: "Data"),
        ResearchSkill(id: 39, name: "Study Quality Analyzer", description: "Assesses methodological quality/risk-of-bias information.", category: "Data"),
        ResearchSkill(id: 40, name: "Evidence Dataset Builder", description: "Converts extracted information into research dataset schema.", category: "Data"),

        // 🧠 Analysis & Research Generation (41-50)
        ResearchSkill(id: 41, name: "Evidence Synthesizer", description: "Combines findings from multiple studies.", category: "Generation"),
        ResearchSkill(id: 42, name: "Study Comparison Engine", description: "Compares studies side-by-side.", category: "Generation"),
        ResearchSkill(id: 43, name: "Statistical Analysis Planner", description: "Selects appropriate statistical approaches.", category: "Generation"),
        ResearchSkill(id: 44, name: "Statistical Calculator", description: "Performs validated statistical calculations.", category: "Generation", isDeterministic: true),
        ResearchSkill(id: 45, name: "Bias & Confounder Detector", description: "Identifies methodological problems.", category: "Generation"),
        ResearchSkill(id: 46, name: "Thesis Writer", description: "Generates structured thesis sections from verified evidence.", category: "Generation"),
        ResearchSkill(id: 47, name: "Discussion Generator", description: "Compares findings with previous literature.", category: "Generation"),
        ResearchSkill(id: 48, name: "Abstract Generator", description: "Creates structured research abstracts.", category: "Generation"),
        ResearchSkill(id: 49, name: "Future Research Generator", description: "Identifies unanswered questions and future studies.", category: "Generation"),
        ResearchSkill(id: 50, name: "Final Research Auditor", description: "Checks every claim, citation, number and reference before the final answer.", category: "Generation", isDeterministic: true),

        // 🎓 Medical Education & Clinical Reasoning (51-70)
        ResearchSkill(id: 51, name: "Case Study Generator", description: "Creates realistic patient scenarios for clinical reasoning practice.", category: "Education"),
        ResearchSkill(id: 52, name: "Differential Diagnosis Builder", description: "Guides students from symptoms to a prioritized list of diagnoses.", category: "Education"),
        ResearchSkill(id: 53, name: "Medical Mnemonic Creator", description: "Generates high-retention memory aids for complex medical facts.", category: "Education"),
        ResearchSkill(id: 54, name: "Socratic Medical Tutor", description: "Interactive tutoring that guides students via questioning.", category: "Education"),
        ResearchSkill(id: 55, name: "Guideline Distiller", description: "Summarizes official clinical guidelines (AHA, GOLD, etc.) for quick review.", category: "Education"),
        ResearchSkill(id: 61, name: "Pharmacology Mechanism Mapper", description: "Explains drug mechanisms of action and pathopharmacology.", category: "Clinical"),
        ResearchSkill(id: 62, name: "Lab Value Interpreter", description: "Analyzes abnormal lab results and suggests underlying causes.", category: "Clinical"),
        ResearchSkill(id: 66, name: "Drug Interaction Checker", description: "Analyzes potential interactions between multiple medications.", category: "Clinical"),
        ResearchSkill(id: 68, name: "Emergency Protocol Guide", description: "Walks through ACLS, BLS, and trauma primary surveys.", category: "Clinical"),
        ResearchSkill(id: 69, name: "Pediatric Dose Calculator", description: "Educational tool for learning weight-based dosing logic.", category: "Clinical", isDeterministic: true),

        // 💻 Advanced Solvers & Coding Tools (170-197)
        ResearchSkill(id: 121, name: "ABG Solver", description: "Arterial blood gas acid-base analysis and compensation logic.", category: "Clinical", isDeterministic: true),
        ResearchSkill(id: 171, name: "IRB Ethics Validator", description: "Validates research protocol against ethical guidelines.", category: "Validation"),
        ResearchSkill(id: 172, name: "Sample Size Calculator", description: "Calculates sample size with 80% power, 5% alpha, and attrition buffers.", category: "Generation", isDeterministic: true),
        ResearchSkill(id: 179, name: "Diff Viewer", description: "Generates clean unified diff blocks for protocol changes.", category: "Coding", isDeterministic: true),
        ResearchSkill(id: 181, name: "Autonomous Coding Agent", description: "Generates production data analysis and parsing scripts.", category: "Coding"),
        ResearchSkill(id: 197, name: "Poster Generator", description: "Generates structured research poster content from abstract.", category: "Generation")
    ]

    public static func getSkillByName(_ name: String) -> ResearchSkill? {
        skills.first { $0.name.caseInsensitiveCompare(name) == .orderedSame }
    }

    public static func getSkillById(_ id: Int) -> ResearchSkill? {
        skills.first { $0.id == id }
    }

    public static var systemPromptExtension: String {
        """
        You are MediGyaan Research OS & AI Medical Specialist.
        WORKSPACE MANAGEMENT: To update the user's research workspace, append markers to your reply:
        • [RESEARCH_QUESTION: text] - Updates research question.
        • [PICO: P=..., I=..., C=..., O=...] - Updates PICO components.
        • [SECTION: Name] - Switches active section (Literature, Evidence, Audit, Methodology).
        • [SEARCH: keyword] - Searches the 280k MediGyaan question bank for practice questions.
        """
    }
}
