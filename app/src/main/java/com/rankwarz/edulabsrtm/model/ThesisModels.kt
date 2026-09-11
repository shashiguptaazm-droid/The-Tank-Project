package com.rankwarz.edulabsrtm.model

import com.google.firebase.database.PropertyName
import com.google.gson.annotations.SerializedName

// ==============================
// Firebase‑stored models (must have default values for all properties)
// ==============================

data class AuditEntry(
    var timestamp: Long = System.currentTimeMillis(),
    var action: String = "",
    var provider: String = "",
    var model: String = "",
    var notes: String = ""
)

data class ThesisAiLogEntry(
    var id: String = "",
    var timestamp: Long = System.currentTimeMillis(),
    var phase: String = "",
    var chapterName: String = "",
    var provider: String = "",
    var model: String = "",
    var status: String = "",
    var prompt: String = "",
    var response: String = "",
    var error: String = "",
    var durationMs: Long = 0L,
    var promptChars: Int = 0,
    var responseChars: Int = 0
)

data class Chapter(
    var name: String = "",
    var content: String = "",
    var id: Int = 0,
    var status: ChapterStatus = ChapterStatus.IDLE,
    var errorMessage: String? = null,
    var tables: List<ThesisTableJson> = emptyList(),
    var rawJson: String = "",
    var figures: List<FigureJson> = emptyList(),
    var charts: List<ChartJson> = emptyList(),
    var abbreviations: List<AbbreviationJson> = emptyList(),
    var chapterReferences: List<ReferenceJson> = emptyList(),
    var textBoxes: List<ChapterTextBoxJson> = emptyList(),
    var sections: List<ThesisSectionJson> = emptyList(),
    var syncEnabled: Boolean = false,
    var workerStatus: String = "",
    var retryCount: Int = 0,
    var lastRetryAt: Long = 0L,
    var lastWorkerError: String = "",
    var lockedBy: String = "",
    var lockedUntil: Long = 0L,
    var workerPrompt: String = "",
    var workerPromptUpdatedAt: Long = 0L,
    var syncedAt: Long = 0L,
    var completedByProvider: String = "",
    var completedByModel: String = "",
    var completedByLabel: String = "",
    var auditTrail: List<AuditEntry> = emptyList()
) {
    enum class ChapterStatus {
        IDLE, LOADING, SUCCESS, PENDING, ERROR
    }
}

data class ChartJson(
    @get:PropertyName("chart_id") @set:PropertyName("chart_id") @SerializedName("chart_id") var chartId: String = "",
    @SerializedName("title") var title: String = "",
    @SerializedName("type") var type: String = "",
    @get:PropertyName("chart_template") @set:PropertyName("chart_template") @SerializedName("chart_template") var chartTemplate: String = "",
    @get:PropertyName("x_axis_label") @set:PropertyName("x_axis_label") @SerializedName("x_axis_label") var xAxisLabel: String? = null,
    @get:PropertyName("y_axis_label") @set:PropertyName("y_axis_label") @SerializedName("y_axis_label") var yAxisLabel: String? = null,
    @SerializedName("labels") var labels: List<String> = emptyList(),
    @SerializedName("values") var values: List<Double> = emptyList(),
    @SerializedName("data") var data: Any? = null,
    @SerializedName("datasets") var datasets: List<ChartDatasetJson> = emptyList(),
    @SerializedName("options") var options: Map<String, Any>? = null
)

data class ChartDatasetJson(
    @SerializedName("label") var label: String = "",
    @SerializedName("values") var values: List<Double> = emptyList(),
    @SerializedName("labels") var labels: List<String> = emptyList(),
    @SerializedName("color") var color: String? = null
)

data class FigureJson(
    @get:PropertyName("figure_number") @set:PropertyName("figure_number") @SerializedName("figure_number") var figureNumber: String = "",
    @SerializedName("title") var title: String = "",
    @SerializedName("caption") var caption: String = "",
    @get:PropertyName("image_search_query") @set:PropertyName("image_search_query") @SerializedName("image_search_query") var imageSearchQuery: String = "",
    @get:PropertyName("image_url") @set:PropertyName("image_url") @SerializedName("image_url") var imageUrl: String = "",
    @get:PropertyName("source_url") @set:PropertyName("source_url") @SerializedName("source_url") var sourceUrl: String = ""
)

data class PubMedFigureJson(
    @SerializedName("pmid") var pmid: String = "",
    @get:PropertyName("pmc_id") @set:PropertyName("pmc_id") @SerializedName("pmc_id") var pmcId: String = "",
    @get:PropertyName("figure_id") @set:PropertyName("figure_id") @SerializedName("figure_id") var figureId: String = "",
    @SerializedName("title") var title: String = "",
    @SerializedName("caption") var caption: String = "",
    @get:PropertyName("image_url") @set:PropertyName("image_url") @SerializedName("image_url") var imageUrl: String = "",
    @get:PropertyName("thumbnail_url") @set:PropertyName("thumbnail_url") @SerializedName("thumbnail_url") var thumbnailUrl: String = "",
    @get:PropertyName("local_uri") @set:PropertyName("local_uri") @SerializedName("local_uri") var localUri: String = "",
    @get:PropertyName("article_url") @set:PropertyName("article_url") @SerializedName("article_url") var articleUrl: String = ""
)

data class PubMedCitedByArticleJson(
    @SerializedName("pmid") var pmid: String = "",
    @SerializedName("doi") var doi: String? = null,
    @SerializedName("title") var title: String = "",
    @SerializedName("citation") var citation: String = "",
    @get:PropertyName("abstract_text") @set:PropertyName("abstract_text") @SerializedName(value = "abstract_text", alternate = ["abstractText"]) var abstractText: String = "",
    @get:PropertyName("abstract_sections") @set:PropertyName("abstract_sections") @SerializedName(value = "abstract_sections", alternate = ["abstractSections"]) var abstractSections: List<PubMedAbstractSectionJson> = emptyList(),
    @get:PropertyName("article_url") @set:PropertyName("article_url") @SerializedName(value = "article_url", alternate = ["articleUrl"]) var articleUrl: String = ""
)

data class PubMedAbstractSectionJson(
    @SerializedName("label") var label: String = "",
    @SerializedName("category") var category: String = "",
    @SerializedName("text") var text: String = ""
)

data class PubMedAbstractSourceJson(
    @SerializedName("pmid") var pmid: String = "",
    @SerializedName("doi") var doi: String? = null,
    @SerializedName("title") var title: String = "",
    @SerializedName("citation") var citation: String = "",
    @get:PropertyName("abstract_text") @set:PropertyName("abstract_text") @SerializedName(value = "abstract_text", alternate = ["abstractText"]) var abstractText: String = "",
    @get:PropertyName("abstract_sections") @set:PropertyName("abstract_sections") @SerializedName(value = "abstract_sections", alternate = ["abstractSections"]) var abstractSections: List<PubMedAbstractSectionJson> = emptyList(),
    @get:PropertyName("cited_by") @set:PropertyName("cited_by") @SerializedName(value = "cited_by", alternate = ["citedBy"]) var citedBy: List<PubMedCitedByArticleJson> = emptyList(),
    @get:PropertyName("similar_articles") @set:PropertyName("similar_articles") @SerializedName(value = "similar_articles", alternate = ["similarArticles"]) var similarArticles: List<PubMedCitedByArticleJson> = emptyList()
)

data class AbbreviationJson(
    @get:PropertyName("short_form") @set:PropertyName("short_form") @SerializedName("short_form") var shortForm: String = "",
    @get:PropertyName("full_form") @set:PropertyName("full_form") @SerializedName("full_form") var fullForm: String = ""
)

data class ReferenceJson(
    @SerializedName("citation") var citation: String = "",
    @get:PropertyName("reference_text") @set:PropertyName("reference_text") @SerializedName(value = "reference_text", alternate = ["text", "citation_text", "vancouver_text"]) var referenceText: String = "",
    @SerializedName(value = "pmid", alternate = ["PMID"]) var pmid: String? = null,
    @SerializedName(value = "doi", alternate = ["DOI"]) var doi: String? = null,
    @get:PropertyName("pubmed_verified") @set:PropertyName("pubmed_verified") @SerializedName(value = "pubmed_verified", alternate = ["pubMedVerified", "verified"]) var pubmedVerified: Boolean = false,
    var authors: List<String> = emptyList(),
    var title: String = "",
    var journal: String = "",
    var year: Int = 0,
    var volume: String = "",
    var pages: String = ""
)

data class ChapterTextBoxJson(
    @SerializedName("id") var id: String = "",
    @SerializedName("text") var text: String = "",
    @SerializedName("x") var x: Float = 0.08f,
    @SerializedName("y") var y: Float = 0.08f,
    @SerializedName("width") var width: Float = 0.84f,
    @SerializedName("height") var height: Float = 0.14f
)

data class ThesisTableJson(
    @get:PropertyName("table_number") @set:PropertyName("table_number") @SerializedName("table_number") var tableNumber: String = "",
    @SerializedName("title") var title: String = "",
    @SerializedName("headers") var headers: List<String> = emptyList(),
    @SerializedName("rows") var rows: List<List<String>> = emptyList(),
    @SerializedName("data") var data: List<Map<String, Any?>> = emptyList(),
    @SerializedName("footnote") var footnote: String? = null
)

data class MasterChartColumnJson(
    var columnName: String = "",
    var displayName: String = "",
    var dataType: String = "text",
    var allowedValues: String = "",
    var role: String = "study_variable",
    var source: String = "",
    var suggestedAnalysis: String = "",
    var notes: String = ""
)

data class MasterChartColumnMappingJson(
    var sourceHeader: String = "",
    var targetColumn: String = "",
    var confidence: Double = 0.0,
    var status: String = "mapped"
)

data class MasterChartValidationIssueJson(
    var rowNumber: Int = 0,
    var columnName: String = "",
    var value: String = "",
    var issue: String = "",
    var severity: String = "warning"
)

data class MasterChartResultSummaryJson(
    var title: String = "",
    var type: String = "frequency",
    var headers: List<String> = emptyList(),
    var rows: List<List<String>> = emptyList()
)

data class ThesisSessionPayload(
    var sessionId: String = "",
    var thesisTitle: String = "",
    var updatedAt: Long = System.currentTimeMillis(),
    var status: String = "IDLE",
    var currentChapter: Int = 0,
    var totalChapters: Int = 0,
    var completionPercent: Int = 0,
    var selectedProvider: String = "auto",
    var collegeLogoUri: String = "",
    var pdfTheme: String = "classic",
    var variables: List<Variable> = emptyList(),
    var chapters: List<Chapter> = emptyList(),
    var verifiedPubMedReferences: List<ReferenceJson> = emptyList(),
    var verifiedPubMedAbstractSources: List<PubMedAbstractSourceJson> = emptyList(),
    var cachedPubMedMatches: List<PubMedMatchCacheJson> = emptyList(),
    var cachedPubMedSearchMatches: List<PubMedSearchMatchCacheJson> = emptyList(),
    var cachedPubMedAbstractSources: List<PubMedAbstractSourceJson> = emptyList(),
    var cachedVerifiedReferences: List<ReferenceJson> = emptyList(),
    var referenceSequenceCounter: Int = 1,
    var pubMedFigureCheckedPmids: List<String> = emptyList(),
    var pubMedFigures: List<PubMedFigureJson> = emptyList(),
    var vpsAutoCompleteEnabled: Boolean = false,
    var autoSyncEnabled: Boolean = true,
    var lastWorkerSyncTime: Long = 0L,
    var exportMargin: String = "normal",
    var exportFont: String = "serif",
    var exportLineSpacing: String = "normal",
    var exportLogoPlacement: String = "theme",
    var exportPageNumbering: String = "theme",
    var exportHeaderFooter: Boolean = true,
    var exportWatermark: Boolean = false,
    var exportAutoToc: Boolean = true,
    var exportAutoLists: Boolean = true,
    var promptSectionSplittingEnabled: Boolean = true,
    var promptMaxChars: Int = 12000,
    var masterChartColumns: List<MasterChartColumnJson> = emptyList(),
    var masterChartCsv: String = "",
    var masterChartGeneratedAt: Long = 0L,
    var masterDataFileName: String = "",
    var masterDataHeaders: List<String> = emptyList(),
    var masterDataRows: List<List<String>> = emptyList(),
    var masterDataMappings: List<MasterChartColumnMappingJson> = emptyList(),
    var masterDataValidationIssues: List<MasterChartValidationIssueJson> = emptyList(),
    var masterDataResultTables: List<MasterChartResultSummaryJson> = emptyList(),
    var masterDataImportedAt: Long = 0L,
    var aiLogs: List<ThesisAiLogEntry> = emptyList()
)

data class PubMedMatchCacheJson(
    var pmid: String = "",
    var doi: String? = null,
    var articleTitle: String = "",
    var canonicalReference: String = ""
)

data class PubMedSearchMatchCacheJson(
    var key: String = "",
    var match: PubMedMatchCacheJson = PubMedMatchCacheJson()
)

data class ThesisReferenceCachePayload(
    var sessionId: String = "",
    var updatedAt: Long = System.currentTimeMillis(),
    var verifiedPubMedReferences: List<ReferenceJson> = emptyList(),
    var verifiedPubMedAbstractSources: List<PubMedAbstractSourceJson> = emptyList(),
    var cachedPubMedMatches: List<PubMedMatchCacheJson> = emptyList(),
    var cachedPubMedSearchMatches: List<PubMedSearchMatchCacheJson> = emptyList(),
    var cachedPubMedAbstractSources: List<PubMedAbstractSourceJson> = emptyList(),
    var cachedVerifiedReferences: List<ReferenceJson> = emptyList(),
    var pubMedFigureCheckedPmids: List<String> = emptyList(),
    var pubMedFigures: List<PubMedFigureJson> = emptyList()
)

data class ThesisReferenceCacheMetaPayload(
    var sessionId: String = "",
    var updatedAt: Long = System.currentTimeMillis(),
    var schemaVersion: Int = 2,
    var cacheSignature: String = "",
    var verifiedReferenceCount: Int = 0,
    var abstractSourceCount: Int = 0,
    var pubMedMatchCount: Int = 0,
    var pubMedSearchMatchCount: Int = 0,
    var pubMedFigureCount: Int = 0,
    var pubMedFigureCheckedPmids: List<String> = emptyList(),
    var lastSyncError: String = ""
)

data class PubMedAbstractSourceCacheDocument(
    var pmid: String = "",
    var source: PubMedAbstractSourceJson = PubMedAbstractSourceJson(),
    var lastFetchedAt: Long = System.currentTimeMillis(),
    var schemaVersion: Int = 2
)

data class Variable(
    var name: String = "",
    var value: String = ""
)

// ==============================
// Helper models (not directly stored in Firebase)
// ==============================

data class ThesisChapterJson(
    @SerializedName("chapter_name") val chapterName: String = "",
    @SerializedName("chapter_type") val chapterType: String = "",
    @SerializedName("sections") val sections: List<ThesisSectionJson> = emptyList(),
    @SerializedName("tables") val tables: List<ThesisTableJson> = emptyList(),
    @SerializedName("figures") val figures: List<FigureJson> = emptyList(),
    @SerializedName("charts") val charts: List<ChartJson> = emptyList(),
    @SerializedName("abbreviations") val abbreviations: List<AbbreviationJson> = emptyList(),
    @SerializedName("chapter_references") val chapterReferences: List<ReferenceJson> = emptyList()
)

data class ThesisSectionJson(
    @SerializedName("heading") val heading: String = "",
    @SerializedName("content") val content: String? = null,
    @SerializedName("paragraphs") val paragraphs: List<String> = emptyList(),
    @SerializedName("bullets") val bullets: List<String> = emptyList(),
    @SerializedName("numbered_points") val numberedPoints: List<String> = emptyList(),
    @SerializedName("subsections") val subsections: List<SubSectionJson> = emptyList(),
    @SerializedName("table") val table: ThesisTableJson? = null,
    @SerializedName("figures") val figures: List<FigureJson> = emptyList(),
    @SerializedName("references") val references: List<ReferenceJson> = emptyList()
)

data class SubSectionJson(
    @SerializedName("heading") val heading: String = "",
    @SerializedName("content") val content: String = ""
)

// TableJson is used only inside ResultsJson, not stored directly in Firebase – no defaults required
data class TableJson(
    @SerializedName("table_number") val tableNumber: String = "",
    @SerializedName("title") val title: String = "",
    @SerializedName("headers") val headers: List<String> = emptyList(),
    @SerializedName("rows") val rows: List<List<String>> = emptyList(),
    @SerializedName("data") val data: List<Map<String, Any?>> = emptyList(),
    @SerializedName("footnote") val footnote: String? = null
)

data class ResultsJson(
    val sections: List<ResultSection> = emptyList(),
    val tables: List<TableJson> = emptyList(),
    val charts: List<ChartJson> = emptyList()
)

data class ResultSection(
    val heading: String = "",
    val content: String = "",
    val observations: List<String>? = null
)

data class ReferencesJson(
    val references: List<ReferenceEntry> = emptyList()
)

data class ReferenceEntry(
    val number: Int = 0,
    @SerializedName(value = "text", alternate = ["reference_text", "citation_text", "vancouver_text"])
    val text: String = "",
    @SerializedName(value = "pmid", alternate = ["PMID"]) val pmid: String? = null,
    @SerializedName(value = "doi", alternate = ["DOI"]) val doi: String? = null,
    val authors: List<String> = emptyList(),
    val title: String = "",
    val journal: String = "",
    val year: Int = 0,
    val volume: String = "",
    val pages: String = ""
)

data class MethodologyJson(
    val designType: String = "",
    val settings: Map<String, String> = emptyMap(),
    val inclusionCriteria: List<String> = emptyList(),
    val exclusionCriteria: List<String> = emptyList(),
    val sampleSize: SampleSizeDetail = SampleSizeDetail(),
    val statisticalAnalysis: List<String> = emptyList()
)

data class SampleSizeDetail(
    val formula: String = "",
    val assumptions: String = "",
    val power: Double = 0.80,
    val confidenceInterval: Double = 0.95,
    val calculatedSize: Int = 0
)

data class DiscussionJson(
    val keyFindings: String = "",
    val comparisonWithLiterature: List<LiteratureComparison> = emptyList(),
    val limitations: List<String> = emptyList(),
    val clinicalImplications: String = "",
    val futureDirections: List<String> = emptyList()
)

data class LiteratureComparison(
    val finding: String = "",
    val citationReference: String = "",
    val comparison: String = ""
)

data class ExtractionResponse(
    @SerializedName("variables") val variables: List<ExtractionVariable> = emptyList()
)

data class ExtractionVariable(
    @SerializedName("variable_name") val variableName: String = "",
    @SerializedName("variable_value") val variableValue: String? = null
)

// ==============================
// Auto‑generated front matter models (not stored in Firebase directly)
// ==============================

data class TableOfContentsJson(val entries: List<TocEntry> = emptyList())
data class TocEntry(val title: String = "", val page: Int = 0)

data class ListOfTablesJson(val tables: List<TableEntry> = emptyList())
data class TableEntry(val number: Int = 0, val title: String = "", val page: Int = 0)

data class ListOfFiguresJson(val figures: List<FigureEntry> = emptyList())
data class FigureEntry(val number: Int = 0, val title: String = "", val page: Int = 0)

data class ListOfAbbreviationsJson(val abbreviations: List<AbbrevEntry> = emptyList())
data class AbbrevEntry(val short: String = "", val full: String = "")

data class KeywordsJson(val keywords: List<String> = emptyList())
data class HypothesisJson(
    @SerializedName(value = "nullHypothesis", alternate = ["null_hypothesis", "null hypothesis", "null-hypothesis"])
    val nullHypothesis: String = "",
    @SerializedName(value = "alternateHypothesis", alternate = ["alternate_hypothesis", "alternate hypothesis", "alternate-hypothesis"])
    val alternateHypothesis: String = ""
)

data class TextBlockJson(val content: String = "")
data class EnhancedTextBlock(
    val content: String = "",
    val figures: List<FigureJson> = emptyList(),
    val abbreviations: List<AbbreviationJson> = emptyList()
)

// ==============================
// Chapter‑specific custom schemas (never stored directly in Firebase)
// ==============================

data class TitlePageJson(
    val title: String = "",
    val subtitle: String? = null,
    val author: String = "",
    val guide: String = "",
    val coGuide: String? = null,
    val institution: String = "",
    val department: String = "",
    val degree: String = "",
    val year: String = ""
)

data class AbstractJson(
    val background: String = "",
    val aim: String = "",
    val methods: String = "",
    val results: String = "",
    val conclusion: String = "",
    val keywords: List<String> = emptyList()
)

data class CertificateJson(
    val title: String = "CERTIFICATE",
    val body: String = "",
    val guideSignature: String = "___________________",
    val hodSignature: String = "___________________",
    val date: String = ""
)

data class DeclarationJson(
    val statement: String = "I hereby declare that...",
    val studentName: String = "",
    val signature: String = "___________________",
    val date: String = ""
)

data class AcknowledgementsJson(val acknowledgements: List<String> = emptyList())

data class AppendicesJson(val appendices: List<Appendix> = emptyList())
data class Appendix(val title: String = "", val content: String = "")

data class ProformaJson(
    val patientName: String = "",
    val age: String = "",
    val sex: String = "",
    val opdIpNo: String = "",
    val address: String = "",
    val history: String = "",
    val examination: String = "",
    val investigations: String = "",
    val diagnosis: String = ""
)

data class ConsentFormJson(
    val title: String = "",
    val introduction: String = "",
    val procedure: String = "",
    val risks: String = "",
    val benefits: String = "",
    val confidentiality: String = "",
    val signatureLine: String = "___________________",
    val date: String = ""
)

// ==============================
// Other project metadata (mostly not stored directly or have defaults)
// ==============================

data class ThesisProject(
    var projectId: String = "",
    var projectName: String = "",
    var thesisTitle: String = "",
    var provider: String = "auto",
    var status: String = "IDLE",
    var createdAt: Long = 0L,
    var updatedAt: Long = 0L,
    var progressPercent: Int = 0,
    var currentChapter: String = "",
    var completedChapters: Int = 0,
    var totalChapters: Int = 0,
    var variables: List<Variable> = emptyList(),
    var chapters: List<Chapter> = emptyList()
)

data class ThesisProjectCheckpoint(
    var checkpointId: String = "",
    var projectId: String = "",
    var label: String = "",
    var chapterName: String = "",
    var chapterIndex: Int = 0,
    var createdAt: Long = 0L
)

data class ChapterVersionItem(
    var chapterName: String = "",
    var versionNo: Int = 0,
    var content: String = "",
    var rawJson: String = "",
    var timestamp: Long = 0L
)

data class FigureAsset(
    var chapterName: String = "",
    var figure: FigureJson = FigureJson(),
    var localPath: String = "",
    var downloaded: Boolean = false
)

data class ProviderAnalytics(
    var provider: String = "",
    var successCount: Int = 0,
    var failureCount: Int = 0,
    var averageLatencyMs: Long = 0L,
    var lastUsedAt: Long = 0L
)

data class ThesisProjectStats(
    var variablesCount: Int = 0,
    var chaptersCount: Int = 0,
    var completedCount: Int = 0,
    var failedCount: Int = 0,
    var figuresCount: Int = 0,
    var referencesCount: Int = 0
)

data class ThesisQualityScore(
    var overall: Int = 0,
    var completeness: Int = 0,
    var figures: Int = 0,
    var references: Int = 0,
    var methodology: Int = 0
)

data class ThesisSession(
    var sessionId: String = "",
    var thesisTitle: String = "",
    var updatedAt: Long = 0L,
    var status: String = "",
    var currentChapter: Int = 0,
    var totalChapters: Int = 0,
    var completionPercent: Double = 0.0,
    var selectedProvider: String = "",
    var variables: MutableMap<String, String> = mutableMapOf(),
    var chapters: MutableMap<String, Chapter> = mutableMapOf()
)

data class SessionItem(
    var sessionId: String = "",
    var thesisTitle: String = "",
    var timestamp: Long = 0L,
    var chaptersCount: Int = 0
)
data class AiResultsJson(
    @SerializedName("sections")
    val sections: List<AiResultSection> = emptyList(),

    @SerializedName("tables")
    val tables: List<AiTable> = emptyList(),

    @SerializedName("charts")
    val charts: List<AiChart> = emptyList()
)


data class AiChart(
    @SerializedName("title")
    val title: String = "",

    @SerializedName("type")
    val type: String = "",

    @SerializedName("chart_template")
    val chartTemplate: String = "",

    @SerializedName("labels")
    val labels: List<String>? = null,

    @SerializedName("values")
    val values: List<Double>? = null,

    @SerializedName("data")
    val data: Any? = null
)

data class AiChartPoint(
    @SerializedName("label")
    val label: String = "",

    @SerializedName("value")
    val value: Double = 0.0
)
data class AiResultSection(
    @SerializedName("heading")
    val heading: String = "",

    @SerializedName("content")
    val content: String = "",

    @SerializedName("observations")
    val observations: List<String> = emptyList()
)
// ==============================
// Enums and type aliases
// ==============================
data class AiTable(
    @SerializedName("title")
    val title: String = "",

    @SerializedName("headers")
    val headers: List<String>? = null,

    @SerializedName("rows")
    val rows: List<List<Any?>>? = null,

    @SerializedName("data")
    val data: List<Map<String, Any?>>? = null
)
enum class ChartType {
    BAR, LINE, PIE, SCATTER, HORIZONTAL_BAR
}

typealias BibliographyJson = ReferencesJson

fun chartDatasetsFromRaw(
    title: String,
    labelsHint: List<String>,
    valuesHint: List<Double>,
    data: Any?
): List<ChartDatasetJson> {
    labelsHint.takeIf { it.isNotEmpty() }?.let { labels ->
        if (valuesHint.isNotEmpty()) {
            return listOf(
                ChartDatasetJson(
                    label = title.ifBlank { "Data" },
                    values = valuesHint,
                    labels = labels
                )
            )
        }
    }

    return when (data) {
        is Map<*, *> -> {
            val labels = data.keys.map { it.toString() }
            val values = data.values.mapNotNull { it?.toString()?.toDoubleOrNull() }
            if (values.isEmpty()) emptyList() else listOf(
                ChartDatasetJson(
                    label = title.ifBlank { "Data" },
                    values = values,
                    labels = labels
                )
            )
        }

        is List<*> -> {
            val maps = data.filterIsInstance<Map<*, *>>()
            if (maps.isNotEmpty()) {
                val categoryKey = detectCategoryKey(maps)
                val seriesKeys = detectSeriesKeys(maps, categoryKey)
                if (seriesKeys.isNotEmpty()) {
                    val labels = maps.mapIndexed { index, row ->
                        row[categoryKey]?.toString()
                            ?: row["label"]?.toString()
                            ?: row["name"]?.toString()
                            ?: row["category"]?.toString()
                            ?: row["time"]?.toString()
                            ?: row["month"]?.toString()
                            ?: "${index + 1}"
                    }
                    return seriesKeys.map { seriesKey ->
                        ChartDatasetJson(
                            label = seriesKey.toString(),
                            values = maps.mapNotNull { row -> row[seriesKey]?.toString()?.toDoubleOrNull() },
                            labels = labels
                        )
                    }.filter { it.values.isNotEmpty() }
                }
            }

            val points = data.filterIsInstance<AiChartPoint>()
            if (points.isNotEmpty()) {
                return listOf(
                    ChartDatasetJson(
                        label = title.ifBlank { "Data" },
                        values = points.map { it.value },
                        labels = points.map { it.label }
                    )
                )
            }

            emptyList()
        }

        else -> emptyList()
    }
}

private fun detectCategoryKey(rows: List<Map<*, *>>): Any? {
    val preferred = listOf("label", "name", "category", "time", "month", "date", "x", "title")
    val first = rows.firstOrNull() ?: return null
    preferred.firstOrNull { first.containsKey(it) }?.let { return it }
    return first.keys.firstOrNull { key ->
        val value = first[key]
        value == null || value is String
    } ?: first.keys.firstOrNull()
}

private fun detectSeriesKeys(rows: List<Map<*, *>>, categoryKey: Any?): List<Any> {
    return rows.firstOrNull()?.keys.orEmpty().filterNotNull().filter { key ->
        key != categoryKey && rows.any { row ->
            row[key] is Number || row[key]?.toString()?.toDoubleOrNull() != null
        }
    }
}

data class PageInsight(
    val pageNo: Int = 0,
    val heading: String = "",
    val sectionType: String = "",
    val summary: String = "",
    val aiComment: String = "",
    val subsections: List<Subsection> = emptyList(),
    val value: String = ""
)

data class Subsection(
    val subheading: String = "",
    val points: List<String> = emptyList()
)

sealed class AnalysisEvent {
    data class Progress(val page: Int, val total: Int, val message: String) : AnalysisEvent()
    data class Success(val pages: List<PageInsight>) : AnalysisEvent()
    data class Failure(val error: String) : AnalysisEvent()
}

data class GeminiContent(
    val parts: List<GeminiPart>
)

data class GeminiPart(
    val text: String
)

data class GeminiGenerationConfig(
    val temperature: Double,
    val maxOutputTokens: Int,
    val responseMimeType: String? = null
)
