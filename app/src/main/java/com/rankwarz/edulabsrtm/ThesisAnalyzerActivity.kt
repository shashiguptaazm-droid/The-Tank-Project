package com.rankwarz.edulabsrtm

import android.annotation.SuppressLint
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.compose.ui.viewinterop.AndroidView
import com.github.mikephil.charting.charts.BarChart
import com.github.mikephil.charting.charts.HorizontalBarChart
import com.github.mikephil.charting.charts.LineChart
import com.github.mikephil.charting.charts.PieChart
import com.github.mikephil.charting.charts.ScatterChart
import android.util.Log
import com.github.mikephil.charting.components.XAxis
import com.github.mikephil.charting.data.*
import com.github.mikephil.charting.formatter.IndexAxisValueFormatter
import com.github.mikephil.charting.utils.ColorTemplate

import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.clickable
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Analytics
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.DarkMode
import androidx.compose.material.icons.filled.FolderOpen
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.LightMode
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.automirrored.filled.OpenInNew
import androidx.compose.material.icons.filled.Save
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.ViewModule
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.PrimaryScrollableTabRow
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Tab
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.FloatingActionButton
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.animation.core.*
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.FormatSize
import androidx.compose.material.icons.filled.ZoomIn
import androidx.compose.material.icons.filled.ZoomOut
import androidx.compose.material.icons.filled.Search
import androidx.compose.runtime.Composable
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.draw.clip
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.zIndex
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.window.Dialog
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.rankwarz.edulabsrtm.model.Chapter
import com.rankwarz.edulabsrtm.model.ChapterVersionItem
import com.rankwarz.edulabsrtm.model.chartDatasetsFromRaw
import com.rankwarz.edulabsrtm.model.FigureAsset
import com.rankwarz.edulabsrtm.model.PubMedAbstractSectionJson
import com.rankwarz.edulabsrtm.model.PubMedAbstractSourceJson
import com.rankwarz.edulabsrtm.model.PubMedFigureJson
import com.rankwarz.edulabsrtm.model.ThesisQualityScore
import com.rankwarz.edulabsrtm.model.ChapterTextBoxJson
import com.rankwarz.edulabsrtm.model.Variable
import coil.compose.SubcomposeAsyncImage
import com.google.gson.Gson
import com.rankwarz.edulabsrtm.model.ChartJson
import com.rankwarz.edulabsrtm.model.MasterChartColumnJson
import com.rankwarz.edulabsrtm.model.MasterChartColumnMappingJson
import com.rankwarz.edulabsrtm.model.MasterChartResultSummaryJson
import com.rankwarz.edulabsrtm.model.MasterChartValidationIssueJson
import com.rankwarz.edulabsrtm.model.ReferenceJson
import com.rankwarz.edulabsrtm.model.ThesisAiLogEntry
import com.rankwarz.edulabsrtm.ui.theme.ThesisExtractorTheme
import com.rankwarz.edulabsrtm.viewmodel.ThesisViewModel
import com.rankwarz.edulabsrtm.viewmodel.PdfTheme
import com.tom_roush.pdfbox.android.PDFBoxResourceLoader
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

data class ChartAsset(
    val chapterName: String,
    val chart: ChartJson
)

data class TableAsset(
    val chapterName: String,
    val table: com.rankwarz.edulabsrtm.model.ThesisTableJson
)

data class ReferenceAsset(
    val chapterName: String,
    val citation: String,
    val text: String,
    val pmid: String = "",
    val doi: String = "",
    val pubmedVerified: Boolean = false
)

data class ExportQualityCheck(
    val label: String,
    val passed: Boolean,
    val detail: String
)

private fun buildExportQualityChecks(
    uiState: ThesisViewModel.UiState,
    references: List<ReferenceAsset>,
    tables: List<TableAsset>,
    figures: List<FigureAsset>
): List<ExportQualityCheck> {
    val generatedChapters = uiState.chapters.filter { it.name.isNotBlank() }
    val completed = generatedChapters.count { it.status == Chapter.ChapterStatus.SUCCESS }
    val emptySuccessful = generatedChapters.filter {
        it.status == Chapter.ChapterStatus.SUCCESS &&
            it.content.isBlank() &&
            it.rawJson.isBlank() &&
            it.tables.isEmpty() &&
            it.figures.isEmpty()
    }
    val verifiedRefs = references.count { it.pubmedVerified || it.pmid.isNotBlank() }
    val citationNumbers = generatedChapters
        .filter { it.status == Chapter.ChapterStatus.SUCCESS }
        .flatMap { chapter -> Regex("""\[(\d+)]""").findAll(chapter.content).mapNotNull { it.groupValues.getOrNull(1)?.toIntOrNull() }.toList() }
        .distinct()
    val frontMatter = listOf("Title", "Certificate", "Declaration", "Abstract")
    val completedFrontMatter = frontMatter.count { expected ->
        generatedChapters.any { it.name.equals(expected, ignoreCase = true) && it.status == Chapter.ChapterStatus.SUCCESS }
    }
    val baseChecks = listOf(
        ExportQualityCheck(
            "All chapters generated",
            generatedChapters.isNotEmpty() && completed == generatedChapters.size,
            "$completed/${generatedChapters.size} chapters completed"
        ),
        ExportQualityCheck(
            "No empty sections",
            emptySuccessful.isEmpty() && generatedChapters.any { it.status == Chapter.ChapterStatus.SUCCESS },
            if (emptySuccessful.isEmpty()) "Generated chapters contain exportable content" else "${emptySuccessful.size} completed chapters are empty"
        ),
        ExportQualityCheck(
            "References verified",
            references.isNotEmpty() && verifiedRefs == references.size,
            "$verifiedRefs/${references.size} references include PMID verification"
        ),
        ExportQualityCheck(
            "Tables have titles",
            tables.all { it.table.title.isNotBlank() },
            if (tables.isEmpty()) "No tables detected" else "${tables.count { it.table.title.isNotBlank() }}/${tables.size} tables titled"
        ),
        ExportQualityCheck(
            "Figures have captions",
            figures.all { it.figure.caption.isNotBlank() },
            if (figures.isEmpty()) "No figures detected" else "${figures.count { it.figure.caption.isNotBlank() }}/${figures.size} figures captioned"
        ),
        ExportQualityCheck(
            "Citations match bibliography",
            citationNumbers.isNotEmpty() && references.isNotEmpty() && citationNumbers.all { it in 1..references.size },
            if (citationNumbers.isEmpty()) "No inline citation labels found" else "${citationNumbers.size} inline citation numbers checked against ${references.size} references"
        ),
        ExportQualityCheck(
            "Front matter complete",
            completedFrontMatter == frontMatter.size,
            "$completedFrontMatter/${frontMatter.size} front matter chapters completed"
        )
    )
    val ready = baseChecks.all { it.passed } && !uiState.processing
    return baseChecks + ExportQualityCheck(
        "PDF export ready",
        ready,
        if (ready) "Ready for final PDF export" else "Resolve failed checklist items before final export"
    )
}

private data class ThesisPosterPayload(
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
    val chapters: List<ThesisPosterChapterPayload> = emptyList(),
    val references: List<String> = emptyList(),
    val figures: List<ThesisPosterFigurePayload> = emptyList(),
    val charts: List<ThesisPosterChartPayload> = emptyList(),
    val tables: List<ThesisPosterTablePayload> = emptyList()
)

private data class ThesisPosterChapterPayload(
    val name: String = "",
    val content: String = ""
)

private data class ThesisPosterFigurePayload(
    val chapterName: String = "",
    val title: String = "",
    val caption: String = "",
    val query: String = "",
    val imageUri: String = ""
)

private data class ThesisPosterChartPayload(
    val chapterName: String = "",
    val title: String = "",
    val type: String = "",
    val labels: List<String> = emptyList(),
    val values: List<Float> = emptyList(),
    val xAxisTitle: String = "",
    val yAxisTitle: String = ""
)

private data class ThesisPosterTablePayload(
    val chapterName: String = "",
    val title: String = "",
    val headers: List<String> = emptyList(),
    val rows: List<List<String>> = emptyList()
)

private fun progressFraction(current: Int, total: Int): Float {
    if (total <= 0) return 0f
    return (current.toFloat() / total.toFloat()).coerceIn(0f, 1f)
}

private fun progressPercentText(current: Int, total: Int): String {
    if (total <= 0) return "0%"
    return "${(progressFraction(current, total) * 100f).toInt()}%"
}

private fun buildPosterPayloadFromThesis(state: ThesisViewModel.UiState): String {
    fun pick(vararg names: String): String {
        val wanted = names.map { it.lowercase().replace(Regex("[^a-z0-9]+"), "") }.toSet()
        return state.variables.firstOrNull { variable ->
            variable.name.lowercase().replace(Regex("[^a-z0-9]+"), "") in wanted
        }?.value?.trim().orEmpty()
    }

    val successfulChapters = state.chapters
        .filter { it.status == Chapter.ChapterStatus.SUCCESS }
        .filterNot {
            it.name.equals("References", true) ||
                it.name.equals("Bibliography", true) ||
                it.name.startsWith("List of", true) ||
                it.name.equals("Table of Contents", true)
        }

    val payload = ThesisPosterPayload(
        thesisSessionId = state.sessionId,
        title = state.thesisTitle.ifBlank { pick("Title", "Thesis Title", "Project Title") },
        disease = pick("Disease_or_Condition", "Disease Topic", "Title Disease Topic", "Keywords")
            .ifBlank { state.thesisTitle },
        abstractText = pick("Abstract_structured", "Abstract", "Introduction_text", "Background_text")
            .ifBlank {
                successfulChapters
                    .firstOrNull { it.name.equals("Abstract", true) }
                    ?.content
                    .orEmpty()
            },
        author = pick("Student Name", "Author", "Researcher"),
        credentials = pick("Degree", "Course", "Registration Number"),
        guide = pick("Guide", "Supervisor"),
        coGuide = pick("Co-guide", "Co Guide", "Co Supervisor"),
        college = pick("Institution", "College", "University"),
        department = pick("Department"),
        contact = pick("Contact", "Email", "Phone"),
        logoUri = state.collegeLogoUri,
        chapters = successfulChapters.map { chapter ->
            ThesisPosterChapterPayload(
                name = chapter.name,
                content = chapter.content.ifBlank { chapter.rawJson }.take(2000)
            )
        },
        references = (
            state.verifiedPubMedReferences.map { it.referenceText } +
                state.chapters.flatMap { chapter -> chapter.chapterReferences.map { it.referenceText } }
            )
            .filter { it.isNotBlank() }
            .distinct()
            .take(30),
        figures = state.chapters.flatMap { chapter ->
            chapter.figures.map { figure ->
                ThesisPosterFigurePayload(
                    chapterName = chapter.name,
                    title = figure.title,
                    caption = figure.caption,
                    query = figure.imageSearchQuery,
                    imageUri = figure.imageUrl.ifBlank { figure.sourceUrl }
                )
            }
        }.distinctBy { "${it.chapterName}|${it.title}|${it.caption}" }.take(30),
        charts = state.chapters.flatMap { chapter ->
            chapter.charts.map { chart ->
                ThesisPosterChartPayload(
                    chapterName = chapter.name,
                    title = chart.title,
                    type = chart.type,
                    labels = chart.labels.ifEmpty { chart.datasets.firstOrNull()?.labels.orEmpty() },
                    values = chart.values.map { it.toFloat() }.ifEmpty {
                        chart.datasets.firstOrNull()?.values?.map { it.toFloat() }.orEmpty()
                    },
                    xAxisTitle = chart.xAxisLabel.orEmpty(),
                    yAxisTitle = chart.yAxisLabel.orEmpty()
                )
            }
        }.filter { it.title.isNotBlank() || it.values.isNotEmpty() }.distinctBy { "${it.chapterName}|${it.title}" }.take(30),
        tables = state.chapters.flatMap { chapter ->
            chapter.tables.map { table ->
                ThesisPosterTablePayload(
                    chapterName = chapter.name,
                    title = table.title,
                    headers = table.headers,
                    rows = table.rows.take(8)
                )
            }
        }.filter { it.title.isNotBlank() || it.rows.isNotEmpty() }.distinctBy { "${it.chapterName}|${it.title}" }.take(30)
    )

    return Gson().toJson(payload)
}

private fun citationNumbersFromText(text: String): Set<String> {
    val bracketedCitations = Regex("""[\[(]\s*\d+(?:\s*(?:,|-|;)\s*\d+)*\s*[])]""")
    return bracketedCitations
        .findAll(text)
        .flatMap { match -> Regex("""\d+""").findAll(match.value).map { it.value } }
        .toSet()
}

private fun citationNumberFromLabel(label: String): String? {
    return Regex("""\d+""").find(label)?.value
}

private fun distinctPubMedFigures(pubMedFigures: List<PubMedFigureJson>): List<PubMedFigureJson> {
    return pubMedFigures
        .filter { it.localUri.isNotBlank() || it.imageUrl.isNotBlank() || it.thumbnailUrl.isNotBlank() }
        .distinctBy { "${it.pmid}|${it.pmcId}|${it.figureId}|${it.imageUrl}|${it.thumbnailUrl}" }
}

private fun hasChapterPubMedReferences(asset: FigureAsset, references: List<ReferenceAsset>): Boolean {
    return references.any { it.chapterName == asset.chapterName && it.pmid.isNotBlank() }
}

private fun pubMedFiguresForFigure(
    asset: FigureAsset,
    pubMedFigures: List<PubMedFigureJson>,
    references: List<ReferenceAsset>
): List<PubMedFigureJson> {
    val figureCitationNumbers = citationNumbersFromText(
        listOf(
            asset.figure.figureNumber,
            asset.figure.title,
            asset.figure.caption,
            asset.figure.imageSearchQuery
        ).joinToString(" ")
    )

    val chapterReferences = references
        .filter { it.chapterName == asset.chapterName && it.pmid.isNotBlank() }

    if (chapterReferences.isEmpty()) {
        return distinctPubMedFigures(pubMedFigures)
    }

    val scopedReferences = if (figureCitationNumbers.isNotEmpty()) {
        chapterReferences.filter { citationNumberFromLabel(it.citation) in figureCitationNumbers }
    } else {
        chapterReferences
    }

    val scopedPmids = scopedReferences.map { it.pmid.trim() }.filter { it.isNotBlank() }.toSet()
    if (scopedPmids.isEmpty()) return emptyList()

    return pubMedFigures
        .filter { it.pmid.trim() in scopedPmids }
        .let(::distinctPubMedFigures)
}

private fun referenceDisplayText(reference: ReferenceJson): String {
    val base = reference.referenceText.trim()
    val hasPmid = Regex("""\bPMID\s*:?\s*\d{4,12}\b""", RegexOption.IGNORE_CASE).containsMatchIn(base)
    val hasDoi = Regex("""\bDOI\s*:?\s*10\.\d{4,9}/[^\s<>"']+""", RegexOption.IGNORE_CASE).containsMatchIn(base)
    return buildString {
        append(base.ifBlank { "PubMed reference" })
        reference.pmid?.takeIf { it.isNotBlank() && !hasPmid }?.let { append(". PMID: ").append(it) }
        reference.doi?.takeIf { it.isNotBlank() && !hasDoi }?.let { append(". DOI: ").append(it) }
    }
}

private fun chapterTextWithoutReferenceBlock(text: String): String {
    if (text.isBlank()) return text
    val lines = text.lines()
    val referenceHeaderIndex = lines.indexOfFirst { line ->
        line.trim().equals("REFERENCES", ignoreCase = true) ||
            line.trim().endsWith("REFERENCES", ignoreCase = true)
    }
    if (referenceHeaderIndex < 0) return text
    return lines.take(referenceHeaderIndex).joinToString("\n").trimEnd()
}

@Composable
private fun boldMarkdownAnnotatedText(text: String): AnnotatedString {
    val highlight = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.6f)
    return buildAnnotatedString {
        var index = 0
        while (index < text.length) {
            val start = text.indexOf("**", startIndex = index)
            if (start < 0) {
                append(text.substring(index))
                break
            }

            append(text.substring(index, start))
            val end = text.indexOf("**", startIndex = start + 2)
            if (end < 0) {
                append(text.substring(start))
                break
            }

            val boldText = text.substring(start + 2, end)
            pushStyle(SpanStyle(fontWeight = FontWeight.Bold, background = highlight))
            append(boldText)
            pop()
            index = end + 2
        }
    }
}

private fun thesisAiProviderOptions(): List<String> = listOf(
    "auto",
    "openrouter",
    "deepseek",
    "groq",
    "gemini",
    "mistral",
    "cloudflare",
    "cerebras",
    "cohere",
    "huggingface",
    "replicate"
)

private fun PdfTheme.exportDesignLabel(): String = when (this) {
    PdfTheme.CLASSIC -> "Classic - Formal Thesis"
    PdfTheme.NAVY -> "Navy - Research Journal"
    PdfTheme.EMERALD -> "Emerald - Clinical Report"
    PdfTheme.MAROON -> "Maroon - Official Binder"
    PdfTheme.TEAL -> "Teal - Data Dashboard"
    PdfTheme.SLATE -> "Slate - Minimal Journal"
    PdfTheme.OLIVE -> "Olive - Academic Clinical"
    PdfTheme.SAND -> "Sand - Premium Cover"
    PdfTheme.ROYAL -> "Royal - Premium Presentation"
    PdfTheme.CRIMSON -> "Crimson - Institutional Report"
}

private fun exportThemeSelectionLabel(selection: String): String {
    val color = PdfTheme.fromName(selection)
    val layout = selection.substringAfter("|", missingDelimiterValue = "").trim()
    if (layout.isBlank()) return color.exportDesignLabel()
    return if (layout.startsWith("SERVER:", ignoreCase = true)) {
        val label = layout.substringAfter("|", "").trim()
        "${color.label} - ${label.ifBlank { layout.removePrefix("SERVER:").substringBefore("|").trim() }}"
    } else {
        "${color.label} - ${exportLayoutDisplayName(layout)}"
    }
}

private fun exportLayoutDisplayName(layout: String): String {
    val id = layout.trim().uppercase()
    if (id.startsWith("SERVER:")) {
        return layout.substringAfter("|", "").trim().ifBlank {
            id.removePrefix("SERVER:").substringBefore("|").trim().lowercase().replaceFirstChar { it.uppercase() }
        }
    }
    return when (id) {
        "FORMAL" -> "Formal Thesis"
        "JOURNAL" -> "Research Journal"
        "CLINICAL" -> "Clinical Report"
        "BINDER" -> "Official Binder"
        "DASHBOARD" -> "Data Dashboard"
        "MINIMAL" -> "Minimal Journal"
        "ACADEMIC" -> "Academic Clinical"
        "PREMIUM" -> "Premium Cover"
        "DEFENSE" -> "Defense Presentation"
        "INSTITUTIONAL" -> "Institutional Report"
        "EDITORIAL" -> "Editorial Folio"
        "ATLAS" -> "Atlas Plate"
        "EXECUTIVE" -> "Executive Summary"
        "MONOGRAPH" -> "Classic Monograph"
        "CASEBOOK" -> "Casebook File"
        "LABBOOK" -> "Lab Notebook"
        "REVIEW" -> "Systematic Review"
        "SIGNATURE" -> "Signature Portfolio"
        "COMPACT" -> "Compact Clinical"
        "ELEGANT" -> "Elegant Academic"
        "MODERN" -> "Modern Clean"
        "VINTAGE" -> "Vintage Classic"
        "CONTRAST" -> "High Contrast"
        "MINIMALIST" -> "Ultra Minimal"
        "GRADIENT" -> "Gradient Flow"
        "NOTEBOOK" -> "Spiral Notebook"
        "SLIDES" -> "Presentation Slides"
        "WIDESCREEN" -> "Widescreen Format"
        "ABSTRACTA" -> "Abstract Art"
        "ANTIQUE" -> "Antique Parchment"
        "ARGENT" -> "Silver Professional"
        "BRONZE" -> "Bronze Classic"
        "CAMEO" -> "Cameo Portrait"
        "CANVAS" -> "Canvas Texture"
        "CEDAR" -> "Cedar Wood"
        "CERAMIC" -> "Ceramic Glaze"
        "CHALK" -> "Chalkboard"
        "CLASSICAL" -> "Classical Scholar"
        "COTTON" -> "Cotton Soft"
        "CRYSTAL" -> "Crystal Clear"
        "DENIM" -> "Denim Blue"
        "FLINT" -> "Flint Stone"
        "FOAM" -> "Foam Green"
        "FROST" -> "Frost Ice"
        "GINGER" -> "Ginger Spice"
        "HAZEL" -> "Hazel Natural"
        "IVORY" -> "Ivory Classic"
        "LACE" -> "Lace Delicate"
        "BRICK" -> "Brick Textured"
        "CORAL" -> "Coral Reef"
        "CORK" -> "Cork Board"
        "EARTH" -> "Earth Tone"
        "GARNET" -> "Garnet Red"
        "GRANITE" -> "Granite Solid"
        "JADE" -> "Jade Green"
        "LEATHER" -> "Leather Bound"
        "LINEN" -> "Linen Texture"
        "MAGMA" -> "Magma Lava"
        "AURORA" -> "Aurora Gradient"
        "BAMBOO" -> "Bamboo Natural"
        "BUBBLE" -> "Bubble Modern"
        "CARBON" -> "Carbon Fiber"
        "CHROME" -> "Chrome Metallic"
        "CLOUD" -> "Cloud Light"
        "COBALT" -> "Cobalt Blue"
        "COPPER" -> "Copper Warm"
        "GOLD" -> "Gold Premium"
        "INDIGO" -> "Indigo Deep"
        "CHARCOAL" -> "Charcoal Dark"
        "EBONY" -> "Ebony Dark"
        "GHOST" -> "Ghost Minimal"
        "GLASS" -> "Glass Transparent"
        "JET" -> "Jet Black"
        "BURLAP" -> "Burlap Weave"
        "FIESTA" -> "Fiesta Bright"
        "LAVENDER" -> "Lavender Soft"
        "LEMON" -> "Lemon Fresh"
        "LILAC" -> "Lilac Purple"
        else -> id.lowercase().replaceFirstChar { it.uppercase() }
    }
}

private fun exportThemeLayoutName(selection: String): String {
    val layout = selection.substringAfter("|", missingDelimiterValue = "").trim()
    if (layout.isBlank()) return PdfTheme.fromName(selection).previewStyle().layoutName
    if (layout.startsWith("SERVER:", ignoreCase = true)) {
        return layout.substringAfter("|", "").trim().ifBlank {
            "Server: ${layout.removePrefix("SERVER:").substringBefore("|").trim()}"
        }
    }
    return exportLayoutDisplayName(layout)
}

private fun isNormalPreviewChapter(chapter: Chapter): Boolean {
    if (chapter.status != Chapter.ChapterStatus.SUCCESS) return false
    val name = chapter.name.trim().lowercase()
    if (name.isBlank()) return false
    val excluded = setOf(
        "title",
        "title page",
        "certificate",
        "declaration",
        "acknowledgement",
        "acknowledgements",
        "proforma",
        "patient consent form",
        "patient consent form (english)",
        "patient consent form (hindi)",
        "consent form",
        "references",
        "bibliography",
        "list of references",
        "list of tables",
        "list of figures",
        "list of abbreviations"
    )
    return excluded.none { name == it || name.contains(it) }
}

private fun previewTextForThemeSelection(chapter: Chapter?): String {
    val source = chapter?.content
        ?.ifBlank { chapter.rawJson }
        .orEmpty()
    return source
        .replace(Regex("""[{}\[\]",:]"""), " ")
        .lines()
        .map { it.trim().replace(Regex("\\s+"), " ") }
        .filter { it.length >= 18 }
        .take(8)
        .joinToString("\n")
        .take(900)
}

private data class ExportDesignPreviewStyle(
    val accent: Color,
    val soft: Color,
    val header: Color,
    val footer: Color,
    val rule: Color,
    val layoutName: String,
    val titleTreatment: String,
    val pageStructure: String,
    val tableTreatment: String,
    val chartTreatment: String
)

private fun PdfTheme.previewStyle(): ExportDesignPreviewStyle = when (this) {
    PdfTheme.CLASSIC -> ExportDesignPreviewStyle(Color(0xFF1B3A57), Color(0xFFDDEBF7), Color(0xFFBFD4EA), Color(0xFFEEF5FB), Color(0xFF6E93B8), "Formal frame", "Centered university cover", "Double border and running label", "Full academic grid", "Simple academic charts")
    PdfTheme.NAVY -> ExportDesignPreviewStyle(Color(0xFF081C2E), Color(0xFFD5DEEA), Color(0xFFB3C2D3), Color(0xFFEAF0F6), Color(0xFF5F7690), "Research journal", "Manuscript title block", "Thin journal rules", "Minimal horizontal rules", "Clean journal lines")
    PdfTheme.EMERALD -> ExportDesignPreviewStyle(Color(0xFF0A5C4E), Color(0xFFD0F0E9), Color(0xFFA7E1D5), Color(0xFFECFAF6), Color(0xFF48B49E), "Clinical report", "Logo top official page", "Clinical rail and header", "Boxed clinical rows", "Muted clinical palette")
    PdfTheme.MAROON -> ExportDesignPreviewStyle(Color(0xFF5C1717), Color(0xFFF4DADA), Color(0xFFEAB6B6), Color(0xFFFFF1F1), Color(0xFFC46E6E), "Official binder", "Authority cover band", "Binder spine and stamp frame", "Registrar-style grid", "Formal evidence charts")
    PdfTheme.TEAL -> ExportDesignPreviewStyle(Color(0xFF075B5B), Color(0xFFD3F3F0), Color(0xFFA9E0DA), Color(0xFFEBFAF8), Color(0xFF45AFA8), "Data dashboard", "Report control header", "Side rail and metric panels", "Dashboard data blocks", "Bold result charts")
    PdfTheme.SLATE -> ExportDesignPreviewStyle(Color(0xFF1F2A37), Color(0xFFDDE3EA), Color(0xFFBEC9D6), Color(0xFFEEF2F7), Color(0xFF6E7D90), "Minimal journal", "Quiet manuscript cover", "Large whitespace journal", "Sparse rule table", "Monochrome figures")
    PdfTheme.OLIVE -> ExportDesignPreviewStyle(Color(0xFF3E5121), Color(0xFFE4ECD4), Color(0xFFCFDDAE), Color(0xFFF6FAEC), Color(0xFF8EA35E), "Academic clinical", "Inset academic cover", "Soft inset paper frame", "Clinical academic boxes", "Muted comparison charts")
    PdfTheme.SAND -> ExportDesignPreviewStyle(Color(0xFF6A4B22), Color(0xFFF4E4CA), Color(0xFFE4C18D), Color(0xFFFFF7ED), Color(0xFFB88449), "Premium cover", "Editorial premium cover", "Wide hero band and side plate", "Premium dashboard table", "Presentation charts")
    PdfTheme.ROYAL -> ExportDesignPreviewStyle(Color(0xFF163FA3), Color(0xFFD8E6FF), Color(0xFFB9CEFF), Color(0xFFF5F8FF), Color(0xFF5D86E8), "Premium presentation", "Defense-ready cover", "Slide-inspired top system", "High contrast data table", "Viva-ready chart blocks")
    PdfTheme.CRIMSON -> ExportDesignPreviewStyle(Color(0xFF6D1111), Color(0xFFF8D6D6), Color(0xFFEEB0B0), Color(0xFFFFF2F2), Color(0xFFC95D5D), "Institutional report", "Official submission header", "Institutional seal frame", "Administrative report grid", "Clinical institutional charts")
}

@Composable
private fun ExportLayoutPreviewDialog(
    theme: PdfTheme,
    thesisTitle: String,
    onDismiss: () -> Unit
) {
    val style = theme.previewStyle()
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(theme.exportDesignLabel()) },
        text = {
            Column(
                modifier = Modifier
                    .heightIn(max = 520.dp)
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                ExportPreviewPage(theme = theme, style = style, thesisTitle = thesisTitle)
                PreviewPaletteRow(style)
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    PreviewDesignLine("Cover", style.titleTreatment)
                    PreviewDesignLine("Page", style.pageStructure)
                    PreviewDesignLine("Tables", style.tableTreatment)
                    PreviewDesignLine("Charts", style.chartTreatment)
                }
                Text(
                    text = "Layout preview only. Export still generates the complete PDF, DOCX, or PPTX.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
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
private fun PreviewPaletteRow(style: ExportDesignPreviewStyle) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        listOf(style.accent, style.header, style.soft, style.footer, style.rule).forEach { color ->
            Box(
                modifier = Modifier
                    .weight(1f)
                    .height(16.dp)
                    .background(color, RoundedCornerShape(4.dp))
                    .border(1.dp, Color.Black.copy(alpha = 0.08f), RoundedCornerShape(4.dp))
            )
        }
    }
}

@Composable
private fun PreviewDesignLine(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalAlignment = Alignment.Top
    ) {
        Text(
            text = label,
            modifier = Modifier.widthIn(min = 58.dp, max = 72.dp),
            style = MaterialTheme.typography.labelMedium,
            fontWeight = FontWeight.Bold
        )
        Text(
            text = value,
            modifier = Modifier.weight(1f),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

@Composable
private fun ExportPreviewPage(
    theme: PdfTheme,
    style: ExportDesignPreviewStyle,
    thesisTitle: String
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(8.dp),
        tonalElevation = 2.dp,
        shadowElevation = 2.dp,
        color = Color.White
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(0.707f)
                .background(Color.White)
        ) {
            Canvas(modifier = Modifier.fillMaxSize()) {
                val w = size.width
                val h = size.height
                drawRect(Color.White)
                when (theme) {
                    PdfTheme.CLASSIC -> {
                        drawRect(style.accent, topLeft = Offset(w * 0.045f, h * 0.035f), size = Size(w * 0.91f, h * 0.93f), style = Stroke(width = 3f))
                        drawRect(style.rule, topLeft = Offset(w * 0.07f, h * 0.06f), size = Size(w * 0.86f, h * 0.88f), style = Stroke(width = 1.5f))
                        drawRect(style.header, topLeft = Offset(w * 0.08f, h * 0.09f), size = Size(w * 0.84f, h * 0.045f))
                    }
                    PdfTheme.NAVY -> {
                        drawRect(style.rule, topLeft = Offset(w * 0.1f, h * 0.12f), size = Size(w * 0.8f, 2f))
                        drawRect(style.rule, topLeft = Offset(w * 0.1f, h * 0.89f), size = Size(w * 0.8f, 2f))
                        drawRect(style.footer, topLeft = Offset(w * 0.1f, h * 0.18f), size = Size(w * 0.8f, h * 0.13f))
                    }
                    PdfTheme.EMERALD -> {
                        drawRect(style.footer, size = Size(w, h * 0.13f))
                        drawRect(style.accent, size = Size(w * 0.045f, h))
                        drawRect(style.rule, topLeft = Offset(w * 0.1f, h * 0.17f), size = Size(w * 0.78f, 2f))
                    }
                    PdfTheme.MAROON -> {
                        drawRect(style.header, topLeft = Offset(0f, 0f), size = Size(w, h * 0.11f))
                        drawRect(style.accent, topLeft = Offset(w * 0.06f, h * 0.08f), size = Size(w * 0.88f, h * 0.84f), style = Stroke(width = 3.5f))
                        drawRect(style.rule, topLeft = Offset(w * 0.1f, h * 0.19f), size = Size(w * 0.8f, 3f))
                    }
                    PdfTheme.TEAL -> {
                        drawRect(style.accent, size = Size(w * 0.13f, h))
                        drawRect(style.soft, topLeft = Offset(w * 0.13f, 0f), size = Size(w * 0.87f, h * 0.18f))
                        drawRect(style.header, topLeft = Offset(w * 0.2f, h * 0.23f), size = Size(w * 0.32f, 8f))
                    }
                    PdfTheme.SLATE -> {
                        drawRect(style.rule, topLeft = Offset(w * 0.12f, h * 0.11f), size = Size(w * 0.76f, 1.5f))
                        drawRect(style.rule, topLeft = Offset(w * 0.12f, h * 0.9f), size = Size(w * 0.76f, 1.5f))
                        drawRect(style.soft, topLeft = Offset(w * 0.12f, h * 0.72f), size = Size(w * 0.26f, h * 0.11f))
                    }
                    PdfTheme.OLIVE -> {
                        drawRect(style.soft, topLeft = Offset(w * 0.06f, h * 0.06f), size = Size(w * 0.88f, h * 0.88f))
                        drawRect(Color.White, topLeft = Offset(w * 0.09f, h * 0.09f), size = Size(w * 0.82f, h * 0.82f))
                        drawRect(style.accent, topLeft = Offset(w * 0.09f, h * 0.09f), size = Size(w * 0.82f, h * 0.82f), style = Stroke(width = 2.5f))
                    }
                    PdfTheme.SAND -> {
                        drawRect(style.footer, size = Size(w, h))
                        drawRect(style.accent, topLeft = Offset(0f, 0f), size = Size(w, h * 0.2f))
                        drawRect(style.header, topLeft = Offset(w * 0.1f, h * 0.28f), size = Size(w * 0.56f, 8f))
                        drawRect(style.soft, topLeft = Offset(w * 0.68f, h * 0.2f), size = Size(w * 0.22f, h * 0.7f))
                    }
                    PdfTheme.ROYAL -> {
                        drawRect(style.accent, size = Size(w, h * 0.16f))
                        drawRect(style.soft, topLeft = Offset(w * 0.72f, 0f), size = Size(w * 0.28f, h * 0.16f))
                        drawRect(style.header, topLeft = Offset(w * 0.1f, h * 0.2f), size = Size(w * 0.36f, 7f))
                    }
                    PdfTheme.CRIMSON -> {
                        drawRect(style.footer, topLeft = Offset(w * 0.06f, h * 0.05f), size = Size(w * 0.88f, h * 0.9f))
                        drawRect(style.accent, topLeft = Offset(0f, 0f), size = Size(w, h * 0.095f))
                        drawRect(style.accent, topLeft = Offset(w * 0.06f, h * 0.05f), size = Size(w * 0.88f, h * 0.9f), style = Stroke(width = 2.5f))
                    }
                }
            }

            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(horizontal = 26.dp, vertical = 24.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                val headingColor = if (theme in setOf(PdfTheme.TEAL, PdfTheme.SAND, PdfTheme.ROYAL, PdfTheme.MAROON, PdfTheme.CRIMSON)) Color.White else style.accent
                Text(
                    text = style.layoutName.uppercase(),
                    style = MaterialTheme.typography.labelSmall,
                    color = headingColor,
                    fontWeight = FontWeight.Bold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = thesisTitle,
                    style = MaterialTheme.typography.titleSmall,
                    color = if (headingColor.luminance() > 0.8f) style.accent else headingColor,
                    fontWeight = FontWeight.Bold,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )
                PreviewCoverSignature(theme, style)
                PreviewSectionBlock(theme, style)
                PreviewTableBlock(style, theme)
                PreviewChartBlock(style, theme)
                PreviewFigureBlock(style, theme)
            }
        }
    }
}

@Composable
private fun PreviewCoverSignature(theme: PdfTheme, style: ExportDesignPreviewStyle) {
    val darkHeader = theme in setOf(PdfTheme.TEAL, PdfTheme.SAND, PdfTheme.ROYAL, PdfTheme.MAROON, PdfTheme.CRIMSON)
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(if (darkHeader) Color.White.copy(alpha = 0.92f) else style.footer, RoundedCornerShape(5.dp))
            .padding(7.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(30.dp)
                .background(style.accent, RoundedCornerShape(if (theme in setOf(PdfTheme.NAVY, PdfTheme.SLATE)) 2.dp else 15.dp))
                .border(1.dp, style.rule.copy(alpha = 0.45f), RoundedCornerShape(if (theme in setOf(PdfTheme.NAVY, PdfTheme.SLATE)) 2.dp else 15.dp))
        )
        Column(
            modifier = Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            Box(modifier = Modifier.fillMaxWidth(0.72f).height(5.dp).background(style.accent.copy(alpha = 0.85f), RoundedCornerShape(2.dp)))
            Box(modifier = Modifier.fillMaxWidth(0.48f).height(4.dp).background(style.rule.copy(alpha = 0.38f), RoundedCornerShape(2.dp)))
        }
        Box(
            modifier = Modifier
                .widthIn(min = 34.dp, max = 42.dp)
                .height(18.dp)
                .background(style.header, RoundedCornerShape(4.dp))
        )
    }
}

@Composable
private fun PreviewSectionBlock(theme: PdfTheme, style: ExportDesignPreviewStyle) {
    val boxed = theme in setOf(PdfTheme.EMERALD, PdfTheme.CRIMSON, PdfTheme.TEAL, PdfTheme.OLIVE)
    val shape = RoundedCornerShape(if (boxed) 4.dp else 0.dp)
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(if (boxed) style.soft else Color.Transparent, shape)
            .then(if (theme in setOf(PdfTheme.SAND, PdfTheme.ROYAL)) Modifier.border(1.dp, style.header, RoundedCornerShape(4.dp)) else Modifier)
            .padding(horizontal = 8.dp, vertical = 6.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        val sectionLabel = when (theme) {
            PdfTheme.CLASSIC -> "CHAPTER HEADING"
            PdfTheme.NAVY -> "Journal section"
            PdfTheme.EMERALD -> "Clinical finding"
            PdfTheme.MAROON -> "Official record"
            PdfTheme.TEAL -> "Result block"
            PdfTheme.SLATE -> "Minimal heading"
            PdfTheme.OLIVE -> "Academic note"
            PdfTheme.SAND -> "Premium section"
            PdfTheme.ROYAL -> "Defense highlight"
            PdfTheme.CRIMSON -> "Institutional section"
        }
        Text(sectionLabel, style = MaterialTheme.typography.labelMedium, color = style.accent, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
        repeat(3) { index ->
            Box(
                modifier = Modifier
                    .fillMaxWidth(if (index == 2) 0.72f else 1f)
                    .height(5.dp)
                    .background(style.rule.copy(alpha = 0.35f), RoundedCornerShape(2.dp))
            )
        }
    }
}

@Composable
private fun PreviewTableBlock(style: ExportDesignPreviewStyle, theme: PdfTheme) {
    val journal = theme in setOf(PdfTheme.NAVY, PdfTheme.SLATE)
    val dashboard = theme in setOf(PdfTheme.TEAL, PdfTheme.SAND, PdfTheme.ROYAL)
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, if (journal) style.rule.copy(alpha = 0.45f) else style.accent.copy(alpha = 0.55f), RoundedCornerShape(if (dashboard) 5.dp else 0.dp))
            .background(if (dashboard) style.footer else Color.White, RoundedCornerShape(if (dashboard) 5.dp else 0.dp))
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(
                    when {
                        journal -> Color.White
                        dashboard -> style.accent
                        else -> style.header
                    }
                )
                .padding(6.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            repeat(3) {
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .height(6.dp)
                        .background(if (journal) style.accent else Color.White, RoundedCornerShape(2.dp))
                )
            }
        }
        repeat(if (dashboard) 2 else 3) { row ->
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(if (journal) Color.White else if (row % 2 == 0) style.footer else Color.White)
                    .padding(6.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                repeat(3) {
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .height(5.dp)
                            .background(style.rule.copy(alpha = 0.35f), RoundedCornerShape(2.dp))
                    )
                }
            }
        }
    }
}

@Composable
private fun PreviewChartBlock(style: ExportDesignPreviewStyle, theme: PdfTheme) {
    val colors = listOf(style.accent, style.rule, Color(0xFFE67E22), Color(0xFF16A085))
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(58.dp)
            .background(if (theme in setOf(PdfTheme.TEAL, PdfTheme.SAND, PdfTheme.ROYAL)) style.soft else style.footer)
            .padding(if (theme in setOf(PdfTheme.NAVY, PdfTheme.SLATE)) 6.dp else 10.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalAlignment = Alignment.Bottom
    ) {
        colors.forEachIndexed { index, color ->
            if (theme in setOf(PdfTheme.NAVY, PdfTheme.SLATE)) {
                Canvas(
                    modifier = Modifier
                        .weight(1f)
                        .height(40.dp)
                ) {
                    val y = size.height - (index * size.height * 0.18f) - 8f
                    drawLine(color, Offset(0f, y), Offset(size.width, y - 10f), strokeWidth = 4f)
                    drawCircle(color, radius = 5f, center = Offset(size.width * 0.72f, y - 7f))
                }
            } else {
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .height((18 + index * 7).dp)
                        .background(color, RoundedCornerShape(topStart = 3.dp, topEnd = 3.dp))
                )
            }
        }
    }
}

@Composable
private fun PreviewFigureBlock(style: ExportDesignPreviewStyle, theme: PdfTheme) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(54.dp)
            .background(
                brush = Brush.horizontalGradient(listOf(style.footer, if (theme in setOf(PdfTheme.TEAL, PdfTheme.SAND, PdfTheme.ROYAL)) style.soft else Color.White))
            )
            .border(1.dp, style.rule.copy(alpha = 0.35f))
            .padding(8.dp)
    ) {
        Box(
            modifier = Modifier
                .size(38.dp)
                .background(style.header, RoundedCornerShape(4.dp))
        )
        Column(
            modifier = Modifier
                .padding(start = 50.dp)
                .align(Alignment.CenterStart),
            verticalArrangement = Arrangement.spacedBy(5.dp)
        ) {
            Box(modifier = Modifier.fillMaxWidth(0.55f).height(6.dp).background(style.accent, RoundedCornerShape(2.dp)))
            Box(modifier = Modifier.fillMaxWidth(0.78f).height(5.dp).background(style.rule.copy(alpha = 0.35f), RoundedCornerShape(2.dp)))
        }
    }
}

@Composable
private fun ExportDesignControlCard(
    selection: String,
    enabled: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val theme = PdfTheme.fromName(selection)
    val style = theme.previewStyle()
    val layoutName = exportThemeLayoutName(selection)
    Card(
        modifier = modifier
            .clickable(enabled = enabled, onClick = onClick)
            .border(1.dp, style.rule.copy(alpha = 0.32f), RoundedCornerShape(8.dp)),
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = if (enabled) style.footer else MaterialTheme.colorScheme.surfaceVariant),
        elevation = CardDefaults.cardElevation(defaultElevation = if (enabled) 3.dp else 0.dp)
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 10.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            ExportDesignMiniPage(style = style)
            Column(
                modifier = Modifier.widthIn(min = 150.dp, max = 230.dp),
                verticalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                Text(
                    text = "Export design",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    text = layoutName,
                    style = MaterialTheme.typography.labelLarge,
                    color = style.accent,
                    fontWeight = FontWeight.Bold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Text(
                    text = theme.label,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                ExportDesignPalette(style)
            }
            Icon(Icons.AutoMirrored.Filled.OpenInNew, contentDescription = null, tint = style.accent)
        }
    }
}

@Composable
private fun ExportDialogDesignHeader(selection: String, onChange: () -> Unit) {
    val theme = PdfTheme.fromName(selection)
    val style = theme.previewStyle()
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(style.footer, RoundedCornerShape(8.dp))
            .border(1.dp, style.rule.copy(alpha = 0.22f), RoundedCornerShape(8.dp))
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Row(
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            ExportDesignMiniPage(style = style)
            Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text("Current design", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Text(exportThemeLayoutName(selection), style = MaterialTheme.typography.titleSmall, color = style.accent, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(theme.label, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
            TextButton(onClick = onChange) {
                Text("Change")
            }
        }
        ExportDesignPalette(style)
    }
}

@Composable
private fun ExportFormatButton(
    title: String,
    subtitle: String,
    primary: Boolean,
    icon: @Composable () -> Unit,
    onClick: () -> Unit
) {
    val content: @Composable RowScope.() -> Unit = {
        icon()
        Spacer(modifier = Modifier.size(10.dp))
        Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(title, fontWeight = FontWeight.Bold)
            Text(subtitle, style = MaterialTheme.typography.labelSmall)
        }
    }
    if (primary) {
        Button(modifier = Modifier.fillMaxWidth(), onClick = onClick, content = content)
    } else {
        OutlinedButton(modifier = Modifier.fillMaxWidth(), onClick = onClick, content = content)
    }
}

@Composable
private fun ExportDesignMiniPage(style: ExportDesignPreviewStyle) {
    Box(
        modifier = Modifier
            .size(width = 42.dp, height = 58.dp)
            .background(Color.White, RoundedCornerShape(5.dp))
            .border(1.dp, style.rule.copy(alpha = 0.28f), RoundedCornerShape(5.dp))
            .padding(5.dp)
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(9.dp)
                .background(style.accent, RoundedCornerShape(3.dp))
        )
        Column(
            modifier = Modifier
                .align(Alignment.BottomStart)
                .fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(3.dp)
        ) {
            Box(Modifier.fillMaxWidth().height(4.dp).background(style.header, RoundedCornerShape(2.dp)))
            Box(Modifier.fillMaxWidth(0.72f).height(4.dp).background(style.rule.copy(alpha = 0.45f), RoundedCornerShape(2.dp)))
            Box(Modifier.fillMaxWidth(0.46f).height(4.dp).background(style.soft, RoundedCornerShape(2.dp)))
        }
    }
}

@Composable
private fun ExportDesignPalette(style: ExportDesignPreviewStyle) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        listOf(style.accent, style.header, style.soft, style.footer, style.rule).forEach { color ->
            Box(
                modifier = Modifier
                    .weight(1f)
                    .height(7.dp)
                    .background(color, RoundedCornerShape(2.dp))
                    .border(1.dp, Color.Black.copy(alpha = 0.05f), RoundedCornerShape(2.dp))
            )
        }
    }
}

@Composable
private fun ThesisAiSettingsDialog(
    uiState: ThesisViewModel.UiState,
    onPdfThemeSelected: (PdfTheme) -> Unit,
    onVpsAutoCompleteChanged: (Boolean) -> Unit,
    onExportMarginChanged: (String) -> Unit,
    onExportFontChanged: (String) -> Unit,
    onExportLineSpacingChanged: (String) -> Unit,
    onExportLogoPlacementChanged: (String) -> Unit,
    onExportPageNumberingChanged: (String) -> Unit,
    onExportHeaderFooterChanged: (Boolean) -> Unit,
    onExportWatermarkChanged: (Boolean) -> Unit,
    onExportAutoTocChanged: (Boolean) -> Unit,
    onExportAutoListsChanged: (Boolean) -> Unit,
    onDismiss: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Professional PDF Controls") },
        text = {
            Column(
                modifier = Modifier
                    .heightIn(max = 520.dp)
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        Text("VPS auto-complete", style = MaterialTheme.typography.labelLarge)
                        Text(
                            "Retry and complete pending thesis chapters on the server every minute.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    Switch(
                        checked = uiState.vpsAutoCompleteEnabled,
                        onCheckedChange = onVpsAutoCompleteChanged
                    )
                }
                HorizontalDivider()
                ExportOptionGroup(
                    title = "Margins",
                    selected = uiState.exportMargin,
                    options = listOf("normal" to "Normal", "narrow" to "Narrow", "wide" to "Wide", "binding" to "Binding"),
                    onSelected = onExportMarginChanged
                )
                ExportOptionGroup(
                    title = "Font",
                    selected = uiState.exportFont,
                    options = listOf("serif" to "Serif", "sans" to "Sans", "modern" to "Modern", "mono" to "Mono"),
                    onSelected = onExportFontChanged
                )
                ExportOptionGroup(
                    title = "Line spacing",
                    selected = uiState.exportLineSpacing,
                    options = listOf("compact" to "Compact", "normal" to "Normal", "relaxed" to "Relaxed", "double" to "Double"),
                    onSelected = onExportLineSpacingChanged
                )
                ExportOptionGroup(
                    title = "Logo placement",
                    selected = uiState.exportLogoPlacement,
                    options = listOf("theme" to "Theme", "top-left" to "Top left", "top-center" to "Top center", "top-right" to "Top right", "none" to "None"),
                    onSelected = onExportLogoPlacementChanged
                )
                ExportOptionGroup(
                    title = "Page numbering",
                    selected = uiState.exportPageNumbering,
                    options = listOf("theme" to "Arabic", "roman" to "Roman", "none" to "None"),
                    onSelected = onExportPageNumberingChanged
                )
                ExportSwitchRow("Header/footer", "Show running header and footer chrome.", uiState.exportHeaderFooter, onExportHeaderFooterChanged)
                ExportSwitchRow("Watermark", "Add a light THESIS DRAFT watermark.", uiState.exportWatermark, onExportWatermarkChanged)
                ExportSwitchRow("Table of contents", "Include generated table of contents pages during export.", uiState.exportAutoToc, onExportAutoTocChanged)
                ExportSwitchRow("Lists of tables/figures", "Include generated lists of tables, figures, abbreviations, and references.", uiState.exportAutoLists, onExportAutoListsChanged)
                HorizontalDivider()
                Text("Export design", style = MaterialTheme.typography.labelLarge)
                PdfTheme.entries.forEach { theme ->
                    val selected = theme.name == uiState.pdfTheme
                    OutlinedButton(
                        modifier = Modifier.fillMaxWidth(),
                        onClick = { onPdfThemeSelected(theme) },
                        enabled = !selected
                    ) {
                        Text(if (selected) "${theme.exportDesignLabel()} selected" else theme.exportDesignLabel())
                    }
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) {
                Text("Done")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Close")
            }
        }
    )
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun ExportOptionGroup(
    title: String,
    selected: String,
    options: List<Pair<String, String>>,
    onSelected: (String) -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(title, style = MaterialTheme.typography.labelLarge)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            options.forEach { (value, label) ->
                val active = selected.equals(value, ignoreCase = true)
                if (active) {
                    Button(onClick = { onSelected(value) }) { Text(label) }
                } else {
                    OutlinedButton(onClick = { onSelected(value) }) { Text(label) }
                }
            }
        }
    }
}

@Composable
private fun ExportSwitchRow(
    title: String,
    subtitle: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(title, style = MaterialTheme.typography.labelLarge)
            Text(subtitle, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        Switch(checked = checked, onCheckedChange = onCheckedChange)
    }
}

private fun normalizedBoxValue(value: Float, min: Float, max: Float): Float {
    return value.coerceIn(min, max)
}

private fun normalizeChapterTextBoxes(boxes: List<ChapterTextBoxJson>): List<ChapterTextBoxJson> {
    var nextSafeY = 0.04f
    return boxes.mapIndexed { index, box ->
        val safeWidth = normalizedBoxValue(box.width, 0.22f, 0.90f)
        val safeHeight = normalizedBoxValue(box.height, 0.10f, 0.58f)
        val requestedY = normalizedBoxValue(box.y, 0.04f, 0.92f)
        val safeY = maxOf(requestedY, nextSafeY).coerceAtMost((0.96f - safeHeight).coerceAtLeast(0.04f))
        nextSafeY = (safeY + safeHeight + 0.025f).coerceAtMost(0.96f)
        ChapterTextBoxJson(
            id = box.id.ifBlank { "box_${index + 1}" },
            text = box.text.trim(),
            x = normalizedBoxValue(box.x, 0.04f, (0.96f - safeWidth).coerceAtLeast(0.04f)),
            y = safeY,
            width = safeWidth,
            height = safeHeight
        )
    }
}

private fun defaultChapterBoxText(box: ChapterTextBoxJson): String = box.text.trim()

private fun estimateEditorTextBoxHeight(text: String, widthFraction: Float): Float {
    val avgCharsPerLine = (widthFraction * 78f).coerceAtLeast(24f)
    val lineCount = text.split(Regex("\\r?\\n")).sumOf { line ->
        maxOf(1, kotlin.math.ceil(line.length / avgCharsPerLine.toDouble()).toInt())
    }
    return (0.08f + lineCount * 0.040f).coerceIn(0.12f, 0.42f)
}

class ThesisAnalyzerActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        PDFBoxResourceLoader.init(applicationContext)
        val prefs = getSharedPreferences(APP_PREFS_NAME, Context.MODE_PRIVATE)
        val initialDarkMode = prefs.getBoolean(KEY_DARK_MODE, false)
        applySavedAppTheme(this)

        setContent {
            var darkModeEnabled by rememberSaveable { mutableStateOf(initialDarkMode) }

            ThesisExtractorTheme(darkTheme = darkModeEnabled) {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    ThesisApp(
                        darkModeEnabled = darkModeEnabled,
                        onToggleTheme = {
                            val next = !darkModeEnabled
                            darkModeEnabled = next
                            setAppDarkMode(this, next)
                        }
                    )
                }
            }
        }
    }
}

suspend fun fetchImageFromWikipedia(query: String): String {
    return try {
        val url = "https://en.wikipedia.org/w/api.php?action=query&format=json&prop=pageimages&pithumbsize=600&titles=$query"
        val connection = java.net.URL(url).openConnection()
        connection.connectTimeout = 5000
        connection.readTimeout = 5000

        val response = connection.getInputStream().bufferedReader().readText()
        val json = org.json.JSONObject(response)
        val pages = json.getJSONObject("query").getJSONObject("pages")

        val keys = pages.keys()
        if (!keys.hasNext()) return ""

        val page = pages.getJSONObject(keys.next())
        page.optJSONObject("thumbnail")?.optString("source") ?: ""
    } catch (e: Exception) {
        ""
    }
}

suspend fun searchImageFromQuery(query: String): String {
    if (query.isBlank()) return ""
    return try {
        val encoded = java.net.URLEncoder.encode(query, "UTF-8")

        // Try with original query first
        var result = fetchImageFromWikipedia(encoded)
        if (result.isNotBlank()) return result

        // 1st fallback: Try with a simpler query (take first 3 words) if query is long
        val words = query.split(" ")
        if (words.size > 3) {
            val simplified = java.net.URLEncoder.encode(words.take(3).joinToString(" "), "UTF-8")
            result = fetchImageFromWikipedia(simplified)
            if (result.isNotBlank()) return result
        }

        // 2nd fallback: Use Unsplash Source (reliable placeholder/search service)
        // Unsplash provides a redirect to a real image based on keywords
        val unsplashUrl = "https://source.unsplash.com/featured/800x600/?${encoded}"

        // We return the direct URL. coil.compose.SubcomposeAsyncImage will handle the redirect.
        unsplashUrl
    } catch (e: Exception) {
        ""
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ThesisApp(
    darkModeEnabled: Boolean,
    onToggleTheme: () -> Unit,
    viewModel: ThesisViewModel = viewModel()
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val clipboardManager = LocalClipboardManager.current
    val scope = rememberCoroutineScope()

    var selectedTab by rememberSaveable { mutableIntStateOf(0) }
    var tabFullView by rememberSaveable { mutableStateOf(false) }
    var showProjectDialog by rememberSaveable { mutableStateOf(false) }
    var showSessionsDialog by rememberSaveable { mutableStateOf(false) }
    var projectNameInput by rememberSaveable { mutableStateOf(uiState.thesisTitle) }
    var showLayoutPreviewDialog by rememberSaveable { mutableStateOf(false) }
    var showExportDialog by rememberSaveable { mutableStateOf(false) }
    var exportDialogTitle by rememberSaveable { mutableStateOf<String?>(null) }
    var pubMedFigureDialogVisible by rememberSaveable { mutableStateOf(false) }
    var showTopActionsMenu by rememberSaveable { mutableStateOf(false) }
    var showAiSettingsDialog by rememberSaveable { mutableStateOf(false) }

    var isGridViewEnabled by rememberSaveable { mutableStateOf(false) }
    var expandAllContents by rememberSaveable { mutableStateOf(false) }
    var globalFontSize by rememberSaveable { mutableStateOf(14f) }
    var activeChapterReaderItem by remember { mutableStateOf<Chapter?>(null) }

    LaunchedEffect(Unit) {
        viewModel.tryLoadLatestSession()
    }

    val pdfPicker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocument()
    ) { uri ->
        uri?.let {
            viewModel.setPdfUri(it)
            scope.launch {
                viewModel.startExtraction(context)
            }
        }
    }

    val logoPicker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocument()
    ) { uri ->
        uri ?: return@rememberLauncherForActivityResult

        val mimeType = context.contentResolver.getType(uri).orEmpty()
        val extension = when {
            mimeType.contains("png", ignoreCase = true) -> "png"
            mimeType.contains("webp", ignoreCase = true) -> "webp"
            mimeType.contains("gif", ignoreCase = true) -> "gif"
            mimeType.contains("heic", ignoreCase = true) || mimeType.contains("heif", ignoreCase = true) -> "heic"
            else -> "jpg"
        }

        val logoDir = java.io.File(context.filesDir, "college_logos").apply { mkdirs() }
        val targetFile = java.io.File(logoDir, "college_logo_${System.currentTimeMillis()}.$extension")

        val copied = runCatching {
            context.contentResolver.openInputStream(uri)?.use { input ->
                java.io.FileOutputStream(targetFile).use { output ->
                    input.copyTo(output)
                }
            }
            targetFile.exists() && targetFile.length() > 0
        }.getOrDefault(false)

        if (copied) {
            viewModel.setCollegeLogoUri(android.net.Uri.fromFile(targetFile).toString())
        }
    }

    val masterDataPicker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocument()
    ) { uri ->
        uri ?: return@rememberLauncherForActivityResult
        viewModel.importMasterData(context, uri)
    }

    val themeSelectionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == android.app.Activity.RESULT_OK) {
            val selectedTheme = result.data
                ?.getStringExtra(ExportThemeSelectionActivity.EXTRA_SELECTED_THEME)
                .orEmpty()
            if (selectedTheme.isNotBlank()) {
                viewModel.setPdfThemeSelection(selectedTheme)
            }
        }
    }

    fun openThemeSelection() {
        val previewChapter = uiState.chapters.firstOrNull(::isNormalPreviewChapter)
        themeSelectionLauncher.launch(
            Intent(context, ExportThemeSelectionActivity::class.java).apply {
                putExtra(ExportThemeSelectionActivity.EXTRA_CURRENT_THEME, uiState.pdfTheme)
                putExtra(ExportThemeSelectionActivity.EXTRA_THESIS_TITLE, uiState.thesisTitle)
                putExtra(ExportThemeSelectionActivity.EXTRA_PREVIEW_CHAPTER_TITLE, previewChapter?.name.orEmpty())
                putExtra(ExportThemeSelectionActivity.EXTRA_PREVIEW_CHAPTER_TEXT, previewTextForThemeSelection(previewChapter))
            }
        )
    }

    val exportLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.CreateDocument("application/pdf")
    ) { uri: Uri? ->
        uri?.let {
            exportDialogTitle = "Exporting PDF"
            scope.launch {
                viewModel.exportAllChaptersToUri(context, it)
            }
        }
    }

    val docxExportLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.CreateDocument("application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    ) { uri: Uri? ->
        uri?.let {
            exportDialogTitle = "Exporting DOCX"
            scope.launch {
                viewModel.exportAllChaptersToDocx(context, it)
            }
        }
    }

    val pptxExportLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.CreateDocument("application/vnd.openxmlformats-officedocument.presentationml.presentation")
    ) { uri: Uri? ->
        uri?.let {
            exportDialogTitle = "Exporting PPTX"
            scope.launch {
                viewModel.exportAllChaptersToPptx(context, it)
            }
        }
    }

    val tabs = listOf("Dashboard", "Variables", "Chapters", "Tables", "Figures", "Charts", "Abstracts", "References", "Master Chart", "Quality", "Worker", "Logs", "Analytics")

    LaunchedEffect(uiState.activeChapterName) {
        if (uiState.activeChapterName.isNotBlank()) {
            selectedTab = 2
        }
    }

    val allFigures by remember(uiState.chapters) {
        derivedStateOf {
            val distinctList = uiState.chapters.flatMap { chapter ->
                chapter.figures.map { figure ->
                    FigureAsset(chapterName = chapter.name, figure = figure)
                }
            }

            distinctList.distinctBy { "${it.figure.figureNumber}_${it.figure.title}" }
        }
    }

    val allCharts by remember(uiState.chapters) {
        derivedStateOf {
            val distinctList = uiState.chapters.flatMap { chapter ->
                chapter.charts.map { chart ->
                    ChartAsset(chapterName = chapter.name, chart = chart)
                }
            }

            distinctList.distinctBy { "${it.chapterName}_${it.chart.chartId}_${it.chart.title}_${it.chart.type}" }
        }
    }

    val allTables by remember(uiState.chapters) {
        derivedStateOf {
            val distinctList = uiState.chapters.flatMap { chapter ->
                chapter.tables.map { table ->
                    TableAsset(chapterName = chapter.name, table = table)
                }
            }

            distinctList.distinctBy { "${it.chapterName}_${it.table.tableNumber}_${it.table.title}" }
        }
    }

    val allReferences by remember(uiState.chapters, uiState.variables) {
        derivedStateOf {
            val canonicalReferences = uiState.verifiedPubMedReferences
                .map { reference ->
                    ReferenceAsset(
                        chapterName = "Verified References",
                        citation = reference.citation,
                        text = referenceDisplayText(reference),
                        pmid = reference.pmid.orEmpty(),
                        doi = reference.doi.orEmpty(),
                        pubmedVerified = reference.pubmedVerified
                    )
                }

            val chapterReferences = uiState.chapters.flatMap { chapter ->
                chapter.chapterReferences.map { reference ->
                    ReferenceAsset(
                        chapterName = chapter.name,
                        citation = reference.citation,
                        text = referenceDisplayText(reference),
                        pmid = reference.pmid.orEmpty(),
                        doi = reference.doi.orEmpty(),
                        pubmedVerified = reference.pubmedVerified
                    )
                }
            }

            val variableReferences = uiState.variables
                .firstOrNull { it.name.equals("References_Vancouver", ignoreCase = true) }
                ?.value
                ?.lines()
                ?.mapIndexedNotNull { index, line ->
                    val trimmed = line.trim()
                    if (trimmed.isBlank()) return@mapIndexedNotNull null
                    val pmid = Regex("""\bPMID\s*:?\s*(\d{4,12})\b""", RegexOption.IGNORE_CASE)
                        .find(trimmed)
                        ?.groupValues
                        ?.getOrNull(1)
                        .orEmpty()
                    val doi = Regex("""10\.\d{4,9}/[^\s<>"']+""", RegexOption.IGNORE_CASE)
                        .find(trimmed)
                        ?.value
                        ?.trimEnd('.', ',', ';')
                        .orEmpty()
                    ReferenceAsset(
                        chapterName = "References_Vancouver",
                        citation = Regex("""^\s*(?:\[(\d+)]|(\d+)[.)])""")
                            .find(trimmed)
                            ?.groupValues
                            ?.drop(1)
                            ?.firstOrNull { it.isNotBlank() }
                            ?.let { "[$it]" }
                            ?: "[${index + 1}]",
                        text = trimmed,
                        pmid = pmid,
                        doi = doi,
                        pubmedVerified = pmid.isNotBlank()
                    )
                }
                .orEmpty()

            (variableReferences + canonicalReferences + chapterReferences).distinctBy {
                when {
                    it.pmid.isNotBlank() -> "pmid:${it.pmid}"
                    it.doi.isNotBlank() -> "doi:${it.doi.lowercase()}"
                    else -> it.text.lowercase().replace(Regex("\\s+"), " ").take(180)
                }
            }.mapIndexed { index, reference ->
                reference.copy(citation = "[${index + 1}]")
            }
        }
    }
    val exportQualityChecks by remember(uiState, allReferences, allTables, allFigures) {
        derivedStateOf { buildExportQualityChecks(uiState, allReferences, allTables, allFigures) }
    }

    val completedCount by remember(uiState.chapters) {
        derivedStateOf { uiState.chapters.count { it.status == Chapter.ChapterStatus.SUCCESS } }
    }
    val failedCount by remember(uiState.chapters) {
        derivedStateOf { uiState.chapters.count { it.status == Chapter.ChapterStatus.ERROR } }
    }
    val pendingCount by remember(uiState.chapters) {
        derivedStateOf { uiState.chapters.count { it.status == Chapter.ChapterStatus.PENDING || it.status == Chapter.ChapterStatus.IDLE } }
    }
    val totalCount by remember(uiState.chapters) {
        derivedStateOf { uiState.chapters.size.coerceAtLeast(1) }
    }
    val qualityScore by remember(uiState.chapters, uiState.variables) {
        derivedStateOf {
            val completeness = ((completedCount.toFloat() / totalCount.toFloat()) * 100f).toInt()
            val figures = allFigures.size.coerceAtMost(20) * 5
            val references = uiState.verifiedPubMedReferences.size.coerceAtMost(100) / 2
            val methodology = if (uiState.chapters.any { it.name.equals("Materials and Methods", true) || it.name.equals("Methodology", true) }) 20 else 10
            ThesisQualityScore(
                overall = (completeness * 0.5f + figures * 0.2f + references * 0.15f + methodology * 0.15f).toInt().coerceIn(0, 100),
                completeness = completeness,
                figures = figures.coerceIn(0, 100),
                references = references.coerceIn(0, 100),
                methodology = methodology
            )
        }
    }

    LaunchedEffect(uiState.thesisTitle) {
        if (projectNameInput.isBlank()) projectNameInput = uiState.thesisTitle
    }

    if (showExportDialog) {
        AlertDialog(
            onDismissRequest = { showExportDialog = false },
            title = { Text("Export thesis") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    ExportDialogDesignHeader(
                        selection = uiState.pdfTheme,
                        onChange = {
                            showExportDialog = false
                            openThemeSelection()
                        }
                    )
                    ExportQualityChecklistPanel(
                        checks = exportQualityChecks,
                        compact = true
                    )
                    ExportFormatButton(
                        title = "PDF",
                        subtitle = "Final formatted thesis document",
                        primary = true,
                        icon = { Icon(Icons.Default.Description, contentDescription = null) },
                        onClick = {
                            showExportDialog = false
                            exportLauncher.launch("Thesis_Export_${System.currentTimeMillis()}.pdf")
                        }
                    )
                    ExportFormatButton(
                        title = "DOCX",
                        subtitle = "Editable Word-compatible report",
                        primary = false,
                        icon = { Icon(Icons.Default.Description, contentDescription = null) },
                        onClick = {
                            showExportDialog = false
                            docxExportLauncher.launch("Thesis_Export_${System.currentTimeMillis()}.docx")
                        }
                    )
                    ExportFormatButton(
                        title = "PPTX",
                        subtitle = "Presentation deck using selected design",
                        primary = false,
                        icon = { Icon(Icons.Default.ViewModule, contentDescription = null) },
                        onClick = {
                            showExportDialog = false
                            pptxExportLauncher.launch("Thesis_Export_${System.currentTimeMillis()}.pptx")
                        }
                    )
                }
            },
            confirmButton = {},
            dismissButton = {
                TextButton(onClick = { showExportDialog = false }) {
                    Text("Cancel")
                }
            }
        )
    }

    if (showLayoutPreviewDialog) {
        ExportLayoutPreviewDialog(
            theme = PdfTheme.fromName(uiState.pdfTheme),
            thesisTitle = uiState.thesisTitle.ifBlank { "Thesis Report" },
            onDismiss = { showLayoutPreviewDialog = false }
        )
    }

    if (showAiSettingsDialog) {
        ThesisAiSettingsDialog(
            uiState = uiState,
            onPdfThemeSelected = { theme -> viewModel.setPdfTheme(theme) },
            onVpsAutoCompleteChanged = { enabled -> viewModel.setVpsAutoCompleteEnabled(enabled) },
            onExportMarginChanged = { viewModel.setExportMargin(it) },
            onExportFontChanged = { viewModel.setExportFont(it) },
            onExportLineSpacingChanged = { viewModel.setExportLineSpacing(it) },
            onExportLogoPlacementChanged = { viewModel.setExportLogoPlacement(it) },
            onExportPageNumberingChanged = { viewModel.setExportPageNumbering(it) },
            onExportHeaderFooterChanged = { viewModel.setExportHeaderFooter(it) },
            onExportWatermarkChanged = { viewModel.setExportWatermark(it) },
            onExportAutoTocChanged = { viewModel.setExportAutoToc(it) },
            onExportAutoListsChanged = { viewModel.setExportAutoLists(it) },
            onDismiss = { showAiSettingsDialog = false }
        )
    }

    val showSessionLoadingDialog = uiState.processing && (
        uiState.status.contains("Loading session", ignoreCase = true) ||
            uiState.status.contains("Restoring session", ignoreCase = true) ||
            uiState.status.contains("Syncing existing verified cache only", ignoreCase = true)
        )

    if (showSessionLoadingDialog) {
        AlertDialog(
            onDismissRequest = {},
            title = { Text("Loading session") },
            text = {
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    CircularProgressIndicator()
                    Text(
                        text = uiState.status.ifBlank { "Loading saved thesis session..." },
                        style = MaterialTheme.typography.bodyMedium
                    )
                }
            },
            confirmButton = {}
        )
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .statusBarsPadding()
    ) {
        if (!tabFullView) {
            val topBarGradient = if (darkModeEnabled) {
                Brush.horizontalGradient(listOf(Color(0xFF0F172A), Color(0xFF1E293B)))
            } else {
                Brush.horizontalGradient(listOf(Color(0xFF0F5B92), Color(0xFF1D4ED8)))
            }
            val titleColor = if (darkModeEnabled) MaterialTheme.colorScheme.onSurface else Color.White
            val subtitleColor = if (darkModeEnabled) MaterialTheme.colorScheme.onSurfaceVariant else Color.White.copy(alpha = 0.8f)

            // Outer TopBar Box
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(topBarGradient)
                    .padding(top = 8.dp, bottom = 12.dp, start = 16.dp, end = 16.dp)
            ) {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    // Header Row
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            Image(
                                painter = painterResource(id = R.drawable.thesis_scholar_logo),
                                contentDescription = "Thesis Scholar logo",
                                modifier = Modifier
                                    .size(44.dp)
                                    .clip(RoundedCornerShape(8.dp))
                            )
                            Column {
                                Row(
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                                ) {
                                    Text(
                                        text = "Thesis Scholar",
                                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                                        color = titleColor
                                    )

                                    // Pulsing Status Indicator
                                    val infiniteTransition = rememberInfiniteTransition(label = "pulse")
                                    val pulseAlpha by infiniteTransition.animateFloat(
                                        initialValue = 0.3f,
                                        targetValue = 1.0f,
                                        animationSpec = infiniteRepeatable(
                                            animation = tween(1000, easing = LinearEasing),
                                            repeatMode = RepeatMode.Reverse
                                        ),
                                        label = "pulseAlpha"
                                    )
                                    val statusColor = when {
                                        uiState.processing -> Color(0xFF3B82F6) // Blue
                                        uiState.hasErrors -> Color(0xFFEF4444) // Red
                                        completedCount > 0 && pendingCount == 0 -> Color(0xFF10B981) // Green
                                        else -> Color(0xFF6B7280) // Grey
                                    }
                                    Box(
                                        modifier = Modifier
                                            .size(10.dp)
                                            .clip(RoundedCornerShape(5.dp))
                                            .background(statusColor.copy(alpha = if (uiState.processing) pulseAlpha else 1.0f))
                                    )
                                }
                                Text(
                                    text = if (uiState.thesisTitle.isNotBlank()) uiState.thesisTitle else "No project loaded",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = subtitleColor,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                    modifier = Modifier.widthIn(max = 200.dp)
                                )
                                Text(
                                    text = "Session: ${uiState.sessionId.takeLast(8)}",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = subtitleColor.copy(alpha = 0.6f)
                                )
                            }
                        }

                        // Top actions
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(4.dp)
                        ) {
                            if (uiState.hasErrors && !uiState.processing) {
                                IconButton(onClick = { viewModel.retryAllFailed() }) {
                                    Icon(
                                        Icons.Default.History,
                                        contentDescription = "Retry failed",
                                        tint = if (darkModeEnabled) MaterialTheme.colorScheme.error else Color(0xFFFCA5A5)
                                    )
                                }
                            }

                            IconButton(onClick = { openThemeSelection() }) {
                                Icon(
                                    Icons.Default.Settings,
                                    contentDescription = "Choose export design",
                                    tint = titleColor
                                )
                            }

                            IconButton(onClick = onToggleTheme) {
                                Icon(
                                    imageVector = if (darkModeEnabled) Icons.Default.LightMode else Icons.Default.DarkMode,
                                    contentDescription = "Toggle theme",
                                    tint = titleColor
                                )
                            }

                            Box {
                                IconButton(onClick = { showTopActionsMenu = true }) {
                                    Icon(
                                        Icons.Default.MoreVert,
                                        contentDescription = "More actions",
                                        tint = titleColor
                                    )
                                }
                                DropdownMenu(
                                    expanded = showTopActionsMenu,
                                    onDismissRequest = { showTopActionsMenu = false }
                                ) {
                                    if (uiState.chapters.any { it.status == Chapter.ChapterStatus.SUCCESS }) {
                                        DropdownMenuItem(
                                            text = { Text("Preview Layout") },
                                            leadingIcon = { Icon(Icons.AutoMirrored.Filled.OpenInNew, contentDescription = null) },
                                            onClick = {
                                                showTopActionsMenu = false
                                                openThemeSelection()
                                            }
                                        )
                                        DropdownMenuItem(
                                            text = { Text("Export") },
                                            leadingIcon = { Icon(Icons.Default.Description, contentDescription = null) },
                                            onClick = {
                                                showTopActionsMenu = false
                                                showExportDialog = true
                                            }
                                        )
                                        DropdownMenuItem(
                                            text = { Text("Generate Poster") },
                                            leadingIcon = { Icon(Icons.Default.Analytics, contentDescription = null) },
                                            onClick = {
                                                showTopActionsMenu = false
                                                val payload = buildPosterPayloadFromThesis(uiState)
                                                context.startActivity(
                                                    Intent(context, PosterAnalysisActivity::class.java).apply {
                                                        putExtra(PosterAnalysisActivity.EXTRA_THESIS_POSTER_PAYLOAD, payload)
                                                        putExtra(PosterAnalysisActivity.EXTRA_AUTO_GENERATE_POSTER, true)
                                                    }
                                                )
                                            }
                                        )
                                    }
                                    DropdownMenuItem(
                                        text = { Text("Previous sessions") },
                                        leadingIcon = { Icon(Icons.Default.FolderOpen, contentDescription = null) },
                                        onClick = {
                                            showTopActionsMenu = false
                                            showSessionsDialog = true
                                        }
                                    )
                                    DropdownMenuItem(
                                        text = { Text("New project") },
                                        leadingIcon = { Icon(Icons.Default.Add, contentDescription = null) },
                                        onClick = {
                                            showTopActionsMenu = false
                                            showProjectDialog = true
                                        }
                                    )
                                }
                            }
                        }
                    }

                    // Stat Cards Row
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        // Completed Card
                        Box(
                            modifier = Modifier
                                .weight(1f)
                                .clip(RoundedCornerShape(8.dp))
                                .background(if (darkModeEnabled) Color(0xFF065F46) else Color(0xFFD1FAE5))
                                .padding(horizontal = 8.dp, vertical = 6.dp)
                        ) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
                                Text("Completed", style = MaterialTheme.typography.labelSmall, color = if (darkModeEnabled) Color(0xFFA7F3D0) else Color(0xFF065F46))
                                Text("$completedCount", style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold), color = if (darkModeEnabled) Color.White else Color(0xFF065F46))
                            }
                        }
                        // Failed Card
                        Box(
                            modifier = Modifier
                                .weight(1f)
                                .clip(RoundedCornerShape(8.dp))
                                .background(if (darkModeEnabled) Color(0xFF7F1D1D) else Color(0xFFFEE2E2))
                                .padding(horizontal = 8.dp, vertical = 6.dp)
                        ) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
                                Text("Failed", style = MaterialTheme.typography.labelSmall, color = if (darkModeEnabled) Color(0xFFFCA5A5) else Color(0xFF7F1D1D))
                                Text("$failedCount", style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold), color = if (darkModeEnabled) Color.White else Color(0xFF7F1D1D))
                            }
                        }
                        // Pending Card
                        Box(
                            modifier = Modifier
                                .weight(1f)
                                .clip(RoundedCornerShape(8.dp))
                                .background(if (darkModeEnabled) Color(0xFF1E3A8A) else Color(0xFFDBEAFE))
                                .padding(horizontal = 8.dp, vertical = 6.dp)
                        ) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
                                Text("Pending", style = MaterialTheme.typography.labelSmall, color = if (darkModeEnabled) Color(0xFF93C5FD) else Color(0xFF1E3A8A))
                                Text("$pendingCount", style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold), color = if (darkModeEnabled) Color.White else Color(0xFF1E3A8A))
                            }
                        }
                        // Score Card
                        Box(
                            modifier = Modifier
                                .weight(1.2f)
                                .clip(RoundedCornerShape(8.dp))
                                .background(if (darkModeEnabled) Color(0xFF311042) else Color(0xFFF5E6FA))
                                .padding(horizontal = 8.dp, vertical = 6.dp)
                        ) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
                                Text("Quality Score", style = MaterialTheme.typography.labelSmall, color = if (darkModeEnabled) Color(0xFFE9D5FF) else Color(0xFF701A75))
                                Text("${qualityScore.overall}%", style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold), color = if (darkModeEnabled) Color.White else Color(0xFF701A75))
                            }
                        }
                    }
                }
            }

            // College Logo & Progress Indicators
            if (uiState.collegeLogoUri.isNotBlank()) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 6.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    SubcomposeAsyncImage(
                        model = uiState.collegeLogoUri,
                        contentDescription = "College logo",
                        modifier = Modifier.size(36.dp),
                        contentScale = ContentScale.Fit
                    )
                    Column(modifier = Modifier.weight(1f)) {
                        Text("College logo loaded", style = MaterialTheme.typography.labelMedium)
                    }
                    TextButton(onClick = { viewModel.clearCollegeLogo() }) {
                        Text("Remove", style = MaterialTheme.typography.labelSmall)
                    }
                }
            }

            if (uiState.processing) {
                val hasProgressTotal = uiState.progressTotal > 0
                val progress = progressFraction(uiState.progressCurrent, uiState.progressTotal)
                val percentText = progressPercentText(uiState.progressCurrent, uiState.progressTotal)

                Column(
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 6.dp),
                    verticalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    if (hasProgressTotal) {
                        LinearProgressIndicator(
                            progress = { progress },
                            modifier = Modifier.fillMaxWidth()
                        )
                    } else {
                        LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
                    }
                    Text(
                        text = if (hasProgressTotal) {
                            "${uiState.status} - $percentText (${uiState.progressCurrent}/${uiState.progressTotal})"
                        } else {
                            uiState.status
                        },
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            } else {
                Text(
                    text = uiState.status,
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 6.dp)
                )
            }
        }

        // Inner Column for padded content
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f)
                .padding(horizontal = 16.dp)
        ) {
            Spacer(modifier = Modifier.height(8.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.End
            ) {
                TextButton(onClick = { tabFullView = !tabFullView }) {
                    Text(if (tabFullView) "Restore ui" else "Full view")
                }
            }

        Surface(
            modifier = Modifier.fillMaxWidth(),
            tonalElevation = 1.dp
        ) {
            PrimaryScrollableTabRow(
                selectedTabIndex = selectedTab,
                edgePadding = 0.dp
            ) {
            tabs.forEachIndexed { index, title ->
                Tab(
                    selected = selectedTab == index,
                    onClick = { selectedTab = index },
                    text = { Text(title) },
                    icon = when (index) {
                        0 -> ({ Icon(Icons.Default.ViewModule, contentDescription = null) })
                        1 -> ({ Icon(Icons.Default.Description, contentDescription = null) })
                        2 -> ({ Icon(Icons.Default.FolderOpen, contentDescription = null) })
                        3 -> ({ Icon(Icons.AutoMirrored.Filled.OpenInNew, contentDescription = null) })
                        10 -> ({ Icon(Icons.Default.Settings, contentDescription = null) })
                        11 -> ({ Icon(Icons.Default.History, contentDescription = null) })
                        else -> ({ Icon(Icons.Default.Analytics, contentDescription = null) })
                    }
                )
            }
            }
        }

        Spacer(modifier = Modifier.height(6.dp))

        TabActionsBar(
            selectedTab = selectedTab,
            isGridViewEnabled = isGridViewEnabled,
            onToggleGridView = { isGridViewEnabled = !isGridViewEnabled },
            expandAllContents = expandAllContents,
            onToggleExpandAll = { expandAllContents = !expandAllContents },
            uiState = uiState,
            viewModel = viewModel
        )

        Spacer(modifier = Modifier.height(12.dp))

        Box(modifier = Modifier.weight(1f).fillMaxWidth()) {
            when (selectedTab) {
                0 -> DashboardScreen(
                    uiState = uiState,
                    qualityScore = qualityScore,
                    onSaveTitle = { viewModel.setThesisTitle(it) },
                    onResume = { viewModel.startChapterGeneration() },
                    onSyncCache = { viewModel.syncVerifiedReferenceCacheNow() },
                    onGenerateMasterChart = { viewModel.generateMasterChartTemplate() },
                    onCopyMasterChart = { clipboardManager.setText(AnnotatedString(uiState.masterChartCsv)) },
                    onSelectTab = { selectedTab = it }
                )

                1 -> {
                    if (uiState.variables.isNotEmpty()) {
                        VariablesEditorScreen(
                            variables = uiState.variables,
                            onVariableUpdate = { name, value -> viewModel.updateVariable(name, value) },
                            onContinue = { viewModel.startChapterGeneration() }
                        )
                    } else {
                        EmptyStateCard(
                            title = "No variables yet",
                            subtitle = "Select a PDF first to extract thesis variables."
                        )
                    }
                }

                2 -> {
                    if (uiState.chapters.isNotEmpty()) {
                        ChaptersScreen(
                            chapters = uiState.chapters,
                            activeChapterName = uiState.activeChapterName,
                            viewModel = viewModel,
                            onCopy = { content -> clipboardManager.setText(AnnotatedString(content)) },
                            onShowFigures = { selectedTab = 4 },
                            onShowTables = { selectedTab = 3 },
                            onShowCharts = { selectedTab = 5 },
                            isGridViewEnabled = isGridViewEnabled,
                            expandAllContents = expandAllContents,
                            onOpenReader = { activeChapterReaderItem = it }
                        )
                    } else {
                        EmptyStateCard(
                            title = "No chapters yet",
                            subtitle = "Start extraction to generate thesis chapters."
                        )
                    }
                }

                3 -> {
                    if (allTables.isNotEmpty() || uiState.chapters.any { it.status == Chapter.ChapterStatus.LOADING }) {
                        TablesScreen(
                            tables = allTables,
                            isProcessing = uiState.processing,
                            onRetryTables = {
                                viewModel.startChapterGeneration()
                            }
                        )
                    } else {
                        EmptyStateCard(
                            title = "No tables found",
                            subtitle = "Tables will appear here after chapter generation."
                        )
                    }
                }

                4 -> {
                    if (allFigures.isNotEmpty() || uiState.chapters.any { it.status == Chapter.ChapterStatus.LOADING }) {
                        FiguresScreen(
                            figures = allFigures,
                            pubMedFigures = uiState.pubMedFigures,
                            references = allReferences,
                            isProcessing = uiState.processing,
                            onRetryFigures = {
                                viewModel.startChapterGeneration()
                            },
                            onSearchGoogle = { query ->
                                val intent = Intent(Intent.ACTION_VIEW, Uri.parse("https://www.google.com/search?q=${Uri.encode(query)}&tbm=isch"))
                                context.startActivity(intent)
                            },
                            onUpdateImageUrl = { chapterName, figureNumber, newUrl ->
                                // This assumes updateFigureImageUrl exists in ViewModel
                                viewModel.updateFigureImageUrl(chapterName, figureNumber, newUrl)
                            }
                        )
                    } else {
                        EmptyStateCard(
                            title = "No figures found",
                            subtitle = "Figures will appear here after chapter generation."
                        )
                    }
                }

                5 -> {
                    if (allCharts.isNotEmpty() || uiState.chapters.any { it.status == Chapter.ChapterStatus.LOADING }) {
                        ChartsScreen(
                            charts = allCharts,
                            isProcessing = uiState.processing,
                            onRetryCharts = {
                                viewModel.startChapterGeneration()
                            }
                        )
                    } else {
                        EmptyStateCard(
                            title = "No charts found",
                            subtitle = "Charts will appear here after chapter generation."
                        )
                    }
                }

                6 -> {
                    AbstractsScreen(
                        sources = uiState.verifiedPubMedAbstractSources,
                        verifiedReferenceCount = uiState.verifiedPubMedReferences.size,
                        lastSyncedAt = uiState.referenceCacheLastSyncedAt,
                        syncInProgress = uiState.referenceCacheSyncInProgress,
                        syncCurrent = uiState.referenceCacheSyncCurrent,
                        syncTotal = uiState.referenceCacheSyncTotal,
                        syncError = uiState.referenceCacheSyncError,
                        isProcessing = uiState.processing,
                        onRefresh = { viewModel.refreshReferenceCorpus() },
                        onSyncCache = { viewModel.syncVerifiedReferenceCacheNow() }
                    )
                }

                7 -> {
                    if (allReferences.isNotEmpty() || uiState.chapters.any { it.status == Chapter.ChapterStatus.LOADING }) {
                        ReferencesScreen(
                            references = allReferences,
                            abstractCount = uiState.verifiedPubMedAbstractSources.size,
                            similarArticleCount = uiState.verifiedPubMedAbstractSources.sumOf { it.similarArticles.size + it.citedBy.size },
                            lastSyncedAt = uiState.referenceCacheLastSyncedAt,
                            syncInProgress = uiState.referenceCacheSyncInProgress,
                            syncCurrent = uiState.referenceCacheSyncCurrent,
                            syncTotal = uiState.referenceCacheSyncTotal,
                            syncError = uiState.referenceCacheSyncError,
                            onSyncCache = { viewModel.syncVerifiedReferenceCacheNow() },
                            onJumpToChapter = { selectedTab = 2 },
                            isProcessing = uiState.processing,
                            onRetryReferences = {
                                viewModel.startChapterGeneration()
                            }
                        )
                    } else {
                        EmptyStateCard(
                            title = "No references found",
                            subtitle = "References will appear here as chapters are generated."
                        )
                    }
                }

                8 -> {
                    MasterChartScreen(
                        uiState = uiState,
                        onGenerate = { viewModel.generateMasterChartTemplate() },
                        onImportData = {
                            masterDataPicker.launch(
                                arrayOf(
                                    "text/*",
                                    "text/csv",
                                    "application/csv",
                                    "application/vnd.ms-excel",
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
                            )
                        },
                        onCopyCsv = { clipboardManager.setText(AnnotatedString(uiState.masterChartCsv)) },
                        onGoVariables = { selectedTab = 1 },
                        onGoChapters = { selectedTab = 2 }
                    )
                }

                9 -> {
                    QualityCheckScreen(
                        checks = exportQualityChecks,
                        uiState = uiState,
                        references = allReferences,
                        tables = allTables,
                        figures = allFigures,
                        onExport = { showExportDialog = true },
                        onGoReferences = { selectedTab = 7 },
                        onGoChapters = { selectedTab = 2 },
                        onGoWorker = { selectedTab = 10 }
                    )
                }

                10 -> {
                    WorkerActivityScreen(
                        uiState = uiState,
                        viewModel = viewModel,
                        onSelectTab = { selectedTab = it }
                    )
                }

                11 -> {
                    ThesisLogsScreen(
                        logs = uiState.aiLogs,
                        chapters = uiState.chapters,
                        onCopy = { content -> clipboardManager.setText(AnnotatedString(content)) },
                        onClear = { viewModel.clearAiLogs() }
                    )
                }

                else -> AnalyticsScreen(
                    uiState = uiState,
                    qualityScore = qualityScore,
                    onRetryFailed = { viewModel.retryAllFailed() },
                    onSelectTab = { selectedTab = it }
                )
            }
        }

        Spacer(modifier = Modifier.height(12.dp))

        Surface(
            modifier = Modifier
                .fillMaxWidth()
                .navigationBarsPadding(),
            tonalElevation = 2.dp,
            shadowElevation = 1.dp
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState())
                    .padding(horizontal = 16.dp, vertical = 10.dp),
                horizontalArrangement = Arrangement.spacedBy(10.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Button(
                    onClick = {
                        pdfPicker.launch(
                            arrayOf(
                                "application/pdf",
                                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                                "application/vnd.ms-powerpoint",
                                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                "application/msword",
                                "text/*",
                                "image/*",
                                "*/*"
                            )
                        )
                    },
                    enabled = !uiState.processing
                ) {
                    Text("Select Document")
                }

                OutlinedButton(
                    onClick = { logoPicker.launch(arrayOf("image/*")) },
                    enabled = !uiState.processing
                ) {
                    Icon(Icons.Default.Add, contentDescription = null)
                    Spacer(modifier = Modifier.size(8.dp))
                    Text("Add College Logo")
                }

                ExportDesignControlCard(
                    selection = uiState.pdfTheme,
                    enabled = !uiState.processing,
                    onClick = { openThemeSelection() },
                    modifier = Modifier.widthIn(min = 230.dp, max = 330.dp)
                )

                val isProviderSelectionLocked = uiState.processing || uiState.chapters.any { it.status == Chapter.ChapterStatus.LOADING }
                var expanded by remember { mutableStateOf(false) }
                ExposedDropdownMenuBox(
                    expanded = expanded,
                    onExpandedChange = { if (!isProviderSelectionLocked) expanded = !expanded }
                ) {
                    OutlinedTextField(
                        value = uiState.selectedProvider,
                        onValueChange = {},
                        readOnly = true,
                        enabled = !isProviderSelectionLocked,
                        label = { Text("AI Provider") },
                        trailingIcon = {
                            ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded)
                        },
                        modifier = Modifier
                            .widthIn(min = 180.dp, max = 240.dp)
                            .menuAnchor()
                    )

                    ExposedDropdownMenu(
                        expanded = expanded && !isProviderSelectionLocked,
                        onDismissRequest = { expanded = false }
                    ) {
                        thesisAiProviderOptions().forEach { provider ->
                            DropdownMenuItem(
                                text = { Text(provider) },
                                onClick = {
                                    viewModel.setProvider(provider)
                                    expanded = false
                                }
                            )
                        }
                    }
                }

                OutlinedButton(
                    onClick = {
                        viewModel.createNewSession(projectNameInput.trim())
                        selectedTab = 0
                    },
                    enabled = !uiState.processing
                ) {
                    Text("New Project")
                }
            }
        }
        }
    }

    uiState.loadingState?.let { loadingMsg ->
        Dialog(onDismissRequest = {}) {
            Surface(
                shape = RoundedCornerShape(12.dp),
                color = MaterialTheme.colorScheme.surface,
                tonalElevation = 6.dp,
                modifier = Modifier.widthIn(max = 320.dp)
            ) {
                Column(
                    modifier = Modifier.padding(24.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    CircularProgressIndicator()
                    Text(
                        text = loadingMsg,
                        style = MaterialTheme.typography.bodyMedium,
                        textAlign = androidx.compose.ui.text.style.TextAlign.Center,
                        fontWeight = FontWeight.SemiBold
                    )
                }
            }
        }
    }

    if (activeChapterReaderItem != null) {
        BrilliantChapterReaderDialog(
            chapter = activeChapterReaderItem!!,
            viewModel = viewModel,
            onDismiss = { activeChapterReaderItem = null },
            onCopy = { content -> clipboardManager.setText(AnnotatedString(content)) },
            onRetry = { c, prompt -> viewModel.retryChapter(c, prompt) },
            onShowFigures = { selectedTab = 4; activeChapterReaderItem = null },
            onShowTables = { selectedTab = 3; activeChapterReaderItem = null },
            onShowCharts = { selectedTab = 5; activeChapterReaderItem = null }
        )
    }

    if (showProjectDialog) {
        AlertDialog(
            onDismissRequest = { showProjectDialog = false },
            title = { Text("New Project") },
            text = {
                Column {
                    Text(
                        text = "Create a fresh thesis session or rename the current project.",
                        style = MaterialTheme.typography.bodySmall
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    OutlinedTextField(
                        value = projectNameInput,
                        onValueChange = { projectNameInput = it },
                        label = { Text("Project / Thesis title") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    viewModel.createNewSession(projectNameInput.trim())
                    viewModel.setThesisTitle(projectNameInput.trim())
                    showProjectDialog = false
                    selectedTab = 0
                }) {
                    Text("Create")
                }
            },
            dismissButton = {
                TextButton(onClick = { showProjectDialog = false }) {
                    Text("Cancel")
                }
            }
        )
    }

    if (showSessionsDialog) {
        AlertDialog(
            onDismissRequest = { showSessionsDialog = false },
            title = { Text("Previous Sessions") },
            text = {
                Column(
                    modifier = Modifier.fillMaxWidth()
                ) {
                    if (uiState.previousSessions.isEmpty()) {
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(24.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            Text("No saved sessions found.")
                        }
                    } else {
                        LazyColumn(
                            modifier = Modifier.height(350.dp),
                            verticalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            items(
                                items = uiState.previousSessions,
                                key = { it.sessionId }
                            ) { session ->
                                ElevatedCard(
                                    modifier = Modifier.fillMaxWidth(),
                                    onClick = {
                                        viewModel.loadSession(
                                            session.sessionId
                                        )
                                        showSessionsDialog = false
                                        selectedTab = 0
                                    }
                                ) {
                                    Column(
                                        modifier = Modifier.padding(12.dp)
                                    ) {
                                        Text(
                                            text = session.thesisTitle.ifBlank {
                                                "Untitled Project"
                                            },
                                            style = MaterialTheme.typography.titleMedium,
                                            fontWeight = FontWeight.SemiBold
                                        )
                                        Spacer(
                                            modifier = Modifier.height(4.dp)
                                        )
                                        Text(
                                            text = "Chapters: ${session.chaptersCount}",
                                            style = MaterialTheme.typography.bodySmall
                                        )
                                        Text(
                                            text = "Session: ${
                                                session.sessionId.takeLast(10)
                                            }",
                                            style = MaterialTheme.typography.bodySmall
                                        )
                                        Text(
                                            text = java.text.SimpleDateFormat(
                                                "dd MMM yyyy HH:mm",
                                                java.util.Locale.getDefault()
                                            ).format(
                                                java.util.Date(session.timestamp)
                                            ),
                                            style = MaterialTheme.typography.bodySmall
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            },
            confirmButton = {},
            dismissButton = {
                TextButton(onClick = { showSessionsDialog = false }) {
                    Text("Close")
                }
            }
        )
    }

    exportDialogTitle?.let { title ->
        val statusLower = uiState.status.lowercase()
        val exportFinished = !uiState.processing && (
            statusLower.contains("exported") ||
                statusLower.contains("export failed") ||
                statusLower.contains("pdf export failed") ||
                statusLower.contains("docx export failed") ||
                statusLower.contains("pptx export failed")
            )

        AlertDialog(
            onDismissRequest = {
                if (exportFinished) exportDialogTitle = null
            },
            title = { Text(title) },
            text = {
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(14.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    if (!exportFinished) {
                        CircularProgressIndicator()
                    }
                    Text(
                        text = uiState.status.ifBlank { "Preparing export..." },
                        style = MaterialTheme.typography.bodyMedium
                    )
                    if (!exportFinished) {
                        val hasProgressTotal = uiState.progressTotal > 0
                        if (hasProgressTotal) {
                            LinearProgressIndicator(
                                progress = { progressFraction(uiState.progressCurrent, uiState.progressTotal) },
                                modifier = Modifier.fillMaxWidth()
                            )
                            Text(
                                text = "${progressPercentText(uiState.progressCurrent, uiState.progressTotal)} (${uiState.progressCurrent}/${uiState.progressTotal})",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        } else {
                            LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
                        }
                    }
                }
            },
            confirmButton = {
                if (exportFinished) {
                    TextButton(onClick = { exportDialogTitle = null }) {
                        Text("Close")
                    }
                }
            }
        )
    }

    if (pubMedFigureDialogVisible) {
        val statusLower = uiState.status.lowercase()
        val downloadFinished = !uiState.processing && (
            statusLower.contains("pubmed figures downloaded")
            )

        AlertDialog(
            onDismissRequest = {
                if (downloadFinished) pubMedFigureDialogVisible = false
            },
            title = { Text("Downloading PubMed Figures") },
            text = {
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(14.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    if (!downloadFinished) {
                        CircularProgressIndicator()
                    }
                    Text(
                        text = uiState.status.ifBlank { "Checking PubMed references..." },
                        style = MaterialTheme.typography.bodyMedium
                    )
                    Text(
                        text = "${uiState.pubMedFigures.size} figures cached",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    if (!downloadFinished) {
                        LinearProgressIndicator(
                            progress = progressFraction(uiState.progressCurrent, uiState.progressTotal),
                            modifier = Modifier.fillMaxWidth()
                        )
                        Text(
                            text = "${progressPercentText(uiState.progressCurrent, uiState.progressTotal)} (${uiState.progressCurrent}/${uiState.progressTotal.coerceAtLeast(1)} references checked)",
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                }
            },
            confirmButton = {
                if (downloadFinished) {
                    TextButton(onClick = { pubMedFigureDialogVisible = false }) {
                        Text("Close")
                    }
                }
            },
            dismissButton = {
                if (!downloadFinished) {
                    TextButton(onClick = { pubMedFigureDialogVisible = false }) {
                        Text("Work in background")
                    }
                }
            }
        )
    }

    uiState.referenceValidationState?.let { validation ->
        AlertDialog(
            onDismissRequest = { viewModel.dismissReferenceValidation() },
            title = { Text("PubMed reference check") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(
                        text = "These references could not be resolved to a PubMed PMID, so they cannot be used.",
                        style = MaterialTheme.typography.bodySmall
                    )

                    LazyColumn(
                        modifier = Modifier.height(340.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        items(
                            items = validation.issues,
                            key = { "${it.citation}_${it.originalText}" }
                        ) { issue ->
                            ElevatedCard(modifier = Modifier.fillMaxWidth()) {
                                Column(
                                    modifier = Modifier.padding(12.dp),
                                    verticalArrangement = Arrangement.spacedBy(6.dp)
                                ) {
                                    Text(
                                        text = "Reference ${issue.citation}",
                                        style = MaterialTheme.typography.titleSmall,
                                        fontWeight = FontWeight.SemiBold
                                    )
                                    Text(
                                        text = issue.issue,
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.error
                                    )
                                    Text(
                                        text = "Original: ${issue.originalText}",
                                        style = MaterialTheme.typography.bodySmall
                                    )
                                    if (issue.updatedText.isNotBlank()) {
                                        Text(
                                            text = "PubMed: ${issue.updatedText}",
                                            style = MaterialTheme.typography.bodySmall,
                                            color = MaterialTheme.colorScheme.primary
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            },
            confirmButton = {
                if (validation.canApply) {
                    TextButton(onClick = { viewModel.confirmReferenceValidationAndGenerate() }) {
                        Text("Use PubMed updates")
                    }
                }
            },
            dismissButton = {
                TextButton(onClick = { viewModel.dismissReferenceValidation() }) {
                    Text("Close")
                }
            }
        )
    }

    uiState.referenceUpdateNoticeState?.let { notice ->
        AlertDialog(
            onDismissRequest = { viewModel.dismissReferenceUpdateNotice() },
            title = { Text("PubMed references updated") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(
                        text = "The rough references were corrected with PubMed metadata before generation.",
                        style = MaterialTheme.typography.bodySmall
                    )

                    LazyColumn(
                        modifier = Modifier.height(340.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        items(
                            items = notice.issues,
                            key = { "${it.citation}_${it.originalText}" }
                        ) { issue ->
                            ElevatedCard(modifier = Modifier.fillMaxWidth()) {
                                Column(
                                    modifier = Modifier.padding(12.dp),
                                    verticalArrangement = Arrangement.spacedBy(6.dp)
                                ) {
                                    Text(
                                        text = "Reference ${issue.citation}",
                                        style = MaterialTheme.typography.titleSmall,
                                        fontWeight = FontWeight.SemiBold
                                    )
                                    Text(
                                        text = issue.issue,
                                        style = MaterialTheme.typography.bodySmall
                                    )
                                    Text(
                                        text = "Original: ${issue.originalText}",
                                        style = MaterialTheme.typography.bodySmall
                                    )
                                    if (issue.updatedText.isNotBlank()) {
                                        Text(
                                            text = "Updated: ${issue.updatedText}",
                                            style = MaterialTheme.typography.bodySmall,
                                            color = MaterialTheme.colorScheme.primary
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { viewModel.dismissReferenceUpdateNotice() }) {
                    Text("Close")
                }
            }
        )
    }
}

@Composable
fun DashboardScreen(
    uiState: ThesisViewModel.UiState,
    qualityScore: ThesisQualityScore,
    onSaveTitle: (String) -> Unit,
    onResume: () -> Unit,
    onSyncCache: () -> Unit,
    onGenerateMasterChart: () -> Unit,
    onCopyMasterChart: () -> Unit,
    onSelectTab: (Int) -> Unit
) {
    val scroll = rememberScrollState()
    val failed = uiState.chapters.count { it.status == Chapter.ChapterStatus.ERROR }
    val running = uiState.chapters.count { it.status == Chapter.ChapterStatus.LOADING }
    val completed = uiState.chapters.count { it.status == Chapter.ChapterStatus.SUCCESS }
    val nextAction = when {
        uiState.variables.isEmpty() -> "Select PDF"
        failed > 0 -> "Review failed chapters"
        completed < uiState.chapters.size -> "Resume generation"
        uiState.verifiedPubMedReferences.isEmpty() -> "Refresh references"
        else -> "Export or review analytics"
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(scroll),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        ElevatedCard(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Current Project", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                OutlinedTextField(
                    value = uiState.thesisTitle,
                    onValueChange = onSaveTitle,
                    label = { Text("Project title") },
                    modifier = Modifier.fillMaxWidth()
                )
                Text("Progress: ${uiState.completionPercent}%", style = MaterialTheme.typography.bodyMedium)
                LinearProgressIndicator(
                    progress = { uiState.completionPercent.coerceIn(0, 100) / 100f },
                    modifier = Modifier.fillMaxWidth()
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    AssistChip(onClick = { onSelectTab(2) }, label = { Text("$completed done") })
                    AssistChip(onClick = { onSelectTab(10) }, label = { Text("$failed failed") })
                    AssistChip(onClick = { onSelectTab(2) }, label = { Text("$running running") })
                }
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Button(onClick = onResume, modifier = Modifier.weight(1f)) {
                        Text("Resume / Continue Generation")
                    }
                    Spacer(modifier = Modifier.width(8.dp))
                    ProviderStatusBadge(uiState = uiState)
                }
            }
        }

        MasterChartDashboardCard(
            columns = uiState.masterChartColumns,
            csv = uiState.masterChartCsv,
            generatedAt = uiState.masterChartGeneratedAt,
            canGenerate = uiState.variables.isNotEmpty() || uiState.chapters.any { it.status == Chapter.ChapterStatus.SUCCESS },
            onGenerate = onGenerateMasterChart,
            onCopy = onCopyMasterChart
        )

        ElevatedCard(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("Next Action", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                Text(nextAction, style = MaterialTheme.typography.bodyMedium)
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(
                        onClick = {
                            when {
                                uiState.variables.isEmpty() -> onSelectTab(1)
                                failed > 0 -> onSelectTab(10)
                                completed < uiState.chapters.size -> onResume()
                                uiState.verifiedPubMedReferences.isEmpty() -> onSelectTab(7)
                                else -> onSelectTab(12)
                            }
                        }
                    ) {
                        Text(nextAction)
                    }
                    OutlinedButton(onClick = { onSelectTab(2) }) { Text("Chapters") }
                    OutlinedButton(onClick = { onSelectTab(7) }) { Text("References") }
                    OutlinedButton(onClick = { onSelectTab(10) }) { Text("Worker") }
                    OutlinedButton(onClick = { onSelectTab(11) }) { Text("Logs") }
                    OutlinedButton(onClick = { onSelectTab(12) }) { Text("Analytics") }
                }
            }
        }

        ReferenceCacheSyncCard(
            verifiedReferenceCount = uiState.verifiedPubMedReferences.size,
            abstractCount = uiState.verifiedPubMedAbstractSources.size,
            similarArticleCount = uiState.verifiedPubMedAbstractSources.sumOf { it.similarArticles.size + it.citedBy.size },
            lastSyncedAt = uiState.referenceCacheLastSyncedAt,
            syncInProgress = uiState.referenceCacheSyncInProgress,
            syncCurrent = uiState.referenceCacheSyncCurrent,
            syncTotal = uiState.referenceCacheSyncTotal,
            syncError = uiState.referenceCacheSyncError,
            onSyncCache = onSyncCache
        )

        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxWidth()) {
            StatCard(title = "Variables", value = uiState.variables.size.toString(), modifier = Modifier.weight(1f))
            StatCard(title = "Chapters", value = uiState.chapters.size.toString(), modifier = Modifier.weight(1f))
            StatCard(title = "Figures", value = uiState.chapters.sumOf { it.figures.size }.toString(), modifier = Modifier.weight(1f))
        }

        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxWidth()) {
            StatCard(title = "References", value = uiState.chapters.sumOf { it.chapterReferences.size }.toString(), modifier = Modifier.weight(1f))
            StatCard(title = "Failed", value = uiState.chapters.count { it.status == Chapter.ChapterStatus.ERROR }.toString(), modifier = Modifier.weight(1f))
            StatCard(title = "Quality", value = "${qualityScore.overall}/100", modifier = Modifier.weight(1f))
        }

        ElevatedCard(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Research Quality", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                LinearProgressIndicator(
                    progress = { qualityScore.overall.coerceIn(0, 100) / 100f },
                    modifier = Modifier.fillMaxWidth()
                )
                Text("Completeness: ${qualityScore.completeness}/100", style = MaterialTheme.typography.bodySmall)
                Text("Figures: ${qualityScore.figures}/100", style = MaterialTheme.typography.bodySmall)
                Text("References: ${qualityScore.references}/100", style = MaterialTheme.typography.bodySmall)
                Text("Methodology: ${qualityScore.methodology}/100", style = MaterialTheme.typography.bodySmall)
            }
        }

        ElevatedCard(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Session Snapshot", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                Text("Session ID: ${uiState.sessionId}", style = MaterialTheme.typography.bodySmall)
                Text("Provider: ${uiState.selectedProvider}", style = MaterialTheme.typography.bodySmall)
                Text("Status: ${uiState.status}", style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
fun MasterChartDashboardCard(
    columns: List<MasterChartColumnJson>,
    csv: String,
    generatedAt: Long,
    canGenerate: Boolean,
    onGenerate: () -> Unit,
    onCopy: () -> Unit
) {
    ElevatedCard(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    Text("Master Chart Template", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                    Text(
                        if (columns.isEmpty()) "Generate a blank data sheet and data dictionary from this thesis."
                        else "${columns.size} variables ready for Excel/CSV entry.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    if (generatedAt > 0L) {
                        Text(
                            "Generated: " + java.text.SimpleDateFormat("yyyy-MM-dd HH:mm", java.util.Locale.getDefault()).format(java.util.Date(generatedAt)),
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
                Surface(
                    color = if (columns.isEmpty()) MaterialTheme.colorScheme.secondaryContainer else Color(0xFFE8F5E9),
                    contentColor = if (columns.isEmpty()) MaterialTheme.colorScheme.onSecondaryContainer else Color(0xFF2E7D32),
                    shape = RoundedCornerShape(6.dp)
                ) {
                    Text(
                        if (columns.isEmpty()) "Not made" else "Ready",
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                        style = MaterialTheme.typography.labelSmall,
                        fontWeight = FontWeight.Bold
                    )
                }
            }

            if (columns.isNotEmpty()) {
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    columns.take(8).forEach { column ->
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text(column.columnName, modifier = Modifier.weight(1f), style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.SemiBold)
                            Text(column.dataType, modifier = Modifier.width(82.dp), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text(column.role, modifier = Modifier.width(104.dp), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                    if (columns.size > 8) {
                        Text("+${columns.size - 8} more variables in copied CSV", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }

            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = onGenerate, enabled = canGenerate, modifier = Modifier.weight(1f)) {
                    Text(if (columns.isEmpty()) "Generate Master Chart" else "Regenerate")
                }
                OutlinedButton(onClick = onCopy, enabled = csv.isNotBlank(), modifier = Modifier.weight(1f)) {
                    Text("Copy CSV")
                }
            }
        }
    }
}

@Composable
fun MasterChartScreen(
    uiState: ThesisViewModel.UiState,
    onGenerate: () -> Unit,
    onImportData: () -> Unit,
    onCopyCsv: () -> Unit,
    onGoVariables: () -> Unit,
    onGoChapters: () -> Unit
) {
    var activeView by rememberSaveable { mutableIntStateOf(0) }
    val columns = uiState.masterChartColumns
    val canGenerate = uiState.variables.isNotEmpty() || uiState.chapters.any { it.status == Chapter.ChapterStatus.SUCCESS }
    val roleCounts = columns.groupingBy { it.role.ifBlank { "study_variable" } }.eachCount()
    val generatedAtText = if (uiState.masterChartGeneratedAt > 0L) {
        java.text.SimpleDateFormat("yyyy-MM-dd HH:mm", java.util.Locale.getDefault())
            .format(java.util.Date(uiState.masterChartGeneratedAt))
    } else {
        "Not generated"
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        ElevatedCard(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text("Master Chart", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                        Text(
                            "$generatedAtText • ${columns.size} columns",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    Surface(
                        color = if (columns.isEmpty()) MaterialTheme.colorScheme.secondaryContainer else Color(0xFFE8F5E9),
                        contentColor = if (columns.isEmpty()) MaterialTheme.colorScheme.onSecondaryContainer else Color(0xFF2E7D32),
                        shape = RoundedCornerShape(6.dp)
                    ) {
                        Text(
                            if (columns.isEmpty()) "Draft needed" else "Template ready",
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }

                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onClick = onGenerate, enabled = canGenerate && !uiState.processing, modifier = Modifier.weight(1f)) {
                        Text(if (columns.isEmpty()) "Generate" else "Regenerate")
                    }
                    OutlinedButton(onClick = onImportData, enabled = !uiState.processing, modifier = Modifier.weight(1f)) {
                        Icon(Icons.Default.FolderOpen, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Import Data")
                    }
                    OutlinedButton(onClick = onCopyCsv, enabled = uiState.masterChartCsv.isNotBlank(), modifier = Modifier.weight(1f)) {
                        Text("Copy CSV")
                    }
                }

                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = onGoVariables, modifier = Modifier.weight(1f)) { Text("Variables") }
                    OutlinedButton(onClick = onGoChapters, modifier = Modifier.weight(1f)) { Text("Chapters") }
                }
            }
        }

        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            StatChip("Total", columns.size, Color(0xFF1976D2), Modifier.weight(1f))
            StatChip("Demo", roleCounts["demographic"] ?: 0, Color(0xFF2E7D32), Modifier.weight(1f))
            StatChip("Clinical", roleCounts["clinical"] ?: 0, Color(0xFF7B1FA2), Modifier.weight(1f))
            StatChip("Outcome", roleCounts["outcome"] ?: 0, Color(0xFFF57C00), Modifier.weight(1f))
        }

        MasterDataImportSummary(uiState = uiState, onImportData = onImportData)

        ElevatedCard(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (activeView == 0) {
                        Button(onClick = { activeView = 0 }, modifier = Modifier.weight(1f)) { Text("Dictionary") }
                        OutlinedButton(onClick = { activeView = 1 }, modifier = Modifier.weight(1f)) { Text("CSV") }
                    } else {
                        OutlinedButton(onClick = { activeView = 0 }, modifier = Modifier.weight(1f)) { Text("Dictionary") }
                        Button(onClick = { activeView = 1 }, modifier = Modifier.weight(1f)) { Text("CSV") }
                    }
                }

                if (columns.isEmpty()) {
                    EmptyStateCard(
                        title = "No master chart yet",
                        subtitle = "Generate it after variables or chapters are available."
                    )
                } else if (activeView == 0) {
                    MasterChartDictionaryTable(columns = columns)
                } else {
                    MasterChartCsvPreview(csv = uiState.masterChartCsv)
                }
            }
        }

        if (uiState.masterDataMappings.isNotEmpty()) {
            MasterDataMappingTable(mappings = uiState.masterDataMappings)
        }

        if (uiState.masterDataValidationIssues.isNotEmpty()) {
            MasterDataValidationPanel(issues = uiState.masterDataValidationIssues)
        }

        if (uiState.masterDataResultTables.isNotEmpty()) {
            MasterDataResultsPanel(resultTables = uiState.masterDataResultTables)
        }
    }
}

@Composable
fun MasterChartDictionaryTable(columns: List<MasterChartColumnJson>) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState())
                .background(MaterialTheme.colorScheme.surfaceVariant, RoundedCornerShape(6.dp))
                .padding(8.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Text("Column", modifier = Modifier.width(150.dp), style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
            Text("Type", modifier = Modifier.width(90.dp), style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
            Text("Role", modifier = Modifier.width(120.dp), style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
            Text("Allowed", modifier = Modifier.width(180.dp), style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
            Text("Analysis", modifier = Modifier.width(260.dp), style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
        }
        LazyColumn(
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(max = 460.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            items(columns, key = { it.columnName }) { column ->
                MasterChartColumnRow(column)
            }
        }
    }
}

@Composable
fun MasterChartColumnRow(column: MasterChartColumnJson) {
    val roleColor = when (column.role.lowercase()) {
        "demographic" -> Color(0xFF2E7D32)
        "clinical" -> Color(0xFF7B1FA2)
        "investigation" -> Color(0xFF1565C0)
        "outcome" -> Color(0xFFF57C00)
        "exposure/grouping" -> Color(0xFFC62828)
        else -> MaterialTheme.colorScheme.primary
    }
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .horizontalScroll(rememberScrollState())
            .border(1.dp, MaterialTheme.colorScheme.outlineVariant, RoundedCornerShape(6.dp))
            .padding(8.dp),
        horizontalArrangement = Arrangement.spacedBy(10.dp),
        verticalAlignment = Alignment.Top
    ) {
        Column(modifier = Modifier.width(150.dp)) {
            Text(column.columnName, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Bold)
            Text(column.displayName, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        Text(column.dataType, modifier = Modifier.width(90.dp), style = MaterialTheme.typography.bodySmall)
        Surface(color = roleColor.copy(alpha = 0.12f), contentColor = roleColor, shape = RoundedCornerShape(5.dp), modifier = Modifier.width(120.dp)) {
            Text(column.role, modifier = Modifier.padding(horizontal = 6.dp, vertical = 3.dp), style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.SemiBold)
        }
        Text(column.allowedValues.ifBlank { "-" }, modifier = Modifier.width(180.dp), style = MaterialTheme.typography.bodySmall)
        Text(column.suggestedAnalysis.ifBlank { "-" }, modifier = Modifier.width(260.dp), style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
fun MasterChartCsvPreview(csv: String) {
    val preview = csv.ifBlank { "No CSV generated." }.lines().take(26).joinToString("\n")
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("CSV Preview", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 180.dp, max = 420.dp)
                .horizontalScroll(rememberScrollState())
                .verticalScroll(rememberScrollState())
                .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.35f), RoundedCornerShape(6.dp))
                .padding(10.dp)
        ) {
            Text(
                text = preview,
                style = MaterialTheme.typography.bodySmall.copy(fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace),
                color = MaterialTheme.colorScheme.onSurface
            )
        }
        if (csv.lines().size > 26) {
            Text("Preview truncated. Copy CSV includes the full template and data dictionary.", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
fun MasterDataImportSummary(
    uiState: ThesisViewModel.UiState,
    onImportData: () -> Unit
) {
    val importedAtText = if (uiState.masterDataImportedAt > 0L) {
        java.text.SimpleDateFormat("yyyy-MM-dd HH:mm", java.util.Locale.getDefault())
            .format(java.util.Date(uiState.masterDataImportedAt))
    } else {
        "Not imported"
    }
    ElevatedCard(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                    Text("Uploaded Master Data", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                    Text(
                        if (uiState.masterDataFileName.isBlank()) "Import Excel/CSV to map real data into the master chart."
                        else "${uiState.masterDataFileName} • $importedAtText",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                OutlinedButton(onClick = onImportData, enabled = !uiState.processing) {
                    Icon(Icons.Default.FolderOpen, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(if (uiState.masterDataFileName.isBlank()) "Upload" else "Replace")
                }
            }

            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                StatChip("Rows", uiState.masterDataRows.size, Color(0xFF1565C0), Modifier.weight(1f))
                StatChip("Headers", uiState.masterDataHeaders.size, Color(0xFF00897B), Modifier.weight(1f))
                StatChip("Mapped", uiState.masterDataMappings.count { it.targetColumn.isNotBlank() }, Color(0xFF2E7D32), Modifier.weight(1f))
                StatChip("Issues", uiState.masterDataValidationIssues.size, Color(0xFFC62828), Modifier.weight(1f))
            }

            if (uiState.masterDataHeaders.isNotEmpty()) {
                Text(
                    uiState.masterDataHeaders.take(12).joinToString("  |  "),
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState())
                        .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f), RoundedCornerShape(6.dp))
                        .padding(8.dp),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
fun MasterDataMappingTable(mappings: List<MasterChartColumnMappingJson>) {
    ElevatedCard(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("AI Column Mapping", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState())
                    .background(MaterialTheme.colorScheme.surfaceVariant, RoundedCornerShape(6.dp))
                    .padding(8.dp),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Text("Uploaded Header", modifier = Modifier.width(180.dp), style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
                Text("Master Variable", modifier = Modifier.width(180.dp), style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
                Text("Confidence", modifier = Modifier.width(90.dp), style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
                Text("Status", modifier = Modifier.width(90.dp), style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
            }
            mappings.take(40).forEach { mapping ->
                val statusColor = when (mapping.status) {
                    "mapped" -> Color(0xFF2E7D32)
                    "review" -> Color(0xFFF57C00)
                    else -> Color(0xFFC62828)
                }
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState())
                        .border(1.dp, MaterialTheme.colorScheme.outlineVariant, RoundedCornerShape(6.dp))
                        .padding(8.dp),
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(mapping.sourceHeader, modifier = Modifier.width(180.dp), style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.SemiBold)
                    Text(mapping.targetColumn.ifBlank { "-" }, modifier = Modifier.width(180.dp), style = MaterialTheme.typography.bodySmall)
                    Text("${(mapping.confidence * 100).toInt()}%", modifier = Modifier.width(90.dp), style = MaterialTheme.typography.bodySmall)
                    Surface(color = statusColor.copy(alpha = 0.12f), contentColor = statusColor, shape = RoundedCornerShape(5.dp), modifier = Modifier.width(90.dp)) {
                        Text(mapping.status, modifier = Modifier.padding(horizontal = 6.dp, vertical = 3.dp), style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
                    }
                }
            }
            if (mappings.size > 40) {
                Text("Showing first 40 mappings.", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

@Composable
fun MasterDataValidationPanel(issues: List<MasterChartValidationIssueJson>) {
    val errors = issues.count { it.severity == "error" }
    ElevatedCard(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Text("Validation Issues", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                Surface(
                    color = if (errors > 0) Color(0xFFFFEBEE) else Color(0xFFFFF8E1),
                    contentColor = if (errors > 0) Color(0xFFC62828) else Color(0xFFF57C00),
                    shape = RoundedCornerShape(6.dp)
                ) {
                    Text("$errors errors", modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp), style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
                }
            }
            issues.take(30).forEach { issue ->
                val color = if (issue.severity == "error") Color(0xFFC62828) else Color(0xFFF57C00)
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .border(1.dp, color.copy(alpha = 0.35f), RoundedCornerShape(6.dp))
                        .padding(8.dp),
                    verticalArrangement = Arrangement.spacedBy(3.dp)
                ) {
                    Text(
                        "${if (issue.rowNumber > 0) "Row ${issue.rowNumber}" else "Dataset"} • ${issue.columnName}",
                        style = MaterialTheme.typography.labelMedium,
                        color = color,
                        fontWeight = FontWeight.Bold
                    )
                    Text(issue.issue, style = MaterialTheme.typography.bodySmall)
                    if (issue.value.isNotBlank()) {
                        Text("Value: ${issue.value}", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
            if (issues.size > 30) {
                Text("Showing first 30 validation issues.", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

@Composable
fun MasterDataResultsPanel(resultTables: List<MasterChartResultSummaryJson>) {
    ElevatedCard(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Generated Results Tables", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            resultTables.take(6).forEachIndexed { index, table ->
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("Table R${index + 1}. ${table.title}", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .horizontalScroll(rememberScrollState())
                            .border(1.dp, MaterialTheme.colorScheme.outlineVariant, RoundedCornerShape(6.dp))
                    ) {
                        Row(
                            modifier = Modifier
                                .background(MaterialTheme.colorScheme.surfaceVariant)
                                .padding(8.dp),
                            horizontalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            table.headers.forEach { header ->
                                Text(header, modifier = Modifier.width(120.dp), style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold)
                            }
                        }
                        table.rows.take(8).forEach { row ->
                            Row(modifier = Modifier.padding(8.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                                table.headers.indices.forEach { cellIndex ->
                                    Text(row.getOrNull(cellIndex).orEmpty(), modifier = Modifier.width(120.dp), style = MaterialTheme.typography.bodySmall)
                                }
                            }
                        }
                    }
                }
            }
            if (resultTables.size > 6) {
                Text("Showing first 6 generated result tables. The Results chapter contains the generated tables and charts.", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            } else {
                Text("The Results chapter has been updated from the uploaded master data.", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

@Composable
fun VariablesEditorScreen(
    variables: List<Variable>,
    onVariableUpdate: (String, String) -> Unit,
    onContinue: () -> Unit
) {
    var query by rememberSaveable { mutableStateOf("") }
    var showRequiredOnly by rememberSaveable { mutableStateOf(false) }
    val requiredNames = remember {
        listOf("title", "topic", "disease", "author", "guide", "college", "department", "method", "sample", "references")
    }
    fun isRequired(variable: Variable): Boolean {
        val normalized = variable.name.lowercase()
        return requiredNames.any { normalized.contains(it) }
    }
    fun variableGroup(variable: Variable): String {
        val name = variable.name.lowercase()
        return when {
            listOf("title", "author", "guide", "college", "department", "contact").any { name.contains(it) } -> "Project identity"
            listOf("objective", "aim", "method", "sample", "inclusion", "exclusion").any { name.contains(it) } -> "Study design"
            listOf("result", "table", "figure", "chart", "analysis").any { name.contains(it) } -> "Results"
            name.contains("reference") || name.contains("citation") -> "References"
            else -> "Other extracted data"
        }
    }
    val filteredVariables = remember(variables, query, showRequiredOnly) {
        variables
            .filter { variable ->
                val matchesQuery = query.isBlank() ||
                    variable.name.contains(query, ignoreCase = true) ||
                    variable.value.contains(query, ignoreCase = true)
                val matchesRequired = !showRequiredOnly || isRequired(variable)
                matchesQuery && matchesRequired
            }
            .groupBy { variableGroup(it) }
    }

    Card(modifier = Modifier.fillMaxSize()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text("Edit Extracted Variables", style = MaterialTheme.typography.titleMedium)
            Spacer(modifier = Modifier.height(8.dp))
            OutlinedTextField(
                value = query,
                onValueChange = { query = it },
                label = { Text("Search variables") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )
            Row(verticalAlignment = Alignment.CenterVertically) {
                Checkbox(checked = showRequiredOnly, onCheckedChange = { showRequiredOnly = it })
                Text("Show required fields only", style = MaterialTheme.typography.bodySmall)
            }

            LazyColumn(
                verticalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier.weight(1f)
            ) {
                filteredVariables.forEach { (group, groupVariables) ->
                    item(key = "group_$group") {
                        Text(group, style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.SemiBold)
                    }
                    items(groupVariables, key = { it.name }) { variable ->
                        val required = isRequired(variable)
                        val missing = required && variable.value.isBlank()
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(
                                containerColor = if (missing) MaterialTheme.colorScheme.errorContainer.copy(alpha = 0.45f) else MaterialTheme.colorScheme.surface
                            )
                        ) {
                            Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text(variable.name, style = MaterialTheme.typography.labelLarge)
                                    AssistChip(onClick = {}, label = { Text(if (required) "Required" else "Optional") })
                                }
                                OutlinedTextField(
                                    value = variable.value,
                                    onValueChange = { onVariableUpdate(variable.name, it) },
                                    modifier = Modifier.fillMaxWidth(),
                                    minLines = 2,
                                    supportingText = {
                                        if (missing) Text("Add this before generating final chapters.")
                                    }
                                )
                            }
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(12.dp))
            Button(onClick = onContinue, modifier = Modifier.fillMaxWidth()) {
                Text("Continue to Chapter Generation")
            }
        }
    }
}

@Composable
fun ChaptersScreen(
    chapters: List<Chapter>,
    activeChapterName: String,
    viewModel: ThesisViewModel,
    onCopy: (String) -> Unit,
    onShowFigures: () -> Unit,
    onShowTables: () -> Unit,
    onShowCharts: () -> Unit,
    isGridViewEnabled: Boolean = false,
    expandAllContents: Boolean = false,
    onOpenReader: (Chapter) -> Unit
) {
    val listState = rememberLazyListState()
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    var searchQuery by remember { mutableStateOf("") }
    var selectedFilter by remember { mutableStateOf("All") }
    var selectionModeActive by remember { mutableStateOf(false) }

    val filteredChapters = remember(chapters, searchQuery, selectedFilter) {
        chapters.filter { chapter ->
            val matchesSearch = chapter.name.contains(searchQuery, ignoreCase = true)
            val matchesFilter = when (selectedFilter) {
                "Synced" -> chapter.workerStatus == "synced"
                "Queued" -> chapter.status == Chapter.ChapterStatus.PENDING
                "Success" -> chapter.status == Chapter.ChapterStatus.SUCCESS
                "Pending" -> chapter.status == Chapter.ChapterStatus.IDLE
                "Failed" -> chapter.status == Chapter.ChapterStatus.ERROR
                else -> true
            }
            matchesSearch && matchesFilter
        }
    }

    LaunchedEffect(activeChapterName, chapters.size) {
        val index = filteredChapters.indexOfFirst { it.name.equals(activeChapterName, ignoreCase = true) }
        if (index >= 0) {
            listState.animateScrollToItem(index)
        }
    }

    Column(modifier = Modifier.fillMaxSize()) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            OutlinedTextField(
                value = searchQuery,
                onValueChange = { searchQuery = it },
                label = { Text("Search Chapters") },
                modifier = Modifier.weight(1f),
                singleLine = true
            )
            OutlinedButton(
                onClick = {
                    selectionModeActive = !selectionModeActive
                    if (!selectionModeActive) {
                        viewModel.clearChapterSelection()
                    }
                }
            ) {
                Text(if (selectionModeActive) "Done" else "Select")
            }
        }

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 4.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            listOf("All", "Synced", "Queued", "Success", "Pending", "Failed").forEach { filter ->
                val isSelected = selectedFilter == filter
                if (isSelected) {
                    Button(onClick = { selectedFilter = filter }) {
                        Text(filter, fontSize = 11.sp)
                    }
                } else {
                    OutlinedButton(onClick = { selectedFilter = filter }) {
                        Text(filter, fontSize = 11.sp)
                    }
                }
            }
        }

        if (selectionModeActive) {
            val selectedCount = uiState.selectedChapters.size
            ElevatedCard(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 6.dp),
                colors = CardDefaults.elevatedCardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer)
            ) {
                Column(
                    modifier = Modifier.padding(12.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(
                        text = "$selectedCount chapters selected",
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSecondaryContainer
                    )
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Button(
                            onClick = { viewModel.retrySelected(uiState.selectedChapters) },
                            enabled = selectedCount > 0,
                            modifier = Modifier.weight(1f)
                        ) {
                            Text("Retry Selected", fontSize = 11.sp)
                        }
                        Button(
                            onClick = { viewModel.retryAllFailed() },
                            modifier = Modifier.weight(1f)
                        ) {
                            Text("Retry Failed", fontSize = 11.sp)
                        }
                        Button(
                            onClick = { viewModel.retryAllIncomplete() },
                            modifier = Modifier.weight(1f)
                        ) {
                            Text("Retry Incomplete", fontSize = 11.sp)
                        }
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        LazyColumn(
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth(),
            state = listState,
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            if (activeChapterName.isNotBlank()) {
                item(key = "active_chapter_banner") {
                    ElevatedCard(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.elevatedCardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)
                    ) {
                        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Text("Writing now", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onPrimaryContainer)
                            Text(activeChapterName, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold, color = MaterialTheme.colorScheme.onPrimaryContainer)
                        }
                    }
                }
            }

            item(key = "chapter_timeline") {
                ElevatedCard(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                                Text("VPS auto-complete", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                                Text(
                                    "Complete pending or failed chapters on the server every minute.",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                            Switch(
                                checked = chapters.any { it.syncEnabled },
                                onCheckedChange = { viewModel.setVpsAutoCompleteEnabled(it) }
                            )
                        }
                        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            chapters.forEachIndexed { index, chapter ->
                                AssistChip(
                                    onClick = {},
                                    label = {
                                        Text("${index + 1}. ${chapter.name.take(18)}${if (chapter.name.length > 18) "..." else ""}")
                                    }
                                )
                            }
                        }
                    }
                }
            }

            if (isGridViewEnabled) {
                val chunkedChapters = filteredChapters.chunked(2)
                items(
                    items = chunkedChapters,
                    key = { list -> list.joinToString("_") { it.name } }
                ) { pair ->
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        pair.forEach { chapter ->
                            Box(modifier = Modifier.weight(1f)) {
                                ChapterGridCard(
                                    chapter = chapter,
                                    onOpenReader = { onOpenReader(chapter) },
                                    viewModel = viewModel
                                )
                            }
                        }
                        if (pair.size == 1) {
                            Spacer(modifier = Modifier.weight(1f))
                        }
                    }
                }
            } else {
                items(
                    items = filteredChapters,
                    key = { it.name }
                ) { chapter ->
                    val rawVersions = viewModel.getChapterVersions(chapter.name)
                    val history = remember(rawVersions) {
                        rawVersions.map {
                            ChapterVersionItem(
                                versionNo = it.versionNo,
                                content = it.content,
                                rawJson = it.rawJson,
                                timestamp = it.timestamp
                            )
                        }
                    }

                    ChapterCard(
                        chapter = chapter,
                        history = history,
                        initiallyExpanded = expandAllContents || chapter.name.equals(activeChapterName, ignoreCase = true) ||
                            chapter.status == Chapter.ChapterStatus.LOADING,
                        onRetry = { c, prompt -> viewModel.retryChapter(c, prompt) },
                        onCopy = onCopy,
                        onShowFigures = onShowFigures,
                        onShowTables = onShowTables,
                        onShowCharts = onShowCharts,
                        onGetTextBoxes = { viewModel.getChapterTextBoxesForEditor(it) },
                        onSaveTextBoxes = { c, boxes -> viewModel.updateChapterTextBoxes(c.name, boxes) },
                        selectionModeActive = selectionModeActive,
                        isSelected = uiState.selectedChapters.contains(chapter.name),
                        onToggleSelection = { viewModel.toggleChapterSelection(chapter.name) },
                        viewModel = viewModel,
                        onOpenReader = onOpenReader
                    )
                }
            }
        }
    }
}

@Composable
fun RenderTable(table: com.rankwarz.edulabsrtm.model.ThesisTableJson) {
    Log.d("ThesisAnalyzer", "Rendering Table: ${table.title} with ${table.rows.size} rows")
    val headers = table.headers.ifEmpty {
        if (table.data.isNotEmpty()) {
            table.data.first().keys.toList()
        } else {
            val maxColumns = table.rows.maxOfOrNull { it.size } ?: 0
            List(maxColumns) { "Column ${it + 1}" }
        }
    }
    val rows = table.rows.ifEmpty {
        table.data.map { row -> headers.map { header -> row[header]?.toString().orEmpty() } }
    }
    val columnCount = headers.size.coerceAtLeast(1)

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outline),
        shape = MaterialTheme.shapes.small
    ) {
        Column(modifier = Modifier.padding(8.dp)) {
            Text(
                text = table.title.ifBlank { table.tableNumber },
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold
            )
            Spacer(modifier = Modifier.height(4.dp))
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(MaterialTheme.colorScheme.surfaceVariant)
                    .border(1.dp, MaterialTheme.colorScheme.outline)
            ) {
                headers.forEach { header ->
                    Text(
                        text = header,
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier
                            .weight(1f)
                            .padding(8.dp)
                    )
                }
            }
            rows.forEach { row ->
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .border(1.dp, MaterialTheme.colorScheme.outlineVariant)
                ) {
                    repeat(columnCount) { columnIndex ->
                        Text(
                            text = row.getOrNull(columnIndex).orEmpty(),
                            style = MaterialTheme.typography.bodyMedium,
                            modifier = Modifier
                                .weight(1f)
                                .padding(8.dp)
                        )
                    }
                }
            }
            table.footnote?.let {
                Spacer(modifier = Modifier.height(4.dp))
                Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

@Composable

fun RenderChart(chart: com.rankwarz.edulabsrtm.model.ChartJson) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer),
        shape = MaterialTheme.shapes.small
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Log.d("ThesisAnalyzer", "Rendering Chart: ${chart.title} [Type: ${chart.type}]")

            Text("📈 ${chart.title}", style = MaterialTheme.typography.titleMedium)
            Text("Type: ${chart.type}", style = MaterialTheme.typography.bodySmall)
            if (chart.xAxisLabel != null) Text("X: ${chart.xAxisLabel}")
            if (chart.yAxisLabel != null) Text("Y: ${chart.yAxisLabel}")

            // Render the actual chart view
            AndroidView(
                factory = { context ->
                    val datasets = chartDatasets(chart)
                    when (chart.type.lowercase()) {
                        "bar" -> createBarChart(context, chart)
                        "horizontal_bar" -> createHorizontalBarChart(context, chart)
                        "line" -> createLineChart(context, chart)
                        "pie" -> createPieChart(context, chart)
                        "scatter" -> createScatterChart(context, chart)
                        "histogram" -> createBarChart(context, chart)
                        else -> when {
                            datasets.size > 1 -> createLineChart(context, chart)
                            chart.type.contains("horizontal", ignoreCase = true) -> createHorizontalBarChart(context, chart)
                            chart.type.contains("scatter", ignoreCase = true) -> createScatterChart(context, chart)
                            datasets.firstOrNull()?.values.orEmpty().size <= 5 -> createPieChart(context, chart)
                            else -> createBarChart(context, chart)
                        }
                    }
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(250.dp)
            )
        }
    }
}

// Helper to create BarChart
private fun createBarChart(context: android.content.Context, chart: ChartJson): BarChart {
    val barChart = BarChart(context)
    val entries = mutableListOf<BarEntry>()
    val datasets = chartDatasets(chart)
    val dataset = datasets.firstOrNull()

    Log.d(
        "ChartEngine",
        "Building BarChart with ${if (dataset == null) 0 else 1} datasets " +
            "(rawDatasets=${chart.datasets.size}, rawData=${chartDataPointCount(chart.data)}, labels=${chart.labels.size}, values=${chart.values.size})"
    )

    dataset?.values?.forEachIndexed { index, value ->
        entries.add(BarEntry(index.toFloat(), value.toFloat()))
    }
    val xLabels = chartLabels(chart, dataset)

    val dataSet = BarDataSet(entries, dataset?.label ?: "Data")
    dataSet.colors = ColorTemplate.MATERIAL_COLORS.toList()
    dataSet.valueTextSize = 10f
    val barData = BarData(dataSet)
    barChart.data = barData

    // Configure x-axis
    val xAxis = barChart.xAxis
    xAxis.valueFormatter = IndexAxisValueFormatter(xLabels)
    xAxis.position = XAxis.XAxisPosition.BOTTOM
    xAxis.labelRotationAngle = -45f
    xAxis.textSize = 10f

    // Configure y-axis
    barChart.axisLeft.textSize = 10f
    barChart.axisRight.isEnabled = false
    barChart.description.isEnabled = false
    barChart.legend.textSize = 10f
    barChart.setTouchEnabled(false)      // disable zoom/pan for simpler UI
    barChart.invalidate()
    return barChart
}

private fun createHorizontalBarChart(context: android.content.Context, chart: ChartJson): HorizontalBarChart {
    val barChart = HorizontalBarChart(context)
    val entries = mutableListOf<BarEntry>()
    val datasets = chartDatasets(chart)
    val dataset = datasets.firstOrNull()

    Log.d(
        "ChartEngine",
        "Building HorizontalBarChart with ${if (dataset == null) 0 else 1} datasets " +
            "(rawDatasets=${chart.datasets.size}, rawData=${chartDataPointCount(chart.data)}, labels=${chart.labels.size}, values=${chart.values.size})"
    )

    dataset?.values?.forEachIndexed { index, value ->
        entries.add(BarEntry(index.toFloat(), value.toFloat()))
    }
    val xLabels = chartLabels(chart, dataset)

    val dataSet = BarDataSet(entries, dataset?.label ?: "Data")
    dataSet.colors = ColorTemplate.MATERIAL_COLORS.toList()
    dataSet.valueTextSize = 10f
    val barData = BarData(dataSet)
    barChart.data = barData

    val xAxis = barChart.xAxis
    xAxis.valueFormatter = IndexAxisValueFormatter(xLabels)
    xAxis.position = XAxis.XAxisPosition.BOTTOM
    xAxis.labelRotationAngle = -25f
    xAxis.textSize = 10f
    barChart.axisLeft.textSize = 10f
    barChart.axisRight.isEnabled = false
    barChart.description.isEnabled = false
    barChart.legend.textSize = 10f
    barChart.setTouchEnabled(false)
    barChart.invalidate()
    return barChart
}

// Helper to create LineChart
private fun createLineChart(context: android.content.Context, chart: ChartJson): LineChart {
    val lineChart = LineChart(context)
    val datasets = chartDatasets(chart)
    val dataset = datasets.firstOrNull()

    Log.d(
        "ChartEngine",
        "Building LineChart with ${if (dataset == null) 0 else 1} datasets " +
            "(rawDatasets=${chart.datasets.size}, rawData=${chartDataPointCount(chart.data)}, labels=${chart.labels.size}, values=${chart.values.size})"
    )

    val xLabels = chartLabels(chart, dataset)

    val dataSets = datasets.mapIndexed { index, ds ->
        val entries = ds.values.mapIndexed { entryIndex, value ->
            Entry(entryIndex.toFloat(), value.toFloat())
        }
        LineDataSet(entries, ds.label.ifBlank { "Series ${index + 1}" }).apply {
            val color = ColorTemplate.COLORFUL_COLORS[index % ColorTemplate.COLORFUL_COLORS.size]
            this.color = color
            setCircleColor(color)
            lineWidth = 2f
            circleRadius = 4f
            valueTextSize = 10f
        }
    }

    val lineData = LineData(dataSets)
    lineChart.data = lineData

    // X-axis labels
    val xAxis = lineChart.xAxis
    xAxis.valueFormatter = IndexAxisValueFormatter(xLabels)
    xAxis.position = XAxis.XAxisPosition.BOTTOM
    xAxis.labelRotationAngle = -45f
    xAxis.textSize = 10f

    lineChart.axisLeft.textSize = 10f
    lineChart.axisRight.isEnabled = false
    lineChart.description.isEnabled = false
    lineChart.legend.textSize = 10f
    lineChart.setTouchEnabled(false)
    lineChart.invalidate()
    return lineChart
}

private fun createScatterChart(context: android.content.Context, chart: ChartJson): ScatterChart {
    val scatterChart = ScatterChart(context)
    val datasets = chartDatasets(chart)
    val dataset = datasets.firstOrNull()

    Log.d(
        "ChartEngine",
        "Building ScatterChart with ${if (dataset == null) 0 else 1} datasets " +
            "(rawDatasets=${chart.datasets.size}, rawData=${chartDataPointCount(chart.data)}, labels=${chart.labels.size}, values=${chart.values.size})"
    )

    val entries = dataset?.values.orEmpty().mapIndexed { index, value ->
        Entry(index.toFloat(), value.toFloat())
    }
    val scatterDataSet = ScatterDataSet(entries, dataset?.label ?: "Data").apply {
        val color = ColorTemplate.COLORFUL_COLORS.first()
        this.color = color
        setScatterShapeSize(8f)
        valueTextSize = 10f
    }
    scatterChart.data = ScatterData(scatterDataSet)

    val xLabels = chartLabels(chart, dataset)
    val xAxis = scatterChart.xAxis
    xAxis.valueFormatter = IndexAxisValueFormatter(xLabels)
    xAxis.position = XAxis.XAxisPosition.BOTTOM
    xAxis.labelRotationAngle = -45f
    xAxis.textSize = 10f
    scatterChart.axisLeft.textSize = 10f
    scatterChart.axisRight.isEnabled = false
    scatterChart.description.isEnabled = false
    scatterChart.legend.textSize = 10f
    scatterChart.setTouchEnabled(false)
    scatterChart.invalidate()
    return scatterChart
}

// Helper to create PieChart
private fun createPieChart(context: android.content.Context, chart: ChartJson): PieChart {
    val pieChart = PieChart(context)
    val entries = mutableListOf<PieEntry>()
    val dataset = chartDatasets(chart).firstOrNull()

    Log.d("ChartEngine", "Building PieChart")

    dataset?.values?.forEachIndexed { index, value ->
        val label = chartLabels(chart, dataset).getOrNull(index) ?: "${dataset.label} ${index + 1}"
        entries.add(PieEntry(value.toFloat(), label))
    }

    val dataSet = PieDataSet(entries, dataset?.label ?: "Data")
    dataSet.colors = ColorTemplate.MATERIAL_COLORS.toList()
    dataSet.valueTextSize = 12f
    dataSet.valueLinePart1Length = 0.5f
    val pieData = PieData(dataSet)
    pieChart.data = pieData

    pieChart.description.isEnabled = false
    pieChart.isDrawHoleEnabled = true
    pieChart.setHoleColor(android.graphics.Color.TRANSPARENT)
    pieChart.setTouchEnabled(false)
    pieChart.invalidate()
    return pieChart
}

private fun chartDatasets(chart: ChartJson): List<com.rankwarz.edulabsrtm.model.ChartDatasetJson> {
    if (chart.datasets.isNotEmpty()) return chart.datasets
    return chartDatasetsFromRaw(
        title = chart.title,
        labelsHint = chart.labels,
        valuesHint = chart.values,
        data = chart.data
    )
}

private fun chartDataPointCount(data: Any?): Int {
    return when (data) {
        is Map<*, *> -> data.size
        is List<*> -> data.size
        else -> 0
    }
}

private fun chartDataLabels(data: Any?): List<String> {
    return when (data) {
        is Map<*, *> -> data.keys.map { it.toString() }
        is List<*> -> data.mapIndexedNotNull { index, item ->
            when (item) {
                is com.rankwarz.edulabsrtm.model.AiChartPoint -> item.label
                is Map<*, *> -> item["label"]?.toString() ?: item["name"]?.toString() ?: "${index + 1}"
                else -> null
            }
        }
        else -> emptyList()
    }
}

private fun chartDataValues(data: Any?): List<Double> {
    return when (data) {
        is Map<*, *> -> data.values.mapNotNull { it?.toChartDoubleOrNull() }
        is List<*> -> data.mapNotNull { item ->
            when (item) {
                is com.rankwarz.edulabsrtm.model.AiChartPoint -> item.value
                is Map<*, *> -> (item["value"] ?: item["count"] ?: item["y"])?.toChartDoubleOrNull()
                is Number -> item.toDouble()
                else -> item?.toString()?.toDoubleOrNull()
            }
        }
        else -> emptyList()
    }
}

private fun Any.toChartDoubleOrNull(): Double? {
    return when (this) {
        is Number -> toDouble()
        is String -> toDoubleOrNull()
        else -> null
    }
}

private fun chartLabels(chart: ChartJson, dataset: com.rankwarz.edulabsrtm.model.ChartDatasetJson?): List<String> {
    val fromDataset = dataset?.labels.orEmpty()
    if (fromDataset.isNotEmpty()) return fromDataset

    val optionLabels = chart.options?.get("labels")
    if (optionLabels is List<*>) return optionLabels.map { it.toString() }

    val valueCount = dataset?.values?.size ?: 0
    return List(valueCount) { "${it + 1}" }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun ChapterCard(
    chapter: Chapter,
    history: List<ChapterVersionItem>,
    initiallyExpanded: Boolean,
    onRetry: (Chapter, String?) -> Unit,
    onCopy: (String) -> Unit,
    onShowFigures: () -> Unit,
    onShowTables: () -> Unit,
    onShowCharts: () -> Unit,
    onGetTextBoxes: (Chapter) -> List<ChapterTextBoxJson>,
    onSaveTextBoxes: (Chapter, List<ChapterTextBoxJson>) -> Unit,
    selectionModeActive: Boolean = false,
    isSelected: Boolean = false,
    onToggleSelection: () -> Unit = {},
    viewModel: ThesisViewModel? = null,
    onOpenReader: (Chapter) -> Unit = {}
) {
    var showImproveDialog by remember { mutableStateOf(false) }
    var showHistoryDialog by remember { mutableStateOf(false) }
    var showLayoutEditor by remember { mutableStateOf(false) }
    var showReferencesDialog by remember { mutableStateOf(false) }
    var actionsExpanded by remember { mutableStateOf(false) }
    var expanded by remember(chapter.name, initiallyExpanded) { mutableStateOf(initiallyExpanded) }
    var viewMode by rememberSaveable(chapter.name) { mutableStateOf("Text") }
    var customPrompt by remember { mutableStateOf("") }
    val context = LocalContext.current
    var showDiffDialog by remember { mutableStateOf(false) }
    var compareVersionText by remember { mutableStateOf("") }

    val statusText = when (chapter.status) {
        Chapter.ChapterStatus.SUCCESS -> "Done"
        Chapter.ChapterStatus.ERROR -> "Error"
        Chapter.ChapterStatus.LOADING -> "Generating..."
        Chapter.ChapterStatus.IDLE -> "Pending"
        Chapter.ChapterStatus.PENDING -> "Pending"
    }

    ElevatedCard(
        modifier = Modifier
            .fillMaxWidth()
            .border(
                width = 1.dp,
                color = MaterialTheme.colorScheme.outlineVariant,
                shape = MaterialTheme.shapes.medium
            ),
        colors = CardDefaults.elevatedCardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.elevatedCardElevation(defaultElevation = 3.dp)
    ) {
        Column(modifier = Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.fillMaxWidth()
            ) {
                if (selectionModeActive) {
                    Checkbox(
                        checked = isSelected,
                        onCheckedChange = { onToggleSelection() }
                    )
                }
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = chapter.name,
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.SemiBold
                    )
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.padding(top = 6.dp)
                    ) {
                        Surface(
                            color = when (chapter.status) {
                                Chapter.ChapterStatus.ERROR -> MaterialTheme.colorScheme.errorContainer
                                Chapter.ChapterStatus.SUCCESS -> MaterialTheme.colorScheme.primaryContainer
                                Chapter.ChapterStatus.LOADING -> MaterialTheme.colorScheme.tertiaryContainer
                                else -> MaterialTheme.colorScheme.secondaryContainer
                            },
                            contentColor = when (chapter.status) {
                                Chapter.ChapterStatus.ERROR -> MaterialTheme.colorScheme.onErrorContainer
                                Chapter.ChapterStatus.SUCCESS -> MaterialTheme.colorScheme.onPrimaryContainer
                                Chapter.ChapterStatus.LOADING -> MaterialTheme.colorScheme.onTertiaryContainer
                                else -> MaterialTheme.colorScheme.onSecondaryContainer
                            },
                            shape = MaterialTheme.shapes.small
                        ) {
                            Text(
                                text = statusText,
                                style = MaterialTheme.typography.labelMedium,
                                fontWeight = FontWeight.SemiBold,
                                modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp)
                            )
                        }
                        if (chapter.chapterReferences.isNotEmpty()) {
                            Text(
                                text = "${chapter.chapterReferences.size} verified refs",
                                style = MaterialTheme.typography.labelMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                        val completedBy = chapter.completedByLabel
                            .ifBlank {
                                listOf(chapter.completedByProvider, chapter.completedByModel)
                                    .filter { it.isNotBlank() }
                                    .joinToString(" / ")
                            }
                        if (completedBy.isNotBlank()) {
                            val provider = chapter.completedByProvider.ifBlank { completedBy }
                            val (badgeTextColor, badgeBgColor) = getProviderBadgeColors(provider)
                            Surface(
                                color = badgeBgColor,
                                contentColor = badgeTextColor,
                                shape = RoundedCornerShape(4.dp)
                            ) {
                                Text(
                                    text = "AI: $completedBy",
                                    style = MaterialTheme.typography.labelSmall,
                                    fontWeight = FontWeight.SemiBold,
                                    modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                )
                            }
                        }
                    }
                }

                Row(verticalAlignment = Alignment.CenterVertically) {
                    if (chapter.status == Chapter.ChapterStatus.LOADING) {
                        CircularProgressIndicator(modifier = Modifier.size(24.dp))
                    } else {
                        TextButton(onClick = { expanded = !expanded }) {
                            Text(if (expanded) "Collapse" else "Open")
                        }
                    }
                    Box {
                        IconButton(onClick = { actionsExpanded = true }) {
                            Icon(Icons.Default.MoreVert, contentDescription = "Chapter actions")
                        }
                        DropdownMenu(
                            expanded = actionsExpanded,
                            onDismissRequest = { actionsExpanded = false }
                        ) {
                            DropdownMenuItem(
                                text = { Text("Copy text") },
                                onClick = {
                                    actionsExpanded = false
                                    onCopy(chapterTextWithoutReferenceBlock(chapter.content))
                                },
                                enabled = chapter.content.isNotBlank() && chapter.status != Chapter.ChapterStatus.LOADING
                            )
                            DropdownMenuItem(
                                text = { Text("Retry") },
                                onClick = {
                                    actionsExpanded = false
                                    onRetry(chapter, null)
                                },
                                enabled = chapter.status != Chapter.ChapterStatus.LOADING
                            )
                            DropdownMenuItem(
                                text = { Text("Improve") },
                                onClick = {
                                    actionsExpanded = false
                                    showImproveDialog = true
                                },
                                enabled = chapter.status != Chapter.ChapterStatus.LOADING
                            )
                            DropdownMenuItem(
                                text = { Text("Edit page") },
                                onClick = {
                                    actionsExpanded = false
                                    showLayoutEditor = true
                                },
                                enabled = chapter.status != Chapter.ChapterStatus.LOADING
                            )
                            DropdownMenuItem(
                                text = { Text("History") },
                                onClick = {
                                    actionsExpanded = false
                                    showHistoryDialog = true
                                }
                            )
                        }
                    }
                }
            }

            if (chapter.errorMessage != null) {
                Text(
                    text = "Failed: ${chapter.errorMessage}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error
                )
            }

            val visibleChapterContent = chapterTextWithoutReferenceBlock(chapter.content)
            if (!expanded && chapter.status != Chapter.ChapterStatus.LOADING) {
                Text(
                    text = visibleChapterContent.ifBlank {
                        chapter.errorMessage.orEmpty().ifBlank { "No generated text yet." }
                    }.take(260),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    AssistChip(onClick = { expanded = true; viewMode = "Text" }, label = { Text("Text") })
                    if (chapter.figures.isNotEmpty()) AssistChip(onClick = { expanded = true; viewMode = "Assets" }, label = { Text("Figures ${chapter.figures.size}") })
                    if (chapter.tables.isNotEmpty()) AssistChip(onClick = { expanded = true; viewMode = "Assets" }, label = { Text("Tables ${chapter.tables.size}") })
                    if (chapter.charts.isNotEmpty()) AssistChip(onClick = { expanded = true; viewMode = "Assets" }, label = { Text("Charts ${chapter.charts.size}") })
                    if (chapter.rawJson.isNotBlank()) AssistChip(onClick = { expanded = true; viewMode = "Debug" }, label = { Text("JSON") })
                }
            } else if (chapter.status == Chapter.ChapterStatus.LOADING) {
                LoadingChapterWritingPreview(
                    chapterName = chapter.name,
                    draft = visibleChapterContent
                )
            } else {
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf("Text", "Assets", "Debug").forEach { mode ->
                        AssistChip(
                            onClick = { viewMode = mode },
                            label = {
                                Text(
                                    text = if (viewMode == mode) "✓ $mode" else mode,
                                    fontWeight = if (viewMode == mode) FontWeight.Bold else FontWeight.Normal
                                )
                            }
                        )
                    }
                }
                if (viewMode == "Text" && visibleChapterContent.isNotBlank()) {
                    ChapterReadingSurface(visibleChapterContent)
                } else if (viewMode == "Debug") {
                    Surface(
                        modifier = Modifier.fillMaxWidth(),
                        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f),
                        shape = MaterialTheme.shapes.medium
                    ) {
                        Text(
                            text = chapter.rawJson.ifBlank { "No raw JSON was saved for this chapter." },
                            style = MaterialTheme.typography.bodySmall,
                            modifier = Modifier.padding(12.dp)
                        )
                    }
                } else if (viewMode == "Assets" && chapter.figures.isEmpty() && chapter.tables.isEmpty() && chapter.charts.isEmpty()) {
                    Text("No chapter assets yet.", style = MaterialTheme.typography.bodySmall)
                }
            }

            if (expanded && viewMode == "Assets" && chapter.figures.isNotEmpty()) {
                Text(
                    text = "📷 FIGURES",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(top = 8.dp)
                )
                chapter.figures.forEach { figure ->
                    RenderFigure(figure)
                }
            }

            // Tables section
            if (expanded && viewMode == "Assets" && chapter.tables.isNotEmpty()) {
                Text(
                    text = "📋 TABLES",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(top = 8.dp)
                )
                chapter.tables.forEach { table ->
                    RenderTable(table)
                }
            }

            // Charts section
            if (expanded && viewMode == "Assets" && chapter.charts.isNotEmpty()) {
                Text(
                    text = "📈 CHARTS",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(top = 8.dp)
                )
                chapter.charts.forEach { chart ->
                    RenderChart(chart)
                }
            }

            if (chapter.tables.isNotEmpty() || chapter.figures.isNotEmpty() || chapter.charts.isNotEmpty() || chapter.chapterReferences.isNotEmpty()) {
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        if (chapter.tables.isNotEmpty()) {
                            AssistChip(onClick = onShowTables, label = { Text("Tables ${chapter.tables.size}") })
                        }
                        if (chapter.figures.isNotEmpty()) {
                            AssistChip(onClick = onShowFigures, label = { Text("Figures ${chapter.figures.size}") })
                        }
                        if (chapter.charts.isNotEmpty()) {
                            AssistChip(onClick = onShowCharts, label = { Text("Charts ${chapter.charts.size}") })
                        }
                        if (chapter.chapterReferences.isNotEmpty()) {
                            AssistChip(onClick = { showReferencesDialog = true }, label = { Text("Refs ${chapter.chapterReferences.size}") })
                        }
                    }
                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        if (chapter.tables.isNotEmpty()) {
                            TextButton(onClick = onShowTables) {
                                Text("View Tables")
                            }
                        }
                        if (chapter.figures.isNotEmpty()) {
                            TextButton(onClick = onShowFigures) {
                                Text("View Figures")
                            }
                        }
                        if (chapter.charts.isNotEmpty()) {
                            TextButton(onClick = onShowCharts) {
                                Text("View Charts")
                            }
                        }
                        if (chapter.chapterReferences.isNotEmpty()) {
                            TextButton(onClick = { showReferencesDialog = true }) {
                                Text("View References")
                            }
                        }
                    }
                }
            }

            HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)

            FlowRow(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                if (chapter.status == Chapter.ChapterStatus.SUCCESS) {
                    Button(onClick = { onOpenReader(chapter) }) {
                        Icon(Icons.AutoMirrored.Filled.OpenInNew, contentDescription = null)
                        Spacer(modifier = Modifier.size(6.dp))
                        Text("Read")
                    }
                }
                Button(onClick = { onCopy(visibleChapterContent) }, enabled = visibleChapterContent.isNotBlank() && chapter.status != Chapter.ChapterStatus.LOADING) {
                    Text("Copy")
                }
                Button(onClick = { onRetry(chapter, null) }, enabled = chapter.status != Chapter.ChapterStatus.LOADING) {
                    Text("Retry")
                }
                OutlinedButton(onClick = { showImproveDialog = true }, enabled = chapter.status != Chapter.ChapterStatus.LOADING) {
                    Text("Improve")
                }
                OutlinedButton(onClick = { showLayoutEditor = true }, enabled = chapter.status != Chapter.ChapterStatus.LOADING) {
                    Icon(Icons.Default.Edit, contentDescription = null)
                    Spacer(modifier = Modifier.size(6.dp))
                    Text("Edit Page")
                }
                OutlinedButton(onClick = { showHistoryDialog = true }) {
                    Text("History")
                }
            }
        }
    }

    if (showImproveDialog) {
        AlertDialog(
            onDismissRequest = { showImproveDialog = false },
            title = { Text("Improve Chapter") },
            text = {
                OutlinedTextField(
                    value = customPrompt,
                    onValueChange = { customPrompt = it },
                    label = { Text("Custom instructions") },
                    modifier = Modifier.fillMaxWidth(),
                    minLines = 3
                )
            },
            confirmButton = {
                TextButton(onClick = {
                    onRetry(chapter, customPrompt.ifBlank { null })
                    showImproveDialog = false
                    customPrompt = ""
                }) { Text("Regenerate") }
            },
            dismissButton = {
                TextButton(onClick = {
                    showImproveDialog = false
                    customPrompt = ""
                }) { Text("Cancel") }
            }
        )
    }

    if (showLayoutEditor) {
        val initialBoxes = remember(chapter.name, chapter.content, chapter.rawJson, chapter.textBoxes, showLayoutEditor) {
            onGetTextBoxes(chapter)
        }
        ChapterTextBoxEditorDialog(
            chapterName = chapter.name,
            initialBoxes = initialBoxes,
            onDismiss = { showLayoutEditor = false },
            onSave = { boxes ->
                onSaveTextBoxes(chapter, boxes)
                showLayoutEditor = false
            }
        )
    }

    if (showReferencesDialog) {
        AlertDialog(
            onDismissRequest = { showReferencesDialog = false },
            title = { Text("${chapter.name} references") },
            text = {
                if (chapter.chapterReferences.isEmpty()) {
                    Text("No verified references are attached to this chapter.")
                } else {
                    LazyColumn(
                        modifier = Modifier.height(360.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        items(chapter.chapterReferences) { reference ->
                            val pmid = reference.pmid.orEmpty().trim()
                            ElevatedCard(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .then(
                                        if (pmid.isNotBlank()) {
                                            Modifier.clickable {
                                                context.startActivity(
                                                    Intent(
                                                        Intent.ACTION_VIEW,
                                                        Uri.parse("https://pubmed.ncbi.nlm.nih.gov/$pmid/")
                                                    )
                                                )
                                            }
                                        } else {
                                            Modifier
                                        }
                                    )
                            ) {
                                Column(
                                    modifier = Modifier.padding(12.dp),
                                    verticalArrangement = Arrangement.spacedBy(4.dp)
                                ) {
                                    Text(
                                        text = reference.citation.ifBlank { "Reference" },
                                        style = MaterialTheme.typography.labelMedium,
                                        fontWeight = FontWeight.SemiBold
                                    )
                                    Text(
                                        text = referenceDisplayText(reference),
                                        style = MaterialTheme.typography.bodySmall
                                    )
                                    if (pmid.isNotBlank()) {
                                        Text(
                                            text = "PMID: $pmid${reference.doi?.takeIf { it.isNotBlank() }?.let { " | DOI: $it" }.orEmpty()}",
                                            style = MaterialTheme.typography.labelSmall,
                                            color = MaterialTheme.colorScheme.primary
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { showReferencesDialog = false }) { Text("Close") }
            }
        )
    }

    if (showHistoryDialog) {
        var activeTab by remember { mutableStateOf(0) } // 0 = Versions, 1 = Audit Trail
        AlertDialog(
            onDismissRequest = { showHistoryDialog = false },
            title = { Text("Chapter History & Audit Trail") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        if (activeTab == 0) {
                            Button(onClick = { activeTab = 0 }, modifier = Modifier.weight(1f)) {
                                Text("Versions")
                            }
                        } else {
                            OutlinedButton(onClick = { activeTab = 0 }, modifier = Modifier.weight(1f)) {
                                Text("Versions")
                            }
                        }
                        if (activeTab == 1) {
                            Button(onClick = { activeTab = 1 }, modifier = Modifier.weight(1f)) {
                                Text("Audit Log")
                            }
                        } else {
                            OutlinedButton(onClick = { activeTab = 1 }, modifier = Modifier.weight(1f)) {
                                Text("Audit Log")
                            }
                        }
                    }

                    HorizontalDivider()

                    if (activeTab == 0) {
                        if (history.isEmpty()) {
                            Text("No saved versions yet.")
                        } else {
                            LazyColumn(modifier = Modifier.height(300.dp)) {
                                items(history) { version ->
                                    Card(
                                        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)
                                    ) {
                                        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                            Row(
                                                modifier = Modifier.fillMaxWidth(),
                                                horizontalArrangement = Arrangement.SpaceBetween,
                                                verticalAlignment = Alignment.CenterVertically
                                            ) {
                                                Text(
                                                    text = "Version ${version.versionNo}",
                                                    style = MaterialTheme.typography.labelMedium,
                                                    fontWeight = FontWeight.Bold
                                                )
                                                val dateStr = java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss", java.util.Locale.getDefault())
                                                    .format(java.util.Date(version.timestamp))
                                                Text(
                                                    text = dateStr,
                                                    style = MaterialTheme.typography.labelSmall,
                                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                                )
                                            }
                                            Text(
                                                text = version.content.take(120) + "...",
                                                style = MaterialTheme.typography.bodySmall
                                            )
                                            Row(
                                                horizontalArrangement = Arrangement.spacedBy(8.dp),
                                                modifier = Modifier.fillMaxWidth()
                                            ) {
                                                TextButton(onClick = { onCopy(version.content) }) {
                                                    Text("Copy")
                                                }
                                                TextButton(onClick = {
                                                    compareVersionText = version.content
                                                    showDiffDialog = true
                                                }) {
                                                    Text("Diff")
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    } else {
                        val auditTrail = chapter.auditTrail
                        if (auditTrail.isEmpty()) {
                            Text("No audit log entries found.")
                        } else {
                            LazyColumn(modifier = Modifier.height(300.dp)) {
                                items(auditTrail) { entry ->
                                    Card(
                                        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)
                                    ) {
                                        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                            Row(
                                                modifier = Modifier.fillMaxWidth(),
                                                horizontalArrangement = Arrangement.SpaceBetween,
                                                verticalAlignment = Alignment.CenterVertically
                                            ) {
                                                Text(
                                                    text = entry.action.uppercase(),
                                                    style = MaterialTheme.typography.labelMedium,
                                                    fontWeight = FontWeight.Bold,
                                                    color = MaterialTheme.colorScheme.primary
                                                )
                                                val dateStr = java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss", java.util.Locale.getDefault())
                                                    .format(java.util.Date(entry.timestamp))
                                                Text(
                                                    text = dateStr,
                                                    style = MaterialTheme.typography.labelSmall,
                                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                                )
                                            }
                                            if (entry.provider.isNotBlank() || entry.model.isNotBlank()) {
                                                Text(
                                                    text = "AI: ${entry.provider} / ${entry.model}",
                                                    style = MaterialTheme.typography.labelSmall,
                                                    fontWeight = FontWeight.SemiBold
                                                )
                                            }
                                            if (entry.notes.isNotBlank()) {
                                                Text(
                                                    text = entry.notes,
                                                    style = MaterialTheme.typography.bodySmall
                                                )
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { showHistoryDialog = false }) { Text("Close") }
            }
        )
    }

    if (showDiffDialog) {
        ShowDiffDialog(
            chapterName = chapter.name,
            oldText = compareVersionText,
            newText = chapterTextWithoutReferenceBlock(chapter.content),
            onDismiss = {
                showDiffDialog = false
                compareVersionText = ""
            }
        )
    }
}

@Composable
private fun LoadingChapterWritingPreview(
    chapterName: String,
    draft: String
) {
    val draftText = remember(chapterName, draft) {
        draft.ifBlank {
            """
            AI is writing $chapterName...

            Waiting for the first generated lines from the model.
            """.trimIndent()
        }
    }
    var visibleChars by remember(chapterName, draftText) { mutableIntStateOf(0) }

    LaunchedEffect(chapterName, draftText) {
        visibleChars = 0
        while (visibleChars < draftText.length) {
            delay(3)
            visibleChars += 1
        }
    }

    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = MaterialTheme.colorScheme.tertiaryContainer.copy(alpha = 0.28f),
        shape = MaterialTheme.shapes.medium
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
            Text(
                text = draftText.take(visibleChars.coerceIn(0, draftText.length)) +
                    if (visibleChars < draftText.length) "|" else "",
                style = MaterialTheme.typography.bodyMedium.copy(lineHeight = 22.sp),
                color = MaterialTheme.colorScheme.onSurface
            )
        }
    }
}

@Composable
private fun ChapterReadingSurface(content: String) {
    val blocks = remember(content) {
        content
            .split(Regex("\\n{2,}"))
            .map { it.trim() }
            .filter { it.isNotBlank() }
    }

    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.36f),
        shape = MaterialTheme.shapes.medium
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            blocks.forEach { block ->
                val singleLine = !block.contains('\n')
                val headingLike = singleLine &&
                    block.length <= 80 &&
                    (
                        block == block.uppercase() ||
                            block.endsWith(":") ||
                            block.matches(Regex("""\d+(\.\d+)*\s+.+"""))
                        )

                if (headingLike) {
                    Text(
                        text = block.trimEnd(':'),
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                } else {
                    Text(
                        text = boldMarkdownAnnotatedText(block),
                        style = MaterialTheme.typography.bodyMedium.copy(lineHeight = 23.sp),
                        color = MaterialTheme.colorScheme.onSurface
                    )
                }
            }
        }
    }
}

@Composable
fun ChapterTextBoxEditorDialog(
    chapterName: String,
    initialBoxes: List<ChapterTextBoxJson>,
    onDismiss: () -> Unit,
    onSave: (List<ChapterTextBoxJson>) -> Unit
) {
    var boxes by remember(chapterName) {
        mutableStateOf(
            normalizeChapterTextBoxes(initialBoxes.ifEmpty {
                listOf(ChapterTextBoxJson(id = "box_1", text = ""))
            })
        )
    }
    var editingIndex by remember { mutableIntStateOf(-1) }
    var draftText by remember { mutableStateOf("") }

    fun openEditor(index: Int) {
        editingIndex = index
        draftText = boxes.getOrNull(index)?.text.orEmpty()
    }

    fun replaceBoxText(index: Int, newText: String) {
        val current = boxes.getOrNull(index) ?: return
        val updatedBox = current.copy(
            text = newText.trim(),
            height = estimateEditorTextBoxHeight(newText.trim(), current.width)
        )
        boxes = boxes.toMutableList().also { list ->
            list[index] = updatedBox
        }
    }

    fun addBox() {
        val nextIndex = boxes.size + 1
        val newBox = ChapterTextBoxJson(
            id = "box_$nextIndex",
            text = "New text box",
            x = 0.08f,
            y = (0.08f + boxes.size * 0.12f).coerceAtMost(0.78f),
            width = 0.84f,
            height = 0.14f
        )
        boxes = boxes + newBox
        openEditor(boxes.lastIndex)
    }

    Dialog(onDismissRequest = onDismiss) {
        Surface(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            shape = MaterialTheme.shapes.large,
            tonalElevation = 6.dp
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = chapterName,
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.SemiBold
                        )
                        Text(
                            text = "Drag the boxes, edit text inside them, and keep the page readable.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedButton(onClick = { addBox() }) {
                            Icon(Icons.Default.Add, contentDescription = null)
                            Spacer(modifier = Modifier.size(6.dp))
                            Text("Add Box")
                        }
                        Button(onClick = { onSave(normalizeChapterTextBoxes(boxes)); onDismiss() }) {
                            Icon(Icons.Default.Save, contentDescription = null)
                            Spacer(modifier = Modifier.size(6.dp))
                            Text("Save")
                        }
                    }
                }

                BoxWithConstraints(
                    modifier = Modifier
                        .fillMaxWidth()
                        .aspectRatio(210f / 297f)
                        .border(1.dp, MaterialTheme.colorScheme.outlineVariant, MaterialTheme.shapes.medium)
                        .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.28f))
                        .padding(10.dp)
                ) {
                    val density = LocalDensity.current
                    val pageWidthPx = with(density) { maxWidth.toPx() }
                    val pageHeightPx = with(density) { maxHeight.toPx() }
                    val densityPx = density

                    Text(
                        text = "Page Preview",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.align(Alignment.TopStart)
                    )

                    boxes.forEachIndexed { index, box ->
                        val leftDp = with(densityPx) { (box.x * pageWidthPx).toDp() }
                        val topDp = with(densityPx) { (box.y * pageHeightPx).toDp() }
                        val boxWidthDp = with(densityPx) { (box.width * pageWidthPx).toDp() }
                        val boxHeightDp = with(densityPx) { (box.height * pageHeightPx).toDp() }
                        Box(
                            modifier = Modifier
                                .offset(leftDp, topDp)
                                .zIndex(index.toFloat() + 1f)
                                .size(boxWidthDp, boxHeightDp)
                                .pointerInput(box.id) {
                                    detectDragGestures { change, dragAmount ->
                                        val newX = (box.x * pageWidthPx + dragAmount.x) / pageWidthPx
                                        val newY = (box.y * pageHeightPx + dragAmount.y) / pageHeightPx
                                        val maxX = (1f - box.width - 0.02f).coerceAtLeast(0.02f)
                                        val maxY = (1f - box.height - 0.02f).coerceAtLeast(0.02f)
                                        boxes = boxes.toMutableList().also { list ->
                                            list[index] = box.copy(
                                                x = normalizedBoxValue(newX, 0.02f, maxX),
                                                y = normalizedBoxValue(newY, 0.02f, maxY)
                                            )
                                        }
                                    }
                                }
                        ) {
                            Surface(
                                modifier = Modifier.fillMaxSize(),
                                shape = MaterialTheme.shapes.small,
                                color = MaterialTheme.colorScheme.surface,
                                tonalElevation = 2.dp,
                                shadowElevation = 1.dp,
                                border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)
                            ) {
                                Column(
                                    modifier = Modifier.padding(10.dp),
                                    verticalArrangement = Arrangement.spacedBy(6.dp)
                                ) {
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.SpaceBetween,
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Text(
                                            text = "Box ${index + 1}",
                                            style = MaterialTheme.typography.labelMedium,
                                            fontWeight = FontWeight.SemiBold
                                        )
                                        Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                            IconButton(onClick = { openEditor(index) }) {
                                                Icon(Icons.Default.Edit, contentDescription = "Edit text")
                                            }
                                            IconButton(onClick = {
                                                boxes = boxes.toMutableList().also { it.removeAt(index) }
                                            }) {
                                                Icon(Icons.Default.Delete, contentDescription = "Remove box")
                                            }
                                        }
                                    }
                                    Text(
                                        text = boldMarkdownAnnotatedText(defaultChapterBoxText(box)),
                                        style = MaterialTheme.typography.bodySmall.copy(lineHeight = 18.sp),
                                        color = MaterialTheme.colorScheme.onSurface,
                                        modifier = Modifier
                                            .weight(1f)
                                            .verticalScroll(rememberScrollState()),
                                        overflow = TextOverflow.Ellipsis
                                    )
                                }
                            }
                            Box(
                                modifier = Modifier
                                    .align(Alignment.BottomEnd)
                                    .size(24.dp)
                                    .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.16f), MaterialTheme.shapes.extraSmall)
                                    .border(1.dp, MaterialTheme.colorScheme.primary, MaterialTheme.shapes.extraSmall)
                                    .pointerInput("${box.id}_resize") {
                                        detectDragGestures { change, dragAmount ->
                                            change.consume()
                                            val newWidth = (box.width * pageWidthPx + dragAmount.x) / pageWidthPx
                                            val newHeight = (box.height * pageHeightPx + dragAmount.y) / pageHeightPx
                                            val maxWidth = (1f - box.x - 0.02f).coerceAtLeast(0.18f)
                                            val maxHeight = (1f - box.y - 0.02f).coerceAtLeast(0.08f)
                                            boxes = boxes.toMutableList().also { list ->
                                                list[index] = box.copy(
                                                    width = normalizedBoxValue(newWidth, 0.18f, maxWidth),
                                                    height = normalizedBoxValue(newHeight, 0.08f, maxHeight)
                                                )
                                            }
                                        }
                                    },
                                contentAlignment = Alignment.Center
                            ) {
                                Text(
                                    text = "::",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.primary
                                )
                            }
                        }
                    }
                }
            }
        }
    }

    if (editingIndex >= 0) {
        AlertDialog(
            onDismissRequest = { editingIndex = -1 },
            title = { Text("Edit Text Box") },
            text = {
                OutlinedTextField(
                    value = draftText,
                    onValueChange = { draftText = it },
                    modifier = Modifier.fillMaxWidth(),
                    minLines = 6
                )
            },
            confirmButton = {
                TextButton(onClick = {
                    replaceBoxText(editingIndex, draftText)
                    editingIndex = -1
                }) {
                    Text("Apply")
                }
            },
            dismissButton = {
                TextButton(onClick = { editingIndex = -1 }) {
                    Text("Cancel")
                }
            }
        )
    }
}

@Composable
fun RenderFigure(figure: com.rankwarz.edulabsrtm.model.FigureJson) {
    val imageSource = figure.imageUrl.ifBlank { figure.sourceUrl }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        shape = MaterialTheme.shapes.small,
        border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outline)
    ) {
        Column(modifier = Modifier.padding(10.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(
                text = figure.figureNumber.ifBlank { "Figure" },
                style = MaterialTheme.typography.labelLarge,
                fontWeight = FontWeight.Bold
            )
            if (figure.title.isNotBlank()) {
                Text(figure.title, style = MaterialTheme.typography.titleSmall)
            }
            if (imageSource.isNotBlank()) {
                SubcomposeAsyncImage(
                    model = imageSource,
                    contentDescription = figure.title.ifBlank { figure.figureNumber },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(220.dp),
                    contentScale = ContentScale.Fit
                )
            } else {
                Text(
                    text = "No figure image attached.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            if (figure.caption.isNotBlank()) {
                Text(
                    text = figure.caption,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
fun FiguresScreen(
    figures: List<FigureAsset>,
    pubMedFigures: List<PubMedFigureJson> = emptyList(),
    references: List<ReferenceAsset> = emptyList(),
    isProcessing: Boolean = false,
    onRetryFigures: () -> Unit = {},
    onSearchGoogle: (String) -> Unit,
    onUpdateImageUrl: (String, String, String) -> Unit
) {
    var editFigureAsset by remember { mutableStateOf<FigureAsset?>(null) }
    var figureImageInput by remember { mutableStateOf("") }
    var showPubMedFigurePicker by remember { mutableStateOf(false) }
    var selectedPubMedFigureIndex by remember { mutableIntStateOf(0) }
    var viewMode by rememberSaveable { mutableStateOf("Generated") }
    var figureQuery by rememberSaveable { mutableStateOf("") }
    val visibleFigures = remember(figures, figureQuery, viewMode) {
        figures.filter { asset ->
            val matchesQuery = figureQuery.isBlank() ||
                asset.chapterName.contains(figureQuery, ignoreCase = true) ||
                asset.figure.title.contains(figureQuery, ignoreCase = true) ||
                asset.figure.caption.contains(figureQuery, ignoreCase = true)
            val matchesMode = when (viewMode) {
                "Missing" -> asset.figure.imageUrl.isBlank()
                else -> true
            }
            matchesQuery && matchesMode
        }
    }
    val context = LocalContext.current
    val localImagePicker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocument()
    ) { uri ->
        val asset = editFigureAsset ?: return@rememberLauncherForActivityResult
        val picked = uri ?: return@rememberLauncherForActivityResult

        val mimeType = context.contentResolver.getType(picked).orEmpty()
        val extension = when {
            mimeType.contains("png", ignoreCase = true) -> "png"
            mimeType.contains("webp", ignoreCase = true) -> "webp"
            mimeType.contains("gif", ignoreCase = true) -> "gif"
            mimeType.contains("heic", ignoreCase = true) || mimeType.contains("heif", ignoreCase = true) -> "heic"
            else -> "jpg"
        }

        val safeChapter = asset.chapterName.lowercase().replace(Regex("[^a-z0-9]+"), "_").trim('_')
        val safeFigure = asset.figure.figureNumber.lowercase().replace(Regex("[^a-z0-9]+"), "_").trim('_')
        val figureDir = java.io.File(context.filesDir, "figure_images").apply { mkdirs() }
        val targetFile = java.io.File(
            figureDir,
            "figure_${safeChapter}_${safeFigure}_${System.currentTimeMillis()}.$extension"
        )

        val copied = runCatching {
            context.contentResolver.openInputStream(picked)?.use { input ->
                java.io.FileOutputStream(targetFile).use { output ->
                    input.copyTo(output)
                }
            }
            targetFile.exists() && targetFile.length() > 0
        }.getOrDefault(false)

        if (copied) {
            val localUri = android.net.Uri.fromFile(targetFile).toString()
            figureImageInput = localUri
            onUpdateImageUrl(asset.chapterName, asset.figure.figureNumber, localUri)
        }
    }

    Column(modifier = Modifier.fillMaxSize()) {
        FlowRow(
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 8.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            listOf("Generated", "PubMed", "Missing").forEach { mode ->
                AssistChip(
                    onClick = { viewMode = mode },
                    label = {
                        Text(
                            text = if (viewMode == mode) "✓ $mode" else mode,
                            fontWeight = if (viewMode == mode) FontWeight.Bold else FontWeight.Normal
                        )
                    }
                )
            }
        }
        OutlinedTextField(
            value = figureQuery,
            onValueChange = { figureQuery = it },
            label = { Text("Search figures") },
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 12.dp),
            singleLine = true
        )

        if (figures.isEmpty() && !isProcessing) {
            ElevatedCard(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 12.dp)
            ) {
                Row(
                    modifier = Modifier
                        .padding(16.dp)
                        .fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(
                        text = "Missing figures? Re-run generation.",
                        style = MaterialTheme.typography.bodyMedium,
                        modifier = Modifier.weight(1f)
                    )
                    Button(onClick = onRetryFigures) {
                        Text("Retry")
                    }
                }
            }
        }

        LazyColumn(
            verticalArrangement = Arrangement.spacedBy(12.dp),
            modifier = Modifier.weight(1f)
        ) {
            if (viewMode == "PubMed") {
                items(
                    items = pubMedFigures,
                    key = { "${it.pmid}_${it.figureId}_${it.imageUrl}" }
                ) { figure ->
                    ElevatedCard(modifier = Modifier.fillMaxWidth()) {
                        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text("PMID ${figure.pmid}", style = MaterialTheme.typography.labelLarge)
                            Text(figure.figureId.ifBlank { "PubMed figure" }, style = MaterialTheme.typography.titleMedium)
                            Text(figure.title.ifBlank { figure.caption.take(120) }, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
                            SubcomposeAsyncImage(
                                model = figure.localUri.ifBlank { figure.imageUrl.ifBlank { figure.thumbnailUrl } },
                                contentDescription = figure.title,
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(220.dp),
                                contentScale = ContentScale.Fit
                            )
                            if (figure.caption.isNotBlank()) {
                                Text(figure.caption, style = MaterialTheme.typography.bodySmall, maxLines = 4)
                            }
                        }
                    }
                }
            } else items(
                items = visibleFigures,
                key = { "${it.chapterName}_${it.figure.figureNumber}" }
            ) { asset ->
                ElevatedCard(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable {
                            editFigureAsset = asset
                            figureImageInput = asset.figure.imageUrl
                        }
                ) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(asset.chapterName, style = MaterialTheme.typography.labelLarge)
                        Text(asset.figure.figureNumber, style = MaterialTheme.typography.titleMedium)
                        Text(asset.figure.title, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
                        Text(asset.figure.caption, style = MaterialTheme.typography.bodySmall)

                        if (asset.figure.imageSearchQuery.isNotBlank()) {
                            Text("Search: ${asset.figure.imageSearchQuery}", style = MaterialTheme.typography.bodySmall)
                        }

                        if (asset.figure.imageUrl.isNotBlank()) {
                            SubcomposeAsyncImage(
                                model = asset.figure.imageUrl,
                                contentDescription = asset.figure.title,
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(240.dp),
                                contentScale = ContentScale.Fit,
                                loading = {
                                    Box(
                                        modifier = Modifier.fillMaxSize(),
                                        contentAlignment = Alignment.Center
                                    ) {
                                        CircularProgressIndicator()
                                    }
                                },
                                error = {
                                    Box(
                                        modifier = Modifier.fillMaxSize(),
                                        contentAlignment = Alignment.Center
                                    ) {
                                        Text(
                                            text = "Failed to load image",
                                            color = MaterialTheme.colorScheme.error
                                        )
                                    }
                                    }
                                )

                        val imageLabel = if (asset.figure.imageUrl.startsWith("file:", ignoreCase = true)) {
                            "Local image selected"
                        } else {
                            asset.figure.imageUrl
                        }
                        Text("Image: $imageLabel", style = MaterialTheme.typography.bodySmall)
                        } else {
                            Card(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(180.dp)
                            ) {
                                Box(
                                    modifier = Modifier.fillMaxSize(),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Text("No image available")
                                }
                            }
                        }

                        if (asset.figure.sourceUrl.isNotBlank()) {
                            AssistChip(onClick = {}, label = { Text("Source attached") })
                        }

                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Button(onClick = {
                                val query = if(asset.figure.imageSearchQuery.isNotBlank()) asset.figure.imageSearchQuery else asset.figure.title
                                onSearchGoogle(query)
                            }) {
                                Text("Search Google")
                            }
                        }
                    }
                }
            }
        }
    }

    editFigureAsset?.let { asset ->
        val figurePubMedFigures = pubMedFiguresForFigure(asset, pubMedFigures, references)
        val hasChapterPubMedReferences = hasChapterPubMedReferences(asset, references)
        AlertDialog(
            onDismissRequest = {
                editFigureAsset = null
                figureImageInput = ""
                showPubMedFigurePicker = false
            },
            title = { Text("Add figure image") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    val previewUrl = figureImageInput.trim()
                    if (previewUrl.isNotBlank()) {
                        SubcomposeAsyncImage(
                            model = previewUrl,
                            contentDescription = asset.figure.title,
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(180.dp),
                            contentScale = ContentScale.Fit
                        )
                    } else {
                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(180.dp)
                        ) {
                            Box(
                                modifier = Modifier.fillMaxSize(),
                                contentAlignment = Alignment.Center
                            ) {
                                Text("Choose a local image")
                            }
                        }
                    }

                    Button(
                        onClick = {
                            localImagePicker.launch(arrayOf("image/*"))
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Upload Local Image")
                    }

                    Button(
                        onClick = {
                            showPubMedFigurePicker = true
                            selectedPubMedFigureIndex = selectedPubMedFigureIndex.coerceIn(
                                0,
                                (figurePubMedFigures.size - 1).coerceAtLeast(0)
                            )
                        },
                        enabled = figurePubMedFigures.isNotEmpty(),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Choose PubMed Figure")
                    }

                    if (figurePubMedFigures.isEmpty()) {
                        Text(
                            text = "No downloaded PubMed figures are available.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    } else {
                        Text(
                            text = if (hasChapterPubMedReferences) {
                                "PubMed figures shown here come only from PMID references cited in this figure/chapter."
                            } else {
                                "No PMID reference is linked to this chapter, so all downloaded PubMed figures are shown."
                            },
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }

                    if (showPubMedFigurePicker && figurePubMedFigures.isNotEmpty()) {
                        val effectivePubMedFigureIndex = selectedPubMedFigureIndex.coerceIn(0, figurePubMedFigures.lastIndex)
                        val selected = figurePubMedFigures[effectivePubMedFigureIndex]
                        ElevatedCard(modifier = Modifier.fillMaxWidth()) {
                            Column(
                                modifier = Modifier.padding(12.dp),
                                verticalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                SubcomposeAsyncImage(
                                    model = selected.localUri.ifBlank { selected.imageUrl.ifBlank { selected.thumbnailUrl } },
                                    contentDescription = selected.title,
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .height(190.dp),
                                    contentScale = ContentScale.Fit,
                                    loading = {
                                        Box(
                                            modifier = Modifier.fillMaxSize(),
                                            contentAlignment = Alignment.Center
                                        ) {
                                            CircularProgressIndicator()
                                        }
                                    }
                                )
                                Text(
                                    text = "${selected.figureId.ifBlank { "Figure" }} • ${selected.pmcId} • PMID ${selected.pmid}",
                                    style = MaterialTheme.typography.labelLarge
                                )
                                if (selected.caption.isNotBlank()) {
                                    Text(
                                        text = selected.caption,
                                        style = MaterialTheme.typography.bodySmall,
                                        maxLines = 3
                                    )
                                }
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    OutlinedButton(
                                        onClick = {
                                            selectedPubMedFigureIndex =
                                                if (selectedPubMedFigureIndex <= 0) figurePubMedFigures.lastIndex else selectedPubMedFigureIndex - 1
                                        }
                                    ) {
                                        Text("Previous")
                                    }
                                    Text(
                                        text = "${effectivePubMedFigureIndex + 1}/${figurePubMedFigures.size}",
                                        style = MaterialTheme.typography.bodySmall
                                    )
                                    OutlinedButton(
                                        onClick = {
                                            selectedPubMedFigureIndex =
                                                if (selectedPubMedFigureIndex >= figurePubMedFigures.lastIndex) 0 else selectedPubMedFigureIndex + 1
                                        }
                                    ) {
                                        Text("Next")
                                    }
                                }
                                Button(
                                    onClick = {
                                        val chosen = selected.localUri.ifBlank { selected.imageUrl.ifBlank { selected.thumbnailUrl } }
                                        figureImageInput = chosen
                                        onUpdateImageUrl(asset.chapterName, asset.figure.figureNumber, chosen)
                                    },
                                    modifier = Modifier.fillMaxWidth()
                                ) {
                                    Text("Use This PubMed Figure")
                                }
                            }
                        }
                    }
                }
            },
            confirmButton = {
                Button(onClick = {
                    onUpdateImageUrl(asset.chapterName, asset.figure.figureNumber, figureImageInput.trim())
                    editFigureAsset = null
                    figureImageInput = ""
                    showPubMedFigurePicker = false
                }) {
                    Text("Save")
                }
            },
            dismissButton = {
                TextButton(onClick = {
                    editFigureAsset = null
                    figureImageInput = ""
                    showPubMedFigurePicker = false
                }) {
                    Text("Cancel")
                }
            }
        )
    }
}

@Composable
fun TablesScreen(
    tables: List<TableAsset>,
    isProcessing: Boolean = false,
    onRetryTables: () -> Unit = {}
) {
    var query by rememberSaveable { mutableStateOf("") }
    var expandedKeys by rememberSaveable { mutableStateOf(listOf<String>()) }
    val filteredTables = remember(tables, query) {
        tables.filter {
            query.isBlank() ||
                it.chapterName.contains(query, ignoreCase = true) ||
                it.table.title.contains(query, ignoreCase = true) ||
                it.table.tableNumber.contains(query, ignoreCase = true)
        }
    }

    Column(modifier = Modifier.fillMaxSize()) {
        OutlinedTextField(
            value = query,
            onValueChange = { query = it },
            label = { Text("Search tables") },
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 12.dp),
            singleLine = true
        )

        if (tables.isEmpty() && !isProcessing) {
            ElevatedCard(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 12.dp)
            ) {
                Row(
                    modifier = Modifier
                        .padding(16.dp)
                        .fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(
                        text = "Missing tables? Re-run generation.",
                        style = MaterialTheme.typography.bodyMedium,
                        modifier = Modifier.weight(1f)
                    )
                    Button(onClick = onRetryTables) {
                        Text("Retry")
                    }
                }
            }
        }

        LazyColumn(
            verticalArrangement = Arrangement.spacedBy(12.dp),
            modifier = Modifier.weight(1f)
        ) {
            items(
                items = filteredTables,
                key = { "${it.chapterName}_${it.table.tableNumber}_${it.table.title}" }
            ) { asset ->
                val key = "${asset.chapterName}_${asset.table.tableNumber}_${asset.table.title}"
                val expanded = key in expandedKeys
                val rowCount = asset.table.rows.ifEmpty { asset.table.data.map { row -> row.values.map { it.toString() } } }.size
                ElevatedCard(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(asset.chapterName, style = MaterialTheme.typography.labelLarge)
                        Text(asset.table.tableNumber.ifBlank { "Table" }, style = MaterialTheme.typography.titleMedium)
                        Text(asset.table.title, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
                        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            AssistChip(onClick = {}, label = { Text("$rowCount rows") })
                            if (asset.table.headers.isEmpty() && asset.table.rows.isEmpty()) {
                                AssistChip(onClick = {}, label = { Text("Needs review") })
                            }
                        }
                        if (expanded) {
                            RenderTable(asset.table)
                        } else {
                            Text(
                                text = asset.table.footnote.orEmpty().ifBlank { "Tap Show full to inspect the complete table." },
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                        TextButton(
                            onClick = {
                                expandedKeys = if (expanded) expandedKeys - key else expandedKeys + key
                            }
                        ) {
                            Text(if (expanded) "Hide full" else "Show full")
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun ChartsScreen(
    charts: List<ChartAsset>,
    isProcessing: Boolean = false,
    onRetryCharts: () -> Unit = {}
) {
    var selectedType by rememberSaveable { mutableStateOf("All") }
    var expandedRawKeys by rememberSaveable { mutableStateOf(listOf<String>()) }
    val chartTypes = remember(charts) { listOf("All") + charts.map { it.chart.type.ifBlank { "auto" } }.distinct().sorted() }
    val filteredCharts = remember(charts, selectedType) {
        charts.filter { selectedType == "All" || it.chart.type.ifBlank { "auto" }.equals(selectedType, ignoreCase = true) }
    }

    Column(modifier = Modifier.fillMaxSize()) {
        FlowRow(
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 12.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            chartTypes.forEach { type ->
                AssistChip(
                    onClick = { selectedType = type },
                    label = {
                        Text(
                            text = if (selectedType == type) "✓ $type" else type,
                            fontWeight = if (selectedType == type) FontWeight.Bold else FontWeight.Normal
                        )
                    }
                )
            }
        }

        if (charts.isEmpty() && !isProcessing) {
            ElevatedCard(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 12.dp)
            ) {
                Row(
                    modifier = Modifier
                        .padding(16.dp)
                        .fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(
                        text = "Missing charts? Re-run generation.",
                        style = MaterialTheme.typography.bodyMedium,
                        modifier = Modifier.weight(1f)
                    )
                    Button(onClick = onRetryCharts) {
                        Text("Retry")
                    }
                }
            }
        }

        LazyColumn(
            verticalArrangement = Arrangement.spacedBy(12.dp),
            modifier = Modifier.weight(1f)
        ) {
            items(
                items = filteredCharts,
                key = { "${it.chapterName}_${it.chart.chartId}_${it.chart.title}" }
            ) { asset ->
                val key = "${asset.chapterName}_${asset.chart.chartId}_${asset.chart.title}"
                val rawExpanded = key in expandedRawKeys
                val hasData = chartDatasets(asset.chart).any { it.values.isNotEmpty() }
                ElevatedCard(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(asset.chapterName, style = MaterialTheme.typography.labelLarge)
                        Text(asset.chart.chartId.ifBlank { "Chart" }, style = MaterialTheme.typography.titleMedium)
                        Text(asset.chart.title, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
                        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            AssistChip(onClick = {}, label = { Text("Type: ${asset.chart.type.ifBlank { "auto" }}") })
                            if (!hasData) AssistChip(onClick = {}, label = { Text("Empty data") })
                        }
                        if (asset.chart.chartTemplate.isNotBlank()) {
                            Text("Template: ${asset.chart.chartTemplate}", style = MaterialTheme.typography.bodySmall)
                        }
                        RenderChart(asset.chart)
                        TextButton(onClick = { expandedRawKeys = if (rawExpanded) expandedRawKeys - key else expandedRawKeys + key }) {
                            Text(if (rawExpanded) "Hide raw" else "Show raw")
                        }
                        if (rawExpanded) {
                            Text(
                                text = Gson().toJson(asset.chart),
                                style = MaterialTheme.typography.bodySmall,
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.35f), MaterialTheme.shapes.small)
                                    .padding(10.dp)
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ReferenceCacheSyncCard(
    verifiedReferenceCount: Int,
    abstractCount: Int,
    similarArticleCount: Int,
    lastSyncedAt: Long,
    syncInProgress: Boolean,
    syncCurrent: Int,
    syncTotal: Int,
    syncError: String?,
    onSyncCache: () -> Unit
) {
    ElevatedCard(
        modifier = Modifier
            .fillMaxWidth()
            .padding(bottom = 12.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text("Verified cache", style = MaterialTheme.typography.titleSmall)
                    Text(
                        text = "$verifiedReferenceCount refs • $abstractCount abstracts • $similarArticleCount similar articles",
                        style = MaterialTheme.typography.bodySmall
                    )
                    Text(
                        text = when {
                            syncInProgress -> "Syncing to Firestore $syncCurrent/${syncTotal.coerceAtLeast(1)}"
                            lastSyncedAt > 0L -> "Cache synced ${relativeTimeLabel(lastSyncedAt)}"
                            else -> "Cache not synced yet"
                        },
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                Button(onClick = onSyncCache, enabled = !syncInProgress) {
                    Text(if (syncInProgress) "Syncing" else "Sync now")
                }
            }
            if (syncInProgress) {
                LinearProgressIndicator(
                    progress = { if (syncTotal > 0) syncCurrent.toFloat() / syncTotal.toFloat() else 0f },
                    modifier = Modifier.fillMaxWidth()
                )
            }
            if (!syncError.isNullOrBlank()) {
                Text(
                    text = "Firestore sync warning: $syncError",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error
                )
            }
        }
    }
}

private fun relativeTimeLabel(timestamp: Long): String {
    val elapsedMs = (System.currentTimeMillis() - timestamp).coerceAtLeast(0L)
    val minutes = elapsedMs / 60_000L
    val hours = minutes / 60L
    val days = hours / 24L
    return when {
        minutes < 1 -> "just now"
        minutes < 60 -> "$minutes min ago"
        hours < 24 -> "$hours hr ago"
        else -> "$days d ago"
    }
}

@Composable
fun AbstractsScreen(
    sources: List<PubMedAbstractSourceJson>,
    verifiedReferenceCount: Int,
    lastSyncedAt: Long,
    syncInProgress: Boolean,
    syncCurrent: Int,
    syncTotal: Int,
    syncError: String?,
    isProcessing: Boolean = false,
    onRefresh: () -> Unit = {},
    onSyncCache: () -> Unit = {}
) {
    val context = LocalContext.current
    var query by rememberSaveable { mutableStateOf("") }
    var filter by rememberSaveable { mutableStateOf("All") }
    var expandedSimilarPmids by rememberSaveable { mutableStateOf(listOf<String>()) }
    val filteredSources = remember(sources, query, filter) {
        sources.filter { source ->
            val similarCount = source.similarArticles.size + source.citedBy.size
            val matchesFilter = when (filter) {
                "Abstract" -> source.abstractText.isNotBlank() || source.abstractSections.isNotEmpty()
                "Similar" -> similarCount > 0
                "Missing DOI" -> source.doi.orEmpty().isBlank()
                else -> true
            }
            val matchesQuery = query.isBlank() ||
                source.title.contains(query, ignoreCase = true) ||
                source.citation.contains(query, ignoreCase = true) ||
                source.pmid.contains(query, ignoreCase = true) ||
                source.doi.orEmpty().contains(query, ignoreCase = true)
            matchesFilter && matchesQuery
        }
    }
    fun openPubMed(pmid: String) {
        if (pmid.isBlank()) return
        runCatching {
            context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse("https://pubmed.ncbi.nlm.nih.gov/${pmid.trim()}/")))
        }
    }

    Column(modifier = Modifier.fillMaxSize()) {
        ReferenceCacheSyncCard(
            verifiedReferenceCount = verifiedReferenceCount,
            abstractCount = sources.size,
            similarArticleCount = sources.sumOf { it.similarArticles.size + it.citedBy.size },
            lastSyncedAt = lastSyncedAt,
            syncInProgress = syncInProgress,
            syncCurrent = syncCurrent,
            syncTotal = syncTotal,
            syncError = syncError,
            onSyncCache = onSyncCache
        )

        OutlinedTextField(
            value = query,
            onValueChange = { query = it },
            label = { Text("Search PMID, DOI, title, citation") },
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 8.dp),
            singleLine = true
        )
        FlowRow(
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 12.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            listOf("All", "Abstract", "Similar", "Missing DOI").forEach { option ->
                AssistChip(
                    onClick = { filter = option },
                    label = {
                        Text(
                            text = if (filter == option) "✓ $option" else option,
                            fontWeight = if (filter == option) FontWeight.Bold else FontWeight.Normal
                        )
                    }
                )
            }
        }

        ElevatedCard(
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 12.dp)
        ) {
            Row(
                modifier = Modifier
                    .padding(16.dp)
                    .fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text("PubMed Abstract Corpus", style = MaterialTheme.typography.titleMedium)
                    Text(
                        text = "${sources.size} validated abstracts with similar articles",
                        style = MaterialTheme.typography.bodySmall
                    )
                }
                Button(
                    onClick = onRefresh,
                    enabled = !isProcessing
                ) {
                    Text("Refresh")
                }
            }
        }

        if (sources.isEmpty() && !isProcessing) {
            EmptyStateCard(
                title = "No abstracts downloaded",
                subtitle = "Extract a PDF with references or refresh after adding References_Vancouver."
            )
            return
        }

        LazyColumn(
            verticalArrangement = Arrangement.spacedBy(12.dp),
            modifier = Modifier.weight(1f)
        ) {
            items(
                items = filteredSources,
                key = { it.pmid.ifBlank { it.citation.take(80) } }
            ) { source ->
                ElevatedCard(modifier = Modifier.fillMaxWidth()) {
                    Column(
                        modifier = Modifier.padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = source.title.ifBlank { "PubMed source" },
                                style = MaterialTheme.typography.titleMedium,
                                modifier = Modifier.weight(1f)
                            )
                            AssistChip(
                                onClick = { openPubMed(source.pmid) },
                                label = { Text("PMID: ${source.pmid}") },
                                leadingIcon = {
                                    Icon(
                                        imageVector = Icons.AutoMirrored.Filled.OpenInNew,
                                        contentDescription = null,
                                        modifier = Modifier.size(16.dp)
                                    )
                                }
                            )
                        }

                        if (source.doi.orEmpty().isNotBlank()) {
                            Text("DOI: ${source.doi}", style = MaterialTheme.typography.bodySmall)
                        }
                        Text(source.citation, style = MaterialTheme.typography.bodyMedium)
                        if (source.abstractText.isNotBlank()) {
                            Surface(
                                modifier = Modifier.fillMaxWidth(),
                                color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.22f),
                                shape = MaterialTheme.shapes.medium
                            ) {
                                Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                    Text("Abstract text", style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.SemiBold)
                                    Text(source.abstractText, style = MaterialTheme.typography.bodyMedium)
                                }
                            }
                        }

                        HorizontalDivider()
                        AbstractSectionsBlock(
                            title = "Separated abstract headings",
                            sections = source.abstractSections,
                            fallbackText = source.abstractText.ifBlank { "No abstract is available for this PubMed record." }
                        )

                        HorizontalDivider()
                        val similarArticles = source.similarArticles.ifEmpty { source.citedBy }
                        val similarExpanded = source.pmid in expandedSimilarPmids || similarArticles.size <= 3
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = "Similar articles (${similarArticles.size})",
                                style = MaterialTheme.typography.labelLarge
                            )
                            TextButton(
                                onClick = {
                                    expandedSimilarPmids = if (source.pmid in expandedSimilarPmids) {
                                        expandedSimilarPmids - source.pmid
                                    } else {
                                        expandedSimilarPmids + source.pmid
                                    }
                                },
                                enabled = similarArticles.isNotEmpty()
                            ) {
                                Text(if (similarExpanded) "Collapse" else "Expand")
                            }
                        }
                        if (similarArticles.isEmpty()) {
                            Text("No similar articles are available for this PubMed record.", style = MaterialTheme.typography.bodySmall)
                        } else {
                            val itemsToShow = if (similarExpanded) similarArticles else similarArticles.take(3)
                            if (!similarExpanded) {
                                Text("Showing a compact list; open more only when needed.", style = MaterialTheme.typography.bodySmall)
                            }
                            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                itemsToShow.forEach { similar ->
                                    Surface(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .clickable { openPubMed(similar.pmid) },
                                        tonalElevation = 1.dp
                                    ) {
                                        Column(
                                            modifier = Modifier.padding(10.dp),
                                            verticalArrangement = Arrangement.spacedBy(4.dp)
                                        ) {
                                            Text(
                                                text = similar.title.ifBlank { similar.citation.ifBlank { "Similar article" } },
                                                style = MaterialTheme.typography.bodyMedium,
                                                fontWeight = FontWeight.SemiBold
                                            )
                                            Text("PMID: ${similar.pmid}${similar.doi?.let { " | DOI: $it" }.orEmpty()}", style = MaterialTheme.typography.bodySmall)
                                            if (similar.citation.isNotBlank()) {
                                                Text(similar.citation, style = MaterialTheme.typography.bodySmall)
                                            }
                                            if (similar.abstractText.isNotBlank() || similar.abstractSections.isNotEmpty()) {
                                                AbstractSectionsBlock(
                                                    title = "Abstract",
                                                    sections = similar.abstractSections,
                                                    fallbackText = similar.abstractText.ifBlank { "No abstract text saved." },
                                                    compact = true
                                                )
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
}

@Composable
private fun AbstractSectionsBlock(
    title: String,
    sections: List<PubMedAbstractSectionJson>,
    fallbackText: String,
    compact: Boolean = false
) {
    Text(title, style = if (compact) MaterialTheme.typography.labelSmall else MaterialTheme.typography.labelLarge)
    if (sections.isEmpty()) {
        Text(
            fallbackText,
            style = if (compact) MaterialTheme.typography.bodySmall else MaterialTheme.typography.bodyMedium
        )
        return
    }

    Column(verticalArrangement = Arrangement.spacedBy(if (compact) 4.dp else 8.dp)) {
        sections.forEach { section ->
            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(
                    text = abstractSectionDisplayHeading(section),
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.SemiBold
                )
                Text(
                    text = section.text,
                    style = if (compact) MaterialTheme.typography.bodySmall else MaterialTheme.typography.bodyMedium
                )
            }
        }
    }
}

private fun abstractSectionDisplayHeading(section: PubMedAbstractSectionJson): String {
    val label = section.label.ifBlank { section.category }
    val category = section.category.ifBlank { "abstract" }
    return if (label.equals(category, ignoreCase = true)) {
        category.replaceFirstChar { it.uppercase() }
    } else {
        "${category.replaceFirstChar { it.uppercase() }} / $label"
    }
}

@Composable
fun ReferencesScreen(
    references: List<ReferenceAsset>,
    abstractCount: Int,
    similarArticleCount: Int,
    lastSyncedAt: Long,
    syncInProgress: Boolean,
    syncCurrent: Int,
    syncTotal: Int,
    syncError: String?,
    onSyncCache: () -> Unit,
    onJumpToChapter: (String) -> Unit,
    isProcessing: Boolean = false,
    onRetryReferences: () -> Unit = {}
) {
    val context = LocalContext.current
    var query by rememberSaveable { mutableStateOf("") }
    var filter by rememberSaveable { mutableStateOf("All") }
    val filteredReferences = remember(references, query, filter) {
        references.filter { reference ->
            val matchesFilter = when (filter) {
                "PMID" -> reference.pmid.isNotBlank()
                "DOI" -> reference.doi.isNotBlank()
                "Unverified" -> !reference.pubmedVerified
                else -> true
            }
            val matchesQuery = query.isBlank() ||
                reference.chapterName.contains(query, ignoreCase = true) ||
                reference.text.contains(query, ignoreCase = true) ||
                reference.pmid.contains(query, ignoreCase = true) ||
                reference.doi.contains(query, ignoreCase = true)
            matchesFilter && matchesQuery
        }
    }

    fun openPubMed(pmid: String) {
        if (pmid.isBlank()) return
        val url = "https://pubmed.ncbi.nlm.nih.gov/${pmid.trim()}/"
        runCatching {
            context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
        }
    }

    Column(modifier = Modifier.fillMaxSize()) {
        ReferenceCacheSyncCard(
            verifiedReferenceCount = references.count { it.pmid.isNotBlank() },
            abstractCount = abstractCount,
            similarArticleCount = similarArticleCount,
            lastSyncedAt = lastSyncedAt,
            syncInProgress = syncInProgress,
            syncCurrent = syncCurrent,
            syncTotal = syncTotal,
            syncError = syncError,
            onSyncCache = onSyncCache
        )

        OutlinedTextField(
            value = query,
            onValueChange = { query = it },
            label = { Text("Search references") },
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 8.dp),
            singleLine = true
        )
        FlowRow(
            modifier = Modifier
                .fillMaxWidth()
                .padding(bottom = 12.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            listOf("All", "PMID", "DOI", "Unverified").forEach { option ->
                AssistChip(
                    onClick = { filter = option },
                    label = {
                        Text(
                            text = if (filter == option) "✓ $option" else option,
                            fontWeight = if (filter == option) FontWeight.Bold else FontWeight.Normal
                        )
                    }
                )
            }
        }

        if (references.isEmpty() && !isProcessing) {
            ElevatedCard(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 12.dp)
            ) {
                Row(
                    modifier = Modifier
                        .padding(16.dp)
                        .fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(
                        text = "Missing references? Re-run generation.",
                        style = MaterialTheme.typography.bodyMedium,
                        modifier = Modifier.weight(1f)
                    )
                    Button(onClick = onRetryReferences) {
                        Text("Retry")
                    }
                }
            }
        }

        LazyColumn(
            verticalArrangement = Arrangement.spacedBy(12.dp),
            modifier = Modifier.weight(1f)
        ) {
            items(
                items = filteredReferences,
                key = {
                    when {
                        it.pmid.isNotBlank() -> "pmid_${it.pmid}"
                        it.doi.isNotBlank() -> "doi_${it.doi}"
                        else -> "${it.chapterName}_${it.citation}_${it.text.take(80)}"
                    }
                }
            ) { asset ->
                val referenceModifier = if (asset.pmid.isNotBlank()) {
                    Modifier
                        .fillMaxWidth()
                        .clickable { openPubMed(asset.pmid) }
                } else {
                    Modifier.fillMaxWidth()
                }
                ElevatedCard(modifier = referenceModifier) {
                    Column(
                        modifier = Modifier.padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            AssistChip(
                                onClick = { onJumpToChapter(asset.chapterName) },
                                label = { Text(asset.chapterName) }
                            )
                            AssistChip(
                                onClick = { if (asset.pmid.isNotBlank()) openPubMed(asset.pmid) },
                                label = {
                                    Text(if (asset.pubmedVerified) "PMID verified" else "Unverified")
                                }
                            )
                        }
                        Text(asset.citation.ifBlank { "Reference" }, style = MaterialTheme.typography.titleMedium)
                        Text(asset.text, style = MaterialTheme.typography.bodyMedium)
                        if (asset.pmid.isNotBlank() || asset.doi.isNotBlank()) {
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                if (asset.pmid.isNotBlank()) {
                                    AssistChip(
                                        onClick = { openPubMed(asset.pmid) },
                                        label = { Text("PMID: ${asset.pmid}") },
                                        leadingIcon = {
                                            Icon(
                                                imageVector = Icons.AutoMirrored.Filled.OpenInNew,
                                                contentDescription = null,
                                                modifier = Modifier.size(16.dp)
                                            )
                                        }
                                    )
                                }
                                if (asset.doi.isNotBlank()) {
                                    AssistChip(onClick = {}, label = { Text("DOI") })
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun AnalyticsScreen(
    uiState: ThesisViewModel.UiState,
    qualityScore: ThesisQualityScore,
    onRetryFailed: () -> Unit,
    onSelectTab: (Int) -> Unit
) {
    val chapters = uiState.chapters
    val success = chapters.count { it.status == Chapter.ChapterStatus.SUCCESS }
    val failed = chapters.count { it.status == Chapter.ChapterStatus.ERROR }
    val pending = chapters.count { it.status == Chapter.ChapterStatus.LOADING || it.status == Chapter.ChapterStatus.IDLE || it.status == Chapter.ChapterStatus.PENDING }

    Column(
        verticalArrangement = Arrangement.spacedBy(12.dp),
        modifier = Modifier.fillMaxSize()
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxWidth()) {
            StatCard(title = "Success", value = success.toString(), modifier = Modifier.weight(1f))
            StatCard(title = "Failed", value = failed.toString(), modifier = Modifier.weight(1f))
            StatCard(title = "Pending", value = pending.toString(), modifier = Modifier.weight(1f))
        }

        ElevatedCard(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Provider / Chapter Health", style = MaterialTheme.typography.titleMedium)
                Text("Provider: ${uiState.selectedProvider}", style = MaterialTheme.typography.bodySmall)
                Text("Completion: ${uiState.completionPercent}%", style = MaterialTheme.typography.bodySmall)
                LinearProgressIndicator(
                    progress = { uiState.completionPercent.coerceIn(0, 100) / 100f },
                    modifier = Modifier.fillMaxWidth()
                )
                Text("Quality Score: ${qualityScore.overall}/100", style = MaterialTheme.typography.bodySmall)
                if (failed > 0) {
                    Button(onClick = onRetryFailed) {
                        Text("Retry Failed Chapters")
                    }
                }
            }
        }

        ElevatedCard(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Figure / Reference Summary", style = MaterialTheme.typography.titleMedium)
                Text("Figures: ${chapters.sumOf { it.figures.size }}", style = MaterialTheme.typography.bodySmall)
                Text("References: ${chapters.sumOf { it.chapterReferences.size }}", style = MaterialTheme.typography.bodySmall)
                Text("Variables: ${uiState.variables.size}", style = MaterialTheme.typography.bodySmall)
            }
        }

        ElevatedCard(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("QA Checklist", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                val issues = buildList {
                    if (failed > 0) add(Triple("Failed chapters", "$failed chapters need retry or review.", 2))
                    if (uiState.variables.any { it.value.isBlank() }) add(Triple("Missing variables", "Some extracted variables are still blank.", 1))
                    if (chapters.sumOf { it.chapterReferences.size } == 0) add(Triple("No chapter references", "References are not attached to chapters yet.", 7))
                    if (chapters.sumOf { it.figures.size } == 0) add(Triple("No figures", "Figure extraction/generation has not produced assets.", 4))
                    if (uiState.referenceCacheLastSyncedAt <= 0L) add(Triple("Cache not synced", "Verified references have not been uploaded to the cache backend.", 7))
                }
                if (issues.isEmpty()) {
                    Text("No obvious UI-visible issues found.", style = MaterialTheme.typography.bodySmall)
                } else {
                    issues.forEach { (title, message, tabIndex) ->
                        Surface(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { onSelectTab(tabIndex) },
                            tonalElevation = 1.dp,
                            shape = MaterialTheme.shapes.medium
                        ) {
                            Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                Text(title, style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.SemiBold)
                                Text(message, style = MaterialTheme.typography.bodySmall)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun StatCard(
    title: String,
    value: String,
    modifier: Modifier = Modifier
) {
    ElevatedCard(modifier = modifier) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(title, style = MaterialTheme.typography.labelMedium)
            Text(value, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
        }
    }
}

@Composable
fun EmptyStateCard(
    title: String,
    subtitle: String
) {
    ElevatedCard(modifier = Modifier.fillMaxSize()) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Icon(Icons.AutoMirrored.Filled.OpenInNew, contentDescription = null, modifier = Modifier.size(40.dp))
            Spacer(modifier = Modifier.height(12.dp))
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Spacer(modifier = Modifier.height(6.dp))
            Text(subtitle, style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
fun ProviderStatusBadge(
    uiState: ThesisViewModel.UiState,
    modifier: Modifier = Modifier
) {
    val isLocked = uiState.processing || uiState.chapters.any { it.status == Chapter.ChapterStatus.LOADING }
    val provider = uiState.selectedProvider
    val (text, containerColor, contentColor) = when {
        isLocked -> Triple(
            "🔒 Locked to ${provider.uppercase()}",
            MaterialTheme.colorScheme.errorContainer,
            MaterialTheme.colorScheme.onErrorContainer
        )
        provider.equals("auto", ignoreCase = true) -> Triple(
            "⚡ Auto Provider",
            MaterialTheme.colorScheme.primaryContainer,
            MaterialTheme.colorScheme.onPrimaryContainer
        )
        else -> Triple(
            "🔗 Bound to ${provider.uppercase()}",
            MaterialTheme.colorScheme.secondaryContainer,
            MaterialTheme.colorScheme.onSecondaryContainer
        )
    }

    Surface(
        color = containerColor,
        contentColor = contentColor,
        shape = RoundedCornerShape(8.dp),
        modifier = modifier
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            Text(
                text = text,
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.Bold
            )
        }
    }
}

@Composable
fun getProviderBadgeColors(provider: String): Pair<Color, Color> {
    val p = provider.lowercase()
    return when {
        p.contains("groq") -> Color(0xFF2E7D32) to Color(0xFFE8F5E9)
        p.contains("gemini") -> Color(0xFF1565C0) to Color(0xFFE3F2FD)
        p.contains("openai") -> Color(0xFF00796B) to Color(0xFFE0F2F1)
        p.contains("anthropic") -> Color(0xFFD84315) to Color(0xFFFBE9E7)
        p.contains("deepseek") -> Color(0xFF6A1B9A) to Color(0xFFF3E5F5)
        else -> MaterialTheme.colorScheme.onSecondaryContainer to MaterialTheme.colorScheme.secondaryContainer
    }
}

@Composable
fun ExportQualityChecklistPanel(
    checks: List<ExportQualityCheck>,
    compact: Boolean = false
) {
    val passed = checks.count { it.passed }
    val total = checks.size
    ElevatedCard(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(if (compact) 12.dp else 16.dp),
            verticalArrangement = Arrangement.spacedBy(if (compact) 6.dp else 10.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Export Readiness",
                    style = if (compact) MaterialTheme.typography.titleSmall else MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
                Surface(
                    color = if (passed == total) Color(0xFFE8F5E9) else MaterialTheme.colorScheme.errorContainer,
                    contentColor = if (passed == total) Color(0xFF2E7D32) else MaterialTheme.colorScheme.onErrorContainer,
                    shape = RoundedCornerShape(6.dp)
                ) {
                    Text(
                        "$passed/$total",
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp),
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
            checks.forEach { check ->
                QualityCheckRow(check = check, compact = compact)
            }
        }
    }
}

@Composable
fun QualityCheckRow(check: ExportQualityCheck, compact: Boolean = false) {
    val statusColor = if (check.passed) Color(0xFF2E7D32) else MaterialTheme.colorScheme.error
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(10.dp),
        verticalAlignment = Alignment.Top
    ) {
        Surface(
            color = statusColor.copy(alpha = 0.12f),
            contentColor = statusColor,
            shape = RoundedCornerShape(4.dp)
        ) {
            Text(
                if (check.passed) "PASS" else "FIX",
                modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                style = MaterialTheme.typography.labelSmall,
                fontWeight = FontWeight.Bold
            )
        }
        Column(modifier = Modifier.weight(1f)) {
            Text(
                check.label,
                style = if (compact) MaterialTheme.typography.bodySmall else MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.SemiBold
            )
            if (!compact || !check.passed) {
                Text(
                    check.detail,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
fun QualityCheckScreen(
    checks: List<ExportQualityCheck>,
    uiState: ThesisViewModel.UiState,
    references: List<ReferenceAsset>,
    tables: List<TableAsset>,
    figures: List<FigureAsset>,
    onExport: () -> Unit,
    onGoReferences: () -> Unit,
    onGoChapters: () -> Unit,
    onGoWorker: () -> Unit
) {
    val ready = checks.lastOrNull { it.label == "PDF export ready" }?.passed == true
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        ExportQualityChecklistPanel(checks = checks)

        ElevatedCard(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("Thesis Assets", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    StatChip("Chapters", uiState.chapters.size, Color(0xFF1976D2), Modifier.weight(1f))
                    StatChip("References", references.size, Color(0xFF2E7D32), Modifier.weight(1f))
                    StatChip("Tables", tables.size, Color(0xFF7B1FA2), Modifier.weight(1f))
                    StatChip("Figures", figures.size, Color(0xFFF57C00), Modifier.weight(1f))
                }
            }
        }

        ElevatedCard(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("Fix Shortcuts", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = onGoChapters, modifier = Modifier.weight(1f)) { Text("Chapters") }
                    OutlinedButton(onClick = onGoReferences, modifier = Modifier.weight(1f)) { Text("References") }
                    OutlinedButton(onClick = onGoWorker, modifier = Modifier.weight(1f)) { Text("Worker") }
                }
                Button(onClick = onExport, enabled = ready, modifier = Modifier.fillMaxWidth()) {
                    Text(if (ready) "Export Final PDF" else "Resolve Checklist Before Export")
                }
            }
        }
    }
}

private data class DisplayLogEntry(
    val id: String,
    val timestamp: Long,
    val phase: String,
    val chapterName: String,
    val provider: String,
    val model: String,
    val status: String,
    val prompt: String,
    val response: String,
    val error: String,
    val durationMs: Long,
    val promptChars: Int,
    val responseChars: Int
)

@Composable
fun ThesisLogsScreen(
    logs: List<ThesisAiLogEntry>,
    chapters: List<Chapter>,
    onCopy: (String) -> Unit,
    onClear: () -> Unit
) {
    var query by rememberSaveable { mutableStateOf("") }
    var statusFilter by rememberSaveable { mutableStateOf("all") }
    var expandedId by rememberSaveable { mutableStateOf("") }
    val derivedWorkerLogs = remember(chapters) {
        chapters.mapNotNull { chapter ->
            val hasPrompt = chapter.workerPrompt.isNotBlank()
            val hasResponse = chapter.rawJson.isNotBlank()
            if (!hasPrompt && !hasResponse && chapter.lastWorkerError.isBlank() && chapter.errorMessage.isNullOrBlank()) {
                null
            } else {
                DisplayLogEntry(
                    id = "worker_${chapter.name}",
                    timestamp = listOf(chapter.syncedAt, chapter.workerPromptUpdatedAt, chapter.lastRetryAt).maxOrNull() ?: 0L,
                    phase = "vps_worker",
                    chapterName = chapter.name,
                    provider = chapter.completedByProvider.ifBlank { "worker" },
                    model = chapter.completedByModel,
                    status = when {
                        chapter.status == Chapter.ChapterStatus.SUCCESS -> "completed"
                        chapter.status == Chapter.ChapterStatus.ERROR -> "failed"
                        chapter.status == Chapter.ChapterStatus.LOADING -> "running"
                        else -> chapter.workerStatus.ifBlank { "queued" }
                    },
                    prompt = chapter.workerPrompt,
                    response = chapter.rawJson,
                    error = chapter.lastWorkerError.ifBlank { chapter.errorMessage.orEmpty() },
                    durationMs = 0L,
                    promptChars = chapter.workerPrompt.length,
                    responseChars = chapter.rawJson.length
                )
            }
        }
    }
    val allLogs = remember(logs, derivedWorkerLogs) {
        (logs.map { entry ->
            DisplayLogEntry(
                id = entry.id,
                timestamp = entry.timestamp,
                phase = entry.phase,
                chapterName = entry.chapterName,
                provider = entry.provider,
                model = entry.model,
                status = entry.status,
                prompt = entry.prompt,
                response = entry.response,
                error = entry.error,
                durationMs = entry.durationMs,
                promptChars = entry.promptChars,
                responseChars = entry.responseChars
            )
        } + derivedWorkerLogs).sortedByDescending { it.timestamp }
    }
    val filtered = remember(allLogs, query, statusFilter) {
        allLogs.filter { entry ->
            val statusMatches = statusFilter == "all" || entry.status.equals(statusFilter, ignoreCase = true)
            val queryMatches = query.isBlank() ||
                entry.chapterName.contains(query, ignoreCase = true) ||
                entry.phase.contains(query, ignoreCase = true) ||
                entry.provider.contains(query, ignoreCase = true) ||
                entry.model.contains(query, ignoreCase = true) ||
                entry.prompt.contains(query, ignoreCase = true) ||
                entry.response.contains(query, ignoreCase = true) ||
                entry.error.contains(query, ignoreCase = true)
            statusMatches && queryMatches
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        ElevatedCard(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                        Text("Thesis AI Logs", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                        Text(
                            "${filtered.size}/${allLogs.size} visible - prompts, raw responses, provider errors, and worker outputs",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    OutlinedButton(onClick = onClear, enabled = logs.isNotEmpty()) {
                        Icon(Icons.Default.Delete, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Clear")
                    }
                }

                OutlinedTextField(
                    value = query,
                    onValueChange = { query = it },
                    label = { Text("Search logs") },
                    leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )

                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    listOf("all" to "All", "completed" to "Completed", "failed" to "Failed", "running" to "Running", "queued" to "Queued").forEach { (value, label) ->
                        if (statusFilter == value) {
                            Button(onClick = { statusFilter = value }) { Text(label) }
                        } else {
                            OutlinedButton(onClick = { statusFilter = value }) { Text(label) }
                        }
                    }
                }
            }
        }

        if (filtered.isEmpty()) {
            EmptyStateCard(
                title = "No logs yet",
                subtitle = "Generate chapters or run the worker to capture prompts, responses, and provider errors."
            )
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                items(filtered, key = { it.id }) { entry ->
                    ThesisLogEntryCard(
                        entry = entry,
                        expanded = expandedId == entry.id,
                        onToggle = { expandedId = if (expandedId == entry.id) "" else entry.id },
                        onCopy = onCopy
                    )
                }
            }
        }
    }
}

@Composable
private fun ThesisLogEntryCard(
    entry: DisplayLogEntry,
    expanded: Boolean,
    onToggle: () -> Unit,
    onCopy: (String) -> Unit
) {
    val statusColor = when (entry.status.lowercase()) {
        "completed", "success", "synced" -> Color(0xFF2E7D32)
        "failed", "error" -> Color(0xFFC62828)
        "running" -> Color(0xFFF57C00)
        else -> Color(0xFF546E7A)
    }
    val dateText = if (entry.timestamp > 0L) {
        java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss", java.util.Locale.getDefault())
            .format(java.util.Date(entry.timestamp))
    } else {
        "No timestamp"
    }
    ElevatedCard(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Top
            ) {
                Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                    Text(
                        entry.chapterName.ifBlank { entry.phase.ifBlank { "AI request" } },
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        "$dateText - ${entry.provider.ifBlank { "provider?" }}${entry.model.takeIf { it.isNotBlank() }?.let { " / $it" }.orEmpty()}",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Text(
                        "Phase: ${entry.phase.ifBlank { "-" }} - Prompt ${entry.promptChars} chars - Response ${entry.responseChars} chars${entry.durationMs.takeIf { it > 0 }?.let { " - ${it}ms" }.orEmpty()}",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                Surface(color = statusColor.copy(alpha = 0.12f), contentColor = statusColor, shape = RoundedCornerShape(6.dp)) {
                    Text(
                        entry.status.ifBlank { "logged" },
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.Bold
                    )
                }
            }

            if (entry.error.isNotBlank()) {
                Text(entry.error.take(600), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
            }

            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = onToggle, modifier = Modifier.weight(1f)) {
                    Text(if (expanded) "Hide Details" else "Show Prompt/Response")
                }
                OutlinedButton(
                    onClick = {
                        onCopy(
                            buildString {
                                appendLine("Phase: ${entry.phase}")
                                appendLine("Chapter: ${entry.chapterName}")
                                appendLine("Provider: ${entry.provider}/${entry.model}")
                                appendLine("Status: ${entry.status}")
                                appendLine()
                                appendLine("PROMPT")
                                appendLine(entry.prompt)
                                appendLine()
                                appendLine("RESPONSE")
                                appendLine(entry.response)
                                if (entry.error.isNotBlank()) {
                                    appendLine()
                                    appendLine("ERROR")
                                    appendLine(entry.error)
                                }
                            }
                        )
                    },
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Copy Log")
                }
            }

            if (expanded) {
                LogTextBlock("Prompt", entry.prompt.ifBlank { "No prompt recorded." })
                LogTextBlock("Response", entry.response.ifBlank { "No response recorded." })
                if (entry.error.isNotBlank()) {
                    LogTextBlock("Error", entry.error)
                }
            }
        }
    }
}

@Composable
private fun LogTextBlock(title: String, text: String) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(title, style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.Bold)
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 120.dp, max = 360.dp)
                .horizontalScroll(rememberScrollState())
                .verticalScroll(rememberScrollState())
                .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.45f), RoundedCornerShape(6.dp))
                .padding(10.dp)
        ) {
            Text(
                text = text,
                style = MaterialTheme.typography.bodySmall.copy(fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace),
                color = MaterialTheme.colorScheme.onSurface
            )
        }
    }
}

@Composable
fun WorkerActivityScreen(
    uiState: ThesisViewModel.UiState,
    viewModel: ThesisViewModel,
    onSelectTab: (Int) -> Unit
) {
    var dashboardExpanded by remember { mutableStateOf(true) }
    val scrollState = rememberScrollState()

    val pendingCount = uiState.chapters.count { it.status == Chapter.ChapterStatus.PENDING || it.status == Chapter.ChapterStatus.IDLE }
    val runningCount = uiState.chapters.count { it.status == Chapter.ChapterStatus.LOADING }
    val successCount = uiState.chapters.count { it.status == Chapter.ChapterStatus.SUCCESS }
    val errorCount = uiState.chapters.count { it.status == Chapter.ChapterStatus.ERROR }
    val syncedCount = uiState.chapters.count { it.workerStatus == "synced" }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(scrollState)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        ElevatedCard(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "VPS Worker Dashboard",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                    TextButton(onClick = { dashboardExpanded = !dashboardExpanded }) {
                        Text(if (dashboardExpanded) "Hide" else "Show")
                    }
                }

                if (dashboardExpanded) {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text("Session ID: ${uiState.sessionId}", style = MaterialTheme.typography.bodySmall)
                    Text(
                        text = "Last Sync: " + if (uiState.lastWorkerSyncTime > 0) {
                            java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss", java.util.Locale.getDefault())
                                .format(java.util.Date(uiState.lastWorkerSyncTime))
                        } else {
                            "Never"
                        },
                        style = MaterialTheme.typography.bodySmall
                    )
                    Spacer(modifier = Modifier.height(12.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        StatChip(label = "Queued", count = pendingCount, color = Color.Gray, modifier = Modifier.weight(1f))
                        StatChip(label = "Running", count = runningCount, color = Color(0xFFF57C00), modifier = Modifier.weight(1f))
                        StatChip(label = "Synced", count = syncedCount, color = Color(0xFF2E7D32), modifier = Modifier.weight(1f))
                        StatChip(label = "Failed", count = errorCount, color = Color(0xFFD32F2F), modifier = Modifier.weight(1f))
                    }
                }
            }
        }

        ElevatedCard(modifier = Modifier.fillMaxWidth()) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Text(
                    text = "Sync & Connection Controls",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold
                )

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text("Auto-Sync", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
                        Text(
                            "Automatically save local progress and listen for remote changes.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    Switch(
                        checked = uiState.autoSyncEnabled,
                        onCheckedChange = { viewModel.setAutoSyncEnabled(it) }
                    )
                }

                HorizontalDivider()

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Button(
                        onClick = { viewModel.refreshFromWorker() },
                        modifier = Modifier.weight(1f)
                    ) {
                        Text("Pull Changes", fontSize = 12.sp)
                    }
                    Button(
                        onClick = { viewModel.pushLocalChanges() },
                        modifier = Modifier.weight(1f)
                    ) {
                        Text("Push Changes", fontSize = 12.sp)
                    }
                }
            }
        }

        ElevatedCard(modifier = Modifier.fillMaxWidth()) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Text(
                    text = "Prompt Size Control",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold
                )
                ExportSwitchRow(
                    title = "Section-sized generation",
                    subtitle = "Compact large prompt blocks and ask the worker to generate mergeable section output.",
                    checked = uiState.promptSectionSplittingEnabled,
                    onCheckedChange = { viewModel.setPromptSectionSplittingEnabled(it) }
                )
                ExportOptionGroup(
                    title = "Prompt budget",
                    selected = uiState.promptMaxChars.toString(),
                    options = listOf("8000" to "8k", "12000" to "12k", "18000" to "18k", "24000" to "24k"),
                    onSelected = { value -> viewModel.setPromptMaxChars(value.toIntOrNull() ?: 12000) }
                )
                Text(
                    "Current queued worker prompts are refreshed when this setting changes.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }

        ElevatedCard(modifier = Modifier.fillMaxWidth()) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Text(
                    text = "Bulk Action Worker Retries",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Button(
                        onClick = { viewModel.retryAllFailed() },
                        modifier = Modifier.weight(1f)
                    ) {
                        Text("Retry Failed", fontSize = 11.sp)
                    }
                    Button(
                        onClick = { viewModel.retryAllIncomplete() },
                        modifier = Modifier.weight(1f)
                    ) {
                        Text("Retry Incomplete", fontSize = 11.sp)
                    }
                }
            }
        }

        Text(
            text = "Chapter Generation Timeline",
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(top = 8.dp)
        )

        uiState.chapters.forEachIndexed { index, chapter ->
            TimelineItem(
                index = index,
                chapter = chapter,
                onRetryWithAnotherProvider = {
                    viewModel.setProvider("auto")
                    viewModel.retryChapter(
                        chapter,
                        "Retry this chapter with a different available provider. Keep the existing schema, use section-sized output, and avoid repeating provider errors."
                    )
                }
            )
        }
    }
}

@Composable
fun StatChip(label: String, count: Int, color: Color, modifier: Modifier = Modifier) {
    Surface(
        color = color.copy(alpha = 0.12f),
        contentColor = color,
        shape = RoundedCornerShape(6.dp),
        modifier = modifier
    ) {
        Column(
            modifier = Modifier.padding(8.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(text = count.toString(), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Text(text = label, style = MaterialTheme.typography.labelSmall, maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
    }
}

@Composable
fun TimelineItem(
    index: Int,
    chapter: Chapter,
    onRetryWithAnotherProvider: (() -> Unit)? = null
) {
    val (statusLabel, statusColor) = when {
        chapter.status == Chapter.ChapterStatus.LOADING -> "Running" to Color(0xFFF57C00)
        chapter.workerStatus == "synced" -> "Synced" to Color(0xFF2E7D32)
        chapter.status == Chapter.ChapterStatus.SUCCESS -> "Success" to Color(0xFF2E7D32)
        chapter.status == Chapter.ChapterStatus.ERROR -> "Failed" to Color(0xFFD32F2F)
        chapter.retryCount > 0 -> "Retrying" to Color(0xFF1976D2)
        else -> "Queued" to Color.Gray
    }
    val lastAudit = chapter.auditTrail.maxByOrNull { it.timestamp }
    val providerUsed = chapter.completedByProvider.ifBlank { lastAudit?.provider.orEmpty() }.ifBlank { "auto" }
    val modelUsed = chapter.completedByModel.ifBlank { lastAudit?.model.orEmpty() }
    val realError = chapter.lastWorkerError.ifBlank { chapter.errorMessage.orEmpty() }

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.width(32.dp)
        ) {
            Surface(
                color = statusColor,
                contentColor = Color.White,
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier.size(24.dp)
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Text((index + 1).toString(), style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Bold)
                }
            }
            Spacer(modifier = Modifier.height(4.dp))
            Box(
                modifier = Modifier
                    .width(2.dp)
                    .height(36.dp)
                    .background(Color.LightGray)
            )
        }

        Card(
            modifier = Modifier.weight(1f)
        ) {
            Column(modifier = Modifier.padding(10.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(text = chapter.name, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Bold)
                    Surface(
                        color = statusColor.copy(alpha = 0.15f),
                        contentColor = statusColor,
                        shape = RoundedCornerShape(4.dp)
                    ) {
                        Text(
                            text = statusLabel,
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                        )
                    }
                }

                Text(
                    text = "Worker: ${chapter.workerStatus.ifBlank { statusLabel.lowercase() }}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                Text(
                    text = "Provider: $providerUsed${modelUsed.takeIf { it.isNotBlank() }?.let { " / $it" }.orEmpty()}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                Text(
                    text = "Retries: ${chapter.retryCount}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                if (chapter.syncedAt > 0L) {
                    val dateStr = java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss", java.util.Locale.getDefault())
                        .format(java.util.Date(chapter.syncedAt))
                    Text(
                        text = "Synced: $dateStr",
                        style = MaterialTheme.typography.labelSmall,
                        color = Color.Gray
                    )
                }

                if (realError.isNotBlank() && chapter.status == Chapter.ChapterStatus.ERROR) {
                    Text(
                        text = realError,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.error
                    )
                }

                if (chapter.status == Chapter.ChapterStatus.ERROR && onRetryWithAnotherProvider != null) {
                    OutlinedButton(onClick = onRetryWithAnotherProvider, modifier = Modifier.fillMaxWidth()) {
                        Text("Retry with another provider")
                    }
                }
            }
        }
    }
}

@Composable
fun ShowDiffDialog(
    chapterName: String,
    oldText: String,
    newText: String,
    onDismiss: () -> Unit
) {
    val oldLines = oldText.lines()
    val newLines = newText.lines()
    val diff = remember(oldText, newText) { diffLines(oldLines, newLines) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Compare Diff - $chapterName") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    text = "Legend: Green (+) = Added, Red (-) = Deleted, White/Gray = Unchanged",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                HorizontalDivider()
                LazyColumn(
                    modifier = Modifier
                        .height(400.dp)
                        .fillMaxWidth()
                        .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.2f))
                        .padding(8.dp)
                ) {
                    items(diff) { line ->
                        val (bgColor, textColor, prefix) = when (line.type) {
                            DiffType.ADDED -> Triple(
                                Color(0xFFE8F5E9),
                                Color(0xFF2E7D32),
                                "+ "
                            )
                            DiffType.DELETED -> Triple(
                                Color(0xFFFFEBEE),
                                Color(0xFFC62828),
                                "- "
                            )
                            DiffType.UNCHANGED -> Triple(
                                Color.Transparent,
                                MaterialTheme.colorScheme.onSurface,
                                "  "
                            )
                        }

                        Surface(
                            color = bgColor,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(
                                text = "$prefix${line.text}",
                                style = androidx.compose.ui.text.TextStyle(
                                    fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace,
                                    fontSize = 12.sp,
                                    color = textColor
                                ),
                                modifier = Modifier.padding(horizontal = 4.dp, vertical = 2.dp)
                            )
                        }
                    }
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) { Text("Dismiss") }
        }
    )
}

enum class DiffType {
    ADDED, DELETED, UNCHANGED
}

data class DiffLine(
    val type: DiffType,
    val text: String
)

fun diffLines(oldLines: List<String>, newLines: List<String>): List<DiffLine> {
    val m = oldLines.size
    val n = newLines.size
    val dp = Array(m + 1) { IntArray(n + 1) }

    for (i in 1..m) {
        for (j in 1..n) {
            if (oldLines[i - 1] == newLines[j - 1]) {
                dp[i][j] = dp[i - 1][j - 1] + 1
            } else {
                dp[i][j] = maxOf(dp[i - 1][j], dp[i][j - 1])
            }
        }
    }

    val diff = mutableListOf<DiffLine>()
    var i = m
    var j = n

    while (i > 0 || j > 0) {
        if (i > 0 && j > 0 && oldLines[i - 1] == newLines[j - 1]) {
            diff.add(0, DiffLine(DiffType.UNCHANGED, oldLines[i - 1]))
            i--
            j--
        } else if (j > 0 && (i == 0 || dp[i][j - 1] >= dp[i - 1][j])) {
            diff.add(0, DiffLine(DiffType.ADDED, newLines[j - 1]))
            j--
        } else {
            diff.add(0, DiffLine(DiffType.DELETED, oldLines[i - 1]))
            i--
        }
    }
    return diff
}

@Composable
fun ChapterGridCard(
    chapter: Chapter,
    onOpenReader: () -> Unit,
    viewModel: ThesisViewModel
) {
    val statusColor = when (chapter.status) {
        Chapter.ChapterStatus.SUCCESS -> Color(0xFF10B981) // Green
        Chapter.ChapterStatus.ERROR -> Color(0xFFEF4444) // Red
        Chapter.ChapterStatus.LOADING -> Color(0xFF3B82F6) // Blue
        else -> Color(0xFF6B7280) // Grey
    }

    val statusText = when (chapter.status) {
        Chapter.ChapterStatus.SUCCESS -> "Done"
        Chapter.ChapterStatus.ERROR -> "Error"
        Chapter.ChapterStatus.LOADING -> "Writing..."
        else -> "Pending"
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 142.dp, max = 190.dp)
            .clickable(enabled = chapter.status == Chapter.ChapterStatus.SUCCESS) { onOpenReader() }
            .border(
                width = 1.5.dp,
                color = statusColor.copy(alpha = 0.6f),
                shape = MaterialTheme.shapes.medium
            ),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier
                .padding(12.dp)
                .fillMaxSize(),
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(
                    text = chapter.name,
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold),
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Row(
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Box(
                        modifier = Modifier
                            .size(8.dp)
                            .clip(RoundedCornerShape(4.dp))
                            .background(statusColor)
                    )
                    Text(
                        text = statusText,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                if (chapter.chapterReferences.isNotEmpty()) {
                    Text(
                        text = "${chapter.chapterReferences.size} refs",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                } else {
                    Spacer(modifier = Modifier.size(1.dp))
                }

                if (chapter.status == Chapter.ChapterStatus.SUCCESS) {
                    Text(
                        text = "Read ➔",
                        style = MaterialTheme.typography.labelLarge.copy(
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary
                        )
                    )
                } else if (chapter.status == Chapter.ChapterStatus.LOADING) {
                    CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                }
            }
        }
    }
}

@Composable
fun TabActionsBar(
    selectedTab: Int,
    isGridViewEnabled: Boolean,
    onToggleGridView: () -> Unit,
    expandAllContents: Boolean,
    onToggleExpandAll: () -> Unit,
    uiState: ThesisViewModel.UiState,
    viewModel: ThesisViewModel
) {
    if (selectedTab != 2 && selectedTab != 3 && selectedTab != 4 && selectedTab != 5 && selectedTab != 7) {
        return
    }

    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(8.dp),
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                if (selectedTab == 2) {
                    OutlinedButton(
                        onClick = onToggleGridView,
                        modifier = Modifier.height(36.dp),
                        contentPadding = PaddingValues(horizontal = 12.dp)
                    ) {
                        Icon(
                            imageVector = if (isGridViewEnabled) Icons.Default.Menu else Icons.Default.ViewModule,
                            contentDescription = null,
                            modifier = Modifier.size(16.dp)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = if (isGridViewEnabled) "List View" else "Grid View",
                            fontSize = 12.sp
                        )
                    }

                    OutlinedButton(
                        onClick = onToggleExpandAll,
                        modifier = Modifier.height(36.dp),
                        contentPadding = PaddingValues(horizontal = 12.dp)
                    ) {
                        Text(
                            text = if (expandAllContents) "Collapse All" else "Expand All",
                            fontSize = 12.sp
                        )
                    }
                } else if (selectedTab == 3) {
                    Text(
                        text = "Tables Overview",
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                } else if (selectedTab == 4) {
                    Text(
                        text = "Figures Management",
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                } else if (selectedTab == 5) {
                    Text(
                        text = "Charts Visualizer",
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                } else if (selectedTab == 7) {
                    Text(
                        text = "References Verification",
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            if (selectedTab == 7 || selectedTab == 2) {
                OutlinedButton(
                    onClick = { viewModel.syncVerifiedReferenceCacheNow() },
                    modifier = Modifier.height(36.dp),
                    contentPadding = PaddingValues(horizontal = 12.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.History,
                        contentDescription = null,
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Sync References", fontSize = 12.sp)
                }
            }
        }
    }
}

@Composable
fun BrilliantChapterReaderDialog(
    chapter: Chapter,
    viewModel: ThesisViewModel,
    onDismiss: () -> Unit,
    onCopy: (String) -> Unit,
    onRetry: (Chapter, String?) -> Unit,
    onShowFigures: () -> Unit,
    onShowTables: () -> Unit,
    onShowCharts: () -> Unit
) {
    var readerFontSize by remember { mutableStateOf(16f) }
    var readerLineHeight by remember { mutableStateOf(24f) }
    var isSerifFont by remember { mutableStateOf(true) }
    var readerTheme by remember { mutableStateOf("Sepia") }
    var searchQuery by remember { mutableStateOf("") }
    var selectedSideTab by remember { mutableStateOf(0) }
    var aiCustomPrompt by remember { mutableStateOf("") }

    val textColor = when (readerTheme) {
        "Sepia" -> Color(0xFF5B4636)
        "Dark" -> Color(0xFFE0E0E6)
        else -> Color(0xFF1F2937)
    }
    val dividerColor = when (readerTheme) {
        "Sepia" -> Color(0xFFE4DCC8)
        "Dark" -> Color(0xFF2C2C30)
        else -> Color(0xFFE5E7EB)
    }

    Dialog(
        onDismissRequest = onDismiss,
        properties = androidx.compose.ui.window.DialogProperties(
            usePlatformDefaultWidth = false
        )
    ) {
        Surface(
            modifier = Modifier.fillMaxSize(),
            color = when (readerTheme) {
                "Sepia" -> Color(0xFFF4ECD8)
                "Dark" -> Color(0xFF121214)
                else -> Color(0xFFFFFFFF)
            },
            contentColor = textColor
        ) {
            BoxWithConstraints(modifier = Modifier.fillMaxSize()) {
                val isWideScreen = maxWidth > 600.dp

                Column(modifier = Modifier.fillMaxSize()) {
                    ReaderHeader(
                        chapterName = chapter.name,
                        readerTheme = readerTheme,
                        onDismiss = onDismiss,
                        onCopy = { onCopy(chapterTextWithoutReferenceBlock(chapter.content)) },
                        onToggleTheme = {
                            readerTheme = when (readerTheme) {
                                "Light" -> "Sepia"
                                "Sepia" -> "Dark"
                                else -> "Light"
                            }
                        },
                        isSerifFont = isSerifFont,
                        onToggleFontFamily = { isSerifFont = !isSerifFont },
                        readerFontSize = readerFontSize,
                        onFontSizeChange = { readerFontSize = it }
                    )

                    val dividerColor = when (readerTheme) {
                        "Sepia" -> Color(0xFFE4DCC8)
                        "Dark" -> Color(0xFF2C2C30)
                        else -> Color(0xFFE5E7EB)
                    }

                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(1.dp)
                            .background(dividerColor)
                    )

                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .weight(1f)
                    ) {
                        Box(
                            modifier = Modifier
                                .weight(if (isWideScreen) 1.6f else 1.0f)
                                .fillMaxHeight()
                        ) {
                            ChapterReadingLayout(
                                content = chapterTextWithoutReferenceBlock(chapter.content),
                                fontSize = readerFontSize,
                                lineHeight = readerLineHeight,
                                isSerifFont = isSerifFont,
                                readerTheme = readerTheme,
                                searchQuery = searchQuery,
                                onSearchQueryChange = { searchQuery = it }
                            )
                        }

                        if (isWideScreen) {
                            Box(
                                modifier = Modifier
                                    .fillMaxHeight()
                                    .width(1.dp)
                                    .background(dividerColor)
                            )
                            Box(
                                modifier = Modifier
                                    .weight(1.0f)
                                    .fillMaxHeight()
                                    .background(
                                        color = when (readerTheme) {
                                            "Sepia" -> Color(0xFFECE4CE)
                                            "Dark" -> Color(0xFF1E1E22)
                                            else -> Color(0xFFF3F4F6)
                                        }
                                    )
                            ) {
                                ChapterSidePanel(
                                    chapter = chapter,
                                    selectedTab = selectedSideTab,
                                    onSelectTab = { selectedSideTab = it },
                                    readerTheme = readerTheme,
                                    aiCustomPrompt = aiCustomPrompt,
                                    onAiCustomPromptChange = { aiCustomPrompt = it },
                                    onRetry = { onRetry(chapter, it) },
                                    onShowFigures = onShowFigures,
                                    onShowTables = onShowTables,
                                    onShowCharts = onShowCharts
                                )
                            }
                        }
                    }
                }

                if (!isWideScreen) {
                    var showOverlayPanel by remember { mutableStateOf(false) }
                    Box(
                        modifier = Modifier
                            .align(Alignment.BottomEnd)
                            .padding(16.dp)
                    ) {
                        FloatingActionButton(
                            onClick = { showOverlayPanel = true },
                            containerColor = MaterialTheme.colorScheme.primary,
                            contentColor = MaterialTheme.colorScheme.onPrimary
                        ) {
                            Icon(Icons.Default.Menu, contentDescription = "Chapter Outline & Assets")
                        }
                    }

                    if (showOverlayPanel) {
                        Dialog(onDismissRequest = { showOverlayPanel = false }) {
                            Surface(
                                modifier = Modifier
                                    .fillMaxWidth(0.95f)
                                    .fillMaxHeight(0.85f),
                                shape = RoundedCornerShape(16.dp),
                                color = when (readerTheme) {
                                    "Sepia" -> Color(0xFFECE4CE)
                                    "Dark" -> Color(0xFF1E1E22)
                                    else -> Color(0xFFF3F4F6)
                                }
                            ) {
                                Column {
                                    Row(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .padding(12.dp),
                                        horizontalArrangement = Arrangement.SpaceBetween,
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Text(
                                            text = "Chapter Details",
                                            style = MaterialTheme.typography.titleMedium,
                                            fontWeight = FontWeight.Bold,
                                            color = textColor
                                        )
                                        IconButton(onClick = { showOverlayPanel = false }) {
                                            Icon(Icons.Default.Close, contentDescription = "Close", tint = textColor)
                                        }
                                    }
                                    Box(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .height(1.dp)
                                            .background(dividerColor)
                                    )
                                    Box(modifier = Modifier.weight(1f)) {
                                        ChapterSidePanel(
                                            chapter = chapter,
                                            selectedTab = selectedSideTab,
                                            onSelectTab = { selectedSideTab = it },
                                            readerTheme = readerTheme,
                                            aiCustomPrompt = aiCustomPrompt,
                                            onAiCustomPromptChange = { aiCustomPrompt = it },
                                            onRetry = { onRetry(chapter, it); showOverlayPanel = false },
                                            onShowFigures = onShowFigures,
                                            onShowTables = onShowTables,
                                            onShowCharts = onShowCharts
                                        )
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

@Composable
fun ReaderHeader(
    chapterName: String,
    readerTheme: String,
    onDismiss: () -> Unit,
    onCopy: () -> Unit,
    onToggleTheme: () -> Unit,
    isSerifFont: Boolean,
    onToggleFontFamily: () -> Unit,
    readerFontSize: Float,
    onFontSizeChange: (Float) -> Unit
) {
    val headerBg = when (readerTheme) {
        "Sepia" -> Color(0xFFE4DCC8)
        "Dark" -> Color(0xFF1E1E22)
        else -> Color(0xFFF3F4F6)
    }
    val textColor = when (readerTheme) {
        "Sepia" -> Color(0xFF5B4636)
        "Dark" -> Color(0xFFE0E0E6)
        else -> Color(0xFF1F2937)
    }

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(headerBg)
            .padding(horizontal = 16.dp, vertical = 10.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            IconButton(onClick = onDismiss) {
                Icon(Icons.Default.Close, contentDescription = "Close Reader", tint = textColor)
            }
            Column {
                Text(
                    text = chapterName,
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                    color = textColor
                )
                Text(
                    text = "Academic Reading Mode",
                    style = MaterialTheme.typography.labelSmall,
                    color = textColor.copy(alpha = 0.7f)
                )
            }
        }

        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            IconButton(onClick = { onFontSizeChange((readerFontSize - 2f).coerceAtLeast(12f)) }) {
                Icon(Icons.Default.ZoomOut, contentDescription = "Decrease Font Size", tint = textColor)
            }
            Text(
                text = "${readerFontSize.toInt()}sp",
                style = MaterialTheme.typography.labelMedium,
                color = textColor
            )
            IconButton(onClick = { onFontSizeChange((readerFontSize + 2f).coerceIn(12f, 28f)) }) {
                Icon(Icons.Default.ZoomIn, contentDescription = "Increase Font Size", tint = textColor)
            }

            IconButton(onClick = onToggleFontFamily) {
                Icon(Icons.Default.FormatSize, contentDescription = "Font Style", tint = textColor)
            }

            IconButton(onClick = onToggleTheme) {
                Icon(
                    imageVector = when (readerTheme) {
                        "Sepia" -> Icons.Default.DarkMode
                        "Dark" -> Icons.Default.LightMode
                        else -> Icons.Default.Settings
                    },
                    contentDescription = "Switch Theme",
                    tint = textColor
                )
            }

            IconButton(onClick = onCopy) {
                Icon(Icons.Default.Save, contentDescription = "Copy content", tint = textColor)
            }
        }
    }
}

@Composable
fun ChapterReadingLayout(
    content: String,
    fontSize: Float,
    lineHeight: Float,
    isSerifFont: Boolean,
    readerTheme: String,
    searchQuery: String,
    onSearchQueryChange: (String) -> Unit
) {
    val blocks = remember(content) {
        content
            .split(Regex("\\n{2,}"))
            .map { it.trim() }
            .filter { it.isNotBlank() }
    }

    val fontFamily = if (isSerifFont) androidx.compose.ui.text.font.FontFamily.Serif else androidx.compose.ui.text.font.FontFamily.SansSerif
    val textColor = when (readerTheme) {
        "Sepia" -> Color(0xFF5B4636)
        "Dark" -> Color(0xFFE0E0E6)
        else -> Color(0xFF1F2937)
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 24.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        OutlinedTextField(
            value = searchQuery,
            onValueChange = onSearchQueryChange,
            label = { Text("Search and highlight in chapter") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
            trailingIcon = if (searchQuery.isNotEmpty()) {
                {
                    IconButton(onClick = { onSearchQueryChange("") }) {
                        Icon(Icons.Default.Close, contentDescription = "Clear search")
                    }
                }
            } else null
        )

        LazyColumn(
            modifier = Modifier.weight(1f).fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            items(blocks) { block ->
                val singleLine = !block.contains('\n')
                val headingLike = singleLine &&
                    block.length <= 80 &&
                    (
                        block == block.uppercase() ||
                            block.endsWith(":") ||
                            block.matches(Regex("""\d+(\.\d+)*\s+.+"""))
                        )

                if (headingLike) {
                    Text(
                        text = block.trimEnd(':'),
                        style = MaterialTheme.typography.titleLarge.copy(
                            fontSize = (fontSize + 4f).sp,
                            fontWeight = FontWeight.Bold,
                            fontFamily = fontFamily
                        ),
                        color = textColor
                    )
                } else {
                    val annotatedText = if (searchQuery.isNotBlank() && block.contains(searchQuery, ignoreCase = true)) {
                        buildHighlightedText(block, searchQuery)
                    } else {
                        boldMarkdownAnnotatedText(block)
                    }

                    Text(
                        text = annotatedText,
                        style = MaterialTheme.typography.bodyLarge.copy(
                            fontSize = fontSize.sp,
                            lineHeight = (fontSize * 1.5f).sp,
                            fontFamily = fontFamily
                        ),
                        color = textColor
                    )
                }
            }
        }
    }
}

private fun buildHighlightedText(text: String, query: String): AnnotatedString {
    val annotatedString = buildAnnotatedString {
        var start = 0
        while (start < text.length) {
            val index = text.indexOf(query, start, ignoreCase = true)
            if (index == -1) {
                append(text.substring(start))
                break
            }
            append(text.substring(start, index))
            pushStyle(SpanStyle(background = Color.Yellow, color = Color.Black, fontWeight = FontWeight.Bold))
            append(text.substring(index, index + query.length))
            pop()
            start = index + query.length
        }
    }
    return annotatedString
}

@Composable
fun ChapterSidePanel(
    chapter: Chapter,
    selectedTab: Int,
    onSelectTab: (Int) -> Unit,
    readerTheme: String,
    aiCustomPrompt: String,
    onAiCustomPromptChange: (String) -> Unit,
    onRetry: (String) -> Unit,
    onShowFigures: () -> Unit,
    onShowTables: () -> Unit,
    onShowCharts: () -> Unit
) {
    val sidebarBg = when (readerTheme) {
        "Sepia" -> Color(0xFFECE4CE)
        "Dark" -> Color(0xFF1E1E22)
        else -> Color(0xFFF3F4F6)
    }
    val textColor = when (readerTheme) {
        "Sepia" -> Color(0xFF5B4636)
        "Dark" -> Color(0xFFE0E0E6)
        else -> Color(0xFF1F2937)
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(sidebarBg)
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        PrimaryScrollableTabRow(
            selectedTabIndex = selectedTab,
            edgePadding = 0.dp,
            containerColor = Color.Transparent,
            contentColor = textColor
        ) {
            Tab(selected = selectedTab == 0, onClick = { onSelectTab(0) }) {
                Text("Outline", modifier = Modifier.padding(vertical = 10.dp), fontSize = 12.sp, color = textColor)
            }
            Tab(selected = selectedTab == 1, onClick = { onSelectTab(1) }) {
                Text("Assets (${chapter.figures.size + chapter.tables.size + chapter.charts.size})", modifier = Modifier.padding(vertical = 10.dp), fontSize = 12.sp, color = textColor)
            }
            Tab(selected = selectedTab == 2, onClick = { onSelectTab(2) }) {
                Text("AI Editor", modifier = Modifier.padding(vertical = 10.dp), fontSize = 12.sp, color = textColor)
            }
        }

        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(1.dp)
                .background(textColor.copy(alpha = 0.15f))
        )

        Box(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f)
        ) {
            when (selectedTab) {
                0 -> {
                    val outlineItems = remember(chapter.content) {
                        chapter.content.lines()
                            .map { it.trim() }
                            .filter { line ->
                                line.length in 5..80 && (
                                    line.matches(Regex("""^(?:[IXV]+|\d+(?:\.\d+)*)\.?\s+[A-Z].*""")) ||
                                    (line == line.uppercase() && !line.startsWith(" ") && line.length > 5 && !line.contains(Regex("""\d""")))
                                )
                            }
                    }
                    if (outlineItems.isEmpty()) {
                        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                            Text("No outline items detected.", style = MaterialTheme.typography.bodySmall, color = textColor.copy(alpha = 0.7f))
                        }
                    } else {
                        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            items(outlineItems) { item ->
                                Card(
                                    modifier = Modifier.fillMaxWidth(),
                                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.5f))
                                ) {
                                    Text(
                                        text = item,
                                        style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Medium),
                                        modifier = Modifier.padding(10.dp),
                                        color = textColor
                                    )
                                }
                            }
                        }
                    }
                }

                1 -> {
                    LazyColumn(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        if (chapter.figures.isNotEmpty()) {
                            item {
                                Text("📷 Figures (${chapter.figures.size})", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold, color = textColor)
                            }
                            items(chapter.figures) { figure ->
                                RenderFigure(figure)
                            }
                        }
                        if (chapter.tables.isNotEmpty()) {
                            item {
                                Spacer(modifier = Modifier.height(6.dp))
                                Text("📋 Tables (${chapter.tables.size})", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold, color = textColor)
                            }
                            items(chapter.tables) { table ->
                                RenderTable(table)
                            }
                        }
                        if (chapter.charts.isNotEmpty()) {
                            item {
                                Spacer(modifier = Modifier.height(6.dp))
                                Text("📈 Charts (${chapter.charts.size})", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold, color = textColor)
                            }
                            items(chapter.charts) { chart ->
                                RenderChart(chart)
                            }
                        }
                        if (chapter.figures.isEmpty() && chapter.tables.isEmpty() && chapter.charts.isEmpty()) {
                            item {
                                Box(modifier = Modifier.fillParentMaxSize(), contentAlignment = Alignment.Center) {
                                    Text("No assets attached to this chapter.", style = MaterialTheme.typography.bodySmall, color = textColor.copy(alpha = 0.7f))
                                }
                            }
                        }
                    }
                }

                2 -> {
                    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Text(
                            text = "Instruct the AI to rewrite or adjust this chapter:",
                            style = MaterialTheme.typography.bodySmall,
                            color = textColor
                        )
                        OutlinedTextField(
                            value = aiCustomPrompt,
                            onValueChange = onAiCustomPromptChange,
                            label = { Text("E.g. Make the discussion more critical, format citations...") },
                            modifier = Modifier.fillMaxWidth(),
                            minLines = 4,
                            maxLines = 8
                        )
                        Button(
                            onClick = { onRetry(aiCustomPrompt) },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text("Refine Chapter with AI")
                        }
                    }
                }
            }
        }
    }
}
