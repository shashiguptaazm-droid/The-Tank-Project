package com.rankwarz.edulabsrtm.utils

data class WorkspaceState(
    val researchQuestion: String = "",
    val pico: PicoData = PicoData(),
    val objectives: List<String> = emptyList(),
    val hypothesis: String = "",
    val studyType: String = "",
    val literatureResults: List<ResearchPaper> = emptyList(),
    val validatedCitations: List<String> = emptyList(),
    val dataset: Map<String, String> = emptyMap(),
    val auditScore: Int = 0,
    val currentSection: String = "Dashboard"
)

data class PicoData(
    val population: String = "",
    val intervention: String = "" ,
    val comparison: String = "",
    val outcome: String = ""
)

data class ResearchPaper(
    val title: String,
    val authors: String,
    val pmid: String,
    val relevance: Int,
    val evidenceLevel: String
)
