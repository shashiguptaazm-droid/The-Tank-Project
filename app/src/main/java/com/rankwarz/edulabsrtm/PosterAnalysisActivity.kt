package com.rankwarz.edulabsrtm

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas as AndroidCanvas
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import android.net.Uri
import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.FolderOpen
import androidx.compose.material.icons.filled.Image
import androidx.compose.material.icons.filled.PictureAsPdf
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.AssistChip
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.ScrollableTabRow
import androidx.compose.material3.Slider
import androidx.compose.material3.Surface
import androidx.compose.material3.Tab
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color as ComposeColor
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.drawIntoCanvas
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import coil.compose.AsyncImage
import com.google.android.material.bottomnavigation.BottomNavigationView
import com.google.firebase.auth.FirebaseAuth
import com.google.gson.Gson
import com.google.gson.annotations.SerializedName
import com.google.gson.JsonElement
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import com.google.gson.stream.JsonReader
import com.rankwarz.edulabsrtm.data.remote.ApiClient
import com.rankwarz.edulabsrtm.data.remote.ChatRequest
import com.rankwarz.edulabsrtm.data.remote.Message
import com.rankwarz.edulabsrtm.model.ModelRotator
import com.rankwarz.edulabsrtm.ui.theme.ThesisExtractorTheme
import com.tom_roush.pdfbox.android.PDFBoxResourceLoader
import com.tom_roush.pdfbox.pdmodel.PDDocument
import com.tom_roush.pdfbox.pdmodel.PDPage
import com.tom_roush.pdfbox.pdmodel.PDPageContentStream
import com.tom_roush.pdfbox.pdmodel.common.PDRectangle
import com.tom_roush.pdfbox.pdmodel.font.PDType1Font
import com.tom_roush.pdfbox.pdmodel.graphics.image.LosslessFactory
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File
import java.io.FileOutputStream
import java.io.StringReader

data class PosterInputState(
    val disease: String = "",
    val title: String = "",
    val abstractText: String = "",
    val author: String = "",
    val credentials: String = "",
    val guide: String = "",
    val coGuide: String = "",
    val college: String = "",
    val department: String = "",
    val contact: String = "",
    val logoUri: String = "",
    val titleLogoUri: String = "",
    val backgroundUri: String = "",
    val fontUri: String = "",
    val titleColor: String = "#FFFFFF",
    val headingColor: String = "#0B5CAD",
    val subheadingColor: String = "#172033",
    val bodyColor: String = "#172033",
    val pointColor: String = "#0B5CAD",
    val footerColor: String = "#FFFFFF"
)

data class PosterSection(
    val title: String = "",
    val content: String = "",
    val bullets: List<String> = emptyList(),
    val subheadings: List<String> = emptyList(),
    val points: List<String> = emptyList(),
    @SerializedName("flowchart_steps") val flowchartSteps: List<String> = emptyList(),
    val id: String = "",
    val column: String = "left"
)

data class PosterChart(
    val title: String = "",
    val type: String = "bar",
    val labels: List<String> = emptyList(),
    val values: List<Float> = emptyList(),
    @SerializedName(value = "xAxisTitle", alternate = ["x_axis_title", "x_axis_label", "xAxisLabel"]) val xAxisTitle: String = "",
    @SerializedName(value = "yAxisTitle", alternate = ["y_axis_title", "y_axis_label", "yAxisLabel"]) val yAxisTitle: String = ""
)

data class PosterFigure(
    val title: String = "",
    val caption: String = "",
    @SerializedName(value = "query", alternate = ["image_search_query", "search_query", "imageQuery"]) val query: String = "",
    @SerializedName(value = "imageUri", alternate = ["image_uri", "image_url", "url"]) val imageUri: String = "",
    val role: String = "figure",
    val xPercent: Float = 0.5f,
    val yPercent: Float = 0.5f,
    val widthPercent: Float = 0.42f,
    val heightPercent: Float = 0.18f
)

data class PosterFlowchart(
    val title: String = "",
    val steps: List<String> = emptyList(),
    val caption: String = ""
)

data class PosterData(
    val title: String = "",
    val subtitle: String = "",
    val authorLine: String = "",
    val institution: String = "",
    val guideLine: String = "",
    val leftSections: List<PosterSection> = emptyList(),
    val centerSections: List<PosterSection> = emptyList(),
    val rightSections: List<PosterSection> = emptyList(),
    val charts: List<PosterChart> = emptyList(),
    val figures: List<PosterFigure> = emptyList(),
    val flowcharts: List<PosterFlowchart> = emptyList(),
    val references: List<String> = emptyList(),
    val contact: String = ""
)

data class PosterAiResponse(
    val title: String = "",
    val subtitle: String = "",
    val chapters: List<PosterSection> = emptyList(),
    @SerializedName("left_sections") val leftSections: List<PosterSection> = emptyList(),
    @SerializedName("center_sections") val centerSections: List<PosterSection> = emptyList(),
    @SerializedName("right_sections") val rightSections: List<PosterSection> = emptyList(),
    val charts: List<PosterChart> = emptyList(),
    val figures: List<PosterFigure> = emptyList(),
    val flowcharts: List<PosterFlowchart> = emptyList(),
    val references: List<String> = emptyList()
)

data class PosterSessionPayload(
    var sessionId: String = "",
    var title: String = "",
    var updatedAt: Long = 0L,
    var selectedProvider: String = "auto",
    var input: PosterInputState = PosterInputState(),
    var poster: PosterData? = null,
    var thesisImport: ThesisPosterImportPayload? = null,
    var selectedThesisChapterNames: List<String> = emptyList()
)

data class PosterSessionItem(
    val sessionId: String = "",
    val title: String = "",
    val timestamp: Long = 0L,
    val sectionsCount: Int = 0
)

data class ThesisPosterImportPayload(
    val thesisSessionId: String = "",
    val title: String = "",
    val disease: String = "",
    val abstractText: String = "",
    val author: String = "",
    val credentials: String = "",
    val guide: String = "",
    val coGuide: String = "",
    val college: String = "",
    val department: String = "",
    val contact: String = "",
    val logoUri: String = "",
    val chapters: List<ThesisPosterImportChapter> = emptyList(),
    val references: List<String> = emptyList(),
    val figures: List<ThesisPosterImportFigure> = emptyList(),
    val charts: List<ThesisPosterImportChart> = emptyList(),
    val tables: List<ThesisPosterImportTable> = emptyList()
)

data class ThesisPosterImportChapter(
    val name: String = "",
    val content: String = ""
)

data class ThesisPosterImportFigure(
    val chapterName: String = "",
    val title: String = "",
    val caption: String = "",
    val query: String = "",
    val imageUri: String = ""
)

data class ThesisPosterImportChart(
    val chapterName: String = "",
    val title: String = "",
    val type: String = "",
    val labels: List<String> = emptyList(),
    val values: List<Float> = emptyList(),
    val xAxisTitle: String = "",
    val yAxisTitle: String = ""
)

data class ThesisPosterImportTable(
    val chapterName: String = "",
    val title: String = "",
    val headers: List<String> = emptyList(),
    val rows: List<List<String>> = emptyList()
)

data class PosterAnalysisUiState(
    val sessionId: String = "",
    val selectedProvider: String = "auto",
    val input: PosterInputState = PosterInputState(),
    val poster: PosterData? = null,
    val thesisImport: ThesisPosterImportPayload? = null,
    val selectedThesisChapterNames: Set<String> = emptySet(),
    val previousSessions: List<PosterSessionItem> = emptyList(),
    val processing: Boolean = false,
    val status: String = "Ready"
)

class PosterAnalysisViewModel : ViewModel() {
    private val _uiState = MutableStateFlow(PosterAnalysisUiState(sessionId = newSessionId()))
    val uiState = _uiState.asStateFlow()
    private val gson = Gson()

    init {
        tryLoadLatestSession()
        loadPreviousSessions()
    }

    private fun newSessionId(): String = "poster_${System.currentTimeMillis()}_${(1000..9999).random()}"

    private fun getUid(): String? = FirebaseAuth.getInstance().currentUser?.uid

    fun createNewSession() {
        _uiState.update {
            PosterAnalysisUiState(
                sessionId = newSessionId(),
                previousSessions = it.previousSessions,
                status = "New poster session"
            )
        }
    }

    private fun getPosterBackendUrl(): String {
        return ApiKeys.THESIS_SESSION_BACKEND_URL.replace("thesis_session_backend.php", "poster_session_backend.php")
    }

    fun saveSessionToFirebase() {
        val uid = getUid() ?: return
        val state = _uiState.value
        val sessionId = state.sessionId.ifBlank { newSessionId() }
        val title = state.poster?.title ?: state.input.title.ifBlank { state.input.disease.ifBlank { "Untitled poster" } }
        val payload = PosterSessionPayload(
            sessionId = sessionId,
            title = title,
            updatedAt = System.currentTimeMillis(),
            selectedProvider = state.selectedProvider,
            input = state.input,
            poster = state.poster,
            thesisImport = state.thesisImport,
            selectedThesisChapterNames = state.selectedThesisChapterNames.toList()
        )
        val backendUrl = getPosterBackendUrl()
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val body = gson.toJson(payload).toRequestBody("application/json; charset=utf-8".toMediaType())
                val request = Request.Builder()
                    .url(backendUrl)
                    .post(body)
                    .build()
                OkHttpClient().newCall(request).execute().use { response ->
                    val raw = response.body?.string().orEmpty()
                    if (!response.isSuccessful) throw java.io.IOException("Poster backend save HTTP ${response.code}: ${raw.take(500)}")
                    val obj = com.google.gson.JsonParser.parseString(raw).asJsonObject
                    if (!obj.get("ok").asBoolean) throw java.io.IOException(obj.get("error")?.asString ?: "Backend returned ok=false")
                    
                    withContext(Dispatchers.Main) {
                        _uiState.update { it.copy(sessionId = sessionId, status = "Poster session saved") }
                        loadPreviousSessions()
                    }
                }
            } catch (e: Exception) {
                Log.e("PosterAnalysis", "Poster session save failed", e)
                withContext(Dispatchers.Main) {
                    _uiState.update { it.copy(status = "Session save failed: ${e.localizedMessage}") }
                }
            }
        }
    }

    fun tryLoadLatestSession() {
        val uid = getUid() ?: return
        val backendUrl = getPosterBackendUrl()
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val url = "$backendUrl?action=latest&user_id=${Uri.encode(uid)}"
                val request = Request.Builder().url(url).build()
                OkHttpClient().newCall(request).execute().use { response ->
                    val raw = response.body?.string().orEmpty()
                    if (!response.isSuccessful) return@launch
                    val obj = com.google.gson.JsonParser.parseString(raw).asJsonObject
                    if (obj.get("ok").asBoolean && !obj.get("session").isJsonNull) {
                        val sessionObj = obj.getAsJsonObject("session")
                        val session = gson.fromJson(sessionObj, PosterSessionPayload::class.java)
                        withContext(Dispatchers.Main) {
                            if (!(_uiState.value.status.contains("thesis", ignoreCase = true) || _uiState.value.processing)) {
                                restoreSession(session)
                            }
                        }
                    }
                }
            } catch (e: Exception) {
                Log.e("PosterAnalysis", "Latest poster session load failed", e)
            }
        }
    }

    fun importThesisPayload(payloadJson: String, autoGenerate: Boolean = true) {
        if (payloadJson.isBlank()) return
        val payload = runCatching {
            gson.fromJson(payloadJson, ThesisPosterImportPayload::class.java)
        }.getOrElse { error ->
            _uiState.update { it.copy(status = "Thesis poster import failed: ${error.localizedMessage}") }
            return
        }

        val input = PosterInputState(
            disease = payload.disease.ifBlank { payload.title },
            title = payload.title.ifBlank { "Thesis Poster" },
            abstractText = buildThesisPosterAbstract(payload),
            author = payload.author,
            credentials = payload.credentials,
            guide = payload.guide,
            coGuide = payload.coGuide,
            college = payload.college,
            department = payload.department,
            contact = payload.contact,
            logoUri = payload.logoUri,
            titleLogoUri = payload.logoUri
        )
        val selectedChapterNames = defaultPosterChapterNames(payload)
        val poster = buildPosterDirectlyFromThesis(payload, input, selectedChapterNames)

        _uiState.update {
            it.copy(
                sessionId = "poster_from_${payload.thesisSessionId.ifBlank { System.currentTimeMillis().toString() }}",
                input = input,
                poster = poster,
                thesisImport = payload,
                selectedThesisChapterNames = selectedChapterNames,
                processing = false,
                status = "Poster built from thesis data"
            )
        }
        if (autoGenerate) saveSessionToFirebase()
    }

    private fun defaultPosterChapterNames(payload: ThesisPosterImportPayload): Set<String> {
        val preferred = listOf(
            "Abstract",
            "Introduction",
            "Background",
            "Disease Burden",
            "Epidemiology",
            "Pathophysiology",
            "Aim of Study",
            "Objectives",
            "Materials and Methods",
            "Study Design",
            "Results",
            "Observations",
            "Discussion",
            "Conclusion",
            "Recommendations"
        )
        val byName = payload.chapters.associateBy { it.name.lowercase() }
        val selected = preferred.mapNotNull { byName[it.lowercase()]?.name }.toMutableSet()
        if (selected.isEmpty()) {
            selected += payload.chapters.take(8).map { it.name }
        }
        return selected
    }

    fun toggleThesisChapterForPoster(chapterName: String) {
        val payload = _uiState.value.thesisImport ?: return
        val nextSelection = _uiState.value.selectedThesisChapterNames.toMutableSet().apply {
            if (chapterName in this) remove(chapterName) else add(chapterName)
        }
        val poster = buildPosterDirectlyFromThesis(payload, _uiState.value.input, nextSelection)
        _uiState.update {
            it.copy(
                selectedThesisChapterNames = nextSelection,
                poster = poster,
                status = "Poster rebuilt from selected thesis chapters"
            )
        }
        saveSessionToFirebase()
    }

    fun rebuildPosterFromSelectedThesisChapters() {
        val payload = _uiState.value.thesisImport ?: return
        val poster = buildPosterDirectlyFromThesis(payload, _uiState.value.input, _uiState.value.selectedThesisChapterNames)
        _uiState.update { it.copy(poster = poster, status = "Poster rebuilt from thesis data") }
        saveSessionToFirebase()
    }

    private fun buildPosterDirectlyFromThesis(
        payload: ThesisPosterImportPayload,
        input: PosterInputState,
        selectedChapterNames: Set<String>
    ): PosterData {
        val selectedChapters = payload.chapters
            .filter { it.name in selectedChapterNames && it.content.isNotBlank() }
        val sections = selectedChapters.mapIndexed { index, chapter ->
            val parsed = parseThesisTextForPoster(chapter.content)
            PosterSection(
                title = posterSectionTitle(chapter.name),
                content = parsed.content,
                bullets = parsed.bullets,
                subheadings = (listOf(chapter.name) + parsed.subheadings).distinct().take(4),
                points = parsed.numberedPoints,
                id = "thesis_${index + 1}",
                column = "left"
            )
        }.ifEmpty {
            buildFallbackPoster(input).leftSections + buildFallbackPoster(input).centerSections + buildFallbackPoster(input).rightSections
        }

        val distributed = distributePosterChapters(sections)
        val importedCharts = payload.charts.take(6).mapIndexed { index, chart ->
            PosterChart(
                title = chart.title.ifBlank { "Thesis Chart ${index + 1}" },
                type = chart.type.ifBlank { "bar" },
                labels = chart.labels,
                values = chart.values,
                xAxisTitle = chart.xAxisTitle,
                yAxisTitle = chart.yAxisTitle
            )
        }
        val importedFigures = payload.figures.take(8).mapIndexed { index, figure ->
            PosterFigure(
                title = figure.title.ifBlank { "Thesis Figure ${index + 1}" },
                caption = figure.caption,
                query = figure.query,
                imageUri = figure.imageUri
            )
        }
        val tableSections = payload.tables.take(3).map { table ->
            PosterSection(
                title = table.title.ifBlank { "Key Table" },
                content = buildString {
                    append(table.headers.joinToString(" | "))
                    table.rows.take(4).forEach { row ->
                        append("\n")
                        append(row.joinToString(" | "))
                    }
                }.trim(),
                subheadings = listOf("Thesis table"),
                column = "center"
            )
        }

        return PosterData(
            title = input.title,
            subtitle = "Generated directly from thesis analysis",
            authorLine = listOf(input.author, input.credentials).filter { it.isNotBlank() }.joinToString(", "),
            institution = listOf(input.department, input.college).filter { it.isNotBlank() }.joinToString(" | "),
            guideLine = listOf(
                input.guide.takeIf { it.isNotBlank() }?.let { "Guide: $it" },
                input.coGuide.takeIf { it.isNotBlank() }?.let { "Co-guide: $it" }
            ).filterNotNull().joinToString("  |  "),
            leftSections = distributed.first,
            centerSections = distributed.second + tableSections,
            rightSections = distributed.third,
            charts = importedCharts,
            figures = importedFigures,
            flowcharts = listOf(
                PosterFlowchart(
                    title = "Thesis to Poster Workflow",
                    steps = listOf("Thesis analysis", "Relevant chapters", "Tables/charts/figures", "Poster layout", "Export"),
                    caption = "Built from existing thesis analysis without AI regeneration."
                )
            ),
            references = payload.references.take(10),
            contact = input.contact
        )
    }

    private fun posterSectionTitle(chapterName: String): String {
        return when (chapterName.lowercase()) {
            "materials and methods", "study design", "study setting", "study population" -> "Methods"
            "results", "observations" -> "Results"
            "aim of study", "objectives" -> "Aim and Objectives"
            else -> chapterName
        }
    }

    private fun extractPosterPointsFromThesisText(text: String): List<String> {
        return parseThesisTextForPoster(text).let { (it.bullets + it.numberedPoints).distinct().take(5) }
    }

    private data class ParsedPosterText(
        val content: String = "",
        val subheadings: List<String> = emptyList(),
        val bullets: List<String> = emptyList(),
        val numberedPoints: List<String> = emptyList()
    )

    private fun parseThesisTextForPoster(raw: String): ParsedPosterText {
        val lines = raw
            .replace("\r\n", "\n")
            .replace('\r', '\n')
            .lines()
            .map { it.trim() }
            .filter { it.isNotBlank() }

        val subheadings = mutableListOf<String>()
        val bullets = mutableListOf<String>()
        val numbered = mutableListOf<String>()
        val contentParts = mutableListOf<String>()

        lines.forEach { line ->
            val normalized = stripPosterMarkdown(line)
            val bullet = Regex("""^\s*(?:[-*\u2022]|\u2013|\u2014)\s+(.+)""").find(line)
            val numberedPoint = Regex("""^\s*(?:\d{1,2}[.)]|\(?[ivxlcdmIVXLCDM]{1,6}[.)])\s+(.+)""").find(line)
            val boldLabel = Regex("""^\s*\*\*([^*]{2,80})\*\*\s*:?\s*(.*)$""").find(line)
            val plainLabel = Regex("""^([A-Z][A-Za-z /&-]{2,60})\s*:\s+(.{8,})$""").find(normalized)

            when {
                bullet != null -> bullets += stripPosterMarkdown(bullet.groupValues[1])
                numberedPoint != null -> numbered += stripPosterMarkdown(numberedPoint.groupValues[1])
                boldLabel != null -> {
                    subheadings += stripPosterMarkdown(boldLabel.groupValues[1])
                    boldLabel.groupValues.getOrNull(2)?.takeIf { it.isNotBlank() }?.let {
                        contentParts += stripPosterMarkdown(it)
                    }
                }
                plainLabel != null && normalized.length < 220 -> {
                    subheadings += plainLabel.groupValues[1].trim()
                    contentParts += plainLabel.groupValues[2].trim()
                }
                normalized.length <= 90 && normalized.count { it == ' ' } <= 8 && !normalized.endsWith(".") -> {
                    subheadings += normalized
                }
                else -> contentParts += normalized
            }
        }

        val sentencePoints = contentParts
            .joinToString(" ")
            .split(Regex("""(?<=[.!?])\s+|;"""))
            .map { stripPosterMarkdown(it).trim() }
            .filter { it.length in 24..220 }
            .distinct()

        val content = contentParts
            .joinToString(" ")
            .replace(Regex("\\s+"), " ")
            .trim()
            .take(520)

        return ParsedPosterText(
            content = content,
            subheadings = subheadings.map(::stripPosterMarkdown).filter { it.isNotBlank() }.distinct().take(3),
            bullets = (bullets + sentencePoints).map(::stripPosterMarkdown).filter { it.isNotBlank() }.distinct().take(5),
            numberedPoints = numbered.map(::stripPosterMarkdown).filter { it.isNotBlank() }.distinct().take(5)
        )
    }

    private fun stripPosterMarkdown(value: String): String {
        return value
            .replace(Regex("""\*\*([^*]+)\*\*"""), "$1")
            .replace(Regex("""__([^_]+)__"""), "$1")
            .replace(Regex("""`([^`]+)`"""), "$1")
            .replace(Regex("""\s+"""), " ")
            .trim(' ', '-', '*', '\u2022', ':')
    }

    private fun buildThesisPosterAbstract(payload: ThesisPosterImportPayload): String {
        val chapterDigest = payload.chapters
            .filter { it.content.isNotBlank() }
            .take(12)
            .joinToString("\n\n") { chapter ->
                "${chapter.name}: ${chapter.content.replace(Regex("\\s+"), " ").take(1200)}"
            }
        val references = payload.references.take(12).joinToString("\n") { "- $it" }
        val figures = payload.figures.take(8).joinToString("\n") { "- ${it.chapterName}: ${it.title} ${it.caption}" }
        val charts = payload.charts.take(8).joinToString("\n") { "- ${it.chapterName}: ${it.title} (${it.type})" }
        val tables = payload.tables.take(8).joinToString("\n") { "- ${it.chapterName}: ${it.title}" }

        return """
            THESIS TITLE: ${payload.title}
            DISEASE/TOPIC: ${payload.disease}

            THESIS CHAPTER DATA:
            $chapterDigest

            AVAILABLE TABLES:
            $tables

            AVAILABLE CHARTS:
            $charts

            AVAILABLE FIGURES:
            $figures
            VERIFIED REFERENCES:
            $references
        """.trimIndent().take(18000)
    }

    fun loadPreviousSessions() {
        val uid = getUid() ?: return
        val backendUrl = getPosterBackendUrl()
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val url = "$backendUrl?action=list&user_id=${Uri.encode(uid)}"
                val request = Request.Builder().url(url).build()
                OkHttpClient().newCall(request).execute().use { response ->
                    val raw = response.body?.string().orEmpty()
                    if (!response.isSuccessful) throw java.io.IOException("HTTP ${response.code}")
                    val obj = com.google.gson.JsonParser.parseString(raw).asJsonObject
                    if (obj.get("ok").asBoolean) {
                        val arr = obj.getAsJsonArray("sessions")
                        val sessions = arr.map { element ->
                            val itemObj = element.asJsonObject
                            PosterSessionItem(
                                sessionId = itemObj.get("session_id").asString,
                                title = itemObj.get("title").asString,
                                timestamp = itemObj.get("updated_at").asLong,
                                sectionsCount = itemObj.get("sectionsCount").asInt
                            )
                        }
                        withContext(Dispatchers.Main) {
                            _uiState.update { it.copy(previousSessions = sessions) }
                        }
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    _uiState.update { it.copy(status = "Failed to load poster sessions: ${e.localizedMessage}") }
                }
            }
        }
    }

    fun loadSession(sessionId: String) {
        val uid = getUid() ?: return
        _uiState.update { it.copy(processing = true, status = "Loading poster session...") }
        val backendUrl = getPosterBackendUrl()
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val url = "$backendUrl?action=load&user_id=${Uri.encode(uid)}&session_id=${Uri.encode(sessionId)}"
                val request = Request.Builder().url(url).build()
                OkHttpClient().newCall(request).execute().use { response ->
                    val raw = response.body?.string().orEmpty()
                    if (!response.isSuccessful) throw java.io.IOException("HTTP ${response.code}")
                    val obj = com.google.gson.JsonParser.parseString(raw).asJsonObject
                    if (obj.get("ok").asBoolean && !obj.get("session").isJsonNull) {
                        val sessionObj = obj.getAsJsonObject("session")
                        val session = gson.fromJson(sessionObj, PosterSessionPayload::class.java)
                        withContext(Dispatchers.Main) {
                            restoreSession(session)
                        }
                    } else {
                        withContext(Dispatchers.Main) {
                            _uiState.update { it.copy(processing = false, status = "Poster session not found") }
                        }
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    _uiState.update { it.copy(processing = false, status = "Poster session load failed: ${e.localizedMessage}") }
                }
            }
        }
    }

    private fun restoreSession(session: PosterSessionPayload) {
        _uiState.update {
            it.copy(
                sessionId = session.sessionId.ifBlank { newSessionId() },
                selectedProvider = session.selectedProvider.ifBlank { it.selectedProvider },
                input = session.input,
                poster = session.poster,
                thesisImport = session.thesisImport,
                selectedThesisChapterNames = session.selectedThesisChapterNames.toSet(),
                processing = false,
                status = "Poster session restored"
            )
        }
    }

    fun updateInput(transform: PosterInputState.() -> PosterInputState) {
        _uiState.update { it.copy(input = it.input.transform()) }
    }

    fun setProvider(provider: String) {
        _uiState.update { it.copy(selectedProvider = provider, status = "Poster AI provider set to $provider") }
        saveSessionToFirebase()
    }

    fun generatePoster() {
        viewModelScope.launch {
            _uiState.update { it.copy(processing = true, status = "Asking AI for poster content...") }
            val input = _uiState.value.input
            var rawAiResponse = ""
            var finalStatus = "Poster generated"
            val poster = runCatching {
                rawAiResponse = callPosterAi(buildPosterPrompt(input))
                parsePosterAiResponse(rawAiResponse, input)
            }.getOrElse { error ->
                finalStatus = "AI parse failed; error shown in poster: ${error.message}"
                buildPosterErrorDraft(input, error.message.orEmpty(), rawAiResponse)
            }
            _uiState.update { it.copy(poster = poster, processing = false, status = finalStatus) }
            saveSessionToFirebase()
        }
    }

    private fun buildPosterErrorDraft(input: PosterInputState, errorMessage: String, rawAiResponse: String): PosterData {
        val base = buildFallbackPoster(input)
        val rawPreview = rawAiResponse
            .ifBlank { "AI did not return text." }
            .take(1800)
        return base.copy(
            subtitle = "AI JSON parse error - editable diagnostic draft",
            leftSections = listOf(
                PosterSection(
                    title = "AI JSON Parse Error",
                    content = "The AI response could not be parsed as valid JSON. Error: ${errorMessage.ifBlank { "Unknown parse error" }}",
                    subheadings = listOf("What happened"),
                    points = listOf("The poster was not generated from parsed AI JSON.", "Raw AI response is shown in the next section.", "Regenerate after correcting the prompt or model output.")
                ),
                PosterSection(
                    title = "Raw AI Response",
                    content = rawPreview,
                    subheadings = listOf("For debugging"),
                    points = listOf("This text is included in preview, PDF export, and PNG export.")
                )
            ),
            centerSections = listOf(
                PosterSection(
                    title = "Required JSON Shape",
                    content = "Return one JSON object with title, subtitle, chapters, charts, figures, flowcharts, and references. Do not wrap it in markdown. Do not add commentary before or after JSON.",
                    subheadings = listOf("Parser requirement"),
                    points = listOf("Use double quotes for all keys and string values.", "Use arrays for chapters/charts/figures/flowcharts.", "No trailing commas.")
                )
            ),
            rightSections = base.rightSections.take(1)
        )
    }

    private fun buildFallbackPoster(input: PosterInputState): PosterData {
        val disease = input.disease.ifBlank { "Clinical Disease Topic" }
        val title = input.title.ifBlank { "Poster Analysis of $disease" }
        val author = listOf(input.author.ifBlank { "Author Name" }, input.credentials)
            .filter { it.isNotBlank() }
            .joinToString(", ")
        val guide = listOf(
            input.guide.takeIf { it.isNotBlank() }?.let { "Guide: $it" },
            input.coGuide.takeIf { it.isNotBlank() }?.let { "Co-guide: $it" }
        ).filterNotNull().joinToString("  |  ")

        return PosterData(
            title = title,
            subtitle = input.abstractText.takeIf { it.isNotBlank() }?.let { "Abstract supplied | AI chapter layout" }
                ?: "Conference poster | recommended portrait A0/A1 ratio",
            authorLine = author,
            institution = listOf(input.department, input.college.ifBlank { "Institution / College" })
                .filter { it.isNotBlank() }
                .joinToString(" | "),
            guideLine = guide,
            leftSections = listOf(
                PosterSection(
                    "Abstract",
                    input.abstractText.ifBlank {
                        "$disease is summarized as a focused clinical/research problem. This poster highlights background, method, analysis, outcomes and practical implications in a compact conference format."
                    },
                    subheadings = listOf("Background", "Aim"),
                    points = listOf("Use verified disease facts only", "Replace illustrative data with study data before submission")
                ),
                PosterSection(
                    "Introduction",
                    "The poster establishes the disease context, burden, key diagnostic concerns and why structured analysis is useful for clinical or academic presentation.",
                    listOf("Disease focus: $disease", "Concise academic framing", "Designed for conference presentation"),
                    subheadings = listOf("Disease Context", "Clinical Relevance"),
                    points = listOf("Definition", "Burden", "Diagnostic concern")
                ),
                PosterSection(
                    "Objectives",
                    "To create a visually clear poster that communicates the disease background, analytic method, result patterns and final recommendations.",
                    listOf("Recognize key disease variables", "Summarize findings", "Present charts and figures"),
                    subheadings = listOf("Primary Objective", "Secondary Objectives"),
                    points = listOf("Summarize verified evidence", "Present a professional visual layout")
                )
            ),
            centerSections = listOf(
                PosterSection(
                    "Methodology",
                    "AI-assisted poster drafting uses the entered disease, author credentials, guide details and college information to produce structured poster content.",
                    listOf("Input normalization", "Section generation", "Visual asset planning", "Export-ready layout"),
                    subheadings = listOf("Workflow", "Verification"),
                    points = listOf("Parse disease topic", "Generate structured sections", "Export poster"),
                    flowchartSteps = listOf("Input", "Verified writing", "Layout", "Export")
                ),
                PosterSection(
                    "Analysis",
                    "The central column prioritizes evidence flow, measurable categories and visual rendering. At least two charts and two figures are generated for every poster."
                ),
                PosterSection(
                    "Results",
                    "Generated result blocks emphasize distribution, severity, workflow and clinically relevant takeaways for $disease."
                )
            ),
            rightSections = listOf(
                PosterSection(
                    "Key Findings",
                    "The generated poster identifies major themes, expected disease workflow, high-value clinical markers and actionable conclusions."
                ),
                PosterSection(
                    "Conclusion",
                    "$disease can be presented effectively using a three-column academic design with abstract, methodology, analysis, findings, figures and charts."
                ),
                PosterSection(
                    "Recommendations",
                    "Use verified data, replace placeholders with local figures where available, and export the final poster as PDF or PNG for submission."
                )
            ),
            charts = listOf(
                PosterChart(
                    "Clinical Pattern Distribution",
                    "bar",
                    listOf("Mild", "Moderate", "Severe", "Critical"),
                    listOf(24f, 38f, 21f, 9f),
                    xAxisTitle = "Clinical category",
                    yAxisTitle = "Cases"
                ),
                PosterChart(
                    "Outcome Share",
                    "pie",
                    listOf("Improved", "Stable", "Follow-up", "Escalated"),
                    listOf(45f, 27f, 18f, 10f),
                    xAxisTitle = "Outcome",
                    yAxisTitle = "Share"
                )
            ),
            figures = listOf(
                PosterFigure("$disease pathway", "Conceptual disease pathway / pathophysiology figure.", "$disease pathophysiology flowchart medical diagram"),
                PosterFigure("Diagnostic workflow", "Suggested diagnostic and management workflow.", "$disease diagnostic workflow algorithm")
            ),
            flowcharts = listOf(
                PosterFlowchart(
                    "$disease poster workflow",
                    listOf("Disease topic", "Verified facts", "Section writing", "Charts/Figures", "Final export"),
                    "Editable professional poster generation flow."
                )
            ),
            references = listOf(
                "Use Vancouver/APA/IEEE references from verified source literature.",
                "Add PMID/DOI backed disease references before final submission."
            ),
            contact = input.contact.ifBlank { "Contact / email / QR link" }
        )
    }

    private fun buildPosterPrompt(input: PosterInputState): String {
        return """
            Return ONLY one valid JSON object. No markdown. No explanation. No code fence.
            The first character must be { and the last character must be }.
            Use double quotes for every key and every string. Do not use trailing commas.
            I want to make a professional medical/research conference poster from this abstract and these details.
            Read the abstract, understand the topic, decide the best poster chapter headings yourself, and fill every chapter with poster-ready content.

            Poster details to use:
            - Disease/topic: ${input.disease}
            - Poster title: ${input.title}
            - Abstract: ${input.abstractText}
            - Author: ${input.author}
            - Credentials: ${input.credentials}
            - Guide: ${input.guide}
            - Co-guide: ${input.coGuide}
            - College/institution: ${input.college}
            - Department: ${input.department}
            - Contact: ${input.contact}

            Make the poster professional, academic, compact, and visually scannable.
            Decide all chapter headings from the abstract. Do not use generic placeholder headings.
            Include an abstract/summary chapter, methods or approach when relevant, findings/results when relevant, conclusion, and recommendations only if they fit the abstract.
            Return 6-10 poster chapters unless the abstract clearly needs a different count.

            Accuracy rules:
            - Write only verified medical facts.
            - Do not invent prevalence, mortality, sensitivity, specificity, treatment effects, guideline claims, PMIDs, DOIs, or study data.
            - If something is not verified from the abstract/details, say "Not verified from supplied data".
            - Charts must use abstract-supplied or clearly illustrative values only; never fabricate study results.

            Visual rules:
            - Add at least 2 useful figures, 2 useful charts, and 1 useful flowchart when appropriate.
            - Figures should include image search queries.
            - Flowcharts should represent real clinical/research workflow from the abstract/topic.
            - Charts must use one of these type values exactly: "bar", "histogram", "line", "pie", "scatter".
            - For a line graph use: {"type":"line","labels":["Baseline","Follow-up"],"values":[10,15],"xAxisTitle":"Time","yAxisTitle":"Value"}.
            - For a histogram use: {"type":"histogram","labels":["0-10","11-20","21-30"],"values":[4,9,3],"xAxisTitle":"Range","yAxisTitle":"Frequency"}.
            - For a pie chart use: {"type":"pie","labels":["Group A","Group B"],"values":[60,40],"xAxisTitle":"Category","yAxisTitle":"Share"}.
            - For a figure use: {"title":"Diagnostic workflow","caption":"Short caption","query":"disease diagnostic workflow medical diagram"}.
            - For a flowchart use: {"title":"Clinical workflow","steps":["Screen","Diagnose","Treat","Follow up"],"caption":"Short caption"}.

            JSON schema:
            {
              "title":"AI improved poster title",
              "subtitle":"short subtitle",
              "chapters":[{"title":"AI-decided chapter heading","subheadings":["Subheading A","Subheading B"],"content":"complete filled chapter text","bullets":["bullet 1","bullet 2","bullet 3"],"points":["point 1","point 2","point 3"],"flowchart_steps":["Step 1","Step 2","Step 3"]}],
              "charts":[{"title":"...","type":"bar","labels":["A","B"],"values":[10,20],"xAxisTitle":"...","yAxisTitle":"..."}],
              "figures":[{"title":"...","caption":"...","query":"..."}],
              "flowcharts":[{"title":"...","steps":["Step 1","Step 2","Step 3","Step 4"],"caption":"..."}],
              "references":["Vancouver style reference placeholder with PMID/DOI if known"]
            }
        """.trimIndent()
    }

    private suspend fun callPosterAi(prompt: String): String = withContext(Dispatchers.IO) {
        val errors = mutableListOf<String>()
        refreshPosterHuggingFaceModelsIfNeeded()
        val selectedProvider = _uiState.value.selectedProvider
        for (candidate in ModelRotator.buildPool(selectedProvider)) {
            val attemptStartedAt = System.currentTimeMillis()
            try {
                if (candidate.provider !in setOf("groq", "openrouter", "deepseek", "mistral", "cerebras", "huggingface")) continue
                if (candidate.provider == "huggingface") {
                    val hfText = callPosterHuggingFace(candidate.model, prompt)
                    logPosterExchange(candidate.provider, candidate.model, prompt, hfText, attemptStartedAt, "completed")
                    return@withContext hfText
                }
                val apiKey = when (candidate.provider) {
                    "groq" -> ApiKeys.GROQ_API_KEY
                    "openrouter" -> ApiKeys.OPENROUTER_API_KEY
                    "deepseek" -> ApiKeys.DEEPSEEK_API_KEY
                    "mistral" -> ApiKeys.MISTRAL_API_KEY
                    "cerebras" -> ApiKeys.CEREBRAS_API_KEY
                    else -> ""
                }.trim()
                if (apiKey.isBlank()) continue
        val request = ChatRequest(
                    model = candidate.model,
                    messages = listOf(
                        Message("system", "Return ONLY valid JSON. No markdown. You are a medical academic poster writer. Use only verified disease facts; never invent data, citations, PMIDs, DOIs, or guideline claims."),
                        Message("user", prompt)
                    ),
                    temperature = 0.25,
                    maxTokens = 5000
                )
                val response = when (candidate.provider) {
                    "groq" -> ApiClient.groqApi.chatCompletion("openai/v1/chat/completions", "Bearer $apiKey", request)
                    "openrouter" -> ApiClient.openRouterApi.chatCompletion("api/v1/chat/completions", "Bearer $apiKey", request)
                    "deepseek" -> ApiClient.deepSeekApi.chatCompletion("chat/completions", "Bearer $apiKey", request)
                    "mistral" -> ApiClient.mistralApi.chatCompletion("v1/chat/completions", "Bearer $apiKey", request)
                    "cerebras" -> ApiClient.cerebrasApi.chatCompletion("v1/chat/completions", "Bearer $apiKey", request)
                    else -> error("Unsupported provider")
                }
                val content = response.choices.firstOrNull()?.message?.content?.trim().orEmpty()
                    .ifBlank { error("Empty AI response") }
                logPosterExchange(candidate.provider, candidate.model, prompt, content, attemptStartedAt, "completed")
                return@withContext content
            } catch (e: Throwable) {
                val msg = e.message ?: e.toString()
                logPosterExchange(candidate.provider, candidate.model, prompt, "", attemptStartedAt, "failed", msg)
                errors += "${candidate.provider}/${candidate.model}: $msg"
            }
        }
        throw IllegalStateException(errors.joinToString(" | ").ifBlank { "No usable AI provider" })
    }

    private fun logPosterExchange(
        provider: String,
        model: String,
        prompt: String,
        content: String,
        startedAt: Long,
        status: String,
        errorMsg: String = ""
    ) {
        runCatching {
            AiTrainingLogger.log(
                source = "poster_ai",
                provider = provider,
                model = model,
                prompt = prompt,
                response = content,
                status = status,
                contextJson = errorMsg.take(2000),
                durationMs = System.currentTimeMillis() - startedAt
            )
        }
    }

    private suspend fun refreshPosterHuggingFaceModelsIfNeeded() {
        if (!ModelRotator.shouldRefreshHuggingFaceModels()) return

        runCatching {
            val apiKey = ApiKeys.HUGGINGFACE_API_KEY.trim()
            if (apiKey.isBlank()) error("Hugging Face API key missing")
            val request = Request.Builder()
                .url("https://router.huggingface.co/v1/models")
                .addHeader("Authorization", "Bearer $apiKey")
                .addHeader("Accept", "application/json")
                .get()
                .build()
            OkHttpClient().newCall(request).execute().use { response ->
                val raw = response.body?.string().orEmpty()
                if (!response.isSuccessful) error("Hugging Face models HTTP ${response.code}: ${raw.take(500)}")
                val root = JsonParser.parseString(raw).asJsonObject
                val modelElements = when {
                    root.get("data")?.isJsonArray == true -> root.getAsJsonArray("data")
                    root.get("models")?.isJsonArray == true -> root.getAsJsonArray("models")
                    else -> null
                } ?: return@runCatching
                val models = modelElements.mapNotNull { element ->
                    val model = element.takeIf { it.isJsonObject }?.asJsonObject ?: return@mapNotNull null
                    listOf("id", "model", "name")
                        .firstNotNullOfOrNull { key ->
                            model.get(key)
                                ?.takeIf { it.isJsonPrimitive }
                                ?.asString
                                ?.trim()
                                ?.takeIf { it.isNotBlank() && !it.contains(' ') }
                        }
                }.distinct()
                if (models.isNotEmpty()) {
                    ModelRotator.replaceProviderModels("huggingface", models)
                }
            }
        }.onFailure {
            Log.w("PosterAnalysis", "Hugging Face model discovery failed; using fallback catalog: ${it.message ?: it.toString()}")
        }
    }

    private fun callPosterHuggingFace(model: String, prompt: String): String {
        val apiKey = ApiKeys.HUGGINGFACE_API_KEY.trim()
        if (apiKey.isBlank()) error("Hugging Face API key missing")

        val payload = mapOf(
            "model" to model.ifBlank { ApiKeys.HUGGINGFACE_MODEL },
            "messages" to listOf(
                mapOf("role" to "system", "content" to "Return ONLY valid JSON. No markdown. You are a medical academic poster writer. Use only verified disease facts; never invent data, citations, PMIDs, DOIs, or guideline claims."),
                mapOf("role" to "user", "content" to prompt)
            ),
            "temperature" to 0.25,
            "max_tokens" to 5000,
            "stream" to false
        )
        val body = Gson().toJson(payload)
            .toRequestBody("application/json; charset=utf-8".toMediaType())
        val request = Request.Builder()
            .url("https://router.huggingface.co/v1/chat/completions")
            .addHeader("Authorization", "Bearer $apiKey")
            .addHeader("Content-Type", "application/json")
            .post(body)
            .build()

        OkHttpClient().newCall(request).execute().use { response ->
            val raw = response.body?.string().orEmpty()
            if (!response.isSuccessful) {
                error("Hugging Face HTTP ${response.code}: ${raw.take(500)}")
            }
            val json = JsonParser.parseString(raw).asJsonObject
            return json.getAsJsonArray("choices")
                ?.firstOrNull()
                ?.asJsonObject
                ?.getAsJsonObject("message")
                ?.get("content")
                ?.asString
                ?.trim()
                .orEmpty()
                .ifBlank { error("Empty Hugging Face response") }
        }
    }

    private fun parsePosterAiResponse(raw: String, input: PosterInputState): PosterData {
        val cleaned = repairPosterJson(extractPosterJsonObject(raw))
        JsonParser.parseString(cleaned)
        val ai = parsePosterAiJson(cleaned)
        val base = buildFallbackPoster(input)
        val aiChapters = normalizeAiChapters(ai.chapters)
        val chapterColumns = if (aiChapters.isNotEmpty()) {
            distributePosterChapters(aiChapters)
        } else {
            Triple(
                normalizeSections(ai.leftSections, base.leftSections, "left"),
                normalizeSections(ai.centerSections, base.centerSections, "center"),
                normalizeSections(ai.rightSections, base.rightSections, "right")
            )
        }
        return base.copy(
            title = ai.title.ifBlank { base.title },
            subtitle = ai.subtitle.ifBlank { base.subtitle },
            leftSections = chapterColumns.first,
            centerSections = chapterColumns.second,
            rightSections = chapterColumns.third,
            charts = normalizeCharts(ai.charts, base.charts),
            figures = normalizeFigures(ai.figures, base.figures),
            flowcharts = normalizeFlowcharts(ai.flowcharts, base.flowcharts),
            references = ai.references.ifEmpty { base.references }
        )
    }

    private fun parsePosterAiJson(json: String): PosterAiResponse {
        return runCatching<PosterAiResponse> {
            JsonReader(StringReader(json)).use { reader ->
                reader.isLenient = true
                gson.fromJson(reader, PosterAiResponse::class.java) as PosterAiResponse
            }
        }.getOrElse {
            val root = JsonParser.parseString(json).asJsonObject
            parsePosterAiJsonObject(root)
        }
    }

    private fun extractPosterJsonObject(raw: String): String {
        val withoutFences = raw
            .replace(Regex("```(?:json)?", RegexOption.IGNORE_CASE), "")
            .replace("```", "")
            .replace(Regex("(?is)<think>.*?</think>"), "")
            .trim()
        val candidates = extractBalancedJsonObjects(withoutFences)
        val best = candidates
            .map { repairPosterJson(it) }
            .maxByOrNull { scorePosterJsonCandidate(it) }
        if (!best.isNullOrBlank() && scorePosterJsonCandidate(best) > 0) return best
        return best ?: error("No JSON object found in AI response")
    }

    private fun extractBalancedJsonObjects(text: String): List<String> {
        val candidates = mutableListOf<String>()
        var start = text.indexOf('{')
        while (start >= 0) {
            findBalancedJsonObject(text, start)?.let { candidates += it }
            start = text.indexOf('{', start + 1)
        }
        return candidates
    }

    private fun findBalancedJsonObject(text: String, start: Int): String? {
        var depth = 0
        var inString = false
        var escaped = false
        for (index in start until text.length) {
            val char = text[index]
            when {
                escaped -> escaped = false
                char == '\\' && inString -> escaped = true
                char == '"' -> inString = !inString
                !inString && char == '{' -> depth++
                !inString && char == '}' -> {
                    depth--
                    if (depth == 0) return text.substring(start, index + 1)
                }
            }
        }
        return null
    }

    private fun scorePosterJsonCandidate(json: String): Int {
        return runCatching {
            val root = JsonParser.parseString(json).takeIf { it.isJsonObject }?.asJsonObject ?: return 0
            var score = 0
            if (root.has("title")) score += 1
            if (root.has("subtitle")) score += 1
            if (root.has("chapters")) score += 5
            if (root.has("left_sections") || root.has("center_sections") || root.has("right_sections")) score += 4
            if (root.has("charts")) score += 3
            if (root.has("figures")) score += 3
            if (root.has("flowcharts")) score += 2
            if (root.has("references")) score += 1
            score
        }.getOrDefault(0)
    }

    private fun repairPosterJson(json: String): String {
        return json
            .replace('\u201c', '"')
            .replace('\u201d', '"')
            .replace('\u2018', '\'')
            .replace('\u2019', '\'')
            .replace(Regex(",\\s*([}\\]])"), "$1")
            .replace(Regex("""(?m)([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:""")) { match ->
                "${match.groupValues[1]}\"${match.groupValues[2]}\":"
            }
            .replace(Regex("""'([^'\\]*(?:\\.[^'\\]*)*)'""")) { match ->
                "\"" + match.groupValues[1].replace("\"", "\\\"") + "\""
            }
    }

    private fun parsePosterAiJsonObject(root: JsonObject): PosterAiResponse {
        return PosterAiResponse(
            title = root.stringValue("title"),
            subtitle = root.stringValue("subtitle"),
            chapters = root.sectionList("chapters"),
            leftSections = root.sectionList("left_sections", "leftSections", "left"),
            centerSections = root.sectionList("center_sections", "centerSections", "center"),
            rightSections = root.sectionList("right_sections", "rightSections", "right"),
            charts = root.chartList("charts"),
            figures = root.figureList("figures"),
            flowcharts = root.flowchartList("flowcharts"),
            references = root.stringList("references")
        )
    }

    private fun JsonObject.stringValue(vararg keys: String): String {
        keys.forEach { key ->
            val value = get(key)
            if (value != null && !value.isJsonNull) {
                if (value.isJsonPrimitive) return value.asString.trim()
                return value.toString().trim()
            }
        }
        return ""
    }

    private fun JsonObject.stringList(vararg keys: String): List<String> {
        keys.forEach { key ->
            val value = get(key) ?: return@forEach
            val parsed = value.toStringList()
            if (parsed.isNotEmpty()) return parsed
        }
        return emptyList()
    }

    private fun JsonElement.toStringList(): List<String> {
        if (isJsonNull) return emptyList()
        if (isJsonArray) {
            return asJsonArray.mapNotNull { item ->
                when {
                    item.isJsonNull -> null
                    item.isJsonPrimitive -> item.asString.trim()
                    item.isJsonObject -> item.asJsonObject.stringValue("text", "content", "title", "caption", "value")
                    else -> item.toString()
                }?.takeIf { it.isNotBlank() }
            }
        }
        if (isJsonPrimitive) {
            return asString
                .split('\n', ';')
                .map { it.trim().trimStart('-', '*', '•').trim() }
                .filter { it.isNotBlank() }
        }
        return listOf(toString()).filter { it.isNotBlank() }
    }

    private fun JsonObject.sectionList(vararg keys: String): List<PosterSection> {
        keys.forEach { key ->
            val value = get(key) ?: return@forEach
            val sections = when {
                value.isJsonArray -> value.asJsonArray.mapIndexedNotNull { index, item ->
                    item.toPosterSection("section_${index + 1}")
                }
                value.isJsonObject -> listOfNotNull(value.toPosterSection(key))
                value.isJsonPrimitive -> listOf(PosterSection(title = key.replace('_', ' ').replaceFirstChar { it.uppercase() }, content = value.asString))
                else -> emptyList()
            }
            if (sections.isNotEmpty()) return sections
        }
        return emptyList()
    }

    private fun JsonElement.toPosterSection(defaultTitle: String): PosterSection? {
        return when {
            isJsonObject -> {
                val obj = asJsonObject
                PosterSection(
                    title = obj.stringValue("title", "heading", "section", "name").ifBlank { defaultTitle },
                    content = obj.stringValue("content", "text", "body", "summary", "description"),
                    bullets = obj.stringList("bullets", "bullet_points", "key_points"),
                    subheadings = obj.stringList("subheadings", "sub_headings"),
                    points = obj.stringList("points", "numbered_points", "takeaways"),
                    flowchartSteps = obj.stringList("flowchart_steps", "flowchartSteps", "steps")
                )
            }
            isJsonPrimitive -> PosterSection(title = defaultTitle, content = asString)
            else -> null
        }
    }

    private fun JsonObject.chartList(vararg keys: String): List<PosterChart> {
        keys.forEach { key ->
            val value = get(key) ?: return@forEach
            val charts = when {
                value.isJsonArray -> value.asJsonArray.mapNotNull { item ->
                    item.takeIf { it.isJsonObject }?.asJsonObject?.let { obj ->
                        PosterChart(
                            title = obj.stringValue("title", "name").ifBlank { "Chart" },
                            type = obj.stringValue("type", "chart_type").ifBlank { "bar" },
                            labels = obj.stringList("labels", "categories", "x"),
                            values = obj.floatList("values", "data", "y"),
                            xAxisTitle = obj.stringValue("xAxisTitle", "x_axis_title", "x_axis_label", "xAxisLabel"),
                            yAxisTitle = obj.stringValue("yAxisTitle", "y_axis_title", "y_axis_label", "yAxisLabel")
                        )
                    }
                }
                else -> emptyList()
            }
            if (charts.isNotEmpty()) return charts
        }
        return emptyList()
    }

    private fun JsonObject.floatList(vararg keys: String): List<Float> {
        keys.forEach { key ->
            val value = get(key) ?: return@forEach
            val numbers = when {
                value.isJsonArray -> value.asJsonArray.mapNotNull { item ->
                    item.takeIf { it.isJsonPrimitive }?.asString?.filter { char -> char.isDigit() || char == '.' || char == '-' }?.toFloatOrNull()
                }
                value.isJsonPrimitive -> value.asString.split(',', ';', ' ').mapNotNull { it.trim().toFloatOrNull() }
                else -> emptyList()
            }
            if (numbers.isNotEmpty()) return numbers
        }
        return emptyList()
    }

    private fun JsonObject.figureList(vararg keys: String): List<PosterFigure> {
        keys.forEach { key ->
            val value = get(key) ?: return@forEach
            val figures = value.takeIf { it.isJsonArray }?.asJsonArray?.mapNotNull { item ->
                item.takeIf { it.isJsonObject }?.asJsonObject?.let { obj ->
                    PosterFigure(
                        title = obj.stringValue("title", "name").ifBlank { "Figure" },
                        caption = obj.stringValue("caption", "description", "content"),
                        query = obj.stringValue("query", "image_search_query", "search_query", "imageQuery").ifBlank {
                            obj.stringValue("title", "name")
                        },
                        imageUri = obj.stringValue("imageUri", "image_uri", "image_url", "url")
                    )
                }
            }.orEmpty()
            if (figures.isNotEmpty()) return figures
        }
        return emptyList()
    }

    private fun JsonObject.flowchartList(vararg keys: String): List<PosterFlowchart> {
        keys.forEach { key ->
            val value = get(key) ?: return@forEach
            val flowcharts = value.takeIf { it.isJsonArray }?.asJsonArray?.mapNotNull { item ->
                item.takeIf { it.isJsonObject }?.asJsonObject?.let { obj ->
                    PosterFlowchart(
                        title = obj.stringValue("title", "name").ifBlank { "Flowchart" },
                        steps = obj.stringList("steps", "flowchart_steps", "flowchartSteps"),
                        caption = obj.stringValue("caption", "description")
                    )
                }
            }.orEmpty()
            if (flowcharts.isNotEmpty()) return flowcharts
        }
        return emptyList()
    }

    private fun normalizeAiChapters(chapters: List<PosterSection>): List<PosterSection> {
        return chapters
            .filter { it.title.isNotBlank() && it.content.isNotBlank() }
            .take(12)
            .mapIndexed { index, section ->
                section.copy(
                    id = section.id.ifBlank { "chapter_${index + 1}" },
                    bullets = section.bullets.filter { it.isNotBlank() }.take(4),
                    subheadings = section.subheadings.filter { it.isNotBlank() }.take(5),
                    points = section.points.filter { it.isNotBlank() }.take(6),
                    flowchartSteps = section.flowchartSteps.filter { it.isNotBlank() }.take(8)
                )
            }
    }

    private fun distributePosterChapters(chapters: List<PosterSection>): Triple<List<PosterSection>, List<PosterSection>, List<PosterSection>> {
        val columns = List(3) { mutableListOf<PosterSection>() }
        val weights = FloatArray(3)
        chapters.forEachIndexed { index, chapter ->
            val target = weights.indices.minBy { weights[it] }
            val column = listOf("left", "center", "right")[target]
            columns[target] += chapter.copy(
                id = chapter.id.ifBlank { "${column}_${index + 1}" },
                column = column
            )
            weights[target] += sectionTextWeight(chapter)
        }
        return Triple(columns[0], columns[1], columns[2])
    }

    private fun normalizeSections(aiSections: List<PosterSection>, fallback: List<PosterSection>, column: String): List<PosterSection> {
        val cleaned = aiSections
            .filter { it.title.isNotBlank() && it.content.isNotBlank() }
            .take(3)
            .mapIndexed { index, section ->
                section.copy(
                    id = section.id.ifBlank { "${column}_${index + 1}" },
                    column = column,
                    bullets = section.bullets.filter { it.isNotBlank() }.take(3),
                    subheadings = section.subheadings.filter { it.isNotBlank() }.take(4),
                    points = section.points.filter { it.isNotBlank() }.take(5),
                    flowchartSteps = section.flowchartSteps.filter { it.isNotBlank() }.take(7)
                )
            }
        return (cleaned + fallback.drop(cleaned.size)).take(3).withPlacement(column)
    }

    private fun normalizeCharts(aiCharts: List<PosterChart>, fallback: List<PosterChart>): List<PosterChart> {
        val cleaned = aiCharts.filter {
            it.title.isNotBlank() && it.labels.size >= 2 && it.values.size >= 2
        }.take(4).map { chart ->
            val type = normalizePosterChartType(chart.type)
            chart.copy(
                type = type,
                labels = chart.labels.take(chart.values.size.coerceAtMost(8)),
                values = chart.values.take(8)
            )
        }
        return if (cleaned.size >= 2) cleaned else fallback
    }

    private fun normalizePosterChartType(rawType: String): String {
        val normalized = rawType.lowercase().trim().replace("-", "_").replace(" ", "_")
        return when (normalized) {
            "bar", "bar_chart", "column", "column_chart" -> "bar"
            "histogram", "frequency", "frequency_distribution" -> "histogram"
            "line", "line_graph", "line_chart", "trend", "trend_line" -> "line"
            "pie", "pie_chart", "donut", "doughnut" -> "pie"
            "scatter", "scatter_plot", "scatter_chart" -> "scatter"
            else -> "bar"
        }
    }

    private fun normalizeFigures(aiFigures: List<PosterFigure>, fallback: List<PosterFigure>): List<PosterFigure> {
        val cleaned = aiFigures.filter {
            it.title.isNotBlank() && it.caption.isNotBlank() && it.query.isNotBlank()
        }.take(3)
        return if (cleaned.size >= 2) cleaned else fallback
    }

    private fun normalizeFlowcharts(aiFlowcharts: List<PosterFlowchart>, fallback: List<PosterFlowchart>): List<PosterFlowchart> {
        val cleaned = aiFlowcharts.filter {
            it.title.isNotBlank() && it.steps.count { step -> step.isNotBlank() } >= 3
        }.take(3).map { flowchart ->
            flowchart.copy(
                steps = flowchart.steps.filter { it.isNotBlank() }.take(7)
            )
        }
        return if (cleaned.isNotEmpty()) cleaned else fallback
    }

    private fun List<PosterSection>.withPlacement(column: String): List<PosterSection> {
        return take(3).mapIndexed { index, section ->
            section.copy(id = section.id.ifBlank { "${column}_${index + 1}" }, column = column)
        }
    }

    fun setLogo(uri: Uri?) {
        _uiState.update { it.copy(input = it.input.copy(logoUri = uri?.toString().orEmpty())) }
        saveSessionToFirebase()
    }

    fun setTitleLogo(uri: Uri?) {
        _uiState.update { it.copy(input = it.input.copy(titleLogoUri = uri?.toString().orEmpty())) }
        saveSessionToFirebase()
    }

    fun setBackground(uri: Uri?) {
        _uiState.update { it.copy(input = it.input.copy(backgroundUri = uri?.toString().orEmpty())) }
        saveSessionToFirebase()
    }

    fun setPosterFont(uri: Uri?) {
        _uiState.update { it.copy(input = it.input.copy(fontUri = uri?.toString().orEmpty())) }
        saveSessionToFirebase()
    }

    fun setFigureImage(index: Int, uri: Uri?) {
        _uiState.update { state ->
            val poster = state.poster ?: return@update state
            val figures = poster.figures.mapIndexed { i, figure ->
                if (i == index) figure.copy(imageUri = uri?.toString().orEmpty()) else figure
            }
            state.copy(poster = poster.copy(figures = figures))
        }
        saveSessionToFirebase()
    }

    fun updateFigure(index: Int, title: String? = null, caption: String? = null, query: String? = null) {
        _uiState.update { state ->
            val poster = state.poster ?: return@update state
            val figures = poster.figures.mapIndexed { i, figure ->
                if (i == index) {
                    figure.copy(
                        title = title ?: figure.title,
                        caption = caption ?: figure.caption,
                        query = query ?: figure.query
                    )
                } else figure
            }
            state.copy(poster = poster.copy(figures = figures))
        }
        saveSessionToFirebase()
    }

    fun updateFigurePlacement(index: Int, width: Float? = null, height: Float? = null) {
        _uiState.update { state ->
            val poster = state.poster ?: return@update state
            val figures = poster.figures.mapIndexed { i, figure ->
                if (i == index) {
                    figure.copy(
                        widthPercent = width?.coerceIn(0.22f, 0.95f) ?: figure.widthPercent,
                        heightPercent = height?.coerceIn(0.10f, 0.42f) ?: figure.heightPercent
                    )
                } else figure
            }
            state.copy(poster = poster.copy(figures = figures))
        }
        saveSessionToFirebase()
    }

    fun updateChart(index: Int, title: String? = null, type: String? = null, labelsCsv: String? = null, valuesCsv: String? = null) {
        _uiState.update { state ->
            val poster = state.poster ?: return@update state
            val charts = poster.charts.mapIndexed { i, chart ->
                if (i == index) {
                    chart.copy(
                        title = title ?: chart.title,
                        type = type?.lowercase()?.takeIf { it in setOf("bar", "pie", "line", "scatter", "histogram") } ?: chart.type,
                        labels = labelsCsv?.split(",")?.map { it.trim() }?.filter { it.isNotBlank() } ?: chart.labels,
                        values = valuesCsv?.split(",")?.mapNotNull { it.trim().toFloatOrNull() }?.takeIf { it.isNotEmpty() } ?: chart.values
                    )
                } else chart
            }
            state.copy(poster = poster.copy(charts = charts))
        }
        saveSessionToFirebase()
    }

    fun updateSection(column: String, index: Int, title: String? = null, content: String? = null) {
        _uiState.update { state ->
            val poster = state.poster ?: return@update state
            fun update(list: List<PosterSection>) = list.mapIndexed { i, section ->
                if (i == index) section.copy(title = title ?: section.title, content = content ?: section.content) else section
            }
            state.copy(
                poster = when (column) {
                    "left" -> poster.copy(leftSections = update(poster.leftSections))
                    "center" -> poster.copy(centerSections = update(poster.centerSections))
                    "right" -> poster.copy(rightSections = update(poster.rightSections))
                    else -> poster
                }
            )
        }
        saveSessionToFirebase()
    }

    fun updateFullSection(column: String, index: Int, updatedSection: PosterSection) {
        _uiState.update { state ->
            val poster = state.poster ?: return@update state
            fun update(list: List<PosterSection>) = list.mapIndexed { i, section ->
                if (i == index) updatedSection.copy(
                    id = updatedSection.id.ifBlank { section.id },
                    column = column
                ) else section
            }
            state.copy(
                poster = when (column) {
                    "left" -> poster.copy(leftSections = update(poster.leftSections))
                    "center" -> poster.copy(centerSections = update(poster.centerSections))
                    "right" -> poster.copy(rightSections = update(poster.rightSections))
                    else -> poster
                }
            )
        }
        saveSessionToFirebase()
    }

    fun moveSection(fromColumn: String, index: Int, toColumn: String) {
        if (fromColumn == toColumn) return
        _uiState.update { state ->
            val poster = state.poster ?: return@update state
            val lists = mutableMapOf(
                "left" to poster.leftSections.toMutableList(),
                "center" to poster.centerSections.toMutableList(),
                "right" to poster.rightSections.toMutableList()
            )
            val source = lists[fromColumn] ?: return@update state
            if (index !in source.indices) return@update state
            val section = source.removeAt(index)
            lists[toColumn]?.add(section.copy(column = toColumn))
            state.copy(
                poster = poster.copy(
                    leftSections = lists["left"].orEmpty(),
                    centerSections = lists["center"].orEmpty(),
                    rightSections = lists["right"].orEmpty()
                )
            )
        }
        saveSessionToFirebase()
    }

    fun exportPdf(context: Context, uri: Uri) {
        val poster = _uiState.value.poster ?: return
        val input = _uiState.value.input
        runCatching {
            PDDocument().use { document ->
                val page = PDPage(PDRectangle(1190f, 1684f))
                document.addPage(page)
                PDPageContentStream(document, page).use { cs ->
                    drawPosterPdf(context, document, cs, poster, input, page.mediaBox)
                }
                outputStreamForUri(context, uri).use { document.save(it) }
            }
        }.onSuccess {
            _uiState.update { it.copy(status = "PDF exported") }
            saveSessionToFirebase()
        }.onFailure { error ->
            _uiState.update { it.copy(status = "PDF export failed: ${error.message}") }
        }
    }

    fun exportPng(context: Context, uri: Uri) {
        val poster = _uiState.value.poster ?: return
        val input = _uiState.value.input
        runCatching {
            val bitmap = Bitmap.createBitmap(1600, 2400, Bitmap.Config.ARGB_8888)
            val canvas = AndroidCanvas(bitmap)
            drawPosterBitmap(context, canvas, poster, input, bitmap.width.toFloat(), bitmap.height.toFloat())
            outputStreamForUri(context, uri).use { out ->
                bitmap.compress(Bitmap.CompressFormat.PNG, 100, out)
            }
            bitmap.recycle()
        }.onSuccess {
            _uiState.update { it.copy(status = "PNG exported") }
            saveSessionToFirebase()
        }.onFailure { error ->
            _uiState.update { it.copy(status = "PNG export failed: ${error.message}") }
        }
    }

    private fun outputStreamForUri(context: Context, uri: Uri) =
        if (uri.scheme.equals("file", ignoreCase = true)) {
            FileOutputStream(java.io.File(uri.path ?: error("Invalid file destination")))
        } else {
            context.contentResolver.openOutputStream(uri, "wt") ?: error("Unable to open output stream")
        }

    private fun drawPosterPdf(context: Context, document: PDDocument, cs: PDPageContentStream, poster: PosterData, input: PosterInputState, box: PDRectangle) {
        val width = box.width
        val height = box.height
        val posterTypeface = loadTypefaceFromUri(context, input.fontUri)
        fun color(hex: Int) {
            cs.setNonStrokingColor(android.graphics.Color.red(hex) / 255f, android.graphics.Color.green(hex) / 255f, android.graphics.Color.blue(hex) / 255f)
        }
        fun stroke(hex: Int) {
            cs.setStrokingColor(android.graphics.Color.red(hex) / 255f, android.graphics.Color.green(hex) / 255f, android.graphics.Color.blue(hex) / 255f)
        }
        fun rect(x: Float, y: Float, w: Float, h: Float, fill: Int, line: Int? = null) {
            color(fill); cs.addRect(x, y, w, h); cs.fill()
            line?.let { stroke(it); cs.addRect(x, y, w, h); cs.stroke() }
        }
        fun pdfFont(bold: Boolean) = if (bold) PDType1Font.HELVETICA_BOLD else PDType1Font.HELVETICA
        fun wrapPdfLines(value: String, font: PDType1Font, size: Float, maxWidth: Float): List<String> {
            val words = safePdfText(value).split(Regex("\\s+")).filter { it.isNotBlank() }
            val lines = mutableListOf<String>()
            var current = ""
            words.forEach { word ->
                val candidate = if (current.isBlank()) word else "$current $word"
                val candidateWidth = runCatching { font.getStringWidth(candidate) / 1000f * size }.getOrDefault(candidate.length * size * 0.5f)
                if (candidateWidth <= maxWidth || current.isBlank()) {
                    current = candidate
                } else {
                    lines += current
                    current = word
                }
            }
            if (current.isNotBlank()) lines += current
            return lines
        }
        fun text(value: String, x: Float, y: Float, size: Float, bold: Boolean = false, maxWidth: Float = width - x - 24f, maxLines: Int = 1, textColor: Int = android.graphics.Color.parseColor("#172033")) {
            val font = pdfFont(bold)
            wrapPdfLines(value, font, size, maxWidth).take(maxLines).forEachIndexed { index, line ->
            cs.beginText()
                cs.setFont(font, size)
            color(textColor)
                cs.newLineAtOffset(x, y - index * size * 1.25f)
                cs.showText(line)
            cs.endText()
            }
        }
        rect(0f, 0f, width, height, 0xFFF6F8FB.toInt())
        loadBitmapFromUri(context, input.backgroundUri)?.let { bg ->
            val image = LosslessFactory.createFromImage(document, bg)
            cs.drawImage(image, 0f, 0f, width, height)
            bg.recycle()
            rect(0f, 0f, width, height, 0xEEF6F8FB.toInt())
        }
        rect(24f, height - 116f, width - 48f, 92f, 0xFF0B5CAD.toInt())
        val titleColor = androidColorFromHex(input.titleColor, android.graphics.Color.WHITE)
        val footerColor = androidColorFromHex(input.footerColor, android.graphics.Color.WHITE)
        text(poster.title, 96f, height - 56f, 22f, true, width - 210f, 2, titleColor)
        text(poster.subtitle, 96f, height - 88f, 10f, false, width - 210f, 1, titleColor)
        text(poster.authorLine, 96f, height - 105f, 9f, false, width - 210f, 1, titleColor)
        rect(42f, height - 94f, 42f, 42f, 0xFFFFFFFF.toInt())
        loadBitmapFromUri(context, input.logoUri)?.let { logo ->
            val image = LosslessFactory.createFromImage(document, logo)
            cs.drawImage(image, 44f, height - 92f, 38f, 38f)
            logo.recycle()
        }
        rect(width - 84f, height - 94f, 42f, 42f, 0xFFFFFFFF.toInt())
        loadBitmapFromUri(context, input.titleLogoUri)?.let { logo ->
            val image = LosslessFactory.createFromImage(document, logo)
            cs.drawImage(image, width - 82f, height - 92f, 38f, 38f)
            logo.recycle()
        }

        val top = height - 150f
        val margin = 28f
        val gap = 12f
        val colW = (width - margin * 2f - gap * 2f) / 3f
        val visualColumns = distributePosterVisuals(context, poster.charts, poster.figures, poster.flowcharts)
        val contentBottom = 56f
        drawPdfColumn(context, document, cs, poster.leftSections, visualColumns[0], margin, top, contentBottom, colW, posterTypeface, input)
        val centerX = margin + colW + gap
        drawPdfColumn(context, document, cs, poster.centerSections, visualColumns[1], centerX, top, contentBottom, colW, posterTypeface, input)
        val rightX = margin + (colW + gap) * 2f
        drawPdfColumn(context, document, cs, poster.rightSections, visualColumns[2], rightX, top, contentBottom, colW, posterTypeface, input)
        text("Charts and figures are required: ${poster.charts.size} charts, ${poster.figures.size} figures", margin, 34f, 8f, true, width - margin * 2f, 1, footerColor)
        text(listOf(poster.guideLine, poster.contact).filter { it.isNotBlank() }.joinToString(" | "), margin, 20f, 8f, false, width - margin * 2f, 1, footerColor)
        text(poster.institution, width / 2f - 120f, 8f, 7f, false, 240f, 1, footerColor)
    }

    private fun drawPdfColumn(
        context: Context,
        document: PDDocument,
        cs: PDPageContentStream,
        sections: List<PosterSection>,
        visualColumn: PosterVisualColumn,
        x: Float,
        top: Float,
        bottom: Float,
        width: Float,
        typeface: Typeface?,
        input: PosterInputState
    ) {
        var y = top
        val headingColor = androidColorFromHex(input.headingColor, android.graphics.Color.parseColor("#0B5CAD"))
        val subheadingColor = androidColorFromHex(input.subheadingColor, android.graphics.Color.parseColor("#172033"))
        val bodyColor = androidColorFromHex(input.bodyColor, android.graphics.Color.parseColor("#172033"))
        val pointColor = androidColorFromHex(input.pointColor, android.graphics.Color.parseColor("#0B5CAD"))
        fun setTextColor(color: Int) {
            cs.setNonStrokingColor(
                android.graphics.Color.red(color) / 255f,
                android.graphics.Color.green(color) / 255f,
                android.graphics.Color.blue(color) / 255f
            )
        }
        val visualItems = visualColumn.itemsBySlot.flatMap { it.value }
        val layoutHeight = top - bottom
        val minSectionHeight = 58f
        val visualHeights = scaledPosterVisualHeights(
            items = visualItems,
            preferredHeight = { posterVisualHeightPdf(context, it, width) },
            maxTotalHeight = (layoutHeight - sections.size * minSectionHeight).coerceAtLeast(layoutHeight * 0.62f)
        )
        val visualTotalHeight = visualHeights.values.sum()
        val sectionHeights = allocatePosterSectionHeights(
            sections = sections,
            availableHeight = (layoutHeight - visualTotalHeight).coerceAtLeast(sections.size * minSectionHeight),
            minHeight = minSectionHeight
        )
        fun drawVisual(item: PosterVisualItem) {
            val visualHeight = visualHeights[item] ?: posterVisualHeightPdf(context, item, width)
            val cardHeight = (visualHeight - 8f).coerceAtLeast(72f)
            when (item) {
                is PosterVisualItem.ChartItem -> {
                    val chartBitmap = renderChartBitmap(item.chart, 900, 520, typeface)
                    val image = LosslessFactory.createFromImage(document, chartBitmap)
                    cs.drawImage(image, x, y - cardHeight, width, cardHeight)
                    chartBitmap.recycle()
                    y -= visualHeight
                }
                is PosterVisualItem.FlowchartItem -> {
                    val flowchart = item.flowchart
                    cs.setNonStrokingColor(1f, 1f, 1f)
                    cs.addRect(x, y - cardHeight, width, cardHeight)
                    cs.fill()
                    cs.setStrokingColor(0.68f, 0.77f, 0.87f)
                    cs.addRect(x, y - cardHeight, width, cardHeight)
                    cs.stroke()
                    var titleY = y - 18f
                    wrapPosterPdfText(flowchart.title, PDType1Font.HELVETICA_BOLD, 9f, width - 20f).take(2).forEach { line ->
                        cs.beginText()
                        cs.setFont(PDType1Font.HELVETICA_BOLD, 9f)
                        setTextColor(headingColor)
                        cs.newLineAtOffset(x + 10f, titleY)
                        cs.showText(safePdfText(line))
                        cs.endText()
                        titleY -= 11f
                    }
                    val columns = if (cardHeight > 138f) 1 else 2
                    val stepWidth = if (columns == 1) width - 24f else width * 0.42f
                    val stepsTop = titleY - 12f
                    flowchart.steps.take(if (columns == 1) 7 else 5).forEachIndexed { index, step ->
                        val sx = x + 12f + (index % columns) * (width * 0.48f)
                        val sy = stepsTop - (index / columns) * 22f
                        cs.setNonStrokingColor(0.91f, 0.96f, 1f)
                        cs.addRect(sx, sy - 12f, stepWidth, 16f)
                        cs.fill()
                        setTextColor(pointColor)
                        cs.addRect(sx + 3f, sy - 10f, 12f, 12f)
                        cs.fill()
                        cs.beginText()
                        cs.setFont(PDType1Font.HELVETICA_BOLD, 6.2f)
                        cs.setNonStrokingColor(1f, 1f, 1f)
                        cs.newLineAtOffset(sx + 6.5f, sy - 6.5f)
                        cs.showText("${index + 1}")
                        cs.endText()
                        cs.beginText()
                        cs.setFont(PDType1Font.HELVETICA, 6.4f)
                        setTextColor(bodyColor)
                        cs.newLineAtOffset(sx + 19f, sy - 6f)
                        cs.showText(safePdfText(wrapPosterPdfText(step, PDType1Font.HELVETICA, 6.4f, stepWidth - 24f).firstOrNull().orEmpty()))
                        cs.endText()
                    }
                    y -= visualHeight
                }
                is PosterVisualItem.FigureItem -> {
                    val figure = item.figure
                    cs.setNonStrokingColor(1f, 1f, 1f)
                    cs.addRect(x, y - cardHeight, width, cardHeight)
                    cs.fill()
                    cs.setStrokingColor(0.68f, 0.77f, 0.87f)
                    cs.addRect(x, y - cardHeight, width, cardHeight)
                    cs.stroke()
                    val titleLines = wrapPosterPdfText(figure.title, PDType1Font.HELVETICA_BOLD, 9f, width - 20f).take(2)
                    val imageTop = y - 18f - titleLines.size * 10f - 10f
                    val captionLines = wrapPosterPdfText(figure.caption, PDType1Font.HELVETICA, 7.2f, width - 20f).take(3)
                    val imageHeight = (imageTop - (y - cardHeight) - 22f - captionLines.size * 10f).coerceAtLeast(42f)
                    loadBitmapFromUri(context, figure.imageUri)?.let { bitmap ->
                        val image = LosslessFactory.createFromImage(document, bitmap)
                        cs.drawImage(image, x + 8f, imageTop - imageHeight, width - 16f, imageHeight)
                        bitmap.recycle()
                    }
                    var figureTitleY = y - 18f
                    titleLines.forEach { line ->
                        cs.beginText()
                        cs.setFont(PDType1Font.HELVETICA_BOLD, 9f)
                        setTextColor(headingColor)
                        cs.newLineAtOffset(x + 10f, figureTitleY)
                        cs.showText(safePdfText(line))
                        cs.endText()
                        figureTitleY -= 10f
                    }
                    captionLines.forEachIndexed { index, line ->
                        cs.beginText()
                        cs.setFont(PDType1Font.HELVETICA, 7.2f)
                        setTextColor(bodyColor)
                        cs.newLineAtOffset(x + 10f, imageTop - imageHeight - 12f - index * 10f)
                        cs.showText(safePdfText(line))
                        cs.endText()
                    }
                    y -= visualHeight
                }
            }
        }

        visualColumn.itemsBySlot[0].orEmpty().forEach(::drawVisual)
        sections.forEachIndexed { sectionIndex, section ->
            val sectionHeight = sectionHeights.getOrElse(sectionIndex) { 104f }
            val rectHeight = (sectionHeight - 8f).coerceAtLeast(58f)
            val rectBottom = y - rectHeight
            cs.setNonStrokingColor(1f, 1f, 1f)
            cs.addRect(x, rectBottom, width, rectHeight)
            cs.fill()
            cs.setStrokingColor(0.68f, 0.77f, 0.87f)
            cs.addRect(x, rectBottom, width, rectHeight)
            cs.stroke()
            var lineY = y - 20f
            wrapPosterPdfText(section.title, PDType1Font.HELVETICA_BOLD, 10f, width - 20f).take(2).forEach { line ->
                cs.beginText()
                cs.setFont(PDType1Font.HELVETICA_BOLD, 10f)
                setTextColor(headingColor)
                cs.newLineAtOffset(x + 10f, lineY)
                cs.showText(safePdfText(line))
                cs.endText()
                lineY -= 12f
            }
            lineY -= 4f
            section.subheadings.take(2).forEach { subheading ->
                wrapPosterPdfText(subheading, PDType1Font.HELVETICA_BOLD, 7.2f, width - 20f).take(2).forEach { line ->
                    cs.beginText()
                    cs.setFont(PDType1Font.HELVETICA_BOLD, 7.2f)
                    setTextColor(subheadingColor)
                    cs.newLineAtOffset(x + 10f, lineY)
                    cs.showText(safePdfText(line))
                    cs.endText()
                    lineY -= 9f
                }
            }
            val contentLineBudget = ((lineY - rectBottom - 20f) / 9f).toInt().coerceAtLeast(1)
            val sectionPoints = (section.points + section.bullets).map(::stripPosterMarkdown).filter { it.isNotBlank() }.distinct().take(4)
            val contentLines = wrapPosterPdfText(stripPosterMarkdown(section.content), PDType1Font.HELVETICA, 7.2f, width - 20f)
            val reservedPointLines = sectionPoints.take(3).size
            contentLines.take((contentLineBudget - reservedPointLines).coerceAtLeast(1)).forEach { line ->
                cs.beginText()
                cs.setFont(PDType1Font.HELVETICA, 7.2f)
                setTextColor(bodyColor)
                cs.newLineAtOffset(x + 10f, lineY)
                cs.showText(safePdfText(line))
                cs.endText()
                lineY -= 9f
            }
            sectionPoints.take(3).takeWhile { lineY > rectBottom + 14f }.forEach { point ->
                wrapPosterPdfText("- $point", PDType1Font.HELVETICA, 6.8f, width - 24f)
                    .takeWhile { lineY > rectBottom + 14f }
                    .take(2)
                    .forEach { line ->
                        cs.beginText()
                        cs.setFont(PDType1Font.HELVETICA, 6.8f)
                        setTextColor(pointColor)
                        cs.newLineAtOffset(x + 12f, lineY)
                        cs.showText(safePdfText(line))
                        cs.endText()
                        lineY -= 8f
                    }
            }
            y -= sectionHeight
            visualColumn.itemsBySlot[sectionIndex + 1].orEmpty().forEach(::drawVisual)
        }
        visualColumn.trailingItemsAfterSectionCount(sections.size).forEach(::drawVisual)
    }

    private fun drawPosterBitmap(context: Context, canvas: AndroidCanvas, poster: PosterData, input: PosterInputState, width: Float, height: Float) {
        val paint = Paint(Paint.ANTI_ALIAS_FLAG)
        val posterTypeface = loadTypefaceFromUri(context, input.fontUri)
        paint.color = android.graphics.Color.parseColor("#F6F8FB")
        canvas.drawRect(0f, 0f, width, height, paint)
        loadBitmapFromUri(context, input.backgroundUri)?.let { bg ->
            canvas.drawBitmap(bg, null, RectF(0f, 0f, width, height), paint)
            paint.color = 0xDDF6F8FB.toInt()
            canvas.drawRect(0f, 0f, width, height, paint)
            bg.recycle()
        }
        paint.color = android.graphics.Color.parseColor("#0B5CAD")
        canvas.drawRoundRect(RectF(60f, 50f, width - 60f, 230f), 18f, 18f, paint)
        loadBitmapFromUri(context, input.logoUri)?.let { logo ->
            canvas.drawBitmap(logo, null, RectF(76f, 74f, 146f, 144f), paint)
            logo.recycle()
        }
        loadBitmapFromUri(context, input.titleLogoUri)?.let { logo ->
            canvas.drawBitmap(logo, null, RectF(width - 146f, 74f, width - 76f, 144f), paint)
            logo.recycle()
        }
        paint.color = androidColorFromHex(input.titleColor, android.graphics.Color.WHITE)
        paint.textSize = 54f
        paint.typeface = posterTypeface?.let { Typeface.create(it, Typeface.BOLD) } ?: android.graphics.Typeface.DEFAULT_BOLD
        wrapPosterPaintText(poster.title, paint, width - 340f).take(2).forEachIndexed { index, line ->
            canvas.drawText(line, 170f, 118f + index * 56f, paint)
        }
        paint.textSize = 25f
        paint.typeface = posterTypeface ?: android.graphics.Typeface.DEFAULT
        wrapPosterPaintText(poster.authorLine, paint, width - 340f).take(1).forEachIndexed { index, line ->
            canvas.drawText(line, 170f, 204f + index * 30f, paint)
        }

        val margin = 70f
        val gap = 34f
        val colW = (width - margin * 2f - gap * 2f) / 3f
        val visualColumns = distributePosterVisuals(context, poster.charts, poster.figures, poster.flowcharts)
        val contentBottom = height - 170f
        drawBitmapColumn(context, canvas, poster.leftSections, visualColumns[0], margin, 280f, contentBottom, colW, paint, posterTypeface, input)
        val centerX = margin + colW + gap
        drawBitmapColumn(context, canvas, poster.centerSections, visualColumns[1], centerX, 280f, contentBottom, colW, paint, posterTypeface, input)
        val rightX = margin + (colW + gap) * 2f
        drawBitmapColumn(context, canvas, poster.rightSections, visualColumns[2], rightX, 280f, contentBottom, colW, paint, posterTypeface, input)
        paint.color = android.graphics.Color.parseColor("#0B5CAD")
        canvas.drawRoundRect(RectF(60f, height - 150f, width - 60f, height - 60f), 18f, 18f, paint)
        paint.color = androidColorFromHex(input.footerColor, android.graphics.Color.WHITE)
        paint.textSize = 24f
        paint.typeface = posterTypeface?.let { Typeface.create(it, Typeface.BOLD) } ?: android.graphics.Typeface.DEFAULT_BOLD
        canvas.drawText(listOf(poster.guideLine, poster.contact).filter { it.isNotBlank() }.joinToString(" | ").take(92), 90f, height - 105f, paint)
        paint.textSize = 20f
        paint.typeface = posterTypeface ?: android.graphics.Typeface.DEFAULT
        canvas.drawText(poster.institution.take(105), 90f, height - 75f, paint)
    }

    private fun drawBitmapColumn(context: Context, canvas: AndroidCanvas, sections: List<PosterSection>, visualColumn: PosterVisualColumn, x: Float, yStart: Float, bottom: Float, width: Float, paint: Paint, typeface: Typeface?, input: PosterInputState) {
        var y = yStart
        val headingColor = androidColorFromHex(input.headingColor, android.graphics.Color.parseColor("#0B5CAD"))
        val subheadingColor = androidColorFromHex(input.subheadingColor, android.graphics.Color.parseColor("#172033"))
        val bodyColor = androidColorFromHex(input.bodyColor, android.graphics.Color.parseColor("#172033"))
        val pointColor = androidColorFromHex(input.pointColor, android.graphics.Color.parseColor("#0B5CAD"))
        val visualItems = visualColumn.itemsBySlot.flatMap { it.value }
        val layoutHeight = bottom - yStart
        val minSectionHeight = 125f
        val visualHeights = scaledPosterVisualHeights(
            items = visualItems,
            preferredHeight = { posterVisualHeightBitmap(context, it, width) },
            maxTotalHeight = (layoutHeight - sections.size * minSectionHeight).coerceAtLeast(layoutHeight * 0.62f)
        )
        val visualTotalHeight = visualHeights.values.sum()
        val sectionHeights = allocatePosterSectionHeights(
            sections = sections,
            availableHeight = (layoutHeight - visualTotalHeight).coerceAtLeast(sections.size * minSectionHeight),
            minHeight = minSectionHeight
        )
        fun drawVisual(item: PosterVisualItem) {
            val visualHeight = visualHeights[item] ?: posterVisualHeightBitmap(context, item, width)
            val cardHeight = (visualHeight - 20f).coerceAtLeast(150f)
            when (item) {
                is PosterVisualItem.ChartItem -> {
                    val chartBitmap = renderChartBitmap(item.chart, 900, 520, typeface)
                    canvas.drawBitmap(chartBitmap, null, RectF(x, y, x + width, y + cardHeight), paint)
                    chartBitmap.recycle()
                    y += visualHeight
                }
                is PosterVisualItem.FlowchartItem -> {
                    val flowchart = item.flowchart
                    paint.color = android.graphics.Color.WHITE
                    canvas.drawRoundRect(RectF(x, y, x + width, y + cardHeight), 16f, 16f, paint)
                    paint.color = headingColor
                    paint.textSize = 25f
                    paint.typeface = typeface?.let { Typeface.create(it, Typeface.BOLD) } ?: android.graphics.Typeface.DEFAULT_BOLD
                    var titleY = y + 36f
                    wrapPosterPaintText(flowchart.title, paint, width - 48f).take(2).forEach { line ->
                        canvas.drawText(line, x + 24f, titleY, paint)
                        titleY += 28f
                    }
                    paint.typeface = typeface ?: android.graphics.Typeface.DEFAULT
                    paint.textSize = 17f
                    val columns = if (cardHeight > 250f) 1 else 2
                    val stepWidth = if (columns == 1) width - 48f else width * 0.40f
                    val stepsTop = titleY + 10f
                    flowchart.steps.take(if (columns == 1) 7 else 5).forEachIndexed { index, step ->
                        val sx = x + 24f + (index % columns) * (width * 0.47f)
                        val sy = stepsTop + (index / columns) * 44f
                        paint.color = android.graphics.Color.parseColor("#E7F2FF")
                        canvas.drawRoundRect(RectF(sx, sy, sx + stepWidth, sy + 32f), 10f, 10f, paint)
                        paint.color = pointColor
                        canvas.drawCircle(sx + 17f, sy + 16f, 12f, paint)
                        paint.color = android.graphics.Color.WHITE
                        paint.textSize = 14f
                        paint.typeface = typeface?.let { Typeface.create(it, Typeface.BOLD) } ?: android.graphics.Typeface.DEFAULT_BOLD
                        canvas.drawText("${index + 1}", sx + 13f, sy + 21f, paint)
                        paint.color = bodyColor
                        paint.textSize = 17f
                        paint.typeface = typeface ?: android.graphics.Typeface.DEFAULT
                        wrapPosterPaintText(step, paint, stepWidth - 44f).take(1).forEach { line ->
                            canvas.drawText(line, sx + 38f, sy + 22f, paint)
                        }
                    }
                    y += visualHeight
                }
                is PosterVisualItem.FigureItem -> {
                    val figure = item.figure
                    paint.color = android.graphics.Color.WHITE
                    canvas.drawRoundRect(RectF(x, y, x + width, y + cardHeight), 16f, 16f, paint)
                    val captionLines = wrapPosterPaintText(figure.caption, paint.apply {
                        textSize = 18f
                        this.typeface = typeface ?: android.graphics.Typeface.DEFAULT
                    }, width - 48f).take(3)
                    paint.color = headingColor
                    paint.textSize = 25f
                    paint.typeface = typeface?.let { Typeface.create(it, Typeface.BOLD) } ?: android.graphics.Typeface.DEFAULT_BOLD
                    val titleLines = wrapPosterPaintText(figure.title, paint, width - 48f).take(2)
                    val imageTop = y + 18f + titleLines.size * 26f + 14f
                    val imageBottom = (y + cardHeight - 38f - captionLines.size * 22f)
                        .coerceAtLeast(imageTop + 54f)
                        .coerceAtMost(y + cardHeight - 24f)
                    paint.color = android.graphics.Color.parseColor("#E7F2FF")
                    canvas.drawRoundRect(RectF(x + 20f, imageTop, x + width - 20f, imageBottom), 12f, 12f, paint)
                    loadBitmapFromUri(context, figure.imageUri)?.let { bitmap ->
                        canvas.drawBitmap(bitmap, null, RectF(x + 20f, imageTop, x + width - 20f, imageBottom), paint)
                        bitmap.recycle()
                    }
                    var figureTitleY = y + 34f
                    titleLines.forEach { line ->
                        canvas.drawText(line, x + 24f, figureTitleY, paint)
                        figureTitleY += 26f
                    }
                    paint.color = bodyColor
                    paint.textSize = 18f
                    paint.typeface = typeface ?: android.graphics.Typeface.DEFAULT
                    captionLines.forEachIndexed { index, line ->
                        canvas.drawText(line, x + 24f, imageBottom + 24f + index * 22f, paint)
                    }
                    y += visualHeight
                }
            }
        }

        visualColumn.itemsBySlot[0].orEmpty().forEach(::drawVisual)
        sections.forEachIndexed { sectionIndex, section ->
            val sectionHeight = sectionHeights.getOrElse(sectionIndex) { 260f }
            val cardHeight = (sectionHeight - 30f).coerceAtLeast(145f)
            paint.color = android.graphics.Color.WHITE
            canvas.drawRoundRect(RectF(x, y, x + width, y + cardHeight), 16f, 16f, paint)
            paint.color = headingColor
            paint.textSize = 27f
            paint.typeface = typeface?.let { Typeface.create(it, Typeface.BOLD) } ?: android.graphics.Typeface.DEFAULT_BOLD
            var titleY = y + 42f
            wrapPosterPaintText(section.title, paint, width - 48f).take(2).forEach { line ->
                canvas.drawText(line, x + 24f, titleY, paint)
                titleY += 30f
            }
            paint.color = bodyColor
            paint.textSize = 20f
            paint.typeface = typeface ?: android.graphics.Typeface.DEFAULT
            var textY = titleY + 4f
            section.subheadings.take(2).forEach { subheading ->
                paint.typeface = typeface?.let { Typeface.create(it, Typeface.BOLD) } ?: android.graphics.Typeface.DEFAULT_BOLD
                paint.color = subheadingColor
                wrapPosterPaintText(subheading, paint, width - 48f).take(2).forEach { line ->
                    canvas.drawText(line, x + 24f, textY, paint)
                    textY += 24f
                }
            }
            paint.typeface = typeface ?: android.graphics.Typeface.DEFAULT
            paint.color = bodyColor
            val lineBudget = ((y + cardHeight - textY - 36f) / 24f).toInt().coerceAtLeast(1)
            val sectionPoints = (section.points + section.bullets).map(::stripPosterMarkdown).filter { it.isNotBlank() }.distinct().take(4)
            val pointReserve = sectionPoints.take(3).size
            wrapPosterPaintText(stripPosterMarkdown(section.content), paint, width - 48f).take((lineBudget - pointReserve).coerceAtLeast(1)).forEach { line ->
                canvas.drawText(line, x + 24f, textY, paint)
                textY += 24f
            }
            sectionPoints.take(3).takeWhile { textY < y + cardHeight - 16f }.forEach { point ->
                paint.color = pointColor
                wrapPosterPaintText("- $point", paint, width - 56f)
                    .takeWhile { textY < y + cardHeight - 16f }
                    .take(2)
                    .forEach { line ->
                        canvas.drawText(line, x + 28f, textY, paint)
                        textY += 22f
                    }
            }
            y += sectionHeight
            visualColumn.itemsBySlot[sectionIndex + 1].orEmpty().forEach(::drawVisual)
        }
        visualColumn.trailingItemsAfterSectionCount(sections.size).forEach(::drawVisual)
    }
}

class PosterAnalysisActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        PDFBoxResourceLoader.init(applicationContext)
        val thesisPayloadJson = intent.getStringExtra(EXTRA_THESIS_POSTER_PAYLOAD).orEmpty()
        val autoGenerateFromThesis = intent.getBooleanExtra(EXTRA_AUTO_GENERATE_POSTER, false)
        setContent {
            ThesisExtractorTheme(darkTheme = isSystemInDarkTheme()) {
                Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                    val posterViewModel: PosterAnalysisViewModel = viewModel()
                    LaunchedEffect(thesisPayloadJson, autoGenerateFromThesis) {
                        if (thesisPayloadJson.isNotBlank()) {
                            posterViewModel.importThesisPayload(thesisPayloadJson, autoGenerateFromThesis)
                        }
                    }
                    PosterAnalysisScreen(viewModel = posterViewModel)
                }
            }
        }
    }

    companion object {
        const val EXTRA_THESIS_POSTER_PAYLOAD = "extra_thesis_poster_payload"
        const val EXTRA_AUTO_GENERATE_POSTER = "extra_auto_generate_poster"
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PosterAnalysisScreen(viewModel: PosterAnalysisViewModel = viewModel()) {
    val state by viewModel.uiState.collectAsState()
    val context = LocalContext.current
    var showSessionsDialog by rememberSaveable { mutableStateOf(false) }
    var showAiSettingsDialog by rememberSaveable { mutableStateOf(false) }
    val pdfExport = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/pdf")) { uri ->
        uri?.let { viewModel.exportPdf(context, it) }
    }
    val pngExport = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("image/png")) { uri ->
        uri?.let { viewModel.exportPng(context, it) }
    }
    val logoPicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        uri?.let {
            context.contentResolver.takePersistableUriPermission(it, android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION)
            viewModel.setLogo(it)
        }
    }
    val backgroundPicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        uri?.let {
            context.contentResolver.takePersistableUriPermission(it, android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION)
            viewModel.setBackground(it)
        }
    }
    val titleLogoPicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        uri?.let {
            context.contentResolver.takePersistableUriPermission(it, android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION)
            viewModel.setTitleLogo(it)
        }
    }
    val fontPicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        uri?.let {
            context.contentResolver.takePersistableUriPermission(it, android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION)
            viewModel.setPosterFont(it)
        }
    }
    var pendingFigureIndex by rememberSaveable { mutableStateOf(-1) }
    val figurePicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (pendingFigureIndex >= 0) {
            uri?.let {
                context.contentResolver.takePersistableUriPermission(it, android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION)
                viewModel.setFigureImage(pendingFigureIndex, it)
            }
            pendingFigureIndex = -1
        }
    }
    var selectedTab by rememberSaveable { mutableStateOf(0) }
    val tabs = listOf("Chapters", "Figures", "Charts", "Preview")

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("PosterAnalysis") },
                actions = {
                    IconButton(onClick = { showAiSettingsDialog = true }) {
                        Icon(Icons.Default.Settings, contentDescription = "AI settings")
                    }
                    IconButton(onClick = viewModel::createNewSession) {
                        Icon(Icons.Default.Add, contentDescription = "New poster session")
                    }
                    IconButton(onClick = {
                        viewModel.loadPreviousSessions()
                        showSessionsDialog = true
                    }) {
                        Icon(Icons.Default.FolderOpen, contentDescription = "Previous poster sessions")
                    }
                    TextButton(onClick = viewModel::saveSessionToFirebase) {
                        Text("Save")
                    }
                    Button(onClick = { pdfExport.launch("PosterAnalysis_${System.currentTimeMillis()}.pdf") }, enabled = state.poster != null) {
                        Icon(Icons.Default.PictureAsPdf, contentDescription = null)
                        Spacer(Modifier.width(6.dp))
                        Text("PDF")
                    }
                    Spacer(Modifier.width(8.dp))
                    Button(onClick = { pngExport.launch("PosterAnalysis_${System.currentTimeMillis()}.png") }, enabled = state.poster != null) {
                        Icon(Icons.Default.Download, contentDescription = null)
                        Spacer(Modifier.width(6.dp))
                        Text("PNG")
                    }
                }
            )
        },
        bottomBar = {
            AndroidView(
                modifier = Modifier.fillMaxWidth(),
                factory = { viewContext ->
                    BottomNavigationView(viewContext).apply {
                        inflateMenu(R.menu.bottom_nav_menu)
                        (context as? android.app.Activity)?.let { activity ->
                            AppBottomNavigation.setup(activity, this, R.id.nav_reels)
                        }
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            ScrollableTabRow(selectedTabIndex = selectedTab) {
                tabs.forEachIndexed { index, title ->
                    Tab(selected = selectedTab == index, onClick = { selectedTab = index }, text = { Text(title) })
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp)) {
                AssistChip(onClick = {}, label = { Text(state.status) })
                AssistChip(onClick = {}, label = { Text("Portrait poster") })
                AssistChip(onClick = {}, label = { Text("Charts: ${state.poster?.charts?.size ?: 0}") })
                AssistChip(onClick = {}, label = { Text("Figures: ${state.poster?.figures?.size ?: 0}") })
                AssistChip(onClick = {}, label = { Text("AI: ${state.selectedProvider}") })
                AssistChip(onClick = {}, label = { Text("Session: ${state.sessionId.takeLast(8)}") })
            }
            when (selectedTab) {
                0 -> PosterChaptersTab(
                    state = state,
                    update = viewModel::updateInput,
                    generate = viewModel::generatePoster,
                    rebuildFromThesis = viewModel::rebuildPosterFromSelectedThesisChapters,
                    toggleThesisChapter = viewModel::toggleThesisChapterForPoster,
                    onUpdateSection = viewModel::updateSection,
                    onUpdateFullSection = viewModel::updateFullSection,
                    onMoveSection = viewModel::moveSection
                )
                1 -> PosterFiguresTab(
                    input = state.input,
                    poster = state.poster,
                    pickCollegeLogo = { logoPicker.launch(arrayOf("image/*")) },
                    pickTitleLogo = { titleLogoPicker.launch(arrayOf("image/*")) },
                    pickBackground = { backgroundPicker.launch(arrayOf("image/*")) },
                    pickFont = { fontPicker.launch(arrayOf("font/ttf", "font/otf", "application/x-font-ttf", "application/octet-stream", "*/*")) },
                    pickFigure = { index ->
                        pendingFigureIndex = index
                        figurePicker.launch(arrayOf("image/*"))
                    },
                    onUpdateFigure = viewModel::updateFigure,
                    onResizeFigure = viewModel::updateFigurePlacement
                )
                2 -> PosterChartsTab(
                    charts = state.poster?.charts.orEmpty(),
                    fontUri = state.input.fontUri,
                    onUpdateChart = viewModel::updateChart
                )
                else -> state.poster?.let {
                    LazyColumn(Modifier.fillMaxSize().padding(14.dp)) {
                        item {
                            PosterPreview(
                                poster = it,
                                logoUri = state.input.logoUri,
                                titleLogoUri = state.input.titleLogoUri,
                                backgroundUri = state.input.backgroundUri,
                                fontUri = state.input.fontUri,
                                input = state.input,
                                onUpdateSection = viewModel::updateSection,
                                onUpdateFullSection = viewModel::updateFullSection,
                                onMoveSection = viewModel::moveSection
                            )
                        }
                    }
                } ?: EmptyPosterPreview()
            }
        }
    }
    if (showSessionsDialog) {
        PosterSessionsDialog(
            sessions = state.previousSessions,
            onDismiss = { showSessionsDialog = false },
            onOpen = { sessionId ->
                viewModel.loadSession(sessionId)
                showSessionsDialog = false
            }
        )
    }
    if (showAiSettingsDialog) {
        PosterAiSettingsDialog(
            selectedProvider = state.selectedProvider,
            onProviderSelected = viewModel::setProvider,
            onDismiss = { showAiSettingsDialog = false }
        )
    }
}

private fun posterAiProviderOptions(): List<String> = listOf(
    "auto",
    "openrouter",
    "deepseek",
    "groq",
    "mistral",
    "cerebras",
    "huggingface"
)

@Composable
private fun PosterAiSettingsDialog(
    selectedProvider: String,
    onProviderSelected: (String) -> Unit,
    onDismiss: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("AI Settings") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Poster Analysis provider", style = MaterialTheme.typography.labelLarge)
                posterAiProviderOptions().forEach { provider ->
                    val selected = provider == selectedProvider
                    OutlinedButton(
                        modifier = Modifier.fillMaxWidth(),
                        onClick = { onProviderSelected(provider) },
                        enabled = !selected
                    ) {
                        Text(if (selected) "$provider selected" else provider)
                    }
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) {
                Text("Done")
            }
        }
    )
}

@Composable
private fun PosterSessionsDialog(
    sessions: List<PosterSessionItem>,
    onDismiss: () -> Unit,
    onOpen: (String) -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Poster Sessions") },
        text = {
            if (sessions.isEmpty()) {
                Text("No saved poster sessions found.")
            } else {
                LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(sessions.size) { index ->
                        val session = sessions[index]
                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { onOpen(session.sessionId) },
                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                        ) {
                            Column(Modifier.padding(10.dp)) {
                                Text(session.title.ifBlank { "Untitled poster" }, fontWeight = FontWeight.Bold)
                                Text("Sections: ${session.sectionsCount} | Session: ${session.sessionId.takeLast(10)}", style = MaterialTheme.typography.bodySmall)
                                Text(java.util.Date(session.timestamp).toString(), style = MaterialTheme.typography.labelSmall)
                            }
                        }
                    }
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) {
                Text("Close")
            }
        }
    )
}

@Composable
private fun ThesisChapterPickerPanel(
    thesisImport: ThesisPosterImportPayload,
    selectedNames: Set<String>,
    onToggle: (String) -> Unit,
    onRebuild: () -> Unit
) {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer)) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text("Thesis chapters used for poster", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                    Text(
                        "${selectedNames.size}/${thesisImport.chapters.size} selected. Tables, charts, figures, and references are reused directly.",
                        style = MaterialTheme.typography.bodySmall
                    )
                }
                Button(onClick = onRebuild) {
                    Text("Rebuild")
                }
            }
            thesisImport.chapters.chunked(2).forEach { rowChapters ->
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    rowChapters.forEach { chapter ->
                        Row(
                            modifier = Modifier
                                .weight(1f)
                                .clip(RoundedCornerShape(8.dp))
                                .background(MaterialTheme.colorScheme.surface)
                                .clickable { onToggle(chapter.name) }
                                .padding(8.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Checkbox(
                                checked = chapter.name in selectedNames,
                                onCheckedChange = { onToggle(chapter.name) }
                            )
                            Column {
                                Text(chapter.name, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Bold)
                                Text("${chapter.content.length.coerceAtMost(9999)} chars", style = MaterialTheme.typography.labelSmall)
                            }
                        }
                    }
                    if (rowChapters.size == 1) Spacer(Modifier.weight(1f))
                }
            }
        }
    }
}

@Composable
private fun PosterChaptersTab(
    state: PosterAnalysisUiState,
    update: (PosterInputState.() -> PosterInputState) -> Unit,
    generate: () -> Unit,
    rebuildFromThesis: () -> Unit,
    toggleThesisChapter: (String) -> Unit,
    onUpdateSection: (String, Int, String?, String?) -> Unit,
    onUpdateFullSection: (String, Int, PosterSection) -> Unit,
    onMoveSection: (String, Int, String) -> Unit
) {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(14.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            PosterInputPanel(
                state.input,
                state.processing,
                update,
                generate
            )
        }
        state.thesisImport?.let { thesisImport ->
            item {
                ThesisChapterPickerPanel(
                    thesisImport = thesisImport,
                    selectedNames = state.selectedThesisChapterNames,
                    onToggle = toggleThesisChapter,
                    onRebuild = rebuildFromThesis
                )
            }
        }
        val poster = state.poster
        if (poster == null) {
            item { EmptyPosterPreview() }
        } else {
            item {
                val context = LocalContext.current
                val visualColumns = distributePosterVisuals(context, poster.charts, poster.figures, poster.flowcharts)
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    PosterColumn("left", poster.leftSections, visualColumns[0], Modifier.weight(1f), onUpdateSection = onUpdateSection, onUpdateFullSection = onUpdateFullSection, onMoveSection = onMoveSection)
                    PosterColumn("center", poster.centerSections, visualColumns[1], Modifier.weight(1f), onUpdateSection = onUpdateSection, onUpdateFullSection = onUpdateFullSection, onMoveSection = onMoveSection)
                    PosterColumn("right", poster.rightSections, visualColumns[2], Modifier.weight(1f), onUpdateSection = onUpdateSection, onUpdateFullSection = onUpdateFullSection, onMoveSection = onMoveSection)
                }
            }
        }
    }
}

@Composable
private fun PosterFiguresTab(
    input: PosterInputState,
    poster: PosterData?,
    pickCollegeLogo: () -> Unit,
    pickTitleLogo: () -> Unit,
    pickBackground: () -> Unit,
    pickFont: () -> Unit,
    pickFigure: (Int) -> Unit,
    onUpdateFigure: (Int, String?, String?, String?) -> Unit,
    onResizeFigure: (Int, Float?, Float?) -> Unit
) {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(14.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Card {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text("Poster visual assets", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                        PosterAssetPicker("College logo", input.logoUri, pickCollegeLogo, Modifier.weight(1f))
                        PosterAssetPicker("Title logo", input.titleLogoUri, pickTitleLogo, Modifier.weight(1f))
                        PosterAssetPicker("Background image", input.backgroundUri, pickBackground, Modifier.weight(1f))
                        PosterAssetPicker("TTF font", input.fontUri, pickFont, Modifier.weight(1f), previewImage = false)
                    }
                }
            }
        }
        if (poster == null) {
            item { EmptyPosterPreview() }
        } else {
            items(poster.figures.size) { index ->
                PosterFigureEditor(
                    index = index,
                    figure = poster.figures[index],
                    pickFigure = { pickFigure(index) },
                    onUpdateFigure = onUpdateFigure,
                    onResizeFigure = onResizeFigure
                )
            }
        }
    }
}

@Composable
private fun PosterAssetPicker(title: String, uri: String, onPick: () -> Unit, modifier: Modifier = Modifier, previewImage: Boolean = true) {
    Column(modifier, verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Box(
            Modifier
                .fillMaxWidth()
                .height(92.dp)
                .clip(RoundedCornerShape(8.dp))
                .background(ComposeColor(0xFFE7F2FF)),
            contentAlignment = Alignment.Center
        ) {
            if (uri.isNotBlank() && previewImage) {
                AsyncImage(model = uri, contentDescription = title, modifier = Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
            } else if (uri.isNotBlank()) {
                Text("Loaded", color = ComposeColor(0xFF0B5CAD), fontWeight = FontWeight.Bold)
            } else {
                Icon(Icons.Default.Image, contentDescription = null, tint = ComposeColor(0xFF0B5CAD))
            }
        }
        Button(onClick = onPick, modifier = Modifier.fillMaxWidth()) {
            Icon(Icons.Default.Image, contentDescription = null)
            Spacer(Modifier.width(6.dp))
            Text(title)
        }
    }
}

@Composable
private fun PosterFigureEditor(
    index: Int,
    figure: PosterFigure,
    pickFigure: () -> Unit,
    onUpdateFigure: (Int, String?, String?, String?) -> Unit,
    onResizeFigure: (Int, Float?, Float?) -> Unit
) {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxWidth()) {
                Box(
                    Modifier
                        .width(170.dp)
                        .height(120.dp)
                        .clip(RoundedCornerShape(8.dp))
                        .background(ComposeColor(0xFFE7F2FF)),
                    contentAlignment = Alignment.Center
                ) {
                    if (figure.imageUri.isNotBlank()) {
                        AsyncImage(model = figure.imageUri, contentDescription = figure.title, modifier = Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
                    } else {
                        Icon(Icons.Default.Image, contentDescription = null, tint = ComposeColor(0xFF0B5CAD))
                    }
                }
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(figure.title, { onUpdateFigure(index, it, null, null) }, label = { Text("Figure heading") }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(figure.caption, { onUpdateFigure(index, null, it, null) }, label = { Text("Caption") }, modifier = Modifier.fillMaxWidth(), minLines = 2)
                    OutlinedTextField(figure.query, { onUpdateFigure(index, null, null, it) }, label = { Text("AI image/search prompt") }, modifier = Modifier.fillMaxWidth())
                    Button(onClick = pickFigure) {
                        Icon(Icons.Default.Image, contentDescription = null)
                        Spacer(Modifier.width(6.dp))
                        Text("Add image")
                    }
                }
            }
            Text("Preview width", style = MaterialTheme.typography.labelMedium)
            Slider(value = figure.widthPercent, onValueChange = { onResizeFigure(index, it, null) }, valueRange = 0.22f..0.95f)
            Text("Preview height", style = MaterialTheme.typography.labelMedium)
            Slider(value = figure.heightPercent, onValueChange = { onResizeFigure(index, null, it) }, valueRange = 0.10f..0.42f)
        }
    }
}

@Composable
private fun PosterChartsTab(
    charts: List<PosterChart>,
    fontUri: String,
    onUpdateChart: (Int, String?, String?, String?, String?) -> Unit
) {
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(14.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        if (charts.isEmpty()) {
            item { EmptyPosterPreview() }
        } else {
            items(charts.size) { index ->
                PosterChartEditor(index, charts[index], fontUri, onUpdateChart)
            }
        }
    }
}

@Composable
private fun PosterChartEditor(
    index: Int,
    chart: PosterChart,
    fontUri: String,
    onUpdateChart: (Int, String?, String?, String?, String?) -> Unit
) {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                OutlinedTextField(chart.title, { onUpdateChart(index, it, null, null, null) }, label = { Text("Chart title") }, modifier = Modifier.weight(1f))
                OutlinedTextField(chart.type, { onUpdateChart(index, null, it, null, null) }, label = { Text("Type") }, modifier = Modifier.weight(0.45f))
            }
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                OutlinedTextField(chart.labels.joinToString(", "), { onUpdateChart(index, null, null, it, null) }, label = { Text("Labels CSV") }, modifier = Modifier.weight(1f))
                OutlinedTextField(chart.values.joinToString(", ") { it.toString() }, { onUpdateChart(index, null, null, null, it) }, label = { Text("Values CSV") }, modifier = Modifier.weight(1f))
            }
            ChartPreview(chart, fontUri)
        }
    }
}

@Composable
private fun PosterInputPanel(
    input: PosterInputState,
    processing: Boolean,
    update: (PosterInputState.() -> PosterInputState) -> Unit,
    generate: () -> Unit
) {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("Poster variables", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                OutlinedTextField(input.disease, { update { copy(disease = it) } }, label = { Text("Disease / topic") }, modifier = Modifier.weight(1f))
                OutlinedTextField(input.title, { update { copy(title = it) } }, label = { Text("Poster title") }, modifier = Modifier.weight(1f))
            }
            OutlinedTextField(
                input.abstractText,
                { update { copy(abstractText = it) } },
                label = { Text("Abstract for AI chapter generation") },
                modifier = Modifier.fillMaxWidth(),
                minLines = 4
            )
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                OutlinedTextField(input.author, { update { copy(author = it) } }, label = { Text("Author name") }, modifier = Modifier.weight(1f))
                OutlinedTextField(input.credentials, { update { copy(credentials = it) } }, label = { Text("Key credentials") }, modifier = Modifier.weight(1f))
            }
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                OutlinedTextField(input.guide, { update { copy(guide = it) } }, label = { Text("Guide") }, modifier = Modifier.weight(1f))
                OutlinedTextField(input.coGuide, { update { copy(coGuide = it) } }, label = { Text("Co-guide") }, modifier = Modifier.weight(1f))
            }
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                OutlinedTextField(input.college, { update { copy(college = it) } }, label = { Text("College name") }, modifier = Modifier.weight(1f))
                OutlinedTextField(input.department, { update { copy(department = it) } }, label = { Text("Department") }, modifier = Modifier.weight(1f))
            }
            OutlinedTextField(input.contact, { update { copy(contact = it) } }, label = { Text("Contact / QR link") }, modifier = Modifier.fillMaxWidth())
            Text("Text colors", style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.SemiBold)
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                ColorHexField("Title", input.titleColor, { update { copy(titleColor = it) } }, Modifier.weight(1f))
                ColorHexField("Heading", input.headingColor, { update { copy(headingColor = it) } }, Modifier.weight(1f))
                ColorHexField("Subheading", input.subheadingColor, { update { copy(subheadingColor = it) } }, Modifier.weight(1f))
            }
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                ColorHexField("Body", input.bodyColor, { update { copy(bodyColor = it) } }, Modifier.weight(1f))
                ColorHexField("Points", input.pointColor, { update { copy(pointColor = it) } }, Modifier.weight(1f))
                ColorHexField("Footer", input.footerColor, { update { copy(footerColor = it) } }, Modifier.weight(1f))
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                Spacer(Modifier.weight(1f))
                Button(onClick = generate, enabled = !processing) {
                    if (processing) CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp) else Icon(Icons.Default.AutoAwesome, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text("Generate with AI")
                }
            }
        }
    }
}

@Composable
private fun ColorHexField(label: String, value: String, onChange: (String) -> Unit, modifier: Modifier = Modifier) {
    var showPalette by rememberSaveable { mutableStateOf(false) }
    Column(modifier, verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Box(
                Modifier
                    .size(28.dp)
                    .clip(RoundedCornerShape(6.dp))
                    .background(composeColorFromHex(value, ComposeColor(0xFF0B5CAD)))
                    .border(1.dp, ComposeColor(0xFFD7E2EF), RoundedCornerShape(6.dp))
                    .clickable { showPalette = true }
            )
            OutlinedTextField(
                value = value,
                onValueChange = onChange,
                label = { Text(label) },
                singleLine = true,
                modifier = Modifier.weight(1f)
            )
        }
        Row(horizontalArrangement = Arrangement.spacedBy(5.dp), modifier = Modifier.fillMaxWidth()) {
            posterColorPalette().take(8).forEach { hex ->
                val selected = normalizeHexColor(value).equals(normalizeHexColor(hex), ignoreCase = true)
                Box(
                    Modifier
                        .size(22.dp)
                        .clip(RoundedCornerShape(6.dp))
                        .background(composeColorFromHex(hex, ComposeColor(0xFF0B5CAD)))
                        .border(
                            width = if (selected) 2.dp else 1.dp,
                            color = if (selected) MaterialTheme.colorScheme.primary else ComposeColor(0xFFD7E2EF),
                            shape = RoundedCornerShape(6.dp)
                        )
                        .clickable { onChange(hex) }
                )
            }
        }
        TextButton(onClick = { showPalette = true }) {
            Text("Open palette")
        }
    }

    if (showPalette) {
        AlertDialog(
            onDismissRequest = { showPalette = false },
            title = { Text("$label color") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    posterColorPalette().chunked(6).forEach { row ->
                        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                            row.forEach { hex ->
                                val selected = normalizeHexColor(value).equals(normalizeHexColor(hex), ignoreCase = true)
                                Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.width(44.dp)) {
                                    Box(
                                        Modifier
                                            .size(38.dp)
                                            .clip(RoundedCornerShape(8.dp))
                                            .background(composeColorFromHex(hex, ComposeColor(0xFF0B5CAD)))
                                            .border(
                                                width = if (selected) 3.dp else 1.dp,
                                                color = if (selected) MaterialTheme.colorScheme.primary else ComposeColor(0xFFD7E2EF),
                                                shape = RoundedCornerShape(8.dp)
                                            )
                                            .clickable {
                                                onChange(hex)
                                                showPalette = false
                                            }
                                    )
                                    Text(hex.removePrefix("#"), style = MaterialTheme.typography.labelSmall, maxLines = 1)
                                }
                            }
                        }
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { showPalette = false }) {
                    Text("Close")
                }
            }
        )
    }
}

@Composable
private fun EmptyPosterPreview() {
    Card {
        Box(Modifier.fillMaxWidth().height(260.dp), contentAlignment = Alignment.Center) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Icon(Icons.Default.Image, contentDescription = null, modifier = Modifier.size(42.dp))
                Text("Generate a poster to preview the three-column layout")
            }
        }
    }
}

@Composable
private fun PosterPreview(
    poster: PosterData,
    logoUri: String,
    titleLogoUri: String,
    backgroundUri: String,
    fontUri: String,
    input: PosterInputState,
    onUpdateSection: (String, Int, String?, String?) -> Unit,
    onUpdateFullSection: (String, Int, PosterSection) -> Unit,
    onMoveSection: (String, Int, String) -> Unit
) {
    Card {
        Box(
            Modifier
                .fillMaxWidth()
                .background(ComposeColor(0xFFF6F8FB))
        ) {
            if (backgroundUri.isNotBlank()) {
                AsyncImage(
                    model = backgroundUri,
                    contentDescription = null,
                    modifier = Modifier
                        .matchParentSize()
                        .alpha(0.18f),
                    contentScale = ContentScale.Crop
                )
            }
            Column(Modifier.padding(12.dp)) {
                Row(
                    Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(8.dp))
                        .background(ComposeColor(0xFF0B5CAD).copy(alpha = 0.94f))
                        .padding(14.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(Modifier.size(54.dp).clip(RoundedCornerShape(6.dp)).background(ComposeColor.White), contentAlignment = Alignment.Center) {
                        if (logoUri.isNotBlank()) {
                            AsyncImage(model = logoUri, contentDescription = null, modifier = Modifier.fillMaxSize())
                        }
                    }
                    Column(Modifier.weight(1f).padding(horizontal = 14.dp)) {
                        Text(poster.title, color = composeColorFromHex(input.titleColor, ComposeColor.White), fontWeight = FontWeight.Bold, maxLines = 2, overflow = TextOverflow.Ellipsis)
                        Text(poster.authorLine, color = ComposeColor(0xFFE7F2FF), style = MaterialTheme.typography.bodySmall)
                        Text(poster.institution, color = ComposeColor(0xFFE7F2FF), style = MaterialTheme.typography.bodySmall)
                    }
                    Box(Modifier.size(54.dp).clip(RoundedCornerShape(6.dp)).background(ComposeColor.White), contentAlignment = Alignment.Center) {
                        if (titleLogoUri.isNotBlank()) {
                            AsyncImage(model = titleLogoUri, contentDescription = null, modifier = Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
                        }
                    }
                }
                Spacer(Modifier.height(10.dp))
                val context = LocalContext.current
                val visualColumns = distributePosterVisuals(context, poster.charts, poster.figures, poster.flowcharts)
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    PosterColumn("left", poster.leftSections, visualColumns[0], Modifier.weight(1f), fontUri, input, onUpdateSection, onUpdateFullSection, onMoveSection)
                    PosterColumn("center", poster.centerSections, visualColumns[1], Modifier.weight(1f), fontUri, input, onUpdateSection, onUpdateFullSection, onMoveSection)
                    PosterColumn("right", poster.rightSections, visualColumns[2], Modifier.weight(1f), fontUri, input, onUpdateSection, onUpdateFullSection, onMoveSection)
                }
                Spacer(Modifier.height(8.dp))
                Text("Footer: ${poster.guideLine} | ${poster.contact}", style = MaterialTheme.typography.labelSmall, color = composeColorFromHex(input.footerColor, ComposeColor(0xFF172033)))
            }
        }
    }
}

@Composable
private fun PosterColumn(
    name: String,
    sections: List<PosterSection>,
    visualColumn: PosterVisualColumn,
    modifier: Modifier,
    fontUri: String = "",
    input: PosterInputState = PosterInputState(),
    onUpdateSection: (String, Int, String?, String?) -> Unit,
    onUpdateFullSection: (String, Int, PosterSection) -> Unit,
    onMoveSection: (String, Int, String) -> Unit
) {
    Column(modifier, verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(name.uppercase(), fontWeight = FontWeight.Bold, color = composeColorFromHex(input.headingColor, ComposeColor(0xFF0B5CAD)))
        visualColumn.itemsBySlot[0].orEmpty().forEach { item ->
            PosterVisualPreview(item, fontUri, input)
        }
        sections.forEachIndexed { index, section ->
            PosterSectionCard(section, name, index, input, onUpdateSection, onUpdateFullSection, onMoveSection)
            visualColumn.itemsBySlot[index + 1].orEmpty().forEach { item ->
                PosterVisualPreview(item, fontUri, input)
            }
        }
        visualColumn.trailingItemsAfterSectionCount(sections.size).forEach { item ->
            PosterVisualPreview(item, fontUri, input)
        }
    }
}

@Composable
private fun PosterVisualPreview(item: PosterVisualItem, fontUri: String, input: PosterInputState) {
    when (item) {
        is PosterVisualItem.ChartItem -> ChartPreview(item.chart, fontUri)
        is PosterVisualItem.FlowchartItem -> FlowchartPreview(item.flowchart, input)
        is PosterVisualItem.FigureItem -> FigurePreview(item.figure)
    }
}

@Composable
private fun PosterSectionCard(
    section: PosterSection,
    column: String,
    index: Int,
    input: PosterInputState,
    onUpdateSection: (String, Int, String?, String?) -> Unit,
    onUpdateFullSection: (String, Int, PosterSection) -> Unit,
    onMoveSection: (String, Int, String) -> Unit
) {
    var showEditor by rememberSaveable(section.id, section.title, column, index) { mutableStateOf(false) }
    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .background(ComposeColor.White.copy(alpha = 0.92f))
            .border(1.dp, ComposeColor(0xFFD7E2EF), RoundedCornerShape(8.dp))
            .clickable { showEditor = true }
            .padding(9.dp)
    ) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Text(
                section.title,
                modifier = Modifier.weight(1f),
                fontWeight = FontWeight.Bold,
                color = composeColorFromHex(input.headingColor, ComposeColor(0xFF0B5CAD)),
                style = MaterialTheme.typography.labelLarge,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
                softWrap = true
            )
            AssistChip(onClick = { showEditor = true }, label = { Text("Edit") })
        }
        Text(
            section.content,
            modifier = Modifier.fillMaxWidth(),
            style = MaterialTheme.typography.bodySmall,
            maxLines = 5,
            overflow = TextOverflow.Ellipsis,
            color = composeColorFromHex(input.bodyColor, ComposeColor(0xFF172033)),
            softWrap = true
        )
        SectionMetaRow(section)
        section.points.take(3).forEachIndexed { pointIndex, point ->
            Text(
                "${pointIndex + 1}. $point",
                modifier = Modifier.fillMaxWidth(),
                style = MaterialTheme.typography.labelSmall,
                color = composeColorFromHex(input.pointColor, ComposeColor(0xFF0B5CAD)),
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
                softWrap = true
            )
        }
        section.bullets.filterNot { it in section.points }.take(2).forEach {
            Text(
                "- $it",
                modifier = Modifier.fillMaxWidth(),
                style = MaterialTheme.typography.labelSmall,
                color = composeColorFromHex(input.bodyColor, ComposeColor(0xFF172033)),
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
                softWrap = true
            )
        }
    }
    if (showEditor) {
        PosterSectionEditorDialog(
            section = section,
            column = column,
            index = index,
            input = input,
            onDismiss = { showEditor = false },
            onSave = {
                onUpdateFullSection(column, index, it)
                showEditor = false
            },
            onMove = {
                onMoveSection(column, index, it)
                showEditor = false
            }
        )
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun SectionMetaRow(section: PosterSection) {
    FlowRow(
        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.spacedBy(6.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        if (section.subheadings.isNotEmpty()) AssistChip(onClick = {}, label = { Text("${section.subheadings.size} headings") })
        if (section.bullets.isNotEmpty()) AssistChip(onClick = {}, label = { Text("${section.bullets.size} bullets") })
        if (section.points.isNotEmpty()) AssistChip(onClick = {}, label = { Text("${section.points.size} points") })
        if (section.flowchartSteps.isNotEmpty()) AssistChip(onClick = {}, label = { Text("${section.flowchartSteps.size} steps") })
    }
}

@Composable
private fun PosterSectionEditorDialog(
    section: PosterSection,
    column: String,
    index: Int,
    input: PosterInputState,
    onDismiss: () -> Unit,
    onSave: (PosterSection) -> Unit,
    onMove: (String) -> Unit
) {
    var title by rememberSaveable(section.id, "title") { mutableStateOf(section.title) }
    var content by rememberSaveable(section.id, "content") { mutableStateOf(section.content) }
    var subheadings by rememberSaveable(section.id, "subheadings") { mutableStateOf(section.subheadings.joinToString("\n")) }
    var bullets by rememberSaveable(section.id, "bullets") { mutableStateOf(section.bullets.joinToString("\n")) }
    var points by rememberSaveable(section.id, "points") { mutableStateOf(section.points.joinToString("\n")) }
    var flowchartSteps by rememberSaveable(section.id, "flowchartSteps") { mutableStateOf(section.flowchartSteps.joinToString("\n")) }

    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(usePlatformDefaultWidth = false)
    ) {
        Surface(
            modifier = Modifier.fillMaxSize(),
            color = MaterialTheme.colorScheme.background,
            shape = RoundedCornerShape(0.dp)
        ) {
            Column(Modifier.fillMaxSize()) {
                Row(
                    Modifier
                        .fillMaxWidth()
                        .background(MaterialTheme.colorScheme.primary)
                        .padding(horizontal = 16.dp, vertical = 12.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(Modifier.weight(1f)) {
                        Text("Edit poster section", color = MaterialTheme.colorScheme.onPrimary, fontWeight = FontWeight.Bold)
                        Text("${column.replaceFirstChar { it.uppercase() }} column • Section ${index + 1}", color = MaterialTheme.colorScheme.onPrimary.copy(alpha = 0.85f), style = MaterialTheme.typography.labelMedium)
                    }
                    TextButton(onClick = onDismiss) {
                        Text("Cancel", color = MaterialTheme.colorScheme.onPrimary)
                    }
                    Button(
                        onClick = {
                            onSave(
                                section.copy(
                                    title = title.trim(),
                                    content = content.trim(),
                                    subheadings = linesToList(subheadings),
                                    bullets = linesToList(bullets),
                                    points = linesToList(points),
                                    flowchartSteps = linesToList(flowchartSteps)
                                )
                            )
                        }
                    ) {
                        Text("Save")
                    }
                }
                LazyColumn(
                    modifier = Modifier.fillMaxSize().padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    item {
                        Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
                            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                OutlinedTextField(title, { title = it }, label = { Text("Section heading") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                                OutlinedTextField(content, { content = it }, label = { Text("Main paragraph/content") }, modifier = Modifier.fillMaxWidth(), minLines = 7)
                            }
                        }
                    }
                    item {
                        Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
                            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                Text("AI structure", fontWeight = FontWeight.Bold, color = composeColorFromHex(input.headingColor, ComposeColor(0xFF0B5CAD)))
                                OutlinedTextField(subheadings, { subheadings = it }, label = { Text("Subheadings, one per line") }, modifier = Modifier.fillMaxWidth(), minLines = 3)
                                OutlinedTextField(bullets, { bullets = it }, label = { Text("Bullets, one per line") }, modifier = Modifier.fillMaxWidth(), minLines = 5)
                                OutlinedTextField(points, { points = it }, label = { Text("Numbered points, one per line") }, modifier = Modifier.fillMaxWidth(), minLines = 5)
                                OutlinedTextField(flowchartSteps, { flowchartSteps = it }, label = { Text("Flowchart steps, one per line") }, modifier = Modifier.fillMaxWidth(), minLines = 4)
                            }
                        }
                    }
                    item {
                        Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)) {
                            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                Text("Move section", fontWeight = FontWeight.Bold)
                                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    listOf("left", "center", "right").forEach { target ->
                                        OutlinedButton(onClick = { onMove(target) }, enabled = target != column) {
                                            Text(target.replaceFirstChar { it.uppercase() })
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

private fun linesToList(value: String): List<String> {
    return value
        .lines()
        .map { it.trim().trimStart('-', '*', '\u2022').trim() }
        .filter { it.isNotBlank() }
        .distinct()
}

@Composable
private fun LegacyPosterSectionCardUnused(
    section: PosterSection,
    column: String,
    index: Int,
    input: PosterInputState,
    onUpdateSection: (String, Int, String?, String?) -> Unit,
    onMoveSection: (String, Int, String) -> Unit
) {
    Column {
        Text(
            section.title,
            modifier = Modifier.fillMaxWidth(),
            fontWeight = FontWeight.Bold,
            color = composeColorFromHex(input.headingColor, ComposeColor(0xFF0B5CAD)),
            style = MaterialTheme.typography.labelLarge,
            maxLines = 3,
            overflow = TextOverflow.Ellipsis,
            softWrap = true
        )
        section.subheadings.take(3).forEach {
            Text(
                it,
                modifier = Modifier.fillMaxWidth(),
                fontWeight = FontWeight.SemiBold,
                style = MaterialTheme.typography.labelMedium,
                color = composeColorFromHex(input.subheadingColor, ComposeColor(0xFF172033)),
                maxLines = 3,
                overflow = TextOverflow.Ellipsis,
                softWrap = true
            )
        }
        Text(
            section.content,
            modifier = Modifier.fillMaxWidth(),
            style = MaterialTheme.typography.bodySmall,
            maxLines = 12,
            overflow = TextOverflow.Ellipsis,
            color = composeColorFromHex(input.bodyColor, ComposeColor(0xFF172033)),
            softWrap = true
        )
        OutlinedTextField(
            value = section.title,
            onValueChange = { onUpdateSection(column, index, it, null) },
            label = { Text("Edit heading") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )
        OutlinedTextField(
            value = section.content,
            onValueChange = { onUpdateSection(column, index, null, it) },
            label = { Text("Edit text") },
            modifier = Modifier.fillMaxWidth(),
            minLines = 2
        )
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.padding(top = 4.dp)) {
            listOf("left", "center", "right").forEach { target ->
                AssistChip(
                    onClick = { onMoveSection(column, index, target) },
                    enabled = target != column,
                    label = { Text(target.replaceFirstChar { it.uppercase() }) }
                )
            }
        }
        section.points.take(5).forEachIndexed { pointIndex, point ->
            Text(
                "${pointIndex + 1}. $point",
                modifier = Modifier.fillMaxWidth(),
                style = MaterialTheme.typography.labelSmall,
                color = composeColorFromHex(input.pointColor, ComposeColor(0xFF0B5CAD)),
                maxLines = 3,
                overflow = TextOverflow.Ellipsis,
                softWrap = true
            )
        }
        section.bullets.filterNot { it in section.points }.take(4).forEach {
            Text(
                "- $it",
                modifier = Modifier.fillMaxWidth(),
                style = MaterialTheme.typography.labelSmall,
                color = composeColorFromHex(input.bodyColor, ComposeColor(0xFF172033)),
                maxLines = 3,
                overflow = TextOverflow.Ellipsis,
                softWrap = true
            )
        }
        if (section.flowchartSteps.isNotEmpty()) {
            FlowchartPreview(PosterFlowchart("${section.title} flow", section.flowchartSteps, ""), input)
        }
    }
}

@Composable
private fun ChartPreview(chart: PosterChart, fontUri: String = "") {
    val context = LocalContext.current
    val typeface = loadTypefaceFromUri(context, fontUri)
    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .background(ComposeColor.White)
            .padding(9.dp)
    ) {
        Canvas(Modifier.fillMaxWidth().height(160.dp)) {
            drawIntoCanvas { canvas ->
                val paint = Paint(Paint.ANTI_ALIAS_FLAG)
                drawChartOnAndroidCanvas(
                    canvas.nativeCanvas,
                    chart,
                    RectF(0f, 0f, size.width, size.height),
                    paint,
                    typeface
                )
            }
        }
    }
}

@Composable
private fun FigurePreview(figure: PosterFigure) {
    val context = LocalContext.current
    val aspectRatio = remember(figure.imageUri, figure.widthPercent, figure.heightPercent) {
        figureOriginalAspectRatio(context, figure)
    }
    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .background(ComposeColor.White)
            .padding(9.dp)
    ) {
        BoxWithConstraints(Modifier.fillMaxWidth()) {
            val imageHeight = (maxWidth.value * aspectRatio).coerceAtLeast(120f).dp
            Box(
                Modifier
                    .fillMaxWidth()
                    .height(imageHeight)
                    .clip(RoundedCornerShape(6.dp))
                    .background(ComposeColor(0xFFE7F2FF)),
                contentAlignment = Alignment.Center
            ) {
                if (figure.imageUri.isNotBlank()) {
                    AsyncImage(model = figure.imageUri, contentDescription = figure.title, modifier = Modifier.fillMaxSize(), contentScale = ContentScale.Fit)
                } else {
                    Icon(Icons.Default.Image, contentDescription = null, tint = ComposeColor(0xFF0B5CAD))
                }
            }
        }
        Text(
            figure.title,
            modifier = Modifier.fillMaxWidth(),
            fontWeight = FontWeight.Bold,
            style = MaterialTheme.typography.labelLarge,
            maxLines = 3,
            overflow = TextOverflow.Ellipsis,
            softWrap = true
        )
        Text(
            figure.caption,
            modifier = Modifier.fillMaxWidth(),
            style = MaterialTheme.typography.labelSmall,
            maxLines = 4,
            overflow = TextOverflow.Ellipsis,
            softWrap = true
        )
    }
}

@Composable
private fun FlowchartPreview(flowchart: PosterFlowchart, input: PosterInputState = PosterInputState()) {
    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .background(ComposeColor.White)
            .padding(9.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp)
    ) {
        Text(
            flowchart.title,
            modifier = Modifier.fillMaxWidth(),
            fontWeight = FontWeight.Bold,
            color = composeColorFromHex(input.headingColor, ComposeColor(0xFF0B5CAD)),
            style = MaterialTheme.typography.labelLarge,
            maxLines = 3,
            overflow = TextOverflow.Ellipsis,
            softWrap = true
        )
        flowchart.steps.take(7).forEachIndexed { index, step ->
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                Box(
                    Modifier
                        .size(18.dp)
                        .clip(RoundedCornerShape(9.dp))
                        .background(composeColorFromHex(input.pointColor, ComposeColor(0xFF0B5CAD))),
                    contentAlignment = Alignment.Center
                ) {
                    Text("${index + 1}", color = ComposeColor.White, style = MaterialTheme.typography.labelSmall)
                }
                Text(
                    step,
                    style = MaterialTheme.typography.labelSmall,
                    modifier = Modifier.weight(1f),
                    color = composeColorFromHex(input.bodyColor, ComposeColor(0xFF172033)),
                    maxLines = 3,
                    overflow = TextOverflow.Ellipsis,
                    softWrap = true
                )
            }
        }
        if (flowchart.caption.isNotBlank()) {
            Text(flowchart.caption, style = MaterialTheme.typography.labelSmall, color = composeColorFromHex(input.bodyColor, ComposeColor(0xFF172033)))
        }
    }
}

private fun chartColor(index: Int): ComposeColor {
    return listOf(
        ComposeColor(0xFF0B5CAD),
        ComposeColor(0xFF16A085),
        ComposeColor(0xFFE67E22),
        ComposeColor(0xFF8E44AD),
        ComposeColor(0xFFC0392B)
    )[index % 5]
}

private fun wrapPosterText(text: String, maxChars: Int): List<String> {
    val words = text.split(Regex("\\s+")).filter { it.isNotBlank() }
    val lines = mutableListOf<String>()
    var current = ""
    words.forEach { word ->
        val candidate = if (current.isBlank()) word else "$current $word"
        if (candidate.length <= maxChars) current = candidate else {
            if (current.isNotBlank()) lines += current
            current = word
        }
    }
    if (current.isNotBlank()) lines += current
    return lines
}

private fun wrapPosterPaintText(text: String, paint: Paint, maxWidth: Float): List<String> {
    val words = text.split(Regex("\\s+")).filter { it.isNotBlank() }
    val lines = mutableListOf<String>()
    var current = ""
    words.forEach { word ->
        val candidate = if (current.isBlank()) word else "$current $word"
        if (paint.measureText(candidate) <= maxWidth) {
            current = candidate
        } else if (current.isBlank()) {
            lines += splitPosterPaintWord(word, paint, maxWidth)
            current = ""
        } else {
            lines += current
            if (paint.measureText(word) <= maxWidth) {
                current = word
            } else {
                lines += splitPosterPaintWord(word, paint, maxWidth)
                current = ""
            }
        }
    }
    if (current.isNotBlank()) lines += current
    return lines
}

private fun splitPosterPaintWord(word: String, paint: Paint, maxWidth: Float): List<String> {
    val parts = mutableListOf<String>()
    var current = ""
    word.forEach { char ->
        val candidate = current + char
        if (paint.measureText(candidate) <= maxWidth || current.isBlank()) {
            current = candidate
        } else {
            parts += current
            current = char.toString()
        }
    }
    if (current.isNotBlank()) parts += current
    return parts
}

private fun wrapPosterPdfText(text: String, font: PDType1Font, size: Float, maxWidth: Float): List<String> {
    val words = safePdfText(text).split(Regex("\\s+")).filter { it.isNotBlank() }
    val lines = mutableListOf<String>()
    var current = ""
    words.forEach { word ->
        val candidate = if (current.isBlank()) word else "$current $word"
        val candidateWidth = runCatching { font.getStringWidth(candidate) / 1000f * size }
            .getOrDefault(candidate.length * size * 0.5f)
        if (candidateWidth <= maxWidth) {
            current = candidate
        } else if (current.isBlank()) {
            lines += splitPosterPdfWord(word, font, size, maxWidth)
            current = ""
        } else {
            lines += current
            val wordWidth = runCatching { font.getStringWidth(word) / 1000f * size }
                .getOrDefault(word.length * size * 0.5f)
            if (wordWidth <= maxWidth) {
                current = word
            } else {
                lines += splitPosterPdfWord(word, font, size, maxWidth)
                current = ""
            }
        }
    }
    if (current.isNotBlank()) lines += current
    return lines
}

private fun splitPosterPdfWord(word: String, font: PDType1Font, size: Float, maxWidth: Float): List<String> {
    val parts = mutableListOf<String>()
    var current = ""
    word.forEach { char ->
        val candidate = current + char
        val candidateWidth = runCatching { font.getStringWidth(candidate) / 1000f * size }
            .getOrDefault(candidate.length * size * 0.5f)
        if (candidateWidth <= maxWidth || current.isBlank()) {
            current = candidate
        } else {
            parts += current
            current = char.toString()
        }
    }
    if (current.isNotBlank()) parts += current
    return parts
}

private fun androidColorFromHex(value: String, fallback: Int): Int {
    return runCatching {
        val normalized = normalizeHexColor(value)
        android.graphics.Color.parseColor(normalized)
    }.getOrDefault(fallback)
}

private fun composeColorFromHex(value: String, fallback: ComposeColor): ComposeColor {
    return ComposeColor(androidColorFromHex(value, fallback.toArgb()))
}

private fun normalizeHexColor(value: String): String {
    val raw = value.trim().removePrefix("#")
    return if (raw.length == 6 || raw.length == 8) "#$raw" else value.trim()
}

private fun posterColorPalette(): List<String> {
    return listOf(
        "#FFFFFF",
        "#F8FAFC",
        "#E5E7EB",
        "#9CA3AF",
        "#6B7280",
        "#374151",
        "#172033",
        "#000000",
        "#0B5CAD",
        "#1D4ED8",
        "#16A085",
        "#047857",
        "#65A30D",
        "#E67E22",
        "#D97706",
        "#F59E0B",
        "#8E44AD",
        "#7C3AED",
        "#DB2777",
        "#C0392B",
        "#DC2626",
        "#2C7BE5",
        "#0891B2",
        "#0F766E"
    )
}

private fun safePdfText(text: String): String {
    return text
        .replace("\u2022", "-")
        .filter { char -> runCatching { PDType1Font.HELVETICA.getStringWidth(char.toString()) }.isSuccess }
}

private data class PosterVisualColumn(
    val charts: List<PosterChart> = emptyList(),
    val figures: List<PosterFigure> = emptyList(),
    val flowcharts: List<PosterFlowchart> = emptyList(),
    val itemsBySlot: Map<Int, List<PosterVisualItem>> = emptyMap()
)

private sealed class PosterVisualItem {
    data class ChartItem(val chart: PosterChart) : PosterVisualItem()
    data class FigureItem(val figure: PosterFigure) : PosterVisualItem()
    data class FlowchartItem(val flowchart: PosterFlowchart) : PosterVisualItem()
}

private fun distributePosterVisuals(context: Context?, charts: List<PosterChart>, figures: List<PosterFigure>, flowcharts: List<PosterFlowchart>): List<PosterVisualColumn> {
    val chartBuckets = List(3) { mutableListOf<PosterChart>() }
    val figureBuckets = List(3) { mutableListOf<PosterFigure>() }
    val flowchartBuckets = List(3) { mutableListOf<PosterFlowchart>() }
    val columnLoads = FloatArray(3)

    fun leastLoadedColumn(): Int = columnLoads.indices.minByOrNull { columnLoads[it] } ?: 0

    figures.sortedByDescending { figureVisualWeight(context, it) }.forEach { figure ->
        val targetColumn = leastLoadedColumn()
        figureBuckets[targetColumn] += figure
        columnLoads[targetColumn] += figureVisualWeight(context, figure)
    }
    charts.sortedByDescending { chartVisualWeight(it) }.forEach { chart ->
        val targetColumn = leastLoadedColumn()
        chartBuckets[targetColumn] += chart
        columnLoads[targetColumn] += chartVisualWeight(chart)
    }
    flowcharts.sortedByDescending { flowchartVisualWeight(it) }.forEach { flowchart ->
        val targetColumn = leastLoadedColumn()
        flowchartBuckets[targetColumn] += flowchart
        columnLoads[targetColumn] += flowchartVisualWeight(flowchart)
    }

    return List(3) { index ->
        val visualItems =
            chartBuckets[index].map { PosterVisualItem.ChartItem(it) } +
                figureBuckets[index].map { PosterVisualItem.FigureItem(it) } +
                flowchartBuckets[index].map { PosterVisualItem.FlowchartItem(it) }
        PosterVisualColumn(
            charts = chartBuckets[index],
            figures = figureBuckets[index],
            flowcharts = flowchartBuckets[index],
            itemsBySlot = stableVisualSlots(visualItems, slotCount = 4, salt = index)
        )
    }
}

private fun figureVisualWeight(context: Context?, figure: PosterFigure): Float {
    val requestedRatio = context?.let { figureOriginalAspectRatio(it, figure) }
        ?: (figure.heightPercent / figure.widthPercent.coerceAtLeast(0.18f)).coerceIn(0.45f, 2.2f)
    return 3f + requestedRatio * 3f
}

private fun chartVisualWeight(chart: PosterChart): Float {
    return 1.8f + chart.labels.size.coerceAtMost(10) * 0.16f
}

private fun flowchartVisualWeight(flowchart: PosterFlowchart): Float {
    return 2f + flowchart.steps.size.coerceAtMost(10) * 0.22f
}

private fun allocatePosterSectionHeights(
    sections: List<PosterSection>,
    availableHeight: Float,
    minHeight: Float
): List<Float> {
    if (sections.isEmpty()) return emptyList()
    val weights = sections.map { sectionTextWeight(it) }
    val totalWeight = weights.sum().coerceAtLeast(1f)
    val minTotal = minHeight * sections.size
    if (availableHeight <= minTotal) return List(sections.size) { minHeight }

    val flexibleHeight = availableHeight - minTotal
    return weights.map { weight ->
        minHeight + flexibleHeight * (weight / totalWeight)
    }
}

private fun sectionTextWeight(section: PosterSection): Float {
    val contentChars = section.content.length
    val structuredChars =
        section.title.length +
            section.subheadings.sumOf { it.length } +
            section.points.sumOf { it.length } +
            section.bullets.sumOf { it.length } +
            section.flowchartSteps.sumOf { it.length }
    val explicitLines =
        section.content.lineSequence().count().coerceAtLeast(1) +
            section.subheadings.size +
            section.points.size +
            section.bullets.size +
            section.flowchartSteps.size
    return (1f + contentChars / 120f + structuredChars / 160f + explicitLines * 0.35f)
        .coerceIn(1f, 8f)
}

private fun scaledPosterVisualHeights(
    items: List<PosterVisualItem>,
    preferredHeight: (PosterVisualItem) -> Float,
    maxTotalHeight: Float
): Map<PosterVisualItem, Float> {
    if (items.isEmpty()) return emptyMap()
    val preferred = items.associateWith(preferredHeight)
    val protectedFigures = preferred.filterKeys { it is PosterVisualItem.FigureItem }
    val flexibleVisuals = preferred.filterKeys { it !is PosterVisualItem.FigureItem }
    val protectedHeight = protectedFigures.values.sum()
    val flexibleHeight = flexibleVisuals.values.sum()
    if (protectedHeight + flexibleHeight <= maxTotalHeight || flexibleHeight <= 0f) return preferred

    val remainingHeight = (maxTotalHeight - protectedHeight).coerceAtLeast(0f)
    val flexibleScale = (remainingHeight / flexibleHeight).coerceIn(0.35f, 1f)
    return protectedFigures + flexibleVisuals.mapValues { (_, height) -> height * flexibleScale }
}

private fun posterVisualHeightPdf(context: Context, item: PosterVisualItem, columnWidth: Float): Float {
    return when (item) {
        is PosterVisualItem.ChartItem -> {
            val chartAspectHeight = columnWidth * 0.58f
            val labelWeight = (item.chart.labels.size * 3f).coerceAtMost(24f)
            (chartAspectHeight + labelWeight + 18f).coerceIn(118f, 220f)
        }
        is PosterVisualItem.FigureItem -> {
            val requestedRatio = figureOriginalAspectRatio(context, item.figure)
            val titleLines = wrapPosterPdfText(item.figure.title, PDType1Font.HELVETICA_BOLD, 9f, columnWidth - 20f).take(2).size
            val captionLines = wrapPosterPdfText(item.figure.caption, PDType1Font.HELVETICA, 7.2f, columnWidth - 20f).take(3).size
            ((columnWidth - 16f) * requestedRatio + 42f + titleLines * 10f + captionLines * 10f).coerceAtLeast(126f)
        }
        is PosterVisualItem.FlowchartItem -> {
            val titleLines = (item.flowchart.title.length / 34 + 1).coerceIn(1, 2)
            val rows = kotlin.math.ceil(item.flowchart.steps.size.coerceAtLeast(3) / 2.0).toFloat()
            (44f + titleLines * 12f + rows * 28f).coerceIn(126f, 230f)
        }
    }
}

private fun posterVisualHeightBitmap(context: Context, item: PosterVisualItem, columnWidth: Float): Float {
    return when (item) {
        is PosterVisualItem.ChartItem -> {
            val chartAspectHeight = columnWidth * 0.58f
            val labelWeight = (item.chart.labels.size * 7f).coerceAtMost(54f)
            (chartAspectHeight + labelWeight + 34f).coerceIn(210f, 390f)
        }
        is PosterVisualItem.FigureItem -> {
            val requestedRatio = figureOriginalAspectRatio(context, item.figure)
            val approxCharsPerLine = (columnWidth / 12f).toInt().coerceAtLeast(18)
            val titleLines = if (item.figure.title.isBlank()) {
                0
            } else {
                kotlin.math.ceil(item.figure.title.length / approxCharsPerLine.toDouble()).toInt().coerceIn(1, 2)
            }
            val captionLines = if (item.figure.caption.isBlank()) {
                0
            } else {
                kotlin.math.ceil(item.figure.caption.length / approxCharsPerLine.toDouble()).toInt().coerceIn(1, 3)
            }
            ((columnWidth - 40f) * requestedRatio + 68f + titleLines * 26f + captionLines * 22f).coerceAtLeast(230f)
        }
        is PosterVisualItem.FlowchartItem -> {
            val titleLines = (item.flowchart.title.length / 30 + 1).coerceIn(1, 2)
            val rows = kotlin.math.ceil(item.flowchart.steps.size.coerceAtLeast(3) / 2.0).toFloat()
            (82f + titleLines * 30f + rows * 54f).coerceIn(230f, 410f)
        }
    }
}

private fun figureOriginalAspectRatio(context: Context, figure: PosterFigure): Float {
    loadBitmapFromUri(context, figure.imageUri)?.let { bitmap ->
        val ratio = bitmap.height.toFloat() / bitmap.width.coerceAtLeast(1).toFloat()
        bitmap.recycle()
        return ratio.coerceAtLeast(0.12f)
    }
    return (figure.heightPercent / figure.widthPercent.coerceAtLeast(0.18f)).coerceIn(0.45f, 2.2f)
}

private fun stableVisualSlots(items: List<PosterVisualItem>, slotCount: Int, salt: Int): Map<Int, List<PosterVisualItem>> {
    if (items.isEmpty()) return emptyMap()
    val slots = List(slotCount.coerceAtLeast(2)) { mutableListOf<PosterVisualItem>() }
    items.sortedBy { stableVisualKey(it, salt) }.forEachIndexed { index, item ->
        val slot = ((stableVisualKey(item, salt) + index) % slots.size).let { if (it < 0) -it else it }
        slots[slot] += item
    }
    return slots.mapIndexedNotNull { index, list -> list.takeIf { it.isNotEmpty() }?.let { index to it.toList() } }.toMap()
}

private fun stableVisualKey(item: PosterVisualItem, salt: Int): Int {
    val text = when (item) {
        is PosterVisualItem.ChartItem -> "chart:${item.chart.title}:${item.chart.type}"
        is PosterVisualItem.FigureItem -> "figure:${item.figure.title}:${item.figure.caption}"
        is PosterVisualItem.FlowchartItem -> "flow:${item.flowchart.title}:${item.flowchart.steps.joinToString("|")}"
    }
    return (text.hashCode() xor (salt * 1103515245))
}

private fun PosterVisualColumn.trailingItemsAfterSectionCount(sectionCount: Int): List<PosterVisualItem> {
    return itemsBySlot
        .filterKeys { it > sectionCount }
        .toSortedMap()
        .values
        .flatten()
}

private fun visualColumnItemsBeforeSection(
    charts: List<PosterChart>,
    figures: List<PosterFigure>,
    flowcharts: List<PosterFlowchart>,
    slot: Int
): List<PosterVisualItem> {
    val items =
        charts.map { PosterVisualItem.ChartItem(it) } +
            figures.map { PosterVisualItem.FigureItem(it) } +
            flowcharts.map { PosterVisualItem.FlowchartItem(it) }
    return stableVisualSlots(items, slotCount = 4, salt = charts.size + figures.size + flowcharts.size)[slot].orEmpty()
}

private fun renderChartBitmap(chart: PosterChart, width: Int, height: Int, typeface: Typeface?): Bitmap {
    val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
    val canvas = AndroidCanvas(bitmap)
    drawChartOnAndroidCanvas(canvas, chart, RectF(0f, 0f, width.toFloat(), height.toFloat()), Paint(Paint.ANTI_ALIAS_FLAG), typeface)
    return bitmap
}

private fun drawChartOnAndroidCanvas(canvas: AndroidCanvas, chart: PosterChart, bounds: RectF, paint: Paint, typeface: Typeface?) {
    val values = chart.values.ifEmpty { listOf(1f, 1f) }
    val labels = chart.labels.take(values.size).ifEmpty { values.indices.map { "V${it + 1}" } }
    val max = values.maxOrNull()?.coerceAtLeast(1f) ?: 1f
    paint.style = Paint.Style.FILL
    paint.color = android.graphics.Color.WHITE
    canvas.drawRoundRect(bounds, bounds.width() * 0.035f, bounds.width() * 0.035f, paint)

    val titleTextSize = bounds.height() * 0.078f
    paint.typeface = typeface?.let { Typeface.create(it, Typeface.BOLD) } ?: Typeface.DEFAULT_BOLD
    paint.textSize = titleTextSize
    paint.color = android.graphics.Color.parseColor("#0B5CAD")
    val titleLines = wrapPosterPaintText(chart.title, paint, bounds.width() * 0.9f).take(2)
    val titleTop = bounds.top + bounds.height() * 0.08f
    var titleY = titleTop
    titleLines.forEach { line ->
        canvas.drawText(line, bounds.left + bounds.width() * 0.04f, titleY, paint)
        titleY += titleTextSize * 1.08f
    }

    val left = bounds.left + bounds.width() * 0.12f
    val top = (titleY + bounds.height() * 0.05f).coerceAtMost(bounds.bottom - bounds.height() * 0.28f)
    val right = bounds.right - bounds.width() * 0.06f
    val bottom = bounds.bottom - bounds.height() * 0.18f
    val chartRect = RectF(left, top, right, bottom)

    fun axis() {
        paint.style = Paint.Style.STROKE
        paint.strokeWidth = 3f
        paint.color = android.graphics.Color.parseColor("#8EA4BC")
        canvas.drawLine(chartRect.left, chartRect.bottom, chartRect.right, chartRect.bottom, paint)
        canvas.drawLine(chartRect.left, chartRect.top, chartRect.left, chartRect.bottom, paint)
        paint.style = Paint.Style.FILL
        paint.typeface = typeface ?: Typeface.DEFAULT
        paint.textSize = bounds.height() * 0.042f
        paint.color = android.graphics.Color.parseColor("#41556B")
        if (chart.xAxisTitle.isNotBlank()) {
            val axisTitle = fitPosterPaintText(chart.xAxisTitle, paint, chartRect.width() * 0.62f)
            canvas.drawText(axisTitle, chartRect.centerX() - paint.measureText(axisTitle) / 2f, bounds.bottom - 18f, paint)
        }
        if (chart.yAxisTitle.isNotBlank()) {
            canvas.drawText(fitPosterPaintText(chart.yAxisTitle, paint, chartRect.width() * 0.42f), bounds.left + 12f, chartRect.top - 10f, paint)
        }
    }

    when (chart.type.lowercase()) {
        "pie" -> {
            val pieSize = kotlin.math.min(chartRect.width(), chartRect.height()) * 0.76f
            val pieRect = RectF(chartRect.left, chartRect.top + 8f, chartRect.left + pieSize, chartRect.top + 8f + pieSize)
            val total = values.sum().coerceAtLeast(1f)
            var start = -90f
            values.forEachIndexed { index, value ->
                paint.style = Paint.Style.FILL
                paint.color = chartAndroidColor(index)
                val sweep = value / total * 360f
                canvas.drawArc(pieRect, start, sweep, true, paint)
                start += sweep
            }
            paint.typeface = typeface ?: Typeface.DEFAULT
            paint.textSize = bounds.height() * 0.04f
            labels.take(5).forEachIndexed { index, label ->
                paint.color = chartAndroidColor(index)
                val lx = pieRect.right + 28f
                val ly = chartRect.top + 28f + index * 34f
                canvas.drawCircle(lx, ly - 7f, 9f, paint)
                paint.color = android.graphics.Color.parseColor("#172033")
                val labelMaxWidth = (bounds.right - lx - 28f).coerceAtLeast(bounds.width() * 0.18f)
                val legendText = "${label.trim()} ${values.getOrElse(index) { 0f }.toInt()}"
                canvas.drawText(fitPosterPaintText(legendText, paint, labelMaxWidth), lx + 18f, ly, paint)
            }
        }
        "line" -> {
            axis()
            val step = chartRect.width() / values.lastIndex.coerceAtLeast(1)
            val points = values.mapIndexed { index, value ->
                android.graphics.PointF(chartRect.left + index * step, chartRect.bottom - chartRect.height() * value / max)
            }
            paint.style = Paint.Style.STROKE
            paint.strokeWidth = 5f
            paint.color = android.graphics.Color.parseColor("#0B5CAD")
            points.zipWithNext().forEach { (a, b) -> canvas.drawLine(a.x, a.y, b.x, b.y, paint) }
            paint.style = Paint.Style.FILL
            points.forEachIndexed { index, point ->
                paint.color = chartAndroidColor(index)
                canvas.drawCircle(point.x, point.y, 10f, paint)
            }
        }
        "scatter" -> {
            axis()
            val step = chartRect.width() / (values.size + 1)
            values.forEachIndexed { index, value ->
                paint.style = Paint.Style.FILL
                paint.color = chartAndroidColor(index)
                canvas.drawCircle(chartRect.left + step * (index + 1), chartRect.bottom - chartRect.height() * value / max, 13f, paint)
            }
        }
        "histogram", "bar" -> {
            axis()
            val barW = chartRect.width() / (values.size * 1.55f)
            values.forEachIndexed { index, value ->
                val h = chartRect.height() * value / max
                val x = chartRect.left + index * barW * 1.55f + barW * 0.25f
                paint.style = Paint.Style.FILL
                paint.color = chartAndroidColor(index)
                canvas.drawRoundRect(RectF(x, chartRect.bottom - h, x + barW, chartRect.bottom), 10f, 10f, paint)
            }
        }
        else -> {
            axis()
            val barW = chartRect.width() / (values.size * 1.55f)
            values.forEachIndexed { index, value ->
                val h = chartRect.height() * value / max
                val x = chartRect.left + index * barW * 1.55f + barW * 0.25f
                paint.style = Paint.Style.FILL
                paint.color = chartAndroidColor(index)
                canvas.drawRoundRect(RectF(x, chartRect.bottom - h, x + barW, chartRect.bottom), 10f, 10f, paint)
            }
        }
    }

    paint.typeface = typeface ?: Typeface.DEFAULT
    paint.textSize = bounds.height() * 0.036f
    paint.color = android.graphics.Color.parseColor("#41556B")
    if (chart.type.lowercase() != "pie") {
        labels.take(6).forEachIndexed { index, label ->
            val slotWidth = chartRect.width() / labels.take(6).size.coerceAtLeast(1)
            val x = chartRect.left + slotWidth * index
            val fittedLabel = fitPosterPaintText(label, paint, (slotWidth - 6f).coerceAtLeast(20f))
            canvas.drawText(fittedLabel, x.coerceAtMost(chartRect.right - paint.measureText(fittedLabel)), bounds.bottom - bounds.height() * 0.07f, paint)
        }
    }
}

private fun fitPosterPaintText(text: String, paint: Paint, maxWidth: Float): String {
    val clean = text.trim()
    if (clean.isBlank() || paint.measureText(clean) <= maxWidth) return clean
    if (maxWidth <= paint.measureText("...")) return ""
    var end = clean.length
    while (end > 1 && paint.measureText(clean.take(end).trimEnd() + "...") > maxWidth) {
        end--
    }
    return clean.take(end).trimEnd() + "..."
}

private fun chartAndroidColor(index: Int): Int {
    return listOf("#0B5CAD", "#16A085", "#E67E22", "#8E44AD", "#C0392B", "#2C7BE5")
        .let { android.graphics.Color.parseColor(it[index % it.size]) }
}

private fun loadTypefaceFromUri(context: Context, uri: String): Typeface? {
    if (uri.isBlank()) return null
    return runCatching {
        val file = File(context.cacheDir, "poster_font_${uri.hashCode()}.ttf")
        if (!file.exists() || file.length() == 0L) {
            context.contentResolver.openInputStream(Uri.parse(uri))?.use { input ->
                file.outputStream().use { output -> input.copyTo(output) }
            }
        }
        Typeface.createFromFile(file)
    }.getOrNull()
}

private fun loadBitmapFromUri(context: Context, uri: String): Bitmap? {
    if (uri.isBlank()) return null
    return runCatching {
        context.contentResolver.openInputStream(Uri.parse(uri))?.use { input ->
            android.graphics.BitmapFactory.decodeStream(input)
        }
    }.getOrNull()
}
