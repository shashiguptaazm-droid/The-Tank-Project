package com.rankwarz.edulabsrtm.viewmodel

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.net.Uri
import android.provider.OpenableColumns
import android.util.Log
import android.view.View
import android.view.ViewGroup
import android.graphics.Color
import android.widget.FrameLayout
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.github.mikephil.charting.charts.BarChart
import com.github.mikephil.charting.charts.HorizontalBarChart
import com.github.mikephil.charting.charts.LineChart
import com.github.mikephil.charting.charts.PieChart
import com.github.mikephil.charting.charts.ScatterChart
import com.github.mikephil.charting.components.XAxis
import com.github.mikephil.charting.data.Entry
import com.github.mikephil.charting.data.BarData
import com.github.mikephil.charting.data.BarDataSet
import com.github.mikephil.charting.data.BarEntry
import com.github.mikephil.charting.data.LineData
import com.github.mikephil.charting.data.LineDataSet
import com.github.mikephil.charting.data.PieData as MPPieData
import com.github.mikephil.charting.data.PieDataSet
import com.github.mikephil.charting.data.PieEntry
import com.github.mikephil.charting.data.ScatterData
import com.github.mikephil.charting.data.ScatterDataSet
import com.github.mikephil.charting.formatter.IndexAxisValueFormatter
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.database.DataSnapshot
import com.google.firebase.database.DatabaseError
import com.google.firebase.database.DatabaseReference
import com.google.firebase.database.FirebaseDatabase
import com.google.firebase.database.ValueEventListener
import com.google.gson.Gson
import com.google.gson.JsonArray
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import com.google.gson.annotations.SerializedName
import com.rankwarz.edulabsrtm.ThesisAnalyzerActivity
import com.rankwarz.edulabsrtm.AiTrainingLogger
import com.rankwarz.edulabsrtm.ApiKeys
import com.rankwarz.edulabsrtm.EduLabsApplication
import com.rankwarz.edulabsrtm.R
import com.rankwarz.edulabsrtm.ThesisBackgroundService
import com.rankwarz.edulabsrtm.RemoteThemeLayout
import com.rankwarz.edulabsrtm.util.AiDocumentOcrHelper
import com.rankwarz.edulabsrtm.enumValueOfOrNull
import com.rankwarz.edulabsrtm.getCachedRemoteThemeLayouts
import com.rankwarz.edulabsrtm.parseHexColor
import com.rankwarz.edulabsrtm.syncRemoteThemeLayouts
import com.rankwarz.edulabsrtm.data.remote.ApiClient
import com.rankwarz.edulabsrtm.data.remote.ChatRequest
import com.rankwarz.edulabsrtm.data.remote.Message
import org.json.JSONObject
import com.rankwarz.edulabsrtm.model.*
import com.rankwarz.edulabsrtm.utils.PdfTextExtractor
import com.rankwarz.edulabsrtm.utils.TextChunker
import com.tom_roush.pdfbox.pdmodel.PDDocument
import com.tom_roush.pdfbox.pdmodel.PDPage
import com.tom_roush.pdfbox.pdmodel.PDPageContentStream
import com.tom_roush.pdfbox.pdmodel.common.PDRectangle
import com.tom_roush.pdfbox.pdmodel.font.PDType1Font
import com.tom_roush.pdfbox.pdmodel.graphics.image.LosslessFactory
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.Job
import kotlinx.coroutines.isActive
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.apache.poi.ss.usermodel.DataFormatter
import org.apache.poi.ss.usermodel.WorkbookFactory
import org.apache.poi.xwpf.usermodel.ParagraphAlignment
import org.apache.poi.xwpf.usermodel.BreakType
import org.apache.poi.xwpf.usermodel.Document
import org.apache.poi.xwpf.usermodel.TextAlignment
import org.apache.poi.xwpf.usermodel.XWPFDocument
import org.apache.poi.xwpf.usermodel.XWPFParagraph
import org.apache.poi.xwpf.usermodel.XWPFTable
import org.apache.poi.xwpf.usermodel.XWPFTableCell
import org.apache.poi.xwpf.usermodel.XWPFTableRow
import org.jsoup.Jsoup
import java.io.FileOutputStream
import java.io.IOException
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.util.UUID
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.TimeUnit
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream
import kotlin.math.sqrt

data class ReferenceValidationIssue(
    val citation: String = "",
    val originalText: String = "",
    val updatedText: String = "",
    val issue: String = ""
)

data class ReferenceValidationState(
    val issues: List<ReferenceValidationIssue> = emptyList(),
    val verifiedReferences: List<ReferenceJson> = emptyList(),
    val canApply: Boolean = false
)

enum class PdfTheme(val label: String) {
    CLASSIC("Classic"),
    NAVY("Navy"),
    EMERALD("Emerald"),
    MAROON("Maroon"),
    TEAL("Teal"),
    SLATE("Slate"),
    OLIVE("Olive"),
    SAND("Sand"),
    ROYAL("Royal"),
    CRIMSON("Crimson");

    companion object {
        fun fromName(value: String): PdfTheme {
            val colorName = value.substringBefore("|").trim()
            return entries.firstOrNull { it.name.equals(colorName, ignoreCase = true) } ?: CLASSIC
        }
    }
}

data class PdfThemeStyle(
    val accentColor: Int,
    val softColor: Int,
    val headerFillColor: Int,
    val footerFillColor: Int,
    val ruleColor: Int,
    val pageChromeLayout: PageChromeLayout,
    val titlePageLayout: TitlePageLayout,
    val chapterLayout: ChapterLayout,
    val sectionLayout: SectionLayout,
    val paragraphLayout: ParagraphLayout,
    val tableLayout: TableLayout,
    val chartLayout: ChartLayout,
    val figureLayout: FigureLayout,
    val headerFooterLayout: HeaderFooterLayout,
    val specialPageLayout: SpecialPageLayout,
    val logoPosition: String = "top-right",
    val logoSize: String = "medium",
    val logoStyle: String = "rounded",
    val logoOffsetX: Int = 0,
    val logoOffsetY: Int = 0,
    val pageMargin: String = "normal",
    val fontScheme: String = "serif",
    val shadowDepth: String = "light"
)

enum class PageChromeLayout {
    FORMAL_FRAME,
    CLINICAL_REPORT,
    JOURNAL_ARTICLE,
    PREMIUM_PRESENTATION,
    OFFICIAL_BINDER,
    MINIMAL_JOURNAL,
    ACADEMIC_INSET,
    DASHBOARD_RAIL,
    DEFENSE_PRESENTATION,
    EDITORIAL_FOLIO,
    ATLAS_PLATE,
    EXECUTIVE_SUMMARY,
    MONOGRAPH_CLASSIC,
    CASEBOOK_FILE,
    LAB_NOTEBOOK,
    SYSTEMATIC_REVIEW,
    SIGNATURE_PORTFOLIO
}

enum class TitlePageLayout {
    CENTERED_UNIVERSITY,
    LOGO_TOP_OFFICIAL,
    JOURNAL_MANUSCRIPT,
    MODERN_COVER
}

enum class ChapterLayout {
    SIMPLE_TITLE,
    LEFT_RULE,
    JOURNAL_HEADING,
    FULL_WIDTH_BANNER
}

enum class SectionLayout {
    FORMAL_HEADING,
    BOXED_LABEL,
    JOURNAL_HEADING,
    DASHBOARD_BLOCK,
    EDITORIAL_MARK,
    PLATE_LABEL,
    EXECUTIVE_BAND,
    MONOGRAPH_DROP
}

enum class ParagraphLayout {
    INDENTED_ACADEMIC,
    COMPACT_REPORT,
    JOURNAL_BODY,
    SPACIOUS_READING
}

enum class TableLayout {
    FULL_GRID,
    CLINICAL_BOXED,
    JOURNAL_MINIMAL,
    DATA_DASHBOARD
}

enum class ChartLayout {
    SIMPLE_ACADEMIC,
    CLINICAL_MUTED,
    JOURNAL_CLEAN,
    PRESENTATION_BOLD
}

enum class FigureLayout {
    CENTERED_CAPTION,
    REPORT_PANEL,
    JOURNAL_FIGURE,
    PRESENTATION_IMAGE
}

enum class HeaderFooterLayout {
    PLAIN_PAGE_NUMBER,
    INSTITUTIONAL_HEADER,
    JOURNAL_STYLE,
    MODERN_BAR
}

enum class SpecialPageLayout {
    FORMAL_DOCUMENT,
    OFFICIAL_CERTIFICATE,
    CLEAN_DECLARATION,
    PREMIUM_PAGE
}

fun resolvePdfThemeStyle(theme: PdfTheme): PdfThemeStyle {
    return when (theme) {
        PdfTheme.CLASSIC -> PdfThemeStyle(
            accentColor = Color.parseColor("#1B3A57"),
            softColor = Color.parseColor("#DDEBF7"),
            headerFillColor = Color.parseColor("#BFD4EA"),
            footerFillColor = Color.parseColor("#EEF5FB"),
            ruleColor = Color.parseColor("#6E93B8"),
            pageChromeLayout = PageChromeLayout.OFFICIAL_BINDER,
            titlePageLayout = TitlePageLayout.CENTERED_UNIVERSITY,
            chapterLayout = ChapterLayout.SIMPLE_TITLE,
            sectionLayout = SectionLayout.FORMAL_HEADING,
            paragraphLayout = ParagraphLayout.INDENTED_ACADEMIC,
            tableLayout = TableLayout.FULL_GRID,
            chartLayout = ChartLayout.SIMPLE_ACADEMIC,
            figureLayout = FigureLayout.CENTERED_CAPTION,
            headerFooterLayout = HeaderFooterLayout.PLAIN_PAGE_NUMBER,
            specialPageLayout = SpecialPageLayout.FORMAL_DOCUMENT
        )
        PdfTheme.NAVY -> PdfThemeStyle(
            accentColor = Color.parseColor("#081C2E"),
            softColor = Color.parseColor("#D5DEEA"),
            headerFillColor = Color.parseColor("#B3C2D3"),
            footerFillColor = Color.parseColor("#EAF0F6"),
            ruleColor = Color.parseColor("#5F7690"),
            pageChromeLayout = PageChromeLayout.MINIMAL_JOURNAL,
            titlePageLayout = TitlePageLayout.JOURNAL_MANUSCRIPT,
            chapterLayout = ChapterLayout.JOURNAL_HEADING,
            sectionLayout = SectionLayout.JOURNAL_HEADING,
            paragraphLayout = ParagraphLayout.JOURNAL_BODY,
            tableLayout = TableLayout.JOURNAL_MINIMAL,
            chartLayout = ChartLayout.JOURNAL_CLEAN,
            figureLayout = FigureLayout.JOURNAL_FIGURE,
            headerFooterLayout = HeaderFooterLayout.JOURNAL_STYLE,
            specialPageLayout = SpecialPageLayout.CLEAN_DECLARATION
        )
        PdfTheme.EMERALD -> PdfThemeStyle(
            accentColor = Color.parseColor("#0A5C4E"),
            softColor = Color.parseColor("#D0F0E9"),
            headerFillColor = Color.parseColor("#A7E1D5"),
            footerFillColor = Color.parseColor("#ECFAF6"),
            ruleColor = Color.parseColor("#48B49E"),
            pageChromeLayout = PageChromeLayout.DASHBOARD_RAIL,
            titlePageLayout = TitlePageLayout.LOGO_TOP_OFFICIAL,
            chapterLayout = ChapterLayout.LEFT_RULE,
            sectionLayout = SectionLayout.BOXED_LABEL,
            paragraphLayout = ParagraphLayout.COMPACT_REPORT,
            tableLayout = TableLayout.CLINICAL_BOXED,
            chartLayout = ChartLayout.CLINICAL_MUTED,
            figureLayout = FigureLayout.REPORT_PANEL,
            headerFooterLayout = HeaderFooterLayout.INSTITUTIONAL_HEADER,
            specialPageLayout = SpecialPageLayout.OFFICIAL_CERTIFICATE
        )
        PdfTheme.MAROON -> PdfThemeStyle(
            accentColor = Color.parseColor("#5C1717"),
            softColor = Color.parseColor("#F4DADA"),
            headerFillColor = Color.parseColor("#EAB6B6"),
            footerFillColor = Color.parseColor("#FFF1F1"),
            ruleColor = Color.parseColor("#C46E6E"),
            pageChromeLayout = PageChromeLayout.ACADEMIC_INSET,
            titlePageLayout = TitlePageLayout.CENTERED_UNIVERSITY,
            chapterLayout = ChapterLayout.FULL_WIDTH_BANNER,
            sectionLayout = SectionLayout.FORMAL_HEADING,
            paragraphLayout = ParagraphLayout.INDENTED_ACADEMIC,
            tableLayout = TableLayout.FULL_GRID,
            chartLayout = ChartLayout.SIMPLE_ACADEMIC,
            figureLayout = FigureLayout.CENTERED_CAPTION,
            headerFooterLayout = HeaderFooterLayout.INSTITUTIONAL_HEADER,
            specialPageLayout = SpecialPageLayout.OFFICIAL_CERTIFICATE
        )
        PdfTheme.TEAL -> PdfThemeStyle(
            accentColor = Color.parseColor("#075B5B"),
            softColor = Color.parseColor("#D3F3F0"),
            headerFillColor = Color.parseColor("#A9E0DA"),
            footerFillColor = Color.parseColor("#EBFAF8"),
            ruleColor = Color.parseColor("#45AFA8"),
            pageChromeLayout = PageChromeLayout.CLINICAL_REPORT,
            titlePageLayout = TitlePageLayout.LOGO_TOP_OFFICIAL,
            chapterLayout = ChapterLayout.LEFT_RULE,
            sectionLayout = SectionLayout.DASHBOARD_BLOCK,
            paragraphLayout = ParagraphLayout.COMPACT_REPORT,
            tableLayout = TableLayout.DATA_DASHBOARD,
            chartLayout = ChartLayout.PRESENTATION_BOLD,
            figureLayout = FigureLayout.REPORT_PANEL,
            headerFooterLayout = HeaderFooterLayout.MODERN_BAR,
            specialPageLayout = SpecialPageLayout.PREMIUM_PAGE
        )
        PdfTheme.SLATE -> PdfThemeStyle(
            accentColor = Color.parseColor("#1F2A37"),
            softColor = Color.parseColor("#DDE3EA"),
            headerFillColor = Color.parseColor("#BEC9D6"),
            footerFillColor = Color.parseColor("#EEF2F7"),
            ruleColor = Color.parseColor("#6E7D90"),
            pageChromeLayout = PageChromeLayout.JOURNAL_ARTICLE,
            titlePageLayout = TitlePageLayout.JOURNAL_MANUSCRIPT,
            chapterLayout = ChapterLayout.JOURNAL_HEADING,
            sectionLayout = SectionLayout.JOURNAL_HEADING,
            paragraphLayout = ParagraphLayout.JOURNAL_BODY,
            tableLayout = TableLayout.JOURNAL_MINIMAL,
            chartLayout = ChartLayout.JOURNAL_CLEAN,
            figureLayout = FigureLayout.JOURNAL_FIGURE,
            headerFooterLayout = HeaderFooterLayout.JOURNAL_STYLE,
            specialPageLayout = SpecialPageLayout.CLEAN_DECLARATION
        )
        PdfTheme.OLIVE -> PdfThemeStyle(
            accentColor = Color.parseColor("#3E5121"),
            softColor = Color.parseColor("#E4ECD4"),
            headerFillColor = Color.parseColor("#CFDDAE"),
            footerFillColor = Color.parseColor("#F6FAEC"),
            ruleColor = Color.parseColor("#8EA35E"),
            pageChromeLayout = PageChromeLayout.FORMAL_FRAME,
            titlePageLayout = TitlePageLayout.CENTERED_UNIVERSITY,
            chapterLayout = ChapterLayout.SIMPLE_TITLE,
            sectionLayout = SectionLayout.BOXED_LABEL,
            paragraphLayout = ParagraphLayout.INDENTED_ACADEMIC,
            tableLayout = TableLayout.CLINICAL_BOXED,
            chartLayout = ChartLayout.CLINICAL_MUTED,
            figureLayout = FigureLayout.CENTERED_CAPTION,
            headerFooterLayout = HeaderFooterLayout.PLAIN_PAGE_NUMBER,
            specialPageLayout = SpecialPageLayout.FORMAL_DOCUMENT
        )
        PdfTheme.SAND -> PdfThemeStyle(
            accentColor = Color.parseColor("#6A4B22"),
            softColor = Color.parseColor("#F4E4CA"),
            headerFillColor = Color.parseColor("#E4C18D"),
            footerFillColor = Color.parseColor("#FFF7ED"),
            ruleColor = Color.parseColor("#B88449"),
            pageChromeLayout = PageChromeLayout.DEFENSE_PRESENTATION,
            titlePageLayout = TitlePageLayout.MODERN_COVER,
            chapterLayout = ChapterLayout.FULL_WIDTH_BANNER,
            sectionLayout = SectionLayout.DASHBOARD_BLOCK,
            paragraphLayout = ParagraphLayout.SPACIOUS_READING,
            tableLayout = TableLayout.DATA_DASHBOARD,
            chartLayout = ChartLayout.PRESENTATION_BOLD,
            figureLayout = FigureLayout.PRESENTATION_IMAGE,
            headerFooterLayout = HeaderFooterLayout.MODERN_BAR,
            specialPageLayout = SpecialPageLayout.PREMIUM_PAGE
        )
        PdfTheme.ROYAL -> PdfThemeStyle(
            accentColor = Color.parseColor("#163FA3"),
            softColor = Color.parseColor("#D8E6FF"),
            headerFillColor = Color.parseColor("#B9CEFF"),
            footerFillColor = Color.parseColor("#F5F8FF"),
            ruleColor = Color.parseColor("#5D86E8"),
            pageChromeLayout = PageChromeLayout.PREMIUM_PRESENTATION,
            titlePageLayout = TitlePageLayout.MODERN_COVER,
            chapterLayout = ChapterLayout.FULL_WIDTH_BANNER,
            sectionLayout = SectionLayout.DASHBOARD_BLOCK,
            paragraphLayout = ParagraphLayout.SPACIOUS_READING,
            tableLayout = TableLayout.DATA_DASHBOARD,
            chartLayout = ChartLayout.PRESENTATION_BOLD,
            figureLayout = FigureLayout.PRESENTATION_IMAGE,
            headerFooterLayout = HeaderFooterLayout.MODERN_BAR,
            specialPageLayout = SpecialPageLayout.PREMIUM_PAGE
        )
        PdfTheme.CRIMSON -> PdfThemeStyle(
            accentColor = Color.parseColor("#6D1111"),
            softColor = Color.parseColor("#F8D6D6"),
            headerFillColor = Color.parseColor("#EEB0B0"),
            footerFillColor = Color.parseColor("#FFF2F2"),
            ruleColor = Color.parseColor("#C95D5D"),
            pageChromeLayout = PageChromeLayout.OFFICIAL_BINDER,
            titlePageLayout = TitlePageLayout.LOGO_TOP_OFFICIAL,
            chapterLayout = ChapterLayout.LEFT_RULE,
            sectionLayout = SectionLayout.BOXED_LABEL,
            paragraphLayout = ParagraphLayout.COMPACT_REPORT,
            tableLayout = TableLayout.CLINICAL_BOXED,
            chartLayout = ChartLayout.CLINICAL_MUTED,
            figureLayout = FigureLayout.REPORT_PANEL,
            headerFooterLayout = HeaderFooterLayout.INSTITUTIONAL_HEADER,
            specialPageLayout = SpecialPageLayout.OFFICIAL_CERTIFICATE
        )
    }
}

private fun builtinLogoDefaults(layoutId: String): LogoSetting {
    val id = layoutId.uppercase()
    return when (id) {
        // Academic
        "FORMAL" -> LogoSetting("top-right", "medium", "rounded", -8, 0)
        "ACADEMIC" -> LogoSetting("top-right", "medium", "bordered", 0, 4)
        "ELEGANT" -> LogoSetting("top-center", "small", "circle", 0, -6)
        "ABSTRACTA" -> LogoSetting("bottom-left", "large", "square", 12, -12)
        "ANTIQUE" -> LogoSetting("top-right", "small", "circle", 0, 0)
        "ARGENT" -> LogoSetting("top-right", "medium", "bordered", 0, 0)
        "BRONZE" -> LogoSetting("top-left", "medium", "rounded", 8, 0)
        "CAMEO" -> LogoSetting("top-center", "small", "circle", 0, 0)
        "CANVAS" -> LogoSetting("top-right", "medium", "square", 0, 0)
        "CEDAR" -> LogoSetting("top-left", "small", "rounded", 6, 0)
        "CERAMIC" -> LogoSetting("top-right", "large", "bordered", 0, 0)
        "CHALK" -> LogoSetting("none", "small", "none", 0, 0)
        "CLASSICAL" -> LogoSetting("top-right", "medium", "rounded", 0, 0)
        // Journal
        "JOURNAL" -> LogoSetting("top-left", "small", "square", 4, 2)
        "MINIMAL" -> LogoSetting("top-left", "small", "square", 0, 0)
        "REVIEW" -> LogoSetting("top-left", "small", "square", 0, 0)
        "MINIMALIST" -> LogoSetting("none", "small", "none", 0, 0)
        "COTTON" -> LogoSetting("top-left", "small", "rounded", 0, 0)
        "CRYSTAL" -> LogoSetting("top-right", "small", "square", 0, 0)
        "DENIM" -> LogoSetting("top-left", "medium", "square", 6, 0)
        "FLINT" -> LogoSetting("top-left", "small", "square", 0, 0)
        "FOAM" -> LogoSetting("top-left", "small", "circle", 0, 0)
        "FROST" -> LogoSetting("top-right", "small", "square", 0, 0)
        "GINGER" -> LogoSetting("top-left", "small", "rounded", 4, 0)
        "HAZEL" -> LogoSetting("top-left", "small", "rounded", 0, 0)
        "IVORY" -> LogoSetting("top-center", "small", "square", 0, 0)
        "LACE" -> LogoSetting("top-right", "small", "circle", 0, 0)
        // Clinical
        "CLINICAL" -> LogoSetting("top-left", "medium", "circle", 8, 0)
        "BINDER" -> LogoSetting("top-left", "medium", "rounded", 10, 0)
        "INSTITUTIONAL" -> LogoSetting("top-left", "large", "bordered", 6, 0)
        "CASEBOOK" -> LogoSetting("top-left", "medium", "square", 0, 0)
        "COMPACT" -> LogoSetting("top-left", "small", "circle", 4, 0)
        "BRICK" -> LogoSetting("top-left", "medium", "square", 0, 0)
        "CORAL" -> LogoSetting("top-left", "medium", "circle", 0, 0)
        "CORK" -> LogoSetting("top-left", "small", "rounded", 6, 0)
        "EARTH" -> LogoSetting("top-left", "medium", "rounded", 0, 0)
        "GARNET" -> LogoSetting("top-left", "medium", "bordered", 0, 0)
        "GRANITE" -> LogoSetting("top-left", "medium", "square", 8, 0)
        "JADE" -> LogoSetting("top-left", "medium", "circle", 0, 0)
        "LEATHER" -> LogoSetting("top-left", "large", "bordered", 0, 0)
        "LINEN" -> LogoSetting("top-left", "medium", "rounded", 0, 0)
        "MAGMA" -> LogoSetting("bottom-left", "medium", "circle", 8, -8)
        // Premium
        "DASHBOARD" -> LogoSetting("top-left", "large", "square", 14, 0)
        "PREMIUM" -> LogoSetting("top-left", "xlarge", "bordered", 0, 0)
        "DEFENSE" -> LogoSetting("top-center", "large", "bordered", 0, 0)
        "EXECUTIVE" -> LogoSetting("top-left", "large", "square", 0, 0)
        "SIGNATURE" -> LogoSetting("top-left", "xlarge", "bordered", 12, 0)
        "MODERN" -> LogoSetting("top-left", "large", "square", 0, 0)
        "GRADIENT" -> LogoSetting("top-center", "large", "circle", 0, 0)
        "SLIDES" -> LogoSetting("bottom-right", "medium", "square", -8, -8)
        "AURORA" -> LogoSetting("top-left", "large", "circle", 0, 0)
        "BAMBOO" -> LogoSetting("top-left", "medium", "square", 8, 0)
        "BUBBLE" -> LogoSetting("top-center", "medium", "circle", 0, 0)
        "CARBON" -> LogoSetting("top-left", "large", "square", 0, 0)
        "CHROME" -> LogoSetting("top-right", "large", "bordered", 0, 0)
        "CLOUD" -> LogoSetting("top-center", "medium", "rounded", 0, 0)
        "COBALT" -> LogoSetting("top-left", "large", "bordered", 6, 0)
        "COPPER" -> LogoSetting("top-left", "medium", "rounded", 0, 0)
        "GOLD" -> LogoSetting("top-center", "xlarge", "bordered", 0, 0)
        "INDIGO" -> LogoSetting("top-left", "large", "square", 0, 0)
        // Report
        "ATLAS" -> LogoSetting("top-right", "medium", "square", 0, 0)
        "LABBOOK" -> LogoSetting("top-left", "small", "square", 0, 0)
        "CONTRAST" -> LogoSetting("top-left", "large", "square", 10, 0)
        "WIDESCREEN" -> LogoSetting("top-left", "large", "square", 0, 0)
        "CHARCOAL" -> LogoSetting("top-right", "medium", "square", 0, 0)
        "EBONY" -> LogoSetting("top-right", "medium", "rounded", 0, 0)
        "GHOST" -> LogoSetting("none", "small", "none", 0, 0)
        "GLASS" -> LogoSetting("bottom-right", "small", "circle", -8, -8)
        "JET" -> LogoSetting("top-right", "medium", "square", 0, 0)
        // Book
        "MONOGRAPH" -> LogoSetting("top-center", "small", "circle", 0, 0)
        "EDITORIAL" -> LogoSetting("top-left", "small", "square", 0, 0)
        "VINTAGE" -> LogoSetting("top-center", "small", "circle", 0, 4)
        "NOTEBOOK" -> LogoSetting("top-left", "small", "square", 6, 0)
        "BURLAP" -> LogoSetting("top-center", "small", "rounded", 0, 0)
        "FIESTA" -> LogoSetting("top-left", "medium", "circle", 0, 0)
        "LAVENDER" -> LogoSetting("top-right", "small", "circle", 0, 0)
        "LEMON" -> LogoSetting("top-left", "small", "square", 0, 0)
        "LILAC" -> LogoSetting("top-right", "small", "rounded", 0, 0)
        else -> LogoSetting("top-right", "medium", "rounded", 0, 0)
    }
}

data class LogoSetting(
    val position: String,
    val size: String,
    val style: String,
    val offsetX: Int = 0,
    val offsetY: Int = 0
)

data class LayoutFeatures(
    val margin: String = "normal",
    val font: String = "serif",
    val shadow: String = "light"
)

private fun builtinLayoutFeatures(layoutId: String): LayoutFeatures {
    return when (layoutId.uppercase()) {
        // Academic
        "FORMAL","ACADEMIC","CLASSICAL" -> LayoutFeatures("normal","serif","light")
        "ELEGANT","CAMEO" -> LayoutFeatures("wide","serif","light")
        "ABSTRACTA" -> LayoutFeatures("narrow","modern","medium")
        "ANTIQUE","BRONZE" -> LayoutFeatures("normal","serif","medium")
        "ARGENT","CANVAS" -> LayoutFeatures("normal","sans","light")
        "CANVAS","CHALK" -> LayoutFeatures("wide","mono","none")
        "CEDAR" -> LayoutFeatures("normal","serif","medium")
        "CERAMIC" -> LayoutFeatures("narrow","modern","deep")
        // Journal
        "JOURNAL","REVIEW" -> LayoutFeatures("narrow","journal","light")
        "MINIMAL","MINIMALIST" -> LayoutFeatures("wide","sans","none")
        "COTTON","GINGER" -> LayoutFeatures("normal","serif","light")
        "CRYSTAL" -> LayoutFeatures("normal","sans","none")
        "DENIM","FLINT" -> LayoutFeatures("narrow","sans","light")
        "FOAM" -> LayoutFeatures("normal","sans","light")
        "FROST","LACE" -> LayoutFeatures("wide","serif","light")
        "HAZEL","IVORY" -> LayoutFeatures("normal","serif","light")
        "GINGER" -> LayoutFeatures("normal","serif","medium")
        "FLINT" -> LayoutFeatures("narrow","sans","deep")
        // Clinical
        "CLINICAL","CASEBOOK","CORAL","CORK","JADE","LINEN" -> LayoutFeatures("normal","sans","light")
        "BINDER","BRICK","GARNET" -> LayoutFeatures("normal","sans","medium")
        "INSTITUTIONAL" -> LayoutFeatures("normal","sans","medium")
        "COMPACT","GRANITE","MAGMA" -> LayoutFeatures("narrow","sans","light")
        "EARTH","LEATHER" -> LayoutFeatures("normal","serif","medium")
        "LEATHER" -> LayoutFeatures("normal","serif","deep")
        "MAGMA" -> LayoutFeatures("narrow","sans","deep")
        // Premium
        "DASHBOARD","EXECUTIVE","GRADIENT" -> LayoutFeatures("narrow","modern","medium")
        "PREMIUM","DEFENSE","SIGNATURE" -> LayoutFeatures("normal","modern","deep")
        "MODERN","CHROME","INDIGO" -> LayoutFeatures("narrow","modern","light")
        "SLIDES" -> LayoutFeatures("narrow","sans","medium")
        "AURORA","COPPER" -> LayoutFeatures("normal","serif","medium")
        "BAMBOO" -> LayoutFeatures("normal","serif","light")
        "BUBBLE","CLOUD" -> LayoutFeatures("normal","sans","light")
        "CARBON" -> LayoutFeatures("narrow","sans","deep")
        "CHROME" -> LayoutFeatures("narrow","modern","medium")
        "CLOUD" -> LayoutFeatures("wide","sans","light")
        "COBALT" -> LayoutFeatures("narrow","sans","medium")
        "GOLD" -> LayoutFeatures("normal","modern","deep")
        // Report
        "ATLAS","CHARCOAL" -> LayoutFeatures("normal","sans","light")
        "LABBOOK" -> LayoutFeatures("narrow","mono","none")
        "CONTRAST" -> LayoutFeatures("narrow","sans","medium")
        "WIDESCREEN" -> LayoutFeatures("narrow","modern","light")
        "CHARCOAL" -> LayoutFeatures("normal","sans","medium")
        "EBONY" -> LayoutFeatures("normal","serif","deep")
        "GHOST","GLASS" -> LayoutFeatures("wide","sans","none")
        "JET" -> LayoutFeatures("narrow","sans","deep")
        // Book
        "MONOGRAPH","BURLAP","LILAC" -> LayoutFeatures("normal","serif","light")
        "EDITORIAL","LAVENDER" -> LayoutFeatures("wide","serif","light")
        "VINTAGE" -> LayoutFeatures("normal","serif","medium")
        "NOTEBOOK" -> LayoutFeatures("normal","mono","none")
        "FIESTA" -> LayoutFeatures("normal","sans","medium")
        "LEMON" -> LayoutFeatures("normal","sans","light")
        else -> LayoutFeatures("normal","serif","light")
    }
}

private fun resolvePdfThemeStyle(selection: String): PdfThemeStyle {
    val colorTheme = PdfTheme.fromName(selection)
    val base = resolvePdfThemeStyle(colorTheme)
    val layout = selection.substringAfter("|", missingDelimiterValue = "").trim().uppercase()
    if (layout.isBlank()) return base

    // Handle server-synced remote layouts
    if (layout.startsWith("SERVER:")) {
        val key = layout.removePrefix("SERVER:").substringBefore("|").trim()
        val context = EduLabsApplication.instance.applicationContext
        val remote = getCachedRemoteThemeLayouts(context).firstOrNull {
            it.layout_key.equals(key, ignoreCase = true)
        }
        if (remote != null) {
            return applyRemoteLayoutToStyle(base, remote)
        }
        return base
    }

    val baseStyle = when (layout) {
        "FORMAL" -> base.copy(
            pageChromeLayout = PageChromeLayout.FORMAL_FRAME,
            titlePageLayout = TitlePageLayout.CENTERED_UNIVERSITY,
            chapterLayout = ChapterLayout.SIMPLE_TITLE,
            sectionLayout = SectionLayout.FORMAL_HEADING,
            paragraphLayout = ParagraphLayout.INDENTED_ACADEMIC,
            tableLayout = TableLayout.FULL_GRID,
            chartLayout = ChartLayout.SIMPLE_ACADEMIC,
            figureLayout = FigureLayout.CENTERED_CAPTION,
            headerFooterLayout = HeaderFooterLayout.PLAIN_PAGE_NUMBER,
            specialPageLayout = SpecialPageLayout.FORMAL_DOCUMENT
        )
        "JOURNAL" -> base.copy(
            pageChromeLayout = PageChromeLayout.JOURNAL_ARTICLE,
            titlePageLayout = TitlePageLayout.JOURNAL_MANUSCRIPT,
            chapterLayout = ChapterLayout.JOURNAL_HEADING,
            sectionLayout = SectionLayout.JOURNAL_HEADING,
            paragraphLayout = ParagraphLayout.JOURNAL_BODY,
            tableLayout = TableLayout.JOURNAL_MINIMAL,
            chartLayout = ChartLayout.JOURNAL_CLEAN,
            figureLayout = FigureLayout.JOURNAL_FIGURE,
            headerFooterLayout = HeaderFooterLayout.JOURNAL_STYLE,
            specialPageLayout = SpecialPageLayout.CLEAN_DECLARATION
        )
        "CLINICAL" -> base.copy(
            pageChromeLayout = PageChromeLayout.CLINICAL_REPORT,
            titlePageLayout = TitlePageLayout.LOGO_TOP_OFFICIAL,
            chapterLayout = ChapterLayout.LEFT_RULE,
            sectionLayout = SectionLayout.BOXED_LABEL,
            paragraphLayout = ParagraphLayout.COMPACT_REPORT,
            tableLayout = TableLayout.CLINICAL_BOXED,
            chartLayout = ChartLayout.CLINICAL_MUTED,
            figureLayout = FigureLayout.REPORT_PANEL,
            headerFooterLayout = HeaderFooterLayout.INSTITUTIONAL_HEADER,
            specialPageLayout = SpecialPageLayout.OFFICIAL_CERTIFICATE
        )
        "BINDER" -> base.copy(
            pageChromeLayout = PageChromeLayout.OFFICIAL_BINDER,
            titlePageLayout = TitlePageLayout.CENTERED_UNIVERSITY,
            chapterLayout = ChapterLayout.FULL_WIDTH_BANNER,
            sectionLayout = SectionLayout.FORMAL_HEADING,
            paragraphLayout = ParagraphLayout.INDENTED_ACADEMIC,
            tableLayout = TableLayout.FULL_GRID,
            chartLayout = ChartLayout.SIMPLE_ACADEMIC,
            figureLayout = FigureLayout.CENTERED_CAPTION,
            headerFooterLayout = HeaderFooterLayout.INSTITUTIONAL_HEADER,
            specialPageLayout = SpecialPageLayout.OFFICIAL_CERTIFICATE
        )
        "DASHBOARD" -> base.copy(
            pageChromeLayout = PageChromeLayout.DASHBOARD_RAIL,
            titlePageLayout = TitlePageLayout.LOGO_TOP_OFFICIAL,
            chapterLayout = ChapterLayout.LEFT_RULE,
            sectionLayout = SectionLayout.DASHBOARD_BLOCK,
            paragraphLayout = ParagraphLayout.COMPACT_REPORT,
            tableLayout = TableLayout.DATA_DASHBOARD,
            chartLayout = ChartLayout.PRESENTATION_BOLD,
            figureLayout = FigureLayout.REPORT_PANEL,
            headerFooterLayout = HeaderFooterLayout.MODERN_BAR,
            specialPageLayout = SpecialPageLayout.PREMIUM_PAGE
        )
        "MINIMAL" -> base.copy(
            pageChromeLayout = PageChromeLayout.MINIMAL_JOURNAL,
            titlePageLayout = TitlePageLayout.JOURNAL_MANUSCRIPT,
            chapterLayout = ChapterLayout.JOURNAL_HEADING,
            sectionLayout = SectionLayout.JOURNAL_HEADING,
            paragraphLayout = ParagraphLayout.JOURNAL_BODY,
            tableLayout = TableLayout.JOURNAL_MINIMAL,
            chartLayout = ChartLayout.JOURNAL_CLEAN,
            figureLayout = FigureLayout.JOURNAL_FIGURE,
            headerFooterLayout = HeaderFooterLayout.JOURNAL_STYLE,
            specialPageLayout = SpecialPageLayout.CLEAN_DECLARATION
        )
        "ACADEMIC" -> base.copy(
            pageChromeLayout = PageChromeLayout.ACADEMIC_INSET,
            titlePageLayout = TitlePageLayout.CENTERED_UNIVERSITY,
            chapterLayout = ChapterLayout.SIMPLE_TITLE,
            sectionLayout = SectionLayout.BOXED_LABEL,
            paragraphLayout = ParagraphLayout.INDENTED_ACADEMIC,
            tableLayout = TableLayout.CLINICAL_BOXED,
            chartLayout = ChartLayout.CLINICAL_MUTED,
            figureLayout = FigureLayout.CENTERED_CAPTION,
            headerFooterLayout = HeaderFooterLayout.PLAIN_PAGE_NUMBER,
            specialPageLayout = SpecialPageLayout.FORMAL_DOCUMENT
        )
        "PREMIUM" -> base.copy(
            pageChromeLayout = PageChromeLayout.PREMIUM_PRESENTATION,
            titlePageLayout = TitlePageLayout.MODERN_COVER,
            chapterLayout = ChapterLayout.FULL_WIDTH_BANNER,
            sectionLayout = SectionLayout.DASHBOARD_BLOCK,
            paragraphLayout = ParagraphLayout.SPACIOUS_READING,
            tableLayout = TableLayout.DATA_DASHBOARD,
            chartLayout = ChartLayout.PRESENTATION_BOLD,
            figureLayout = FigureLayout.PRESENTATION_IMAGE,
            headerFooterLayout = HeaderFooterLayout.MODERN_BAR,
            specialPageLayout = SpecialPageLayout.PREMIUM_PAGE
        )
        "DEFENSE" -> base.copy(
            pageChromeLayout = PageChromeLayout.DEFENSE_PRESENTATION,
            titlePageLayout = TitlePageLayout.MODERN_COVER,
            chapterLayout = ChapterLayout.FULL_WIDTH_BANNER,
            sectionLayout = SectionLayout.DASHBOARD_BLOCK,
            paragraphLayout = ParagraphLayout.SPACIOUS_READING,
            tableLayout = TableLayout.DATA_DASHBOARD,
            chartLayout = ChartLayout.PRESENTATION_BOLD,
            figureLayout = FigureLayout.PRESENTATION_IMAGE,
            headerFooterLayout = HeaderFooterLayout.MODERN_BAR,
            specialPageLayout = SpecialPageLayout.PREMIUM_PAGE
        )
        "INSTITUTIONAL" -> base.copy(
            pageChromeLayout = PageChromeLayout.OFFICIAL_BINDER,
            titlePageLayout = TitlePageLayout.LOGO_TOP_OFFICIAL,
            chapterLayout = ChapterLayout.LEFT_RULE,
            sectionLayout = SectionLayout.BOXED_LABEL,
            paragraphLayout = ParagraphLayout.COMPACT_REPORT,
            tableLayout = TableLayout.CLINICAL_BOXED,
            chartLayout = ChartLayout.CLINICAL_MUTED,
            figureLayout = FigureLayout.REPORT_PANEL,
            headerFooterLayout = HeaderFooterLayout.INSTITUTIONAL_HEADER,
            specialPageLayout = SpecialPageLayout.OFFICIAL_CERTIFICATE
        )
        "EDITORIAL" -> base.copy(
            pageChromeLayout = PageChromeLayout.EDITORIAL_FOLIO,
            titlePageLayout = TitlePageLayout.MODERN_COVER,
            chapterLayout = ChapterLayout.JOURNAL_HEADING,
            sectionLayout = SectionLayout.EDITORIAL_MARK,
            paragraphLayout = ParagraphLayout.SPACIOUS_READING,
            tableLayout = TableLayout.JOURNAL_MINIMAL,
            chartLayout = ChartLayout.JOURNAL_CLEAN,
            figureLayout = FigureLayout.PRESENTATION_IMAGE,
            headerFooterLayout = HeaderFooterLayout.JOURNAL_STYLE,
            specialPageLayout = SpecialPageLayout.PREMIUM_PAGE
        )
        "ATLAS" -> base.copy(
            pageChromeLayout = PageChromeLayout.ATLAS_PLATE,
            titlePageLayout = TitlePageLayout.LOGO_TOP_OFFICIAL,
            chapterLayout = ChapterLayout.FULL_WIDTH_BANNER,
            sectionLayout = SectionLayout.PLATE_LABEL,
            paragraphLayout = ParagraphLayout.COMPACT_REPORT,
            tableLayout = TableLayout.CLINICAL_BOXED,
            chartLayout = ChartLayout.PRESENTATION_BOLD,
            figureLayout = FigureLayout.PRESENTATION_IMAGE,
            headerFooterLayout = HeaderFooterLayout.MODERN_BAR,
            specialPageLayout = SpecialPageLayout.PREMIUM_PAGE
        )
        "EXECUTIVE" -> base.copy(
            pageChromeLayout = PageChromeLayout.EXECUTIVE_SUMMARY,
            titlePageLayout = TitlePageLayout.MODERN_COVER,
            chapterLayout = ChapterLayout.LEFT_RULE,
            sectionLayout = SectionLayout.EXECUTIVE_BAND,
            paragraphLayout = ParagraphLayout.COMPACT_REPORT,
            tableLayout = TableLayout.DATA_DASHBOARD,
            chartLayout = ChartLayout.PRESENTATION_BOLD,
            figureLayout = FigureLayout.REPORT_PANEL,
            headerFooterLayout = HeaderFooterLayout.MODERN_BAR,
            specialPageLayout = SpecialPageLayout.PREMIUM_PAGE
        )
        "MONOGRAPH" -> base.copy(
            pageChromeLayout = PageChromeLayout.MONOGRAPH_CLASSIC,
            titlePageLayout = TitlePageLayout.CENTERED_UNIVERSITY,
            chapterLayout = ChapterLayout.SIMPLE_TITLE,
            sectionLayout = SectionLayout.MONOGRAPH_DROP,
            paragraphLayout = ParagraphLayout.INDENTED_ACADEMIC,
            tableLayout = TableLayout.FULL_GRID,
            chartLayout = ChartLayout.SIMPLE_ACADEMIC,
            figureLayout = FigureLayout.CENTERED_CAPTION,
            headerFooterLayout = HeaderFooterLayout.PLAIN_PAGE_NUMBER,
            specialPageLayout = SpecialPageLayout.FORMAL_DOCUMENT
        )
        "CASEBOOK" -> base.copy(
            pageChromeLayout = PageChromeLayout.CASEBOOK_FILE,
            titlePageLayout = TitlePageLayout.LOGO_TOP_OFFICIAL,
            chapterLayout = ChapterLayout.LEFT_RULE,
            sectionLayout = SectionLayout.BOXED_LABEL,
            paragraphLayout = ParagraphLayout.COMPACT_REPORT,
            tableLayout = TableLayout.CLINICAL_BOXED,
            chartLayout = ChartLayout.CLINICAL_MUTED,
            figureLayout = FigureLayout.REPORT_PANEL,
            headerFooterLayout = HeaderFooterLayout.INSTITUTIONAL_HEADER,
            specialPageLayout = SpecialPageLayout.OFFICIAL_CERTIFICATE
        )
        "LABBOOK" -> base.copy(
            pageChromeLayout = PageChromeLayout.LAB_NOTEBOOK,
            titlePageLayout = TitlePageLayout.LOGO_TOP_OFFICIAL,
            chapterLayout = ChapterLayout.LEFT_RULE,
            sectionLayout = SectionLayout.PLATE_LABEL,
            paragraphLayout = ParagraphLayout.COMPACT_REPORT,
            tableLayout = TableLayout.DATA_DASHBOARD,
            chartLayout = ChartLayout.PRESENTATION_BOLD,
            figureLayout = FigureLayout.REPORT_PANEL,
            headerFooterLayout = HeaderFooterLayout.MODERN_BAR,
            specialPageLayout = SpecialPageLayout.PREMIUM_PAGE
        )
        "REVIEW" -> base.copy(
            pageChromeLayout = PageChromeLayout.SYSTEMATIC_REVIEW,
            titlePageLayout = TitlePageLayout.JOURNAL_MANUSCRIPT,
            chapterLayout = ChapterLayout.JOURNAL_HEADING,
            sectionLayout = SectionLayout.EDITORIAL_MARK,
            paragraphLayout = ParagraphLayout.JOURNAL_BODY,
            tableLayout = TableLayout.JOURNAL_MINIMAL,
            chartLayout = ChartLayout.JOURNAL_CLEAN,
            figureLayout = FigureLayout.JOURNAL_FIGURE,
            headerFooterLayout = HeaderFooterLayout.JOURNAL_STYLE,
            specialPageLayout = SpecialPageLayout.CLEAN_DECLARATION
        )
        "SIGNATURE" -> base.copy(
            pageChromeLayout = PageChromeLayout.SIGNATURE_PORTFOLIO,
            titlePageLayout = TitlePageLayout.MODERN_COVER,
            chapterLayout = ChapterLayout.FULL_WIDTH_BANNER,
            sectionLayout = SectionLayout.EXECUTIVE_BAND,
            paragraphLayout = ParagraphLayout.SPACIOUS_READING,
            tableLayout = TableLayout.DATA_DASHBOARD,
            chartLayout = ChartLayout.PRESENTATION_BOLD,
            figureLayout = FigureLayout.PRESENTATION_IMAGE,
            headerFooterLayout = HeaderFooterLayout.MODERN_BAR,
            specialPageLayout = SpecialPageLayout.PREMIUM_PAGE
        )
        "COMPACT" -> base.copy(
            pageChromeLayout = PageChromeLayout.CLINICAL_REPORT,
            titlePageLayout = TitlePageLayout.LOGO_TOP_OFFICIAL,
            chapterLayout = ChapterLayout.LEFT_RULE,
            sectionLayout = SectionLayout.BOXED_LABEL,
            paragraphLayout = ParagraphLayout.COMPACT_REPORT,
            tableLayout = TableLayout.CLINICAL_BOXED,
            chartLayout = ChartLayout.CLINICAL_MUTED,
            figureLayout = FigureLayout.REPORT_PANEL,
            headerFooterLayout = HeaderFooterLayout.PLAIN_PAGE_NUMBER,
            specialPageLayout = SpecialPageLayout.FORMAL_DOCUMENT
        )
        "ELEGANT" -> base.copy(
            pageChromeLayout = PageChromeLayout.EDITORIAL_FOLIO,
            titlePageLayout = TitlePageLayout.CENTERED_UNIVERSITY,
            chapterLayout = ChapterLayout.SIMPLE_TITLE,
            sectionLayout = SectionLayout.EDITORIAL_MARK,
            paragraphLayout = ParagraphLayout.SPACIOUS_READING,
            tableLayout = TableLayout.FULL_GRID,
            chartLayout = ChartLayout.SIMPLE_ACADEMIC,
            figureLayout = FigureLayout.CENTERED_CAPTION,
            headerFooterLayout = HeaderFooterLayout.JOURNAL_STYLE,
            specialPageLayout = SpecialPageLayout.PREMIUM_PAGE
        )
        "MODERN" -> base.copy(
            pageChromeLayout = PageChromeLayout.MINIMAL_JOURNAL,
            titlePageLayout = TitlePageLayout.MODERN_COVER,
            chapterLayout = ChapterLayout.FULL_WIDTH_BANNER,
            sectionLayout = SectionLayout.DASHBOARD_BLOCK,
            paragraphLayout = ParagraphLayout.SPACIOUS_READING,
            tableLayout = TableLayout.DATA_DASHBOARD,
            chartLayout = ChartLayout.PRESENTATION_BOLD,
            figureLayout = FigureLayout.PRESENTATION_IMAGE,
            headerFooterLayout = HeaderFooterLayout.MODERN_BAR,
            specialPageLayout = SpecialPageLayout.PREMIUM_PAGE
        )
        "VINTAGE" -> base.copy(
            pageChromeLayout = PageChromeLayout.MONOGRAPH_CLASSIC,
            titlePageLayout = TitlePageLayout.CENTERED_UNIVERSITY,
            chapterLayout = ChapterLayout.SIMPLE_TITLE,
            sectionLayout = SectionLayout.MONOGRAPH_DROP,
            paragraphLayout = ParagraphLayout.INDENTED_ACADEMIC,
            tableLayout = TableLayout.FULL_GRID,
            chartLayout = ChartLayout.SIMPLE_ACADEMIC,
            figureLayout = FigureLayout.CENTERED_CAPTION,
            headerFooterLayout = HeaderFooterLayout.PLAIN_PAGE_NUMBER,
            specialPageLayout = SpecialPageLayout.FORMAL_DOCUMENT
        )
        "CONTRAST" -> base.copy(
            pageChromeLayout = PageChromeLayout.OFFICIAL_BINDER,
            titlePageLayout = TitlePageLayout.MODERN_COVER,
            chapterLayout = ChapterLayout.FULL_WIDTH_BANNER,
            sectionLayout = SectionLayout.DASHBOARD_BLOCK,
            paragraphLayout = ParagraphLayout.COMPACT_REPORT,
            tableLayout = TableLayout.DATA_DASHBOARD,
            chartLayout = ChartLayout.PRESENTATION_BOLD,
            figureLayout = FigureLayout.PRESENTATION_IMAGE,
            headerFooterLayout = HeaderFooterLayout.MODERN_BAR,
            specialPageLayout = SpecialPageLayout.PREMIUM_PAGE
        )
        "MINIMALIST" -> base.copy(
            pageChromeLayout = PageChromeLayout.MINIMAL_JOURNAL,
            titlePageLayout = TitlePageLayout.JOURNAL_MANUSCRIPT,
            chapterLayout = ChapterLayout.JOURNAL_HEADING,
            sectionLayout = SectionLayout.FORMAL_HEADING,
            paragraphLayout = ParagraphLayout.SPACIOUS_READING,
            tableLayout = TableLayout.JOURNAL_MINIMAL,
            chartLayout = ChartLayout.JOURNAL_CLEAN,
            figureLayout = FigureLayout.CENTERED_CAPTION,
            headerFooterLayout = HeaderFooterLayout.PLAIN_PAGE_NUMBER,
            specialPageLayout = SpecialPageLayout.CLEAN_DECLARATION
        )
        "GRADIENT" -> base.copy(
            pageChromeLayout = PageChromeLayout.DEFENSE_PRESENTATION,
            titlePageLayout = TitlePageLayout.MODERN_COVER,
            chapterLayout = ChapterLayout.FULL_WIDTH_BANNER,
            sectionLayout = SectionLayout.EXECUTIVE_BAND,
            paragraphLayout = ParagraphLayout.SPACIOUS_READING,
            tableLayout = TableLayout.DATA_DASHBOARD,
            chartLayout = ChartLayout.PRESENTATION_BOLD,
            figureLayout = FigureLayout.PRESENTATION_IMAGE,
            headerFooterLayout = HeaderFooterLayout.MODERN_BAR,
            specialPageLayout = SpecialPageLayout.PREMIUM_PAGE
        )
        "NOTEBOOK" -> base.copy(
            pageChromeLayout = PageChromeLayout.LAB_NOTEBOOK,
            titlePageLayout = TitlePageLayout.LOGO_TOP_OFFICIAL,
            chapterLayout = ChapterLayout.LEFT_RULE,
            sectionLayout = SectionLayout.PLATE_LABEL,
            paragraphLayout = ParagraphLayout.COMPACT_REPORT,
            tableLayout = TableLayout.CLINICAL_BOXED,
            chartLayout = ChartLayout.SIMPLE_ACADEMIC,
            figureLayout = FigureLayout.REPORT_PANEL,
            headerFooterLayout = HeaderFooterLayout.PLAIN_PAGE_NUMBER,
            specialPageLayout = SpecialPageLayout.OFFICIAL_CERTIFICATE
        )
        "SLIDES" -> base.copy(
            pageChromeLayout = PageChromeLayout.PREMIUM_PRESENTATION,
            titlePageLayout = TitlePageLayout.MODERN_COVER,
            chapterLayout = ChapterLayout.FULL_WIDTH_BANNER,
            sectionLayout = SectionLayout.DASHBOARD_BLOCK,
            paragraphLayout = ParagraphLayout.COMPACT_REPORT,
            tableLayout = TableLayout.DATA_DASHBOARD,
            chartLayout = ChartLayout.PRESENTATION_BOLD,
            figureLayout = FigureLayout.PRESENTATION_IMAGE,
            headerFooterLayout = HeaderFooterLayout.MODERN_BAR,
            specialPageLayout = SpecialPageLayout.PREMIUM_PAGE
        )
        "WIDESCREEN" -> base.copy(
            pageChromeLayout = PageChromeLayout.EXECUTIVE_SUMMARY,
            titlePageLayout = TitlePageLayout.MODERN_COVER,
            chapterLayout = ChapterLayout.LEFT_RULE,
            sectionLayout = SectionLayout.EXECUTIVE_BAND,
            paragraphLayout = ParagraphLayout.COMPACT_REPORT,
            tableLayout = TableLayout.DATA_DASHBOARD,
            chartLayout = ChartLayout.PRESENTATION_BOLD,
            figureLayout = FigureLayout.REPORT_PANEL,
            headerFooterLayout = HeaderFooterLayout.MODERN_BAR,
            specialPageLayout = SpecialPageLayout.PREMIUM_PAGE
        )
        else -> base
    }

    // Apply family-based logo defaults for built-in layouts
    val logoDef = builtinLogoDefaults(layout)
    val feat = builtinLayoutFeatures(layout)
    return baseStyle.copy(
        logoPosition = logoDef.position, logoSize = logoDef.size, logoStyle = logoDef.style,
        logoOffsetX = logoDef.offsetX, logoOffsetY = logoDef.offsetY,
        pageMargin = feat.margin, fontScheme = feat.font, shadowDepth = feat.shadow
    )
}

private fun applyRemoteLayoutToStyle(style: PdfThemeStyle, remote: RemoteThemeLayout): PdfThemeStyle {
    val layout = try {
        val ctx = EduLabsApplication.instance.applicationContext
        getCachedRemoteThemeLayouts(ctx).firstOrNull { it.layout_key == remote.layout_key } ?: remote
    } catch (_: Exception) { remote }

    return style.copy(
        pageChromeLayout = enumValueOfOrNull<PageChromeLayout>(layout.page_chrome_layout) ?: style.pageChromeLayout,
        titlePageLayout = enumValueOfOrNull<TitlePageLayout>(layout.title_page_layout) ?: style.titlePageLayout,
        chapterLayout = enumValueOfOrNull<ChapterLayout>(layout.chapter_layout) ?: style.chapterLayout,
        sectionLayout = enumValueOfOrNull<SectionLayout>(layout.section_layout) ?: style.sectionLayout,
        paragraphLayout = enumValueOfOrNull<ParagraphLayout>(layout.paragraph_layout) ?: style.paragraphLayout,
        tableLayout = enumValueOfOrNull<TableLayout>(layout.table_layout) ?: style.tableLayout,
        chartLayout = enumValueOfOrNull<ChartLayout>(layout.chart_layout) ?: style.chartLayout,
        figureLayout = enumValueOfOrNull<FigureLayout>(layout.figure_layout) ?: style.figureLayout,
        headerFooterLayout = enumValueOfOrNull<HeaderFooterLayout>(layout.header_footer_layout) ?: style.headerFooterLayout,
        specialPageLayout = enumValueOfOrNull<SpecialPageLayout>(layout.special_page_layout) ?: style.specialPageLayout,
        accentColor = parseHexColor(layout.accent_color) ?: style.accentColor,
        softColor = parseHexColor(layout.soft_color) ?: style.softColor,
        headerFillColor = parseHexColor(layout.header_fill_color) ?: style.headerFillColor,
        footerFillColor = parseHexColor(layout.footer_fill_color) ?: style.footerFillColor,
        ruleColor = parseHexColor(layout.rule_color) ?: style.ruleColor,
        logoPosition = layout.logo_position.ifBlank { "top-right" },
        logoSize = layout.logo_size.ifBlank { "medium" },
        logoStyle = layout.logo_style.ifBlank { "rounded" },
        logoOffsetX = layout.logo_offset_x,
        logoOffsetY = layout.logo_offset_y,
        pageMargin = layout.page_margin.ifBlank { "normal" },
        fontScheme = layout.font_scheme.ifBlank { "serif" },
        shadowDepth = layout.shadow_depth.ifBlank { "light" },
    )
}

private enum class DocxTextRole {
    TITLE,
    CHAPTER,
    SECTION,
    BODY,
    TABLE,
    CAPTION,
    META
}

private fun PdfThemeStyle.titleFont(): PDType1Font = when (pageChromeLayout) {
    PageChromeLayout.JOURNAL_ARTICLE,
    PageChromeLayout.MINIMAL_JOURNAL,
    PageChromeLayout.EDITORIAL_FOLIO,
    PageChromeLayout.MONOGRAPH_CLASSIC,
    PageChromeLayout.SYSTEMATIC_REVIEW -> PDType1Font.TIMES_BOLD
    else -> PDType1Font.HELVETICA_BOLD
}

private fun PdfThemeStyle.chapterFont(): PDType1Font = when (pageChromeLayout) {
    PageChromeLayout.JOURNAL_ARTICLE,
    PageChromeLayout.MINIMAL_JOURNAL,
    PageChromeLayout.EDITORIAL_FOLIO,
    PageChromeLayout.MONOGRAPH_CLASSIC,
    PageChromeLayout.SYSTEMATIC_REVIEW -> PDType1Font.TIMES_BOLD
    else -> PDType1Font.HELVETICA_BOLD
}

private fun PdfThemeStyle.sectionFont(): PDType1Font = when (pageChromeLayout) {
    PageChromeLayout.JOURNAL_ARTICLE,
    PageChromeLayout.MINIMAL_JOURNAL,
    PageChromeLayout.EDITORIAL_FOLIO,
    PageChromeLayout.MONOGRAPH_CLASSIC,
    PageChromeLayout.SYSTEMATIC_REVIEW -> PDType1Font.TIMES_BOLD
    else -> PDType1Font.HELVETICA_BOLD
}

private fun PdfThemeStyle.bodyFont(): PDType1Font = when (pageChromeLayout) {
    PageChromeLayout.JOURNAL_ARTICLE,
    PageChromeLayout.MINIMAL_JOURNAL,
    PageChromeLayout.EDITORIAL_FOLIO,
    PageChromeLayout.MONOGRAPH_CLASSIC,
    PageChromeLayout.SYSTEMATIC_REVIEW -> PDType1Font.TIMES_ROMAN
    else -> PDType1Font.HELVETICA
}

private fun PdfThemeStyle.headingSize(): Float = when (pageChromeLayout) {
    PageChromeLayout.JOURNAL_ARTICLE,
    PageChromeLayout.MINIMAL_JOURNAL,
    PageChromeLayout.SYSTEMATIC_REVIEW -> 14.2f
    PageChromeLayout.EDITORIAL_FOLIO,
    PageChromeLayout.MONOGRAPH_CLASSIC -> 14.6f
    PageChromeLayout.ATLAS_PLATE,
    PageChromeLayout.EXECUTIVE_SUMMARY,
    PageChromeLayout.SIGNATURE_PORTFOLIO -> 15.2f
    PageChromeLayout.CASEBOOK_FILE,
    PageChromeLayout.LAB_NOTEBOOK -> 14.8f
    else -> 13.4f
}

private fun PdfThemeStyle.chapterTitleSize(): Float = when (pageChromeLayout) {
    PageChromeLayout.PREMIUM_PRESENTATION,
    PageChromeLayout.DEFENSE_PRESENTATION,
    PageChromeLayout.SIGNATURE_PORTFOLIO -> 21.5f
    PageChromeLayout.ATLAS_PLATE,
    PageChromeLayout.EXECUTIVE_SUMMARY,
    PageChromeLayout.CASEBOOK_FILE -> 20.5f
    PageChromeLayout.EDITORIAL_FOLIO,
    PageChromeLayout.MONOGRAPH_CLASSIC,
    PageChromeLayout.SYSTEMATIC_REVIEW -> 20f
    else -> 19f
}

private fun PdfThemeStyle.docxFontFamily(role: DocxTextRole): String = when (pageChromeLayout) {
    PageChromeLayout.JOURNAL_ARTICLE,
    PageChromeLayout.MINIMAL_JOURNAL,
    PageChromeLayout.EDITORIAL_FOLIO,
    PageChromeLayout.MONOGRAPH_CLASSIC,
    PageChromeLayout.SYSTEMATIC_REVIEW -> when (role) {
        DocxTextRole.TITLE, DocxTextRole.CHAPTER, DocxTextRole.SECTION -> "Times New Roman"
        DocxTextRole.BODY, DocxTextRole.TABLE, DocxTextRole.CAPTION, DocxTextRole.META -> "Times New Roman"
    }
    PageChromeLayout.LAB_NOTEBOOK -> when (role) {
        DocxTextRole.BODY, DocxTextRole.TABLE -> "Courier New"
        else -> "Arial"
    }
    else -> when (role) {
        DocxTextRole.TITLE -> "Arial"
        DocxTextRole.CHAPTER -> "Arial"
        DocxTextRole.SECTION -> "Arial"
        DocxTextRole.BODY, DocxTextRole.TABLE, DocxTextRole.CAPTION, DocxTextRole.META -> "Arial"
    }
}

private fun PdfThemeStyle.docxHeadingSize(role: DocxTextRole): Int = when (pageChromeLayout) {
    PageChromeLayout.JOURNAL_ARTICLE,
    PageChromeLayout.MINIMAL_JOURNAL,
    PageChromeLayout.EDITORIAL_FOLIO,
    PageChromeLayout.MONOGRAPH_CLASSIC,
    PageChromeLayout.SYSTEMATIC_REVIEW -> when (role) {
        DocxTextRole.TITLE -> 27
        DocxTextRole.CHAPTER -> 20
        DocxTextRole.SECTION -> 15
        else -> 11
    }
    PageChromeLayout.ATLAS_PLATE,
    PageChromeLayout.EXECUTIVE_SUMMARY,
    PageChromeLayout.CASEBOOK_FILE,
    PageChromeLayout.SIGNATURE_PORTFOLIO,
    PageChromeLayout.PREMIUM_PRESENTATION,
    PageChromeLayout.DEFENSE_PRESENTATION -> when (role) {
        DocxTextRole.TITLE -> 28
        DocxTextRole.CHAPTER -> 21
        DocxTextRole.SECTION -> 15
        else -> 11
    }
    else -> when (role) {
        DocxTextRole.TITLE -> 26
        DocxTextRole.CHAPTER -> 19
        DocxTextRole.SECTION -> 14
        else -> 11
    }
}

private fun PdfThemeStyle.androidTypeface(role: DocxTextRole): Typeface = when (pageChromeLayout) {
    PageChromeLayout.JOURNAL_ARTICLE,
    PageChromeLayout.MINIMAL_JOURNAL,
    PageChromeLayout.EDITORIAL_FOLIO,
    PageChromeLayout.MONOGRAPH_CLASSIC,
    PageChromeLayout.SYSTEMATIC_REVIEW -> when (role) {
        DocxTextRole.TITLE, DocxTextRole.CHAPTER, DocxTextRole.SECTION -> Typeface.create(Typeface.SERIF, Typeface.BOLD)
        DocxTextRole.BODY, DocxTextRole.TABLE, DocxTextRole.CAPTION, DocxTextRole.META -> Typeface.create(Typeface.SERIF, Typeface.NORMAL)
    }
    PageChromeLayout.LAB_NOTEBOOK -> when (role) {
        DocxTextRole.BODY, DocxTextRole.TABLE -> Typeface.create(Typeface.MONOSPACE, Typeface.NORMAL)
        else -> Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
    }
    else -> when (role) {
        DocxTextRole.TITLE, DocxTextRole.CHAPTER, DocxTextRole.SECTION -> Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
        DocxTextRole.BODY, DocxTextRole.TABLE, DocxTextRole.CAPTION, DocxTextRole.META -> Typeface.create(Typeface.SANS_SERIF, Typeface.NORMAL)
    }
}

private fun PdfThemeStyle.withExportOverrides(
    margin: String,
    font: String,
    logoPlacement: String,
    headerFooterEnabled: Boolean
): PdfThemeStyle {
    val normalizedMargin = margin.lowercase().ifBlank { pageMargin }
    val normalizedFont = font.lowercase().ifBlank { fontScheme }
    val normalizedLogo = logoPlacement.lowercase().ifBlank { "theme" }
    return copy(
        pageMargin = normalizedMargin,
        fontScheme = normalizedFont,
        logoPosition = if (normalizedLogo == "theme") logoPosition else normalizedLogo,
        headerFooterLayout = if (headerFooterEnabled) headerFooterLayout else HeaderFooterLayout.PLAIN_PAGE_NUMBER
    )
}

private fun PdfThemeStyle.exportMarginPoints(): Float = when (pageMargin.lowercase()) {
    "compact", "narrow" -> 42f
    "wide" -> 64f
    "binding" -> 72f
    else -> 50f
}

private fun exportLineSpacingMultiplier(value: String): Float = when (value.lowercase()) {
    "compact" -> 1.12f
    "relaxed" -> 1.55f
    "double" -> 1.9f
    else -> 1.32f
}

private fun romanNumeral(value: Int): String {
    if (value <= 0) return value.toString()
    var remaining = value
    val parts = listOf(
        1000 to "M", 900 to "CM", 500 to "D", 400 to "CD",
        100 to "C", 90 to "XC", 50 to "L", 40 to "XL",
        10 to "X", 9 to "IX", 5 to "V", 4 to "IV", 1 to "I"
    )
    return buildString {
        parts.forEach { (number, numeral) ->
            while (remaining >= number) {
                append(numeral)
                remaining -= number
            }
        }
    }
}

private fun PdfThemeStyle.fontOverride(base: PDType1Font, bold: Boolean = false): PDType1Font = when (fontScheme.lowercase()) {
    "sans", "modern" -> if (bold) PDType1Font.HELVETICA_BOLD else PDType1Font.HELVETICA
    "mono" -> if (bold) PDType1Font.COURIER_BOLD else PDType1Font.COURIER
    "journal", "serif" -> if (bold) PDType1Font.TIMES_BOLD else PDType1Font.TIMES_ROMAN
    else -> base
}

private fun officeColor(color: Int): String {
        return "%02X%02X%02X".format(Color.red(color), Color.green(color), Color.blue(color))
    }

private fun sanitizeOfficeText(value: String): String {
    return value
        .replace("\u00E2\u20AC\u00A2", "\u2022")
        .filter { char ->
            char == '\t' ||
                char == '\n' ||
                char == '\r' ||
                char.code in 0x20..0xD7FF ||
                char.code in 0xE000..0xFFFD
        }
}

class ThesisViewModel : ViewModel() {

    init {
        ModelRotator.buildPool("auto")
        tryLoadLatestSession()
        loadPreviousSessions()
        syncRemoteThemeLayoutsOnStart()
    }

    data class UiState(
        val sessionId: String = "",
        val thesisTitle: String = "",
        val pdfUri: Uri? = null,
        val processing: Boolean = false,
        val status: String = "Idle",
        val progressCurrent: Int = 0,
        val progressTotal: Int = 0,
        val variables: List<Variable> = emptyList(),
        val chapters: List<Chapter> = emptyList(),
        val showVariablesEditor: Boolean = false,
        val selectedProvider: String = "auto",
        val hasErrors: Boolean = false,
        val lastExportedUri: Uri? = null,
        val completionPercent: Int = 0,
        val previousSessions: List<SessionItem> = emptyList(),
        val referenceValidationState: ReferenceValidationState? = null,
        val referenceUpdateNoticeState: ReferenceValidationState? = null,
        val collegeLogoUri: String = "",
        val pdfTheme: String = PdfTheme.CLASSIC.name,
        val verifiedPubMedReferences: List<ReferenceJson> = emptyList(),
        val verifiedPubMedAbstractSources: List<PubMedAbstractSourceJson> = emptyList(),
        val referenceSequenceCounter: Int = 1,
        val pubMedFigureCheckedPmids: List<String> = emptyList(),
        val pubMedFigures: List<PubMedFigureJson> = emptyList(),
        val activeChapterName: String = "",
        val referenceCacheLastSyncedAt: Long = 0L,
        val referenceCacheSyncInProgress: Boolean = false,
        val referenceCacheSyncCurrent: Int = 0,
        val referenceCacheSyncTotal: Int = 0,
        val referenceCacheSyncError: String? = null,
        val vpsAutoCompleteEnabled: Boolean = false,
        val loadingState: String? = null,
        val autoSyncEnabled: Boolean = true,
        val lastWorkerSyncTime: Long = 0L,
        val selectedChapters: Set<String> = emptySet(),
        val exportMargin: String = "normal",
        val exportFont: String = "serif",
        val exportLineSpacing: String = "normal",
        val exportLogoPlacement: String = "theme",
        val exportPageNumbering: String = "theme",
        val exportHeaderFooter: Boolean = true,
        val exportWatermark: Boolean = false,
        val exportAutoToc: Boolean = true,
        val exportAutoLists: Boolean = true,
        val promptSectionSplittingEnabled: Boolean = true,
        val promptMaxChars: Int = 12000,
        val masterChartColumns: List<MasterChartColumnJson> = emptyList(),
        val masterChartCsv: String = "",
        val masterChartGeneratedAt: Long = 0L,
        val masterDataFileName: String = "",
        val masterDataHeaders: List<String> = emptyList(),
        val masterDataRows: List<List<String>> = emptyList(),
        val masterDataMappings: List<MasterChartColumnMappingJson> = emptyList(),
        val masterDataValidationIssues: List<MasterChartValidationIssueJson> = emptyList(),
        val masterDataResultTables: List<MasterChartResultSummaryJson> = emptyList(),
        val masterDataImportedAt: Long = 0L,
        val aiLogs: List<ThesisAiLogEntry> = emptyList()
    )

    private val _uiState = MutableStateFlow(UiState(sessionId = newSessionId()))
    val uiState = _uiState.asStateFlow()

    private val gson = Gson()

    private val rawClient: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .connectTimeout(60, TimeUnit.SECONDS)
            .readTimeout(180, TimeUnit.SECONDS)
            .writeTimeout(180, TimeUnit.SECONDS)
            .retryOnConnectionFailure(true)
            .build()
    }

    private val pubMedPmidCache = ConcurrentHashMap<String, PubMedMatch>()
    private val pubMedSearchCache = ConcurrentHashMap<String, PubMedMatch>()
    private val pubMedAbstractSourceCache = ConcurrentHashMap<String, PubMedAbstractSourceJson>()
    private val pubMedAbstractFetchedAt = ConcurrentHashMap<String, Long>()
    private val pubMedFigureCache = ConcurrentHashMap<String, List<PubMedFigureJson>>()
    private val verifiedReferenceCache = ConcurrentHashMap<String, ReferenceJson>()
    private val maxFirestoreReferenceCacheChars = 450_000
    private val maxFirestoreChunkChars = 850_000
    private val pubMedAbstractStaleAfterMs = TimeUnit.DAYS.toMillis(30)
    private val referenceCacheBackendUrls = listOf(
        "https://medigyaan.xyz/Neurons/reference_cache_backend.php",
        "http://medigyaan.xyz/Neurons/reference_cache_backend.php"
    )
    private var lastUploadedReferenceCacheSignature: String = ""
    private var currentSessionListenerRef: DatabaseReference? = null
    private var currentSessionListener: ValueEventListener? = null
    private var currentSessionListenerSessionId: String = ""
    private var remoteSessionMergeJob: Job? = null
    private var vpsPollingJob: Job? = null
    private var lastRemoteWorkerSignature: String = ""
    private var lastNotifiedChapterSuccessSignature: String = ""
    private var lastSavedChapters: List<Chapter>? = null
    private var firebaseSaveJob: Job? = null
    private val exactPubMedMatchScore = 90
    private val minimumPubMedSearchScore = 45
    private val minimumTitleTokenOverlapScore = 15

    private fun startBackgroundWork(context: Context, message: String) {
        ThesisBackgroundService.start(context.applicationContext, message)
    }

    private fun stopBackgroundWork(context: Context) {
        ThesisBackgroundService.stop(context.applicationContext)
    }

    private val chapterHeadings = listOf(
        "Title", "Certificate", "Declaration", "Acknowledgements", "Abstract", "Keywords", "Introduction", "Background",
        "Disease Burden", "Epidemiology", "Pathophysiology", "Current Treatment", "Research Gap", "Need for Study",
        "Literature Review", "Aim of Study", "Objectives", "Hypothesis", "Materials and Methods", "Study Design", "Study Setting",
        "Study Duration", "Study Population", "Inclusion Criteria", "Exclusion Criteria",
        "Sample Size", "Sampling Technique", "Data Collection", "Variables Collected",
        "Investigations", "Study Procedure", "Outcome Measures", "Statistical Analysis",
        "Ethical Considerations", "Results", "Observations", "Discussion", "Conclusion",
        "Summary", "Recommendations", "Limitations", "Future Scope", "References",
        "Bibliography", "Appendices", "Proforma", "Patient Consent Form (English)",
        "Patient Consent Form (Hindi)"
    ) // Note: TOC, List of Tables/Figures/Abbreviations are auto-generated later

    private val autoGeneratedChapterHeadings = listOf(
        "Table of Contents",
        "List of Tables",
        "List of Figures",
        "List of Abbreviations",
        "List of References",
        "References",
        "Bibliography"
    )

    private val autoGeneratedChapterNames = autoGeneratedChapterHeadings
        .map { it.lowercase() }
        .toSet()

    private val methodologyFormChapterNames = setOf(
        "study design",
        "study setting",
        "study duration",
        "study population",
        "inclusion criteria",
        "exclusion criteria",
        "sample size",
        "sampling technique",
        "data collection",
        "variables collected",
        "study procedure",
        "outcome measures",
        "statistical analysis",
        "ethical considerations"
    )

    private val maxChapterGenerationAttempts = 3

    private fun initialChapterList(): List<Chapter> {
        val frontMatterInsertIndex = chapterHeadings.indexOf("Introduction")
            .takeIf { it >= 0 }
            ?: chapterHeadings.size
        val ordered = chapterHeadings.toMutableList()
        autoGeneratedChapterHeadings.asReversed().forEach { heading ->
            ordered.removeAll { it.equals(heading, ignoreCase = true) }
            ordered.add(frontMatterInsertIndex, heading)
        }
        return ordered.map { heading ->
            Chapter(
                name = heading,
                status = if (heading.lowercase() in autoGeneratedChapterNames) {
                    Chapter.ChapterStatus.PENDING
                } else {
                    Chapter.ChapterStatus.IDLE
                }
            )
        }
    }

    private val chapterVersions = mutableMapOf<String, MutableList<ChapterVersion>>()

    private val chapterVariableMap = mapOf(
        // Front matter
        "title" to listOf("Title", "Degree", "Department", "Institution", "Guide", "Co-guide", "Student Name", "Year", "Registration Number"),
        "abstract" to listOf("Abstract_structured", "Keywords"),
        "keywords" to listOf("Keywords"),

        // Introduction & background
        "introduction" to listOf("Introduction_text", "Background_text", "Literature_Review_text", "Research_Gap"),
        "background" to listOf("Background_text"),
        "disease burden" to listOf("Introduction_text", "Background_text", "Research_Gap", "References_Vancouver"),
        "epidemiology" to listOf("Introduction_text", "Background_text", "References_Vancouver"),
        "pathophysiology" to listOf("Introduction_text", "Background_text", "References_Vancouver"),
        "current treatment" to listOf("Introduction_text", "Background_text", "References_Vancouver"),
        "literature review" to listOf("Literature_Review_text", "Research_Gap", "References_Vancouver"),
        "research gap" to listOf("Research_Gap"),
        "need for study" to listOf("Research_Gap", "Aim_of_Study", "Objectives_primary", "References_Vancouver"),
        "aim of study" to listOf("Aim_of_Study"),
        "objectives" to listOf("Objectives_primary", "Objectives_secondary"),
        "hypothesis" to listOf("Hypothesis_null", "Hypothesis_alternate"),

        // Methodology
        "materials and methods" to listOf(
            "Study_Design", "Study_Setting", "Study_Duration", "Study_Population",
            "Inclusion_Criteria", "Exclusion_Criteria", "Sample_Size", "Sampling_Technique",
            "Data_Collection", "Variables_Collected", "Investigations", "Study_Procedure",
            "Outcome_Measures_primary", "Outcome_Measures_secondary", "Statistical_Analysis",
            "Ethical_Considerations"
        ),
        "study design" to listOf("Study_Design"),
        "study setting" to listOf("Study_Setting"),
        "study duration" to listOf("Study_Duration"),
        "study population" to listOf("Study_Population"),
        "inclusion criteria" to listOf("Inclusion_Criteria"),
        "exclusion criteria" to listOf("Exclusion_Criteria"),
        "sample size" to listOf("Sample_Size"),
        "sampling technique" to listOf("Sampling_Technique"),
        "data collection" to listOf("Data_Collection"),
        "variables collected" to listOf("Variables_Collected"),
        "investigations" to listOf("Investigations"),
        "study procedure" to listOf("Study_Procedure"),
        "outcome measures" to listOf("Outcome_Measures_primary", "Outcome_Measures_secondary"),
        "statistical analysis" to listOf("Statistical_Analysis"),
        "ethical considerations" to listOf("Ethical_Considerations"),

        // Results
        "results" to listOf("Results_text", "Observations", "Tables", "Figures"),
        "observations" to listOf("Observations"),

        // Discussion & conclusion
        "discussion" to listOf("Discussion_text", "Comparison_with_Literature", "Limitations"),
        "conclusion" to listOf("Conclusion_text"),
        "summary" to listOf("Summary"),
        "recommendations" to listOf("Recommendations"),
        "limitations" to listOf("Limitations"),
        "future scope" to listOf("Future_Scope"),

        // References & appendices
        "references" to listOf("References_Vancouver"),
        "bibliography" to listOf("References_Vancouver"),
        "appendices" to listOf("Appendices")
    )

    private data class ChapterSchema(
        val schemaDescription: String,   // JSON schema to embed in prompt
        val parser: (String) -> Any?,    // function to parse JSON into the specific data class
        val formatter: (Any) -> String   // convert parsed object to displayable text
    )

    private val chapterSchemas = mapOf(
        // ========== FRONT MATTER (custom structures) ==========
        "title" to ChapterSchema(
            schemaDescription = """
        {"title":"Full thesis title","subtitle":"Optional","author":"Candidate name","guide":"Guide name","coGuide":"Co-guide","institution":"Institution name","department":"Department","degree":"Degree (MD/MS/DM)","year":"Year"}
        """,
            parser = { json -> gson.fromJson(json, TitlePageJson::class.java) },
            formatter = { obj ->
                val t = obj as TitlePageJson
                buildString {
                    appendLine(t.title.uppercase())
                    t.subtitle?.let { appendLine(it) }
                    appendLine("\nBy")
                    appendLine(t.author)
                    appendLine("\nGuide: ${t.guide}")
                    t.coGuide?.let { appendLine("Co-guide: $it") }
                    appendLine("\n${t.department}")
                    appendLine(t.institution)
                    appendLine("\n${t.degree}")
                    appendLine(t.year)
                }
            }
        ),
        "certificate" to ChapterSchema(
            schemaDescription = """{"title":"CERTIFICATE","body":"...","guideSignature":"...","hodSignature":"...","date":"..."}""",
            parser = { json -> gson.fromJson(json, CertificateJson::class.java) },
            formatter = { obj ->
                val c = obj as CertificateJson
                buildString {
                    appendLine(c.title)
                    appendLine("\n${c.body}")
                    appendLine("\nGuide: ${c.guideSignature}")
                    appendLine("HOD: ${c.hodSignature}")
                    appendLine("Date: ${c.date}")
                }
            }
        ),
        "declaration" to ChapterSchema(
            schemaDescription = """{"statement":"...","studentName":"...","signature":"...","date":"..."}""",
            parser = { json -> gson.fromJson(json, DeclarationJson::class.java) },
            formatter = { obj ->
                val d = obj as DeclarationJson
                buildString {
                    appendLine("DECLARATION")
                    appendLine(d.statement)
                    appendLine("\n${d.studentName}")
                    appendLine(d.signature)
                    appendLine(d.date)
                }
            }
        ),
        "acknowledgements" to ChapterSchema(
            schemaDescription = """{"acknowledgements":["Thank you..."]}""",
            parser = { json -> gson.fromJson(json, AcknowledgementsJson::class.java) },
            formatter = { obj ->
                val a = obj as AcknowledgementsJson
                buildString {
                    appendLine("ACKNOWLEDGEMENTS")
                    a.acknowledgements.forEach { appendLine(it) }
                }
            }
        ),

        // ========== AUTO-GENERATED (TOC, lists) – will be overwritten later but schema exists ==========
        "table of contents" to ChapterSchema(
            schemaDescription = """{"entries":[{"title":"...","page":1}]}""",
            parser = { json -> gson.fromJson(json, TableOfContentsJson::class.java) },
            formatter = { obj ->
                val toc = obj as TableOfContentsJson
                buildString {
                    appendLine("TABLE OF CONTENTS")
                    toc.entries.forEach { appendLine("${it.title} .... ${it.page}") }
                }
            }
        ),
        "list of tables" to ChapterSchema(
            schemaDescription = """{"tables":[{"number":1,"title":"...","page":10}]}""",
            parser = { json -> gson.fromJson(json, ListOfTablesJson::class.java) },
            formatter = { obj ->
                val lot = obj as ListOfTablesJson
                buildString {
                    appendLine("LIST OF TABLES")
                    lot.tables.forEach { appendLine("Table ${it.number}: ${it.title} .... ${it.page}") }
                }
            }
        ),
        "list of figures" to ChapterSchema(
            schemaDescription = """{"figures":[{"number":1,"title":"...","page":15}]}""",
            parser = { json -> gson.fromJson(json, ListOfFiguresJson::class.java) },
            formatter = { obj ->
                val lof = obj as ListOfFiguresJson
                buildString {
                    appendLine("LIST OF FIGURES")
                    lof.figures.forEach { appendLine("Figure ${it.number}: ${it.title} .... ${it.page}") }
                }
            }
        ),
        "list of abbreviations" to ChapterSchema(
            schemaDescription = """{"abbreviations":[{"short":"BMI","full":"Body Mass Index"}]}""",
            parser = { json -> gson.fromJson(json, ListOfAbbreviationsJson::class.java) },
            formatter = { obj ->
                val loa = obj as ListOfAbbreviationsJson
                buildString {
                    appendLine("LIST OF ABBREVIATIONS")
                    loa.abbreviations.forEach { appendLine("${it.short} = ${it.full}") }
                }
            }
        ),

        // ========== ABSTRACT & KEYWORDS ==========
        "abstract" to ChapterSchema(
            schemaDescription = """
            {
              "background": "Brief clinical background and rationale (max 50 words)",
              "aim": "Primary study objective or aim (max 25 words)",
              "methods": "Study design, settings, sample size, primary interventions/measurements (max 75 words)",
              "results": "Key observation values, hazard ratios, p-values, major results (max 75 words)",
              "conclusion": "Key takeaway and clinical significance (max 25 words)",
              "keywords": ["keyword1", "keyword2", "keyword3"]
            }
            """.trimIndent(),
            parser = { json -> gson.fromJson(json, AbstractJson::class.java) },
            formatter = { obj ->
                val a = obj as AbstractJson
                val totalWords = (a.background.split(Regex("\\s+")).size +
                                  a.aim.split(Regex("\\s+")).size +
                                  a.methods.split(Regex("\\s+")).size +
                                  a.results.split(Regex("\\s+")).size +
                                  a.conclusion.split(Regex("\\s+")).size)
                buildString {
                    appendLine("ABSTRACT")
                    appendLine("\nBackground: ${a.background}")
                    appendLine("Aim: ${a.aim}")
                    appendLine("Methods: ${a.methods}")
                    appendLine("Results: ${a.results}")
                    appendLine("Conclusion: ${a.conclusion}")
                    appendLine("\nKeywords: ${a.keywords.joinToString(", ")}")
                    appendLine("\nTotal Abstract Word Count: $totalWords/250")
                    if (totalWords > 250) {
                        appendLine("⚠️ WARNING: Abstract exceeds the standard 250-word limit.")
                    }
                }
            }
        ),
        "keywords" to ChapterSchema(
            schemaDescription = """{"keywords":["keyword1","keyword2"]}""",
            parser = { json -> gson.fromJson(json, KeywordsJson::class.java) },
            formatter = { obj -> "KEYWORDS\n${(obj as KeywordsJson).keywords.joinToString(", ")}" }
        ),

        // ========== INTRODUCTION & BACKGROUND (generic text but with own schema entries) ==========
        "introduction" to professionalTextSchema(
            title = "INTRODUCTION",
            chapterType = "CHAPTER_1",
            sections = listOf("Background", "Problem Statement", "Need for the Study", "Aim", "Objectives", "Scope"),
            guidance = "Build the chapter from broad clinical context to the specific problem. Use a formal thesis tone and avoid filler text."
        ),
        "background" to professionalTextSchema(
            title = "BACKGROUND",
            chapterType = "CHAPTER_1",
            sections = listOf("Epidemiology", "Clinical Relevance", "Current Evidence", "Knowledge Gap"),
            guidance = "Write a clinically grounded background with a clear evidence trail and a polished academic flow."
        ),

        // ========== DISEASE BURDEN, EPIDEMIOLOGY, PATHOPHYSIOLOGY, TREATMENT, NEED ==========
        "disease burden" to professionalTextSchema(
            title = "DISEASE BURDEN",
            chapterType = "CHAPTER_1",
            sections = listOf(
                "Global Burden",
                "National Burden",
                "Local/Regional Burden",
                "Clinical Burden",
                "Public Health Impact",
                "Disability Adjusted Life Years (DALYs)",
                "Economic Burden",
                "Burden Relevance to Thesis"
            ),
            guidance = "Write a focused disease burden chapter covering magnitude of disease, prevalence, incidence, clinical burden, public health burden, disability/mortality, service burden, economic burden where supported, and local relevance to the thesis setting. Use verified PubMed abstracts and similar-article references when available. Do not invent statistics; if a statistic is not present in the source evidence, describe the burden qualitatively. End by linking the burden to why the present study is needed. Include at least one relevant figure (incidence trend, burden map, or disease pathway diagram). Include a detailed burden-magnitude-reference table with PMID-backed citations."
        ),
        "epidemiology" to professionalTextSchema(
            title = "EPIDEMIOLOGY",
            chapterType = "CHAPTER_1",
            sections = listOf(
                "Prevalence",
                "Incidence",
                "Age Distribution",
                "Sex Distribution",
                "Geographic Distribution",
                "Risk Groups",
                "Time Trends",
                "Epidemiological Determinants",
                "Local Epidemiological Data"
            ),
            guidance = "Write a focused epidemiology chapter covering prevalence, incidence, age and sex distribution, risk groups, geographic distribution, time trends, epidemiological determinants, and population factors relevant to the thesis topic. Use only PubMed-backed claims and cite every factual sentence. Include an epidemiology-focused figure (age-sex pyramid, trend chart, or distribution map) and an epidemiological summary table with prevalence/incidence data by region or population."
        ),
        "pathophysiology" to professionalTextSchema(
            title = "PATHOPHYSIOLOGY",
            chapterType = "CHAPTER_1",
            sections = listOf(
                "Disease Mechanism Overview",
                "Cellular and Molecular Basis",
                "Organ System Involvement",
                "Disease Progression",
                "Compensatory Mechanisms",
                "Pathophysiological Basis of Symptoms",
                "Clinical-Pathological Correlation"
            ),
            guidance = "Write a detailed pathophysiology chapter explaining the disease mechanism from molecular to clinical level. Cover cellular/molecular basis, organ system involvement, disease progression, compensatory mechanisms, and clinical-pathological correlation. Include a centered disease mechanism figure (pathway diagram, organ involvement schematic) with detailed caption. Include a pathophysiological mechanism-summary-reference table with PMID-backed citations. Use formal medical language."
        ),
        "current treatment" to professionalTextSchema(
            title = "CURRENT TREATMENT",
            chapterType = "CHAPTER_1",
            sections = listOf(
                "Medical Management",
                "Pharmacological Therapy",
                "Surgical/Interventional Options",
                "Treatment Guidelines",
                "Treatment Algorithms",
                "Novel/Experimental Therapies",
                "Treatment Outcomes and Prognosis"
            ),
            guidance = "Write a comprehensive current treatment chapter covering medical management, pharmacological therapy, surgical/interventional options, treatment guidelines, algorithms, novel therapies, and treatment outcomes. Include a treatment algorithm figure (flowchart) and a treatment-regimen-outcome-reference table with PMID-backed citations. Cite treatment guidelines where available (WHO, AHA, ATS, IDSA, etc.) and use PubMed-verified references. Cover standard of care as well as emerging therapies relevant to the thesis topic."
        ),
        "need for study" to professionalTextSchema(
            title = "NEED FOR STUDY",
            chapterType = "CHAPTER_2",
            sections = listOf(
                "Evidence Gap",
                "Clinical Relevance",
                "Public Health Significance",
                "Unanswered Questions",
                "Potential Impact of the Study",
                "Justification for the Current Research"
            ),
            guidance = "Write a persuasive need for study chapter that synthesizes the evidence gap, clinical relevance, public health significance, unanswered questions, potential impact, and justification for the current research. Connect the disease burden and gaps directly to the aims of this thesis. State clearly why this study is needed now and what it will contribute. Use citations for claims about gaps and significance."
        ),
        "literature review" to professionalTextSchema(
            title = "LITERATURE REVIEW",
            chapterType = "CHAPTER_2",
            sections = listOf(
                "Disease Definition",
                "Epidemiology",
                "Risk Factors",
                "Pathophysiology",
                "Types and Classification",
                "Investigations in Literature",
                "Relation of Investigations with Disease",
                "Key Study Summary and Research Gap"
            ),
            guidance = "Write a detailed disease-focused review with disease definition, epidemiology, risk factors, pathophysiology, types/classification where present, investigations, and relation of investigations with the disease. Add required figures for epidemiology, risk factors, pathophysiology, and investigations. Cite every factual point with PubMed PMID-backed Vancouver references directly related to the thesis title/topic."
        ),
        "research gap" to professionalTextSchema(
            title = "RESEARCH GAP",
            chapterType = "CHAPTER_2",
            sections = listOf("What is known", "What is missing", "Why this study is needed"),
            guidance = "State the gap crisply and justify the thesis in academically defensible terms."
        ),
        "aim of study" to professionalTextSchema(
            title = "AIM OF STUDY",
            chapterType = "CHAPTER_2",
            sections = listOf("Aim", "Clinical Rationale"),
            guidance = "Write one precise aim statement followed by a brief rationale."
        ),
        "objectives" to professionalTextSchema(
            title = "OBJECTIVES",
            chapterType = "CHAPTER_2",
            sections = listOf("Primary Objective", "Secondary Objectives"),
            guidance = "List measurable, specific objectives. Keep them numbered and unambiguous."
        ),

        // ========== HYPOTHESIS ==========
        "hypothesis" to ChapterSchema(
            schemaDescription = """{"nullHypothesis":"...","alternateHypothesis":"..."}""",
            parser = { json -> gson.fromJson(json, HypothesisJson::class.java) },
            formatter = { obj ->
                val h = obj as HypothesisJson
                buildString {
                    appendLine("HYPOTHESIS")
                    appendLine("Null: ${h.nullHypothesis}")
                    appendLine("Alternate: ${h.alternateHypothesis}")
                }
            }
        ),

        // ========== METHODOLOGY (structured) ==========
        "materials and methods" to ChapterSchema(
            schemaDescription = """
            {
              "designType": "Study design type (e.g. Randomized Controlled Trial, Prospective Cohort, Cross-Sectional)",
              "settings": {
                "hospital": "Name of the hospital/institution where conducted",
                "department": "Name of the clinical department",
                "details": "Other setting details"
              },
              "inclusionCriteria": [
                "Detailed inclusion condition 1",
                "Detailed inclusion condition 2"
              ],
              "exclusionCriteria": [
                "Detailed exclusion condition 1",
                "Detailed exclusion condition 2"
              ],
              "sampleSize": {
                "formula": "The specific statistical formula used (e.g., n = Z^2*p*q/d^2)",
                "assumptions": "Underlying statistical assumptions",
                "power": 0.80,
                "confidenceInterval": 0.95,
                "calculatedSize": 120
              },
              "statisticalAnalysis": [
                "Descriptive stats description",
                "Specific inferential tests used (e.g. Chi-Square, Student's t-test) and significance levels"
              ]
            }
            """.trimIndent(),
            parser = { json -> gson.fromJson(json, MethodologyJson::class.java) },
            formatter = { obj ->
                when (obj) {
                    is MethodologyJson -> formatMethodologyPreview(obj)
                    is ThesisChapterJson -> formatChapterPreview(obj)
                    else -> obj.toString()
                }
            }
        ),
        "study design" to professionalTextSchema(
            title = "STUDY DESIGN",
            chapterType = "CHAPTER_3",
            sections = listOf("Design Overview", "Design Rationale", "Study Flow"),
            guidance = "Describe the design precisely and keep the narrative reproducible and formal."
        ),
        "study setting" to professionalTextSchema(
            title = "STUDY SETTING",
            chapterType = "CHAPTER_3",
            sections = listOf("Institution", "Department", "Setting Description"),
            guidance = "Describe the hospital/department setting in a way suitable for a thesis methods chapter."
        ),
        "study duration" to professionalTextSchema(
            title = "STUDY DURATION",
            chapterType = "CHAPTER_3",
            sections = listOf("Start Date", "End Date", "Total Duration"),
            guidance = "State dates and duration clearly and formally."
        ),
        "study population" to professionalTextSchema(
            title = "STUDY POPULATION",
            chapterType = "CHAPTER_3",
            sections = listOf("Target Population", "Source Population", "Eligibility Overview"),
            guidance = "Define the study population and the clinical context precisely."
        ),
        "inclusion criteria" to professionalTextSchema(
            title = "INCLUSION CRITERIA",
            chapterType = "CHAPTER_3",
            sections = listOf("Inclusion Criteria"),
            guidance = "List inclusion criteria as concise numbered or bulleted statements."
        ),
        "exclusion criteria" to professionalTextSchema(
            title = "EXCLUSION CRITERIA",
            chapterType = "CHAPTER_3",
            sections = listOf("Exclusion Criteria"),
            guidance = "List exclusion criteria as concise numbered or bulleted statements."
        ),
        "sample size" to professionalTextSchema(
            title = "SAMPLE SIZE",
            chapterType = "CHAPTER_3",
            sections = listOf("Sample Size Calculation", "Assumptions", "Final Sample Size"),
            guidance = "Explain the formula, assumptions, and final sample size in a thesis-appropriate way."
        ),
        "sampling technique" to professionalTextSchema(
            title = "SAMPLING TECHNIQUE",
            chapterType = "CHAPTER_3",
            sections = listOf("Sampling Method", "Selection Process", "Rationale"),
            guidance = "Describe the sampling approach and why it is appropriate."
        ),
        "data collection" to professionalTextSchema(
            title = "DATA COLLECTION",
            chapterType = "CHAPTER_3",
            sections = listOf("Data Sources", "Data Collection Procedure", "Quality Control"),
            guidance = "Detail the acquisition process and how consistency was maintained."
        ),
        "variables collected" to professionalTextSchema(
            title = "VARIABLES COLLECTED",
            chapterType = "CHAPTER_3",
            sections = listOf("Independent Variables", "Dependent Variables", "Confounders"),
            guidance = "Define the variables clearly and keep the taxonomy clinically sensible."
        ),
        "investigations" to professionalTextSchema(
            title = "INVESTIGATIONS",
            chapterType = "CHAPTER_3",
            sections = listOf(
                "Brief Overview",
                "Clinical Examination and Bedside Assessment",
                "Laboratory Investigations",
                "Imaging Investigations",
                "Device-Based and Special Investigations",
                "Diagnostic Workflow",
                "Relation of Investigations with Disease",
                "Evidence from Literature"
            ),
            guidance = "Start with a brief overview of why investigations are needed for the disease, then describe clinical, laboratory, imaging, device-based, special, scoring, histopathology, microbiology, genetic, or functional investigations as applicable. Explain relation to diagnosis, severity, staging, prognosis, treatment response, and follow-up. Include a centered diagnostic/device/workflow figure, a detailed investigation-purpose-interpretation-reference table, and PubMed PMID-backed references directly related to the thesis title/topic."
        ),
        "study procedure" to professionalTextSchema(
            title = "STUDY PROCEDURE",
            chapterType = "CHAPTER_3",
            sections = listOf("Screening", "Enrollment", "Intervention/Observation", "Follow-up", "Data Recording"),
            guidance = "Present the procedure step by step, with the flow of the study easy to follow."
        ),
        "outcome measures" to professionalTextSchema(
            title = "OUTCOME MEASURES",
            chapterType = "CHAPTER_3",
            sections = listOf("Primary Outcome", "Secondary Outcomes", "Measurement Time Points"),
            guidance = "Define outcomes with enough precision for later results reporting."
        ),
        "statistical analysis" to professionalTextSchema(
            title = "STATISTICAL ANALYSIS",
            chapterType = "CHAPTER_3",
            sections = listOf("Software", "Descriptive Statistics", "Inferential Tests", "Significance Threshold"),
            guidance = "Write the statistical plan in formal thesis style, with clear test selection and significance thresholds."
        ),
        "ethical considerations" to professionalTextSchema(
            title = "ETHICAL CONSIDERATIONS",
            chapterType = "CHAPTER_3",
            sections = listOf("Ethics Approval", "Informed Consent", "Confidentiality", "Risk/Benefit Statement"),
            guidance = "State ethics and consent details in a formal, concise, academically acceptable way."
        ),

        // ========== RESULTS (with charts & tables) ==========
        "results" to ChapterSchema(
            schemaDescription = """
        {
          "sections":[
            {
              "heading":"...",
              "content":"...",
              "observations":["..."]
            }
          ],
          "tables":[
            {
              "title":"Table title",
              "headers":["Column 1","Column 2"],
              "rows":[["Value 1","Value 2"]],
              "data":[{"Column 1":"Value 1","Column 2":"Value 2"}]
            }
          ],
          "charts":[
            // Single-series only. Do not use map/object data or multi-series rows.
            {
              "title":"Chart title",
              "type":"pie",
              "chart_template":"pie_share",
              "labels":["A","B"],
              "values":[10,20],
              "data":[{"label":"A","value":10},{"label":"B","value":20}]
            }
          ]
        }
        """,
            parser = { json -> gson.fromJson(json, ResultsJson::class.java) },
            formatter = { obj ->
                val r = obj as ResultsJson
                buildString {
                    appendLine("RESULTS")
                    r.sections.forEach { sec ->
                        appendLine("\n${sec.heading}")
                        appendLine(sec.content)
                        sec.observations?.forEach { appendLine("• $it") }
                    }
                    if (r.tables.isNotEmpty()) appendLine("\n[TABLES: ${r.tables.size}]")
                    if (r.charts.isNotEmpty()) appendLine("[CHARTS: ${r.charts.size}]")
                }
            }
        ),
        "observations" to professionalTextSchema(
            title = "OBSERVATIONS",
            chapterType = "CHAPTER_4",
            sections = listOf("Observation Summary", "Trend Analysis", "Key Notes"),
            guidance = "Write objective observations with a clean thesis style and enough detail to support the results chapter."
        ),

        // ========== DISCUSSION (structured) ==========
        "discussion" to ChapterSchema(
            schemaDescription = """
            {
              "keyFindings": "Detailed summary of the key findings of this study",
              "comparisonWithLiterature": [
                {
                  "finding": "Specific study finding / endpoint observation",
                  "citationReference": "Vancouver citation string [1]",
                  "comparison": "Detailed comparison detailing concordance/discordance with published literature"
                }
              ],
              "limitations": [
                "Detailed limitation 1",
                "Detailed limitation 2"
              ],
              "clinicalImplications": "Clinical value and utility of the observations",
              "futureDirections": [
                "Recommended future research avenue 1",
                "Recommended future research avenue 2"
              ]
            }
            """.trimIndent(),
            parser = { json -> gson.fromJson(json, DiscussionJson::class.java) },
            formatter = { obj ->
                when (obj) {
                    is DiscussionJson -> formatDiscussionPreview(obj)
                    is ThesisChapterJson -> formatChapterPreview(obj)
                    else -> obj.toString()
                }
            }
        ),
        "conclusion" to professionalTextSchema(
            title = "CONCLUSION",
            chapterType = "CHAPTER_6",
            sections = listOf("Key Findings", "Clinical Relevance", "Final Conclusion"),
            guidance = "Write a concise conclusion that restates the thesis message without introducing new data."
        ),
        "summary" to professionalTextSchema(
            title = "SUMMARY",
            chapterType = "CHAPTER_6",
            sections = listOf("Thesis Summary", "Overall Message"),
            guidance = "Provide a short but polished summary of the thesis."
        ),
        "recommendations" to professionalTextSchema(
            title = "RECOMMENDATIONS",
            chapterType = "CHAPTER_6",
            sections = listOf("Clinical Recommendations", "Future Research", "Practice Implications"),
            guidance = "Offer evidence-based recommendations that follow logically from the study."
        ),
        "limitations" to professionalTextSchema(
            title = "LIMITATIONS",
            chapterType = "CHAPTER_6",
            sections = listOf("Study Limitations"),
            guidance = "State limitations honestly and professionally, without self-critique or overstatement."
        ),
        "future scope" to professionalTextSchema(
            title = "FUTURE SCOPE",
            chapterType = "CHAPTER_6",
            sections = listOf("Future Research Directions", "Potential Applications"),
            guidance = "Identify the next logical research steps and practical extensions."
        ),

        // ========== REFERENCES & BIBLIOGRAPHY ==========
        "references" to ChapterSchema(
            schemaDescription = """{"references":[{"number":1,"text":"Author AA, Author BB. Complete disease-related article title. Journal Name. 2020;12(3):123-130. PMID: 12345678. DOI: 10.xxxx/xxxxx","pmid":"12345678","doi":"10.xxxx/xxxxx"}]}""",
            parser = { json -> gson.fromJson(json, ReferencesJson::class.java) },
            formatter = { obj ->
                val refs = obj as ReferencesJson
                buildString {
                    appendLine("REFERENCES")
                    refs.references.forEach { appendLine("${it.number}. ${it.text.completeCitationText(it.pmid, it.doi)}") }
                }
            }
        ),
        "bibliography" to ChapterSchema(
            schemaDescription = """{"references":[{"number":1,"text":"Author AA, Author BB. Complete disease-related article title. Journal Name. 2020;12(3):123-130. PMID: 12345678. DOI: 10.xxxx/xxxxx","pmid":"12345678","doi":"10.xxxx/xxxxx"}]}""",
            parser = { json -> gson.fromJson(json, ReferencesJson::class.java) },
            formatter = { obj ->
                val bib = obj as ReferencesJson
                buildString {
                    appendLine("BIBLIOGRAPHY")
                    bib.references.forEach { appendLine("${it.number}. ${it.text.completeCitationText(it.pmid, it.doi)}") }
                }
            }
        ),

        // ========== APPENDICES ==========
        "appendices" to ChapterSchema(
            schemaDescription = """{"appendices":[{"title":"...","content":"..."}]}""",
            parser = { json -> gson.fromJson(json, AppendicesJson::class.java) },
            formatter = { obj ->
                val app = obj as AppendicesJson
                buildString {
                    appendLine("APPENDICES")
                    app.appendices.forEach { appendLine("${it.title}\n${it.content}\n") }
                }
            }
        ),

        // ========== PROFORMA ==========
        "proforma" to ChapterSchema(
            schemaDescription = """{"patientName":"","age":"","sex":"","opdIpNo":"","address":"","history":"","examination":"","investigations":"","diagnosis":""}""",
            parser = { json -> gson.fromJson(json, ProformaJson::class.java) },
            formatter = { obj ->
                val p = obj as ProformaJson
                buildString {
                    appendLine("PROFORMA")
                    appendLine("Patient Name: ${p.patientName}")
                    appendLine("Age: ${p.age}")
                    appendLine("Sex: ${p.sex}")
                    appendLine("OPD/IP No: ${p.opdIpNo}")
                    appendLine("Address: ${p.address}")
                    appendLine("History: ${p.history}")
                    appendLine("Examination: ${p.examination}")
                    appendLine("Investigations: ${p.investigations}")
                    appendLine("Diagnosis: ${p.diagnosis}")
                }
            }
        ),

        // ========== CONSENT FORMS ==========
        "patient consent form (english)" to consentSchema("ENGLISH"),
        "patient consent form (hindi)" to consentSchema("HINDI")
    )
    private fun professionalTextSchema(
        title: String,
        chapterType: String,
        sections: List<String>,
        guidance: String,
        includeFigures: Boolean = false,
        includeCharts: Boolean = false,
        includeTables: Boolean = false,
        includeAbbreviations: Boolean = true,
        includeReferences: Boolean = true
    ): ChapterSchema {
        val sectionObjects = sections.joinToString(",\n") { section ->
            """        {"heading":"$section","content":"short section summary [1]","paragraphs":["Paragraph 1 with inline citation [1]","Paragraph 2 with inline citation [2]"],"bullets":["... [1]"],"numbered_points":["... [1]"],"subsections":[{"heading":"...","content":"... [1]"}],"table":{"table_number":"T1","title":"...","headers":["..."],"rows":[["... [1]"]]},"figures":[{"figure_number":"1","title":"...","caption":"...","image_search_query":"..."}],"references":[{"citation":"[1]","reference_text":"Author AA, Author BB. Complete disease-related article title. Journal Name. 2020;12(3):123-130. PMID: 12345678. DOI: 10.xxxx/xxxxx","pmid":"12345678","doi":"10.xxxx/xxxxx","pubmed_verified":true}]}"""
        }

        val tableBlock = if (includeTables) """
      "tables": [
        {"table_number":"T1","title":"...","headers":["..."],"rows":[["..."]],"data":[{"...":"..."}],"footnote":"..."}
      ],
""" else ""
        val figureBlock = if (includeFigures) """
      "figures": [],
""" else """      "figures": [],
"""
        val chartBlock = if (includeCharts) """
      "charts": [
        {"chart_id":"chart_1","title":"...","type":"bar","chart_template":"category_bar","labels":["..."],"values":[1],"data":[{"label":"...","value":1}],"datasets":[]}
      ],
""" else """      "charts": [],
"""
        val abbreviationBlock = if (includeAbbreviations) """
      "abbreviations": [],
""" else ""
        val referenceBlock = if (includeReferences) """
      "chapter_references": [{"citation":"[1]","reference_text":"Author AA, Author BB. Complete disease-related article title. Journal Name. 2020;12(3):123-130. PMID: 12345678. DOI: 10.xxxx/xxxxx","pmid":"12345678","doi":"10.xxxx/xxxxx","pubmed_verified":true}]
""" else ""

        val schema = """
    {
      "chapter_name": "$title",
      "chapter_type": "$chapterType",
      "sections": [
$sectionObjects
      ],
$tableBlock$figureBlock$chartBlock$abbreviationBlock$referenceBlock
    }
    """.trimIndent()

        return ChapterSchema(
            schemaDescription = schema,
            parser = { json -> parseThesisChapterJson(json, title) },
            formatter = { obj -> formatChapterPreview(obj as ThesisChapterJson) }
        )
    }

    private fun consentSchema(language: String): ChapterSchema = ChapterSchema(
        schemaDescription = """{"title":"Consent Form","introduction":"...","procedure":"...","risks":"...","benefits":"...","confidentiality":"...","signatureLine":"___________________","date":""}""",
        parser = { json -> gson.fromJson(json, ConsentFormJson::class.java) },
        formatter = { obj ->
            val cf = obj as ConsentFormJson
            buildString {
                appendLine("PATIENT CONSENT FORM ($language)")
                appendLine("\n${cf.title}")
                appendLine("\nINTRODUCTION\n${cf.introduction}")
                appendLine("\nPROCEDURE\n${cf.procedure}")
                appendLine("\nRISKS\n${cf.risks}")
                appendLine("\nBENEFITS\n${cf.benefits}")
                appendLine("\nCONFIDENTIALITY\n${cf.confidentiality}")
                appendLine("\nSignature: ${cf.signatureLine}")
                appendLine("Date: ${cf.date}")
            }
        }
    )

    private fun getVariablesForChapter(chapterName: String, allVariables: List<Variable>): List<Variable> {
        val normalizedPatterns = (chapterVariableMap[chapterName.lowercase()]
            ?: chapterVariableGroups(chapterName).flatMap { it.keys })
            .map(::normalizeVariableKey)
            .filter { it.isNotBlank() }

        if (normalizedPatterns.isEmpty()) return allVariables

        val matched = allVariables.filter { variable ->
            val normalizedName = normalizeVariableKey(variable.name)
            normalizedPatterns.any { pattern ->
                normalizedName == pattern ||
                    normalizedName.contains(pattern) ||
                    pattern.contains(normalizedName)
            }
        }

        return if (matched.isNotEmpty()) matched else allVariables
    }

    data class ChapterVersion(
        val versionNo: Int,
        val content: String,
        val rawJson: String,
        val timestamp: Long = System.currentTimeMillis()
    )

    private fun newSessionId(): String =
        "thesis_${System.currentTimeMillis()}_${UUID.randomUUID().toString().take(8)}"

    private fun getUid(): String? = FirebaseAuth.getInstance().currentUser?.uid

    fun setPdfUri(uri: Uri) {
        _uiState.update { it.copy(pdfUri = uri) }
        saveSessionToFirebase()
    }

    fun setCollegeLogoUri(uri: String) {
        _uiState.update { it.copy(collegeLogoUri = uri) }
        saveSessionToFirebase()
    }

    fun clearCollegeLogo() {
        _uiState.update { it.copy(collegeLogoUri = "") }
        saveSessionToFirebase()
    }

    fun setPdfTheme(theme: PdfTheme) {
        _uiState.update { it.copy(pdfTheme = theme.name) }
        saveSessionToFirebase()
    }

    fun setPdfThemeSelection(selection: String) {
        _uiState.update { it.copy(pdfTheme = selection.ifBlank { PdfTheme.CLASSIC.name }) }
        saveSessionToFirebase()
    }

    fun setExportMargin(value: String) {
        _uiState.update { it.copy(exportMargin = value.ifBlank { "normal" }) }
        saveSessionToFirebase()
    }

    fun setExportFont(value: String) {
        _uiState.update { it.copy(exportFont = value.ifBlank { "serif" }) }
        saveSessionToFirebase()
    }

    fun setExportLineSpacing(value: String) {
        _uiState.update { it.copy(exportLineSpacing = value.ifBlank { "normal" }) }
        saveSessionToFirebase()
    }

    fun setExportLogoPlacement(value: String) {
        _uiState.update { it.copy(exportLogoPlacement = value.ifBlank { "theme" }) }
        saveSessionToFirebase()
    }

    fun setExportPageNumbering(value: String) {
        _uiState.update { it.copy(exportPageNumbering = value.ifBlank { "theme" }) }
        saveSessionToFirebase()
    }

    fun setExportHeaderFooter(enabled: Boolean) {
        _uiState.update { it.copy(exportHeaderFooter = enabled) }
        saveSessionToFirebase()
    }

    fun setExportWatermark(enabled: Boolean) {
        _uiState.update { it.copy(exportWatermark = enabled) }
        saveSessionToFirebase()
    }

    fun setExportAutoToc(enabled: Boolean) {
        _uiState.update { it.copy(exportAutoToc = enabled) }
        saveSessionToFirebase()
    }

    fun setExportAutoLists(enabled: Boolean) {
        _uiState.update { it.copy(exportAutoLists = enabled) }
        saveSessionToFirebase()
    }

    fun setPromptSectionSplittingEnabled(enabled: Boolean) {
        _uiState.update { it.copy(promptSectionSplittingEnabled = enabled) }
        saveSessionToFirebase()
        refreshWorkerPromptsForCurrentSettings()
    }

    fun setPromptMaxChars(value: Int) {
        _uiState.update { it.copy(promptMaxChars = value.coerceIn(4000, 30000)) }
        saveSessionToFirebase()
        refreshWorkerPromptsForCurrentSettings()
    }

    fun generateMasterChartTemplate() {
        viewModelScope.launch(Dispatchers.Default) {
            val state = _uiState.value
            if (state.variables.isEmpty() && state.chapters.none { it.status == Chapter.ChapterStatus.SUCCESS }) {
                _uiState.update { it.copy(status = "Generate or load thesis variables before creating master chart") }
                return@launch
            }
            val columns = buildMasterChartColumns(state)
            val csv = buildMasterChartCsv(columns)
            _uiState.update {
                it.copy(
                    masterChartColumns = columns,
                    masterChartCsv = csv,
                    masterChartGeneratedAt = System.currentTimeMillis(),
                    status = "Master chart template generated with ${columns.size} variables"
                )
            }
            saveSessionToFirebase()
        }
    }

    fun importMasterData(context: Context, uri: Uri) {
        viewModelScope.launch {
            _uiState.update { it.copy(status = "Importing master data...") }
            val imported = runCatching {
                withContext(Dispatchers.IO) { readMasterDataFile(context, uri) }
            }.getOrElse { error ->
                Log.e("ThesisViewModel", "Failed to import master data", error)
                _uiState.update { it.copy(status = "Master data import failed: ${error.message ?: "Unknown error"}") }
                return@launch
            }

            if (imported.headers.isEmpty() || imported.rows.isEmpty()) {
                _uiState.update { it.copy(status = "Master data import failed: no header row or data rows found") }
                return@launch
            }

            withContext(Dispatchers.Default) {
                val snapshot = _uiState.value
                val columns = snapshot.masterChartColumns.ifEmpty { buildMasterChartColumns(snapshot) }
                val csv = snapshot.masterChartCsv.ifBlank { buildMasterChartCsv(columns) }
                val rowsForSession = imported.rows.take(5000)
                val mappings = buildMasterDataMappings(imported.headers, columns)
                val validationIssues = validateMasterDataRows(rowsForSession, imported.headers, mappings, columns)
                val resultTables = buildMasterDataResultTables(rowsForSession, imported.headers, mappings, columns)
                val updatedChapters = buildChaptersWithMasterDataResults(
                    state = snapshot,
                    fileName = imported.fileName,
                    rowCount = rowsForSession.size,
                    validationIssues = validationIssues,
                    resultTables = resultTables
                )
                val truncated = imported.rows.size > rowsForSession.size
                _uiState.update {
                    it.copy(
                        masterChartColumns = columns,
                        masterChartCsv = csv,
                        masterChartGeneratedAt = if (it.masterChartGeneratedAt > 0L) it.masterChartGeneratedAt else System.currentTimeMillis(),
                        masterDataFileName = imported.fileName,
                        masterDataHeaders = imported.headers,
                        masterDataRows = rowsForSession,
                        masterDataMappings = mappings,
                        masterDataValidationIssues = validationIssues,
                        masterDataResultTables = resultTables,
                        masterDataImportedAt = System.currentTimeMillis(),
                        chapters = updatedChapters,
                        status = buildString {
                            append("Imported ${rowsForSession.size} rows from ${imported.fileName}. ")
                            append("Mapped ${mappings.count { map -> map.targetColumn.isNotBlank() }} columns, ")
                            append("found ${validationIssues.size} validation issues, generated ${resultTables.size} result tables.")
                            if (truncated) append(" Large file was limited to first ${rowsForSession.size} rows for session sync.")
                        }
                    )
                }
                saveSessionToFirebase()
            }
        }
    }

    private data class ImportedMasterData(
        val fileName: String,
        val headers: List<String>,
        val rows: List<List<String>>
    )

    private fun readMasterDataFile(context: Context, uri: Uri): ImportedMasterData {
        val fileName = resolveMasterDataFileName(context, uri)
        val rawRows = context.contentResolver.openInputStream(uri)?.use { input ->
            if (fileName.endsWith(".xlsx", ignoreCase = true) || fileName.endsWith(".xlsm", ignoreCase = true) || fileName.endsWith(".xls", ignoreCase = true)) {
                parseWorkbookRows(input)
            } else {
                parseCsvRows(input.bufferedReader().use { it.readText() })
            }
        }.orEmpty()

        val usefulRows = rawRows
            .map { row -> row.map { it.trim() } }
            .filter { row -> row.any { it.isNotBlank() } }
        val headers = usefulRows.firstOrNull()
            ?.mapIndexed { index, header -> header.ifBlank { "column_${index + 1}" } }
            .orEmpty()
        val rows = usefulRows.drop(1)
            .map { row ->
                List(headers.size) { index -> row.getOrNull(index).orEmpty() }
            }
            .filter { row -> row.any { it.isNotBlank() } }
        return ImportedMasterData(fileName, headers, rows)
    }

    private fun resolveMasterDataFileName(context: Context, uri: Uri): String {
        val queried = runCatching {
            context.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { cursor ->
                if (cursor.moveToFirst()) {
                    val index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                    if (index >= 0) cursor.getString(index) else null
                } else {
                    null
                }
            }
        }.getOrNull()
        return queried?.takeIf { it.isNotBlank() } ?: uri.lastPathSegment?.substringAfterLast('/') ?: "master_data.csv"
    }

    private fun parseWorkbookRows(input: java.io.InputStream): List<List<String>> {
        val formatter = DataFormatter()
        WorkbookFactory.create(input).use { workbook ->
            val sheet = workbook.getSheetAt(0) ?: return emptyList()
            var maxColumns = 0
            for (rowIndex in sheet.firstRowNum..sheet.lastRowNum) {
                val row = sheet.getRow(rowIndex) ?: continue
                maxColumns = maxOf(maxColumns, row.lastCellNum.toInt().coerceAtLeast(0))
            }
            if (maxColumns == 0) return emptyList()
            return (sheet.firstRowNum..sheet.lastRowNum).mapNotNull { rowIndex ->
                val row = sheet.getRow(rowIndex) ?: return@mapNotNull null
                List(maxColumns) { cellIndex ->
                    formatter.formatCellValue(row.getCell(cellIndex)).trim()
                }
            }
        }
    }

    private fun parseCsvRows(text: String): List<List<String>> {
        val rows = mutableListOf<MutableList<String>>()
        var row = mutableListOf<String>()
        val cell = StringBuilder()
        var inQuotes = false
        var index = 0
        while (index < text.length) {
            val ch = text[index]
            when {
                ch == '"' && inQuotes && index + 1 < text.length && text[index + 1] == '"' -> {
                    cell.append('"')
                    index++
                }
                ch == '"' -> inQuotes = !inQuotes
                ch == ',' && !inQuotes -> {
                    row.add(cell.toString())
                    cell.clear()
                }
                (ch == '\n' || ch == '\r') && !inQuotes -> {
                    if (ch == '\r' && index + 1 < text.length && text[index + 1] == '\n') index++
                    row.add(cell.toString())
                    cell.clear()
                    rows.add(row)
                    row = mutableListOf()
                }
                else -> cell.append(ch)
            }
            index++
        }
        row.add(cell.toString())
        if (row.any { it.isNotBlank() }) rows.add(row)
        return rows
    }

    private fun buildMasterDataMappings(
        headers: List<String>,
        columns: List<MasterChartColumnJson>
    ): List<MasterChartColumnMappingJson> {
        return headers.map { header ->
            val best = columns
                .map { column -> column to masterDataMappingScore(header, column) }
                .maxByOrNull { it.second }
            val score = best?.second ?: 0.0
            val target = if (score >= 0.42) best?.first?.columnName.orEmpty() else ""
            MasterChartColumnMappingJson(
                sourceHeader = header,
                targetColumn = target,
                confidence = String.format(java.util.Locale.US, "%.2f", score).toDoubleOrNull() ?: score,
                status = when {
                    target.isBlank() -> "unmapped"
                    score >= 0.72 -> "mapped"
                    else -> "review"
                }
            )
        }
    }

    private fun masterDataMappingScore(header: String, column: MasterChartColumnJson): Double {
        val source = normalizeMasterDataName(header)
        val target = normalizeMasterDataName(column.columnName)
        val display = normalizeMasterDataName(column.displayName)
        if (source.isBlank()) return 0.0
        if (source == target || source == display) return 1.0
        if (target.contains(source) || source.contains(target) || display.contains(source) || source.contains(display)) return 0.86
        val sourceTokens = source.split("_").filter { it.isNotBlank() }.toSet()
        val targetTokens = (target.split("_") + display.split("_")).filter { it.isNotBlank() }.toSet()
        if (sourceTokens.isEmpty() || targetTokens.isEmpty()) return 0.0
        val overlap = sourceTokens.intersect(targetTokens).size.toDouble()
        val union = sourceTokens.union(targetTokens).size.toDouble().coerceAtLeast(1.0)
        var score = overlap / union
        if (sourceTokens.any { it in setOf("sex", "gender") } && targetTokens.any { it in setOf("sex", "gender") }) score += 0.35
        if (sourceTokens.any { it in setOf("id", "case", "serial", "sr") } && targetTokens.any { it in setOf("id", "case", "serial", "number") }) score += 0.25
        return score.coerceIn(0.0, 1.0)
    }

    private fun normalizeMasterDataName(value: String): String {
        return value.lowercase()
            .replace("patient", "case")
            .replace("gender", "sex")
            .replace("sr no", "serial number")
            .replace(Regex("""\([^)]*\)"""), "")
            .replace(Regex("""[^a-z0-9]+"""), "_")
            .trim('_')
    }

    private fun validateMasterDataRows(
        rows: List<List<String>>,
        headers: List<String>,
        mappings: List<MasterChartColumnMappingJson>,
        columns: List<MasterChartColumnJson>
    ): List<MasterChartValidationIssueJson> {
        val issues = mutableListOf<MasterChartValidationIssueJson>()
        val columnsByName = columns.associateBy { it.columnName }
        val mappedByTarget = mappings.filter { it.targetColumn.isNotBlank() }.associateBy { it.targetColumn }
        val usedTargets = mappedByTarget.keys
        listOf("case_id", "serial_number").forEach { required ->
            if (required !in usedTargets) {
                issues += MasterChartValidationIssueJson(
                    rowNumber = 0,
                    columnName = required,
                    issue = "Required master chart column is not mapped from uploaded data",
                    severity = "error"
                )
            }
        }

        val caseIdMapping = mappedByTarget["case_id"]
        val seenCaseIds = mutableSetOf<String>()
        rows.forEachIndexed { rowIndex, row ->
            mappings.forEachIndexed { headerIndex, mapping ->
                if (mapping.targetColumn.isBlank()) return@forEachIndexed
                val column = columnsByName[mapping.targetColumn] ?: return@forEachIndexed
                val value = row.getOrNull(headerIndex).orEmpty().trim()
                val rowNumber = rowIndex + 2
                val isRequiredRole = column.role in setOf("identifier", "outcome") || column.columnName in setOf("age", "sex")
                if (value.isBlank() && isRequiredRole) {
                    issues += MasterChartValidationIssueJson(
                        rowNumber = rowNumber,
                        columnName = mapping.sourceHeader,
                        issue = "Missing value for ${column.displayName.ifBlank { column.columnName }}",
                        severity = if (column.role == "identifier") "error" else "warning"
                    )
                    return@forEachIndexed
                }
                if (value.isBlank()) return@forEachIndexed
                if (column.dataType.contains("numeric", ignoreCase = true) || column.dataType.contains("integer", ignoreCase = true)) {
                    val numeric = value.replace(",", "").toDoubleOrNull()
                    if (numeric == null) {
                        issues += MasterChartValidationIssueJson(rowNumber, mapping.sourceHeader, value, "Expected numeric value", "error")
                    }
                }
                val allowed = column.allowedValues
                    .split(";", ",", "|")
                    .map { it.trim() }
                    .filter { it.isNotBlank() }
                if (allowed.isNotEmpty() && allowed.none { it.equals(value, ignoreCase = true) }) {
                    issues += MasterChartValidationIssueJson(
                        rowNumber = rowNumber,
                        columnName = mapping.sourceHeader,
                        value = value,
                        issue = "Value is outside allowed set: ${allowed.joinToString("; ")}",
                        severity = "warning"
                    )
                }
            }
            caseIdMapping?.let { mapping ->
                val caseIndex = headers.indexOf(mapping.sourceHeader)
                val caseId = row.getOrNull(caseIndex).orEmpty().trim()
                if (caseId.isNotBlank() && !seenCaseIds.add(caseId.lowercase())) {
                    issues += MasterChartValidationIssueJson(rowIndex + 2, mapping.sourceHeader, caseId, "Duplicate case ID", "error")
                }
            }
        }
        return issues.take(300)
    }

    private fun buildMasterDataResultTables(
        rows: List<List<String>>,
        headers: List<String>,
        mappings: List<MasterChartColumnMappingJson>,
        columns: List<MasterChartColumnJson>
    ): List<MasterChartResultSummaryJson> {
        val columnsByName = columns.associateBy { it.columnName }
        val resultTables = mutableListOf<MasterChartResultSummaryJson>()
        val numericRows = mutableListOf<List<String>>()

        mappings.filter { it.targetColumn.isNotBlank() && it.status != "unmapped" }.forEach { mapping ->
            val headerIndex = headers.indexOf(mapping.sourceHeader)
            if (headerIndex < 0) return@forEach
            val column = columnsByName[mapping.targetColumn] ?: return@forEach
            val values = rows.mapNotNull { row -> row.getOrNull(headerIndex)?.trim()?.takeIf { it.isNotBlank() } }
            if (values.isEmpty()) return@forEach
            val label = column.displayName.ifBlank { mapping.sourceHeader }
            val numericValues = values.mapNotNull { it.replace(",", "").toDoubleOrNull() }
            val isNumeric = column.dataType.contains("numeric", true) || column.dataType.contains("integer", true) || numericValues.size >= values.size * 0.8
            if (isNumeric && numericValues.isNotEmpty()) {
                val mean = numericValues.average()
                val sd = if (numericValues.size > 1) {
                    sqrt(numericValues.sumOf { value -> (value - mean) * (value - mean) } / (numericValues.size - 1))
                } else 0.0
                numericRows += listOf(
                    label,
                    numericValues.size.toString(),
                    formatStat(mean),
                    formatStat(sd),
                    formatStat(numericValues.minOrNull() ?: 0.0),
                    formatStat(numericValues.maxOrNull() ?: 0.0)
                )
            } else {
                val counts = values.groupingBy { it }.eachCount()
                    .entries
                    .sortedWith(compareByDescending<Map.Entry<String, Int>> { it.value }.thenBy { it.key })
                    .take(12)
                if (counts.size in 1..12) {
                    val total = values.size.toDouble().coerceAtLeast(1.0)
                    resultTables += MasterChartResultSummaryJson(
                        title = "Distribution of $label",
                        type = "frequency",
                        headers = listOf("Category", "Frequency", "Percentage"),
                        rows = counts.map { entry ->
                            listOf(entry.key, entry.value.toString(), "${formatStat(entry.value * 100.0 / total)}%")
                        }
                    )
                }
            }
        }

        if (numericRows.isNotEmpty()) {
            resultTables.add(
                0,
                MasterChartResultSummaryJson(
                    title = "Descriptive statistics for continuous variables",
                    type = "statistics",
                    headers = listOf("Variable", "N", "Mean", "SD", "Minimum", "Maximum"),
                    rows = numericRows
                )
            )
        }
        return resultTables.take(10)
    }

    private fun formatStat(value: Double): String {
        return if (value % 1.0 == 0.0) value.toInt().toString() else String.format(java.util.Locale.US, "%.2f", value)
    }

    private fun buildChaptersWithMasterDataResults(
        state: UiState,
        fileName: String,
        rowCount: Int,
        validationIssues: List<MasterChartValidationIssueJson>,
        resultTables: List<MasterChartResultSummaryJson>
    ): List<Chapter> {
        val tableModels = resultTables.mapIndexed { index, table ->
            ThesisTableJson(
                tableNumber = "R${index + 1}",
                title = table.title,
                headers = table.headers,
                rows = table.rows,
                footnote = "Generated from uploaded master data file: $fileName."
            )
        }
        val charts = resultTables
            .filter { it.type == "frequency" && it.rows.isNotEmpty() }
            .take(6)
            .mapIndexed { index, table ->
                ChartJson(
                    chartId = "master_data_chart_${index + 1}",
                    title = table.title,
                    type = "bar",
                    chartTemplate = "bar",
                    xAxisLabel = "Category",
                    yAxisLabel = "Frequency",
                    labels = table.rows.map { it.getOrNull(0).orEmpty() },
                    values = table.rows.map { it.getOrNull(1)?.toDoubleOrNull() ?: 0.0 },
                    datasets = listOf(
                        ChartDatasetJson(
                            label = table.title,
                            labels = table.rows.map { it.getOrNull(0).orEmpty() },
                            values = table.rows.map { it.getOrNull(1)?.toDoubleOrNull() ?: 0.0 }
                        )
                    )
                )
            }
        val sections = listOf(
            ResultSection(
                heading = "Master data analysis",
                content = "Results were generated from $rowCount uploaded records in $fileName. The analysis uses only uploaded master data rows.",
                observations = listOf(
                    "${resultTables.size} result tables generated.",
                    "${charts.size} charts generated.",
                    "${validationIssues.count { it.severity == "error" }} blocking data issues and ${validationIssues.count { it.severity != "error" }} warnings detected."
                )
            )
        )
        val rawResults = ResultsJson(
            sections = sections,
            tables = tableModels.map {
                TableJson(
                    tableNumber = it.tableNumber,
                    title = it.title,
                    headers = it.headers,
                    rows = it.rows,
                    footnote = it.footnote
                )
            },
            charts = charts
        )
        val content = buildString {
            appendLine("RESULTS")
            appendLine()
            appendLine("Results were generated from $rowCount uploaded master data records in $fileName.")
            appendLine("Validation found ${validationIssues.size} issue(s); review the Master Chart tab before final export.")
            resultTables.forEachIndexed { index, table ->
                appendLine()
                appendLine("Table R${index + 1}. ${table.title}")
            }
        }
        val chapters = state.chapters.toMutableList()
        val existingIndex = chapters.indexOfFirst { it.name.equals("Results", ignoreCase = true) }
        val resultChapter = (chapters.getOrNull(existingIndex) ?: Chapter(
            name = "Results",
            id = (chapters.maxOfOrNull { it.id } ?: chapters.size) + 1
        )).copy(
            name = "Results",
            content = content,
            status = Chapter.ChapterStatus.SUCCESS,
            errorMessage = null,
            tables = tableModels,
            charts = charts,
            rawJson = gson.toJson(rawResults),
            completedByProvider = "uploaded-master-data",
            completedByLabel = "Uploaded master data analysis"
        )
        if (existingIndex >= 0) {
            chapters[existingIndex] = resultChapter
        } else {
            chapters += resultChapter
        }
        return chapters
    }

    private fun buildMasterChartColumns(state: UiState): List<MasterChartColumnJson> {
        val columns = linkedMapOf<String, MasterChartColumnJson>()

        fun add(
            name: String,
            display: String,
            type: String,
            role: String,
            source: String,
            allowed: String = "",
            analysis: String = "",
            notes: String = ""
        ) {
            val key = sanitizeMasterChartColumnName(name)
            if (key.isBlank()) return
            columns.putIfAbsent(
                key,
                MasterChartColumnJson(
                    columnName = key,
                    displayName = display.ifBlank { name },
                    dataType = type,
                    allowedValues = allowed,
                    role = role,
                    source = source,
                    suggestedAnalysis = analysis,
                    notes = notes
                )
            )
        }

        add("case_id", "Case ID", "text", "identifier", "Required master chart identifier", notes = "Use anonymous IDs such as P001, P002.")
        add("serial_number", "Serial number", "integer", "identifier", "Required master chart identifier")
        add("age", "Age", "numeric", "demographic", "Standard demographic variable", analysis = "Mean, SD, range; compare by groups if applicable")
        add("sex", "Sex", "categorical", "demographic", "Standard demographic variable", allowed = "Male; Female; Other", analysis = "Frequency, percentage; chi-square/Fisher test")

        val methodsText = state.chapters
            .filter { it.name.contains("method", ignoreCase = true) || it.name.contains("proforma", ignoreCase = true) || it.name.contains("data collection", ignoreCase = true) || it.name.contains("outcome", ignoreCase = true) || it.name.contains("results", ignoreCase = true) }
            .joinToString("\n") { listOf(it.name, it.content, it.rawJson).joinToString("\n") }

        val variableNames = linkedSetOf<String>()
        state.variables.forEach { variable ->
            val normalized = variable.name.trim()
            if (normalized.isNotBlank() && !normalized.contains("References", ignoreCase = true) && !normalized.startsWith("Previous Chapter", true)) {
                variableNames += normalized
            }
        }
        Regex("""(?i)\b(?:variables?|parameters?|data collected|outcome measures?)\b[:\s-]+([^.\n]{8,260})""")
            .findAll(methodsText)
            .forEach { match ->
                match.groupValues[1]
                    .split(",", ";", " and ")
                    .map { it.trim().trim('.', ':', '-') }
                    .filter { it.length in 3..80 }
                    .forEach { variableNames += it }
            }

        variableNames.forEach { rawName ->
            val role = inferMasterChartRole(rawName)
            add(
                name = rawName,
                display = rawName.replace('_', ' ').replace(Regex("\\s+"), " ").trim(),
                type = inferMasterChartType(rawName),
                role = role,
                source = "Thesis variables / generated chapters",
                allowed = inferMasterChartAllowedValues(rawName),
                analysis = suggestedMasterChartAnalysis(rawName, role)
            )
        }

        state.chapters
            .filter { it.status == Chapter.ChapterStatus.SUCCESS }
            .flatMap { chapter ->
                chapter.tables.flatMap { table -> table.headers } +
                    runCatching { parseThesisChapterJson(chapter.rawJson, chapter.name).tables.flatMap { it.headers } }.getOrDefault(emptyList())
            }
            .map { it.trim() }
            .filter { it.length in 2..80 && !it.equals("s.no", true) && !it.equals("serial number", true) }
            .forEach { header ->
                val role = inferMasterChartRole(header)
                add(
                    name = header,
                    display = header,
                    type = inferMasterChartType(header),
                    role = role,
                    source = "Generated thesis tables",
                    allowed = inferMasterChartAllowedValues(header),
                    analysis = suggestedMasterChartAnalysis(header, role)
                )
            }

        if (columns.keys.none { it.contains("outcome") || it.contains("result") }) {
            add("primary_outcome", "Primary outcome", "categorical/text", "outcome", "Outcome Measures", analysis = "Primary endpoint summary; compare across exposure/groups")
        }
        return columns.values.toList()
    }

    private fun sanitizeMasterChartColumnName(value: String): String {
        return value
            .lowercase()
            .replace(Regex("""\([^)]*\)"""), "")
            .replace(Regex("""[^a-z0-9]+"""), "_")
            .trim('_')
            .take(48)
    }

    private fun inferMasterChartType(name: String): String {
        val n = name.lowercase()
        return when {
            listOf("age", "score", "index", "ratio", "count", "level", "value", "duration", "size", "weight", "height", "bmi", "pressure", "velocity", "ri", "pi", "mean", "sd").any { n.contains(it) } -> "numeric"
            listOf("grade", "stage", "class", "severity").any { n.contains(it) } -> "ordinal"
            listOf("sex", "gender", "yes", "no", "present", "absent", "group", "type", "category", "diagnosis", "outcome").any { n.contains(it) } -> "categorical"
            listOf("date", "year", "month").any { n.contains(it) } -> "date/text"
            else -> "text"
        }
    }

    private fun inferMasterChartRole(name: String): String {
        val n = name.lowercase()
        return when {
            listOf("age", "sex", "gender", "residence", "occupation").any { n.contains(it) } -> "demographic"
            listOf("symptom", "diagnosis", "grade", "stage", "severity", "history", "comorbid").any { n.contains(it) } -> "clinical"
            listOf("investigation", "doppler", "oct", "ultrasound", "ri", "pi", "velocity", "lab", "test").any { n.contains(it) } -> "investigation"
            listOf("outcome", "result", "follow", "improved", "mortality", "complication").any { n.contains(it) } -> "outcome"
            listOf("group", "exposure", "intervention", "treatment").any { n.contains(it) } -> "exposure/grouping"
            else -> "study_variable"
        }
    }

    private fun inferMasterChartAllowedValues(name: String): String {
        val n = name.lowercase()
        return when {
            n.contains("sex") || n.contains("gender") -> "Male; Female; Other"
            n.contains("yes") || n.contains("no") || n.contains("present") || n.contains("absent") -> "Yes; No"
            n.contains("grade") -> "Grade 1; Grade 2; Grade 3; Grade 4; Grade 5"
            n.contains("outcome") -> "Improved; Not improved; Complication; Lost to follow-up"
            else -> ""
        }
    }

    private fun suggestedMasterChartAnalysis(name: String, role: String): String {
        val type = inferMasterChartType(name)
        return when {
            role == "outcome" -> "Frequency/percentage; association with key exposure using chi-square/Fisher or logistic regression"
            role == "investigation" && type == "numeric" -> "Mean +/- SD or median/IQR; t-test/ANOVA or Mann-Whitney/Kruskal-Wallis"
            type == "numeric" -> "Mean, SD, median, range; compare between groups if applicable"
            type == "ordinal" -> "Frequency by category; trend/ordinal association test"
            type == "categorical" -> "Frequency and percentage; chi-square/Fisher test"
            else -> "Descriptive summary"
        }
    }

    private fun buildMasterChartCsv(columns: List<MasterChartColumnJson>): String {
        val header = columns.joinToString(",") { csvEscape(it.columnName) }
        val dictionaryHeader = "column_name,display_name,data_type,allowed_values,role,source,suggested_analysis,notes"
        val dictionaryRows = columns.joinToString("\n") { col ->
            listOf(col.columnName, col.displayName, col.dataType, col.allowedValues, col.role, col.source, col.suggestedAnalysis, col.notes)
                .joinToString(",") { csvEscape(it) }
        }
        return "$header\n\nDATA_DICTIONARY\n$dictionaryHeader\n$dictionaryRows"
    }

    private fun csvEscape(value: String): String {
        val escaped = value.replace("\"", "\"\"")
        return if (escaped.any { it == ',' || it == '\n' || it == '"' }) "\"$escaped\"" else escaped
    }

    private fun refreshWorkerPromptsForCurrentSettings() {
        viewModelScope.launch(Dispatchers.Default) {
            val snapshot = _uiState.value
            if (snapshot.chapters.isEmpty()) return@launch
            val now = System.currentTimeMillis()
            val updated = snapshot.chapters.map { chapter ->
                if (!chapter.syncEnabled || chapter.name.lowercase() in autoGeneratedChapterNames) {
                    chapter
                } else {
                    val schema = chapterSchemas[chapter.name.lowercase()]
                    val vars = getVariablesForChapter(chapter.name, snapshot.variables)
                    val prompt = runCatching {
                        buildChapterPrompt(chapter.name, vars, schema, forceDetailed = false)
                    }.getOrDefault(chapter.workerPrompt)
                    chapter.copy(
                        workerPrompt = prompt,
                        workerPromptUpdatedAt = if (prompt != chapter.workerPrompt) now else chapter.workerPromptUpdatedAt
                    )
                }
            }
            _uiState.update { it.copy(chapters = updated, status = "Prompt size settings applied") }
            saveSessionToFirebase()
        }
    }

    fun setProvider(provider: String) {
        val normalized = provider.trim().ifBlank { "auto" }
        _uiState.update {
            it.copy(
                selectedProvider = normalized,
                status = if (normalized.equals("auto", ignoreCase = true)) {
                    "AI provider set to auto rotation"
                } else {
                    "AI provider bound to $normalized for chapter generation"
                }
            )
        }
        saveSessionToFirebase()
    }

    fun setVpsAutoCompleteEnabled(enabled: Boolean) {
        viewModelScope.launch {
            val snapshot = _uiState.value
            _uiState.update {
                it.copy(
                    vpsAutoCompleteEnabled = enabled,
                    status = if (enabled) "Preparing VPS auto-complete queue..." else "VPS auto-complete disabled"
                )
            }

            val updatedChapters = withContext(Dispatchers.Default) {
                snapshot.chapters.map { chapter ->
                    if (chapter.name.lowercase() in autoGeneratedChapterNames) {
                        chapter.copy(syncEnabled = false)
                    } else {
                        val schema = chapterSchemas[chapter.name.lowercase()]
                        val vars = getVariablesForChapter(chapter.name, snapshot.variables)
                        val prompt = if (enabled) {
                            runCatching {
                                if (chapter.name.equals("Literature Review", ignoreCase = true)) {
                                    chapter.workerPrompt.ifBlank {
                                        buildChapterPrompt(chapter.name, vars, schema, forceDetailed = false)
                                    }
                                } else {
                                    buildChapterPrompt(chapter.name, vars, schema, forceDetailed = false)
                                }
                            }.getOrElse { chapter.workerPrompt }
                        } else {
                            chapter.workerPrompt
                        }
                        chapter.copy(
                            syncEnabled = enabled,
                            workerStatus = if (enabled) "queued" else "",
                            retryCount = if (enabled && chapter.status != Chapter.ChapterStatus.SUCCESS) 0 else chapter.retryCount,
                            workerPrompt = if (enabled) prompt else chapter.workerPrompt,
                            workerPromptUpdatedAt = if (enabled && prompt.isNotBlank()) System.currentTimeMillis() else chapter.workerPromptUpdatedAt,
                            lastWorkerError = if (enabled) "" else chapter.lastWorkerError,
                            lockedBy = "",
                            lockedUntil = 0L
                        )
                    }
                }
            }

            _uiState.update { state ->
                state.copy(
                    vpsAutoCompleteEnabled = enabled,
                    chapters = updatedChapters,
                    status = if (enabled) "VPS auto-complete enabled for pending chapters" else "VPS auto-complete disabled"
                )
            }
            saveSessionToFirebase()
        }
    }

    fun setThesisTitle(title: String) {
        _uiState.update { state ->
            state.copy(
                thesisTitle = title,
                variables = ensureDiseaseTopicVariable(state.variables, title)
            )
        }
        saveSessionToFirebase()
    }

    fun createNewSession(title: String = "") {
        detachCurrentSessionWorkerListener()
        _uiState.update {
            UiState(
                sessionId = newSessionId(),
                thesisTitle = title,
                variables = ensureDiseaseTopicVariable(emptyList(), title),
                selectedProvider = it.selectedProvider,
                collegeLogoUri = it.collegeLogoUri,
                pdfTheme = it.pdfTheme
            )
        }
        saveSessionToFirebase()
    }

    fun startExtraction(context: Context) {
        viewModelScope.launch {
            val appContext = context.applicationContext
            val uri = _uiState.value.pdfUri ?: return@launch
            startBackgroundWork(appContext, "Extracting thesis PDF")

            try {
                _uiState.update {
                    it.copy(
                        processing = true,
                        status = "Extracting document text...",
                        progressCurrent = 0,
                        progressTotal = 0
                    )
                }

                val pdfText = try {
                    withContext(Dispatchers.IO) {
                        val helperExtracted = AiDocumentOcrHelper.extractText(appContext, uri)
                        if (helperExtracted.isNotBlank()) {
                            helperExtracted
                        } else {
                            appContext.contentResolver.openInputStream(uri)?.use { stream ->
                                PdfTextExtractor.extractText(appContext, stream)
                            } ?: ""
                        }
                    }
                } catch (e: Exception) {
                    _uiState.update { it.copy(processing = false, status = "Document error: ${e.message}") }
                    return@launch
                }

                if (pdfText.isBlank()) {
                    _uiState.update { it.copy(processing = false, status = "No text found in document") }
                    return@launch
                }

                _uiState.update { it.copy(status = "Extracting variables...") }

                val variables = ensureDiseaseTopicVariable(extractVariables(pdfText))
                _uiState.update {
                    it.copy(
                        variables = variables,
                        status = "Variables extracted. Preparing PubMed reference corpus...",
                        processing = true,
                        showVariablesEditor = true
                    )
                }
                val abstractCount = prepareReferenceCorpusFromCurrentVariables()
                val sourceCount = _uiState.value.verifiedPubMedAbstractSources.size
                val finalStatus = if (sourceCount > 0) {
                    "Variables extracted. PubMed references included: $sourceCount; abstracts available: $abstractCount. Edit if needed, then generate chapters."
                } else {
                    "Variables extracted. No PubMed-validated references were available. Edit if needed, then generate chapters."
                }
                _uiState.update {
                    it.copy(
                        status = finalStatus,
                        processing = false,
                        showVariablesEditor = true
                    )
                }
                saveSessionToFirebase()
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        processing = false,
                        status = "Extraction failed: ${e.localizedMessage ?: e.message ?: "Unknown error"}"
                    )
                }
            } finally {
                stopBackgroundWork(appContext)
            }
        }
    }

    fun refreshReferenceCorpus() {
        viewModelScope.launch {
            if (_uiState.value.processing) return@launch
            val appContext = EduLabsApplication.instance.applicationContext
            startBackgroundWork(appContext, "Refreshing PubMed abstracts")
            try {
                _uiState.update {
                    it.copy(
                        processing = true,
                        status = "Refreshing PubMed reference corpus..."
                    )
                }
                val abstractCount = prepareReferenceCorpusFromCurrentVariables()
                val sourceCount = _uiState.value.verifiedPubMedAbstractSources.size
                _uiState.update {
                    it.copy(
                        processing = false,
                        status = if (sourceCount > 0) {
                            "PubMed references included: $sourceCount; abstracts available: $abstractCount"
                        } else {
                            "No PubMed-validated references were available"
                        }
                    )
                }
                saveSessionToFirebase()
            } finally {
                stopBackgroundWork(appContext)
            }
        }
    }

    private suspend fun prepareReferenceCorpusFromCurrentVariables(): Int {
        val references = parseReferencesVariableForProcessing()
        if (references.isEmpty()) {
            _uiState.update {
                it.copy(
                    verifiedPubMedReferences = emptyList(),
                    verifiedPubMedAbstractSources = emptyList(),
                    referenceSequenceCounter = 1
                )
            }
            return 0
        }

        _uiState.update {
            it.copy(
                status = "Validating extracted references with PubMed...",
                progressCurrent = 0,
                progressTotal = references.size
            )
        }

        val verifiedReferences = verifyReferencesWithPubMed(references)
            .filter { it.hasRequiredPmid() }
            .distinctBy { ref -> referenceIdentity(ref) ?: canonicalReferenceTextKey(ref.referenceText) }
            .mapIndexed { index, reference -> reference.copy(citation = serializedCitation(index + 1)) }

        if (verifiedReferences.isEmpty()) {
            updateVariable("References_Vancouver", "")
            _uiState.update {
                it.copy(
                    verifiedPubMedReferences = emptyList(),
                    verifiedPubMedAbstractSources = emptyList(),
                    referenceSequenceCounter = 1,
                    progressCurrent = 0,
                    progressTotal = 0
                )
            }
            return 0
        }

        updateVariable("References_Vancouver", formatReferencesForVariable(verifiedReferences))
        seedVerifiedReferenceCache(verifiedReferences)
        persistVerifiedReferenceCache()

        _uiState.update {
            it.copy(
                status = "Downloading PubMed abstracts and similar articles...",
                progressCurrent = 0,
                progressTotal = verifiedReferences.size
            )
        }

        val now = System.currentTimeMillis()
        val pmids = verifiedReferences
            .mapNotNull { it.pmid?.trim()?.takeIf { pmid -> pmid.isNotBlank() } }
            .distinct()
        val freshCached = pmids.mapNotNull { pmid ->
            val cached = pubMedAbstractSourceCache[pmid] ?: return@mapNotNull null
            val fetchedAt = pubMedAbstractFetchedAt[pmid] ?: 0L
            cached.takeIf { now - fetchedAt <= pubMedAbstractStaleAfterMs }
        }
        val freshPmids = freshCached.map { it.pmid.trim() }.toSet()
        val pmidsToFetch = pmids.filter { it !in freshPmids }
        val fetched = fetchPubMedAbstractSources(pmidsToFetch)
        fetched.forEach { source ->
            val pmid = source.pmid.trim()
            if (pmid.isNotBlank()) {
                pubMedAbstractSourceCache[pmid] = source
                pubMedAbstractFetchedAt[pmid] = now
            }
        }
        val mergedSources = (freshCached + fetched)
            .filter { it.pmid.isNotBlank() }
            .distinctBy { it.pmid.trim() }
            .sortedBy { it.pmid.trim() }
        _uiState.update {
            it.copy(
                verifiedPubMedAbstractSources = mergedSources,
                progressCurrent = mergedSources.size,
                progressTotal = verifiedReferences.size
            )
        }
        return mergedSources.count { it.abstractText.isNotBlank() }
    }

    private suspend fun extractVariables(fullText: String): List<Variable> {
        val chunks = TextChunker.chunkText(fullText, 8000)
        val allVars = linkedMapOf<String, Variable>()

        for ((idx, chunk) in chunks.withIndex()) {
            _uiState.update {
                it.copy(
                    status = "Extracting chunk ${idx + 1}/${chunks.size}",
                    progressCurrent = idx + 1,
                    progressTotal = chunks.size
                )
            }

            val prompt = buildExtractionPrompt(idx + 1, chunk, allVars.values.toList())

            try {
                val rawText = callVariableExtractionAi(prompt)
                val extracted = parseExtractionJson(rawText)
                extracted.forEach { newVar ->
                    val existing = allVars[newVar.name]
                    allVars[newVar.name] = mergeExtractedVariable(existing, newVar)
                }
                saveSessionToFirebase()
            } catch (_: Exception) {
            }
        }

        return allVars.values.toList()
    }

    private suspend fun callVariableExtractionAi(prompt: String): String = withContext(Dispatchers.IO) {
        val preferredProviders = listOf("groq")
        val errors = mutableListOf<String>()
        val rejectedProviders = mutableSetOf<String>()

        for (provider in preferredProviders) {
            if (provider in rejectedProviders) continue
            val apiKeyPresent = when (provider) {
                "groq" -> ApiKeys.GROQ_API_KEY.isNotBlank()
                else -> false
            }
            if (!apiKeyPresent) {
                errors += "$provider: API key missing"
                continue
            }

            val providerPool = ModelRotator.buildPool(provider)
            if (providerPool.isEmpty()) {
                errors += "$provider: no models available"
                continue
            }

            for (candidate in providerPool) {
                if (candidate.provider in rejectedProviders) continue
                val attemptStartedAt = System.currentTimeMillis()
                try {
                    _uiState.update { state ->
                        if (state.processing) {
                            state.copy(status = "Extracting variables with ${candidate.provider}/${candidate.model}")
                        } else {
                            state
                        }
                    }

                    val result = retryTransientNetwork("variable-extraction-${candidate.provider}/${candidate.model}") {
                        when (candidate.provider) {
                            "groq" -> callOpenAiStyleProvider("groq", candidate.model, prompt)
                            else -> throw Exception("Unsupported extraction provider: ${candidate.provider}")
                        }
                    }.trim()

                    if (result.isBlank()) throw Exception("Empty response from ${candidate.provider}/${candidate.model}")
                    appendAiLogEntry(
                        phase = "variable_extraction",
                        provider = candidate.provider,
                        model = candidate.model,
                        status = "completed",
                        prompt = prompt,
                        response = result,
                        durationMs = System.currentTimeMillis() - attemptStartedAt
                    )
                    if (isProviderWideRefusalText(result)) {
                        ModelRotator.markProviderFailure(candidate.provider, result)
                        ModelRotator.clearLastSuccessfulIfMatches(candidate.provider, candidate.model)
                        rejectedProviders += candidate.provider
                        errors += "${candidate.provider}/${candidate.model}: provider-wide refusal"
                        break
                    }

                    ModelRotator.markSuccess(candidate)
                    return@withContext result
                } catch (e: Throwable) {
                    val msg = e.message ?: e.toString()
                    appendAiLogEntry(
                        phase = "variable_extraction",
                        provider = candidate.provider,
                        model = candidate.model,
                        status = "failed",
                        prompt = prompt,
                        error = msg,
                        durationMs = System.currentTimeMillis() - attemptStartedAt
                    )
                    errors += "${candidate.provider}/${candidate.model}: $msg"
                    ModelRotator.markFailure(candidate.provider, candidate.model, msg)
                    ModelRotator.clearLastSuccessfulIfMatches(candidate.provider, candidate.model)
                    if (isProviderWideRefusalText(msg)) {
                        ModelRotator.markProviderFailure(candidate.provider, msg)
                        rejectedProviders += candidate.provider
                        break
                    }
                    if (isSkipToNextModelError(msg)) continue
                }
            }
        }

        Log.w("ThesisViewModel", "Variable extraction preferred providers failed; falling back to general pool: ${errors.joinToString(" | ").take(1200)}")
        callAiApi(prompt, phase = "variable_extraction")
    }

    private fun mergeExtractedVariable(existing: Variable?, incoming: Variable): Variable {
        if (existing == null) return incoming

        val existingValue = existing.value.trim()
        val incomingValue = incoming.value.trim()
        if (incomingValue.isBlank()) return existing
        if (existingValue.isBlank()) return incoming
        if (existingValue == incomingValue) return existing

        val normalizedExisting = normalizeExtractedText(existingValue)
        val normalizedIncoming = normalizeExtractedText(incomingValue)
        if (normalizedIncoming.isBlank()) return existing
        if (normalizedExisting.contains(normalizedIncoming, ignoreCase = true)) return existing
        if (normalizedIncoming.contains(normalizedExisting, ignoreCase = true)) return incoming

        val separator = if (existingValue.endsWith("\n") || incomingValue.startsWith("\n")) "" else "\n"
        val mergedValue = buildString {
            append(existingValue)
            append(separator)
            append(incomingValue)
        }

        return existing.copy(value = mergedValue)
    }

    private fun ensureDiseaseTopicVariable(
        variables: List<Variable>,
        titleOverride: String = _uiState.value.thesisTitle
    ): List<Variable> {
        val diseaseKeys = setOf(
            normalizeVariableKey("Disease_or_Condition"),
            normalizeVariableKey("Title_Disease_Topic"),
            normalizeVariableKey("Disease Topic")
        )
        val existing = variables.firstOrNull { normalizeVariableKey(it.name) in diseaseKeys }
        val existingValue = existing?.value?.trim().orEmpty()
        if (existingValue.isNotBlank() && !isPlaceholderDiseaseTopic(existingValue)) return variables

        fun pick(vararg names: String): String {
            val normalizedNames = names.map(::normalizeVariableKey).toSet()
            return variables.firstOrNull { normalizeVariableKey(it.name) in normalizedNames }
                ?.value
                ?.trim()
                .orEmpty()
        }

        val title = titleOverride.ifBlank { pick("Title", "Thesis Title", "Project Title") }
        val derived = deriveDiseaseTopic(
            title = title,
            keywords = pick("Keywords", "MeSH Keywords"),
            aim = pick("Aim_of_Study", "Aim of Study", "Aim"),
            population = pick("Study_Population", "Study Population")
        )
        if (derived.isBlank()) return variables

        return if (existing != null) {
            variables.map {
                if (it === existing) it.copy(name = "Disease_or_Condition", value = derived) else it
            }
        } else {
            listOf(Variable("Disease_or_Condition", derived)) + variables
        }
    }

    private fun deriveDiseaseTopic(
        title: String,
        keywords: String = "",
        aim: String = "",
        population: String = ""
    ): String {
        val source = listOf(title, aim, population, keywords)
            .firstOrNull { it.isNotBlank() }
            .orEmpty()
        if (source.isBlank()) return ""

        val cleaned = source
            .replace(Regex("""(?i)\b(a|an|the)\s+(clinical\s+)?(prospective|retrospective|observational|cross[- ]sectional|comparative|case[- ]control|cohort)?\s*study\s+(of|on|to assess|to evaluate|to determine)?\b"""), " ")
            .replace(Regex("""(?i)\b(evaluation|assessment|correlation|association|comparison|prevalence|incidence|profile|role|study)\s+of\b"""), " ")
            .replace(Regex("""\s+"""), " ")
            .trim(' ', '.', ':', ';', '-')

        val patternCandidates = listOf(
            Regex("""(?i)\bpatients?\s+with\s+([^,.;:()]+)"""),
            Regex("""(?i)\bsubjects?\s+with\s+([^,.;:()]+)"""),
            Regex("""(?i)\b(?:in|among)\s+([^,.;:()]+?)\s+(?:patients?|subjects?|cases?)\b"""),
            Regex("""(?i)\b(?:in|among)\s+patients?\s+(?:of|having|diagnosed with)\s+([^,.;:()]+)"""),
            Regex("""(?i)\b(?:with|of)\s+([^,.;:()]+)""")
        )
        patternCandidates.forEach { pattern ->
            val candidate = pattern.find(cleaned)?.groupValues?.getOrNull(1)?.let(::cleanDiseaseTopicCandidate).orEmpty()
            if (candidate.isNotBlank()) return candidate
        }

        return cleanDiseaseTopicCandidate(cleaned)
    }

    private fun isPlaceholderDiseaseTopic(value: String): Boolean {
        val normalized = value.trim().lowercase()
        return normalized.isBlank() ||
            normalized in setOf("n/a", "na", "not specified", "not mentioned", "none", "unknown") ||
            normalized.contains("not enough information")
    }

    private fun cleanDiseaseTopicCandidate(value: String): String {
        val stopPhrases = listOf(
            "attending", "admitted", "using", "by", "at", "in relation", "and its",
            "and their", "and", "with respect", "among", "compared"
        )
        var candidate = value
            .replace(Regex("""(?i)\b(adult|pediatric|paediatric|male|female)\s+"""), " ")
            .replace(Regex("""\s+"""), " ")
            .trim(' ', '.', ':', ';', '-', ',', '/', '\\')
        stopPhrases.forEach { phrase ->
            candidate = candidate.replace(Regex("""(?i)\s+\Q$phrase\E\b.*$"""), "").trim()
        }
        return candidate
            .split(Regex("""\s+"""))
            .take(8)
            .joinToString(" ")
            .trim()
    }

    private fun normalizeExtractedText(text: String): String {
        return text
            .replace(Regex("\\s+"), " ")
            .trim()
    }

    private fun buildThesisSessionPayload(sessionId: String): ThesisSessionPayload {
        val state = _uiState.value
        return ThesisSessionPayload(
            sessionId = sessionId,
            thesisTitle = state.thesisTitle,
            updatedAt = System.currentTimeMillis(),
            status = if (state.processing) "IN_PROGRESS" else "IDLE",
            currentChapter = state.progressCurrent,
            totalChapters = state.progressTotal,
            completionPercent = state.completionPercent,
            selectedProvider = state.selectedProvider,
            collegeLogoUri = state.collegeLogoUri,
            pdfTheme = state.pdfTheme,
            variables = state.variables,
            chapters = state.chapters,
            verifiedPubMedReferences = state.verifiedPubMedReferences,
            verifiedPubMedAbstractSources = state.verifiedPubMedAbstractSources,
            cachedPubMedMatches = emptyList(),
            cachedPubMedSearchMatches = emptyList(),
            cachedPubMedAbstractSources = emptyList(),
            cachedVerifiedReferences = emptyList(),
            referenceSequenceCounter = state.referenceSequenceCounter,
            pubMedFigureCheckedPmids = state.pubMedFigureCheckedPmids,
            pubMedFigures = state.pubMedFigures,
            vpsAutoCompleteEnabled = state.vpsAutoCompleteEnabled,
            autoSyncEnabled = state.autoSyncEnabled,
            lastWorkerSyncTime = state.lastWorkerSyncTime,
            exportMargin = state.exportMargin,
            exportFont = state.exportFont,
            exportLineSpacing = state.exportLineSpacing,
            exportLogoPlacement = state.exportLogoPlacement,
            exportPageNumbering = state.exportPageNumbering,
            exportHeaderFooter = state.exportHeaderFooter,
            exportWatermark = state.exportWatermark,
            exportAutoToc = state.exportAutoToc,
            exportAutoLists = state.exportAutoLists,
            promptSectionSplittingEnabled = state.promptSectionSplittingEnabled,
            promptMaxChars = state.promptMaxChars,
            masterChartColumns = state.masterChartColumns,
            masterChartCsv = state.masterChartCsv,
            masterChartGeneratedAt = state.masterChartGeneratedAt,
            masterDataFileName = state.masterDataFileName,
            masterDataHeaders = state.masterDataHeaders,
            masterDataRows = state.masterDataRows,
            masterDataMappings = state.masterDataMappings,
            masterDataValidationIssues = state.masterDataValidationIssues,
            masterDataResultTables = state.masterDataResultTables,
            masterDataImportedAt = state.masterDataImportedAt,
            aiLogs = state.aiLogs
        )
    }

    private suspend fun saveThesisSessionToBackend(baseUrl: String, payload: ThesisSessionPayload): Boolean {
        val body = gson.toJson(
            mapOf(
                "action" to "save",
                "user_id" to (FirebaseAuth.getInstance().currentUser?.uid ?: return false),
                "session_id" to payload.sessionId,
                "payload" to payload
            )
        ).toRequestBody("application/json; charset=utf-8".toMediaType())
        val request = Request.Builder()
            .url(baseUrl)
            .post(body)
            .build()
        rawClient.newCall(request).execute().use { response ->
            val raw = response.body?.string().orEmpty()
            if (!response.isSuccessful) throw IOException("Thesis session backend HTTP ${response.code}: ${raw.take(500)}")
            val obj = JsonParser.parseString(raw).asJsonObject
            if (!obj.get("ok").asBoolean) throw IOException(obj.get("error")?.asString ?: "Backend returned ok=false")
            return true
        }
    }

    private suspend fun loadThesisSessionFromBackend(action: String, userId: String, sessionId: String? = null): ThesisSessionPayload? {
        val baseUrl = ApiKeys.THESIS_SESSION_BACKEND_URL.trim()
        if (baseUrl.isBlank()) return null
        val url = buildString {
            append(baseUrl)
            append("?action=")
            append(action)
            append("&user_id=")
            append(Uri.encode(userId))
            if (!sessionId.isNullOrBlank()) {
                append("&session_id=")
                append(Uri.encode(sessionId))
            }
        }
        val request = Request.Builder().url(url).get().build()
        rawClient.newCall(request).execute().use { response ->
            val raw = response.body?.string().orEmpty()
            if (!response.isSuccessful) throw IOException("Thesis session backend HTTP ${response.code}: ${raw.take(500)}")
            val obj = JsonParser.parseString(raw).asJsonObject
            if (!obj.get("ok").asBoolean) throw IOException(obj.get("error")?.asString ?: "Backend returned ok=false")
            val sessionObj = obj.getAsJsonObject("session") ?: return null
            val payloadElement = sessionObj.get("payload")
                ?: sessionObj.get("payload_json")
                ?: sessionObj.get("session")
                ?: sessionObj
            return gson.fromJson(payloadElement, ThesisSessionPayload::class.java)
        }
    }

    private suspend fun listThesisSessionsFromBackend(userId: String, limit: Int = 50): List<SessionItem> {
        val baseUrl = ApiKeys.THESIS_SESSION_BACKEND_URL.trim()
        if (baseUrl.isBlank()) return emptyList()
        val url = "$baseUrl?action=list&user_id=${Uri.encode(userId)}&limit=${limit.coerceIn(1, 100)}"
        val request = Request.Builder().url(url).get().build()
        rawClient.newCall(request).execute().use { response ->
            val raw = response.body?.string().orEmpty()
            if (!response.isSuccessful) throw IOException("Thesis session backend HTTP ${response.code}: ${raw.take(500)}")
            val obj = JsonParser.parseString(raw).asJsonObject
            if (!obj.get("ok").asBoolean) throw IOException(obj.get("error")?.asString ?: "Backend returned ok=false")
            return obj.getAsJsonArray("sessions")?.mapNotNull { element ->
                val item = element.asJsonObject
                val sessionId = item.get("session_id")?.asString ?: item.get("sessionId")?.asString ?: return@mapNotNull null
                SessionItem(
                    sessionId = sessionId,
                    thesisTitle = item.get("thesis_title")?.asString ?: item.get("thesisTitle")?.asString.orEmpty(),
                    timestamp = item.get("updated_at")?.asLong ?: item.get("updatedAt")?.asLong ?: 0L,
                    chaptersCount = item.get("chapters_count")?.asInt ?: item.get("chaptersCount")?.asInt ?: 0
                )
            }.orEmpty()
        }
    }

    private fun appendAiLogEntry(
        phase: String,
        chapterName: String = "",
        provider: String = "",
        model: String = "",
        status: String,
        prompt: String = "",
        response: String = "",
        error: String = "",
        durationMs: Long = 0L
    ) {
        val maxBodyChars = 120_000
        val entry = ThesisAiLogEntry(
            id = "${System.currentTimeMillis()}_${UUID.randomUUID()}",
            timestamp = System.currentTimeMillis(),
            phase = phase,
            chapterName = chapterName,
            provider = provider,
            model = model,
            status = status,
            prompt = prompt.take(maxBodyChars),
            response = response.take(maxBodyChars),
            error = error.take(maxBodyChars),
            durationMs = durationMs,
            promptChars = prompt.length,
            responseChars = response.length
        )
        _uiState.update { state ->
            state.copy(aiLogs = (listOf(entry) + state.aiLogs).take(250))
        }
        // Persist the exchange to the training database (best-effort, never blocks UI).
        if (status == "completed" || response.isNotBlank()) {
            val contextJson = try {
                JSONObject()
                    .put("chapter", chapterName)
                    .put("phase", phase)
                    .put("error", error.take(2000))
                    .toString()
            } catch (e: Throwable) {
                chapterName
            }
            AiTrainingLogger.log(
                source = "thesis_$phase",
                provider = provider,
                model = model,
                prompt = prompt,
                response = response.ifBlank { error },
                status = if (response.isNotBlank()) "completed" else "failed",
                contextJson = contextJson,
                durationMs = durationMs
            )
        }
    }

    fun clearAiLogs() {
        _uiState.update { it.copy(aiLogs = emptyList()) }
        saveSessionToFirebase(immediate = true)
    }

    private suspend fun callAiApi(
        prompt: String,
        requireStrongResponse: Boolean = false,
        retryAttempt: Int = 0,
        chapterName: String = "",
        phase: String = "ai_request"
    ): String = withContext(Dispatchers.IO) {
        val selected = if (retryAttempt > 0) {
            when (retryAttempt) {
                1 -> "gemini"
                2 -> "deepseek"
                3 -> "cloudflare"
                else -> "auto"
            }
        } else {
            _uiState.value.selectedProvider
        }
        val providerBound = selected.isNotBlank() && !selected.equals("auto", ignoreCase = true)
        if (selected == "auto" || selected == "openrouter") {
            refreshOpenRouterFreeModelsIfNeeded()
        }
        val pool = ModelRotator.buildPool(selected)
        val rejectedProviders = mutableSetOf<String>()

        if (pool.isEmpty()) {
            throw Exception("No models available for provider selection: $selected")
        }

        val errors = mutableListOf<String>()

        for (candidate in pool) {
            if (candidate.provider in rejectedProviders) continue
            val attemptStartedAt = System.currentTimeMillis()
            try {
                val result = retryTransientNetwork("${candidate.provider}/${candidate.model}") {
                    when (candidate.provider) {
                        "gemini" -> callGemini(candidate.model, prompt)
                        "cloudflare" -> callCloudflare(candidate.model, prompt)
                        "groq" -> callOpenAiStyleProvider("groq", candidate.model, prompt)
                        "openrouter" -> callOpenAiStyleProvider("openrouter", candidate.model, prompt)
                        "deepseek" -> callOpenAiStyleProvider("deepseek", candidate.model, prompt)
                        "mistral" -> callOpenAiStyleProvider("mistral", candidate.model, prompt)
                        "cerebras" -> callOpenAiStyleProvider("cerebras", candidate.model, prompt)
                        "cohere" -> callCohere(candidate.model, prompt)
                        "replicate" -> callReplicate(candidate.model, prompt)
                        else -> throw Exception("Unknown provider: ${candidate.provider}")
                    }
                }

                val cleaned = result.trim()
                if (cleaned.isNotBlank()) {
                    appendAiLogEntry(
                        phase = phase,
                        chapterName = chapterName,
                        provider = candidate.provider,
                        model = candidate.model,
                        status = "completed",
                        prompt = prompt,
                        response = cleaned,
                        durationMs = System.currentTimeMillis() - attemptStartedAt
                    )
                    if (isProviderWideRefusalText(cleaned)) {
                        val refusalMessage = "Provider ${candidate.provider} returned a provider-wide refusal"
                        ModelRotator.markProviderFailure(candidate.provider, cleaned)
                        ModelRotator.clearLastSuccessfulIfMatches(candidate.provider, candidate.model)
                        rejectedProviders += candidate.provider
                        errors += "${candidate.provider}/${candidate.model}: $refusalMessage"
                        Log.w(
                            "ThesisViewModel",
                            "$refusalMessage; skipping remaining ${candidate.provider} models"
                        )
                        continue
                    }
                    if (requireStrongResponse && isWeakChapterContent(cleaned)) {
                        throw Exception("Weak response from ${candidate.provider}/${candidate.model}")
                    }
                    ModelRotator.markSuccess(candidate)
                    return@withContext cleaned
                }

                throw Exception("Empty response from ${candidate.provider}/${candidate.model}")
            } catch (e: Throwable) {
                val msg = e.message ?: e.toString()
                appendAiLogEntry(
                    phase = phase,
                    chapterName = chapterName,
                    provider = candidate.provider,
                    model = candidate.model,
                    status = "failed",
                    prompt = prompt,
                    error = msg,
                    durationMs = System.currentTimeMillis() - attemptStartedAt
                )
                errors += "${candidate.provider}/${candidate.model}: $msg"
                ModelRotator.markFailure(candidate.provider, candidate.model, msg)
                ModelRotator.clearLastSuccessfulIfMatches(candidate.provider, candidate.model)
                if (isProviderWideRefusalText(msg)) {
                    ModelRotator.markProviderFailure(candidate.provider, msg)
                    rejectedProviders += candidate.provider
                }
                if (isSkipToNextModelError(msg)) continue
            }
        }

        if (providerBound) {
            throw Exception("Selected provider $selected exhausted: ${errors.joinToString(" | ")}")
        }

        try {
            val attemptStartedAt = System.currentTimeMillis()
            val endpointResult = retryTransientNetwork("endpoint-fallback") {
                callOpenAiCompatibleFallback(prompt)
            }
            val cleaned = endpointResult.trim()
            if (cleaned.isNotBlank()) {
                appendAiLogEntry(
                    phase = phase,
                    chapterName = chapterName,
                    provider = "endpoint-fallback",
                    model = "openai-compatible",
                    status = "completed",
                    prompt = prompt,
                    response = cleaned,
                    durationMs = System.currentTimeMillis() - attemptStartedAt
                )
                if (requireStrongResponse && isWeakChapterContent(cleaned)) {
                    throw Exception("Weak response from endpoint fallback")
                }
                return@withContext cleaned
            }
            errors += "endpoint-fallback: empty response"
            notifyEndpointGatewayStillFailing("empty response")
        } catch (e: Throwable) {
            val msg = e.message ?: e.toString()
            appendAiLogEntry(
                phase = phase,
                chapterName = chapterName,
                provider = "endpoint-fallback",
                model = "openai-compatible",
                status = "failed",
                prompt = prompt,
                error = msg
            )
            errors += "endpoint-fallback: $msg"
            notifyEndpointGatewayStillFailing(msg)
        }

        try {
            val attemptStartedAt = System.currentTimeMillis()
            val deepSeekResult = retryTransientNetwork("deepseek-last-resort") {
                callDeepSeekLastResort(prompt)
            }
            val cleaned = deepSeekResult.trim()
            if (cleaned.isNotBlank()) {
                appendAiLogEntry(
                    phase = phase,
                    chapterName = chapterName,
                    provider = "deepseek-last-resort",
                    model = ApiKeys.DEEPSEEK_MODEL,
                    status = "completed",
                    prompt = prompt,
                    response = cleaned,
                    durationMs = System.currentTimeMillis() - attemptStartedAt
                )
                if (requireStrongResponse && isWeakChapterContent(cleaned)) {
                    throw Exception("Weak response from DeepSeek last resort")
                }
                return@withContext cleaned
            }
            errors += "deepseek-last-resort: empty response"
        } catch (e: Throwable) {
            val msg = e.message ?: e.toString()
            appendAiLogEntry(
                phase = phase,
                chapterName = chapterName,
                provider = "deepseek-last-resort",
                model = ApiKeys.DEEPSEEK_MODEL,
                status = "failed",
                prompt = prompt,
                error = msg
            )
            errors += "deepseek-last-resort: $msg"
        }

        throw Exception("All providers/models failed: ${errors.joinToString(" | ")}")
    }

    private suspend fun refreshOpenRouterFreeModelsIfNeeded() {
        if (!ModelRotator.shouldRefreshOpenRouterFreeModels()) return

        try {
            val models = fetchOpenRouterFreeModels()
            if (models.isNotEmpty()) {
                ModelRotator.replaceProviderModels("openrouter", models)
                Log.d("ThesisViewModel", "Loaded ${models.size} free OpenRouter models")
            }
        } catch (e: Throwable) {
            Log.w(
                "ThesisViewModel",
                "OpenRouter free model discovery failed; using fallback catalog: ${e.message ?: e.toString()}"
            )
        }
    }

    private suspend fun fetchOpenRouterFreeModels(): List<String> = withContext(Dispatchers.IO) {
        val request = Request.Builder()
            .url("https://openrouter.ai/api/frontend/models/find?max_price=0")
            .addHeader("Content-Type", "application/json")
            .addHeader("Accept", "application/json")
            .get()
            .build()

        rawClient.newCall(request).execute().use { response ->
            val raw = response.body?.string().orEmpty()
            if (!response.isSuccessful) {
                throw IOException("OpenRouter models HTTP ${response.code}: ${raw.take(500)}")
            }
            parseOpenRouterFreeModels(raw).ifEmpty {
                throw IOException("OpenRouter returned no free models")
            }
        }
    }

    private fun parseOpenRouterFreeModels(raw: String): List<String> {
        val root = JsonParser.parseString(raw).asJsonObject
        val data = root.get("data")

        val modelElements = when {
            data?.isJsonObject == true -> data.asJsonObject.getAsJsonArray("models")
            data?.isJsonArray == true -> data.asJsonArray
            root.get("models")?.isJsonArray == true -> root.getAsJsonArray("models")
            else -> null
        } ?: return emptyList()

        return modelElements.mapNotNull { element ->
            val model = element.takeIf { it.isJsonObject }?.asJsonObject ?: return@mapNotNull null
            listOf("id", "slug", "canonical_slug", "model", "name")
                .firstNotNullOfOrNull { key ->
                    model.get(key)
                        ?.takeIf { it.isJsonPrimitive }
                        ?.asString
                        ?.trim()
                        ?.takeIf { it.isNotBlank() && !it.contains(' ') }
                }
        }.distinct()
    }



    private suspend fun <T> retryTransientNetwork(
        label: String,
        attempts: Int = 3,
        initialDelayMs: Long = 600,
        operation: suspend () -> T
    ): T {
        var lastError: Throwable? = null
        repeat(attempts) { attempt ->
            try {
                return operation()
            } catch (t: Throwable) {
                lastError = t
                if (!isTransientNetworkFailure(t) || attempt == attempts - 1) {
                    throw t
                }
                val backoff = initialDelayMs * (attempt + 1)
                Log.w("ThesisViewModel", "$label transient network error, retrying in ${backoff}ms: ${t.message ?: t.toString()}")
                delay(backoff)
            }
        }
        throw lastError ?: Exception("$label failed without an explicit error")
    }

    private fun isTransientNetworkFailure(error: Throwable): Boolean {
        val message = (error.message ?: error.toString()).lowercase()
        return error is IOException ||
                message.contains("timeout") ||
                message.contains("timed out") ||
                message.contains("failed to connect") ||
                message.contains("connection reset") ||
                message.contains("broken pipe") ||
                message.contains("network is unreachable") ||
                message.contains("host is unresolved") ||
                message.contains("unknownhost") ||
                message.contains("socketexception") ||
                message.contains("unreachable") ||
                message.contains("connection refused") ||
                message.contains("tls") ||
                message.contains("ssl")
    }

    private fun notifyEndpointGatewayStillFailing(reason: String) {
        val message = "Endpoint AI gateway still failing; trying backup providers"
        Log.w("ThesisViewModel", "$message: ${reason.take(250)}")
        _uiState.update { state ->
            if (state.processing) state.copy(status = message) else state
        }
    }

    private suspend fun callOpenAiCompatibleFallback(prompt: String): String {
        val apiKey = ApiKeys.ENDPOINT_AI_API_KEY.trim()
        if (apiKey.isBlank()) throw Exception("Endpoint AI API key missing")

        val model = ApiKeys.ENDPOINT_AI_MODEL.trim().ifBlank { "deepseek-r1:7b" }
        val baseUrl = ApiKeys.ENDPOINT_AI_BASE_URL.trim().ifBlank {
            "https://endpointai-backend-production.up.railway.app/"
        }.trimEnd('/')

        val requestBody = mapOf(
            "model" to model,
            "messages" to listOf(
                mapOf("role" to "system", "content" to "You are a helpful AI assistant. Return ONLY valid JSON. No markdown."),
                mapOf("role" to "user", "content" to prompt)
            ),
            "temperature" to 0.7,
            "max_tokens" to 1000
        )

        val body = gson.toJson(requestBody)
            .toRequestBody("application/json; charset=utf-8".toMediaType())

        val url = "$baseUrl/api/v1/chat/completions"

        val request = Request.Builder()
            .url(url)
            .addHeader("Content-Type", "application/json")
            .addHeader("X-API-Key", apiKey)
            .post(body)
            .build()

        rawClient.newCall(request).execute().use { response ->
            val raw = response.body?.string().orEmpty()
            Log.d(
                "ThesisViewModel",
                "Endpoint AI attempt url=$url status=${response.code} success=${response.isSuccessful} body=${raw.take(250)}"
            )
            if (!response.isSuccessful) {
                throw IOException("Endpoint AI HTTP ${response.code}: ${raw.take(500)}")
            }

            val json = JsonParser.parseString(raw).asJsonObject
            val text = extractEndpointCompletionText(json)
            return text.trim().ifBlank {
                throw Exception("Empty endpoint fallback response")
            }
        }
    }

    private suspend fun callDeepSeekLastResort(prompt: String): String {
        val apiKey = ApiKeys.DEEPSEEK_API_KEY.trim()
        if (apiKey.isBlank()) throw Exception("DeepSeek API key missing")

        val requestBody = mapOf(
            "model" to ApiKeys.DEEPSEEK_MODEL.trim().ifBlank { "deepseek-v4-flash" },
            "messages" to listOf(
                mapOf("role" to "system", "content" to "You are a helpful AI assistant. Return ONLY valid JSON. No markdown."),
                mapOf("role" to "user", "content" to prompt)
            ),
            "thinking" to mapOf("type" to "enabled"),
            "reasoning_effort" to "high",
            "temperature" to 0.2,
            "max_tokens" to 6000,
            "stream" to false
        )

        val body = gson.toJson(requestBody)
            .toRequestBody("application/json; charset=utf-8".toMediaType())

        val request = Request.Builder()
            .url("https://api.deepseek.com/chat/completions")
            .addHeader("Content-Type", "application/json")
            .addHeader("Authorization", "Bearer $apiKey")
            .post(body)
            .build()

        repeat(2) { attempt ->
            rawClient.newCall(request).execute().use { response ->
                val raw = response.body?.string().orEmpty()
                Log.d(
                    "ThesisViewModel",
                    "DeepSeek last-resort attempt=${attempt + 1} status=${response.code} success=${response.isSuccessful} body=${raw.take(250)}"
                )
                if (!response.isSuccessful) {
                    if (attempt == 0) return@use
                    throw IOException("DeepSeek HTTP ${response.code}: ${raw.take(500)}")
                }

                val json = JsonParser.parseString(raw).asJsonObject
                val text = extractEndpointCompletionText(json)
                val cleaned = text.trim()
                if (cleaned.isNotBlank()) return cleaned
                if (attempt == 1) throw Exception("Empty DeepSeek last-resort response")
            }
            if (attempt == 0) delay(800)
        }
        throw Exception("DeepSeek last-resort response unavailable")
    }



    private fun extractEndpointCompletionText(json: JsonObject): String {
        val choices = json.getAsJsonArray("choices")
        val contentFromChoices = choices?.firstOrNull()?.asJsonObject
            ?.getAsJsonObject("message")
            ?.get("content")
            ?.asString
            ?.trim()
            .orEmpty()

        if (contentFromChoices.isNotBlank()) return contentFromChoices

        val altMessage = choices?.firstOrNull()?.asJsonObject
        val altText = altMessage?.get("text")?.asString?.trim().orEmpty()
        if (altText.isNotBlank()) return altText

        val directText = json.get("text")?.takeIf { it.isJsonPrimitive }?.asString?.trim().orEmpty()
        if (directText.isNotBlank()) return directText

        val output = json.get("output")
        if (output != null && !output.isJsonNull) {
            return when {
                output.isJsonPrimitive -> output.asString.trim()
                output.isJsonArray -> output.asJsonArray.joinToString("") { element ->
                    when {
                        element.isJsonPrimitive -> element.asString
                        element.isJsonObject -> element.asJsonObject.get("text")?.takeIf { it.isJsonPrimitive }?.asString.orEmpty()
                        else -> ""
                    }
                }.trim()
                else -> ""
            }
        }

        return ""
    }

    private suspend fun callOpenAiStyleProvider(
        provider: String,
        model: String,
        prompt: String
    ): String {
        val apiKey = when (provider) {
            "groq" -> ApiKeys.GROQ_API_KEY
            "openrouter" -> ApiKeys.OPENROUTER_API_KEY
            "deepseek" -> ApiKeys.DEEPSEEK_API_KEY
            "mistral" -> ApiKeys.MISTRAL_API_KEY
            "cerebras" -> ApiKeys.CEREBRAS_API_KEY
            else -> throw Exception("Unsupported provider: $provider")
        }.trim()

        if (apiKey.isBlank()) throw Exception("$provider API key missing")

        val request = ChatRequest(
            model = model,
            messages = listOf(
                Message("system", "Return ONLY valid JSON. No markdown."),
                Message("user", prompt)
            ),
            temperature = 0.2,
            maxTokens = 6000,
            responseFormat = null
        )

        val response = when (provider) {
            "groq" -> ApiClient.groqApi.chatCompletion(
                "openai/v1/chat/completions",
                "Bearer $apiKey",
                request
            )

            "openrouter" -> ApiClient.openRouterApi.chatCompletion(
                "api/v1/chat/completions",
                "Bearer $apiKey",
                request
            )

            "deepseek" -> ApiClient.deepSeekApi.chatCompletion(
                "chat/completions",
                "Bearer $apiKey",
                request
            )

            "mistral" -> ApiClient.mistralApi.chatCompletion(
                "v1/chat/completions",
                "Bearer $apiKey",
                request
            )

            "cerebras" -> ApiClient.cerebrasApi.chatCompletion(
                "v1/chat/completions",
                "Bearer $apiKey",
                request
            )

            else -> throw Exception("Unsupported provider: $provider")
        }

        return response.choices.firstOrNull()?.message?.content?.trim().orEmpty()
            .ifBlank { throw Exception("Empty response from $provider/$model") }
    }

    private suspend fun callGemini(model: String, prompt: String): String {
        val apiKey = ApiKeys.GEMINI_API_KEY.trim()
        if (apiKey.isBlank()) throw Exception("Gemini API key missing")

        val url =
            "https://generativelanguage.googleapis.com/v1beta/models/$model:generateContent?key=$apiKey"

        val payload = GeminiRequest(
            contents = listOf(
                GeminiContent(
                    parts = listOf(
                        GeminiPart(
                            text = """
                                Return ONLY valid JSON. No markdown.
                                Do not stop early.
                                If the JSON is long, continue until it is complete.
                                $prompt
                            """.trimIndent()
                        )
                    )
                )
            ),
            generationConfig = GeminiGenerationConfig(
                temperature = 0.2,
                maxOutputTokens = 8192,
                responseMimeType = "application/json"
            )
        )

        val body =
            gson.toJson(payload).toRequestBody("application/json; charset=utf-8".toMediaType())

        val request = Request.Builder()
            .url(url)
            .post(body)
            .build()

        rawClient.newCall(request).execute().use { response ->
            val raw = response.body?.string().orEmpty()
            if (!response.isSuccessful) {
                throw IOException("Gemini HTTP ${response.code}: ${raw.take(500)}")
            }

            val obj = JsonParser.parseString(raw).asJsonObject
            val text = obj.getAsJsonArray("candidates")
                ?.firstOrNull()?.asJsonObject
                ?.getAsJsonObject("content")
                ?.getAsJsonArray("parts")
                ?.firstOrNull()?.asJsonObject
                ?.get("text")?.asString

            return text?.trim().orEmpty().ifBlank {
                throw Exception("Empty Gemini response")
            }
        }
    }

    private suspend fun callCloudflare(model: String, prompt: String): String {
        val accountId = ApiKeys.CLOUDFLARE_ACCOUNT_ID.trim()
        val apiKey = ApiKeys.CLOUDFLARE_WORKER_API_KEY.trim()

        if (accountId.isBlank() || accountId.contains("your_account_id_here", ignoreCase = true)) {
            throw Exception("Cloudflare account ID missing or placeholder")
        }
        if (apiKey.isBlank()) {
            throw Exception("Cloudflare API key missing")
        }

        val url = "https://api.cloudflare.com/client/v4/accounts/$accountId/ai/run/$model"

        val payload = CloudflareRequest(
            messages = listOf(
                CloudflareMessage("system", "Return ONLY valid JSON. No markdown."),
                CloudflareMessage("user", prompt)
            ),
            temperature = 0.2,
            maxTokens = 6000,
            stream = false
        )

        val body =
            gson.toJson(payload).toRequestBody("application/json; charset=utf-8".toMediaType())

        val request = Request.Builder()
            .url(url)
            .addHeader("Authorization", "Bearer $apiKey")
            .post(body)
            .build()

        rawClient.newCall(request).execute().use { response ->
            val raw = response.body?.string().orEmpty()
            if (!response.isSuccessful) {
                throw IOException("Cloudflare HTTP ${response.code}: ${raw.take(500)}")
            }

            val obj = JsonParser.parseString(raw).asJsonObject
            val text = firstCloudflareText(obj)

            return text?.trim().orEmpty().ifBlank {
                throw Exception("Empty Cloudflare response")
            }
        }
    }

    private suspend fun callCohere(model: String, prompt: String): String {
        val apiKey = ApiKeys.COHERE_API_KEY.trim()
        if (apiKey.isBlank()) throw Exception("Cohere API key missing")

        val url = "https://api.cohere.ai/v1/chat"

        val payload = CohereRequest(
            model = model,
            message = """
                Return ONLY valid JSON. No markdown.
                $prompt
            """.trimIndent(),
            temperature = 0.2
        )

        val body =
            gson.toJson(payload).toRequestBody("application/json; charset=utf-8".toMediaType())

        val request = Request.Builder()
            .url(url)
            .addHeader("Authorization", "Bearer $apiKey")
            .addHeader("Accept", "application/json")
            .post(body)
            .build()

        rawClient.newCall(request).execute().use { response ->
            val raw = response.body?.string().orEmpty()
            if (!response.isSuccessful) {
                throw IOException("Cohere HTTP ${response.code}: ${raw.take(500)}")
            }

            return try {
                val obj = JsonParser.parseString(raw).asJsonObject
                val text = obj.get("text")?.asString
                text?.trim().orEmpty().ifBlank {
                    throw Exception("Empty Cohere response")
                }
            } catch (e: Exception) {
                throw Exception("Failed to parse Cohere response: ${e.message}")
            }
        }
    }

    private suspend fun callReplicate(model: String, prompt: String): String {
        val apiKey = ApiKeys.REPLICATE_API_KEY.trim()
        if (apiKey.isBlank()) throw Exception("Replicate API key missing")

        // Replicate uses a prediction-based flow.
        // This implementation assumes the model follows a standard Llama/Mistral input schema on Replicate.
        val url = "https://api.replicate.com/v1/models/$model/predictions"

        val payload = ReplicateRequest(
            input = ReplicateInput(
                prompt = prompt,
                system_prompt = "Return ONLY valid JSON. No markdown.",
                temperature = 0.2,
                max_new_tokens = 4000
            )
        )

        val body = gson.toJson(payload).toRequestBody("application/json; charset=utf-8".toMediaType())

        val request = Request.Builder()
            .url(url)
            .addHeader("Authorization", "Token $apiKey")
            .post(body)
            .build()

        rawClient.newCall(request).execute().use { response ->
            val raw = response.body?.string().orEmpty()
            if (!response.isSuccessful) {
                throw IOException("Replicate HTTP ${response.code}: ${raw.take(500)}")
            }

            val predictionObj = JsonParser.parseString(raw).asJsonObject
            val statusUrl = predictionObj.getAsJsonObject("urls").get("get").asString

            // Poll for completion
            repeat(30) {
                delay(2000)
                val pollRequest = Request.Builder().url(statusUrl).addHeader("Authorization", "Token $apiKey").build()
                rawClient.newCall(pollRequest).execute().use { pollRes ->
                    val pollRaw = pollRes.body?.string().orEmpty()
                    val pollObj = JsonParser.parseString(pollRaw).asJsonObject
                    val status = pollObj.get("status").asString
                    if (status == "succeeded") {
                        val output = pollObj.get("output")
                        return if (output.isJsonArray) {
                            output.asJsonArray.joinToString("") { it.asString }
                        } else {
                            output.asString
                        }
                    } else if (status == "failed" || status == "canceled") {
                        throw Exception("Replicate prediction $status")
                    }
                }
            }
            throw Exception("Replicate prediction timed out")
        }
    }

    private fun firstCloudflareText(obj: JsonObject): String? {
        val result = obj.getAsJsonObject("result") ?: return null
        return result.get("response")?.asString
            ?: result.get("text")?.asString
            ?: result.get("output")?.asString
    }

    private fun isSkipToNextModelError(message: String): Boolean {
        val m = message.lowercase()
        return m.contains("model_decommissioned") ||
                m.contains("decommissioned") ||
                m.contains("no longer supported") ||
                m.contains("unsupported") ||
                m.contains("invalid request") ||
                m.contains("invalid_argument") ||
                m.contains("cannot find field") ||
                m.contains("unknown name") ||
                m.contains("unsupported json") ||
                m.contains("json_object") ||
                m.contains("json schema") ||
                m.contains("404") ||
                m.contains("400") ||
                m.contains("429") ||
                m.contains("timeout") ||
                m.contains("rate limit")
    }

    private fun isProviderWideRefusalText(text: String): Boolean {
        val m = text.lowercase()
        return m.contains("none of its models can be used for the day") ||
                m.contains("no models can be used for the day") ||
                m.contains("no models available for the day") ||
                m.contains("models cannot be used today") ||
                m.contains("provider unavailable for today") ||
                m.contains("try again tomorrow") ||
                m.contains("come back tomorrow") ||
                m.contains("temporarily unavailable")
    }

    private fun buildExtractionPrompt(
        chunkNo: Int,
        chunkText: String,
        existingVars: List<Variable>
    ): String {
        val existingSummary = existingVars.take(20).joinToString(", ") {
            "\"${it.name}\": \"${it.value.take(80)}\""
        }

        return """
            You are an expert medical thesis extractor.
            From the given thesis text, extract ALL the following variables. For each variable, provide the **complete content** (do not truncate, summarise, paraphrase, or clean up the wording).
            Preserve the original order, headings, numbering, bullets, tables, and paragraph breaks as they appear in the PDF whenever possible.
            If a variable spans multiple paragraphs or pages, include the full continuous text exactly as present in the source chunk.

            Return ONLY valid JSON in this exact structure:

            {
              "variables": [
                { "variable_name": "Title", "variable_value": "full thesis title" },
                { "variable_name": "Disease_or_Condition", "variable_value": "main disease/condition/topic named in the thesis title, e.g. type 2 diabetes mellitus, acute myocardial infarction, cataract, chronic kidney disease" },
                { "variable_name": "Degree", "variable_value": "MD/MS/DM etc." },
                { "variable_name": "Department", "variable_value": "e.g., General Medicine" },
                { "variable_name": "Institution", "variable_value": "full institution name" },
                { "variable_name": "Guide", "variable_value": "name and designation" },
                { "variable_name": "Co-guide", "variable_value": "if any" },
                { "variable_name": "Student Name", "variable_value": "candidate's name" },
                { "variable_name": "Year", "variable_value": "academic year" },
                { "variable_name": "Registration Number", "variable_value": "university reg no" },
                { "variable_name": "Abstract_structured", "variable_value": "Background: ...\nAim: ...\nMethods: ...\nResults: ...\nConclusion: ..." },
                { "variable_name": "Keywords", "variable_value": "MeSH term1, term2, term3" },
                { "variable_name": "Introduction_text", "variable_value": "full introduction section" },
                { "variable_name": "Background_text", "variable_value": "full background / epidemiology" },
                { "variable_name": "Literature_Review_text", "variable_value": "detailed review of past studies" },
                { "variable_name": "Research_Gap", "variable_value": "what is missing" },
                { "variable_name": "Aim_of_Study", "variable_value": "primary aim" },
                { "variable_name": "Objectives_primary", "variable_value": "list: 1. ... 2. ..." },
                { "variable_name": "Objectives_secondary", "variable_value": "if any" },
                { "variable_name": "Hypothesis_null", "variable_value": "null hypothesis statement" },
                { "variable_name": "Hypothesis_alternate", "variable_value": "alternate hypothesis" },
                { "variable_name": "Study_Design", "variable_value": "e.g., prospective cohort" },
                { "variable_name": "Study_Setting", "variable_value": "hospital/community" },
                { "variable_name": "Study_Duration", "variable_value": "start and end dates" },
                { "variable_name": "Study_Population", "variable_value": "description of target population" },
                { "variable_name": "Inclusion_Criteria", "variable_value": "bulleted list" },
                { "variable_name": "Exclusion_Criteria", "variable_value": "bulleted list" },
                { "variable_name": "Sample_Size", "variable_value": "number and calculation justification" },
                { "variable_name": "Sampling_Technique", "variable_value": "random/convenience etc." },
                { "variable_name": "Data_Collection", "variable_value": "procedures, forms, timelines" },
                { "variable_name": "Variables_Collected", "variable_value": "list of all independent/dependent variables" },
                { "variable_name": "Investigations", "variable_value": "lab tests, imaging modalities" },
                { "variable_name": "Study_Procedure", "variable_value": "step‑by‑step intervention/observation" },
                { "variable_name": "Outcome_Measures_primary", "variable_value": "primary endpoint" },
                { "variable_name": "Outcome_Measures_secondary", "variable_value": "secondary endpoints" },
                { "variable_name": "Statistical_Analysis", "variable_value": "tests, software, p‑value threshold" },
                { "variable_name": "Ethical_Considerations", "variable_value": "IRB, consent, confidentiality" },
                { "variable_name": "Results_text", "variable_value": "full results narrative with numbers" },
                { "variable_name": "Observations", "variable_value": "key objective findings" },
                { "variable_name": "Tables", "variable_value": "JSON array of tables if present" },
                { "variable_name": "Figures", "variable_value": "descriptions of figures" },
                { "variable_name": "Discussion_text", "variable_value": "full discussion" },
                { "variable_name": "Comparison_with_Literature", "variable_value": "how findings compare" },
                { "variable_name": "Limitations", "variable_value": "study limitations" },
                { "variable_name": "Conclusion_text", "variable_value": "final conclusion" },
                { "variable_name": "Summary", "variable_value": "short summary" },
                { "variable_name": "Recommendations", "variable_value": "clinical/policy recommendations" },
                { "variable_name": "Future_Scope", "variable_value": "future research directions" },
                { "variable_name": "Abbreviations", "variable_value": "all abbreviations used in the thesis with full forms" },
                { "variable_name": "References_Vancouver", "variable_value": "numbered Vancouver references exactly as present; one complete reference per numbered entry; preserve PMID and DOI if shown, e.g. 1. Author AA, Author BB. Article title. Journal. 2020;12(3):123-130. PMID: 12345678. DOI: 10.xxxx/xxxxx" },
                { "variable_name": "Appendices", "variable_value": "list of annexures" }
              ]
            }

            IMPORTANT RULES:
            - For **long text variables** (e.g., Introduction_text, Results_text), extract the **entire section** from the PDF, not just a summary. Keep the full wording.
            - For **list variables** (Inclusion_Criteria, Objectives_primary), use bullet points or numbered lines.
            - For **References_Vancouver**, preserve complete numbered Vancouver citations and keep any PMID/DOI metadata present in the PDF. Do not split one citation into multiple references. If one citation wraps across several PDF lines, join those wrapped lines into the same numbered reference entry. Do not invent missing PMID or DOI during extraction.
            - Do not compress multi-line content into a one-line summary. Preserve line breaks where they exist.
            - If the current chunk contains only part of a long section, still return the exact part you can see; the app will merge chunk pieces later.
            - If a variable is not found in the current chunk, leave it out of the JSON (do not set empty value).
            - Keep the variable_name **exactly** as written above.

            Known variables already extracted (you may skip adding them again, but can update if new info appears):
            $existingSummary

            Chunk $chunkNo of many:
            $chunkText
        """.trimIndent()
    }

    private fun parseExtractionJson(text: String): List<Variable> {
        return try {
            val cleaned = extractJsonBlock(text)
            val response = gson.fromJson(cleaned, ExtractionResponse::class.java)
            response.variables.mapNotNull { varData ->
                if (varData.variableName.isNotBlank() && varData.variableValue != null) {
                    Variable(varData.variableName, varData.variableValue)
                } else null
            }
        } catch (e: Exception) {
            Log.w("ThesisViewModel", "Failed to parse extraction JSON", e)
            emptyList()
        }
    }

    // Helper data class for extraction response
    data class ExtractionResponse(
        val variables: List<ExtractionVariable>
    )

    data class ExtractionVariable(
        @SerializedName("variable_name") val variableName: String,
        @SerializedName("variable_value") val variableValue: String?
    )

    private fun extractJsonBlock(text: String): String {
        val trimmed = text.trim()
            .removePrefix("```json")
            .removePrefix("```")
            .removeSuffix("```")
            .trim()

        val first = trimmed.indexOf('{')
        if (first < 0) return trimmed

        val slice = trimmed.substring(first)
        val stack = ArrayDeque<Char>()
        var inString = false
        var escaped = false

        for (index in slice.indices) {
            val ch = slice[index]
            if (inString) {
                when {
                    escaped -> escaped = false
                    ch == '\\' -> escaped = true
                    ch == '"' -> inString = false
                }
                continue
            }
            when (ch) {
                '"' -> inString = true
                '{', '[' -> stack.addLast(ch)
                '}', ']' -> {
                    val open = stack.lastOrNull()
                    if ((ch == '}' && open == '{') || (ch == ']' && open == '[')) {
                        stack.removeLast()
                        if (stack.isEmpty()) return slice.substring(0, index + 1)
                    }
                }
            }
        }

        val closing = buildString {
            stack.toList().asReversed().forEach { open ->
                append(if (open == '{') '}' else ']')
            }
        }
        return slice + closing
    }

    private fun looksLikeJsonObject(text: String): Boolean {
        val cleaned = extractJsonBlock(text)
        return cleaned.startsWith("{") && cleaned.endsWith("}")
    }

    private fun isCompleteJson(text: String): Boolean {
        val cleaned = text.trim()
        if (!cleaned.startsWith("{")) return false
        return try {
            JsonParser.parseString(extractJsonBlock(cleaned))
            true
        } catch (_: Exception) {
            false
        }
    }

    private fun buildContinuationPrompt(basePrompt: String, previousOutput: String, chapterName: String): String {
        val tail = previousOutput.takeLast(1200)

        return """
            Original chapter prompt:
            ${basePrompt.trim()}

            Partial JSON to continue:
            $tail

            Your previous response was cut off before the JSON was complete.

            Continue from the exact point where it stopped.
            Do NOT restart the JSON.
            Do NOT repeat earlier content.
            Do NOT add markdown or explanations.
            Output ONLY the remaining JSON needed to complete the same object.

            Chapter: $chapterName

            LAST OUTPUT TAIL:
            $tail
        """.trimIndent()
    }

    private suspend fun callAiJsonWithContinuation(
        basePrompt: String,
        chapterName: String,
        maxContinuations: Int = 3,
        retryAttempt: Int = 0
    ): String {
        var combined = ""
        var prompt = basePrompt

        repeat(maxContinuations + 1) {
            val part = callAiApi(
                prompt = prompt,
                requireStrongResponse = false,
                retryAttempt = retryAttempt,
                chapterName = chapterName,
                phase = "chapter_generation"
            )
            combined += part

            val cleaned = extractJsonBlock(combined)
            if (isCompleteJson(cleaned)) {
                return cleaned
            }

            prompt = buildContinuationPrompt(basePrompt, combined, chapterName)
        }

        throw Exception("Incomplete JSON after continuation attempts for $chapterName")
    }

    private fun isWeakChapterContent(text: String): Boolean {
        val t = text.lowercase().trim()
        return t.isBlank() ||
                t.length < 120 ||
                t.contains("not mentioned") ||
                t.contains("not enough information") ||
                t == "n/a" ||
                t == "na"
    }

    fun updateVariable(name: String, newValue: String) {
        _uiState.update { state ->
            val existing = state.variables.find { it.name == name }
            val newVars = if (existing != null) {
                state.variables.map {
                    if (it.name == name) it.copy(value = newValue) else it
                }
            } else {
                state.variables + Variable(name, newValue)
            }
            state.copy(variables = newVars)
        }
        saveSessionToFirebase()
    }

    fun getChapterTextBoxesForEditor(chapter: Chapter): List<ChapterTextBoxJson> {
        val existing = chapter.textBoxes.filter { it.text.isNotBlank() }
        if (existing.isNotEmpty()) return existing
        return buildDefaultChapterTextBoxes(chapter)
    }

    fun ensureChapterTextBoxes(chapterName: String) {
        val chapters = _uiState.value.chapters.toMutableList()
        val index = chapters.indexOfFirst { it.name == chapterName }
        if (index < 0) return
        val chapter = chapters[index]
        if (chapter.textBoxes.isNotEmpty()) return
        val boxes = buildDefaultChapterTextBoxes(chapter)
        chapters[index] = chapter.copy(textBoxes = boxes)
        _uiState.update { it.copy(chapters = chapters) }
        saveSessionToFirebase()
    }

    fun updateChapterTextBoxes(chapterName: String, textBoxes: List<ChapterTextBoxJson>) {
        val chapters = _uiState.value.chapters.toMutableList()
        val index = chapters.indexOfFirst { it.name == chapterName }
        if (index < 0) return

        val sortedBoxes = textBoxes
            .filter { it.text.isNotBlank() }
            .sortedWith(compareBy<ChapterTextBoxJson> { it.y }.thenBy { it.x })
            .mapIndexed { boxIndex, box ->
                box.copy(id = box.id.ifBlank { "box_${boxIndex + 1}" })
            }

        val rebuiltContent = sortedBoxes.joinToString("\n\n") { it.text.trim() }.trim()
        chapters[index] = chapters[index].copy(
            textBoxes = sortedBoxes,
            content = rebuiltContent.ifBlank { chapters[index].content }
        )

        _uiState.update { it.copy(chapters = chapters) }
        saveSessionToFirebase()
    }

    fun startChapterGeneration() {
        viewModelScope.launch {
            if (_uiState.value.processing) return@launch
            val appContext = EduLabsApplication.instance.applicationContext
            startBackgroundWork(appContext, "Generating thesis chapters")

            val validation = validateReferencesBeforeGeneration()
            if (validation != null) {
                _uiState.update {
                    it.copy(
                        referenceValidationState = validation,
                        processing = false,
                        status = "PubMed could not resolve any usable PMID references"
                    )
                }
                saveSessionToFirebase()
                stopBackgroundWork(appContext)
                return@launch
            }

            beginChapterGeneration()
        }
    }

    fun dismissReferenceValidation() {
        _uiState.update { it.copy(referenceValidationState = null) }
    }

    fun dismissReferenceUpdateNotice() {
        _uiState.update { it.copy(referenceUpdateNoticeState = null) }
    }

    fun confirmReferenceValidationAndGenerate() {
        viewModelScope.launch {
            val appContext = EduLabsApplication.instance.applicationContext
            startBackgroundWork(appContext, "Generating thesis chapters")
            val validation = _uiState.value.referenceValidationState ?: return@launch
            val pmidReferences = validation.verifiedReferences
                .filter { it.hasRequiredPmid() }
            if (pmidReferences.isEmpty() || pmidReferences.size != validation.verifiedReferences.size) {
                _uiState.update {
                    it.copy(
                        processing = false,
                        status = "Every reference must resolve to a PubMed PMID before generation"
                    )
                }
                stopBackgroundWork(appContext)
                return@launch
            }

            val updatedReferences = formatReferencesForVariable(pmidReferences)

            updateVariable("References_Vancouver", updatedReferences)
            _uiState.update { it.copy(referenceValidationState = null) }
            saveSessionToFirebase()
            beginChapterGeneration()
        }
    }

    private suspend fun validateReferencesBeforeGeneration(): ReferenceValidationState? {
        val references = parseReferencesVariableForProcessing()
        if (references.isEmpty()) return null

        _uiState.update {
            it.copy(
                processing = true,
                status = "Validating references with PubMed..."
            )
        }

        val verifiedReferences = verifyReferencesWithPubMed(references)
        val pmidReferences = verifiedReferences
            .filter { it.hasRequiredPmid() }
        val issues = buildReferenceValidationIssues(references, verifiedReferences)

        if (pmidReferences.isNotEmpty()) {
            updateVariable("References_Vancouver", formatReferencesForVariable(pmidReferences))
            _uiState.update {
                it.copy(
                    processing = false,
                    referenceValidationState = null,
                    referenceUpdateNoticeState = ReferenceValidationState(
                        issues = issues,
                        verifiedReferences = pmidReferences,
                        canApply = false
                    ).takeIf { issues.isNotEmpty() },
                status = if (pmidReferences.size == references.size) {
                    "References corrected and updated with PubMed PMID"
                } else {
                    "PubMed updated ${pmidReferences.size}/${references.size} references with PMID; unresolved references were not used"
                }
                )
            }
            saveSessionToFirebase()
            return null
        }

        _uiState.update {
            it.copy(
                processing = false,
                status = "PubMed found reference updates"
            )
        }

        return ReferenceValidationState(
            issues = issues,
            verifiedReferences = verifiedReferences,
            canApply = false
        )
    }

    private fun beginChapterGeneration() {
        val appContext = EduLabsApplication.instance.applicationContext
        startBackgroundWork(appContext, "Generating thesis chapters")
        _uiState.update {
            it.copy(
                chapters = initialChapterList(),
                showVariablesEditor = false,
                processing = true,
                status = "Generating chapters...",
                progressCurrent = 0,
                progressTotal = chapterHeadings.size,
                hasErrors = false,
                referenceValidationState = null
            )
        }
        saveSessionToFirebase()

        viewModelScope.launch {
            try {
                generateAllChapters()
                if (areAllNormalChaptersCompleted(_uiState.value.chapters)) {
                    assembleAutoGeneratedFrontMatter()
                    saveSessionToFirebase(immediate = true)
                }
            } finally {
                stopBackgroundWork(appContext)
            }
        }
    }

    private fun buildReferenceValidationIssues(
        originalReferences: List<ReferenceJson>,
        verifiedReferences: List<ReferenceJson>
    ): List<ReferenceValidationIssue> {
        return originalReferences.zip(verifiedReferences).mapNotNull { (original, verified) ->
            val originalText = original.referenceText.trim()
            val updatedText = verified.referenceText.trim()
            val hasTextChange = normalizeReferenceText(originalText) != normalizeReferenceText(updatedText)
            val hasMetadataChange = original.pmid != verified.pmid || original.doi != verified.doi
            val hasPubMedMatch = verified.hasRequiredPmid()

            when {
                !hasPubMedMatch -> ReferenceValidationIssue(
                    citation = original.citation.ifBlank { "-" },
                    originalText = original.referenceText.ifBlank { "-" },
                    updatedText = "",
                    issue = "No PubMed PMID match found. This reference cannot be used until PubMed validation supplies a PMID."
                )
                hasTextChange || hasMetadataChange -> ReferenceValidationIssue(
                    citation = original.citation.ifBlank { "-" },
                    originalText = original.referenceText.ifBlank { "-" },
                    updatedText = verified.referenceText.ifBlank { original.referenceText },
                    issue = when {
                        hasTextChange && hasMetadataChange -> "PubMed supplied a corrected citation and PMID metadata"
                        hasTextChange -> "PubMed supplied a corrected citation"
                        else -> "PubMed added verified PMID metadata"
                    }
                )
                else -> null
            }
        }
    }

    private fun normalizeReferenceText(text: String): String {
        return text.replace(Regex("\\s+"), " ").trim().lowercase()
    }

    private fun canonicalReferenceTextKey(text: String): String {
        return stripReferenceMetadata(text)
            .replace(Regex("""^\s*(?:\[\d+]|\d+[.)])\s*"""), "")
            .replace(Regex("""https?://\S+""", RegexOption.IGNORE_CASE), "")
            .replace(Regex("""[^\p{L}\p{N}\s]"""), " ")
            .replace(Regex("\\s+"), " ")
            .trim()
            .lowercase()
    }

    private fun calculateLevenshteinDistance(s1: String, s2: String): Int {
        val dp = IntArray(s2.length + 1) { it }
        for (i in 1..s1.length) {
            var prev = dp[0]
            dp[0] = i
            for (j in 1..s2.length) {
                val temp = dp[j]
                if (s1[i - 1] == s2[j - 1]) {
                    dp[j] = prev
                } else {
                    dp[j] = minOf(dp[j - 1], dp[j], prev) + 1
                }
                prev = temp
            }
        }
        return dp[s2.length]
    }

    private fun isFuzzyMatch(ref1: String, ref2: String): Boolean {
        val k1 = canonicalReferenceTextKey(ref1)
        val k2 = canonicalReferenceTextKey(ref2)
        if (k1.isBlank() || k2.isBlank()) return false
        val dist = calculateLevenshteinDistance(k1, k2)
        val maxLen = maxOf(k1.length, k2.length)
        if (maxLen == 0) return true
        val similarity = 1.0 - (dist.toDouble() / maxLen.toDouble())
        return similarity >= 0.90
    }

    private fun deduplicateFuzzy(references: List<ReferenceJson>): List<ReferenceJson> {
        val result = mutableListOf<ReferenceJson>()
        for (ref in references) {
            val hasDuplicate = result.any { existing ->
                val sharedIdentities = referenceIdentities(ref).intersect(referenceIdentities(existing).toSet())
                if (sharedIdentities.isNotEmpty()) {
                    true
                } else {
                    isFuzzyMatch(ref.referenceText, existing.referenceText)
                }
            }
            if (!hasDuplicate) {
                result.add(ref)
            }
        }
        return result
    }

    private fun formatReferencesForVariable(references: List<ReferenceJson>): String {
        return references.filter { it.hasRequiredPmid() }.mapIndexed { index, reference ->
            buildString {
                append(index + 1)
                append(". ")
                append(reference.completeCitationText())
            }.trim()
        }.joinToString("\n")
    }

    private suspend fun mergeReferencesIntoGlobalVariable(
        references: List<ReferenceJson>,
        verifyNewReferences: Boolean = true
    ) {
        if (references.isEmpty()) return

        seedVerifiedReferenceCache(_uiState.value.verifiedPubMedReferences)
        val existing = parseReferencesVariable(_uiState.value.variables)
        val existingKeys = existing.flatMap(::referenceIdentities).toMutableSet()
        val newReferences = references
            .filter { it.referenceText.isNotBlank() || !it.pmid.isNullOrBlank() || !it.doi.isNullOrBlank() }
            .filter { ref -> referenceIdentities(ref).none { it in existingKeys } }
            .filter { ref -> existing.none { ext -> isFuzzyMatch(ref.referenceText, ext.referenceText) } }
            .distinctBy { ref ->
                referenceIdentity(ref) ?: canonicalReferenceTextKey(ref.referenceText)
            }

        if (newReferences.isEmpty()) {
            if (existing.any { it.hasRequiredPmid() }) {
                updateVariable("References_Vancouver", formatReferencesForVariable(existing.filter { it.hasRequiredPmid() }))
            }
            return
        }

        val verifiedNew = if (verifyNewReferences) {
            verifyReferencesWithPubMed(newReferences)
        } else {
            newReferences.mapNotNull { reference ->
                findCachedVerifiedReference(reference, stripReferenceMetadata(reference.referenceText))
                    ?: reference.takeIf { it.hasRequiredPmid() }
            }
        }

        val merged = deduplicateFuzzy(existing + verifiedNew)
            .filter { it.hasRequiredPmid() }
            .mapIndexed { index, ref -> ref.copy(citation = serializedCitation(index + 1)) }

        if (merged.isNotEmpty()) {
            updateVariable("References_Vancouver", formatReferencesForVariable(merged))
            seedVerifiedReferenceCache(merged)
            persistVerifiedReferenceCache()
        }
    }

    private suspend fun generateAllChapters(
        targetChapterNames: Set<String>? = null,
        finalStatus: String? = null
    ) {
        if (_uiState.value.vpsAutoCompleteEnabled) {
            queuePendingChaptersForVps(targetChapterNames)
            _uiState.update { state ->
                state.copy(
                    processing = false,
                    hasErrors = state.chapters.any { it.status == Chapter.ChapterStatus.ERROR },
                    status = finalStatus ?: "Queued for VPS auto-complete"
                )
            }
            saveSessionToFirebase()
            return
        }

        val chapters = _uiState.value.chapters.toMutableList()
        for ((index, chapter) in chapters.withIndex()) {
            if (chapter.name.lowercase() in autoGeneratedChapterNames) continue
            if (chapter.status == Chapter.ChapterStatus.SUCCESS) continue
            if (targetChapterNames != null && chapter.name !in targetChapterNames) continue

            var attempt = 0
            var success = false
            var workingChapter: Chapter? = null

            while (!success && attempt < maxChapterGenerationAttempts) {
                attempt += 1
                val previewVariables = getVariablesForChapter(chapter.name, _uiState.value.variables)
                workingChapter = chapter.copy(
                    status = Chapter.ChapterStatus.LOADING,
                    errorMessage = null,
                    content = if (chapter.content.isBlank()) {
                        chapterWritingPreview(chapter.name, attempt, previewVariables)
                    } else {
                        chapter.content
                    }
                )
                chapters[index] = workingChapter!!
                _uiState.update {
                    it.copy(
                        chapters = chapters.toList(),
                        status = "Generating ${chapter.name} (${index + 1}/${chapters.size}) attempt $attempt",
                        progressCurrent = index + 1,
                        activeChapterName = chapter.name
                    )
                }
                saveSessionToFirebase()

                success = generateSingleChapter(workingChapter!!, retryAttempt = attempt - 1)
                if (!success) {
                    _uiState.update {
                        it.copy(
                        chapters = chapters.toList(),
                        hasErrors = true,
                        status = "Retrying ${chapter.name} after attempt $attempt",
                        progressCurrent = index + 1,
                        activeChapterName = chapter.name
                    )
                }
                    saveSessionToFirebase()
                    delay((1500L * attempt).coerceAtMost(10_000L))
                }
            }

            if (!success) {
                val failedChapter = (workingChapter ?: chapter).copy(
                    status = Chapter.ChapterStatus.ERROR,
                    errorMessage = (workingChapter?.errorMessage ?: "AI could not generate ${chapter.name} after $maxChapterGenerationAttempts attempts"),
                    content = chapter.content
                )
                chapters[index] = failedChapter
                _uiState.update {
                    it.copy(
                        chapters = chapters.toList(),
                        hasErrors = true,
                        status = "Skipped ${chapter.name} after $maxChapterGenerationAttempts failed attempts",
                        progressCurrent = index + 1,
                        completionPercent = computeCompletionPercent(chapters),
                        activeChapterName = chapter.name
                    )
                }
                saveSessionToFirebase()
                continue
            }

            chapters[index] = workingChapter!!.copy(status = Chapter.ChapterStatus.SUCCESS)
            _uiState.update {
                it.copy(
                    chapters = chapters.toList(),
                    hasErrors = chapters.any { ch -> ch.status == Chapter.ChapterStatus.ERROR },
                    completionPercent = computeCompletionPercent(chapters)
                )
            }
            saveSessionToFirebase()
        }

        _uiState.update {
            it.copy(
                processing = false,
                status = finalStatus ?: if (it.hasErrors) "Completed with errors" else "Complete",
                completionPercent = computeCompletionPercent(_uiState.value.chapters),
                activeChapterName = ""
            )
        }
        saveSessionToFirebase()
    }


    private suspend fun generateSingleChapter(
        chapter: Chapter,
        customPrompt: String? = null,
        retryAttempt: Int = 0
    ): Boolean {
        return try {
            if (chapter.name.equals("Literature Review", ignoreCase = true)) {
                return generateLiteratureReviewChapter(chapter, customPrompt, retryAttempt = retryAttempt)
            }

            val schema = chapterSchemas[chapter.name.lowercase()]
            val vars = getVariablesForChapter(chapter.name, _uiState.value.variables)
            val prompt = customPrompt ?: buildChapterPrompt(chapter.name, vars, schema, forceDetailed = false)
            chapter.workerPrompt = prompt
            chapter.workerPromptUpdatedAt = System.currentTimeMillis()

            if (chapter.name.equals("References", true) || chapter.name.equals("Bibliography", true)) {
                val sourceReferences = parseReferencesVariable(_uiState.value.variables)
                if (sourceReferences.isNotEmpty()) {
                    val normalizedRefs = requirePubMedVerifiedReferences(sourceReferences, chapter.name).mapIndexed { index, ref ->
                        ref.copy(
                            citation = (index + 1).toString()
                        )
                    }

                    chapter.rawJson = gson.toJson(
                        ReferencesJson(
                            references = normalizedRefs.mapIndexed { index, ref ->
                                ReferenceEntry(
                                    number = index + 1,
                                    text = ref.completeCitationText(),
                                    pmid = ref.pmid,
                                    doi = ref.doi
                                )
                            }
                        )
                    )
                    chapter.content = buildString {
                        appendLine(chapter.name.uppercase())
                        normalizedRefs.forEach { ref ->
                        appendLine("${ref.citation}. ${ref.completeCitationText()}")
                        }
                    }.trim()
                    chapter.tables = emptyList()
                    chapter.figures = emptyList()
                    chapter.charts = emptyList()
                    chapter.abbreviations = emptyList()
                    chapter.chapterReferences = normalizedRefs
                    mergeReferencesIntoGlobalVariable(normalizedRefs, verifyNewReferences = false)
                    chapter.status = Chapter.ChapterStatus.SUCCESS
                    chapter.errorMessage = null
                    return true
                }
            }

            val rawJson = callAiJsonWithContinuation(prompt, chapter.name, retryAttempt = retryAttempt)
            chapter.rawJson = rawJson

            val parsed = validateOrThrowParsedChapterValue(chapter.name, rawJson, schema)
            chapter.content = if (schema != null) {
                schema.formatter(parsed)
            } else {
                val generic = parsed as ThesisChapterJson
                formatChapterPreview(generic)
            }
            chapter.sections = when {
                parsed is ThesisChapterJson -> parsed.sections
                else -> convertStructuredPayloadToSections(chapter.name, parsed)
            }
            showParsedChapterWritingDraft(chapter.name, chapter.content, rawJson)

            if (schema != null) {
                when (parsed) {
                    is ResultsJson -> {
                        chapter.tables = parsed.tables.mapNotNull { table ->
                            val normalized = normalizeResultTable(table)
                            Log.d("TableDebug", "Title=${normalized.title} Headers=${normalized.headers.size} Rows=${normalized.rows.size}")
                            if (normalized.headers.isEmpty() || normalized.rows.isEmpty()) {
                                Log.e("TableDebug", "Rejected table because it has no usable data: ${normalized.title}")
                                return@mapNotNull null
                            }
                            normalized
                        }

                        chapter.charts = ensureRequiredCharts(
                            chapterName = chapter.name,
                            charts = sanitizeChartsForUse(parsed.charts, chapter.name),
                            tables = chapter.tables
                        )
                        chapter.figures = ensureRequiredFigures(
                            chapter.name,
                            chartsToFigures(chapter.charts)
                        )
                        chapter.abbreviations = emptyList()
                        chapter.chapterReferences = emptyList()
                    }
                    is ThesisChapterJson -> {
                        // Extract tables from sections
                        chapter.tables = (parsed.tables + parsed.sections.mapNotNull { it.table })
                            .map(::normalizeThesisTable)
                        chapter.figures = collectChapterFigures(parsed)
                        chapter.charts = ensureRequiredCharts(
                            chapterName = chapter.name,
                            charts = sanitizeChartsForUse(parsed.charts, chapter.name),
                            tables = chapter.tables
                        )
                        chapter.abbreviations = parsed.abbreviations
                        chapter.chapterReferences = requirePubMedVerifiedReferences(collectChapterReferences(parsed), chapter.name)
                    }
                    is ReferencesJson -> {
                        val rawRefs = parsed.references.map { entry ->
                            sanitizeReferenceForLookup(
                                ReferenceJson(
                                    citation = entry.number.takeIf { it > 0 }?.toString().orEmpty(),
                                    referenceText = entry.text,
                                    pmid = entry.pmid,
                                    doi = entry.doi
                                )
                            )
                        }
                        val verifiedRefs = requirePubMedVerifiedReferences(rawRefs, chapter.name)
                        chapter.tables = emptyList()
                        chapter.figures = emptyList()
                        chapter.charts = emptyList()
                        chapter.abbreviations = emptyList()
                        chapter.chapterReferences = verifiedRefs.mapIndexed { index, ref ->
                            ref.copy(citation = (index + 1).toString())
                        }
                        chapter.content = buildString {
                            appendLine(chapter.name.uppercase())
                            chapter.chapterReferences.forEach { ref ->
                                appendLine("${ref.citation}. ${ref.completeCitationText()}")
                            }
                        }.trim()
                    }
                    else -> {
                        // Other custom schemas (TitlePageJson, etc.) – no tables/charts
                        chapter.tables = emptyList()
                        chapter.figures = emptyList()
                        chapter.charts = emptyList()
                        chapter.abbreviations = emptyList()
                        chapter.chapterReferences = emptyList()
                    }
                }
            } else {
                val generic = parsed as ThesisChapterJson
                chapter.tables = generic.sections.mapNotNull { it.table }
                chapter.figures = collectChapterFigures(generic)
                chapter.charts = ensureRequiredCharts(
                    chapterName = chapter.name,
                    charts = sanitizeChartsForUse(generic.charts, chapter.name),
                    tables = chapter.tables
                )
                chapter.abbreviations = generic.abbreviations
                chapter.chapterReferences = requirePubMedVerifiedReferences(collectChapterReferences(generic), chapter.name)
            }

            chapter.figures = ensureRequiredFigures(chapter.name, chapter.figures)

            val extractedAbbrs = extractAbbreviationsFromText(chapter.content)
            if (extractedAbbrs.isNotEmpty()) {
                val existingAbbrs = chapter.abbreviations.orEmpty()
                chapter.abbreviations = (existingAbbrs + extractedAbbrs).distinctBy { it.shortForm }
            }

            if (chapter.name.equals("Sample Size", ignoreCase = true)) {
                val correction = verifySampleSizeCalculation(chapter.content)
                if (correction != null) {
                    throw Exception("Math Validation Error: $correction")
                }
            }

            if (requiresFigureForChapter(chapter.name) && chapter.figures.isEmpty()) {
                throw IllegalStateException("Missing required figure for ${chapter.name}")
            }

            if (isWeakChapterContent(chapter.content)) {
                throw IllegalStateException("Empty or weak parsed chapter content for ${chapter.name}")
            }

            if (requiresPubMedCitations(chapter.name)) {
                if (chapter.chapterReferences.isEmpty() || !chapter.chapterReferences.all { it.hasRequiredPmid() } || !hasInTextCitation(chapter.content)) {
                    throw IllegalStateException("Missing PubMed citations with PMID in generated chapter")
                }
            }

            // Append metadata to content for UI visibility (optional, keeps backward compatibility)
            val contentWithMetadata = buildString {
                append(chapter.content)
                if (chapter.figures.isNotEmpty()) {
                    appendLine("\n\n📊 FIGURES")
                    chapter.figures.forEach { fig ->
                        appendLine("${fig.figureNumber}: ${fig.title}")
                        if (fig.caption.isNotBlank()) appendLine("   Caption: ${fig.caption}")
                    }
                }
                if (chapter.tables.isNotEmpty()) {
                    appendLine("\n\n📋 TABLES")
                    chapter.tables.forEach { table ->
                        appendLine("${table.tableNumber}: ${table.title}")
                    }
                }
                if (chapter.charts.isNotEmpty()) {
                    appendLine("\n\n📈 CHARTS")
                    chapter.charts.forEach { chart ->
                        appendLine("${chart.chartId}: ${chart.title} (${chart.type})")
                    }
                }
                if (chapter.abbreviations.isNotEmpty()) {
                    appendLine("\n\n📖 ABBREVIATIONS")
                    chapter.abbreviations.forEach { abbr ->
                        appendLine("${abbr.shortForm} = ${abbr.fullForm}")
                    }
                }
            }
            chapter.content = contentWithMetadata

            chapter.status = Chapter.ChapterStatus.SUCCESS
            chapter.errorMessage = null
            chapter.textBoxes = ensureChapterTextBoxes(chapter)
            mergeReferencesIntoGlobalVariable(chapter.chapterReferences, verifyNewReferences = false)
            true
        } catch (e: Exception) {
            chapter.errorMessage = e.message
            chapter.status = Chapter.ChapterStatus.ERROR
            false
        }
    }

    private fun queuePendingChaptersForVps(
        targetChapterNames: Set<String>? = null,
        customPrompts: Map<String, String> = emptyMap()
    ) {
        val isRetryRequest = targetChapterNames != null
        val updated = _uiState.value.chapters.map { chapter ->
            if (chapter.name.lowercase() in autoGeneratedChapterNames) {
                chapter.copy(syncEnabled = false)
            } else if (targetChapterNames != null && chapter.name !in targetChapterNames) {
                chapter
            } else {
                val retryPrompt = customPrompts[chapter.name].orEmpty()
                var errorMsg: String? = null
                var hasError = false
                val prompt = retryPrompt.ifBlank {
                    chapter.workerPrompt.ifBlank {
                        runCatching {
                            if (chapter.name.equals("Literature Review", ignoreCase = true)) {
                                val sources = fetchLiteratureReviewSources()
                                if (sources.isEmpty()) {
                                    hasError = true
                                    errorMsg = "Literature Review needs stored PubMed abstracts from the Abstracts tab. Refresh the Abstracts tab before generating this chapter."
                                    ""
                                } else {
                                    buildLiteratureReviewPrompt(sources, null)
                                }
                            } else {
                                val schema = chapterSchemas[chapter.name.lowercase()]
                                val vars = getVariablesForChapter(chapter.name, _uiState.value.variables)
                                buildChapterPrompt(chapter.name, vars, schema, forceDetailed = false)
                            }
                        }.getOrElse { e ->
                            hasError = true
                            errorMsg = e.message
                            chapter.workerPrompt
                        }
                    }
                }
                chapter.copy(
                    status = if (hasError) Chapter.ChapterStatus.ERROR else if (isRetryRequest) Chapter.ChapterStatus.PENDING else chapter.status,
                    errorMessage = if (hasError) errorMsg else if (isRetryRequest) null else chapter.errorMessage,
                    syncEnabled = !hasError,
                    workerStatus = if (hasError) "error" else "queued",
                    retryCount = if (isRetryRequest) 0 else chapter.retryCount,
                    lastRetryAt = if (isRetryRequest) System.currentTimeMillis() else chapter.lastRetryAt,
                    workerPrompt = prompt.ifBlank { chapter.workerPrompt },
                    workerPromptUpdatedAt = if (prompt.isNotBlank()) System.currentTimeMillis() else chapter.workerPromptUpdatedAt,
                    lastWorkerError = if (hasError) errorMsg.orEmpty() else "",
                    lockedBy = "",
                    lockedUntil = 0L
                )
            }
        }
        _uiState.update { it.copy(chapters = updated) }
        saveSessionToFirebase()
    }
    private suspend fun showParsedChapterWritingDraft(chapterName: String, content: String, rawJson: String = "") {
        updateLoadingChapterDraft(chapterName, content, rawJson)
        val visibleDelayMs = (content.length * 3L).coerceIn(1_200L, 4_500L)
        delay(visibleDelayMs)
    }

    private fun updateLoadingChapterDraft(chapterName: String, content: String, rawJson: String = "") {
        _uiState.update { state ->
            val index = state.chapters.indexOfFirst { it.name.equals(chapterName, ignoreCase = true) }
            if (index < 0) return@update state
            val updated = state.chapters.toMutableList()
            val current = updated[index]
            if (current.status != Chapter.ChapterStatus.LOADING) return@update state
            updated[index] = current.copy(
                content = content,
                rawJson = rawJson.ifBlank { current.rawJson }
            )
            state.copy(chapters = updated, activeChapterName = current.name)
        }
    }

    private fun chapterWritingPreview(chapterName: String, attempt: Int, variables: List<Variable> = emptyList()): String {
        val sectionNames = chapterSchemas[chapterName.lowercase()]
            ?.schemaDescription
            ?.let { Regex(""""heading"\s*:\s*"([^"]+)"""").findAll(it).map { match -> match.groupValues[1] }.distinct().take(8).toList() }
            .orEmpty()

        val variableLines = variables
            .filter { it.value.isNotBlank() }
            .take(6)
            .joinToString("\n") { "- ${it.name}: ${it.value.replace(Regex("\\s+"), " ").take(140)}" }

        return buildString {
            appendLine("AI is writing $chapterName...")
            appendLine()
            appendLine("Attempt $attempt")
            if (sectionNames.isNotEmpty()) {
                appendLine()
                appendLine("Planned sections:")
                sectionNames.forEach { appendLine("- $it") }
            }
            if (variableLines.isNotBlank()) {
                appendLine()
                appendLine("Using thesis details:")
                appendLine(variableLines)
            }
        }.trim()
    }

    private suspend fun generateLiteratureReviewChapter(
        chapter: Chapter,
        customInstructions: String? = null,
        retryAttempt: Int = 0
    ): Boolean {
        _uiState.update { it.copy(status = "Using stored PubMed abstracts for Literature Review...") }
        val sources = fetchLiteratureReviewSources()
        if (sources.isEmpty()) {
            throw IllegalStateException("Literature Review needs stored PubMed abstracts from the Abstracts tab. Refresh the Abstracts tab before generating this chapter.")
        }

        val selectedSources = sources
        val prompt = buildLiteratureReviewPrompt(selectedSources, customInstructions)
        chapter.workerPrompt = prompt
        chapter.workerPromptUpdatedAt = System.currentTimeMillis()
        val rawJson = callAiJsonWithContinuation(prompt, chapter.name, retryAttempt = retryAttempt)
        val parsed = try {
            parseThesisChapterJson(rawJson, chapter.name)
        } catch (e: Exception) {
            throw Exception("JSON Syntax Error: ${e.message}\nRaw Output: ${rawJson.take(300)}")
        }
        if (!isMeaningfulThesisChapter(parsed)) {
            throw Exception("Schema Validation Error: Literature Review narrative structure is empty or weak.")
        }
        val sourceReferences = selectedSources.mapIndexed { index, source ->
            source.reference.copy(citation = serializedCitation(index + 1))
        }
        val sanitizedParsed = parsed.copy(
            sections = parsed.sections.map { it.copy(references = emptyList()) },
            chapterReferences = sourceReferences
        )
        val serializedRawJson = gson.toJson(sanitizedParsed)

        chapter.rawJson = serializedRawJson
        chapter.content = formatChapterPreview(sanitizedParsed.copy(chapterReferences = emptyList()))
        showParsedChapterWritingDraft(chapter.name, chapter.content, serializedRawJson)
        chapter.tables = sanitizedParsed.tables.map(::normalizeThesisTable)
        chapter.figures = ensureRequiredFigures(chapter.name, collectChapterFigures(sanitizedParsed))
        chapter.charts = ensureRequiredCharts(
            chapterName = chapter.name,
            charts = sanitizeChartsForUse(sanitizedParsed.charts, chapter.name),
            tables = chapter.tables
        )
        chapter.abbreviations = sanitizedParsed.abbreviations
        chapter.chapterReferences = sourceReferences
        chapter.textBoxes = ensureChapterTextBoxes(chapter)
        chapter.status = Chapter.ChapterStatus.SUCCESS
        chapter.errorMessage = null

        mergeReferencesIntoGlobalVariable(sourceReferences, verifyNewReferences = false)
        return true
    }

    private fun buildLiteratureReviewPrompt(
        sources: List<PubMedReviewSource>,
        customInstructions: String? = null
    ): String {
        val schema = chapterSchemas["literature review"]?.schemaDescription ?: defaultGenericSchema()
        val diseaseTopic = currentDiseaseTopic().ifBlank { _uiState.value.thesisTitle }
        val referenceCursor = currentReferenceSequence()
        val referenceLedger = buildReferenceLedgerContext()
        val promptControl = buildPromptSizeControlInstructions()
        val sourceBlockRaw = sources.mapIndexed { index, source ->
            val citation = serializedCitation(index + 1)
            """
            SOURCE ${index + 1} $citation
            PMID: ${source.reference.pmid.orEmpty()}
            DOI: ${source.reference.doi.orEmpty()}
            Title: ${source.title.ifBlank { source.reference.referenceText.substringBefore(".") }}
            Vancouver reference: ${source.reference.completeCitationText()}
            Separated abstract sections:
            ${formatAbstractSectionsForPrompt(source.abstractSections)}
            Complete PubMed abstract:
            ${source.abstractText}
            """.trimIndent()
        }.joinToString("\n\n")
        val sourceBlock = capPromptBlock(
            sourceBlockRaw,
            if (_uiState.value.promptSectionSplittingEnabled) _uiState.value.promptMaxChars.coerceIn(4000, 30000) / 2 else _uiState.value.promptMaxChars.coerceIn(4000, 30000),
            "literature review abstracts"
        )

        return """
            Return ONLY valid JSON. Do not put markdown outside JSON.
            Follow this JSON schema exactly:
            $schema

            Chapter: LITERATURE REVIEW.
            This chapter must not be a generic AI-written overview. Write as if a human researcher personally reviewed the PubMed abstracts below and is synthesizing the literature in thesis style.
            Use exactly these ${sources.size} verified PubMed sources. Do not invent or add any other studies, citations, PMID values, DOI values, or references.
            Write one opening synthesis paragraph, then one paragraph per abstract source so the chapter reads like a ${sources.size}-abstract literature review rather than a generic overview.
            Every paragraph must synthesize evidence from the abstracts, not merely list them. Use local Vancouver citations [1] to [${sources.size}] matching the source numbers below.
            The current global reference cursor for the thesis is [${referenceCursor}]. If the chapter needs to mention any newly introduced study beyond the provided source set, continue numbering from that cursor rather than restarting at [1].
            If a reference already appears in the thesis reference ledger below, reuse its exact existing citation number. Do not assign a fresh number to the same article.
            The review must include disease definition, epidemiology, risk factors, pathophysiology, types/classification where relevant, investigations in literature, relation of investigations with disease, comparative study findings, limitations in existing literature, and a final research gap.
            Emphasize each study's **purpose**, **methods**, **results**, and **conclusion** in natural academic prose, but do not use headings named Purpose/Methods/Results/Conclusion for every individual source.
            Inside JSON string values, bold only key clinical terms, major findings, methods, outcomes, and research-gap phrases using **bold** markers. Do not bold citation labels or reference text.
            Store the same ${sources.size} sources in `chapter_references` with citation values [1] to [${sources.size}], complete Vancouver `reference_text`, verified `pmid`, DOI when available, and `pubmed_verified=true`.
            Keep full citation text out of chapter body. Use only inline citation labels in content.
            $promptControl
            Recognized disease/topic: "$diseaseTopic".
            Current thesis reference ledger:
            $referenceLedger
            ${customInstructions?.takeIf { it.isNotBlank() }?.let { "Additional retry instructions from user: $it" }.orEmpty()}

            Verified PubMed abstract sources:
            $sourceBlock
        """.trimIndent()
    }

    private fun formatAbstractSectionsForPrompt(sections: List<PubMedAbstractSectionJson>): String {
        if (sections.isEmpty()) return "No separated sections available."
        return sections.joinToString("\n") { section ->
            "${section.category.uppercase()} (${section.label}): ${section.text}"
        }
    }

    private fun buildPromptSizeControlInstructions(): String {
        val state = _uiState.value
        val maxChars = state.promptMaxChars.coerceIn(4000, 30000)
        return if (state.promptSectionSplittingEnabled) {
            """
            Prompt size control:
            - Keep the generated JSON concise enough for one worker response, target under approximately $maxChars characters when possible.
            - For long chapters, write the chapter as clearly separated schema sections and keep each section self-contained so the worker/app can retry or merge section-sized output.
            - Prefer fewer, stronger paragraphs per section over one oversized chapter body. Preserve all required schema keys even when compacting.
            """.trimIndent()
        } else {
            "Prompt size control: section splitting is disabled; still keep the JSON valid and avoid unnecessary repetition."
        }
    }

    private fun capPromptBlock(text: String, maxChars: Int, label: String): String {
        if (maxChars <= 0 || text.length <= maxChars) return text
        val head = (maxChars * 0.72f).toInt().coerceAtLeast(400)
        val tail = (maxChars - head).coerceAtLeast(200)
        return buildString {
            append(text.take(head).trimEnd())
            append("\n\n[$label compacted for prompt size; non-essential middle content omitted]\n\n")
            append(text.takeLast(tail).trimStart())
        }
    }

    private fun buildChapterPrompt(
        chapterName: String,
        variables: List<Variable>,
        schema: ChapterSchema? = null,
        forceDetailed: Boolean = false
    ): String {
        val maxPromptChars = _uiState.value.promptMaxChars.coerceIn(4000, 30000)
        val splitPrompts = _uiState.value.promptSectionSplittingEnabled
        val data = capPromptBlock(
            buildNormalizedVariableContext(chapterName, variables),
            if (splitPrompts) maxPromptChars / 4 else maxPromptChars,
            "thesis data"
        )
        val referenceLedger = capPromptBlock(
            buildReferenceLedgerContext(),
            if (splitPrompts) maxPromptChars / 5 else maxPromptChars,
            "reference ledger"
        )
        val titleTopicContext = buildTitleTopicContext()
        val recognizedDiseaseTopic = diseaseTopicFromVariables(variables)
            .ifBlank { currentDiseaseTopic() }
            .ifBlank { "Not specified" }
        val jsonSchema = schema?.schemaDescription ?: defaultGenericSchema()
        val instructions = getSpecialInstructions(chapterName)
        val pubMedEvidence = capPromptBlock(
            buildVerifiedPubMedEvidenceContext(chapterName),
            if (splitPrompts) maxPromptChars / 3 else maxPromptChars,
            "PubMed evidence"
        )
        val chartRules = getChartFormatRules(chapterName)
        val figureRules = getFigureRequirementInstructions(chapterName)
        val referenceRules = getReferenceRelevanceInstructions(chapterName)
        val capabilitySpec = thesisCapabilitySpec()
        val chapterType = chapterTypeFor(chapterName)
        val referenceCursor = currentReferenceSequence()
        val lastReferenceNumber = (referenceCursor - 1).coerceAtLeast(0)
        val referenceChapterRules = getReferenceChapterRules(chapterName)
        val approvedReferenceCorpus = capPromptBlock(
            buildApprovedReferenceCorpusContext(chapterName),
            if (splitPrompts) maxPromptChars / 4 else maxPromptChars,
            "approved references"
        )
        val promptControl = buildPromptSizeControlInstructions()

        return """
            Return ONLY valid JSON. Do not put markdown outside JSON.
            Follow this JSON schema exactly:
            $jsonSchema

            Thesis system capabilities to target:
            $capabilitySpec

            Chapter family: $chapterType
            Keep the structure professional, thesis-like, and internally consistent.
            Write like a medical thesis: formal chapter title, numbered sections where appropriate, concise subheadings, objective narration, and figure/table references inside the chapter body.
            For narrative sections, put the complete body text in the `paragraphs` array. Use one string per paragraph. Keep `content` as a short section summary only when needed. Every paragraph that makes a factual claim must include inline citation labels such as [1] or [2].
            Inside JSON string values, wrap key clinical terms, major findings, statistically important values, conclusions, and thesis-critical phrases with markdown-style bold markers like **important point**. Use bold sparingly: highlight only the highest-value words or short phrases, not whole paragraphs, tables, citation labels, PMID/DOI metadata, or reference text.
            Recognized disease/condition/topic for this thesis: "$recognizedDiseaseTopic".
            Use this exact recognized disease/condition/topic as the hard filter for every disease-specific claim and every disease-specific PubMed reference.
            For every factual point, bullet, and numbered item in narrative chapters, add a local Vancouver citation inline like [1], [2], [3]. Each inline citation number must correspond to a reference object in `chapter_references` or the section's `references` array with the same citation value. Every reference object must include a complete Vancouver citation in `reference_text`, a real `pmid`, and a DOI when PubMed provides one. References without PMID are invalid and must not be used. The app strips PMID/DOI from the citation text and validates the remaining citation over PubMed before accepting it. The app will later serialize all chapters into one global reference order.
            Reference relevance is mandatory: every reference must be directly related to "$recognizedDiseaseTopic", the thesis title/topic, keywords, and the chapter section where it is cited. Do not add random PubMed-indexed papers only because they have a PMID.
            The chapter-specific approved evidence below is the only allowed reference source for this chapter. It contains selected user references after PubMed validation and relevant PubMed similar articles downloaded from those references. Do not cite or emit any article that is absent from that evidence JSON.
            In all generated JSON, `chapter_references` and section `references` must be copied from the chapter-specific evidence only. Keep citations in JSON as `[n]` labels matching the evidence item you cited inline. Do not create fresh reference numbers outside the selected evidence.
            The app reads inline citation labels from each paragraph and remaps them after PubMed verification into final thesis-wide reference numbers, so paragraph citation labels and reference object citation labels must stay consistent within this chapter.
            Do not leave uncited claims in the chapter body.
            If this chapter uses a figure, add 3-5 explanatory points about what the figure shows, why it matters clinically, and how it supports the surrounding thesis text. Cite those figure explanation points with PubMed-backed Vancouver citations and add the same sources to `chapter_references`.
            Keep headings stable and hierarchical so the PDF exporter can generate table of contents, lists of tables/figures/abbreviations, bookmarks, page breaks, and running header/footer logic from the output.
            Use the exact section headings requested by the schema. Do not invent extra top-level keys.
            $promptControl

            Mandatory thesis title/topic context for this AI request:
            $titleTopicContext

            Reference selection must use this title/topic context. Choose PubMed citations whose article title/abstract directly matches "$recognizedDiseaseTopic" plus the title/topic, population, exposure/intervention/investigation, and outcomes listed above.
            Current global reference cursor: [${referenceCursor}]. Last assigned reference number: [${lastReferenceNumber}].
            If this chapter introduces new references, continue numbering from [${referenceCursor}] and never restart at [1] unless the thesis has no prior references.

            Use the following thesis data (only relevant parts):
            $data

            Current thesis reference ledger:
            $referenceLedger

            $approvedReferenceCorpus

            $pubMedEvidence
            Current global reference cursor: [${referenceCursor}].
            This cursor is for final serialization only. Do not introduce references outside the approved corpus, and do not restart or invent numbering when the chapter is a retry or continuation of a previous session.

            Additional instructions: $instructions
            $referenceRules
            $referenceChapterRules
            $figureRules
            $chartRules
            ${if (forceDetailed) "Produce maximum detail and depth." else ""}
        """.trimIndent()
    }

    private fun buildReferenceLedgerContext(limit: Int = Int.MAX_VALUE): String {
        val ledger = currentReferenceLedgerReferences()
            .filter { it.hasRequiredPmid() }
            .distinctBy { ref ->
                referenceIdentity(ref) ?: canonicalReferenceTextKey(ref.referenceText)
            }
            .mapIndexed { index, ref ->
                ref.copy(citation = serializedCitation(index + 1))
            }
            .take(limit)

        if (ledger.isEmpty()) return "No verified references are available yet."

        return ledger.joinToString("\n") { ref ->
            "${ref.citation}. ${ref.completeCitationText()}"
        }
    }

    private fun currentReferenceLedgerReferences(): List<ReferenceJson> {
        return (
            parseReferencesVariable(_uiState.value.variables) +
                _uiState.value.verifiedPubMedReferences +
                _uiState.value.chapters.flatMap { it.chapterReferences }
            )
            .filter { it.hasRequiredPmid() }
            .distinctBy { ref ->
                referenceIdentity(ref) ?: canonicalReferenceTextKey(ref.referenceText)
            }
    }

    private fun approvedReferenceCorpusReferences(): List<ReferenceJson> {
        val ordered = linkedMapOf<String, ReferenceJson>()

        fun addReference(reference: ReferenceJson) {
            if (!reference.hasRequiredPmid()) return
            val key = referenceIdentity(reference) ?: canonicalReferenceTextKey(reference.referenceText)
            if (key.isBlank()) return
            ordered.putIfAbsent(
                key,
                reference.copy(
                    referenceText = reference.completeCitationText(),
                    pmid = reference.pmid?.trim(),
                    doi = reference.doi?.trim(),
                    pubmedVerified = true
                )
            )
        }

        parseReferencesVariable(_uiState.value.variables).forEach(::addReference)
        _uiState.value.verifiedPubMedReferences.forEach(::addReference)
        _uiState.value.verifiedPubMedAbstractSources.forEach { source ->
            addReference(
                ReferenceJson(
                    referenceText = source.citation.ifBlank { source.title.ifBlank { "PMID: ${source.pmid}" } },
                    pmid = source.pmid,
                    doi = source.doi,
                    pubmedVerified = true
                )
            )
            val relatedArticles = source.similarArticles.ifEmpty { source.citedBy }
            relatedArticles.forEach { similar ->
                addReference(
                    ReferenceJson(
                        referenceText = similar.citation.ifBlank { similar.title.ifBlank { "PMID: ${similar.pmid}" } },
                        pmid = similar.pmid,
                        doi = similar.doi,
                        pubmedVerified = true
                    )
                )
            }
        }

        return ordered.values.toList()
    }

    private fun approvedReferenceEvidence(): List<ReferenceEvidence> {
        val evidence = linkedMapOf<String, ReferenceEvidence>()

        fun add(item: ReferenceEvidence) {
            if (!item.reference.hasRequiredPmid()) return
            val key = referenceIdentity(item.reference) ?: canonicalReferenceTextKey(item.reference.referenceText)
            if (key.isBlank()) return
            evidence.putIfAbsent(key, item)
        }

        val abstractByPmid = _uiState.value.verifiedPubMedAbstractSources
            .associateBy { it.pmid.trim() }

        val baseReferences = (
            parseReferencesVariable(_uiState.value.variables) +
                _uiState.value.verifiedPubMedReferences
            )
            .filter { it.hasRequiredPmid() }
            .distinctBy { ref -> referenceIdentity(ref) ?: canonicalReferenceTextKey(ref.referenceText) }

        baseReferences.forEach { reference ->
            val pmid = reference.pmid?.trim().orEmpty()
            val source = abstractByPmid[pmid]
            add(
                ReferenceEvidence(
                    reference = reference.copy(
                        referenceText = source?.citation?.ifBlank { reference.completeCitationText() } ?: reference.completeCitationText(),
                        doi = reference.doi ?: source?.doi,
                        pubmedVerified = true
                    ),
                    sourceType = "validated_reference",
                    title = source?.title.orEmpty(),
                    abstractText = source?.abstractText.orEmpty(),
                    abstractSections = source?.abstractSections.orEmpty()
                )
            )
        }

        _uiState.value.verifiedPubMedAbstractSources.forEach { source ->
            source.similarArticles.ifEmpty { source.citedBy }.forEach { similar ->
                add(
                    ReferenceEvidence(
                        reference = ReferenceJson(
                            referenceText = similar.citation.ifBlank { similar.title.ifBlank { "PMID: ${similar.pmid}" } },
                            pmid = similar.pmid,
                            doi = similar.doi,
                            pubmedVerified = true
                        ),
                        sourceType = "similar_article",
                        parentPmid = source.pmid,
                        title = similar.title,
                        abstractText = similar.abstractText,
                        abstractSections = similar.abstractSections
                    )
                )
            }
        }

        return evidence.values.toList()
    }

    private fun selectEvidenceForChapter(chapterName: String, limit: Int = 12): List<ReferenceEvidence> {
        val normalizedChapter = chapterName.lowercase()
        val titleTopic = buildTitleTopicContext()
        val diseaseTopic = currentDiseaseTopic()
        val variablesText = _uiState.value.variables.joinToString(" ") { "${it.name} ${it.value}" }
        val chapterTerms = when (normalizedChapter) {
            "introduction", "background", "disease burden", "epidemiology" ->
                "definition epidemiology prevalence incidence burden risk population mortality morbidity public health"
            "pathophysiology" ->
                "pathophysiology mechanism biology pathology inflammation molecular progression complication"
            "current treatment" ->
                "treatment therapy management intervention drug surgery procedure standard care outcome"
            "literature review", "research gap", "need for study" ->
                "study objective methods results conclusion review evidence gap limitation investigation outcome"
            "investigations" ->
                "diagnosis diagnostic investigation imaging laboratory biomarker test score sensitivity specificity"
            "materials and methods", "study design", "sample size", "sampling technique", "statistical analysis" ->
                "study design methodology sample size statistics analysis cohort case control randomized protocol"
            "discussion", "recommendations", "future scope" ->
                "findings comparison similar contrast outcome implication limitation recommendation future research"
            else -> normalizedChapter
        }
        val query = listOf(titleTopic, diseaseTopic, normalizedChapter, chapterTerms, variablesText)
            .joinToString(" ")
            .lowercase()
        val queryTokens = queryTokens(query)

        val allEvidence = approvedReferenceEvidence()
        val selected = allEvidence
            .map { evidence ->
                val haystack = listOf(
                    evidence.reference.referenceText,
                    evidence.title,
                    evidence.abstractText,
                    evidence.abstractSections.joinToString(" ") { "${it.category} ${it.label} ${it.text}" },
                    evidence.sourceType
                ).joinToString(" ").lowercase()
                val score = evidenceScore(queryTokens, haystack, evidence.sourceType)
                evidence to score
            }
            .filter { (_, score) -> score > 0 }
            .sortedWith(
                compareByDescending<Pair<ReferenceEvidence, Int>> { it.second }
                    .thenBy { if (it.first.sourceType == "validated_reference") 0 else 1 }
            )
            .map { it.first }

        val fallbackValidated = allEvidence
            .filter { it.sourceType == "validated_reference" }
            .filter { evidence -> selected.none { it.reference.pmid?.trim() == evidence.reference.pmid?.trim() } }
        val selectedWithFallback = selected + fallbackValidated

        val validated = selectedWithFallback.filter { it.sourceType == "validated_reference" }.take(6)
        val similar = selectedWithFallback.filter { it.sourceType == "similar_article" }.take((limit - validated.size).coerceAtLeast(0))
        return (validated + similar).distinctBy { it.reference.pmid?.trim().orEmpty() }.take(limit)
    }

    private fun queryTokens(text: String): Set<String> {
        val stop = setOf(
            "the", "and", "with", "from", "that", "this", "study", "thesis", "title", "topic",
            "not", "specified", "primary", "objective", "objectives", "method", "methods"
        )
        return text
            .replace(Regex("""[^\p{L}\p{N}\s]"""), " ")
            .split(Regex("\\s+"))
            .map { it.trim().lowercase() }
            .filter { it.length >= 4 && it !in stop && !it.all(Char::isDigit) }
            .take(120)
            .toSet()
    }

    private fun evidenceScore(queryTokens: Set<String>, haystack: String, sourceType: String): Int {
        if (queryTokens.isEmpty() || haystack.isBlank()) return 0
        val haystackTokens = queryTokens(haystack)
        val overlap = queryTokens.count { it in haystackTokens }
        val sourceBoost = if (sourceType == "validated_reference") 8 else 0
        val abstractBoost = if (haystack.length > 300) 4 else 0
        return overlap * 3 + sourceBoost + abstractBoost
    }

    private fun buildApprovedReferenceCorpusContext(chapterName: String): String {
        if (!requiresPubMedCitations(chapterName) && chapterName.lowercase() !in setOf("references", "bibliography")) {
            return "Approved reference corpus: this chapter does not require citations."
        }

        val selectedEvidence = selectEvidenceForChapter(chapterName)
        if (selectedEvidence.isEmpty()) {
            return """
                Approved reference corpus:
                []
                No PubMed-validated references are available. For narrative chapters that require citations, do not invent references; keep claims general or fail validation.
            """.trimIndent()
        }

        val corpusJson = selectedEvidence.mapIndexed { index, evidence ->
            val reference = evidence.reference.copy(citation = serializedCitation(index + 1))
            mapOf(
                "citation" to reference.citation,
                "reference_text" to reference.completeCitationText(),
                "pmid" to reference.pmid.orEmpty(),
                "doi" to reference.doi.orEmpty(),
                "pubmed_verified" to true,
                "source_type" to evidence.sourceType,
                "parent_pmid" to evidence.parentPmid.orEmpty(),
                "title" to evidence.title,
                "abstract_text" to evidence.abstractText,
                "abstract_sections" to evidence.abstractSections.map { section ->
                    mapOf(
                        "label" to section.label,
                        "category" to section.category,
                        "text" to section.text
                    )
                }
            )
        }

        val focusedSectionBlocks = buildChapterAbstractSectionContext(chapterName, selectedEvidence)
        val abstractBlocks = selectedEvidence
            .filter { it.abstractText.isNotBlank() }
            .joinToString("\n\n") { source ->
                val index = selectedEvidence.indexOf(source) + 1
                val reference = source.reference.copy(citation = serializedCitation(index))
                """
                ${reference.citation} ${source.sourceType}${source.parentPmid?.let { " from PMID $it" }.orEmpty()}
                PMID: ${reference.pmid.orEmpty()}
                DOI: ${reference.doi.orEmpty()}
                Citation: ${reference.completeCitationText()}
                Complete abstract:
                ${source.abstractText}
                """.trimIndent()
            }

        return """
            Chapter-specific approved evidence JSON:
            ${gson.toJson(corpusJson)}

            Citation rules for this corpus:
            - Use only citation labels present in `Chapter-specific approved evidence JSON`.
            - `chapter_references` must contain only objects copied from that JSON, with the same citation, reference_text, pmid, doi, and pubmed_verified=true.
            - `validated_reference` entries are the user's original PubMed-validated references and should be preferred.
            - `similar_article` entries are PubMed similar articles attached to `parent_pmid`; use them only when their title/abstract directly supports the chapter claim.
            - If the corpus does not support a claim, rewrite the claim so it does not need unsupported citation evidence.
            - References/Bibliography must include only corpus items actually cited in generated chapters.

            Chapter-relevant separated abstract sections:
            $focusedSectionBlocks

            Selected abstracts for this chapter:
            ${abstractBlocks.ifBlank { "No abstracts are available for the approved corpus. Use only the verified citation metadata above." }}
        """.trimIndent()
    }

    private fun abstractSectionCategoriesForChapter(chapterName: String): Set<String> {
        val normalized = chapterName.trim().lowercase()
        return when {
            normalized in setOf("materials and methods", "study design", "study setting", "study duration",
                "study population", "sample size", "sampling technique", "data collection", "variables collected",
                "investigations", "study procedure", "outcome measures", "statistical analysis") ->
                setOf("materials and methods")
            normalized in setOf("results", "observations") ->
                setOf("results", "methods and results")
            normalized == "discussion" ->
                setOf("discussion", "results and discussion", "discussion and conclusion", "results", "conclusion")
            normalized in setOf("conclusion", "summary", "recommendations", "limitations", "future scope") ->
                setOf("conclusion", "discussion and conclusion", "discussion", "results")
            normalized in setOf("introduction", "background", "disease burden", "epidemiology", "pathophysiology") ->
                setOf("background", "objective", "introduction", "abstract")
            normalized in setOf("literature review", "research gap", "need for study") ->
                setOf("objective", "materials and methods", "results", "discussion", "conclusion")
            normalized in setOf("aim of study", "objectives", "hypothesis") ->
                setOf("objective", "background", "introduction")
            normalized == "abstract" ->
                setOf("background", "objective", "materials and methods", "results", "discussion", "conclusion", "abstract")
            else -> emptySet()
        }
    }

    private fun buildChapterAbstractSectionContext(
        chapterName: String,
        selectedEvidence: List<ReferenceEvidence>
    ): String {
        val categories = abstractSectionCategoriesForChapter(chapterName)
        if (categories.isEmpty()) {
            return "No abstract section routing is required for this chapter."
        }

        val blocks = selectedEvidence.mapIndexedNotNull { index, evidence ->
            val citation = serializedCitation(index + 1)
            val sections = evidence.abstractSections
                .filter { section -> section.category.lowercase() in categories && section.text.isNotBlank() }
            if (sections.isEmpty()) return@mapIndexedNotNull null
            """
            $citation PMID: ${evidence.reference.pmid.orEmpty()} ${evidence.sourceType}
            ${sections.joinToString("\n") { section -> "${section.category.uppercase()} (${section.label}): ${section.text}" }}
            """.trimIndent()
        }

        if (blocks.isEmpty()) {
            return "No matching separated sections were found; use the complete abstracts only if directly relevant."
        }

        val routingName = when {
            "materials and methods" in categories -> "Methods"
            "results" in categories -> "Results"
            "discussion" in categories -> "Discussion"
            "conclusion" in categories -> "Conclusion"
            "objective" in categories -> "Objective/Aim"
            else -> categories.joinToString()
        }

        return """
            Route "$routingName" sections from all selected abstracts into this chapter's evidence synthesis.
            Use the citation shown before each section, and copy that same source into chapter_references when cited.

            ${blocks.joinToString("\n\n")}
        """.trimIndent()
    }

    private fun buildTitleTopicContext(): String {
        fun variableValue(vararg names: String): String {
            val normalizedNames = names.map(::normalizeVariableKey)
            return _uiState.value.variables.firstOrNull { variable ->
                normalizeVariableKey(variable.name) in normalizedNames
            }?.value.orEmpty()
        }

        val title = _uiState.value.thesisTitle
            .ifBlank { variableValue("Title", "Thesis Title", "Project Title") }
            .ifBlank { "Not specified" }
        val diseaseTopic = variableValue("Disease_or_Condition", "Title_Disease_Topic", "Disease Topic")
            .ifBlank { deriveDiseaseTopic(title) }
            .ifBlank { "Not specified" }
        val keywords = variableValue("Keywords", "MeSH Keywords").ifBlank { "Not specified" }
        val aim = variableValue("Aim_of_Study", "Aim of Study", "Aim").ifBlank { "Not specified" }
        val primaryObjectives = variableValue("Objectives_primary", "Primary Objectives", "Objectives").ifBlank { "Not specified" }
        val population = variableValue("Study_Population", "Study Population").ifBlank { "Not specified" }
        val investigations = variableValue("Investigations").ifBlank { "Not specified" }
        val outcomes = variableValue("Outcome_Measures_primary", "Primary Outcome", "Outcome Measures").ifBlank { "Not specified" }

        return """
            - Thesis title/topic: $title
            - Disease/condition/topic variable: $diseaseTopic
            - Keywords/MeSH terms: $keywords
            - Aim: $aim
            - Primary objectives: $primaryObjectives
            - Study population: $population
            - Main investigations/exposures/interventions: $investigations
            - Primary outcomes: $outcomes
            - Hard reference filter: every PubMed reference must be about "$diseaseTopic" or must combine "$diseaseTopic" with the exact investigation/exposure/outcome claim. Reject PubMed articles on other diseases/topics even if they have a valid PMID.
        """.trimIndent()
    }

    private fun buildVerifiedPubMedEvidenceContext(chapterName: String): String {
        val normalizedChapter = chapterName.lowercase()
        if (normalizedChapter !in setOf(
                "introduction",
                "background",
                "disease burden",
                "epidemiology",
                "pathophysiology",
                "current treatment",
                "research gap",
                "need for study",
                "discussion"
            )
        ) return ""

        val sources = _uiState.value.verifiedPubMedAbstractSources
            .filter { it.abstractText.isNotBlank() && it.pmid.isNotBlank() }
            .take(5)
        if (sources.isEmpty()) return ""

        val sourceBlock = sources.mapIndexed { index, source ->
            val citation = serializedCitation(index + 1)
            val similarBlock = source.similarArticles.ifEmpty { source.citedBy }.take(5).joinToString("\n") { similar ->
                "- Similar article PMID ${similar.pmid}; DOI: ${similar.doi.orEmpty()}; ${similar.title.ifBlank { similar.citation }}"
            }.ifBlank { "- No similar articles captured from PubMed HTML." }
            """
            SOURCE ${index + 1} $citation
            PMID: ${source.pmid}
            DOI: ${source.doi.orEmpty()}
            Title: ${source.title}
            Vancouver reference: ${source.citation}
            PubMed abstract:
            ${source.abstractText}
            Similar articles from PubMed:
            $similarBlock
            """.trimIndent()
        }.joinToString("\n\n")

        val chapterUse = when (normalizedChapter) {
            "discussion" -> """
                Use these abstracts to write a human-style discussion:
                - Merge the abstracts with the present study findings.
                - Explicitly state similar findings as "Similar findings were reported by Author et al. [n]" when supported by an abstract.
                - Explicitly state contrary findings as "In contrast..." when an abstract differs from the present study.
                - Give plausible clinical, methodological, population, sample-size, setting, measurement, bias, or confounding explanations for agreement and disagreement.
                - Separate real study data from interpretive or possibly manipulated/unsupported claims; do not overstate any abstract.
            """.trimIndent()
            else -> """
                Use these abstracts to strengthen Introduction/Background with these required areas:
                - Disease burden
                - Epidemiology
                - Pathophysiology
                - Current treatment
                - Research gap
                - Need for study
                Synthesize the sources into these headings where appropriate and keep every factual claim cited.
            """.trimIndent()
        }

        return """
            Verified PubMed evidence already downloaded after reference verification:
            $chapterUse

            $sourceBlock
        """.trimIndent()
    }

    private fun thesisCapabilitySpec(): String = """
        PDF: professional cover page, logo page, Roman front matter numbering, TOC, list of tables, list of figures, list of abbreviations, running headers/footers, chapter page breaks, page numbering, cross-references, hyperlinks, bookmarks, watermark-ready output.
        Tables: auto-generated from observations, numeric detection, statistical summaries, comparisons, demographic tables, multi-page support, repeated headers, auto widths, wrapped cells, professional styling.
        Graphs: bar, horizontal bar, line, pie, scatter, histogram, box-plot-ready structure, legends, themes, PNG/SVG export-ready structure, table-driven graph generation, correlation and trend graphs.
        Figures: automatic figure references, captions, numbering, download hints, attribution-ready fields, placement-aware descriptions.
        References: Vancouver numbering, mandatory PMID fields, DOI/PubMed validation-ready fields, duplicate detection, global serialized bibliography generation. Every factual sentence or bullet in narrative chapters must carry an inline PubMed-backed Vancouver citation and the same sources must be present in the chapter_references array. The final app pass renumbers every chapter into one global [n] sequence and writes the References/List of References from that same sequence. Do not invent or use references without PubMed PMID.
        Reference relevance: citations must be selected for the thesis title/topic and chapter claim being supported, never as random PMID-bearing references.
        Quality: completeness, missing sections/tables/figures/references detection, consistency checks, methodology validation, variable usage validation.
    """.trimIndent()

    private fun requiresPubMedCitations(chapterName: String): Boolean {
        if (chapterName.lowercase() in methodologyFormChapterNames) return false

        return when (chapterName.lowercase()) {
            "title", "certificate", "declaration", "acknowledgements", "proforma",
            "abstract", "references", "bibliography", "appendices",
            "patient consent form (english)", "patient consent form (hindi)",
            "hypothesis",
            "keywords", "table of contents", "list of tables", "list of figures", "list of abbreviations"
            -> false
            else -> true
        }
    }

    private fun requiresFigureForChapter(chapterName: String): Boolean {
        return chapterName.lowercase() in setOf(
            "introduction",
            "background",
            "literature review",
            "materials and methods",
            "study design",
            "investigations",
            "study procedure",
            "discussion"
        )
    }

    private fun requiredFigureCountForChapter(chapterName: String): Int {
        return when (chapterName.lowercase()) {
            "literature review" -> 4
            else -> if (requiresFigureForChapter(chapterName)) 1 else 0
        }
    }

    private fun requiresChartForChapter(chapterName: String): Boolean {
        return chapterName.lowercase() in setOf("results", "observations")
    }

    private suspend fun ensureRequiredCharts(
        chapterName: String,
        charts: List<ChartJson>,
        tables: List<ThesisTableJson>
    ): List<ChartJson> {
        val renderable = sanitizeChartsForUse(charts, chapterName)
        if (!requiresChartForChapter(chapterName) || renderable.isNotEmpty()) return renderable

        val fallback = buildFallbackChartFromTables(chapterName, tables)
            ?: buildFallbackChartFromVariables(chapterName)
            ?: return renderable

        return sanitizeChartsForUse(renderable + fallback, chapterName)
    }

    private fun ensureRequiredFigures(chapterName: String, figures: List<FigureJson>): List<FigureJson> {
        val requiredCount = requiredFigureCountForChapter(chapterName)
        if (requiredCount == 0) return figures

        val cleaned = figures
            .filter { it.title.isNotBlank() || it.caption.isNotBlank() || it.imageSearchQuery.isNotBlank() }
            .distinctBy { listOf(it.title, it.imageSearchQuery).joinToString("|").lowercase() }
            .mapIndexed { index, figure ->
                figure.copy(figureNumber = figure.figureNumber.ifBlank { (index + 1).toString() })
            }

        if (cleaned.size >= requiredCount) return cleaned

        val existingKeys = cleaned
            .map { listOf(it.title, it.imageSearchQuery).joinToString("|").lowercase() }
            .toMutableSet()
        val additions = defaultFigureSpecsForChapter(chapterName)
            .filter { spec -> listOf(spec.title, spec.imageSearchQuery).joinToString("|").lowercase() !in existingKeys }
            .take(requiredCount - cleaned.size)
            .mapIndexed { index, spec ->
                existingKeys += listOf(spec.title, spec.imageSearchQuery).joinToString("|").lowercase()
                spec.copy(figureNumber = (cleaned.size + index + 1).toString())
            }

        return cleaned + additions
    }

    private fun chartsToFigures(charts: List<ChartJson>): List<FigureJson> {
        return charts.mapIndexed { index, chart ->
            FigureJson(
                figureNumber = (index + 1).toString(),
                title = chart.title.ifBlank { "Results chart ${index + 1}" },
                caption = "Chart generated from thesis result data.",
                imageSearchQuery = chart.title.ifBlank { "medical thesis results chart" },
                imageUrl = "",
                sourceUrl = ""
            )
        }
    }

    private fun defaultFigureSpecsForChapter(chapterName: String): List<FigureJson> {
        val diseaseTopic = currentDiseaseTopic().ifBlank { _uiState.value.thesisTitle }.ifBlank { "the study topic" }
        return when (chapterName.lowercase()) {
            "literature review" -> listOf(
                FigureJson(
                    title = "Epidemiology and burden of $diseaseTopic",
                    caption = "Disease burden, prevalence/incidence pattern, demographic distribution, or geographic variation relevant to the reviewed literature.",
                    imageSearchQuery = "$diseaseTopic epidemiology prevalence incidence burden chart"
                ),
                FigureJson(
                    title = "Risk factors and risk pathway for $diseaseTopic",
                    caption = "Modifiable and non-modifiable risk factors and their relationship to disease development or progression.",
                    imageSearchQuery = "$diseaseTopic risk factors pathway diagram"
                ),
                FigureJson(
                    title = "Pathophysiology of $diseaseTopic",
                    caption = "Mechanistic pathway, pathological change, anatomical involvement, or clinical progression described in the literature.",
                    imageSearchQuery = "$diseaseTopic pathophysiology mechanism diagram"
                ),
                FigureJson(
                    title = "Investigation workflow for $diseaseTopic",
                    caption = "Diagnostic or investigation workflow showing how tests support diagnosis, severity assessment, prognosis, or follow-up.",
                    imageSearchQuery = "$diseaseTopic diagnostic investigation workflow algorithm"
                )
            )
            "introduction", "background" -> listOf(
                FigureJson(
                    title = "Conceptual overview of $diseaseTopic",
                    caption = "Overview figure showing disease burden, anatomy, pathophysiology, or core clinical concept introduced in this chapter.",
                    imageSearchQuery = "$diseaseTopic anatomy pathophysiology clinical overview diagram"
                )
            )
            "materials and methods", "study design" -> listOf(
                FigureJson(
                    title = "Study design and participant flow",
                    caption = "Flow diagram summarizing screening, eligibility, enrollment, data collection, analysis, and final study groups.",
                    imageSearchQuery = "medical thesis study design participant flowchart"
                )
            )
            "investigations" -> listOf(
                FigureJson(
                    title = "Diagnostic investigation workflow for $diseaseTopic",
                    caption = "Workflow linking clinical suspicion, investigation selection, interpretation, severity assessment, and follow-up.",
                    imageSearchQuery = "$diseaseTopic diagnostic investigation algorithm workflow"
                )
            )
            "study procedure" -> listOf(
                FigureJson(
                    title = "Stepwise study procedure",
                    caption = "Procedure flowchart summarizing consent, baseline assessment, investigations, intervention or observation, follow-up, and analysis.",
                    imageSearchQuery = "clinical study procedure flowchart"
                )
            )
            "discussion" -> listOf(
                FigureJson(
                    title = "Interpretive framework for study findings",
                    caption = "Mechanism, comparison, or clinical algorithm connecting the present findings with published evidence and practical implications.",
                    imageSearchQuery = "$diseaseTopic clinical algorithm mechanism discussion diagram"
                )
            )
            else -> listOf(
                FigureJson(
                    title = "Clinically relevant figure for $diseaseTopic",
                    caption = "Figure supporting the chapter narrative and thesis topic.",
                    imageSearchQuery = "$diseaseTopic clinical diagram"
                )
            )
        }
    }

    private fun buildFallbackChartFromTables(chapterName: String, tables: List<ThesisTableJson>): ChartJson? {
        tables.forEach { table ->
            val points = table.rows.mapNotNull { row ->
                val label = row.firstOrNull { cell -> cell.toChartNumberOrNull() == null && cell.trim().length >= 2 }
                    ?.trim()
                    ?.take(48)
                    ?: return@mapNotNull null
                val value = row.firstNotNullOfOrNull { cell -> cell.toChartNumberOrNull() }
                    ?: return@mapNotNull null
                label to value
            }
                .distinctBy { it.first.lowercase() }
                .take(8)

            if (points.size >= 2) {
                return ChartJson(
                    chartId = "${chapterName.lowercase().replace(Regex("[^a-z0-9]+"), "_").trim('_')}_summary_chart",
                    title = table.title.ifBlank { "${chapterName} summary chart" },
                    type = "bar",
                    chartTemplate = "category_bar",
                    xAxisLabel = table.headers.firstOrNull(),
                    yAxisLabel = table.headers.drop(1).firstOrNull(),
                    labels = points.map { it.first },
                    values = points.map { it.second }
                )
            }
        }
        return null
    }

    private fun buildFallbackChartFromVariables(chapterName: String): ChartJson? {
        val sourceText = _uiState.value.variables
            .filter { normalizeVariableKey(it.name) in setOf("results_text", "observations", "tables") }
            .joinToString("\n") { it.value }
        val points = Regex("""([A-Za-z][A-Za-z0-9 /%()_-]{2,60})[:=\-]\s*([0-9]+(?:\.[0-9]+)?)\s*%?""")
            .findAll(sourceText)
            .map { match -> match.groupValues[1].trim().take(48) to match.groupValues[2].toDouble() }
            .distinctBy { it.first.lowercase() }
            .take(8)
            .toList()

        if (points.size < 2) return null
        return ChartJson(
            chartId = "${chapterName.lowercase().replace(Regex("[^a-z0-9]+"), "_").trim('_')}_summary_chart",
            title = "${chapterName} summary chart",
            type = "bar",
            chartTemplate = "category_bar",
            labels = points.map { it.first },
            values = points.map { it.second }
        )
    }

    private fun String.toChartNumberOrNull(): Double? {
        val cleaned = trim()
            .replace(",", "")
            .replace("%", "")
            .replace(Regex("""^[^\d.-]+"""), "")
            .replace(Regex("""[^\d.-]+$"""), "")
        return cleaned.toDoubleOrNull()
    }

    private fun getFigureRequirementInstructions(chapterName: String): String {
        if (!requiresFigureForChapter(chapterName)) return ""

        if (chapterName.equals("literature review", ignoreCase = true)) {
            return """
                Figure requirements for Literature Review:
                - Add separate figures for epidemiology, risk factors, pathophysiology, and investigations whenever the disease topic supports them.
                - The epidemiology figure should show disease burden, prevalence/incidence trend, demographic distribution, or geographic pattern.
                - The risk-factor figure should show modifiable/non-modifiable risk factors or a risk pathway framework.
                - The pathophysiology figure should show disease mechanism, pathology, anatomical change, molecular pathway, or clinical progression.
                - The investigations figure should show diagnostic workflow, investigation algorithm, device/machine image, test interpretation diagram, or how investigations map to disease severity.
                - Put each figure either in the top-level `figures` array or inside the most relevant section's `figures` array.
                - Use concrete `image_search_query` values that can retrieve each image.
                - Near each figure, add 3-5 explanatory points about what it shows, why it matters clinically, and how it supports the literature review.
                - Every figure explanation point and factual review statement must have an inline Vancouver citation.
                - Add PubMed-indexed references for those points to `chapter_references`, with complete Vancouver `reference_text`, real `pmid`, `doi` if available, and `pubmed_verified=true`.
            """.trimIndent()
        }

        if (chapterName.equals("investigations", ignoreCase = true)) {
            return """
                Figure and table requirements for Investigations:
                - Add at least one figure showing a diagnostic workflow, investigation algorithm, device/machine image, disease-specific test interpretation diagram, or investigation-to-severity pathway.
                - Put the figure either in the top-level `figures` array or inside the most relevant section's `figures` array.
                - Use a concrete `image_search_query` that can retrieve the image.
                - In the nearby section content, bullets, or numbered_points, add 3-5 figure explanation points.
                - Add a table titled `Investigation - Purpose - Expected finding - Interpretation - PMID-backed reference`.
                - Every figure explanation point, table interpretation, and factual investigation statement must have an inline Vancouver citation.
                - Add PubMed-indexed references for those points to `chapter_references`, with complete Vancouver `reference_text`, real `pmid`, `doi` if available, and `pubmed_verified=true`.
            """.trimIndent()
        }

        val figureType = when (chapterName.lowercase()) {
            "introduction", "background" -> "disease pathology, pathophysiology, anatomy, or disease-burden concept figure"
            "literature review" -> "epidemiology, risk-factor, pathophysiology, and investigation figures"
            "materials and methods", "study design" -> "study design flowchart or participant-flow diagram"
            "investigations" -> "diagnostic workflow, investigation algorithm, device/machine image, or test interpretation diagram"
            "study procedure" -> "procedure flowchart or stepwise study-process diagram"
            "discussion" -> "mechanism, comparison, proposed clinical algorithm, or implication figure"
            else -> "clinically relevant thesis figure"
        }

        return """
            Figure requirement for this chapter:
            - Add at least one figure relevant to this chapter: $figureType.
            - Put the figure either in the top-level `figures` array or inside the most relevant section's `figures` array.
            - Use a concrete `image_search_query` that can retrieve the image, for example disease pathology diagram, diagnostic device, investigation workflow, or clinical algorithm.
            - In the nearby section content, bullets, or numbered_points, add 3-5 figure explanation points.
            - Every figure explanation point must have an inline Vancouver citation.
            - Add PubMed-indexed references for those figure explanation points to `chapter_references`, with complete Vancouver `reference_text`, real `pmid`, `doi` if available, and `pubmed_verified=true`.
        """.trimIndent()
    }

    private fun getReferenceRelevanceInstructions(chapterName: String): String {
        if (!requiresPubMedCitations(chapterName)) return ""
        val recognizedDiseaseTopic = currentDiseaseTopic().ifBlank { "the recognized Disease_or_Condition" }
        val cursor = currentReferenceSequence()
        val lastReferenceNumber = (cursor - 1).coerceAtLeast(0)

        return """
            Reference selection rules:
            - The recognized disease/condition/topic is "$recognizedDiseaseTopic".
            - Treat "$recognizedDiseaseTopic" as the mandatory disease/topic variable for all disease-specific citations.
            - Use only articles from the approved reference corpus whose article title/abstract is about "$recognizedDiseaseTopic" and whose claim also matches the exact chapter statement being cited.
            - Reject any PMID about a different disease/topic, even if it is PubMed-indexed and medically valid.
            - For methodology-only claims, use approved-corpus references related to the specific method, tool, diagnostic test, statistic, guideline, or study design used in this thesis.
            - Do not cite broad unrelated papers, random clinical studies, or papers that merely share one generic medical word.
            - For each reference object, write a complete Vancouver citation in `reference_text`, and also fill `pmid` with the real PubMed PMID and `doi` with the DOI if PubMed provides one.
            - It is acceptable if `reference_text` also ends with `PMID: ...` and `DOI: ...`; the app will strip PMID/DOI from `reference_text` and validate the remaining citation against PubMed.
            - Provide PMID and DOI only from the approved corpus entry being cited. The app will verify the supplied PMID/DOI against the stripped citation text over PubMed.
            - Do not fabricate a PMID, DOI, author list, journal, or title. Do not add any PubMed article absent from the approved corpus. If the approved corpus cannot support a claim, omit that reference and rewrite the claim more generally.
            - Each `reference_text` must contain authors, real article title, journal/source, year/date, and enough Vancouver metadata to show why it is related to the thesis topic.
            - References in `chapter_references` must only include sources actually cited inline in this chapter.
            - If a reference already exists in the thesis, reuse its current citation number exactly. Do not create a fresh number for the same article.
            - If you are paraphrasing with an already-listed reference, keep that reference's existing `[n]` index.
            - Current global reference cursor is [$cursor]. Last assigned reference number is [$lastReferenceNumber]. These are for final serialization only; never invent a new reference outside the approved corpus.
        """.trimIndent()
    }

    private fun getReferenceChapterRules(chapterName: String): String {
        val normalized = chapterName.lowercase()
        if (normalized !in setOf("references", "bibliography", "list of references")) return ""
        val cursor = currentReferenceSequence()
        val lastReferenceNumber = (cursor - 1).coerceAtLeast(0)

        return """
            Reference-list chapter rules:
            - This chapter is a reference list, not a narrative chapter.
            - Output only the schema's `references` array. Do not add prose, inline citations, tables, or figures.
            - Use the same sequential source list for References and Bibliography; only the heading/formatting differs.
            - Continue numbering from the global cursor [$cursor]. The last assigned reference number is [$lastReferenceNumber].
            - Do not renumber from [1] unless there are no prior references in the thesis.
            - Keep the order strictly sequential and aligned with the thesis-wide citation index.
        """.trimIndent()
    }


    private fun hasInTextCitation(text: String): Boolean {
        return Regex("""(\[\d+(?:\s*[-,]\s*\d+)*\]|\(\d+(?:\s*[-,]\s*\d+)*\))""").containsMatchIn(text)
    }

    private data class VariableGroup(
        val heading: String,
        val keys: List<String>
    )

    private fun buildNormalizedVariableContext(chapterName: String, variables: List<Variable>): String {
        val canonical = ensureDiseaseTopicVariable(variables)
            .map { Variable(normalizeVariableKey(it.name), it.value.trim()) }
            .filter { it.name.isNotBlank() && it.value.isNotBlank() }

        val groups = chapterVariableGroups(chapterName)
        val usedKeys = mutableSetOf<String>()

        val renderedGroups = mutableListOf<String>()
        groups.forEach { group ->
            val matched = canonical.filter { variable ->
                group.keys.any { key -> variable.name.equals(normalizeVariableKey(key), ignoreCase = true) }
            }.distinctBy { it.name.lowercase() }

            if (matched.isNotEmpty()) {
                usedKeys += matched.map { it.name.lowercase() }
                renderedGroups += buildString {
                    appendLine("${group.heading}:")
                    matched.forEach { variable ->
                        appendLine("- ${denormalizeVariableKey(variable.name)}: ${variable.value}")
                    }
                }.trimEnd()
            }
        }

        val remaining = canonical.filterNot { usedKeys.contains(it.name.lowercase()) }
            .sortedBy { it.name }

        if (remaining.isNotEmpty()) {
            renderedGroups += buildString {
                appendLine("Other relevant variables:")
                remaining.forEach { variable ->
                    appendLine("- ${denormalizeVariableKey(variable.name)}: ${variable.value}")
                }
            }.trimEnd()
        }

        val contextBody = if (renderedGroups.isEmpty()) {
            "No chapter-specific variables were extracted."
        } else {
            renderedGroups.joinToString("\n\n")
        }

        return """
            Normalized chapter variables:
            Chapter: ${chapterName.uppercase()}

            $contextBody
        """.trimIndent()
    }

    private fun chapterVariableGroups(chapterName: String): List<VariableGroup> {
        return when (chapterName.lowercase()) {
            "title" -> listOf(
                VariableGroup("Title page metadata", listOf("Title", "Subtitle", "Degree", "Department", "Institution", "Guide", "Co-guide", "Student Name", "Year", "Registration Number"))
            )

            "certificate", "declaration", "acknowledgements" -> listOf(
                VariableGroup("Front matter text", listOf("Certificate", "Declaration", "Acknowledgements", "Guide", "HOD", "Student Name", "Date"))
            )

            "abstract" -> listOf(
                VariableGroup("Structured abstract", listOf("Disease_or_Condition", "Abstract_structured", "Keywords", "Abstract", "Background", "Aim", "Methods", "Results", "Conclusion"))
            )

            "keywords" -> listOf(
                VariableGroup("Keyword list", listOf("Disease_or_Condition", "Keywords"))
            )

            "introduction", "background", "literature review", "research gap", "aim of study", "objectives", "hypothesis" -> listOf(
                VariableGroup("Core thesis framing", listOf("Disease_or_Condition", "Introduction_text", "Background_text", "Literature_Review_text", "Research_Gap", "Aim_of_Study", "Objectives_primary", "Objectives_secondary", "Hypothesis_null", "Hypothesis_alternate")),
                VariableGroup("Source references", listOf("References_Vancouver"))
            )

            "materials and methods", "study design", "study setting", "study duration", "study population", "inclusion criteria", "exclusion criteria", "sample size", "sampling technique", "data collection", "variables collected", "investigations", "study procedure", "outcome measures", "statistical analysis", "ethical considerations" -> listOf(
                VariableGroup("Study design and setting", listOf("Disease_or_Condition", "Study_Design", "Study_Setting", "Study_Duration", "Study_Population")),
                VariableGroup("Eligibility and sampling", listOf("Inclusion_Criteria", "Exclusion_Criteria", "Sample_Size", "Sampling_Technique")),
                VariableGroup("Methods details", listOf("Data_Collection", "Variables_Collected", "Investigations", "Study_Procedure", "Outcome_Measures_primary", "Outcome_Measures_secondary", "Statistical_Analysis", "Ethical_Considerations"))
            )

            "results", "observations" -> listOf(
                VariableGroup("Results narrative", listOf("Results_text", "Observations")),
                VariableGroup("Tables", listOf("Tables")),
                VariableGroup("Figures", listOf("Figures")),
                VariableGroup("Outcome references", listOf("References_Vancouver"))
            )

            "discussion" -> listOf(
                VariableGroup("Discussion narrative", listOf("Discussion_text", "Comparison_with_Literature", "Limitations")),
                VariableGroup("References", listOf("References_Vancouver"))
            )

            "conclusion" -> listOf(
                VariableGroup("Conclusion summary", listOf("Conclusion_text"))
            )

            "summary" -> listOf(
                VariableGroup("Summary", listOf("Summary"))
            )

            "recommendations" -> listOf(
                VariableGroup("Recommendations", listOf("Recommendations", "Future_Scope", "References_Vancouver"))
            )

            "limitations" -> listOf(
                VariableGroup("Limitations", listOf("Limitations"))
            )

            "future scope" -> listOf(
                VariableGroup("Future scope", listOf("Future_Scope", "Recommendations"))
            )

            "references", "bibliography" -> listOf(
                VariableGroup("Reference list", listOf("References_Vancouver"))
            )

            "appendices" -> listOf(
                VariableGroup("Appendices", listOf("Appendices"))
            )

            "proforma" -> listOf(
                VariableGroup("Clinical form fields", listOf("Patient Name", "Age", "Sex", "OPD/IP No", "Address", "History", "Examination", "Investigations", "Diagnosis"))
            )

            "patient consent form (english)", "patient consent form (hindi)" -> listOf(
                VariableGroup("Consent form fields", listOf("Introduction", "Procedure", "Risks", "Benefits", "Confidentiality", "Signature", "Date"))
            )

            else -> listOf(
                VariableGroup("Relevant thesis variables", canonicalVariableHints())
            )
        }
    }

    private fun canonicalVariableHints(): List<String> {
        return listOf(
            "Title", "Degree", "Department", "Institution", "Guide", "Student Name", "Abstract_structured",
            "Keywords", "Introduction_text", "Background_text", "Literature_Review_text", "Research_Gap",
            "Aim_of_Study", "Objectives_primary", "Objectives_secondary", "Study_Design", "Study_Setting",
            "Study_Duration", "Study_Population", "Inclusion_Criteria", "Exclusion_Criteria", "Sample_Size",
            "Sampling_Technique", "Data_Collection", "Variables_Collected", "Investigations", "Study_Procedure",
            "Outcome_Measures_primary", "Outcome_Measures_secondary", "Statistical_Analysis", "Ethical_Considerations",
            "Results_text", "Observations", "Discussion_text", "Conclusion_text", "Summary", "Recommendations",
            "Future_Scope", "References_Vancouver"
        )
    }

    private fun normalizeVariableKey(name: String): String {
        return name.trim()
            .replace(Regex("[^A-Za-z0-9]+"), "_")
            .replace(Regex("_+"), "_")
            .trim('_')
            .lowercase()
    }

    private fun denormalizeVariableKey(name: String): String {
        return when (name.lowercase()) {
            "opd_ip_no" -> "OPD/IP No"
            "co_guide" -> "Co-guide"
            "student_name" -> "Student Name"
            "abstract_structured" -> "Abstract structured"
            "research_gap" -> "Research Gap"
            "aim_of_study" -> "Aim of Study"
            "study_design" -> "Study Design"
            "study_setting" -> "Study Setting"
            "study_duration" -> "Study Duration"
            "study_population" -> "Study Population"
            "sample_size" -> "Sample Size"
            "sampling_technique" -> "Sampling Technique"
            "data_collection" -> "Data Collection"
            "variables_collected" -> "Variables Collected"
            "study_procedure" -> "Study Procedure"
            "outcome_measures_primary" -> "Outcome Measures Primary"
            "outcome_measures_secondary" -> "Outcome Measures Secondary"
            "statistical_analysis" -> "Statistical Analysis"
            "ethical_considerations" -> "Ethical Considerations"
            "references_vancouver" -> "References Vancouver"
            "future_scope" -> "Future Scope"
            else -> name.split('_').joinToString(" ") { part ->
                part.replaceFirstChar { ch -> if (ch.isLowerCase()) ch.titlecase() else ch.toString() }
            }
        }
    }

    private fun getChartFormatRules(chapterName: String): String {
        return when (chapterName.lowercase()) {
            "results", "observations", "discussion", "summary", "recommendations", "future scope" -> """
            When you include charts, use one of these thesis templates only:
            - `category_bar` for category counts and proportions
            - `ranked_bar` for ordered comparisons
            - `horizontal_bar` for long category names
            - `trend_line` for time trends
            - `multi_line` for 2-series or 3-series comparisons over time
            - `pie_share` for proportions
            - `scatter_correlation` for correlation or association
            - `histogram_distribution` for continuous distribution summaries

            Each chart must stay in a renderable form:
            1. `labels` + `values`
            2. `data` as an array of `{label, value}` objects
            3. For comparison charts, a small row-based object array is allowed if every row has one category key and up to 3 numeric series keys.

            Do not emit radar, donut, heatmap, funnel, waterfall, box plot, or other unsupported custom chart payloads.
            If the data does not fit a chart cleanly, use a table instead of forcing a chart.
        """.trimIndent()
            else -> """
            If you include any chart, keep it in a supported template:
            - `category_bar`
            - `horizontal_bar`
            - `trend_line`
            - `pie_share`
            - `scatter_correlation`
            - `histogram_distribution`
            Use only `labels` + `values` or `data` as an array of `{label, value}` objects unless a comparison chart is required.
        """.trimIndent()
        }
    }

    private suspend fun sanitizeChartsForUse(charts: List<ChartJson>, chapterName: String): List<ChartJson> {
        val usableCharts = mutableListOf<ChartJson>()

        for (chart in charts) {
            val normalized = normalizeResultChart(chart)
            if (isRenderableChart(normalized)) {
                usableCharts += normalized
                continue
            }

            val repaired = repairChartWithAi(normalized, chapterName)
            val repairedNormalized = repaired?.let(::normalizeResultChart)
            if (isRenderableChart(repairedNormalized)) {
                usableCharts += repairedNormalized!!
                continue
            }

            val fallback = repairedNormalized ?: normalized
            if (fallback.datasets.isNotEmpty()) {
                usableCharts += fallback
            }
        }

        return usableCharts
    }

    private suspend fun repairChartWithAi(chart: ChartJson, chapterName: String): ChartJson? {
        val titleTopicContext = buildTitleTopicContext()
        val prompt = """
            Return ONLY valid JSON. No markdown.
            Rewrite this thesis chart into a supported format the app can render.

            Rules:
            - Use only these chart types: bar, line, pie
            - Template names allowed: category_bar, ranked_bar, horizontal_bar, trend_line, multi_line, pie_share, scatter_correlation, histogram_distribution
            - Prefer a single series
            - If the chart compares multiple groups over time, use line only if the data is clear
            - For category counts, use bar or pie
            - Do not use scatter, radar, donut, stacked, heatmap, area, or custom chart types
            - Keep labels readable and preserve the original meaning
            - Output only this object shape:
              {
                "chart_id": "...",
                "title": "...",
                "type": "bar|line|pie",
                "chart_template": "category_bar",
                "labels": ["..."],
                "values": [1, 2],
                "data": [{"label":"...","value":1}],
                "datasets": []
              }

            Chapter: $chapterName
            Thesis title/topic context:
            $titleTopicContext

            Source chart:
            ${gson.toJson(chart)}
        """.trimIndent()

        return runCatching {
            val repairedJson = callAiJsonWithContinuation(prompt, "chart_repair")
            gson.fromJson(extractJsonBlock(repairedJson), ChartJson::class.java)
        }.onFailure { e ->
            Log.e("ChartRepair", "AI repair failed for chart ${chart.title}", e)
        }.getOrNull()
    }

    private fun isRenderableChart(chart: ChartJson?): Boolean {
        if (chart == null) return false
        val type = chart.type.lowercase()
        return type in setOf("bar", "line", "pie", "scatter", "horizontal_bar", "histogram") &&
            normalizeResultChart(chart).datasets.any { it.values.isNotEmpty() }
    }

    private fun getSpecialInstructions(chapterName: String): String {
        return when (chapterName.lowercase()) {
            // ========== FRONT MATTER (no figures, but may have abbreviations) ==========
            "title" -> """
            Create a formal title page. Include title, subtitle (if any), author, guide, co‑guide, institution, department, degree, and year.
            No figures needed, but if any abbreviations appear (e.g., MD, PhD), list them in the abbreviations array.
        """.trimIndent()
            "certificate" -> """
            Write a university‑style certificate page with signature lines for the guide and head of department.
            No figures. Include abbreviations only if used.
        """.trimIndent()
            "declaration" -> """
            Write a formal declaration page stating the work is original.
            No figures. Include abbreviations if any.
        """.trimIndent()
            "acknowledgements" -> """
            Write a sincere acknowledgement section.
            No figures. Abbreviations rarely needed.
        """.trimIndent()
            "abstract" -> """
            Write a structured abstract with sections: Background, Aim, Methods, Results, Conclusion, and 5‑10 keywords.
            No figures, but include any abbreviations used.
        """.trimIndent()
            "keywords" -> """
            List 5‑10 MeSH‑style keywords. No figures.
        """.trimIndent()

            // ========== INTRODUCTION & BACKGROUND (figures encouraged) ==========
            "introduction" -> """
            Write a large, thesis-style introduction to the disease.
            Cover the topic from broad epidemiology to specific clinical relevance:
            1. Define the disease clearly.
            2. Explain etiology, pathophysiology, risk factors, and natural history.
            3. Describe global, national, and local burden where applicable.
            4. Explain the clinical presentation, complications, prognosis, and public health importance.
            5. End with the exact rationale for this study and the knowledge gap it addresses.

            Make this chapter detailed and substantial, not brief.
            Use formal medical language and include section headings if helpful.
            **Include at least one figure** such as disease mechanism, anatomy, or conceptual diagram.
            Add all abbreviations used and include references for factual claims.
        """.trimIndent()
            "background" -> """
            Write a detailed background section that expands the disease context before the study.
            Focus on epidemiology, burden of disease, disease mechanism, and why the condition matters in clinical practice.
            Include current trends, common populations affected, and a short review of the most relevant literature.
            **Include one relevant figure** such as an incidence trend, disease pathway, or anatomical diagram.
            List abbreviations and references.
        """.trimIndent()
            "disease burden" -> """
            Write a focused disease burden chapter. Cover magnitude of disease, clinical burden, public health burden, disability or mortality, service burden, economic burden where supported, and local relevance to the thesis setting.
            Use verified PubMed abstracts and similar-article references when available. Do not invent statistics; if a statistic is not present in the source evidence, describe the burden qualitatively.
            End by linking the burden to why the present study is needed.
        """.trimIndent()
            "epidemiology" -> """
            Write a focused epidemiology chapter. Cover prevalence, incidence, age and sex distribution, risk groups, geography, trends, and population factors relevant to the thesis topic.
            Use only PubMed-backed claims and cite every factual sentence.
        """.trimIndent()
            "pathophysiology" -> """
            Write a focused pathophysiology chapter. Explain mechanisms from initiating factors to tissue or system changes, clinical manifestations, complications, and investigation findings.
            Use PubMed-backed citations and keep unsupported mechanisms out.
        """.trimIndent()
            "current treatment" -> """
            Write a focused current treatment chapter. Cover current standard treatment, supportive care, procedural or surgical options if relevant, monitoring, limitations of current treatment, and areas of uncertainty.
            Cite every treatment claim with verified PubMed references and avoid guideline-like certainty unless the evidence supports it.
        """.trimIndent()
            "literature review" -> """
            Summarize key studies chronologically or thematically. Use Vancouver‑style in‑text citations.
            **Include a figure** (e.g., summary table of studies or PRISMA flow diagram).
            Abbreviations and references mandatory.
            Write a detailed disease-focused review, not a short summary.
            Required sections:
            1. Disease Definition: accepted clinical/diagnostic definition with PubMed-backed citations.
            2. Epidemiology: prevalence/incidence, burden, demographics, geography, and trends; include an epidemiology figure with 3-5 cited explanation points.
            3. Risk Factors: modifiable and non-modifiable risk factors, risk groups, and associations; include a risk-factor figure with 3-5 cited explanation points.
            4. Pathophysiology: explain the disease mechanism from early events to clinical manifestations; include a pathology/pathophysiology figure with 3-5 cited explanation points.
            5. Types and Classification: describe types, subtypes, stages, grades, phenotypes, or severity classes where present. If none are established, state that with a citation.
            6. Investigations in Literature: review clinical, laboratory, imaging, device-based, special, scoring, histopathology, microbiology, genetic, or functional investigations; include an investigations figure with 3-5 cited explanation points.
            7. Relation of Investigations with Disease: explain how investigations relate to disease definition, pathophysiology, diagnosis, staging, severity, prognosis, treatment decisions, treatment response, and follow-up.
            8. Key Study Summary and Research Gap: summarize major PubMed-indexed studies and identify the evidence gap for the thesis.
            Every factual sentence, bullet, figure explanation point, and table row must have an inline Vancouver citation like [1].
            Each cited source must be present in `chapter_references` or the section's `references` array with the same local citation number, complete Vancouver `reference_text`, a real `pmid`, DOI if available, and `pubmed_verified=true`.
            Use only PubMed sources directly related to the thesis title/topic and the section claim being supported; do not use random PMID references.
            References without PMID are invalid and must not be used.
        """.trimIndent()
            "research gap" -> """
            Identify the gap in literature and justify the need for this study.
            **Optional figure** (e.g., concept map of missing evidence).
            Abbreviations if any.
        """.trimIndent()
            "need for study" -> """
            Write a focused need-for-study chapter. Connect disease burden, epidemiology, pathophysiology, current treatment limitations, local context, and the exact thesis aim.
            The final paragraphs should clearly justify why this study is necessary and what specific evidence gap it addresses.
        """.trimIndent()
            "aim of study" -> """
            Write a single clear aim statement. No figures.
        """.trimIndent()
            "objectives" -> """
            List primary and secondary objectives (numbered). No figures.
        """.trimIndent()
            "hypothesis" -> """
            Write null and alternate hypotheses. No figures.
        """.trimIndent()

            // ========== METHODOLOGY (figures for study design, flowcharts) ==========
            "materials and methods" -> """
            Write a full methodology section: study design, setting, duration, population, sample size, criteria, data collection, statistical analysis, ethics.
            **Include a study design flowchart or diagram** as a figure.
            Add all abbreviations (e.g., RCT, SD). Provide references for standard methods.
        """.trimIndent()
            "study design" -> """
            Explain the study design (e.g., cohort, case‑control, RCT). 
            **Add a figure** illustrating the design.
            Abbreviations and references as needed.
        """.trimIndent()
            "study setting" -> """
            Describe the hospital, department, and community setting. 
            **Optional figure** (e.g., map or facility photo).
        """.trimIndent()
            "study duration" -> """
            State start and end dates. No figures.
        """.trimIndent()
            "study population" -> """
            Describe the target population and eligibility. No figures.
        """.trimIndent()
            "inclusion criteria" -> """
            List inclusion criteria as bullet points. No figures.
        """.trimIndent()
            "exclusion criteria" -> """
            List exclusion criteria as bullet points. No figures.
        """.trimIndent()
            "sample size" -> """
            Explain sample size calculation with formula and justification. 
            **Optional figure** (e.g., sample size nomogram).
        """.trimIndent()
            "sampling technique" -> """
            Describe sampling method (random, convenience, etc.). No figures.
        """.trimIndent()
            "data collection" -> """
            Detail data collection procedure, forms, and timelines. 
            **Optional figure** (e.g., data collection form screenshot).
        """.trimIndent()
            "variables collected" -> """
            List and explain all variables (independent, dependent, confounders). 
            **Optional table** (represented as a JSON table inside the section).
        """.trimIndent()
            "investigations" -> """
            Write a detailed investigations chapter for the disease.
            Explain the diagnostic workup in depth:
            1. Clinical examination findings relevant to the disease.
            2. Laboratory tests and what each test contributes.
            3. Imaging studies and their indications.
            4. Special tests, scoring systems, or procedures used for confirmation.
            5. Expected normal values, abnormal values, and interpretation where relevant.
            6. How investigations help in diagnosis, staging, severity assessment, and follow-up.

            Make this section long and clinically useful, not a short list.
            **Include a figure** if possible, such as a diagnostic workflow, machine image, or investigation algorithm.
            Add abbreviations and references where useful.
            Start with a brief overview paragraph explaining why investigations are needed, what clinical question they answer, and how they relate to the disease process.
            Also cover device-based tests, scoring systems, procedures, histopathology, microbiology, genetics, functional testing, or monitoring tools whenever relevant to the disease.
            Include a table titled `Investigation - Purpose - Expected finding - Interpretation - PMID-backed reference`.
            Include at least one figure such as a diagnostic workflow, disease-specific investigation algorithm, device/machine image, or test interpretation diagram.
            Add 3-5 cited explanation points beside the figure explaining what it shows and why it matters clinically.
            Explain how investigations relate to disease definition, risk factors, pathophysiology, complications, diagnosis, staging, severity, prognosis, treatment selection, treatment response, and follow-up.
            Every factual sentence, bullet, numbered point, table row, and figure explanation point must have an inline Vancouver citation like [1].
            Each cited source must be present in `chapter_references` or the section's `references` array with the same local citation number, complete Vancouver `reference_text`, a real `pmid`, DOI if available, and `pubmed_verified=true`.
            Use only PubMed sources directly related to the thesis title/topic, the disease, and the investigation being discussed; do not use random PMID references.
            References without PMID are invalid and must not be used.
        """.trimIndent()
            "study procedure" -> """
            Write step‑by‑step study procedure. 
            **Include a procedural flowchart** as a figure.
        """.trimIndent()
            "outcome measures" -> """
            Explain primary and secondary outcomes. No figures.
        """.trimIndent()
            "statistical analysis" -> """
            Write statistical methods, software, tests, p‑value threshold. 
            **Optional figure** (e.g., power curve or analysis schema).
        """.trimIndent()
            "ethical considerations" -> """
            Describe ethics approval, consent, confidentiality. No figures.
        """.trimIndent()

            // ========== RESULTS (charts and tables mandatory if numeric) ==========
            "results" -> """
            Report findings objectively. Use clear headings for primary/secondary outcomes.
            Structure the chapter as sections with headings, subheadings, tables, figures, and short narrative under each heading.
            **If numerical data exists, generate at least one chart** using a supported thesis template.
            Include demographic, comparison, and summary tables where relevant.
            Add all abbreviations.
            Chart templates available:
            - category_bar
            - ranked_bar
            - horizontal_bar
            - trend_line
            - multi_line
            - pie_share
            - scatter_correlation
            - histogram_distribution
            Keep charts renderable in JSON and do not use unsupported chart types.
            Do NOT interpret findings here.
        """.trimIndent()
            "observations" -> """
            Write objective observations with numbered points and trends.
            Use numbered points, short subheadings, and summary tables if needed.
            **If numbers are present, add a simple chart or a chart template that the app can render**.
            Do not emit unsupported chart types.
            Abbreviations and references not needed.
        """.trimIndent()

            // ========== DISCUSSION & CONCLUSION (figures for comparison, mechanisms) ==========
            "discussion" -> """
            Compare results with existing literature. Discuss clinical implications, mechanisms, and unexpected findings.
            **Include a figure** (e.g., comparison forest plot, mechanism diagram, or proposed algorithm).
            List abbreviations and provide references for every cited study.
        """.trimIndent()
            "conclusion" -> """
            Write a concise conclusion with main findings and clinical relevance.
            No figures, but include abbreviations if used.
        """.trimIndent()
            "summary" -> """
            Write a short academic summary of the entire thesis.
            No figures.
        """.trimIndent()
            "recommendations" -> """
            Provide evidence‑based recommendations for practice and future research.
            **Optional figure** (e.g., clinical pathway diagram).
            References required for each recommendation.
        """.trimIndent()
            "limitations" -> """
            Write the study limitations. No figures.
        """.trimIndent()
            "future scope" -> """
            Write future research directions. **Optional figure** (e.g., roadmap).
        """.trimIndent()

            // ========== REFERENCES & BIBLIOGRAPHY ==========
            "references" -> """
            Generate numbered Vancouver‑style references for all citations in the thesis.
            Return the `references` array exactly as the schema shows: `number`, complete Vancouver `text`, real `pmid`, and `doi` if PubMed provides one.
            Every reference must be PubMed indexed and must include a PMID. Validate each reference against PubMed and update the citation text with verified PMID/DOI metadata.
            Include only references directly related to the thesis title/topic and actually cited in the generated chapters.
            Do not include random PubMed-indexed articles just because they have a PMID.
            Do not use `chapter_references` for this chapter; use the schema's `references` array.
            Continue numbering from the current thesis reference cursor. This chapter must be the sequential thesis-wide reference list, not a fresh local list.
        """.trimIndent()
            "bibliography" -> """
            Return the `references` array exactly as the schema shows: `number`, complete Vancouver `text`, real `pmid`, and `doi` if PubMed provides one.
            Same as References – numbered Vancouver style with mandatory PubMed PMID metadata. Include only topic-related sources that support the thesis content.
            Keep the same global sequential order as References; the only difference is the chapter heading/formatting.
        """.trimIndent()
            "appendices" -> """
            List appendices with titles and brief content. Include any supplementary figures or tables.
            Abbreviations as needed.
        """.trimIndent()

            // ========== FORMS & CONSENT ==========
            "proforma" -> """
            Create a structured clinical data collection sheet with fields: patient name, age, sex, OPD/IP number, address, history, examination, investigations, diagnosis.
            No figures, but include abbreviations (e.g., OPD, IP).
        """.trimIndent()
            "patient consent form (english)" -> """
            Write a formal informed consent form in English. Include introduction, procedure, risks, benefits, confidentiality, signature line, date.
            No figures.
        """.trimIndent()
            "patient consent form (hindi)" -> """
            Write the same consent form in Hindi. No figures.
        """.trimIndent()

            // ========== AUTO‑GENERATED CHAPTERS (used by assembleAutoGeneratedFrontMatter) ==========
            "table of contents" -> "Generate the Table of Contents from the thesis structure. No figures."
            "list of tables" -> "Generate the List of Tables from all tables in the thesis. No figures."
            "list of figures" -> "Generate the List of Figures from all figures in the thesis. No figures."
            "list of abbreviations" -> "Generate the List of Abbreviations from all abbreviations used in the thesis. No figures."

            // Fallback for any other chapter
            else -> """
            Write in a formal, academic, medical tone. Ensure high clinical accuracy and logical flow.
            Include at least one figure if the topic allows (e.g., diagram, flowchart). Provide abbreviations and references where applicable.
        """.trimIndent()
        }
    }

private fun defaultGenericSchema(): String = """
{
  "chapter_name": "...",
  "sections": [
    {
      "heading":"...",
      "content":"...",
      "paragraphs":["Paragraph 1 with inline citation [1]","Paragraph 2 with inline citation [2]"],
      "bullets":["..."],
      "numbered_points":["..."],
      "figures":[{"figure_number":"1","title":"...","caption":"...","image_search_query":"..."}],
      "references":[{"citation":"[1]","reference_text":"Author AA, Author BB. Complete disease-related article title. Journal Name. 2020;12(3):123-130. PMID: 12345678. DOI: 10.xxxx/xxxxx","pmid":"12345678","doi":"10.xxxx/xxxxx","pubmed_verified":true}]
    }
  ],
  "figures": [{"figure_number":"1","title":"...","caption":"...","image_search_query":"..."}],
  "abbreviations": [],
  "chapter_references": [{"citation":"[1]","reference_text":"Author AA, Author BB. Complete disease-related article title. Journal Name. 2020;12(3):123-130. PMID: 12345678. DOI: 10.xxxx/xxxxx","pmid":"12345678","doi":"10.xxxx/xxxxx","pubmed_verified":true}]
}
"""

    private suspend fun assembleAutoGeneratedFrontMatter() {
        val chapters = _uiState.value.chapters.toMutableList()
        val allTables = mutableListOf<TableEntry>()
        val allFigures = mutableListOf<FigureEntry>()
        val allAbbreviations = mutableListOf<AbbreviationJson>()
        val allReferences = mutableListOf<ReferenceJson>()
        val extractedVariables = _uiState.value.variables

        // 1. Collect data from all generated chapters
        chapters.forEach { chapter ->
            if (chapter.rawJson.isNotBlank()) {
                try {
                    val generic = parseThesisChapterJson(chapter.rawJson, chapter.name)
                    allTables.addAll(generic.tables.mapIndexed { idx, table ->
                        TableEntry(
                            number = table.tableNumber.toIntOrNull() ?: idx + 1,
                            title = table.title,
                            page = 0
                        )
                    })
                    generic.sections.forEach { section ->
                        section.table?.let { table ->
                            allTables.add(TableEntry(
                                number = table.tableNumber.toIntOrNull() ?: 0,
                                title = table.title,
                                page = 0
                            ))
                        }
                    }
                    allFigures.addAll(collectChapterFigures(generic).mapIndexed { idx, fig ->
                        FigureEntry(number = idx + 1, title = fig.title, page = 0)
                    })
                    allAbbreviations.addAll(generic.abbreviations)
                    allReferences.addAll(collectChapterReferences(generic))
                } catch (_: Exception) { }
            }

            // Also collect from chapter.figures, .abbreviations, .chapterReferences (for custom schemas)
            allTables.addAll(chapter.tables.mapIndexed { idx, table ->
                TableEntry(
                    number = (idx + 1).takeIf { table.tableNumber.isBlank() } ?: table.tableNumber.toIntOrNull() ?: idx + 1,
                    title = table.title,
                    page = 0
                )
            })
            allFigures.addAll(chapter.figures.mapIndexed { idx, fig ->
                FigureEntry(number = idx + 1, title = fig.title, page = 0)
            })
            allAbbreviations.addAll(chapter.abbreviations)
            allReferences.addAll(chapter.chapterReferences)
            allAbbreviations.addAll(extractAbbreviationsFromText(chapter.content))
        }

        allReferences.addAll(parseReferencesVariable(extractedVariables))
        allAbbreviations.addAll(parseAbbreviationsVariable(extractedVariables))
        allAbbreviations.addAll(extractAbbreviationsFromText(extractedVariables.joinToString("\n") { "${it.name}: ${it.value}" }))

        // 2. Deduplicate
        val uniqueTables = allTables.distinctBy { it.title }
        val uniqueFigures = allFigures.distinctBy { it.title }
        val uniqueAbbr = allAbbreviations.distinctBy { it.shortForm.uppercase() }
        val canonicalLedger = _uiState.value.verifiedPubMedReferences
            .ifEmpty { allReferences.filter { it.pmid?.isNotBlank() == true } }
            .distinctBy { ref ->
                referenceIdentity(ref) ?: canonicalReferenceTextKey(ref.referenceText)
            }

        val verifiedRefs = verifyReferencesWithPubMed(
            canonicalLedger.ifEmpty {
                allReferences.distinctBy { ref ->
                    referenceIdentity(ref) ?: canonicalReferenceTextKey(ref.referenceText)
                }
            }
        )
        val uniqueRefs = verifiedRefs
            .filter { it.hasRequiredPmid() }
            .mapIndexed { index, ref ->
                ref.copy(citation = serializedCitation(index + 1))
            }
        val globalReferenceNumbers = uniqueRefs.flatMapIndexed { index, ref ->
            referenceIdentities(ref).map { identity -> identity to (index + 1) }
        }.toMap()

        val serializedChapters = chapters.map { chapter ->
            serializeChapterCitations(chapter, globalReferenceNumbers)
        }.toMutableList()
        chapters.clear()
        chapters.addAll(serializedChapters)
        updateVariable("References_Vancouver", formatReferencesForVariable(uniqueRefs))
        _uiState.update { it.copy(referenceSequenceCounter = nextReferenceSequence(uniqueRefs)) }

        // 3. Build content strings
        val tocRows = chapters.filter { it.status == Chapter.ChapterStatus.SUCCESS }
            .mapIndexed { idx, ch ->
                listOf(
                    (idx + 1).toString(),
                    ch.name.uppercase(),
                    chapterTypeFor(ch.name).replace('_', ' ')
                )
            }

        val lotRows = uniqueTables.mapIndexed { idx, table ->
            listOf(
                (idx + 1).toString(),
                table.title,
                if (table.page > 0) table.page.toString() else "TBD"
            )
        }

        val lofRows = uniqueFigures.mapIndexed { idx, figure ->
            listOf(
                (idx + 1).toString(),
                figure.title,
                if (figure.page > 0) figure.page.toString() else "TBD"
            )
        }

        val loaRows = uniqueAbbr.mapIndexed { idx, abbr ->
            listOf(
                (idx + 1).toString(),
                abbr.shortForm,
                abbr.fullForm
            )
        }

        val referencesRows = uniqueRefs.mapIndexed { idx, ref ->
            listOf(
                (idx + 1).toString(),
                serializedCitation(idx + 1),
                ref.completeCitationText().ifBlank { "-" }
            )
        }

        val referencesContent = buildReferencesContent("REFERENCES", uniqueRefs)
        val bibliographyContent = buildReferencesContent("BIBLIOGRAPHY", uniqueRefs)

        // 4. Add or update auto chapters
        fun addOrUpdateChapter(name: String, content: String, tables: List<ThesisTableJson> = emptyList()) {
            val index = chapters.indexOfFirst { it.name.equals(name, ignoreCase = true) }
            if (index >= 0) {
                chapters[index] = chapters[index].copy(
                    content = content,
                    tables = tables,
                    status = Chapter.ChapterStatus.SUCCESS
                )
            } else {
                chapters.add(
                    Chapter(
                        name = name,
                        content = content,
                        tables = tables,
                        status = Chapter.ChapterStatus.SUCCESS
                    )
                )
            }
        }

        addOrUpdateChapter(
            "Table of Contents",
            "TABLE OF CONTENTS",
            listOf(
                ThesisTableJson(
                    tableNumber = "TOC",
                    title = "Table of Contents",
                    headers = listOf("No.", "Chapter", "Type"),
                    rows = tocRows,
                    footnote = "Generated from all successfully assembled chapters."
                )
            )
        )
        addOrUpdateChapter(
            "List of Tables",
            "LIST OF TABLES",
            listOf(
                ThesisTableJson(
                    tableNumber = "LOT",
                    title = "List of Tables",
                    headers = listOf("No.", "Table Title", "Page"),
                    rows = lotRows,
                    footnote = "Page values are marked TBD until page mapping is available."
                )
            )
        )
        addOrUpdateChapter(
            "List of Figures",
            "LIST OF FIGURES",
            listOf(
                ThesisTableJson(
                    tableNumber = "LOF",
                    title = "List of Figures",
                    headers = listOf("No.", "Figure Title", "Page"),
                    rows = lofRows,
                    footnote = "Page values are marked TBD until page mapping is available."
                )
            )
        )
        addOrUpdateChapter(
            "List of Abbreviations",
            "LIST OF ABBREVIATIONS",
            listOf(
                ThesisTableJson(
                    tableNumber = "LOA",
                    title = "List of Abbreviations",
                    headers = listOf("No.", "Abbreviation", "Full Form"),
                    rows = loaRows,
                    footnote = "Generated from all abbreviations extracted across the thesis."
                )
            )
        )
        addOrUpdateChapter(
            "List of References",
            "LIST OF REFERENCES",
            listOf(
                ThesisTableJson(
                    tableNumber = "LOR",
                    title = "List of References",
                    headers = listOf("No.", "Citation", "Reference"),
                    rows = referencesRows,
                    footnote = "Serialized global reference list used by all inline thesis citations."
                )
            )
        )
        addOrUpdateChapter(
            "References",
            referencesContent,
            listOf(
                ThesisTableJson(
                    tableNumber = "REF",
                    title = "References",
                    headers = listOf("No.", "Citation", "Reference"),
                    rows = referencesRows,
                    footnote = "Merged and deduplicated from all generated chapters."
                )
            )
        )
        addOrUpdateChapter(
            "Bibliography",
            bibliographyContent,
            listOf(
                ThesisTableJson(
                    tableNumber = "BIB",
                    title = "Bibliography",
                    headers = listOf("No.", "Citation", "Reference"),
                    rows = referencesRows,
                    footnote = "Mirrors the thesis references in bibliography format."
                )
            )
        )

        // 5. Update UI state
        _uiState.update { it.copy(chapters = chapters) }
        saveSessionToFirebase()
    }

    private fun chapterTypeFor(chapterName: String): String {
        return when (chapterName.trim().lowercase()) {
            "title", "certificate", "declaration", "acknowledgements", "proforma", "patient consent form (english)", "patient consent form (hindi)" -> "FRONT_MATTER"

            "abstract", "keywords" -> "FRONT_MATTER"
            "introduction", "background", "disease burden", "epidemiology", "pathophysiology",
            "current treatment", "literature review", "research gap", "need for study",
            "aim of study", "objectives", "hypothesis" -> "CHAPTER_1"

            "materials and methods", "study design", "study setting", "study duration",
            "study population", "inclusion criteria", "exclusion criteria", "sample size",
            "sampling technique", "data collection", "variables collected", "investigations",
            "study procedure", "outcome measures", "statistical analysis",
            "ethical considerations" -> "CHAPTER_3"

            "results", "observations" -> "CHAPTER_4"
            "discussion" -> "CHAPTER_5"
            "conclusion", "summary", "recommendations", "limitations", "future scope" -> "CHAPTER_6"
            "references", "bibliography" -> "REFERENCES"
            "appendices" -> "APPENDICES"
            else -> "OTHER"
        }
    }

    private fun parseReferencesVariable(variables: List<Variable>): List<ReferenceJson> {
        val refsText = referencesVariableText(variables)

        if (refsText.isBlank()) return emptyList()

        val entries = splitReferenceEntries(refsText)
        if (entries.isEmpty()) return emptyList()

        return entries.mapIndexed { index, entry ->
            val cleaned = stripReferenceEntryNumber(entry).trim()
            val pmid = extractPmid(cleaned)
            val doi = extractDoi(cleaned)
            ReferenceJson(
                citation = serializedCitation(index + 1),
                referenceText = stripReferenceMetadata(cleaned).ifBlank { stripReferenceMetadata(entry) },
                pmid = pmid.ifBlank { null },
                doi = doi,
                pubmedVerified = pmid.isNotBlank()
            )
        }
    }

    private fun referencesVariableText(variables: List<Variable>): String {
        return variables.firstOrNull {
            normalizeVariableKey(it.name) == normalizeVariableKey("References_Vancouver")
        }?.value.orEmpty()
    }

    private suspend fun parseReferencesVariableForProcessing(): List<ReferenceJson> {
        val refsText = referencesVariableText(_uiState.value.variables)
        if (refsText.isBlank()) return emptyList()

        val baseline = parseReferencesVariable(_uiState.value.variables)
        val repaired = repairReferenceBlockWithAi(refsText, baseline)
        return repaired.ifEmpty { baseline }
            .filterNot { isMetadataOnlyReference(it) }
            .distinctBy { ref ->
                referenceIdentity(ref) ?: canonicalReferenceTextKey(ref.referenceText)
            }
            .mapIndexed { index, ref -> ref.copy(citation = serializedCitation(index + 1)) }
    }

    private suspend fun repairReferenceBlockWithAi(
        refsText: String,
        baseline: List<ReferenceJson>
    ): List<ReferenceJson> {
        if (refsText.isBlank()) return emptyList()
        val shouldRepair = baseline.isEmpty() ||
            baseline.any(::isMetadataOnlyReference) ||
            refsText.lines().any { line ->
                Regex("""^\s*(?:PMID|DOI)\s*:?\s*""", RegexOption.IGNORE_CASE).containsMatchIn(line)
            }

        if (!shouldRepair) return baseline

        return runCatching {
            _uiState.update { it.copy(status = "Repairing reference separation with AI...") }
            val prompt = """
                You are repairing an extracted Vancouver reference list.
                Separate the raw text into complete references only.
                Rules:
                - Do not create a new reference from a wrapped continuation line.
                - Lines containing only PMID, DOI, URL, page numbers, journal continuation, or volume/issue data belong to the previous reference.
                - Preserve PMID/DOI only when they are explicitly present in the raw text.
                - Do not invent authors, titles, journals, PMID, DOI, or years.
                - Return ONLY JSON using this exact schema:
                {"references":[{"number":1,"text":"complete Vancouver reference without PMID/DOI metadata","pmid":"12345678 or null","doi":"10.xxxx/yyyy or null"}]}

                RAW REFERENCES:
                ${refsText.take(12000)}
            """.trimIndent()

            val raw = callAiApi(prompt, requireStrongResponse = false, phase = "reference_or_asset_generation")
            parseRepairedReferencesJson(raw)
        }.getOrElse { error ->
            Log.w("ThesisViewModel", "AI reference repair failed; using baseline parser: ${error.message ?: error.toString()}")
            baseline
        }
    }

    private fun parseRepairedReferencesJson(raw: String): List<ReferenceJson> {
        val cleaned = extractJsonBlock(raw)
        val refs = gson.fromJson(cleaned, ReferencesJson::class.java).references
        return refs.mapIndexedNotNull { index, entry ->
            val text = stripReferenceMetadata(entry.text).trim()
            val pmid = entry.pmid?.trim()?.takeIf { it.isNotBlank() && it != "null" }
                ?: extractPmid(entry.text).takeIf { it.isNotBlank() }
            val doi = entry.doi?.trim()?.takeIf { it.isNotBlank() && it != "null" }
                ?: extractDoi(entry.text)
            val reference = ReferenceJson(
                citation = serializedCitation(entry.number.takeIf { it > 0 } ?: index + 1),
                referenceText = text,
                pmid = pmid,
                doi = doi,
                pubmedVerified = false
            )
            reference.takeUnless(::isMetadataOnlyReference)
        }
    }

    private fun splitReferenceEntries(refsText: String): List<String> {
        val normalizedLines = refsText
            .replace("\r\n", "\n")
            .replace('\r', '\n')
            .lines()
            .map { it.trim() }
            .filter { line ->
                line.isNotBlank() &&
                    !line.equals("references", ignoreCase = true) &&
                    !line.equals("bibliography", ignoreCase = true) &&
                    !line.equals("list of references", ignoreCase = true)
            }

        if (normalizedLines.isEmpty()) return emptyList()

        val singleLineText = normalizedLines.joinToString(" ")
        if (countReferenceEntryMarkers(singleLineText) > 1) {
            val inlineEntries = splitInlineNumberedReferences(singleLineText)
                .map { it.replace(Regex("\\s+"), " ").trim() }
                .filter { looksLikeReferenceEntry(it) }
            if (inlineEntries.size > 1) return inlineEntries
        }

        val entries = mutableListOf<String>()
        val current = StringBuilder()

        fun flush() {
            val entry = current.toString()
                .replace(Regex("\\s+"), " ")
                .trim()
                .trimEnd(';')
            if (entry.isNotBlank() && looksLikeReferenceEntry(entry)) {
                entries += entry
            }
            current.clear()
        }

        normalizedLines.forEach { rawLine ->
            val line = rawLine.trim().trimEnd()
            val startsNew = isReferenceEntryStart(line)
            if (startsNew && current.isNotBlank()) {
                flush()
            }
            if (current.isNotBlank()) current.append(' ')
            current.append(line)
        }
        flush()

        if (entries.isNotEmpty()) return entries

        return splitInlineNumberedReferences(refsText)
            .map { it.replace(Regex("\\s+"), " ").trim() }
            .filter { looksLikeReferenceEntry(it) }
    }

    private fun isReferenceEntryStart(line: String): Boolean {
        val trimmed = line.trimStart()
        return referenceEntryStartRegex.containsMatchIn(trimmed)
    }

    private val referenceEntryStartRegex = Regex("""^(?:\[\d{1,4}]|\d{1,4}[.)])\s+\S+""")
    private val inlineReferenceEntryMarkerRegex = Regex("""(?:^|\s)(?:\[\d{1,4}]|\d{1,4}[.)])\s+\S+""")

    private fun countReferenceEntryMarkers(text: String): Int {
        return inlineReferenceEntryMarkerRegex.findAll(text).count()
    }

    private fun stripReferenceEntryNumber(entry: String): String {
        return entry
            .replace(Regex("""^\s*(?:\[\d{1,4}]|\d{1,4}[.)])\s*"""), "")
            .trim()
    }

    private fun looksLikeReferenceEntry(entry: String): Boolean {
        val cleaned = stripReferenceEntryNumber(entry)
        val citationOnly = stripReferenceMetadata(cleaned)
        if (citationOnly.length < 20) return false
        if (isReferenceMetadataOnlyText(cleaned)) return false
        if (extractPmid(cleaned).isNotBlank() || extractDoi(cleaned) != null) return true
        val wordCount = citationOnly.split(Regex("\\s+")).count { token -> token.any(Char::isLetter) }
        val hasYear = Regex("""\b(?:19|20)\d{2}\b""").containsMatchIn(citationOnly)
        val hasSentencePunctuation = citationOnly.count { it == '.' } >= 2 || citationOnly.contains(";")
        return wordCount >= 6 && (hasYear || hasSentencePunctuation)
    }

    private fun isMetadataOnlyReference(reference: ReferenceJson): Boolean {
        return isReferenceMetadataOnlyText(reference.referenceText.completeCitationText(reference.pmid, reference.doi))
    }

    private fun isReferenceMetadataOnlyText(text: String): Boolean {
        val withoutMetadata = stripReferenceMetadata(text)
            .replace(Regex("""https?://\S+""", RegexOption.IGNORE_CASE), "")
            .replace(Regex("""^\s*(?:\[\d{1,4}]|\d{1,4}[.)])\s*"""), "")
            .replace(Regex("""[.;,\s]+"""), " ")
            .trim()
        val wordCount = withoutMetadata.split(Regex("\\s+")).count { it.any(Char::isLetter) }
        return withoutMetadata.length < 20 || wordCount < 4
    }

    private fun splitInlineNumberedReferences(refsText: String): List<String> {
        val text = refsText.replace(Regex("\\s+"), " ").trim()
        if (text.isBlank()) return emptyList()
        val marker = Regex("""(?=(?:^|\s)(?:\[\d{1,4}]|\d{1,4}[.)])\s+\S)""")
        return marker.split(text)
            .map { it.trim() }
            .filter { it.isNotBlank() }
    }

    private fun parseAbbreviationsVariable(variables: List<Variable>): List<AbbreviationJson> {
        val abbreviations = variables.filter {
            val normalized = normalizeVariableKey(it.name)
            normalized.contains("abbrevi") || normalized == normalizeVariableKey("Abbreviations")
        }.flatMap { variable ->
            variable.value.split(Regex("\\r?\\n+"))
                .map { it.trim() }
                .filter { it.isNotBlank() }
        }

        return abbreviations.mapNotNull { line ->
            val parts = line.split(":", "=", "-", "–", "—")
                .map { it.trim() }
                .filter { it.isNotBlank() }
            if (parts.size >= 2) {
                AbbreviationJson(shortForm = parts.first(), fullForm = parts.drop(1).joinToString(" "))
            } else null
        }
    }

    private suspend fun verifyReferencesWithPubMed(references: List<ReferenceJson>): List<ReferenceJson> {
        return withContext(Dispatchers.IO) {
            if (references.isEmpty()) return@withContext emptyList()

            seedVerifiedReferenceCache(_uiState.value.verifiedPubMedReferences + references)
            val verifiedReferences = mutableListOf<ReferenceJson>()
            _uiState.update {
                it.copy(
                    status = "Starting PubMed reference verification 0/${references.size}",
                    progressCurrent = 0,
                    progressTotal = references.size
                )
            }
            for ((index, reference) in references.withIndex()) {
                val strippedCitation = stripReferenceMetadata(reference.referenceText)
                val cachedReference = findCachedVerifiedReference(reference, strippedCitation)
                if (cachedReference != null) {
                    verifiedReferences += cachedReference.copy(citation = reference.citation.ifBlank { cachedReference.citation })
                    _uiState.update {
                        it.copy(
                            status = "Using cached PubMed reference ${index + 1}/${references.size}",
                            progressCurrent = index + 1,
                            progressTotal = references.size
                        )
                    }
                    continue
                }

                _uiState.update {
                    it.copy(
                        status = "Verifying PubMed reference ${index + 1}/${references.size}",
                        progressCurrent = index,
                        progressTotal = references.size
                    )
                }
                val pubmed = resolvePubMedForReference(reference, strippedCitation)
                val verified = if (pubmed == null) {
                    reference.copy(
                        referenceText = strippedCitation,
                        pubmedVerified = false
                    )
                } else {
                    reference.copy(
                        referenceText = pubmed.canonicalReference.ifBlank { strippedCitation },
                        pmid = pubmed.pmid,
                        doi = pubmed.doi,
                        pubmedVerified = true
                    )
                }
                if (verified.hasRequiredPmid()) {
                    cacheVerifiedReference(verified)
                    cacheVerifiedReferenceAliases(reference, strippedCitation, verified)
                }
                verifiedReferences += verified
                _uiState.update {
                    it.copy(
                        status = "PubMed reference checked ${index + 1}/${references.size}",
                        progressCurrent = index + 1,
                        progressTotal = references.size
                    )
                }
            }
            persistVerifiedReferenceCache()
            refreshVerifiedPubMedEvidence(verifiedReferences.filter { it.hasRequiredPmid() })
            _uiState.update {
                it.copy(
                    status = "PubMed references verified ${verifiedReferences.count { ref -> ref.hasRequiredPmid() }}/${references.size}",
                    progressCurrent = references.size,
                    progressTotal = references.size
                )
            }
            saveSessionToFirebase()
            verifiedReferences
        }
    }

    private suspend fun refreshVerifiedPubMedEvidence(references: List<ReferenceJson>) {
        withContext(Dispatchers.IO) {
            val now = System.currentTimeMillis()
            val pmids = references
                .mapNotNull { it.pmid?.trim()?.takeIf { pmid -> pmid.isNotBlank() } }
                .distinct()
            if (pmids.isEmpty()) return@withContext
            val freshCached = pmids.mapNotNull { pmid ->
                val cached = pubMedAbstractSourceCache[pmid] ?: return@mapNotNull null
                val fetchedAt = pubMedAbstractFetchedAt[pmid] ?: 0L
                cached.takeIf { now - fetchedAt <= pubMedAbstractStaleAfterMs }
            }
            val freshPmids = freshCached.map { it.pmid.trim() }.toSet()
            val pmidsToFetch = pmids.filter { it !in freshPmids }

            _uiState.update {
                it.copy(
                    status = "Downloading PubMed abstracts 0/${pmidsToFetch.size}",
                    progressCurrent = 0,
                    progressTotal = pmidsToFetch.size
                )
            }

            val fetched = fetchPubMedAbstractSources(pmidsToFetch)
            fetched.forEach { source ->
                val pmid = source.pmid.trim()
                if (pmid.isNotBlank()) {
                    pubMedAbstractSourceCache[pmid] = source
                    pubMedAbstractFetchedAt[pmid] = now
                }
            }
            if (fetched.isEmpty() && freshCached.isEmpty()) return@withContext

            val merged = (_uiState.value.verifiedPubMedAbstractSources + freshCached + fetched)
                .filter { it.pmid.isNotBlank() }
                .distinctBy { it.pmid.trim() }
                .sortedBy { it.pmid.trim() }

            _uiState.update {
                it.copy(
                    verifiedPubMedAbstractSources = merged,
                    status = "PubMed abstracts ready ${merged.size}/${pmids.size}",
                    progressCurrent = pmidsToFetch.size,
                    progressTotal = pmidsToFetch.size
                )
            }
        }
    }

    private fun seedVerifiedReferenceCache(references: List<ReferenceJson>) {
        references.filter { it.hasRequiredPmid() }.forEach(::cacheVerifiedReference)
    }

    private fun cacheVerifiedReference(reference: ReferenceJson) {
        val canonical = reference.copy(
            referenceText = reference.completeCitationText(),
            pmid = reference.pmid?.trim(),
            doi = reference.doi?.trim(),
            pubmedVerified = true
        )
        verifiedReferenceKeys(canonical).forEach { key ->
            verifiedReferenceCache[key] = canonical
        }
    }

    private fun cacheVerifiedReferenceAliases(
        original: ReferenceJson,
        strippedCitation: String,
        verified: ReferenceJson
    ) {
        val canonical = verified.copy(
            referenceText = verified.completeCitationText(),
            pmid = verified.pmid?.trim(),
            doi = verified.doi?.trim(),
            pubmedVerified = true
        )
        val aliasReferences = listOf(
            original,
            original.copy(referenceText = strippedCitation),
            verified
        )
        aliasReferences.flatMap(::verifiedReferenceKeys).forEach { key ->
            verifiedReferenceCache[key] = canonical
        }
    }

    private fun findCachedVerifiedReference(reference: ReferenceJson, strippedCitation: String): ReferenceJson? {
        if (reference.hasRequiredPmid()) {
            return reference.copy(
                referenceText = reference.completeCitationText(),
                pmid = reference.pmid?.trim(),
                doi = reference.doi?.trim(),
                pubmedVerified = true
            )
        }

        val lookup = reference.copy(referenceText = strippedCitation)
        return verifiedReferenceKeys(lookup)
            .firstNotNullOfOrNull { key -> verifiedReferenceCache[key] }
    }

    private fun verifiedReferenceKeys(reference: ReferenceJson): List<String> {
        val keys = mutableListOf<String>()
        reference.pmid?.trim()?.takeIf { it.isNotBlank() }?.let { keys += "pmid:$it" }
        reference.doi?.trim()?.takeIf { it.isNotBlank() }?.let { keys += "doi:${it.lowercase()}" }
        normalizeReferenceText(reference.referenceText)
            .takeIf { it.isNotBlank() }
            ?.let { keys += "text:$it" }
        canonicalReferenceTextKey(reference.referenceText)
            .takeIf { it.isNotBlank() }
            ?.let { keys += "canonical-text:$it" }
        return keys
    }

    private fun persistVerifiedReferenceCache() {
        val cached = verifiedReferenceCache.values
            .filter { it.hasRequiredPmid() }
            .distinctBy { it.pmid?.trim().orEmpty() }
            .sortedBy { it.pmid?.trim().orEmpty() }
        _uiState.update {
            it.copy(
                verifiedPubMedReferences = cached,
                referenceSequenceCounter = nextReferenceSequence(cached)
            )
        }
    }

    private suspend fun resolvePubMedForReference(reference: ReferenceJson, strippedCitation: String): PubMedMatch? {
        searchPubMedReference(strippedCitation)?.let { return it }

        reference.doi
            ?.trim()
            ?.takeIf { it.isNotBlank() }
            ?.let { doi ->
                searchPubMedReference(doi)?.let { return it }
            }

        val suppliedPmid = reference.pmid
            ?.trim()
            ?.takeIf { it.isNotBlank() }
            ?: extractPmid(reference.referenceText).takeIf { it.isNotBlank() }

        val suppliedPmidMatch = suppliedPmid
            ?.let { batchFetchPubMedMatches(listOf(it))[it] ?: pubMedPmidCache[it] }

        if (suppliedPmidMatch != null && isCitationCompatibleWithPubMed(strippedCitation, suppliedPmidMatch)) {
            return suppliedPmidMatch
        }

        return null
    }

    private fun isCitationCompatibleWithPubMed(strippedCitation: String, pubmed: PubMedMatch): Boolean {
        if (strippedCitation.isBlank()) return true
        val hints = buildReferenceSearchHints(strippedCitation)
        val score = scorePubMedMatch(pubmed, hints)
        return isAcceptablePubMedSearchMatch(pubmed, hints) || score >= minimumPubMedSearchScore
    }

    private suspend fun requirePubMedVerifiedReferences(
        references: List<ReferenceJson>,
        chapterName: String
    ): List<ReferenceJson> {
        if (references.isEmpty()) return emptyList()

        val pmidVerified = verifyReferencesWithPubMed(references)
            .filter { it.hasRequiredPmid() }
            .mapIndexed { index, ref -> ref.copy(citation = ref.citation.ifBlank { (index + 1).toString() }) }

        if (pmidVerified.isEmpty()) {
            throw IllegalStateException("Every reference in $chapterName must validate against PubMed and include a PMID")
        }
        if (requiresPubMedCitations(chapterName)) {
            val approvedIdentities = selectEvidenceForChapter(chapterName)
                .map { it.reference }
                .flatMap(::referenceIdentities)
                .toSet()
            if (approvedIdentities.isNotEmpty()) {
                val outsideCorpus = pmidVerified.filter { reference ->
                    referenceIdentities(reference).none { identity -> identity in approvedIdentities }
                }
                if (outsideCorpus.isNotEmpty()) {
                    throw IllegalStateException("Rejected references in $chapterName because they are outside the approved extracted-reference/similar-article corpus")
                }
            }
        }
        if (requiresPubMedCitations(chapterName) && pmidVerified.size != references.size) {
            throw IllegalStateException("Rejected PubMed references in $chapterName because one or more references could not resolve to a PMID")
        }

        return pmidVerified
    }

    private fun isReferenceRelatedToDiseaseTopic(reference: ReferenceJson, chapterName: String): Boolean {
        if (!requiresPubMedCitations(chapterName)) return true

        val diseaseTopic = currentDiseaseTopic()
        if (diseaseTopic.isBlank()) return true

        val referenceText = normalizeReferenceText(reference.referenceText)
        if (referenceText.isBlank()) return false

        val diseaseNormalized = normalizeReferenceText(diseaseTopic)
        if (diseaseNormalized.isNotBlank() && referenceText.contains(diseaseNormalized)) return true

        val diseaseTokens = topicTokens(diseaseTopic)
        if (diseaseTokens.isEmpty()) return true

        val referenceTokens = topicTokens(reference.referenceText)
        val matchedDiseaseTokens = diseaseTokens.count { it in referenceTokens }
        if (matchedDiseaseTokens >= 2) return true
        if (diseaseTokens.size == 1 && matchedDiseaseTokens == 1) return true

        val titleTokens = topicTokens(_uiState.value.thesisTitle)
        return titleTokens.isNotEmpty() && titleTokens.count { it in referenceTokens } >= 3
    }

    private fun currentDiseaseTopic(): String {
        val variables = ensureDiseaseTopicVariable(_uiState.value.variables)
        return diseaseTopicFromVariables(variables)
    }

    private fun diseaseTopicFromVariables(variables: List<Variable>): String {
        val ensuredVariables = ensureDiseaseTopicVariable(variables)
        return variables.firstOrNull {
            normalizeVariableKey(it.name) in setOf(
                normalizeVariableKey("Disease_or_Condition"),
                normalizeVariableKey("Title_Disease_Topic"),
                normalizeVariableKey("Disease Topic")
            )
        }?.value?.trim().orEmpty()
            .ifBlank {
                ensuredVariables.firstOrNull {
                    normalizeVariableKey(it.name) in setOf(
                        normalizeVariableKey("Disease_or_Condition"),
                        normalizeVariableKey("Title_Disease_Topic"),
                        normalizeVariableKey("Disease Topic")
                    )
                }?.value?.trim().orEmpty()
            }
    }

    private fun topicTokens(text: String): Set<String> {
        val stopWords = setOf(
            "study", "patients", "patient", "subjects", "subject", "cases", "case",
            "clinical", "evaluation", "assessment", "correlation", "association",
            "comparison", "prevalence", "incidence", "profile", "role", "effect",
            "among", "with", "without", "using", "based", "hospital", "adult",
            "pediatric", "paediatric", "male", "female", "group"
        )
        return normalizeReferenceText(text)
            .split(Regex("""\s+"""))
            .map { it.trim('.', ',', ';', ':', '(', ')', '[', ']') }
            .filter { it.length >= 4 && it !in stopWords && !it.all(Char::isDigit) }
            .toSet()
    }

    private fun ReferenceJson.hasRequiredPmid(): Boolean {
        return pubmedVerified && !pmid.isNullOrBlank()
    }

    private fun extractPmid(text: String): String {
        return Regex("""\bPMID\s*:?\s*(\d{4,12})\b""", RegexOption.IGNORE_CASE)
            .find(text)
            ?.groupValues
            ?.getOrNull(1)
            ?: extractBarePmid(text)
            .orEmpty()
    }

    private fun extractBarePmid(text: String): String {
        val trimmed = text.trim()
        return if (trimmed.matches(Regex("""\d{4,12}"""))) trimmed else ""
    }

    private fun extractDoi(text: String): String? {
        return Regex("""10\.\d{4,9}/[^\s<>"']+""", RegexOption.IGNORE_CASE)
            .find(text)
            ?.value
            ?.trimEnd('.', ',', ';')
    }

    private fun String.withoutReferenceMetadata(): String {
        return replace(Regex("""\bPMID\s*:?\s*\d{4,12}\b\.?""", RegexOption.IGNORE_CASE), "")
            .replace(Regex("""\bDOI\s*:?\s*10\.\d{4,9}/[^\s<>"']+\.?""", RegexOption.IGNORE_CASE), "")
            .replace(Regex("\\s+"), " ")
            .trim()
            .trimEnd('.', ';', ',')
            .trim()
    }

    private fun String.withRequiredPmid(pmid: String): String {
        val base = withoutReferenceMetadata()
        return if (pmid.isBlank()) {
            base
        } else {
            "$base. PMID: $pmid"
        }
    }

    private fun String.completeCitationText(pmid: String? = null, doi: String? = null): String {
        val trimmed = withoutReferenceMetadata()
        if (trimmed.isBlank()) {
            val pmidPart = pmid?.takeIf { it.isNotBlank() }?.let { "PMID: $it" }.orEmpty()
            val doiPart = doi?.takeIf { it.isNotBlank() }?.let { "DOI: $it" }.orEmpty()
            return listOf(pmidPart, doiPart).filter { it.isNotBlank() }.joinToString(". ")
        }

        val hasPmid = Regex("""\bPMID\s*:?\s*\d{4,12}\b""", RegexOption.IGNORE_CASE).containsMatchIn(trimmed)
        val hasDoi = Regex("""\bDOI\s*:?\s*10\.\d{4,9}/[^\s<>"']+""", RegexOption.IGNORE_CASE).containsMatchIn(trimmed)
        val builder = StringBuilder(trimmed)
        if (!hasPmid && !pmid.isNullOrBlank()) {
            builder.append(". PMID: ").append(pmid.trim())
        }
        if (!hasDoi && !doi.isNullOrBlank()) {
            builder.append(". DOI: ").append(doi.trim())
        }
        return builder.toString().trim()
    }

    private fun ReferenceJson.completeCitationText(): String {
        if (authors.isNotEmpty() && title.isNotBlank() && journal.isNotBlank()) {
            val authorsStr = authors.take(6).joinToString(", ") + (if (authors.size > 6) ", et al" else "")
            val volPagesStr = when {
                volume.isNotBlank() && pages.isNotBlank() -> ";$volume:$pages"
                volume.isNotBlank() -> ";$volume"
                pages.isNotBlank() -> ";:$pages"
                else -> ""
            }
            val pmidStr = pmid?.takeIf { it.isNotBlank() }?.let { ". PMID: $it" } ?: ""
            val doiStr = doi?.takeIf { it.isNotBlank() }?.let { ". DOI: $it" } ?: ""
            return "$authorsStr. $title. $journal. $year$volPagesStr$pmidStr$doiStr"
        }
        return referenceText.completeCitationText(pmid, doi)
    }

    private fun sanitizeReferenceForLookup(reference: ReferenceJson): ReferenceJson {
        val pmid = reference.pmid
            ?.trim()
            ?.takeIf { it.isNotBlank() }
            ?: extractPmid(reference.referenceText).takeIf { it.isNotBlank() }
        val doi = reference.doi
            ?.trim()
            ?.takeIf { it.isNotBlank() }
            ?: extractDoi(reference.referenceText)
        return reference.copy(
            referenceText = stripReferenceMetadata(reference.referenceText),
            pmid = pmid,
            doi = doi,
            pubmedVerified = !pmid.isNullOrBlank()
        )
    }

    private fun stripReferenceMetadata(text: String): String {
        return text
            .replace(Regex("""\bPMID\s*:?\s*\d{4,12}\b\.?""", RegexOption.IGNORE_CASE), "")
            .replace(Regex("""\bDOI\s*:?\s*10\.\d{4,9}/[^\s<>"']+\.?""", RegexOption.IGNORE_CASE), "")
            .replace(Regex("\\s+"), " ")
            .trim()
            .trimEnd('.', ';', ',')
            .trim()
    }

    private fun stripAppendedReferenceBlock(text: String): String {
        if (text.isBlank()) return text
        val lines = text.lines()
        val referenceHeaderIndex = lines.indexOfFirst { line ->
            line.trim().equals("REFERENCES", ignoreCase = true) ||
                line.trim().endsWith("REFERENCES", ignoreCase = true)
        }
        if (referenceHeaderIndex < 0) return text
        return lines.take(referenceHeaderIndex).joinToString("\n").trimEnd()
    }

    private fun buildDefaultChapterTextBoxes(chapter: Chapter): List<ChapterTextBoxJson> {
        val sourceText = stripAppendedReferenceBlock(
            extractVisibleText(chapter.rawJson).ifBlank { chapter.content }
        ).trim()
        if (sourceText.isBlank()) return emptyList()

        val paragraphs = sourceText
            .split(Regex("\\r?\\n\\s*\\r?\\n+"))
            .map { it.trim() }
            .filter { it.isNotBlank() }

        if (paragraphs.isEmpty()) return emptyList()

        var y = 0.08f
        return paragraphs.take(8).mapIndexedNotNull { index, paragraph ->
            val approxWidth = 0.84f
            val estimatedHeight = estimateTextBoxHeight(paragraph, approxWidth).coerceAtMost(0.30f)
            if (y + estimatedHeight > 0.92f) return@mapIndexedNotNull null
            val box = ChapterTextBoxJson(
                id = "box_${index + 1}",
                text = paragraph,
                x = 0.08f,
                y = y,
                width = approxWidth,
                height = estimatedHeight
            )
            y += estimatedHeight + 0.035f
            box
        }
    }

    private fun ensureChapterTextBoxes(chapter: Chapter): List<ChapterTextBoxJson> {
        return chapter.textBoxes.takeIf { it.isNotEmpty() } ?: buildDefaultChapterTextBoxes(chapter)
    }

    private fun estimateTextBoxHeight(text: String, widthFraction: Float): Float {
        val avgCharsPerLine = (widthFraction * 72f).coerceAtLeast(28f)
        val estimatedLines = (text.length / avgCharsPerLine).toInt().coerceAtLeast(text.lineSequence().count())
        return (0.08f + estimatedLines * 0.038f).coerceIn(0.12f, 0.42f)
    }

    private data class ReferenceSearchHints(
        val doi: String? = null,
        val year: String? = null,
        val titleHint: String? = null,
        val titleCandidates: List<String> = emptyList(),
        val authorHint: String? = null,
        val cleanedText: String = ""
    )

    private fun buildReferenceSearchHints(referenceText: String): ReferenceSearchHints {
        val cleaned = referenceText
            .replace(Regex("^\\s*\\[?\\d+\\]?\\s*[.)-]?\\s*"), "")
            .replace(Regex("\\s+"), " ")
            .trim()

        val doi = Regex("""10\.\d{4,9}/[^\s<>"']+""", RegexOption.IGNORE_CASE)
            .find(cleaned)
            ?.value

        val year = Regex("""\b(19|20)\d{2}\b""")
            .find(cleaned)
            ?.value

        val authorPart = cleaned
            .substringBefore(".")
            .trim()
            .takeIf { it.isNotBlank() }

        val titleCandidates = extractReferenceTitleCandidates(cleaned)
        val titleHint = titleCandidates.firstOrNull()

        return ReferenceSearchHints(
            doi = doi,
            year = year,
            titleHint = titleHint,
            titleCandidates = titleCandidates,
            authorHint = authorPart,
            cleanedText = cleaned
        )
    }

    private fun extractReferenceTitleCandidates(cleanedReference: String): List<String> {
        val cleaned = cleanedReference
            .replace(Regex("""\bPMID\s*:?\s*\d{4,12}\b\.?""", RegexOption.IGNORE_CASE), "")
            .replace(Regex("""\bDOI\s*:?\s*10\.\d{4,9}/[^\s<>"']+\.?""", RegexOption.IGNORE_CASE), "")
            .replace(Regex("\\s+"), " ")
            .trim()
            .trimEnd('.', ';', ',')

        val segments = cleaned
            .split(Regex("""\.\s+"""))
            .map { it.trim().trim('.', ';', ',') }
            .filter { it.isNotBlank() }

        val candidates = linkedSetOf<String>()
        segments.drop(1).forEach { segment ->
            if (looksLikeArticleTitle(segment)) candidates += segment
        }
        segments.forEach { segment ->
            if (looksLikeArticleTitle(segment)) candidates += segment
        }

        val longestPhrase = longestReferencePhrase(cleaned)
        if (longestPhrase.isNotBlank()) candidates += longestPhrase

        return candidates
            .map { it.replace(Regex("""\s+"""), " ").trim().trimEnd('.', ';', ',') }
            .filter { searchableTokenCount(it) >= 3 || it.length >= 20 }
            .distinct()
            .take(5)
    }

    private fun looksLikeArticleTitle(segment: String): Boolean {
        val normalized = normalizeReferenceText(segment)
        if (normalized.isBlank()) return false
        if (Regex("""\b(19|20)\d{2}\b""").containsMatchIn(segment)) return false
        if (normalized.contains("doi") || normalized.contains("pmid")) return false
        val tokens = segment.split(Regex("\\s+")).filter { it.any(Char::isLetter) }
        if (tokens.size < 3) return false
        val lower = normalized.split(Regex("\\s+")).toSet()
        val journalWords = setOf("journal", "j", "vol", "volume", "issue", "pages", "pp", "pubmed", "lancet", "bmj")
        if (lower.any { it in journalWords } && tokens.size <= 6) return false
        return true
    }

    private fun longestReferencePhrase(cleanedReference: String): String {
        return cleanedReference
            .split(Regex("""[.;]"""))
            .map { it.trim() }
            .filter { looksLikeArticleTitle(it) }
            .maxByOrNull { searchableTokenCount(it) }
            .orEmpty()
    }

    private data class PubMedMatch(
        val pmid: String,
        val doi: String?,
        val articleTitle: String,
        val canonicalReference: String
    )

    private data class PubMedReviewSource(
        val reference: ReferenceJson,
        val title: String,
        val abstractText: String,
        val abstractSections: List<PubMedAbstractSectionJson> = emptyList(),
        val citedBy: List<PubMedCitedByArticleJson> = emptyList()
    )

    private data class ReferenceEvidence(
        val reference: ReferenceJson,
        val sourceType: String,
        val parentPmid: String? = null,
        val title: String = "",
        val abstractText: String = "",
        val abstractSections: List<PubMedAbstractSectionJson> = emptyList()
    )

    private data class PubMedFetchedAbstract(
        val abstractText: String = "",
        val sections: List<PubMedAbstractSectionJson> = emptyList()
    )

    private suspend fun searchPubMedReference(referenceText: String): PubMedMatch? = withContext(Dispatchers.IO) {
        runCatching {
            val hints = buildReferenceSearchHints(referenceText)
            val cacheKey = normalizeReferenceText(hints.cleanedText).take(240)
            pubMedSearchCache[cacheKey]?.let { return@runCatching it }

            val queries = buildPubMedQueries(hints)
            val candidates = mutableListOf<PubMedMatch>()

            for (query in queries) {
                candidates += searchPubMedMatches(query, hints, limit = 10)
                val bestSoFar = candidates.maxByOrNull { scorePubMedMatch(it, hints) }
                if (bestSoFar != null && scorePubMedMatch(bestSoFar, hints) >= exactPubMedMatchScore) {
                    pubMedSearchCache[cacheKey] = bestSoFar
                    return@runCatching bestSoFar
                }
            }

            candidates
                .maxByOrNull { scorePubMedMatch(it, hints) }
                ?.takeIf { isAcceptablePubMedSearchMatch(it, hints) }
                ?.also {
                    pubMedSearchCache[cacheKey] = it
                }
        }.getOrNull()
    }

    private fun buildPubMedQueries(hints: ReferenceSearchHints): List<String> {
        val queries = linkedSetOf<String>()

        hints.doi?.takeIf { it.isNotBlank() }?.let { doi ->
            queries += "\"$doi\""
            queries += doi
        }

        hints.titleCandidates.forEach { title ->
            val cleanTitle = title.take(220)
            queries += "\"${cleanTitle.take(160)}\""
            hints.year?.takeIf { it.isNotBlank() }?.let { year ->
                queries += "\"${cleanTitle.take(140)}\" AND $year[dp]"
            }
            queries += cleanTitle
            hints.authorHint?.takeIf { it.isNotBlank() }?.let { author ->
                queries += "${author.take(80)} ${cleanTitle.take(120)}"
            }
        }

        hints.authorHint?.takeIf { it.isNotBlank() }?.let { author ->
            queries += author.take(180)
        }

        val titleWords = (hints.titleHint ?: hints.cleanedText)
            .split(Regex("\\s+"))
            .map { it.trim('.', ',', ';', ':', '(', ')', '[', ']') }
            .filter { it.length >= 4 && !it.all(Char::isDigit) }
            .take(10)
        if (titleWords.isNotEmpty()) {
            queries += titleWords.joinToString(" ")
            hints.year?.takeIf { it.isNotBlank() }?.let { year ->
                queries += "${titleWords.joinToString(" ")} AND $year[dp]"
            }
            queries += titleWords.take(6).joinToString(" ")
        }

        val compact = hints.cleanedText.take(220)
        if (compact.isNotBlank()) queries += compact

        return queries.filter { it.isNotBlank() }.distinct()
    }

    private suspend fun searchPubMedMatches(
        query: String,
        hints: ReferenceSearchHints,
        limit: Int = 5
    ): List<PubMedMatch> = withContext(Dispatchers.IO) {
        runCatching {
            val encodedQuery = java.net.URLEncoder.encode(query, "UTF-8")
            val searchUrl = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&retmax=$limit&term=$encodedQuery"
            rawClient.newCall(
                Request.Builder().url(searchUrl).build()
            ).execute().use { searchResponse ->
                if (!searchResponse.isSuccessful) return@withContext emptyList()

                val searchJson = searchResponse.body?.string().orEmpty()
                val searchObj = JsonParser.parseString(searchJson).asJsonObject
                val idList = searchObj
                    .getAsJsonObject("esearchresult")
                    ?.getAsJsonArray("idlist")
                    ?.map { it.asString }
                    .orEmpty()
                    .distinct()

                batchFetchPubMedMatches(idList).values.toList()
            }
        }.getOrDefault(emptyList())
    }

    private suspend fun batchFetchPubMedMatches(pmids: List<String>): Map<String, PubMedMatch> = withContext(Dispatchers.IO) {
        val normalizedPmids = pmids
            .map { it.trim() }
            .filter { it.isNotBlank() }
            .distinct()
        if (normalizedPmids.isEmpty()) return@withContext emptyMap()

        val cached = normalizedPmids.mapNotNull { pmid ->
            pubMedPmidCache[pmid]?.let { pmid to it }
        }.toMap()
        val missing = normalizedPmids.filterNot { cached.containsKey(it) }
        if (missing.isEmpty()) return@withContext cached

        val fetched = mutableMapOf<String, PubMedMatch>()
        missing.chunked(80).forEach { chunk ->
            runCatching {
                val ids = chunk.joinToString(",")
                val summaryUrl = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json&id=$ids"
                rawClient.newCall(
                    Request.Builder().url(summaryUrl).build()
                ).execute().use { summaryResponse ->
                    if (!summaryResponse.isSuccessful) return@use

                    val summaryJson = summaryResponse.body?.string().orEmpty()
                    val summaryObj = JsonParser.parseString(summaryJson).asJsonObject
                    val resultObj = summaryObj.getAsJsonObject("result") ?: return@use

                    chunk.forEach { pmid ->
                        val item = resultObj.getAsJsonObject(pmid) ?: return@forEach
                        parsePubMedSummaryItem(pmid, item)?.let { match ->
                            pubMedPmidCache[pmid] = match
                            fetched[pmid] = match
                        }
                    }
                }
            }
        }

        cached + fetched
    }

    private suspend fun fetchPubMedMatch(pmid: String, hints: ReferenceSearchHints): PubMedMatch? = withContext(Dispatchers.IO) {
        runCatching {
            pubMedPmidCache[pmid]?.let { return@runCatching it }
            val summaryUrl = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json&id=$pmid"
            rawClient.newCall(
                Request.Builder().url(summaryUrl).build()
            ).execute().use { summaryResponse ->
                if (!summaryResponse.isSuccessful) {
                    return@runCatching PubMedMatch(
                        pmid = pmid,
                        doi = null,
                        articleTitle = "",
                        canonicalReference = "PMID:$pmid"
                    )
                }

                val summaryJson = summaryResponse.body?.string().orEmpty()
                val summaryObj = JsonParser.parseString(summaryJson).asJsonObject
                val resultObj = summaryObj
                    .getAsJsonObject("result")
                    ?.getAsJsonObject(pmid)

                parsePubMedSummaryItem(pmid, resultObj)?.also { pubMedPmidCache[pmid] = it }
            }
        }.getOrNull()
    }

    private fun fetchLiteratureReviewSources(): List<PubMedReviewSource> {
        val references = (
            parseReferencesVariable(_uiState.value.variables) +
                _uiState.value.verifiedPubMedReferences +
                _uiState.value.chapters.flatMap { it.chapterReferences }
            )
            .filter { it.hasRequiredPmid() }
            .distinctBy { it.pmid?.trim().orEmpty() }

        if (references.isEmpty()) return emptyList()

        val storedEvidenceByPmid = _uiState.value.verifiedPubMedAbstractSources
            .filter { it.pmid.isNotBlank() }
            .associateBy { it.pmid.trim() }

        return references.mapNotNull { reference ->
            val pmid = reference.pmid?.trim().orEmpty()
            val source = storedEvidenceByPmid[pmid] ?: return@mapNotNull null
            val abstractText = source.abstractText.trim()
            if (abstractText.isBlank()) return@mapNotNull null
            val title = pubMedPmidCache[pmid]?.articleTitle
                ?: source.title.ifBlank { reference.referenceText.substringBefore(".").trim() }
            PubMedReviewSource(
                reference = reference.copy(
                    citation = serializedCitation(0),
                    referenceText = source.citation.ifBlank { reference.completeCitationText() },
                    doi = reference.doi ?: source.doi,
                    pubmedVerified = true
                ),
                title = title,
                abstractText = abstractText,
                abstractSections = source.abstractSections,
                citedBy = source.similarArticles.ifEmpty { source.citedBy }
            )
        }
    }

    private suspend fun fetchPubMedAbstractSources(pmids: List<String>): List<PubMedAbstractSourceJson> = withContext(Dispatchers.IO) {
        val normalizedPmids = pmids.map { it.trim() }.filter { it.isNotBlank() }.distinct()
        if (normalizedPmids.isEmpty()) return@withContext emptyList()

        val cachedComplete = normalizedPmids
            .mapNotNull { pubMedAbstractSourceCache[it] }
        val missing = normalizedPmids.filter { pmid ->
            val cached = pubMedAbstractSourceCache[pmid]
            cached == null
        }
        val needsSimilarRefresh = normalizedPmids.filter { pmid ->
            val cached = pubMedAbstractSourceCache[pmid]
            cached != null && cached.similarArticles.isEmpty() && cached.citedBy.isEmpty()
        }
        if (missing.isEmpty() && needsSimilarRefresh.isEmpty()) return@withContext cachedComplete

        val abstractsByPmid = fetchPubMedAbstractRecords(missing)
        val matchesByPmid = batchFetchPubMedMatches(missing)
        val abstractWorkTotal = (missing.size + needsSimilarRefresh.size).coerceAtLeast(1)
        var abstractWorkDone = 0
        val fetched = missing.map { pmid ->
            val existing = pubMedAbstractSourceCache[pmid]
            val fetchedAbstract = abstractsByPmid[pmid]
            val abstractText = fetchedAbstract?.abstractText?.trim().orEmpty().ifBlank {
                existing?.abstractText?.trim().orEmpty()
            }
            val match = matchesByPmid[pmid] ?: pubMedPmidCache[pmid]
            _uiState.update {
                it.copy(
                    status = "Downloading PubMed abstract links ${abstractWorkDone + 1}/$abstractWorkTotal: PMID $pmid",
                    progressCurrent = abstractWorkDone,
                    progressTotal = abstractWorkTotal
                )
            }
            val similarArticles = fetchPubMedSimilarArticles(pmid)
            abstractWorkDone += 1
            _uiState.update {
                it.copy(
                    status = "PubMed abstract links downloaded $abstractWorkDone/$abstractWorkTotal",
                    progressCurrent = abstractWorkDone,
                    progressTotal = abstractWorkTotal
                )
            }
            PubMedAbstractSourceJson(
                pmid = pmid,
                doi = match?.doi ?: existing?.doi,
                title = match?.articleTitle.orEmpty().ifBlank { existing?.title.orEmpty() },
                citation = match?.canonicalReference.orEmpty().ifBlank { existing?.citation ?: "PMID: $pmid" },
                abstractText = abstractText,
                abstractSections = fetchedAbstract?.sections?.ifEmpty { existing?.abstractSections.orEmpty() }
                    ?: existing?.abstractSections.orEmpty(),
                similarArticles = similarArticles
            ).also { pubMedAbstractSourceCache[pmid] = it }
        }

        val refreshedSimilar = needsSimilarRefresh.mapNotNull { pmid ->
            val existing = pubMedAbstractSourceCache[pmid] ?: return@mapNotNull null
            _uiState.update {
                it.copy(
                    status = "Refreshing PubMed similar articles ${abstractWorkDone + 1}/$abstractWorkTotal: PMID $pmid",
                    progressCurrent = abstractWorkDone,
                    progressTotal = abstractWorkTotal
                )
            }
            val similarArticles = fetchPubMedSimilarArticles(pmid)
            abstractWorkDone += 1
            _uiState.update {
                it.copy(
                    status = "PubMed similar articles refreshed $abstractWorkDone/$abstractWorkTotal",
                    progressCurrent = abstractWorkDone,
                    progressTotal = abstractWorkTotal
                )
            }
            existing.copy(similarArticles = similarArticles).also { pubMedAbstractSourceCache[pmid] = it }
        }

        (refreshedSimilar + cachedComplete + fetched)
            .distinctBy { it.pmid.trim() }
    }

    private suspend fun fetchPubMedSimilarArticles(pmid: String): List<PubMedCitedByArticleJson> = withContext(Dispatchers.IO) {
        runCatching {
            val articleUrl = "https://pubmed.ncbi.nlm.nih.gov/$pmid/"
            rawClient.newCall(
                Request.Builder()
                    .url(articleUrl)
                    .header("User-Agent", "EduLabsRTM/1.0")
                    .build()
            ).execute().use { response ->
                if (!response.isSuccessful) return@runCatching emptyList()
                val document = Jsoup.parse(response.body?.string().orEmpty(), articleUrl)
                val similarLinks = document
                    .select("a.docsum-title[href][ref*=similar_articles_link], a.docsum-title[href][data-ga-category=similar_article], #similar-articles a.docsum-title[href], div.similar-articles a.docsum-title[href], section.similar-articles a.docsum-title[href], a[href*='linksrc=similar_articles_link']")
                    .mapNotNull { item ->
                        val similarPmid = Regex("""/(\d{4,12})/?""")
                            .find(item.attr("href"))
                            ?.groupValues
                            ?.getOrNull(1)
                            .orEmpty()
                        if (similarPmid.isBlank() || similarPmid == pmid) return@mapNotNull null
                        val title = item.text().replace(Regex("\\s+"), " ").trim()
                        PubMedCitedByArticleJson(
                            pmid = similarPmid,
                            title = title,
                            articleUrl = "https://pubmed.ncbi.nlm.nih.gov/$similarPmid/"
                        )
                    }
                    .distinctBy { it.pmid }

                val htmlPmids = similarLinks.map { it.pmid }
                val relatedPmids = if (htmlPmids.isNotEmpty()) {
                    htmlPmids
                } else {
                    fetchPubMedSimilarPmidsFromELink(pmid)
                }
                val baseSimilarArticles = if (similarLinks.isNotEmpty()) {
                    similarLinks
                } else {
                    relatedPmids.map { similarPmid ->
                        PubMedCitedByArticleJson(
                            pmid = similarPmid,
                            articleUrl = "https://pubmed.ncbi.nlm.nih.gov/$similarPmid/"
                        )
                    }
                }.distinctBy { it.pmid }.take(10)

                val matches = batchFetchPubMedMatches(baseSimilarArticles.map { it.pmid })
                val abstracts = fetchPubMedAbstractRecords(baseSimilarArticles.map { it.pmid })
                baseSimilarArticles.map { similar ->
                    val match = matches[similar.pmid]
                    val fetchedAbstract = abstracts[similar.pmid]
                    similar.copy(
                        doi = match?.doi,
                        title = similar.title.ifBlank { match?.articleTitle.orEmpty() },
                        citation = similar.citation.ifBlank { match?.canonicalReference.orEmpty() },
                        abstractText = fetchedAbstract?.abstractText.orEmpty(),
                        abstractSections = fetchedAbstract?.sections.orEmpty()
                    )
                }
            }
        }.onFailure {
            Log.e("ThesisViewModel", "PubMed similar-article scrape failed for PMID $pmid", it)
        }.getOrDefault(emptyList())
    }

    private suspend fun fetchPubMedSimilarPmidsFromELink(pmid: String): List<String> = withContext(Dispatchers.IO) {
        runCatching {
            val url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi" +
                "?dbfrom=pubmed&db=pubmed&id=$pmid&cmd=neighbor_score&retmode=xml"
            rawClient.newCall(
                Request.Builder()
                    .url(url)
                    .header("User-Agent", "EduLabsRTM/1.0")
                    .build()
            ).execute().use { response ->
                if (!response.isSuccessful) return@runCatching emptyList()
                val xml = response.body?.string().orEmpty()
                val document = Jsoup.parse(xml, "", org.jsoup.parser.Parser.xmlParser())
                document.select("LinkSetDb Link Id")
                    .map { it.text().trim() }
                    .filter { it.isNotBlank() && it != pmid }
                    .distinct()
                    .take(10)
            }
        }.onFailure {
            Log.e("ThesisViewModel", "PubMed ELink similar lookup failed for PMID $pmid", it)
        }.getOrDefault(emptyList())
    }

    private suspend fun fetchPubMedAbstracts(pmids: List<String>): Map<String, String> = withContext(Dispatchers.IO) {
        fetchPubMedAbstractRecords(pmids).mapValues { it.value.abstractText }
    }

    private suspend fun fetchPubMedAbstractRecords(pmids: List<String>): Map<String, PubMedFetchedAbstract> = withContext(Dispatchers.IO) {
        val normalizedPmids = pmids.map { it.trim() }.filter { it.isNotBlank() }.distinct()
        if (normalizedPmids.isEmpty()) return@withContext emptyMap()

        val fetched = mutableMapOf<String, PubMedFetchedAbstract>()
        normalizedPmids.chunked(40).forEach { chunk ->
            runCatching {
                val ids = chunk.joinToString(",")
                val url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&retmode=xml&id=$ids"
                rawClient.newCall(Request.Builder().url(url).build()).execute().use { response ->
                    if (!response.isSuccessful) return@use
                    val xml = response.body?.string().orEmpty()
                    val document = Jsoup.parse(xml, "", org.jsoup.parser.Parser.xmlParser())
                    document.select("PubmedArticle").forEach { article ->
                        val pmid = article.selectFirst("PMID")?.text()?.trim().orEmpty()
                        if (pmid.isBlank()) return@forEach
                        val sections = parsePubMedAbstractSections(article)
                        val abstractText = sections.joinToString("\n") { section ->
                            if (section.label.isNotBlank()) "${section.label}: ${section.text}" else section.text
                        }
                        if (abstractText.isNotBlank()) {
                            fetched[pmid] = PubMedFetchedAbstract(
                                abstractText = abstractText,
                                sections = sections
                            )
                        }
                    }
                }
            }
        }
        fetched
    }

    private fun parsePubMedAbstractSections(article: org.jsoup.nodes.Element): List<PubMedAbstractSectionJson> {
        return article.select("AbstractText").mapNotNull { node ->
            val label = node.attr("Label").trim()
                .ifBlank { node.attr("NlmCategory").trim() }
            val text = node.text().trim().replace(Regex("\\s+"), " ")
            if (text.isBlank()) return@mapNotNull null
            val category = normalizeAbstractSectionCategory(label)
            PubMedAbstractSectionJson(
                label = label.ifBlank { category.ifBlank { "Abstract" } },
                category = category.ifBlank { "abstract" },
                text = text
            )
        }
    }

    private fun normalizeAbstractSectionLabel(label: String): String {
        return label
            .trim()
            .replace("&", " and ")
            .replace("/", " ")
            .replace("-", " ")
            .replace("_", " ")
            .lowercase()
            .replace(Regex("\\s+"), " ")
            .trim()
    }

    private fun normalizeAbstractSectionCategory(label: String): String {
        val normalized = normalizeAbstractSectionLabel(label)
        if (normalized.isBlank()) return "abstract"
        return when {
            normalized in setOf("abstract", "summary", "unlabelled") -> "abstract"
            normalized.contains("background") || normalized.contains("motivation") || normalized.contains("context") -> "background"
            normalized.contains("objective") || normalized.contains("purpose") || normalized == "aim" ||
                normalized.contains("aims") || normalized.contains("hypothesis") -> "objective"
            normalized.contains("introduction") -> "introduction"
            normalized.contains("method") || normalized.contains("material") || normalized.contains("design") ||
                normalized.contains("setting") || normalized.contains("participant") || normalized.contains("approach") ||
                normalized.contains("investigation") -> "materials and methods"
            normalized.contains("result") || normalized.contains("finding") || normalized.contains("outcome") ||
                normalized.contains("measurement") -> "results"
            normalized.contains("discussion") || normalized.contains("interpretation") || normalized.contains("implication") -> "discussion"
            normalized.contains("conclusion") || normalized.contains("take home") || normalized.contains("relevance") -> "conclusion"
            normalized.contains("limitation") || normalized.contains("future") -> "discussion and conclusion"
            normalized.contains("funding") -> "funding"
            else -> normalized
        }
    }

    private fun hasPurposeMethodResultConclusion(abstractText: String): Boolean {
        val normalized = normalizeReferenceText(abstractText)
        if (normalized.isBlank()) return false
        val hasPurpose = Regex("""\b(purpose|aim|aims|objective|objectives)\b""").containsMatchIn(normalized)
        val hasMethods = Regex("""\b(method|methods|methodology|design|materials and methods)\b""").containsMatchIn(normalized)
        val hasResults = Regex("""\b(result|results|findings)\b""").containsMatchIn(normalized)
        val hasConclusion = Regex("""\b(conclusion|conclusions|interpretation)\b""").containsMatchIn(normalized)
        return hasPurpose && hasMethods && hasResults && hasConclusion
    }

    private fun parsePubMedSummaryItem(pmid: String, resultObj: JsonObject?): PubMedMatch? {
        val title = resultObj?.get("title")?.takeIf { it.isJsonPrimitive }?.asString.orEmpty()
        val source = resultObj?.get("source")?.takeIf { it.isJsonPrimitive }?.asString.orEmpty()
        val pubDate = resultObj?.get("pubdate")?.takeIf { it.isJsonPrimitive }?.asString.orEmpty()
        val doi = resultObj?.getAsJsonArray("articleids")
            ?.mapNotNull { element ->
                val obj = element.asJsonObject
                val idType = obj.get("idtype")?.takeIf { it.isJsonPrimitive }?.asString.orEmpty()
                val value = obj.get("value")?.takeIf { it.isJsonPrimitive }?.asString.orEmpty()
                if (idType.equals("doi", ignoreCase = true) && value.isNotBlank()) value else null
            }
            ?.firstOrNull()

        val authors = resultObj?.getAsJsonArray("authors")
            ?.mapNotNull { element ->
                val obj = element.asJsonObject
                obj.get("name")?.takeIf { it.isJsonPrimitive }?.asString?.trim()
            }
            ?.take(3)
            .orEmpty()

        val authorPart = if (authors.isNotEmpty()) authors.joinToString(", ") else ""
        val journalPart = source.ifBlank { "PubMed" }
        val reference = buildString {
            if (authorPart.isNotBlank()) append(authorPart).append(". ")
            if (title.isNotBlank()) append(title).append(". ")
            append(journalPart)
            if (pubDate.isNotBlank()) append(". ").append(pubDate)
            append(". PMID: ").append(pmid)
            doi?.takeIf { it.isNotBlank() }?.let { append(". DOI: ").append(it) }
        }.trim()

        return PubMedMatch(
            pmid = pmid,
            doi = doi,
            articleTitle = title,
            canonicalReference = reference
        )
    }

    private fun scorePubMedMatch(match: PubMedMatch, hints: ReferenceSearchHints): Int {
        var score = 0
        val canonical = normalizeReferenceText(match.canonicalReference)
        val articleTitle = normalizeReferenceText(match.articleTitle)
        val titleHint = normalizeReferenceText(hints.titleHint.orEmpty())
        val cleaned = normalizeReferenceText(hints.cleanedText)
        val year = hints.year.orEmpty()

        if (hints.doi != null && match.doi != null && normalizeReferenceText(hints.doi) == normalizeReferenceText(match.doi)) {
            score += 100
        }

        if (year.isNotBlank() && canonical.contains(year)) {
            score += 20
        }

        val bestTitleOverlap = hints.titleCandidates
            .maxOfOrNull { candidate ->
                maxOf(
                    tokenOverlapScore(normalizeReferenceText(candidate), articleTitle),
                    tokenOverlapScore(normalizeReferenceText(candidate), canonical)
                )
            }
            ?: tokenOverlapScore(titleHint, articleTitle)
        val overlapWithCleanedTitle = tokenOverlapScore(cleaned, articleTitle)
        val overlapWithCleaned = tokenOverlapScore(cleaned, canonical)
        score += bestTitleOverlap * 2
        score += overlapWithCleanedTitle
        score += (overlapWithCleaned / 2)

        if (hints.titleCandidates.any { candidate ->
                val normalizedCandidate = normalizeReferenceText(candidate)
                normalizedCandidate.length >= 30 && articleTitle.contains(normalizedCandidate.take(30))
            }
        ) {
            score += 30
        }
        if (canonical.contains(titleHint.take(40)) && titleHint.isNotBlank()) score += 10
        if (canonical.contains(cleaned.take(40)) && cleaned.isNotBlank()) score += 10

        return score
    }

    private fun isAcceptablePubMedSearchMatch(match: PubMedMatch, hints: ReferenceSearchHints): Boolean {
        val canonical = normalizeReferenceText(match.canonicalReference)
        val articleTitle = normalizeReferenceText(match.articleTitle)
        val titleHint = normalizeReferenceText(hints.titleHint.orEmpty())
        val cleaned = normalizeReferenceText(hints.cleanedText)
        val score = scorePubMedMatch(match, hints)

        if (hints.doi != null && match.doi != null && normalizeReferenceText(hints.doi) == normalizeReferenceText(match.doi)) {
            return true
        }

        val bestTitleCandidate = hints.titleCandidates.maxByOrNull { searchableTokenCount(it) } ?: hints.titleHint.orEmpty()
        val normalizedBestTitle = normalizeReferenceText(bestTitleCandidate)
        if (normalizedBestTitle.isNotBlank()) {
            val titleOverlap = maxOf(
                tokenOverlapScore(normalizedBestTitle, articleTitle),
                tokenOverlapScore(normalizedBestTitle, canonical)
            )
            val titleTokenCount = searchableTokenCount(normalizedBestTitle)
            val requiredTitleOverlap = when {
                titleTokenCount <= 3 -> 10
                titleTokenCount <= 6 -> minimumTitleTokenOverlapScore
                else -> 20
            }
            val hasTitlePhrase = normalizedBestTitle.length >= 30 &&
                (articleTitle.contains(normalizedBestTitle.take(30)) || canonical.contains(normalizedBestTitle.take(30)))
            return score >= minimumPubMedSearchScore &&
                (titleOverlap >= requiredTitleOverlap || hasTitlePhrase)
        }

        return score >= exactPubMedMatchScore && tokenOverlapScore(cleaned, canonical) >= minimumTitleTokenOverlapScore
    }

    private fun tokenOverlapScore(source: String, target: String): Int {
        if (source.isBlank() || target.isBlank()) return 0
        val sourceTokens = source.split(Regex("\\s+")).filter { it.length >= 4 }.take(20).toSet()
        val targetTokens = target.split(Regex("\\s+")).filter { it.length >= 4 }.toSet()
        if (sourceTokens.isEmpty() || targetTokens.isEmpty()) return 0
        return sourceTokens.count { it in targetTokens } * 5
    }

    private fun searchableTokenCount(text: String): Int {
        return text.split(Regex("\\s+")).count { it.length >= 4 }
    }

    private fun extractAbbreviationsFromText(text: String): List<AbbreviationJson> {
        if (text.isBlank()) return emptyList()

        val list = mutableListOf<AbbreviationJson>()
        
        // 1. Line-by-line format e.g. "BMI: Body Mass Index"
        text.lines().forEach { line ->
            val trimmed = line.trim()
            val matches = Regex("^([A-Z0-9][A-Z0-9/\\-]{1,12})\\s*[:=\\-–—]\\s*(.+)$")
                .find(trimmed)
            if (matches != null) {
                val short = matches.groupValues.getOrNull(1).orEmpty().trim()
                val full = matches.groupValues.getOrNull(2).orEmpty().trim()
                if (short.isNotBlank() && full.isNotBlank()) {
                    list.add(AbbreviationJson(shortForm = short, fullForm = full))
                }
            }
        }

        // 2. Paragraph format e.g. "Body Mass Index (BMI)"
        val regex = Regex("""\b((?:[a-zA-Z]{3,}\s+){1,5}[a-zA-Z]{3,})\s*\((\b[A-Z]{2,6}\b)\)""")
        regex.findAll(text).forEach { match ->
            val full = match.groups[1]?.value?.trim().orEmpty()
            val short = match.groups[2]?.value?.trim().orEmpty()
            if (full.isNotBlank() && short.isNotBlank()) {
                val words = full.split(Regex("\\s+"))
                val firstLetters = words.mapNotNull { it.firstOrNull()?.uppercaseChar() }.joinToString("")
                if (short.all { it in firstLetters || it.lowercaseChar() in full }) {
                    list.add(AbbreviationJson(shortForm = short, fullForm = full))
                }
            }
        }

        return list.distinctBy { it.shortForm }
    }

    private fun parseThesisChapterJson(text: String, fallbackName: String = ""): ThesisChapterJson {
        val cleaned = extractJsonBlock(text)
        val jsonElement = runCatching { JsonParser.parseString(cleaned) }.getOrNull()
        if (jsonElement != null && !hasMeaningfulJsonContent(jsonElement)) {
            return fallbackThesisChapterJson(fallbackName)
        }
        return try {
            val parsed = gson.fromJson(cleaned, ThesisChapterJson::class.java)
            normalizeThesisChapterJson(parsed, fallbackName)
        } catch (_: Exception) {
            parseLooseThesisChapterJson(cleaned, fallbackName)
        }
    }

    private fun hasMeaningfulJsonContent(element: com.google.gson.JsonElement?): Boolean {
        if (element == null || element.isJsonNull) return false
        return when {
            element.isJsonPrimitive -> {
                val value = runCatching { element.asString }.getOrNull()?.trim().orEmpty()
                value.isNotBlank() && value != "..." && !isWeakChapterContent(value)
            }
            element.isJsonArray -> element.asJsonArray.any { hasMeaningfulJsonContent(it) }
            element.isJsonObject -> element.asJsonObject.entrySet().any { (key, value) ->
                val normalizedKey = key.lowercase()
                normalizedKey !in setOf(
                    "chapter_name",
                    "chapter_type",
                    "title",
                    "signature",
                    "signatureline",
                    "guideSignature".lowercase(),
                    "hodSignature".lowercase(),
                    "date",
                    "page",
                    "number",
                    "table_number",
                    "figure_number",
                    "chart_id"
                ) && hasMeaningfulJsonContent(value)
            }
            else -> false
        }
    }

    private fun isMeaningfulThesisChapter(chapter: ThesisChapterJson): Boolean {
        return chapter.sections.any { section ->
            section.content?.trim()?.takeIf { !isWeakChapterContent(it) } != null ||
                section.paragraphs.any { !isWeakChapterContent(it) } ||
                section.bullets.any { !isWeakChapterContent(it) } ||
                section.numberedPoints.any { !isWeakChapterContent(it) } ||
                section.subsections.any { sub -> !isWeakChapterContent(sub.content) } ||
                section.table?.let { table -> table.rows.isNotEmpty() || table.data.isNotEmpty() } == true ||
                section.figures.any { it.title.isNotBlank() || it.caption.isNotBlank() || it.imageSearchQuery.isNotBlank() } ||
                section.references.any { it.referenceText.isNotBlank() || it.citation.isNotBlank() || !it.pmid.isNullOrBlank() }
        } ||
            chapter.tables.any { it.rows.isNotEmpty() || it.data.isNotEmpty() || it.headers.isNotEmpty() } ||
            chapter.figures.any { it.title.isNotBlank() || it.caption.isNotBlank() || it.imageSearchQuery.isNotBlank() } ||
            chapter.charts.any { it.title.isNotBlank() || it.labels.isNotEmpty() || it.values.isNotEmpty() || it.datasets.isNotEmpty() } ||
            chapter.abbreviations.any { it.shortForm.isNotBlank() || it.fullForm.isNotBlank() } ||
            chapter.chapterReferences.any { it.referenceText.isNotBlank() || !it.pmid.isNullOrBlank() }
    }

    private fun isMeaningfulParsedChapterValue(chapterName: String, parsed: Any): Boolean {
        return when (parsed) {
            is ThesisChapterJson -> isMeaningfulThesisChapter(parsed)
            is ResultsJson -> parsed.sections.any { !isWeakChapterContent(it.content) || it.observations.orEmpty().any { obs -> !isWeakChapterContent(obs) } } ||
                parsed.tables.any { it.rows.isNotEmpty() || it.data.isNotEmpty() || it.headers.isNotEmpty() } ||
                parsed.charts.any { it.title.isNotBlank() || it.labels.isNotEmpty() || it.values.isNotEmpty() || it.datasets.isNotEmpty() }
            is ReferencesJson -> parsed.references.any { it.text.isNotBlank() || !it.pmid.isNullOrBlank() || !it.doi.isNullOrBlank() }
            is TitlePageJson -> listOf(parsed.title, parsed.author, parsed.guide, parsed.institution, parsed.department, parsed.degree, parsed.year)
                .any { it.isNotBlank() && it != chapterName }
            is AbstractJson -> listOf(parsed.background, parsed.aim, parsed.methods, parsed.results, parsed.conclusion).any { !isWeakChapterContent(it) } ||
                parsed.keywords.any { it.isNotBlank() }
            is CertificateJson -> !isWeakChapterContent(parsed.body)
            is DeclarationJson -> parsed.statement.isNotBlank() && parsed.statement != "I hereby declare that..."
            is AcknowledgementsJson -> parsed.acknowledgements.any { !isWeakChapterContent(it) }
            is TableOfContentsJson -> parsed.entries.any { it.title.isNotBlank() }
            is ListOfTablesJson -> parsed.tables.any { it.title.isNotBlank() }
            is ListOfFiguresJson -> parsed.figures.any { it.title.isNotBlank() }
            is ListOfAbbreviationsJson -> parsed.abbreviations.any { it.short.isNotBlank() || it.full.isNotBlank() }
            is KeywordsJson -> parsed.keywords.any { it.isNotBlank() }
            is HypothesisJson -> !isWeakChapterContent(parsed.nullHypothesis) || !isWeakChapterContent(parsed.alternateHypothesis)
            is AppendicesJson -> parsed.appendices.any { !isWeakChapterContent(it.title) || !isWeakChapterContent(it.content) }
            is MethodologyJson -> !isWeakChapterContent(parsed.designType) || parsed.inclusionCriteria.any { !isWeakChapterContent(it) } || parsed.exclusionCriteria.any { !isWeakChapterContent(it) }
            is DiscussionJson -> !isWeakChapterContent(parsed.keyFindings) || parsed.comparisonWithLiterature.any { !isWeakChapterContent(it.finding) }
            is ProformaJson -> listOf(parsed.patientName, parsed.age, parsed.sex, parsed.opdIpNo, parsed.address, parsed.history, parsed.examination, parsed.investigations, parsed.diagnosis)
                .any { !isWeakChapterContent(it) }
            is ConsentFormJson -> listOf(parsed.introduction, parsed.procedure, parsed.risks, parsed.benefits, parsed.confidentiality)
                .any { !isWeakChapterContent(it) }
            else -> hasMeaningfulJsonContent(runCatching { JsonParser.parseString(gson.toJson(parsed)) }.getOrNull())
        }
    }

    private fun validateOrThrowParsedChapterValue(chapterName: String, rawJson: String, schema: ChapterSchema?): Any {
        if (schema == null) {
            val generic = try {
                parseThesisChapterJson(rawJson, chapterName)
            } catch (e: Exception) {
                throw Exception("JSON Syntax Error: ${e.message}\nRaw Output: ${rawJson.take(300)}")
            }
            if (!isMeaningfulThesisChapter(generic)) {
                throw Exception("Schema Validation Error: Chapter narrative structure is empty or weak.")
            }
            return generic
        }

        val parsed = try {
            schema.parser(rawJson)
        } catch (e: Exception) {
            val fallback = try {
                fallbackParsedChapterValue(chapterName, rawJson)
            } catch (fe: Exception) {
                null
            }
            if (fallback != null) {
                fallback
            } else {
                throw Exception("JSON Syntax Error: ${e.message}\nRaw Output: ${rawJson.take(300)}")
            }
        }

        if (parsed == null) {
            throw Exception("Could not parse chapter JSON.\nRaw Output: ${rawJson.take(300)}")
        }

        if (!isMeaningfulParsedChapterValue(chapterName, parsed)) {
            val reason = getDetailedUnmeaningfulReason(chapterName, parsed)
            throw Exception("Schema Validation Error: $reason")
        }

        return parsed
    }

    private fun getDetailedUnmeaningfulReason(chapterName: String, parsed: Any): String {
        return when (parsed) {
            is ThesisChapterJson -> {
                if (parsed.sections.isEmpty()) "JSON structure is empty (no sections found)."
                else {
                    val weakSections = parsed.sections.filter { s ->
                        s.content?.trim()?.takeIf { !isWeakChapterContent(it) } == null &&
                        s.paragraphs.all { isWeakChapterContent(it) } &&
                        s.bullets.all { isWeakChapterContent(it) } &&
                        s.numberedPoints.all { isWeakChapterContent(it) } &&
                        s.subsections.all { sub -> isWeakChapterContent(sub.content) } &&
                        (s.table == null || (s.table.rows.isEmpty() && s.table.data.isEmpty())) &&
                        s.figures.isEmpty() && s.references.isEmpty()
                    }
                    if (weakSections.size == parsed.sections.size) {
                        "All generated sections contain weak placeholder content or are blank."
                    } else {
                        "Chapter is missing meaningful narrative content or references."
                    }
                }
            }
            is ResultsJson -> {
                if (parsed.sections.isEmpty() && parsed.tables.isEmpty() && parsed.charts.isEmpty()) {
                    "Results chapter contains no sections, tables, or charts."
                } else {
                    "Results chapter has empty/placeholder text."
                }
            }
            is ReferencesJson -> {
                "No valid bibliography/references list could be extracted."
            }
            is TitlePageJson -> {
                "Title page is missing vital parameters (title, author, guide, institution, or year)."
            }
            is AbstractJson -> {
                "Structured abstract is missing required components (background, aim, methods, results, or conclusion)."
            }
            is CertificateJson -> {
                "Certificate body is empty or contains placeholders."
            }
            is DeclarationJson -> {
                "Declaration statement is blank or set to default placeholder."
            }
            is AcknowledgementsJson -> {
                "Acknowledgements list is empty or contains placeholder content."
            }
            is TableOfContentsJson -> "Table of Contents is empty."
            is ListOfTablesJson -> "List of Tables is empty."
            is ListOfFiguresJson -> "List of Figures is empty."
            is ListOfAbbreviationsJson -> "List of Abbreviations is empty."
            is KeywordsJson -> "Keywords list is empty."
            is HypothesisJson -> "Hypothesis fields (null/alternate) are blank or contain placeholders."
            is AppendicesJson -> "Appendices list is empty or contains placeholder content."
            is ProformaJson -> "Proforma form is blank or contains placeholder patient fields."
            is ConsentFormJson -> "Consent form is blank or missing key procedural details."
            else -> "The generated JSON structure is empty or weak."
        }
    }


    private fun verifySampleSizeCalculation(content: String): String? {
        var p = 0.5
        var d = 0.05
        val z = 1.96
        
        val pRegex = Regex("""(?i)\b(?:prevalence|proportion|rate)\b.*?\b(\d+(?:\.\d+)?)\s*%""")
        pRegex.find(content)?.let { match ->
            val pct = match.groups[1]?.value?.toDoubleOrNull()
            if (pct != null && pct > 0 && pct < 100) {
                p = pct / 100.0
            }
        }
        
        val dRegex = Regex("""(?i)\b(?:precision|error|allowable error|margin of error|bound)\b.*?\b(\d+(?:\.\d+)?)\s*%""")
        dRegex.find(content)?.let { match ->
            val pct = match.groups[1]?.value?.toDoubleOrNull()
            if (pct != null && pct > 0 && pct < 100) {
                d = pct / 100.0
            }
        }

        val expectedN = (z * z * p * (1 - p)) / (d * d)
        val expectedNRounded = Math.ceil(expectedN).toInt()

        val nRegex = Regex("""(?i)(?:sample size|size|n\s*=|N\s*=|patients|subjects|participants)\b.*?\b(\d+)\b""")
        val matchN = nRegex.findAll(content).mapNotNull { it.groups[1]?.value?.toIntOrNull() }.firstOrNull { it > 10 }
        
        if (matchN != null) {
            val diffPercent = Math.abs(matchN - expectedNRounded).toDouble() / expectedNRounded.toDouble()
            if (diffPercent > 0.05) {
                return "The mathematical Cochran's formula for prevalence ${p * 100}% and margin of error ${d * 100}% yields an expected sample size of $expectedNRounded, but the AI generated $matchN. Please ensure the generated content reflects the math correctly."
            }
        }
        return null
    }

    fun reindexAllCitations() {
        val chapters = _uiState.value.chapters
        val orderedChapters = chapters.filter { !autoGeneratedChapterNames.contains(it.name.lowercase().trim()) }
        val orderedReferences = mutableListOf<ReferenceJson>()
        val citationPattern = Regex("""\[(\d+)]""")
        
        val allRefs = chapters.flatMap { it.chapterReferences }.distinctBy { it.pmid ?: it.doi ?: canonicalReferenceTextKey(it.referenceText) }
        val refsByOldCitation = allRefs.associateBy { it.citation }

        val uniqueOldCitationsSeen = mutableListOf<String>()
        orderedChapters.forEach { chapter ->
            val text = chapter.content + " " + chapter.tables.flatMap { t -> t.rows.flatten() }.joinToString(" ")
            citationPattern.findAll(text).forEach { match ->
                val cit = "[${match.groups[1]?.value}]"
                if (cit in refsByOldCitation && cit !in uniqueOldCitationsSeen) {
                    uniqueOldCitationsSeen.add(cit)
                }
            }
        }

        allRefs.forEach { ref ->
            if (ref.citation !in uniqueOldCitationsSeen) {
                uniqueOldCitationsSeen.add(ref.citation)
            }
        }

        val citationRemap = mutableMapOf<String, String>()
        val newReferences = mutableListOf<ReferenceJson>()
        uniqueOldCitationsSeen.forEachIndexed { index, oldCit ->
            val newIndex = index + 1
            val newCit = "[$newIndex]"
            citationRemap[oldCit] = newCit
            
            val ref = refsByOldCitation[oldCit]
            if (ref != null) {
                newReferences.add(ref.copy(citation = newCit))
            }
        }

        val updatedChapters = chapters.map { chapter ->
            var updatedContent = chapter.content
            citationRemap.forEach { (old, new) ->
                val oldNum = old.removeSurrounding("[", "]")
                val newNum = new.removeSurrounding("[", "]")
                updatedContent = updatedContent.replace(Regex("""\b\Q$oldNum\E\b"""), newNum)
            }

            val updatedChapterRefs = chapter.chapterReferences.mapNotNull { ref ->
                val newCit = citationRemap[ref.citation]
                if (newCit != null) {
                    ref.copy(citation = newCit)
                } else null
            }.sortedBy { referenceNumber(it) ?: 999 }

            chapter.copy(
                content = updatedContent,
                chapterReferences = updatedChapterRefs
            )
        }

        _uiState.update { state ->
            val updatedVars = state.variables.map { v ->
                if (v.name == "References_Vancouver") {
                    v.copy(value = formatReferencesForVariable(newReferences))
                } else v
            }
            state.copy(
                chapters = updatedChapters,
                variables = updatedVars,
                verifiedPubMedReferences = newReferences
            )
        }
        saveSessionToFirebase(immediate = true)
    }

    private fun parseLooseThesisChapterJson(text: String, fallbackName: String): ThesisChapterJson {
        val jsonObject = runCatching { JsonParser.parseString(text).asJsonObject }.getOrNull()
            ?: return fallbackThesisChapterJson(fallbackName, text)

        val sections = mutableListOf<ThesisSectionJson>()

        if (jsonObject.has("sections") && jsonObject.get("sections").isJsonArray) {
            runCatching {
                jsonObject.getAsJsonArray("sections").forEach { element ->
                    val section = gson.fromJson(element, ThesisSectionJson::class.java)
                    sections += section
                }
            }
        }

        if (sections.isEmpty()) {
            val sectionFieldPairs = listOf(
                "content" to "Main content",
                "body" to "Main content",
                "text" to "Main content",
                "introduction" to "Introduction",
                "background" to "Background",
                "aim" to "Aim",
                "objective" to "Objective",
                "objectives" to "Objectives",
                "methods" to "Methods",
                "materials_and_methods" to "Materials and Methods",
                "results" to "Results",
                "discussion" to "Discussion",
                "conclusion" to "Conclusion",
                "summary" to "Summary",
                "recommendations" to "Recommendations",
                "limitations" to "Limitations",
                "future_scope" to "Future Scope",
                "future scope" to "Future Scope"
            )

            sectionFieldPairs.forEach { (fieldName, heading) ->
                val value = jsonObject.get(fieldName)?.takeIf { it.isJsonPrimitive }?.asString?.trim().orEmpty()
                if (value.isNotBlank()) {
                    sections += ThesisSectionJson(heading = heading, content = value)
                }
            }
        }

        if (sections.isEmpty() && jsonObject.has("heading") && jsonObject.has("content")) {
            val heading = jsonObject.get("heading")?.takeIf { it.isJsonPrimitive }?.asString.orEmpty()
            val content = jsonObject.get("content")?.takeIf { it.isJsonPrimitive }?.asString.orEmpty()
            if (heading.isNotBlank() || content.isNotBlank()) {
                sections += ThesisSectionJson(heading = heading.ifBlank { "Main content" }, content = content.ifBlank { null })
            }
        }

        val parsedTables = runCatching {
            if (jsonObject.has("tables") && jsonObject.get("tables").isJsonArray) {
                jsonObject.getAsJsonArray("tables").mapNotNull { element ->
                    runCatching { normalizeThesisTable(gson.fromJson(element, ThesisTableJson::class.java)) }.getOrNull()
                }
            } else emptyList()
        }.getOrElse { emptyList() }

        val parsedFigures = runCatching {
            if (jsonObject.has("figures") && jsonObject.get("figures").isJsonArray) {
                jsonObject.getAsJsonArray("figures").mapNotNull { element ->
                    runCatching { gson.fromJson(element, FigureJson::class.java) }.getOrNull()
                }
            } else emptyList()
        }.getOrElse { emptyList() }

        val parsedCharts = runCatching {
            if (jsonObject.has("charts") && jsonObject.get("charts").isJsonArray) {
                jsonObject.getAsJsonArray("charts").mapNotNull { element ->
                    runCatching { normalizeResultChart(gson.fromJson(element, ChartJson::class.java)) }.getOrNull()
                }
            } else emptyList()
        }.getOrElse { emptyList() }

        val parsedAbbreviations = runCatching {
            if (jsonObject.has("abbreviations") && jsonObject.get("abbreviations").isJsonArray) {
                jsonObject.getAsJsonArray("abbreviations").mapNotNull { element ->
                    runCatching { gson.fromJson(element, AbbreviationJson::class.java) }.getOrNull()
                }
            } else emptyList()
        }.getOrElse { emptyList() }

        val parsedReferences = runCatching {
            if (jsonObject.has("chapter_references") && jsonObject.get("chapter_references").isJsonArray) {
                jsonObject.getAsJsonArray("chapter_references").mapNotNull { element ->
                    runCatching { gson.fromJson(element, ReferenceJson::class.java) }.getOrNull()
                }
            } else emptyList()
        }.getOrElse { emptyList() }

        return normalizeThesisChapterJson(
            ThesisChapterJson(
                chapterName = jsonObject.get("chapter_name")?.takeIf { it.isJsonPrimitive }?.asString.orEmpty(),
                chapterType = jsonObject.get("chapter_type")?.takeIf { it.isJsonPrimitive }?.asString.orEmpty(),
                sections = sections,
                tables = parsedTables,
                figures = parsedFigures,
                charts = parsedCharts,
                abbreviations = parsedAbbreviations,
                chapterReferences = parsedReferences
            ),
            fallbackName
        )
    }

    private fun fallbackThesisChapterJson(fallbackName: String, rawText: String = ""): ThesisChapterJson {
        val fallbackSections = buildList {
            val trimmed = rawText.trim()
            if (trimmed.isNotBlank()) {
                add(
                    ThesisSectionJson(
                        heading = if (fallbackName.isBlank()) "Main content" else fallbackName,
                        content = trimmed
                    )
                )
            }
        }

        return ThesisChapterJson(
            chapterName = fallbackName,
            chapterType = chapterTypeFor(fallbackName),
            sections = fallbackSections
        )
    }

    private fun normalizeThesisChapterJson(
        chapter: ThesisChapterJson,
        fallbackName: String = ""
    ): ThesisChapterJson {
        val cleanedSections = chapter.sections.mapNotNull { section ->
            val heading = section.heading.trim()
            val content = section.content?.trim().orEmpty()
            val bullets = section.bullets.map { it.trim() }.filter { it.isNotBlank() }
            val numberedPoints = section.numberedPoints.map { it.trim() }.filter { it.isNotBlank() }
            val subsections = section.subsections.mapNotNull { sub ->
                val subHeading = sub.heading.trim()
                val subContent = sub.content.trim()
                if (subHeading.isBlank() && subContent.isBlank()) null else sub.copy(
                    heading = subHeading,
                    content = subContent
                )
            }
            val table = section.table?.let { normalizeThesisTable(it) }
            val figures = section.figures.filter { it.title.isNotBlank() || it.caption.isNotBlank() || it.imageSearchQuery.isNotBlank() }
            val references = section.references
                .map(::sanitizeReferenceForLookup)
                .filter { it.referenceText.isNotBlank() || it.citation.isNotBlank() || !it.pmid.isNullOrBlank() }

            if (
                heading.isBlank() &&
                content.isBlank() &&
                bullets.isEmpty() &&
                numberedPoints.isEmpty() &&
                subsections.isEmpty() &&
                table == null &&
                figures.isEmpty() &&
                references.isEmpty()
            ) {
                null
            } else {
                section.copy(
                    heading = heading,
                    content = if (content.isBlank()) null else content,
                    bullets = bullets,
                    numberedPoints = numberedPoints,
                    subsections = subsections,
                    table = table,
                    figures = figures,
                    references = references
                )
            }
        }

        val cleanedTopReferences = chapter.chapterReferences
            .map(::sanitizeReferenceForLookup)
            .filter { it.referenceText.isNotBlank() || it.citation.isNotBlank() || !it.pmid.isNullOrBlank() }
        val sectionReferences = cleanedSections.flatMap { it.references }

        return chapter.copy(
            chapterName = chapter.chapterName.ifBlank { fallbackName },
            chapterType = chapter.chapterType.ifBlank { chapterTypeFor(fallbackName) },
            sections = cleanedSections,
            tables = chapter.tables.mapNotNull { table ->
                val normalized = normalizeThesisTable(table)
                if (normalized.title.isNotBlank() || normalized.headers.isNotEmpty() || normalized.rows.isNotEmpty() || normalized.data.isNotEmpty()) normalized else null
            },
            figures = chapter.figures.filter { it.title.isNotBlank() || it.caption.isNotBlank() || it.imageSearchQuery.isNotBlank() },
            charts = chapter.charts.filter { it.title.isNotBlank() || it.datasets.isNotEmpty() || it.labels.isNotEmpty() || it.values.isNotEmpty() },
            abbreviations = chapter.abbreviations.filter { it.shortForm.isNotBlank() || it.fullForm.isNotBlank() },
            chapterReferences = (cleanedTopReferences + sectionReferences)
                .distinctBy { ref ->
                    referenceIdentity(ref) ?: canonicalReferenceTextKey(ref.referenceText)
                }
        )
    }

    private fun collectChapterFigures(chapter: ThesisChapterJson): List<FigureJson> {
        return (chapter.figures + chapter.sections.flatMap { it.figures })
            .filter { it.title.isNotBlank() || it.caption.isNotBlank() || it.imageSearchQuery.isNotBlank() }
            .distinctBy { figure ->
                listOf(figure.figureNumber, figure.title, figure.imageSearchQuery)
                    .joinToString("|")
                    .lowercase()
            }
            .mapIndexed { index, figure ->
                figure.copy(figureNumber = figure.figureNumber.ifBlank { (index + 1).toString() })
            }
    }

    private fun collectChapterReferences(chapter: ThesisChapterJson): List<ReferenceJson> {
        return (chapter.chapterReferences + chapter.sections.flatMap { it.references })
            .filter { it.referenceText.isNotBlank() || it.citation.isNotBlank() || !it.pmid.isNullOrBlank() }
            .distinctBy { ref ->
                referenceIdentity(ref) ?: canonicalReferenceTextKey(ref.referenceText)
            }
    }

    private fun parseChapterFromRawJson(rawJson: String, fallbackName: String): ThesisChapterJson? {
        if (rawJson.isBlank()) return null
        return runCatching {
            parseThesisChapterJson(rawJson, fallbackName)
        }.getOrElse {
            runCatching {
                val cleaned = extractJsonBlock(rawJson)
                val refs = gson.fromJson(cleaned, ReferencesJson::class.java)
                val chapterRefs = refs.references.mapIndexedNotNull { index, entry ->
                    val text = entry.text.completeCitationText(entry.pmid, entry.doi)
                    if (text.isBlank() && entry.pmid.isNullOrBlank()) return@mapIndexedNotNull null
                    ReferenceJson(
                        citation = serializedCitation(entry.number.takeIf { it > 0 } ?: index + 1),
                        referenceText = text,
                        pmid = entry.pmid,
                        doi = entry.doi,
                        pubmedVerified = !entry.pmid.isNullOrBlank()
                    )
                }
                ThesisChapterJson(
                    chapterName = fallbackName,
                    chapterReferences = chapterRefs
                )
            }.getOrNull()
        }
    }

    private fun serializedCitation(number: Int): String = "[$number]"

    private fun referenceIdentity(reference: ReferenceJson): String? {
        return referenceIdentities(reference).firstOrNull()
    }

    private fun referenceIdentities(reference: ReferenceJson): List<String> {
        val identities = mutableListOf<String>()
        reference.pmid
            ?.takeIf { it.isNotBlank() }
            ?.let { identities += "pmid:${it.trim()}" }
        reference.doi
            ?.takeIf { it.isNotBlank() }
            ?.let { identities += "doi:${it.trim().lowercase()}" }
        normalizeReferenceText(reference.referenceText)
            .takeIf { it.isNotBlank() }
            ?.let { identities += "text:$it" }
        canonicalReferenceTextKey(reference.referenceText)
            .takeIf { it.isNotBlank() }
            ?.let { identities += "canonical-text:$it" }

        findCachedVerifiedReference(reference, stripReferenceMetadata(reference.referenceText))
            ?.pmid
            ?.trim()
            ?.takeIf { it.isNotBlank() }
            ?.let { identities += "pmid:$it" }

        return identities.distinct()
    }

    private fun referenceNumber(reference: ReferenceJson): Int? {
        return citationNumber(reference.citation)
            ?: reference.pmid
                ?.trim()
                ?.takeIf { it.isNotBlank() }
                ?.toIntOrNull()
    }

    private fun nextReferenceSequence(references: List<ReferenceJson>): Int {
        val maxNumber = references
            .mapNotNull(::referenceNumber)
            .maxOrNull()
            ?: references.size
        return (maxNumber + 1).coerceAtLeast(1)
    }

    private fun currentReferenceSequence(): Int {
        val ledger = currentReferenceLedgerReferences()
        return maxOf(_uiState.value.referenceSequenceCounter, nextReferenceSequence(ledger))
    }

    private fun citationNumber(citation: String): Int? {
        return Regex("""\d+""").find(citation)?.value?.toIntOrNull()
    }

    private fun rewriteInlineCitations(text: String, oldToNew: Map<Int, Int>): String {
        if (text.isBlank() || oldToNew.isEmpty()) return text
        return text.replace(Regex("""\[(\d+)]""")) { match ->
            val oldNumber = match.groupValues.getOrNull(1)?.toIntOrNull()
            val newNumber = oldNumber?.let { oldToNew[it] }
            if (newNumber != null) serializedCitation(newNumber) else match.value
        }
    }

    private fun inlineCitationNumbers(text: String): List<Int> {
        return Regex("""\[(\d+)]""")
            .findAll(text)
            .mapNotNull { it.groupValues.getOrNull(1)?.toIntOrNull() }
            .toList()
    }

    private fun inlineCitationNumbers(chapter: ThesisChapterJson): List<Int> {
        val numbers = mutableListOf<Int>()
        chapter.sections.forEach { section ->
            section.content?.let { numbers += inlineCitationNumbers(it) }
            section.paragraphs.forEach { numbers += inlineCitationNumbers(it) }
            section.bullets.forEach { numbers += inlineCitationNumbers(it) }
            section.numberedPoints.forEach { numbers += inlineCitationNumbers(it) }
            section.subsections.forEach { sub ->
                numbers += inlineCitationNumbers(sub.heading)
                numbers += inlineCitationNumbers(sub.content)
            }
            section.table?.rows.orEmpty().flatten().forEach { numbers += inlineCitationNumbers(it) }
        }
        return numbers.distinct()
    }

    private fun inferInlineCitationMap(
        rawChapter: ThesisChapterJson?,
        renderedContent: String,
        serializedRefs: List<ReferenceJson>
    ): Map<Int, Int> {
        val inlineNumbers = (
            rawChapter?.let(::inlineCitationNumbers).orEmpty() +
                inlineCitationNumbers(renderedContent)
            )
            .distinct()
        if (inlineNumbers.isEmpty() || serializedRefs.isEmpty()) return emptyMap()

        return inlineNumbers
            .zip(serializedRefs)
            .mapNotNull { (oldNumber, reference) ->
                citationNumber(reference.citation)?.let { newNumber -> oldNumber to newNumber }
            }
            .toMap()
    }

    private fun serializeReferenceList(
        references: List<ReferenceJson>,
        globalReferenceNumbers: Map<String, Int>
    ): Pair<List<ReferenceJson>, Map<Int, Int>> {
        val oldToNew = mutableMapOf<Int, Int>()
        val serialized = references.mapIndexedNotNull { index, ref ->
            val newNumber = referenceIdentities(ref)
                .firstNotNullOfOrNull { identity -> globalReferenceNumbers[identity] }
                ?: return@mapIndexedNotNull null
            oldToNew[index + 1] = newNumber
            citationNumber(ref.citation)?.let { oldToNew[it] = newNumber }
            ref.copy(citation = serializedCitation(newNumber))
        }.distinctBy { it.citation }

        return serialized to oldToNew
    }

    private fun serializeChapterCitations(
        chapter: Chapter,
        globalReferenceNumbers: Map<String, Int>
    ): Chapter {
        if (globalReferenceNumbers.isEmpty()) return chapter

        val rawChapter = runCatching {
            if (chapter.rawJson.isNotBlank()) parseThesisChapterJson(chapter.rawJson, chapter.name) else null
        }.getOrNull()
        val effectiveReferences = (
            chapter.chapterReferences +
                rawChapter?.let(::collectChapterReferences).orEmpty()
            )
            .filter { it.referenceText.isNotBlank() || it.citation.isNotBlank() || !it.pmid.isNullOrBlank() }
            .distinctBy { ref ->
                referenceIdentity(ref) ?: canonicalReferenceTextKey(ref.referenceText)
            }
        if (effectiveReferences.isEmpty()) return chapter

        val (serializedRefs, oldToNew) = serializeReferenceList(effectiveReferences, globalReferenceNumbers)
        if (serializedRefs.isEmpty()) return chapter.copy(chapterReferences = emptyList())
        val finalOldToNew = oldToNew + inferInlineCitationMap(rawChapter, chapter.content, serializedRefs)

        val serializedRawJson = runCatching {
            if (rawChapter == null) {
                chapter.rawJson
            } else {
                val serializedChapter = serializeThesisChapterCitations(rawChapter, globalReferenceNumbers, finalOldToNew)
                gson.toJson(serializedChapter)
            }
        }.getOrDefault(chapter.rawJson)

        return chapter.copy(
            content = rewriteInlineCitations(chapter.content, finalOldToNew),
            rawJson = serializedRawJson,
            chapterReferences = serializedRefs
        )
    }

    private fun serializeThesisChapterCitations(
        chapter: ThesisChapterJson,
        globalReferenceNumbers: Map<String, Int>,
        inheritedOldToNew: Map<Int, Int>
    ): ThesisChapterJson {
        val (serializedChapterRefs, chapterOldToNew) = serializeReferenceList(
            collectChapterReferences(chapter),
            globalReferenceNumbers
        )
        val oldToNew = inheritedOldToNew + chapterOldToNew

        val serializedSections = chapter.sections.map { section ->
            val (sectionRefs, sectionOldToNew) = serializeReferenceList(section.references, globalReferenceNumbers)
            val sectionMap = oldToNew + sectionOldToNew
            section.copy(
                content = section.content?.let { rewriteInlineCitations(it, sectionMap) },
                paragraphs = section.paragraphs.map { rewriteInlineCitations(it, sectionMap) },
                bullets = section.bullets.map { rewriteInlineCitations(it, sectionMap) },
                numberedPoints = section.numberedPoints.map { rewriteInlineCitations(it, sectionMap) },
                subsections = section.subsections.map { sub ->
                    sub.copy(
                        heading = rewriteInlineCitations(sub.heading, sectionMap),
                        content = rewriteInlineCitations(sub.content, sectionMap)
                    )
                },
                references = sectionRefs
            )
        }

        return chapter.copy(
            sections = serializedSections,
            chapterReferences = serializedChapterRefs
        )
    }

    private fun buildReferencesContent(title: String, references: List<ReferenceJson>): String {
        return buildString {
            appendLine(title)
            references.forEachIndexed { index, ref ->
                appendLine("${serializedCitation(index + 1)} ${ref.completeCitationText()}")
            }
        }.trim()
    }

    private fun parseChapterJson(text: String): ThesisChapterJson {
        return parseThesisChapterJson(text)
    }

    private fun fallbackParsedChapterValue(chapterName: String, rawJson: String): Any? {
        val visibleText = extractVisibleText(rawJson)
        return when (chapterName.lowercase()) {
            "title" -> TitlePageJson(title = chapterName.uppercase())
            "certificate" -> CertificateJson(body = visibleText.ifBlank { "CERTIFICATE" })
            "declaration" -> DeclarationJson(statement = visibleText.ifBlank { "I hereby declare..." })
            "acknowledgements" -> AcknowledgementsJson(
                acknowledgements = listOfNotNull(visibleText.takeIf { it.isNotBlank() })
            )
            "abstract" -> AbstractJson(results = visibleText)
            "keywords" -> KeywordsJson(keywords = visibleText.split(Regex("[,\\n]")).map { it.trim() }.filter { it.isNotBlank() }.takeIf { it.isNotEmpty() }.orEmpty())
            "hypothesis" -> HypothesisJson(nullHypothesis = visibleText, alternateHypothesis = visibleText)
            "results", "observations" -> parseResultsFromRawJson(rawJson)
                ?: ResultsJson(
                    sections = listOf(
                        ResultSection(
                            heading = "Results",
                            content = visibleText.ifBlank { "Results not available in structured form." }
                        )
                    )
                )
            "references", "bibliography" -> ReferencesJson()
            "appendices" -> AppendicesJson()
            "proforma" -> ProformaJson()
            "patient consent form (english)", "patient consent form (hindi)" -> ConsentFormJson(title = chapterName.uppercase())
            else -> parseThesisChapterJson(rawJson, chapterName)
        }
    }

    private fun extractVisibleText(rawJson: String): String {
        val cleaned = extractJsonBlock(rawJson)
        val jsonElement = runCatching { JsonParser.parseString(cleaned) }.getOrNull()
            ?: return cleaned.trim()
        val jsonObject = jsonElement.takeIf { it.isJsonObject }?.asJsonObject
            ?: return if (jsonElement.isJsonPrimitive) {
                runCatching { jsonElement.asString.trim() }.getOrDefault(cleaned.trim())
            } else {
                ""
            }

        val preferredKeys = listOf(
            "content",
            "body",
            "text",
            "introduction",
            "background",
            "aim",
            "methods",
            "results",
            "conclusion",
            "discussion",
            "summary",
            "recommendations",
            "limitations",
            "future_scope",
            "future scope"
        )

        val values = preferredKeys.mapNotNull { key ->
            jsonObject.get(key)?.takeIf { it.isJsonPrimitive }?.asString?.trim()
        }.filter { it.isNotBlank() }

        if (values.isNotEmpty()) return values.joinToString("\n\n")

        fun collectText(element: com.google.gson.JsonElement?): List<String> {
            if (element == null || element.isJsonNull) return emptyList()
            return when {
                element.isJsonPrimitive -> {
                    val value = runCatching { element.asString }.getOrNull()?.trim().orEmpty()
                    if (value.isNotBlank() && value != "...") listOf(value) else emptyList()
                }
                element.isJsonArray -> element.asJsonArray.flatMap { collectText(it) }
                element.isJsonObject -> element.asJsonObject.entrySet().flatMap { (key, value) ->
                    val normalizedKey = key.lowercase()
                    if (normalizedKey in setOf("chapter_name", "chapter_type", "title", "date", "page", "number")) {
                        emptyList()
                    } else {
                        collectText(value)
                    }
                }
                else -> emptyList()
            }
        }

        return collectText(jsonObject)
            .filter { !isWeakChapterContent(it) }
            .distinct()
            .joinToString("\n\n")
    }

    private fun formatMethodologyPreview(m: MethodologyJson): String {
        return buildString {
            appendLine("MATERIALS AND METHODS")
            appendLine("\n1. Study Design: ${m.designType}")
            if (m.settings.isNotEmpty()) {
                appendLine("\n2. Settings:")
                m.settings.forEach { (key, value) ->
                    appendLine("   - $key: $value")
                }
            }
            if (m.inclusionCriteria.isNotEmpty()) {
                appendLine("\n3. Inclusion Criteria:")
                m.inclusionCriteria.forEach { appendLine("   - $it") }
            }
            if (m.exclusionCriteria.isNotEmpty()) {
                appendLine("\n4. Exclusion Criteria:")
                m.exclusionCriteria.forEach { appendLine("   - $it") }
            }
            val ss = m.sampleSize
            if (ss.calculatedSize > 0 || ss.formula.isNotBlank()) {
                appendLine("\n5. Sample Size:")
                if (ss.formula.isNotBlank()) appendLine("   - Formula: ${ss.formula}")
                if (ss.assumptions.isNotBlank()) appendLine("   - Assumptions: ${ss.assumptions}")
                appendLine("   - Power: ${ss.power}, CI: ${ss.confidenceInterval}")
                appendLine("   - Calculated Sample Size: ${ss.calculatedSize}")
            }
            if (m.statisticalAnalysis.isNotEmpty()) {
                appendLine("\n6. Statistical Analysis:")
                m.statisticalAnalysis.forEach { appendLine("   - $it") }
            }
        }
    }

    private fun formatDiscussionPreview(d: DiscussionJson): String {
        return buildString {
            appendLine("DISCUSSION")
            appendLine("\n1. Key Findings:\n${d.keyFindings}")
            if (d.comparisonWithLiterature.isNotEmpty()) {
                appendLine("\n2. Comparison with Literature:")
                d.comparisonWithLiterature.forEach { comp ->
                    appendLine("   - Finding: ${comp.finding}")
                    appendLine("     Reference: ${comp.citationReference}")
                    appendLine("     Comparison: ${comp.comparison}")
                }
            }
            if (d.limitations.isNotEmpty()) {
                appendLine("\n3. Limitations:")
                d.limitations.forEach { appendLine("   - $it") }
            }
            if (d.clinicalImplications.isNotBlank()) {
                appendLine("\n4. Clinical Implications:\n${d.clinicalImplications}")
            }
            if (d.futureDirections.isNotEmpty()) {
                appendLine("\n5. Future Directions:")
                d.futureDirections.forEach { appendLine("   - $it") }
            }
        }
    }

    private fun convertStructuredPayloadToSections(chapterName: String, parsedValue: Any): List<ThesisSectionJson> {
        return when (parsedValue) {
            is HypothesisJson -> listOf(
                ThesisSectionJson(heading = "Null Hypothesis", paragraphs = listOf(parsedValue.nullHypothesis)),
                ThesisSectionJson(heading = "Alternate Hypothesis", paragraphs = listOf(parsedValue.alternateHypothesis))
            )
            is MethodologyJson -> listOf(
                ThesisSectionJson(heading = "Study Design", paragraphs = listOf(parsedValue.designType)),
                ThesisSectionJson(heading = "Settings", paragraphs = parsedValue.settings.map { "${it.key}: ${it.value}" }),
                ThesisSectionJson(heading = "Inclusion Criteria", paragraphs = parsedValue.inclusionCriteria),
                ThesisSectionJson(heading = "Exclusion Criteria", paragraphs = parsedValue.exclusionCriteria),
                ThesisSectionJson(heading = "Sample Size", paragraphs = listOf(
                    "Formula: ${parsedValue.sampleSize.formula}",
                    "Assumptions: ${parsedValue.sampleSize.assumptions}",
                    "Power: ${parsedValue.sampleSize.power}, CI: ${parsedValue.sampleSize.confidenceInterval}",
                    "Calculated Size: ${parsedValue.sampleSize.calculatedSize}"
                ).filter { it.isNotBlank() }),
                ThesisSectionJson(heading = "Statistical Analysis", paragraphs = parsedValue.statisticalAnalysis)
            )
            is DiscussionJson -> listOf(
                ThesisSectionJson(heading = "Key Findings", paragraphs = listOf(parsedValue.keyFindings)),
                ThesisSectionJson(heading = "Comparison with Literature", paragraphs = parsedValue.comparisonWithLiterature.map { 
                    "Finding: ${it.finding}\nReference: ${it.citationReference}\nComparison: ${it.comparison}" 
                }),
                ThesisSectionJson(heading = "Limitations", paragraphs = parsedValue.limitations),
                ThesisSectionJson(heading = "Clinical Implications", paragraphs = listOf(parsedValue.clinicalImplications).filter { it.isNotBlank() }),
                ThesisSectionJson(heading = "Future Directions", paragraphs = parsedValue.futureDirections)
            )
            is ResultsJson -> parsedValue.sections.map { sec ->
                ThesisSectionJson(
                    heading = sec.heading,
                    paragraphs = listOf(sec.content) + (sec.observations?.map { "• $it" } ?: emptyList())
                )
            }
            is ProformaJson -> listOf(
                ThesisSectionJson(heading = "Patient Proforma", paragraphs = listOf(
                    "Patient Name: ${parsedValue.patientName}",
                    "Age: ${parsedValue.age}, Sex: ${parsedValue.sex}",
                    "OPD/IP No: ${parsedValue.opdIpNo}",
                    "Address: ${parsedValue.address}",
                    "History: ${parsedValue.history}",
                    "Examination: ${parsedValue.examination}",
                    "Investigations: ${parsedValue.investigations}",
                    "Diagnosis: ${parsedValue.diagnosis}"
                ))
            )
            is ConsentFormJson -> listOf(
                ThesisSectionJson(heading = parsedValue.title.ifBlank { "Consent Form" }, paragraphs = listOf(
                    "Introduction: ${parsedValue.introduction}",
                    "Procedure: ${parsedValue.procedure}",
                    "Risks: ${parsedValue.risks}",
                    "Benefits: ${parsedValue.benefits}",
                    "Confidentiality: ${parsedValue.confidentiality}",
                    "Signature: ${parsedValue.signatureLine}",
                    "Date: ${parsedValue.date}"
                ).filter { it.isNotBlank() })
            )
            is TitlePageJson -> listOf(
                ThesisSectionJson(heading = "Title Page Details", paragraphs = listOf(
                    "Title: ${parsedValue.title}",
                    "Subtitle: ${parsedValue.subtitle.orEmpty()}",
                    "Author: ${parsedValue.author}",
                    "Guide: ${parsedValue.guide}",
                    "Co-Guide: ${parsedValue.coGuide.orEmpty()}",
                    "Institution: ${parsedValue.institution}",
                    "Department: ${parsedValue.department}",
                    "Degree: ${parsedValue.degree}",
                    "Year: ${parsedValue.year}"
                ).filter { it.isNotBlank() })
            )
            is AbstractJson -> listOf(
                ThesisSectionJson(heading = "Background", paragraphs = listOf(parsedValue.background)),
                ThesisSectionJson(heading = "Aim", paragraphs = listOf(parsedValue.aim)),
                ThesisSectionJson(heading = "Methods", paragraphs = listOf(parsedValue.methods)),
                ThesisSectionJson(heading = "Results", paragraphs = listOf(parsedValue.results)),
                ThesisSectionJson(heading = "Conclusion", paragraphs = listOf(parsedValue.conclusion)),
                ThesisSectionJson(heading = "Keywords", paragraphs = listOf(parsedValue.keywords.joinToString(", ")))
            )
            is CertificateJson -> listOf(
                ThesisSectionJson(heading = "Certificate", paragraphs = listOf(parsedValue.body)),
                ThesisSectionJson(heading = "Signatures", paragraphs = listOf("Guide: ${parsedValue.guideSignature}", "HOD: ${parsedValue.hodSignature}", "Date: ${parsedValue.date}"))
            )
            is DeclarationJson -> listOf(
                ThesisSectionJson(heading = "Declaration", paragraphs = listOf(parsedValue.statement)),
                ThesisSectionJson(heading = "Signature", paragraphs = listOf("Student: ${parsedValue.studentName}", "Signature: ${parsedValue.signature}", "Date: ${parsedValue.date}"))
            )
            is AcknowledgementsJson -> listOf(
                ThesisSectionJson(heading = "Acknowledgements", paragraphs = parsedValue.acknowledgements)
            )
            is AppendicesJson -> parsedValue.appendices.map { app ->
                ThesisSectionJson(heading = app.title, paragraphs = listOf(app.content))
            }
            else -> emptyList()
        }
    }

    private fun formatChapterPreview(chapter: ThesisChapterJson): String {
        val out = StringBuilder()

        if (chapter.chapterName.isNotBlank()) {
            out.appendLine(chapter.chapterName.uppercase())
            out.appendLine()
        }

        chapter.sections.forEach { section ->
            if (section.heading.isNotBlank()) out.appendLine(section.heading)

            section.content?.takeIf { it.isNotBlank() }?.let {
                out.appendLine(it)
            }

            section.paragraphs.forEach { paragraph ->
                if (paragraph.isNotBlank()) out.appendLine(paragraph)
            }

            section.bullets.forEach { bullet ->
                out.appendLine("• $bullet")
            }

            section.numberedPoints.forEachIndexed { index, item ->
                out.appendLine("${index + 1}. $item")
            }

            section.subsections.forEach { sub ->
                if (sub.heading.isNotBlank()) out.appendLine(sub.heading)
                if (sub.content.isNotBlank()) out.appendLine(sub.content)
            }

            section.table?.let { table ->
                out.appendLine(table.title)
                out.appendLine(table.headers.joinToString(" | "))
                table.rows.forEach { row ->
                    out.appendLine(row.joinToString(" | "))
                }
            }

            out.appendLine()
        }

        if (chapter.tables.isNotEmpty()) {
            out.appendLine("TABLES")
            chapter.tables.forEach { table ->
                out.appendLine(table.title)
                if (table.headers.isNotEmpty()) {
                    out.appendLine(table.headers.joinToString(" | "))
                }
                table.rows.forEach { row ->
                    out.appendLine(row.joinToString(" | "))
                }
                out.appendLine()
            }
        }

        if (chapter.figures.isNotEmpty()) {
            out.appendLine("FIGURES")
            chapter.figures.forEach { figure ->
                out.appendLine("${figure.figureNumber}: ${figure.title}")
                out.appendLine("Query: ${figure.imageSearchQuery}")
                if (figure.imageUrl.isNotBlank()) out.appendLine("Image URL: ${figure.imageUrl}")
                if (figure.sourceUrl.isNotBlank()) out.appendLine("Source URL: ${figure.sourceUrl}")
                out.appendLine(figure.caption)
                out.appendLine()
            }
        }

        val sectionTables = chapter.sections.mapNotNull { it.table }
        if (sectionTables.isNotEmpty()) {
            out.appendLine("TABLES")
            sectionTables.forEach { table ->
                out.appendLine("${table.tableNumber}: ${table.title}")
            }
            out.appendLine()
        }

        if (chapter.charts.isNotEmpty()) {
            out.appendLine("CHARTS")
            chapter.charts.forEach { chart ->
                out.appendLine("${chart.chartId}: ${chart.title} (${chart.type})")
            }
            out.appendLine()
        }

        if (chapter.abbreviations.isNotEmpty()) {
            out.appendLine("ABBREVIATIONS")
            chapter.abbreviations.forEach {
                out.appendLine("${it.shortForm} = ${it.fullForm}")
            }
            out.appendLine()
        }

        return out.toString().trim()
    }

    fun retryAllFailed() {
        val failedNames = _uiState.value.chapters
            .filter { it.status == Chapter.ChapterStatus.ERROR }
            .map { it.name }
            .toSet()
        if (failedNames.isEmpty()) return

        _uiState.update { state ->
            val updated = state.chapters.map { ch ->
                if (ch.name in failedNames) {
                    val entry = AuditEntry(
                        action = "Retried (Bulk Failed)",
                        provider = state.selectedProvider,
                        notes = "Retried from bulk failed action"
                    )
                    ch.copy(
                        status = if (state.vpsAutoCompleteEnabled) Chapter.ChapterStatus.PENDING else Chapter.ChapterStatus.LOADING,
                        errorMessage = null,
                        lastWorkerError = "",
                        workerStatus = if (state.vpsAutoCompleteEnabled) "queued" else "",
                        auditTrail = ch.auditTrail + entry
                    )
                } else ch
            }
            state.copy(
                chapters = updated,
                hasErrors = updated.any { it.status == Chapter.ChapterStatus.ERROR },
                completionPercent = computeCompletionPercent(updated),
                status = "Clearing errors and retrying failed..."
            )
        }
        saveSessionToFirebase(immediate = true)

        viewModelScope.launch {
            val appContext = EduLabsApplication.instance.applicationContext
            startBackgroundWork(appContext, "Retrying failed thesis chapters")
            try {
                if (_uiState.value.vpsAutoCompleteEnabled) {
                    queuePendingChaptersForVps(failedNames)
                    _uiState.update {
                        it.copy(
                            processing = false,
                            status = "Queued failed chapters for VPS auto-complete"
                        )
                    }
                    saveSessionToFirebase()
                    return@launch
                }
                _uiState.update { it.copy(processing = true, status = "Retrying failed chapters...") }
                val failed = _uiState.value.chapters.filter { it.name in failedNames }
                failed.forEach { retryChapter(it) }
                _uiState.update {
                    it.copy(
                        processing = false,
                        hasErrors = _uiState.value.chapters.any { ch -> ch.status == Chapter.ChapterStatus.ERROR },
                        completionPercent = computeCompletionPercent(_uiState.value.chapters),
                        activeChapterName = ""
                    )
                }
                saveSessionToFirebase()
            } finally {
                stopBackgroundWork(appContext)
            }
        }
    }

    fun retrySelected(chapterNames: Set<String>) {
        if (chapterNames.isEmpty()) return

        _uiState.update { state ->
            val updated = state.chapters.map { ch ->
                if (ch.name in chapterNames) {
                    val entry = AuditEntry(
                        action = "Retried (Selected)",
                        provider = state.selectedProvider,
                        notes = "Retried from bulk selected action"
                    )
                    ch.copy(
                        status = if (state.vpsAutoCompleteEnabled) Chapter.ChapterStatus.PENDING else Chapter.ChapterStatus.LOADING,
                        errorMessage = null,
                        lastWorkerError = "",
                        workerStatus = if (state.vpsAutoCompleteEnabled) "queued" else "",
                        auditTrail = ch.auditTrail + entry
                    )
                } else ch
            }
            state.copy(
                chapters = updated,
                hasErrors = updated.any { it.status == Chapter.ChapterStatus.ERROR },
                completionPercent = computeCompletionPercent(updated),
                status = "Clearing errors and retrying selected..."
            )
        }
        saveSessionToFirebase(immediate = true)

        viewModelScope.launch {
            val appContext = EduLabsApplication.instance.applicationContext
            startBackgroundWork(appContext, "Retrying selected thesis chapters")
            try {
                if (_uiState.value.vpsAutoCompleteEnabled) {
                    queuePendingChaptersForVps(chapterNames)
                    _uiState.update {
                        it.copy(
                            processing = false,
                            status = "Queued selected chapters for VPS auto-complete"
                        )
                    }
                    saveSessionToFirebase()
                    return@launch
                }
                _uiState.update { it.copy(processing = true, status = "Retrying selected chapters...") }
                val selected = _uiState.value.chapters.filter { it.name in chapterNames }
                selected.forEach { retryChapter(it) }
                _uiState.update {
                    it.copy(
                        processing = false,
                        hasErrors = _uiState.value.chapters.any { ch -> ch.status == Chapter.ChapterStatus.ERROR },
                        completionPercent = computeCompletionPercent(_uiState.value.chapters),
                        activeChapterName = ""
                    )
                }
                saveSessionToFirebase()
            } finally {
                stopBackgroundWork(appContext)
            }
        }
    }

    fun retryAllIncomplete() {
        val incompleteNames = _uiState.value.chapters
            .filter { it.status == Chapter.ChapterStatus.ERROR || it.status == Chapter.ChapterStatus.IDLE || it.status == Chapter.ChapterStatus.PENDING }
            .map { it.name }
            .toSet()
        if (incompleteNames.isEmpty()) return

        _uiState.update { state ->
            val updated = state.chapters.map { ch ->
                if (ch.name in incompleteNames) {
                    val entry = AuditEntry(
                        action = "Retried (All Incomplete)",
                        provider = state.selectedProvider,
                        notes = "Retried all incomplete chapters"
                    )
                    ch.copy(
                        status = if (state.vpsAutoCompleteEnabled) Chapter.ChapterStatus.PENDING else Chapter.ChapterStatus.LOADING,
                        errorMessage = null,
                        lastWorkerError = "",
                        workerStatus = if (state.vpsAutoCompleteEnabled) "queued" else "",
                        auditTrail = ch.auditTrail + entry
                    )
                } else ch
            }
            state.copy(
                chapters = updated,
                hasErrors = updated.any { it.status == Chapter.ChapterStatus.ERROR },
                completionPercent = computeCompletionPercent(updated),
                status = "Clearing errors and retrying incomplete..."
            )
        }
        saveSessionToFirebase(immediate = true)

        viewModelScope.launch {
            val appContext = EduLabsApplication.instance.applicationContext
            startBackgroundWork(appContext, "Retrying incomplete thesis chapters")
            try {
                if (_uiState.value.vpsAutoCompleteEnabled) {
                    queuePendingChaptersForVps(incompleteNames)
                    _uiState.update {
                        it.copy(
                            processing = false,
                            status = "Queued incomplete chapters for VPS auto-complete"
                        )
                    }
                    saveSessionToFirebase()
                    return@launch
                }
                _uiState.update { it.copy(processing = true, status = "Retrying incomplete chapters...") }
                val incomplete = _uiState.value.chapters.filter { it.name in incompleteNames }
                incomplete.forEach { retryChapter(it) }
                _uiState.update {
                    it.copy(
                        processing = false,
                        hasErrors = _uiState.value.chapters.any { ch -> ch.status == Chapter.ChapterStatus.ERROR },
                        completionPercent = computeCompletionPercent(_uiState.value.chapters),
                        activeChapterName = ""
                    )
                }
                saveSessionToFirebase()
            } finally {
                stopBackgroundWork(appContext)
            }
        }
    }

    fun retryChapter(chapter: Chapter, customPrompt: String? = null) {
        viewModelScope.launch {
            val appContext = EduLabsApplication.instance.applicationContext
            startBackgroundWork(appContext, "Retrying thesis chapter")
            val chapterName = chapter.name

            if (_uiState.value.vpsAutoCompleteEnabled && chapterName.lowercase() !in autoGeneratedChapterNames) {
                _uiState.update { state ->
                    val updated = state.chapters.map { ch ->
                        if (ch.name == chapterName) {
                            val entry = AuditEntry(
                                action = "Retried",
                                provider = state.selectedProvider,
                                notes = customPrompt ?: "Queued for VPS worker"
                            )
                            ch.copy(
                                status = Chapter.ChapterStatus.PENDING,
                                errorMessage = null,
                                lastWorkerError = "",
                                workerStatus = "queued",
                                auditTrail = ch.auditTrail + entry
                            )
                        } else ch
                    }
                    state.copy(chapters = updated)
                }
                queuePendingChaptersForVps(
                    targetChapterNames = setOf(chapterName),
                    customPrompts = customPrompt?.takeIf { it.isNotBlank() }
                        ?.let { mapOf(chapterName to it) }
                        .orEmpty()
                )
                _uiState.update {
                    it.copy(
                        processing = false,
                        hasErrors = it.chapters.any { ch -> ch.status == Chapter.ChapterStatus.ERROR },
                        completionPercent = computeCompletionPercent(it.chapters),
                        activeChapterName = "",
                        status = "Queued $chapterName for VPS auto-complete"
                    )
                }
                saveSessionToFirebase()
                stopBackgroundWork(appContext)
                return@launch
            }

            try {
                val initialIndex = _uiState.value.chapters.indexOfFirst { it.name == chapterName }
                if (initialIndex < 0) return@launch

                _uiState.update { state ->
                    val index = state.chapters.indexOfFirst { it.name == chapterName }
                    if (index < 0) {
                        return@update state.copy(
                            processing = false,
                            status = "Retry target no longer exists"
                        )
                    }

                    val updated = state.chapters.toMutableList()
                    val previewVariables = getVariablesForChapter(chapterName, state.variables)
                    val entry = AuditEntry(
                        action = "Retried",
                        provider = state.selectedProvider,
                        notes = customPrompt ?: "Local generation started"
                    )
                    updated[index] = updated[index].copy(
                        status = Chapter.ChapterStatus.LOADING,
                        errorMessage = null,
                        lastWorkerError = "",
                        workerStatus = "",
                        auditTrail = updated[index].auditTrail + entry,
                        content = if (updated[index].content.isBlank()) {
                            chapterWritingPreview(chapterName, 1, previewVariables)
                        } else {
                            updated[index].content
                        }
                    )
                    state.copy(
                        chapters = updated,
                        processing = true,
                        status = "Retrying $chapterName...",
                        activeChapterName = chapterName
                    )
                }

                if (chapterName.equals("Literature Review", ignoreCase = true)) {
                    val retryTarget = _uiState.value.chapters.firstOrNull { it.name == chapterName }?.copy()
                        ?: return@launch
                    saveChapterVersion(chapterName, chapter.content, chapter.rawJson)
                    var attempt = 0
                    var success = false
                    while (!success && attempt < maxChapterGenerationAttempts) {
                        attempt += 1
                        success = runCatching { generateLiteratureReviewChapter(retryTarget, customPrompt) }
                            .onFailure {
                                retryTarget.status = Chapter.ChapterStatus.ERROR
                                retryTarget.errorMessage = "AI SERVER BUSY"
                            }
                            .isSuccess
                        if (!success) {
                            _uiState.update { state ->
                                val index = state.chapters.indexOfFirst { it.name == chapterName }
                                if (index < 0) return@update state
                                val updated = state.chapters.toMutableList()
                                updated[index] = updated[index].copy(
                                    status = Chapter.ChapterStatus.LOADING,
                                    errorMessage = null
                                )
                                state.copy(
                                    chapters = updated,
                                    processing = true,
                                    status = "Retrying $chapterName after attempt $attempt",
                                    activeChapterName = chapterName
                                )
                            }
                            saveSessionToFirebase()
                            delay((1500L * attempt).coerceAtMost(10_000L))
                        }
                    }
                    retryTarget.textBoxes = ensureChapterTextBoxes(retryTarget)

                    _uiState.update { state ->
                        val index = state.chapters.indexOfFirst { it.name == chapterName }
                        if (index < 0) {
                            return@update state.copy(
                                processing = false,
                                status = "Retry target no longer exists"
                            )
                        }

                        val updated = state.chapters.toMutableList()
                        updated[index] = retryTarget
                        state.copy(
                            chapters = updated,
                            processing = false,
                            status = if (success) "Retry successful" else "AI SERVER BUSY",
                            hasErrors = updated.any { it.status == Chapter.ChapterStatus.ERROR },
                            completionPercent = computeCompletionPercent(updated),
                            activeChapterName = ""
                        )
                    }
                    if (success) {
                        updateVariable("Previous Chapter: $chapterName", retryTarget.content)
                    }
                    saveSessionToFirebase()
                    return@launch
                }

                val schema = chapterSchemas[chapterName.lowercase()]
                val prompt = customPrompt ?: buildRetryPrompt(
                    chapterName,
                    getVariablesForChapter(chapterName, _uiState.value.variables)
                )

                var success = false
                var finalContent = ""
                var lastError: String? = null
                var finalParsed: Any? = null
                var finalCharts: List<ChartJson> = emptyList()

                var attempt = 0
                    while (!success && attempt < maxChapterGenerationAttempts) {
                    attempt += 1
                    try {
                        _uiState.update {
                            it.copy(status = "Retrying $chapterName (attempt $attempt)")
                        }

                        val rawText = callAiJsonWithContinuation(prompt, chapterName)
                        val parsed = parseGeneratedChapterValue(chapterName, rawText, schema)
                            ?: throw IllegalStateException("Parser returned null")

                        finalParsed = parsed
                        finalCharts = when (parsed) {
                            is ThesisChapterJson -> sanitizeChartsForUse(parsed.charts, chapterName)
                            else -> emptyList()
                        }
                        finalContent = when (parsed) {
                            is ThesisChapterJson -> formatChapterPreview(parsed)
                            is HypothesisJson -> buildString {
                                appendLine("HYPOTHESIS")
                                appendLine("Null: ${parsed.nullHypothesis}")
                                appendLine("Alternate: ${parsed.alternateHypothesis}")
                            }.trim()
                            else -> schema?.formatter?.invoke(parsed).orEmpty()
                        }
                        showParsedChapterWritingDraft(chapterName, finalContent, rawText)

                        saveChapterVersion(
                            chapterName,
                            chapter.content,
                            chapter.rawJson
                        )

                        success = true
                    } catch (e: Throwable) {
                        val msg = e.message ?: e.toString()
                        lastError = msg
                        delay(if (isSkipToNextModelError(msg)) 500 else 2000)
                    }
                }

                val parsedResult = finalParsed
                val retryReferences = if (success && parsedResult != null) {
                    when (parsedResult) {
                        is ThesisChapterJson -> runCatching { requirePubMedVerifiedReferences(collectChapterReferences(parsedResult), chapterName) }
                            .getOrDefault(emptyList())
                        else -> emptyList()
                    }
                } else {
                    emptyList()
                }

                _uiState.update { state ->
                    val index = state.chapters.indexOfFirst { it.name == chapterName }
                    if (index < 0) {
                        return@update state.copy(
                            processing = false,
                            status = "Retry target no longer exists"
                        )
                    }

                    val updated = state.chapters.toMutableList()
                    val currentChapter = updated[index]

                    updated[index] = if (success && parsedResult != null) {
                        val updatedFigures = when (parsedResult) {
                            is ThesisChapterJson -> collectChapterFigures(parsedResult)
                            else -> emptyList()
                        }
                        val updatedAbbreviations = when (parsedResult) {
                            is ThesisChapterJson -> parsedResult.abbreviations
                            else -> emptyList()
                        }
                        val updatedSections = when {
                            parsedResult is ThesisChapterJson -> parsedResult.sections
                            else -> convertStructuredPayloadToSections(chapterName, parsedResult)
                        }
                        val updatedChapter = currentChapter.copy(
                            content = finalContent,
                            rawJson = gson.toJson(parsedResult),
                            figures = updatedFigures,
                            charts = finalCharts,
                            abbreviations = updatedAbbreviations,
                            chapterReferences = retryReferences,
                            sections = updatedSections,
                            status = Chapter.ChapterStatus.SUCCESS,
                            errorMessage = null
                        )
                        updatedChapter.copy(textBoxes = ensureChapterTextBoxes(updatedChapter))
                    } else {
                        currentChapter.copy(
                            status = Chapter.ChapterStatus.ERROR,
                            errorMessage = lastError ?: "AI SERVER BUSY"
                        )
                    }

                    state.copy(
                        chapters = updated,
                        processing = false,
                        status = if (success) "Retry successful" else "AI SERVER BUSY",
                        hasErrors = updated.any { it.status == Chapter.ChapterStatus.ERROR },
                        completionPercent = computeCompletionPercent(updated),
                        activeChapterName = ""
                    )
                }

                if (success && parsedResult != null) {
                    mergeReferencesIntoGlobalVariable(retryReferences, verifyNewReferences = false)
                    updateVariable("Previous Chapter: $chapterName", finalContent)
                    saveSessionToFirebase()
                }
            } finally {
                stopBackgroundWork(appContext)
            }
        }
    }

    fun exportAllChaptersToUri(context: Context, uri: Uri) {
        reindexAllCitations()
        viewModelScope.launch(Dispatchers.IO) {
            val appContext = context.applicationContext
            startBackgroundWork(appContext, "Exporting thesis PDF")
            var pdfToClose: PDDocument? = null
            var logoBitmap: Bitmap? = null
            try {
                _uiState.update {
                    it.copy(
                        processing = true,
                        status = "Starting PDF export...",
                        progressCurrent = 0,
                        progressTotal = 1
                    )
                }
                val pdf = PDDocument().also { pdfToClose = it }
                val pageSize = PDRectangle.A4
                val exportSettings = _uiState.value
                val pdfThemeStyle = resolvePdfThemeStyle(exportSettings.pdfTheme).withExportOverrides(
                    margin = exportSettings.exportMargin,
                    font = exportSettings.exportFont,
                    logoPlacement = exportSettings.exportLogoPlacement,
                    headerFooterEnabled = exportSettings.exportHeaderFooter
                )
                val margin = pdfThemeStyle.exportMarginPoints()
                val lineSpacingMultiplier = exportLineSpacingMultiplier(exportSettings.exportLineSpacing)
                var yCoord = 0f
                var pageCounter = 0
                var currentSectionLabel = "THESIS"
                logoBitmap = loadCollegeLogoBitmap(context, exportSettings.collegeLogoUri)
                lateinit var contentStream: PDPageContentStream
                var contentStreamOpen = false

                fun closeContentStream() {
                    if (contentStreamOpen) {
                        contentStream.close()
                        contentStreamOpen = false
                    }
                }

                fun setStrokeColor(cs: PDPageContentStream, color: Int) {
                    cs.setStrokingColor(
                        Color.red(color) / 255f,
                        Color.green(color) / 255f,
                        Color.blue(color) / 255f
                    )
                }

                fun setFillColor(cs: PDPageContentStream, color: Int) {
                    cs.setNonStrokingColor(
                        Color.red(color) / 255f,
                        Color.green(color) / 255f,
                        Color.blue(color) / 255f
                    )
                }

                fun drawPageChrome(cs: PDPageContentStream, sectionLabel: String) {
                    val outerLeft = margin - 12f
                    val outerBottom = margin - 12f
                    val outerWidth = pageSize.width - (outerLeft * 2f)
                    val outerHeight = pageSize.height - (outerBottom * 2f)
                    val innerLeft = outerLeft + 10f
                    val innerBottom = outerBottom + 10f
                    val innerWidth = outerWidth - 20f
                    val innerHeight = outerHeight - 20f
                    val headerTop = pageSize.height - margin - 22f
                    val headerBottom = headerTop - 40f
                    val contentTop = headerBottom - 42f
                    val contentBottom = margin + 56f

                    setFillColor(cs, Color.parseColor("#FFFFFF"))
                    cs.addRect(0f, 0f, pageSize.width, pageSize.height)
                    cs.fill()

                    if (!exportSettings.exportHeaderFooter) {
                        yCoord = pageSize.height - margin - 32f
                        contentStream = cs
                    }

                    when (pdfThemeStyle.pageChromeLayout) {
                        PageChromeLayout.FORMAL_FRAME -> {
                            setStrokeColor(cs, pdfThemeStyle.accentColor)
                            cs.setLineWidth(1.3f)
                            cs.addRect(outerLeft, outerBottom, outerWidth, outerHeight)
                            cs.stroke()

                            setStrokeColor(cs, pdfThemeStyle.ruleColor)
                            cs.setLineWidth(0.7f)
                            cs.addRect(innerLeft, innerBottom, innerWidth, innerHeight)
                            cs.stroke()

                            setFillColor(cs, pdfThemeStyle.headerFillColor)
                            cs.addRect(margin, headerBottom, pageSize.width - (margin * 2f), 24f)
                            cs.fill()

                            setFillColor(cs, pdfThemeStyle.softColor)
                            cs.addRect(margin, contentTop, pageSize.width - (margin * 2f), 12f)
                            cs.fill()

                            setStrokeColor(cs, pdfThemeStyle.accentColor)
                            cs.setLineWidth(2.2f)
                            cs.moveTo(margin, contentTop)
                            cs.lineTo(pageSize.width - margin, contentTop)
                            cs.stroke()
                        }
                        PageChromeLayout.CLINICAL_REPORT -> {
                            setFillColor(cs, pdfThemeStyle.footerFillColor)
                            cs.addRect(0f, pageSize.height - 92f, pageSize.width, 92f)
                            cs.fill()
                            setFillColor(cs, pdfThemeStyle.accentColor)
                            cs.addRect(0f, 0f, 16f, pageSize.height)
                            cs.fill()
                            setStrokeColor(cs, pdfThemeStyle.ruleColor)
                            cs.setLineWidth(1.1f)
                            cs.moveTo(margin, contentTop + 8f)
                            cs.lineTo(pageSize.width - margin, contentTop + 8f)
                            cs.stroke()
                            setFillColor(cs, pdfThemeStyle.softColor)
                            cs.addRect(margin, contentTop - 10f, 96f, 6f)
                            cs.fill()
                        }
                        PageChromeLayout.JOURNAL_ARTICLE -> {
                            setStrokeColor(cs, pdfThemeStyle.ruleColor)
                            cs.setLineWidth(0.8f)
                            cs.moveTo(margin, pageSize.height - margin - 18f)
                            cs.lineTo(pageSize.width - margin, pageSize.height - margin - 18f)
                            cs.stroke()
                            cs.moveTo(margin, margin + 32f)
                            cs.lineTo(pageSize.width - margin, margin + 32f)
                            cs.stroke()
                        }
                        PageChromeLayout.PREMIUM_PRESENTATION -> {
                            setFillColor(cs, pdfThemeStyle.accentColor)
                            cs.addRect(0f, pageSize.height - 118f, pageSize.width, 118f)
                            cs.fill()
                            setFillColor(cs, pdfThemeStyle.softColor)
                            cs.addRect(pageSize.width - 150f, pageSize.height - 118f, 150f, 118f)
                            cs.fill()
                            setFillColor(cs, pdfThemeStyle.headerFillColor)
                            cs.addRect(margin, contentTop - 4f, pageSize.width - (margin * 2f), 10f)
                            cs.fill()
                        }
                        PageChromeLayout.OFFICIAL_BINDER -> {
                            setFillColor(cs, pdfThemeStyle.headerFillColor)
                            cs.addRect(0f, pageSize.height - 82f, pageSize.width, 82f)
                            cs.fill()
                            setFillColor(cs, pdfThemeStyle.footerFillColor)
                            cs.addRect(0f, 0f, pageSize.width, 42f)
                            cs.fill()
                            setFillColor(cs, pdfThemeStyle.accentColor)
                            cs.addRect(0f, 0f, 22f, pageSize.height)
                            cs.fill()
                            setStrokeColor(cs, pdfThemeStyle.accentColor)
                            cs.setLineWidth(1.5f)
                            cs.addRect(margin - 4f, margin - 4f, pageSize.width - (margin * 2f) + 8f, pageSize.height - (margin * 2f) + 8f)
                            cs.stroke()
                        }
                        PageChromeLayout.MINIMAL_JOURNAL -> {
                            setStrokeColor(cs, pdfThemeStyle.ruleColor)
                            cs.setLineWidth(0.55f)
                            cs.moveTo(margin, pageSize.height - margin - 26f)
                            cs.lineTo(pageSize.width - margin, pageSize.height - margin - 26f)
                            cs.stroke()
                            cs.moveTo(margin, margin + 36f)
                            cs.lineTo(pageSize.width - margin, margin + 36f)
                            cs.stroke()
                            setFillColor(cs, pdfThemeStyle.softColor)
                            cs.addRect(margin, pageSize.height - margin - 54f, 96f, 5f)
                            cs.fill()
                        }
                        PageChromeLayout.ACADEMIC_INSET -> {
                            setFillColor(cs, pdfThemeStyle.softColor)
                            cs.addRect(margin - 18f, margin - 18f, pageSize.width - (margin * 2f) + 36f, pageSize.height - (margin * 2f) + 36f)
                            cs.fill()
                            setFillColor(cs, Color.WHITE)
                            cs.addRect(margin - 4f, margin - 4f, pageSize.width - (margin * 2f) + 8f, pageSize.height - (margin * 2f) + 8f)
                            cs.fill()
                            setStrokeColor(cs, pdfThemeStyle.accentColor)
                            cs.setLineWidth(1.1f)
                            cs.addRect(margin - 4f, margin - 4f, pageSize.width - (margin * 2f) + 8f, pageSize.height - (margin * 2f) + 8f)
                            cs.stroke()
                            setFillColor(cs, pdfThemeStyle.headerFillColor)
                            cs.addRect(margin, contentTop - 8f, pageSize.width - (margin * 2f), 8f)
                            cs.fill()
                        }
                        PageChromeLayout.DASHBOARD_RAIL -> {
                            setFillColor(cs, pdfThemeStyle.accentColor)
                            cs.addRect(0f, 0f, 68f, pageSize.height)
                            cs.fill()
                            setFillColor(cs, pdfThemeStyle.footerFillColor)
                            cs.addRect(68f, pageSize.height - 96f, pageSize.width - 68f, 96f)
                            cs.fill()
                            setFillColor(cs, pdfThemeStyle.headerFillColor)
                            cs.addRect(margin + 28f, contentTop - 4f, pageSize.width - margin - 78f, 10f)
                            cs.fill()
                            setStrokeColor(cs, pdfThemeStyle.ruleColor)
                            cs.setLineWidth(0.8f)
                            cs.addRect(margin + 18f, margin + 42f, pageSize.width - margin - 86f, pageSize.height - (margin * 2f) - 70f)
                            cs.stroke()
                        }
                        PageChromeLayout.DEFENSE_PRESENTATION -> {
                            setFillColor(cs, pdfThemeStyle.accentColor)
                            cs.addRect(0f, pageSize.height - 128f, pageSize.width, 128f)
                            cs.fill()
                            setFillColor(cs, pdfThemeStyle.footerFillColor)
                            cs.addRect(pageSize.width - 132f, 0f, 132f, pageSize.height)
                            cs.fill()
                            setFillColor(cs, pdfThemeStyle.headerFillColor)
                            cs.addRect(margin, contentTop - 2f, pageSize.width - margin - 154f, 12f)
                            cs.fill()
                            setStrokeColor(cs, pdfThemeStyle.ruleColor)
                            cs.setLineWidth(1f)
                            cs.moveTo(margin, margin + 42f)
                            cs.lineTo(pageSize.width - 154f, margin + 42f)
                            cs.stroke()
                        }
                        PageChromeLayout.EDITORIAL_FOLIO -> {
                            setFillColor(cs, pdfThemeStyle.footerFillColor)
                            cs.addRect(0f, 0f, pageSize.width, pageSize.height)
                            cs.fill()
                            setFillColor(cs, Color.WHITE)
                            cs.addRect(margin - 6f, margin - 6f, pageSize.width - (margin * 2f) + 12f, pageSize.height - (margin * 2f) + 12f)
                            cs.fill()
                            setFillColor(cs, pdfThemeStyle.accentColor)
                            cs.addRect(margin, pageSize.height - margin - 78f, pageSize.width - (margin * 2f), 5f)
                            cs.fill()
                            setStrokeColor(cs, pdfThemeStyle.ruleColor)
                            cs.setLineWidth(0.7f)
                            cs.moveTo(margin, margin + 44f)
                            cs.lineTo(pageSize.width - margin, margin + 44f)
                            cs.stroke()
                        }
                        PageChromeLayout.ATLAS_PLATE -> {
                            setFillColor(cs, Color.WHITE)
                            cs.addRect(0f, 0f, pageSize.width, pageSize.height)
                            cs.fill()
                            setFillColor(cs, pdfThemeStyle.accentColor)
                            cs.addRect(0f, pageSize.height - 96f, pageSize.width, 96f)
                            cs.fill()
                            setFillColor(cs, pdfThemeStyle.footerFillColor)
                            cs.addRect(margin, contentTop - 12f, pageSize.width - (margin * 2f), 18f)
                            cs.fill()
                            setStrokeColor(cs, pdfThemeStyle.ruleColor)
                            cs.setLineWidth(1.2f)
                            cs.addRect(margin, margin + 42f, pageSize.width - (margin * 2f), pageSize.height - (margin * 2f) - 92f)
                            cs.stroke()
                        }
                        PageChromeLayout.EXECUTIVE_SUMMARY -> {
                            setFillColor(cs, pdfThemeStyle.accentColor)
                            cs.addRect(0f, pageSize.height - 92f, pageSize.width, 92f)
                            cs.fill()
                            setFillColor(cs, pdfThemeStyle.footerFillColor)
                            cs.addRect(0f, 0f, pageSize.width, 44f)
                            cs.fill()
                            setFillColor(cs, pdfThemeStyle.headerFillColor)
                            cs.addRect(margin, contentTop - 8f, pageSize.width - (margin * 2f), 14f)
                            cs.fill()
                            setStrokeColor(cs, pdfThemeStyle.ruleColor)
                            cs.setLineWidth(0.8f)
                            cs.moveTo(margin, contentTop - 20f)
                            cs.lineTo(pageSize.width - margin, contentTop - 20f)
                            cs.stroke()
                        }
                        PageChromeLayout.MONOGRAPH_CLASSIC -> {
                            setStrokeColor(cs, pdfThemeStyle.accentColor)
                            cs.setLineWidth(2f)
                            cs.addRect(margin - 16f, margin - 16f, pageSize.width - (margin * 2f) + 32f, pageSize.height - (margin * 2f) + 32f)
                            cs.stroke()
                            setStrokeColor(cs, pdfThemeStyle.ruleColor)
                            cs.setLineWidth(0.6f)
                            cs.addRect(margin - 6f, margin - 6f, pageSize.width - (margin * 2f) + 12f, pageSize.height - (margin * 2f) + 12f)
                            cs.stroke()
                            setFillColor(cs, pdfThemeStyle.softColor)
                            cs.addRect(margin, pageSize.height - margin - 76f, pageSize.width - (margin * 2f), 9f)
                            cs.fill()
                        }
                        PageChromeLayout.CASEBOOK_FILE -> {
                            setFillColor(cs, pdfThemeStyle.footerFillColor)
                            cs.addRect(0f, 0f, pageSize.width, pageSize.height)
                            cs.fill()
                            setFillColor(cs, Color.WHITE)
                            cs.addRect(margin - 2f, margin - 4f, pageSize.width - (margin * 2f) + 4f, pageSize.height - (margin * 2f) + 8f)
                            cs.fill()
                            setFillColor(cs, pdfThemeStyle.accentColor)
                            cs.addRect(0f, pageSize.height - 78f, pageSize.width, 78f)
                            cs.fill()
                            setFillColor(cs, pdfThemeStyle.headerFillColor)
                            cs.addRect(pageSize.width - margin - 92f, pageSize.height - 108f, 92f, 30f)
                            cs.fill()
                            setStrokeColor(cs, pdfThemeStyle.ruleColor)
                            cs.setLineWidth(0.9f)
                            cs.moveTo(margin, contentTop + 2f)
                            cs.lineTo(pageSize.width - margin, contentTop + 2f)
                            cs.stroke()
                        }
                        PageChromeLayout.LAB_NOTEBOOK -> {
                            setFillColor(cs, Color.WHITE)
                            cs.addRect(0f, 0f, pageSize.width, pageSize.height)
                            cs.fill()
                            setStrokeColor(cs, pdfThemeStyle.softColor)
                            cs.setLineWidth(0.35f)
                            var gridX = margin
                            while (gridX < pageSize.width - margin) {
                                cs.moveTo(gridX, margin + 42f)
                                cs.lineTo(gridX, pageSize.height - margin - 58f)
                                gridX += 24f
                            }
                            var gridY = margin + 48f
                            while (gridY < pageSize.height - margin - 58f) {
                                cs.moveTo(margin, gridY)
                                cs.lineTo(pageSize.width - margin, gridY)
                                gridY += 24f
                            }
                            cs.stroke()
                            setFillColor(cs, pdfThemeStyle.accentColor)
                            cs.addRect(margin, pageSize.height - margin - 62f, pageSize.width - (margin * 2f), 34f)
                            cs.fill()
                            setFillColor(cs, pdfThemeStyle.headerFillColor)
                            cs.addRect(margin, contentTop - 10f, 130f, 12f)
                            cs.fill()
                        }
                        PageChromeLayout.SYSTEMATIC_REVIEW -> {
                            setFillColor(cs, Color.WHITE)
                            cs.addRect(0f, 0f, pageSize.width, pageSize.height)
                            cs.fill()
                            setStrokeColor(cs, pdfThemeStyle.ruleColor)
                            cs.setLineWidth(0.7f)
                            cs.moveTo(margin, pageSize.height - margin - 22f)
                            cs.lineTo(pageSize.width - margin, pageSize.height - margin - 22f)
                            cs.stroke()
                            cs.moveTo(pageSize.width / 2f, margin + 50f)
                            cs.lineTo(pageSize.width / 2f, pageSize.height - margin - 84f)
                            cs.stroke()
                            setFillColor(cs, pdfThemeStyle.softColor)
                            cs.addRect(margin, contentTop - 8f, pageSize.width - (margin * 2f), 12f)
                            cs.fill()
                            setFillColor(cs, pdfThemeStyle.accentColor)
                            cs.addRect(margin, contentTop + 10f, 82f, 5f)
                            cs.fill()
                        }
                        PageChromeLayout.SIGNATURE_PORTFOLIO -> {
                            setFillColor(cs, pdfThemeStyle.footerFillColor)
                            cs.addRect(0f, 0f, pageSize.width, pageSize.height)
                            cs.fill()
                            setFillColor(cs, Color.WHITE)
                            cs.addRect(margin - 8f, margin + 18f, pageSize.width - (margin * 2f) + 16f, pageSize.height - (margin * 2f) - 20f)
                            cs.fill()
                            setFillColor(cs, pdfThemeStyle.accentColor)
                            cs.addRect(margin - 8f, pageSize.height - margin - 112f, 34f, 112f)
                            cs.fill()
                            setFillColor(cs, pdfThemeStyle.headerFillColor)
                            cs.addRect(margin + 44f, pageSize.height - margin - 76f, pageSize.width - (margin * 2f) - 88f, 10f)
                            cs.fill()
                            setStrokeColor(cs, pdfThemeStyle.ruleColor)
                            cs.setLineWidth(1f)
                            cs.addRect(margin - 8f, margin + 18f, pageSize.width - (margin * 2f) + 16f, pageSize.height - (margin * 2f) - 20f)
                            cs.stroke()
                        }
                    }

                    if (sectionLabel.isNotBlank()) {
                        contentStream = cs
                        if (exportSettings.exportHeaderFooter) {
                            when (pdfThemeStyle.headerFooterLayout) {
                                HeaderFooterLayout.PLAIN_PAGE_NUMBER -> {
                                    setFillColor(cs, pdfThemeStyle.accentColor)
                                    cs.addRect(margin + 4f, headerBottom - 2f, 170f, 28f)
                                    cs.fill()
                                    cs.setNonStrokingColor(1f, 1f, 1f)
                                    drawCenteredText(cs, sectionLabel.uppercase(), pdfThemeStyle.sectionFont(), 13f, 2f * (margin + 4f) + 170f, headerBottom + 7f)
                                }
                                HeaderFooterLayout.INSTITUTIONAL_HEADER -> {
                                    cs.beginText()
                                    cs.setFont(pdfThemeStyle.sectionFont(), 11.5f)
                                    cs.setNonStrokingColor(Color.red(pdfThemeStyle.accentColor) / 255f, Color.green(pdfThemeStyle.accentColor) / 255f, Color.blue(pdfThemeStyle.accentColor) / 255f)
                                    cs.newLineAtOffset(margin, pageSize.height - margin - 28f)
                                    cs.showText(sanitizePdfText(sectionLabel.uppercase()).take(58))
                                    cs.endText()
                                }
                                HeaderFooterLayout.JOURNAL_STYLE -> {
                                    cs.beginText()
                                    cs.setFont(pdfThemeStyle.sectionFont(), 10f)
                                    cs.setNonStrokingColor(Color.red(pdfThemeStyle.ruleColor) / 255f, Color.green(pdfThemeStyle.ruleColor) / 255f, Color.blue(pdfThemeStyle.ruleColor) / 255f)
                                    cs.newLineAtOffset(margin, pageSize.height - margin - 34f)
                                    cs.showText(sanitizePdfText(sectionLabel).take(64))
                                    cs.endText()
                                }
                                HeaderFooterLayout.MODERN_BAR -> {
                                    cs.setNonStrokingColor(1f, 1f, 1f)
                                    drawCenteredText(cs, sectionLabel.uppercase(), pdfThemeStyle.sectionFont(), 13.5f, pageSize.width, pageSize.height - 69f)
                                }
                            }
                        }
                        setStrokeColor(cs, pdfThemeStyle.accentColor)
                    }

                    logoBitmap?.let { logo ->
                        val logoSizePx = when (pdfThemeStyle.logoSize) {
                            "small" -> 40f
                            "medium" -> 58f
                            "large" -> 80f
                            "xlarge" -> 100f
                            else -> 58f
                        }
                        val ratio = minOf(logoSizePx / logo.width.toFloat(), logoSizePx / logo.height.toFloat())
                        val drawWidth = logo.width * ratio
                        val drawHeight = logo.height * ratio
                        val offsetX = pdfThemeStyle.logoOffsetX.toFloat()
                        val offsetY = pdfThemeStyle.logoOffsetY.toFloat()
                        val (logoX, logoY) = when (pdfThemeStyle.logoPosition) {
                            "top-left" -> Pair(margin + 8f + offsetX, pageSize.height - margin - drawHeight + offsetY)
                            "top-center" -> Pair((pageSize.width - drawWidth) / 2f + offsetX, pageSize.height - margin - drawHeight + offsetY)
                            "top-right" -> Pair(pageSize.width - margin - drawWidth + offsetX, headerBottom - 12f + offsetY)
                            "bottom-left" -> Pair(margin + 8f + offsetX, margin + 40f + offsetY)
                            "bottom-center" -> Pair((pageSize.width - drawWidth) / 2f + offsetX, margin + 40f + offsetY)
                            "bottom-right" -> Pair(pageSize.width - margin - drawWidth + offsetX, margin + 40f + offsetY)
                            else -> Pair(pageSize.width - margin - drawWidth, headerBottom - 12f) // none hidden, but render anyway as fallback
                        }
                        if (pdfThemeStyle.logoPosition != "none") {
                            val pdImage = LosslessFactory.createFromImage(pdf, logo)
                            cs.drawImage(pdImage, logoX, logoY, drawWidth, drawHeight)
                        }
                    }

                    if (exportSettings.exportHeaderFooter) {
                        when (pdfThemeStyle.headerFooterLayout) {
                            HeaderFooterLayout.PLAIN_PAGE_NUMBER,
                            HeaderFooterLayout.INSTITUTIONAL_HEADER -> {
                                cs.moveTo(margin + 8f, margin + 34f)
                                cs.lineTo(pageSize.width - margin - 8f, margin + 34f)
                                cs.stroke()
                                setFillColor(cs, pdfThemeStyle.footerFillColor)
                                cs.addRect(margin + 2f, margin + 10f, pageSize.width - (margin * 2f) - 4f, 18f)
                                cs.fill()
                            }
                            HeaderFooterLayout.JOURNAL_STYLE -> {
                                setStrokeColor(cs, pdfThemeStyle.ruleColor)
                                cs.setLineWidth(0.6f)
                                cs.moveTo(margin, margin + 34f)
                                cs.lineTo(pageSize.width - margin, margin + 34f)
                                cs.stroke()
                            }
                            HeaderFooterLayout.MODERN_BAR -> {
                                setFillColor(cs, pdfThemeStyle.accentColor)
                                cs.addRect(0f, 0f, pageSize.width, 34f)
                                cs.fill()
                            }
                        }
                    }

                    contentStream = cs
                    yCoord = when (pdfThemeStyle.pageChromeLayout) {
                        PageChromeLayout.PREMIUM_PRESENTATION -> contentTop - 8f
                        PageChromeLayout.JOURNAL_ARTICLE -> pageSize.height - margin - 58f
                        PageChromeLayout.CLINICAL_REPORT -> contentTop - 6f
                        PageChromeLayout.FORMAL_FRAME -> contentTop - 18f
                        PageChromeLayout.OFFICIAL_BINDER -> contentTop - 4f
                        PageChromeLayout.MINIMAL_JOURNAL -> pageSize.height - margin - 70f
                        PageChromeLayout.ACADEMIC_INSET -> contentTop - 12f
                        PageChromeLayout.DASHBOARD_RAIL -> contentTop - 10f
                        PageChromeLayout.DEFENSE_PRESENTATION -> contentTop - 6f
                        PageChromeLayout.EDITORIAL_FOLIO -> contentTop - 14f
                        PageChromeLayout.ATLAS_PLATE -> contentTop - 18f
                        PageChromeLayout.EXECUTIVE_SUMMARY -> contentTop - 28f
                        PageChromeLayout.MONOGRAPH_CLASSIC -> contentTop - 16f
                        PageChromeLayout.CASEBOOK_FILE -> contentTop - 12f
                        PageChromeLayout.LAB_NOTEBOOK -> contentTop - 18f
                        PageChromeLayout.SYSTEMATIC_REVIEW -> contentTop - 14f
                        PageChromeLayout.SIGNATURE_PORTFOLIO -> contentTop - 24f
                    }

                    if (exportSettings.exportWatermark) {
                        cs.beginText()
                        cs.setNonStrokingColor(0.82f, 0.82f, 0.82f)
                        cs.setFont(PDType1Font.HELVETICA_BOLD, 42f)
                        cs.newLineAtOffset(margin + 54f, pageSize.height / 2f)
                        cs.showText("THESIS DRAFT")
                        cs.endText()
                    }

                    val shouldDrawPageNumber = exportSettings.exportPageNumbering.lowercase() != "none"
                    if (shouldDrawPageNumber) {
                        cs.beginText()
                        if (pdfThemeStyle.headerFooterLayout == HeaderFooterLayout.MODERN_BAR && exportSettings.exportHeaderFooter) {
                            cs.setNonStrokingColor(1f, 1f, 1f)
                        } else {
                            cs.setNonStrokingColor(0f, 0f, 0f)
                        }
                        cs.setFont(PDType1Font.HELVETICA, 8.5f)
                        val pageNumY = if (pdfThemeStyle.headerFooterLayout == HeaderFooterLayout.MODERN_BAR && exportSettings.exportHeaderFooter) 13f else margin + 16f
                        val pageLabel = if (exportSettings.exportPageNumbering.equals("roman", true)) {
                            "Page ${romanNumeral(pageCounter)}"
                        } else {
                            "Page $pageCounter"
                        }
                        cs.newLineAtOffset(pageSize.width - margin - 58f, pageNumY)
                        cs.showText(pageLabel)
                        cs.endText()
                    }
                }

                fun newPage(sectionLabel: String = currentSectionLabel, decorate: Boolean = true): PDPageContentStream {
                    val page = PDPage(pageSize)
                    pdf.addPage(page)
                    val cs = PDPageContentStream(pdf, page)
                    contentStreamOpen = true
                    pageCounter += 1
                    currentSectionLabel = sectionLabel
                    if (decorate) {
                        drawPageChrome(cs, sectionLabel)
                    } else {
                        contentStream = cs
                        yCoord = pageSize.height - margin - 36f
                    }
                    return cs
                }

                fun ensureSpace(needed: Float) {
                    if (yCoord < margin + needed) {
                        closeContentStream()
                        contentStream = newPage()
                    }
                }

                fun contentWidth(): Float = pageSize.width - (margin * 2f)

                fun drawScaledCenteredBitmap(bitmap: Bitmap, maxWidth: Float, maxHeight: Float): Float {
                    val ratio = minOf(maxWidth / bitmap.width.toFloat(), maxHeight / bitmap.height.toFloat())
                    val drawWidth = bitmap.width * ratio
                    val drawHeight = bitmap.height * ratio
                    ensureSpace(drawHeight + 24f)
                    val pdImage = LosslessFactory.createFromImage(pdf, bitmap)
                    val drawX = margin + ((contentWidth() - drawWidth) / 2f)
                    contentStream.drawImage(pdImage, drawX, yCoord - drawHeight - 8f, drawWidth, drawHeight)
                    yCoord -= drawHeight + 18f
                    return drawHeight
                }

                fun normalizePdfParagraphText(text: String): String {
                    return text
                        .replace("\r\n", "\n")
                        .replace("\r", "\n")
                        .replace("\u03c3", "sigma")
                        .replace("\u03a3", "Sigma")
                        .lines()
                        .joinToString("\n") { line ->
                            line.filter { char -> runCatching { PDType1Font.HELVETICA.getStringWidth(char.toString()) }.isSuccess }
                        }
                }

                fun pdfFontForRun(baseFont: PDType1Font, runBold: Boolean): PDType1Font {
                    val themedBase = pdfThemeStyle.fontOverride(baseFont, bold = false)
                    return when {
                        !runBold -> themedBase
                        themedBase == PDType1Font.TIMES_ROMAN || themedBase == PDType1Font.TIMES_BOLD -> PDType1Font.TIMES_BOLD
                        themedBase == PDType1Font.COURIER || themedBase == PDType1Font.COURIER_BOLD -> PDType1Font.COURIER_BOLD
                        themedBase == PDType1Font.HELVETICA_OBLIQUE -> PDType1Font.HELVETICA_BOLD_OBLIQUE
                        themedBase == PDType1Font.HELVETICA_BOLD_OBLIQUE -> PDType1Font.HELVETICA_BOLD_OBLIQUE
                        themedBase == PDType1Font.HELVETICA_BOLD -> PDType1Font.HELVETICA_BOLD
                        else -> PDType1Font.HELVETICA_BOLD
                    }
                }

                fun pdfTextWidth(runs: List<ExportTextRun>, baseFont: PDType1Font, size: Float): Float {
                    return runs.sumOf { run ->
                        runCatching {
                            (pdfFontForRun(baseFont, run.bold).getStringWidth(run.text) / 1000f) * size
                        }.getOrElse { 0f }.toDouble()
                    }.toFloat()
                }

                data class FormattedToken(val text: String, val bold: Boolean, val isWhitespace: Boolean)

                fun wrapPdfMarkdownLine(line: String, baseFont: PDType1Font, size: Float, maxWidth: Float): List<List<ExportTextRun>> {
                    val tokens = mutableListOf<FormattedToken>()
                    parseBoldMarkdownRuns(line).forEach { run ->
                        var currentToken = StringBuilder()
                        var isTokenWhitespace = false
                        run.text.forEach { char ->
                            val charIsWhitespace = char.isWhitespace()
                            if (currentToken.isEmpty()) {
                                currentToken.append(char)
                                isTokenWhitespace = charIsWhitespace
                            } else {
                                val lastChar = currentToken.last()
                                val shouldSplit = (charIsWhitespace != isTokenWhitespace) ||
                                                  (lastChar == '-' || lastChar == '/' || lastChar == ',')
                                if (shouldSplit) {
                                    tokens.add(FormattedToken(currentToken.toString(), run.bold, isTokenWhitespace))
                                    currentToken = StringBuilder().append(char)
                                    isTokenWhitespace = charIsWhitespace
                                } else {
                                    currentToken.append(char)
                                }
                            }
                        }
                        if (currentToken.isNotEmpty()) {
                            tokens.add(FormattedToken(currentToken.toString(), run.bold, isTokenWhitespace))
                        }
                    }

                    val output = mutableListOf<List<ExportTextRun>>()
                    var currentLine = mutableListOf<ExportTextRun>()
                    var currentLineWidth = 0f

                    tokens.forEach { token ->
                        val tokenWidth = runCatching {
                            (pdfFontForRun(baseFont, token.bold).getStringWidth(token.text) / 1000f) * size
                        }.getOrElse { 0f }

                        if (currentLineWidth + tokenWidth > maxWidth) {
                            if (token.isWhitespace) {
                                return@forEach
                            }
                            if (currentLine.isNotEmpty()) {
                                output.add(currentLine.toList())
                                currentLine.clear()
                                currentLineWidth = 0f
                            }
                            if (tokenWidth > maxWidth) {
                                token.text.forEach { char ->
                                    val charText = char.toString()
                                    val charWidth = runCatching {
                                        (pdfFontForRun(baseFont, token.bold).getStringWidth(charText) / 1000f) * size
                                    }.getOrElse { 0f }
                                    if (currentLineWidth + charWidth > maxWidth && currentLine.isNotEmpty()) {
                                        output.add(currentLine.toList())
                                        currentLine.clear()
                                        currentLineWidth = 0f
                                    }
                                    appendExportRun(currentLine, charText, token.bold)
                                    currentLineWidth += charWidth
                                }
                            } else {
                                appendExportRun(currentLine, token.text, token.bold)
                                currentLineWidth += tokenWidth
                            }
                        } else {
                            if (token.isWhitespace && currentLine.isEmpty()) {
                                return@forEach
                            }
                            appendExportRun(currentLine, token.text, token.bold)
                            currentLineWidth += tokenWidth
                        }
                    }
                    if (currentLine.isNotEmpty()) {
                        output.add(currentLine.toList())
                    }
                    return output
                }

                fun writeText(
                    text: String,
                    font: PDType1Font,
                    size: Float,
                    align: String = "LEFT",
                    xOffset: Float = 0f,
                    color: Int = Color.BLACK
                ) {
                    val sanitized = normalizePdfParagraphText(text)
                    if (sanitized.isBlank()) return
                    val effectiveFont = pdfThemeStyle.fontOverride(font, bold = font in setOf(PDType1Font.HELVETICA_BOLD, PDType1Font.TIMES_BOLD, PDType1Font.COURIER_BOLD))
                    val safeXOffset = xOffset.coerceIn(0f, (contentWidth() - 32f).coerceAtLeast(0f))
                    val safeLineWidth = (contentWidth() - safeXOffset - 8f).coerceAtLeast(32f)
                    val lines = sanitized.lines().flatMap { line ->
                        wrapPdfMarkdownLine(line, effectiveFont, size, safeLineWidth)
                    }
                    for (lineRuns in lines) {
                        val leading = size * lineSpacingMultiplier
                        ensureSpace(leading + 3f)
                        val textWidth = pdfTextWidth(lineRuns, effectiveFont, size).coerceAtMost(safeLineWidth)
                        val x = when (align) {
                            "CENTER" -> (margin + safeXOffset + ((safeLineWidth - textWidth) / 2f)).coerceIn(margin, pageSize.width - margin - textWidth)
                            "RIGHT" -> pageSize.width - margin - textWidth
                            else -> margin + safeXOffset
                        }
                        contentStream.beginText()
                        contentStream.setNonStrokingColor(
                            Color.red(color) / 255f,
                            Color.green(color) / 255f,
                            Color.blue(color) / 255f
                        )
                        contentStream.setFont(effectiveFont, size)
                        contentStream.newLineAtOffset(x, yCoord)
                        lineRuns.forEach { run ->
                            contentStream.setFont(pdfFontForRun(effectiveFont, run.bold), size)
                            contentStream.showText(run.text)
                        }
                        contentStream.endText()
                        yCoord -= leading
                    }
                }

                fun writeBulletText(
                    bulletText: String,
                    font: PDType1Font,
                    size: Float,
                    xOffset: Float = 14f,
                    bulletIndent: Float = 12f,
                    color: Int = Color.BLACK
                ) {
                    val sanitized = normalizePdfParagraphText(bulletText)
                    if (sanitized.isBlank()) return
                    
                    val textXOffset = xOffset + bulletIndent
                    val safeXOffset = textXOffset.coerceIn(0f, (contentWidth() - 32f).coerceAtLeast(0f))
                    val safeLineWidth = (contentWidth() - safeXOffset - 8f).coerceAtLeast(32f)
                    val lines = sanitized.lines().flatMap { line ->
                        wrapPdfMarkdownLine(line, font, size, safeLineWidth)
                    }
                    
                    var isFirstLine = true
                    for (lineRuns in lines) {
                        val leading = size * 1.35f
                        ensureSpace(leading + 3f)
                        
                        if (isFirstLine) {
                            contentStream.beginText()
                            contentStream.setNonStrokingColor(
                                Color.red(color) / 255f,
                                Color.green(color) / 255f,
                                Color.blue(color) / 255f
                            )
                            contentStream.setFont(font, size)
                            contentStream.newLineAtOffset(margin + xOffset, yCoord)
                            contentStream.showText("• ")
                            contentStream.endText()
                            isFirstLine = false
                        }
                        
                        contentStream.beginText()
                        contentStream.setNonStrokingColor(
                            Color.red(color) / 255f,
                            Color.green(color) / 255f,
                            Color.blue(color) / 255f
                        )
                        contentStream.setFont(font, size)
                        contentStream.newLineAtOffset(margin + safeXOffset, yCoord)
                        lineRuns.forEach { run ->
                            contentStream.setFont(pdfFontForRun(font, run.bold), size)
                            contentStream.showText(run.text)
                        }
                        contentStream.endText()
                        yCoord -= leading
                    }
                }

                fun writeNumberedPointText(
                    index: Int,
                    pointText: String,
                    font: PDType1Font,
                    size: Float,
                    xOffset: Float = 14f,
                    numIndent: Float = 16f,
                    color: Int = Color.BLACK
                ) {
                    val sanitized = normalizePdfParagraphText(pointText)
                    if (sanitized.isBlank()) return
                    
                    val textXOffset = xOffset + numIndent
                    val safeXOffset = textXOffset.coerceIn(0f, (contentWidth() - 32f).coerceAtLeast(0f))
                    val safeLineWidth = (contentWidth() - safeXOffset - 8f).coerceAtLeast(32f)
                    val lines = sanitized.lines().flatMap { line ->
                        wrapPdfMarkdownLine(line, font, size, safeLineWidth)
                    }
                    
                    var isFirstLine = true
                    for (lineRuns in lines) {
                        val leading = size * 1.35f
                        ensureSpace(leading + 3f)
                        
                        if (isFirstLine) {
                            contentStream.beginText()
                            contentStream.setNonStrokingColor(
                                Color.red(color) / 255f,
                                Color.green(color) / 255f,
                                Color.blue(color) / 255f
                            )
                            contentStream.setFont(font, size)
                            contentStream.newLineAtOffset(margin + xOffset, yCoord)
                            contentStream.showText("${index + 1}. ")
                            contentStream.endText()
                            isFirstLine = false
                        }
                        
                        contentStream.beginText()
                        contentStream.setNonStrokingColor(
                            Color.red(color) / 255f,
                            Color.green(color) / 255f,
                            Color.blue(color) / 255f
                        )
                        contentStream.setFont(font, size)
                        contentStream.newLineAtOffset(margin + safeXOffset, yCoord)
                        lineRuns.forEach { run ->
                            contentStream.setFont(pdfFontForRun(font, run.bold), size)
                            contentStream.showText(run.text)
                        }
                        contentStream.endText()
                        yCoord -= leading
                    }
                }

                fun exportTextForChapter(chapter: Chapter): String {
                    val text = chapter.content.ifBlank { extractVisibleText(chapter.rawJson) }
                    return if (chapterTypeFor(chapter.name) == "REFERENCES") text else stripAppendedReferenceBlock(text)
                }

                fun drawCenteredText(
                    text: String,
                    font: PDType1Font,
                    size: Float,
                    y: Float,
                    color: Int = Color.BLACK
                ) {
                    val source = stripBoldMarkdown(normalizePdfParagraphText(text)).replace("\n", " ")
                    var sanitized = source
                    val maxTextWidth = contentWidth() - 8f
                    while (sanitized.length > 1 && (font.getStringWidth(sanitized) / 1000f) * size > maxTextWidth) {
                        sanitized = sanitized.dropLast(1)
                    }
                    if (sanitized.length < source.length && sanitized.length > 3) {
                        sanitized = sanitized.dropLast(3) + "..."
                    }
                    val width = (font.getStringWidth(sanitized) / 1000f) * size
                    contentStream.beginText()
                    contentStream.setNonStrokingColor(
                        Color.red(color) / 255f,
                        Color.green(color) / 255f,
                        Color.blue(color) / 255f
                    )
                    contentStream.setFont(font, size)
                    contentStream.newLineAtOffset((pageSize.width - width) / 2f, y)
                    contentStream.showText(sanitized)
                    contentStream.endText()
                }

                suspend fun renderFigureBlock(
                    figureNumber: String,
                    title: String,
                    caption: String,
                    imageSource: String,
                    searchQuery: String? = null
                ) {
                    val bitmap = loadFigureBitmap(context, imageSource, searchQuery)

                    ensureSpace(120f)
                    if (pdfThemeStyle.figureLayout == FigureLayout.REPORT_PANEL || pdfThemeStyle.figureLayout == FigureLayout.PRESENTATION_IMAGE) {
                        setFillColor(contentStream, pdfThemeStyle.footerFillColor)
                        contentStream.addRect(margin + 4f, yCoord - 88f, contentWidth() - 8f, 78f)
                        contentStream.fill()
                    }
                    writeText(
                        "Figure ${figureNumber.ifBlank { "?" }}: ${title.ifBlank { "Untitled figure" }}",
                        pdfThemeStyle.sectionFont(),
                        pdfThemeStyle.headingSize() - 3.8f,
                        xOffset = if (pdfThemeStyle.figureLayout == FigureLayout.JOURNAL_FIGURE) 0f else 8f,
                        color = if (pdfThemeStyle.figureLayout == FigureLayout.PRESENTATION_IMAGE) pdfThemeStyle.accentColor else Color.BLACK
                    )

                    bitmap?.let { bmp ->
                        drawScaledCenteredBitmap(bmp, contentWidth() - 24f, 250f)
                        bmp.recycle()
                    } ?: run {
                        ensureSpace(72f)
                        contentStream.setLineWidth(0.8f)
                        contentStream.addRect(margin + 8f, yCoord - 70f, pageSize.width - (margin * 2f) - 16f, 56f)
                        contentStream.stroke()
                        writeText("Image not available for export", pdfThemeStyle.bodyFont(), 9f, xOffset = 18f, color = pdfThemeStyle.ruleColor)
                        yCoord -= 24f
                    }

                    if (caption.isNotBlank()) {
                        writeText(caption, pdfThemeStyle.bodyFont(), 10f, xOffset = 12f)
                    }
                    if (searchQuery?.isNotBlank() == true) {
                        writeText("Search: $searchQuery", pdfThemeStyle.bodyFont(), 9f, xOffset = 12f)
                    }
                    yCoord -= 8f
                }

                suspend fun renderChartBlock(chart: ChartJson) {
                    val normalizedChart = normalizeResultChart(chart)
                    val chartBitmap = withContext(Dispatchers.Main) {
                        renderChartToBitmap(context, normalizedChart, pdfThemeStyle, widthPx = 900, heightPx = 560)
                    }
                    if (pdfThemeStyle.chartLayout == ChartLayout.PRESENTATION_BOLD) {
                        ensureSpace(28f)
                        setFillColor(contentStream, pdfThemeStyle.accentColor)
                        contentStream.addRect(margin, yCoord - 18f, contentWidth(), 18f)
                        contentStream.fill()
                        yCoord -= 24f
                    }
                    if (chartBitmap != null) {
                        drawScaledCenteredBitmap(chartBitmap, contentWidth() - 18f, 300f)
                        chartBitmap.recycle()
                    } else {
                        Log.e("ThesisExport", "Failed to render chart bitmap for: ${normalizedChart.title}")
                    }
                    ensureSpace(18f)
                    writeText(
                        "${normalizedChart.title} (${normalizedChart.type}${normalizedChart.chartTemplate.takeIf { it.isNotBlank() }?.let { ", $it" } ?: ""})",
                        pdfThemeStyle.sectionFont(),
                        10.5f,
                        xOffset = 8f
                    )
                    yCoord -= 8f
                }

                suspend fun renderStructuredSection(section: ThesisSectionJson, chapterName: String, resolvedFigures: List<FigureJson>) {
                    if (section.heading.isNotBlank() && !sameExportHeading(section.heading, chapterName)) {
                        ensureSpace(85f)
                        when (pdfThemeStyle.sectionLayout) {
                            SectionLayout.FORMAL_HEADING -> {
                                writeText(section.heading.uppercase(), pdfThemeStyle.sectionFont(), pdfThemeStyle.headingSize(), color = pdfThemeStyle.accentColor)
                                yCoord -= 12f
                            }
                            SectionLayout.BOXED_LABEL -> {
                                setFillColor(contentStream, pdfThemeStyle.softColor)
                                contentStream.addRect(margin, yCoord - 24f, contentWidth(), 28f)
                                contentStream.fill()
                                writeText(section.heading.uppercase(), pdfThemeStyle.sectionFont(), pdfThemeStyle.headingSize(), xOffset = 10f, color = pdfThemeStyle.accentColor)
                                yCoord -= 12f
                            }
                            SectionLayout.JOURNAL_HEADING -> {
                                writeText(section.heading, pdfThemeStyle.sectionFont(), pdfThemeStyle.headingSize(), color = Color.BLACK)
                                setStrokeColor(contentStream, pdfThemeStyle.ruleColor)
                                contentStream.setLineWidth(0.5f)
                                contentStream.moveTo(margin, yCoord + 7f)
                                contentStream.lineTo(margin + 180f, yCoord + 7f)
                                contentStream.stroke()
                                yCoord -= 14f
                            }
                            SectionLayout.DASHBOARD_BLOCK -> {
                                setFillColor(contentStream, pdfThemeStyle.accentColor)
                                contentStream.addRect(margin, yCoord - 24f, 8f, 34f)
                                contentStream.fill()
                                writeText(section.heading.uppercase(), pdfThemeStyle.sectionFont(), pdfThemeStyle.headingSize(), xOffset = 18f, color = pdfThemeStyle.accentColor)
                                yCoord -= 12f
                            }
                            SectionLayout.EDITORIAL_MARK -> {
                                setFillColor(contentStream, pdfThemeStyle.accentColor)
                                contentStream.addRect(margin, yCoord + 4f, 88f, 4f)
                                contentStream.fill()
                                writeText(section.heading, pdfThemeStyle.sectionFont(), pdfThemeStyle.headingSize() + 0.3f, color = Color.BLACK)
                                setStrokeColor(contentStream, pdfThemeStyle.ruleColor)
                                contentStream.setLineWidth(0.6f)
                                contentStream.moveTo(margin, yCoord + 7f)
                                contentStream.lineTo(pageSize.width - margin, yCoord + 4f)
                                contentStream.stroke()
                                yCoord -= 14f
                            }
                            SectionLayout.PLATE_LABEL -> {
                                setFillColor(contentStream, pdfThemeStyle.accentColor)
                                contentStream.addRect(margin, yCoord - 26f, contentWidth(), 32f)
                                contentStream.fill()
                                writeText(section.heading.uppercase(), pdfThemeStyle.sectionFont(), pdfThemeStyle.headingSize(), xOffset = 12f, color = Color.WHITE)
                                yCoord -= 14f
                            }
                            SectionLayout.EXECUTIVE_BAND -> {
                                setFillColor(contentStream, pdfThemeStyle.footerFillColor)
                                contentStream.addRect(margin, yCoord - 28f, contentWidth(), 36f)
                                contentStream.fill()
                                setFillColor(contentStream, pdfThemeStyle.accentColor)
                                contentStream.addRect(margin, yCoord - 28f, 6f, 36f)
                                contentStream.fill()
                                writeText(section.heading.uppercase(), pdfThemeStyle.sectionFont(), pdfThemeStyle.headingSize(), xOffset = 18f, color = pdfThemeStyle.accentColor)
                                yCoord -= 14f
                            }
                            SectionLayout.MONOGRAPH_DROP -> {
                                setStrokeColor(contentStream, pdfThemeStyle.accentColor)
                                contentStream.setLineWidth(1.2f)
                                contentStream.moveTo(margin, yCoord + 8f)
                                contentStream.lineTo(pageSize.width - margin, yCoord + 8f)
                                contentStream.stroke()
                                writeText(section.heading.uppercase(), pdfThemeStyle.sectionFont(), pdfThemeStyle.headingSize() + 0.2f, align = "CENTER", color = pdfThemeStyle.accentColor)
                                setStrokeColor(contentStream, pdfThemeStyle.ruleColor)
                                contentStream.setLineWidth(0.6f)
                                contentStream.moveTo(margin + 80f, yCoord + 6f)
                                contentStream.lineTo(pageSize.width - margin - 80f, yCoord + 6f)
                                contentStream.stroke()
                                yCoord -= 14f
                            }
                        }
                    }

                    section.content?.takeIf { it.isNotBlank() }?.let {
                        ensureSpace(28f)
                        val paragraphOffset = when (pdfThemeStyle.paragraphLayout) {
                            ParagraphLayout.INDENTED_ACADEMIC -> 18f
                            ParagraphLayout.COMPACT_REPORT -> 8f
                            ParagraphLayout.JOURNAL_BODY -> 0f
                            ParagraphLayout.SPACIOUS_READING -> 12f
                        }
                        val paragraphSize = when (pdfThemeStyle.paragraphLayout) {
                            ParagraphLayout.COMPACT_REPORT -> 10.5f
                            ParagraphLayout.SPACIOUS_READING -> 11.5f
                            else -> 11f
                        }
                        writeText(it, pdfThemeStyle.bodyFont(), paragraphSize, xOffset = paragraphOffset)
                        yCoord -= if (pdfThemeStyle.paragraphLayout == ParagraphLayout.SPACIOUS_READING) 10f else 6f
                    }

                    section.bullets.forEach { bullet ->
                        writeBulletText(bullet, pdfThemeStyle.bodyFont(), 10.5f, xOffset = 14f)
                    }

                    section.numberedPoints.forEachIndexed { index, point ->
                        writeNumberedPointText(index, point, pdfThemeStyle.bodyFont(), 10.5f, xOffset = 14f)
                    }

                    section.subsections.forEach { sub ->
                        if (sub.heading.isNotBlank()) {
                            ensureSpace(60f)
                            writeText(sub.heading, pdfThemeStyle.sectionFont(), 12.4f, xOffset = 10f, color = pdfThemeStyle.accentColor)
                        }
                        if (sub.content.isNotBlank()) {
                            ensureSpace(24f)
                            writeText(sub.content, pdfThemeStyle.bodyFont(), 10.5f, xOffset = 16f)
                        }
                    }

                    section.table?.let { table ->
                        val normalized = normalizeThesisTable(table)
                        ensureSpace(120f)
                        val newState = drawPdfTable(
                            pdf,
                            TableDrawingState(yCoord, contentStream),
                            normalized.headers,
                            normalized.rows,
                            normalized.footnote,
                            pageSize,
                            margin,
                            headerFillColor = pdfThemeStyle.headerFillColor,
                            accentColor = pdfThemeStyle.accentColor,
                            tableLayout = pdfThemeStyle.tableLayout,
                            ruleColor = pdfThemeStyle.ruleColor,
                            newPage = { newPage() }
                        )
                        yCoord = newState.y
                        contentStream = newState.contentStream ?: contentStream
                        yCoord -= 12f
                    }

                    section.figures.forEach { figure ->
                        val resolved = resolveExportFigure(figure, resolvedFigures)
                        val source = resolved.imageUrl.ifBlank { resolved.sourceUrl }
                        renderFigureBlock(
                            resolved.figureNumber,
                            resolved.title,
                            resolved.caption,
                            source,
                            resolved.imageSearchQuery
                        )
                    }
                }

                fun renderStructuredMethodology(m: MethodologyJson) {
                    ensureSpace(40f)
                    writeText("1. Study Design", pdfThemeStyle.sectionFont(), 12f, color = pdfThemeStyle.accentColor)
                    yCoord -= 4f
                    writeText(m.designType, pdfThemeStyle.bodyFont(), 10.5f, xOffset = 10f)
                    yCoord -= 8f

                    if (m.settings.isNotEmpty()) {
                        ensureSpace(40f)
                        writeText("2. Study Settings", pdfThemeStyle.sectionFont(), 12f, color = pdfThemeStyle.accentColor)
                        yCoord -= 4f
                        m.settings.forEach { (key, value) ->
                            writeText("$key: $value", pdfThemeStyle.bodyFont(), 10.5f, xOffset = 10f)
                        }
                        yCoord -= 8f
                    }

                    if (m.inclusionCriteria.isNotEmpty()) {
                        ensureSpace(40f)
                        writeText("3. Inclusion Criteria", pdfThemeStyle.sectionFont(), 12f, color = pdfThemeStyle.accentColor)
                        yCoord -= 4f
                        m.inclusionCriteria.forEach { criterion ->
                            writeBulletText(criterion, pdfThemeStyle.bodyFont(), 10.5f, xOffset = 10f)
                        }
                        yCoord -= 8f
                    }

                    if (m.exclusionCriteria.isNotEmpty()) {
                        ensureSpace(40f)
                        writeText("4. Exclusion Criteria", pdfThemeStyle.sectionFont(), 12f, color = pdfThemeStyle.accentColor)
                        yCoord -= 4f
                        m.exclusionCriteria.forEach { criterion ->
                            writeBulletText(criterion, pdfThemeStyle.bodyFont(), 10.5f, xOffset = 10f)
                        }
                        yCoord -= 8f
                    }

                    val ss = m.sampleSize
                    if (ss.calculatedSize > 0 || ss.formula.isNotBlank()) {
                        ensureSpace(60f)
                        writeText("5. Sample Size Calculation", pdfThemeStyle.sectionFont(), 12f, color = pdfThemeStyle.accentColor)
                        yCoord -= 4f
                        if (ss.formula.isNotBlank()) {
                            writeText("Formula: ${ss.formula}", pdfThemeStyle.bodyFont(), 10.5f, xOffset = 10f)
                        }
                        if (ss.assumptions.isNotBlank()) {
                            writeText("Assumptions: ${ss.assumptions}", pdfThemeStyle.bodyFont(), 10.5f, xOffset = 10f)
                        }
                        writeText("Statistical power: ${ss.power}, confidence level: ${ss.confidenceInterval}", pdfThemeStyle.bodyFont(), 10.5f, xOffset = 10f)
                        writeText("Calculated Sample Size: ${ss.calculatedSize} patients", pdfThemeStyle.bodyFont(), 10.5f, xOffset = 10f)
                        yCoord -= 8f
                    }

                    if (m.statisticalAnalysis.isNotEmpty()) {
                        ensureSpace(40f)
                        writeText("6. Statistical Analysis", pdfThemeStyle.sectionFont(), 12f, color = pdfThemeStyle.accentColor)
                        yCoord -= 4f
                        m.statisticalAnalysis.forEach { analysis ->
                            writeBulletText(analysis, pdfThemeStyle.bodyFont(), 10.5f, xOffset = 10f)
                        }
                        yCoord -= 8f
                    }
                }

                fun renderStructuredDiscussion(d: DiscussionJson) {
                    ensureSpace(40f)
                    writeText("1. Key Findings", pdfThemeStyle.sectionFont(), 12f, color = pdfThemeStyle.accentColor)
                    yCoord -= 4f
                    writeText(d.keyFindings, pdfThemeStyle.bodyFont(), 10.5f, xOffset = 10f)
                    yCoord -= 8f

                    if (d.comparisonWithLiterature.isNotEmpty()) {
                        ensureSpace(60f)
                        writeText("2. Comparison with Literature", pdfThemeStyle.sectionFont(), 12f, color = pdfThemeStyle.accentColor)
                        yCoord -= 4f
                        d.comparisonWithLiterature.forEachIndexed { index, comp ->
                            ensureSpace(40f)
                            writeText("Comparison point ${index + 1}:", pdfThemeStyle.sectionFont(), 10.5f, xOffset = 10f, color = pdfThemeStyle.accentColor)
                            writeText("Finding: ${comp.finding}", pdfThemeStyle.bodyFont(), 10.5f, xOffset = 16f)
                            writeText("Reference: ${comp.citationReference}", pdfThemeStyle.bodyFont(), 10.5f, xOffset = 16f)
                            writeText("Comparison: ${comp.comparison}", pdfThemeStyle.bodyFont(), 10.5f, xOffset = 16f)
                            yCoord -= 4f
                        }
                        yCoord -= 8f
                    }

                    if (d.limitations.isNotEmpty()) {
                        ensureSpace(40f)
                        writeText("3. Study Limitations", pdfThemeStyle.sectionFont(), 12f, color = pdfThemeStyle.accentColor)
                        yCoord -= 4f
                        d.limitations.forEach { limit ->
                            writeBulletText(limit, pdfThemeStyle.bodyFont(), 10.5f, xOffset = 10f)
                        }
                        yCoord -= 8f
                    }

                    if (d.clinicalImplications.isNotBlank()) {
                        ensureSpace(40f)
                        writeText("4. Clinical Implications", pdfThemeStyle.sectionFont(), 12f, color = pdfThemeStyle.accentColor)
                        yCoord -= 4f
                        writeText(d.clinicalImplications, pdfThemeStyle.bodyFont(), 10.5f, xOffset = 10f)
                        yCoord -= 8f
                    }

                    if (d.futureDirections.isNotEmpty()) {
                        ensureSpace(40f)
                        writeText("5. Future Directions", pdfThemeStyle.sectionFont(), 12f, color = pdfThemeStyle.accentColor)
                        yCoord -= 4f
                        d.futureDirections.forEach { dir ->
                            writeBulletText(dir, pdfThemeStyle.bodyFont(), 10.5f, xOffset = 10f)
                        }
                        yCoord -= 8f
                    }
                }

                suspend fun renderStructuredChapter(chapter: Chapter): Boolean {
                    if (chapter.name.lowercase().contains("methods") || chapter.name.lowercase().contains("methodology")) {
                        val m = runCatching { gson.fromJson(chapter.rawJson, MethodologyJson::class.java) }.getOrNull()
                        if (m != null && !m.designType.isNullOrBlank()) {
                            currentSectionLabel = chapter.name
                            renderStructuredMethodology(m)
                            return true
                        }
                    }
                    if (chapter.name.lowercase().contains("discussion")) {
                        val d = runCatching { gson.fromJson(chapter.rawJson, DiscussionJson::class.java) }.getOrNull()
                        if (d != null && !d.keyFindings.isNullOrBlank()) {
                            currentSectionLabel = chapter.name
                            renderStructuredDiscussion(d)
                            return true
                        }
                    }
                    val structured = parseThesisChapterJson(chapter.rawJson, chapter.name)
                    if (structured.sections.isEmpty()) return false
                    val resolvedFigures = chapter.figures.ifEmpty { collectChapterFigures(structured) }
                    val sectionCount = structured.sections.size.coerceAtLeast(1)
                    val topLevelFiguresBySection = structured.figures.withIndex().groupBy(
                        keySelector = { (index, _) -> ((index + 1) * sectionCount / (structured.figures.size + 1).coerceAtLeast(2)).coerceIn(0, sectionCount - 1) },
                        valueTransform = { it.value }
                    )
                    val chartsBySection = structured.charts.withIndex().groupBy(
                        keySelector = { (index, _) -> ((index + 1) * sectionCount / (structured.charts.size + 1).coerceAtLeast(2)).coerceIn(0, sectionCount - 1) },
                        valueTransform = { it.value }
                    )

                    currentSectionLabel = chapter.name
                    for ((sectionIndex, section) in structured.sections.withIndex()) {
                        renderStructuredSection(section, chapter.name, resolvedFigures)
                        topLevelFiguresBySection[sectionIndex].orEmpty().forEach { figure ->
                            val resolved = resolveExportFigure(figure, resolvedFigures)
                            renderFigureBlock(
                                resolved.figureNumber,
                                resolved.title,
                                resolved.caption,
                                resolved.imageUrl.ifBlank { resolved.sourceUrl },
                                resolved.imageSearchQuery
                            )
                        }
                        chartsBySection[sectionIndex].orEmpty().forEach { chart ->
                            renderChartBlock(chart)
                        }
                    }

                    if (structured.tables.isNotEmpty()) {
                        ensureSpace(24f)
                        writeText("TABLES", pdfThemeStyle.sectionFont(), pdfThemeStyle.headingSize(), color = pdfThemeStyle.accentColor)
                        structured.tables.forEach { table ->
                            val normalized = normalizeThesisTable(table)
                            ensureSpace(120f)
                            val newState = drawPdfTable(
                                pdf,
                                TableDrawingState(yCoord, contentStream),
                                normalized.headers,
                                normalized.rows,
                                normalized.footnote,
                                pageSize,
                                margin,
                                headerFillColor = pdfThemeStyle.headerFillColor,
                                accentColor = pdfThemeStyle.accentColor,
                                tableLayout = pdfThemeStyle.tableLayout,
                                ruleColor = pdfThemeStyle.ruleColor,
                                newPage = { newPage(currentSectionLabel) }
                            )
                            yCoord = newState.y
                            contentStream = newState.contentStream ?: contentStream
                            yCoord -= 12f
                        }
                    }

                    if (structured.abbreviations.isNotEmpty()) {
                        ensureSpace(24f)
                        writeText("ABBREVIATIONS", pdfThemeStyle.sectionFont(), pdfThemeStyle.headingSize(), color = pdfThemeStyle.accentColor)
                        structured.abbreviations.forEach { abbr ->
                            ensureSpace(18f)
                            writeText("${abbr.shortForm} = ${abbr.fullForm}", pdfThemeStyle.bodyFont(), 10.5f, xOffset = 8f)
                        }
                    }

                    return true
                }

                suspend fun renderSpecialFormChapter(chapter: Chapter): Boolean {
                    val bitmap = renderSpecialFormChapterBitmap(context, logoBitmap, pdfThemeStyle, chapter) ?: return false

                    closeContentStream()
                    contentStream = newPage(chapter.name, decorate = false)

                    val image = LosslessFactory.createFromImage(pdf, bitmap)
                    val drawableWidth = pageSize.width - (margin * 2)
                    val drawableHeight = pageSize.height - (margin * 2)
                    contentStream.drawImage(image, margin, margin, drawableWidth, drawableHeight)
                    Log.d("ThesisExport", "PDF special page drawn as bitmap: ${chapter.name}")
                    yCoord = margin
                    bitmap.recycle()
                    return true
                }

                val titleChapter = uiState.value.chapters.firstOrNull { it.name.equals("title", ignoreCase = true) }
                val titleBitmap = if (titleChapter != null) {
                    renderSpecialFormChapterBitmap(context, logoBitmap, pdfThemeStyle, titleChapter)
                } else {
                    renderTitlePageBitmap(context, logoBitmap, pdfThemeStyle, buildTitlePageDataFromVariables(), "TITLE PAGE")
                }

                titleBitmap?.let { bitmap ->
                    Log.d("ThesisExport", "PDF rendering title page bitmap")
                    contentStream = newPage("TITLE PAGE", decorate = false)
                    val image = LosslessFactory.createFromImage(pdf, bitmap)
                    contentStream.drawImage(image, margin, margin, pageSize.width - (margin * 2), pageSize.height - (margin * 2))
                    bitmap.recycle()
                }

                // Chapters
                val exportChapters = uiState.value.chapters.filter {
                    if (it.status != Chapter.ChapterStatus.SUCCESS) return@filter false
                    if (it.name.equals("title", ignoreCase = true)) return@filter false
                    val normalizedName = it.name.lowercase().trim()
                    if (!exportSettings.exportAutoToc && normalizedName == "table of contents") return@filter false
                    if (!exportSettings.exportAutoLists && normalizedName in setOf("list of tables", "list of figures", "list of abbreviations", "list of references")) return@filter false
                    true
                }
                _uiState.update { it.copy(progressCurrent = 0, progressTotal = (exportChapters.size + 1).coerceAtLeast(1)) }
                for ((chapterIndex, chapter) in exportChapters.withIndex()) {
                if (chapter.status != Chapter.ChapterStatus.SUCCESS) continue
                if (chapter.name.equals("title", ignoreCase = true)) continue
                _uiState.update {
                    it.copy(
                        status = "Exporting PDF chapter ${chapterIndex + 1}/${exportChapters.size}: ${chapter.name}",
                        progressCurrent = chapterIndex + 1,
                        progressTotal = (exportChapters.size + 1).coerceAtLeast(1)
                    )
                }
                Log.d("ThesisExport", "PDF exporting chapter: ${chapter.name}, contentChars=${chapter.content.length}, rawJsonChars=${chapter.rawJson.length}")
                if (renderSpecialFormChapter(chapter)) {
                    Log.d("ThesisExport", "PDF exported special-form chapter: ${chapter.name}")
                    continue
                }

                    closeContentStream()
                    currentSectionLabel = chapter.name
                    contentStream = newPage(chapter.name)

                    // Render the chapter layout header in PDF body
                    when (pdfThemeStyle.chapterLayout) {
                        ChapterLayout.SIMPLE_TITLE -> {
                            ensureSpace(40f)
                            drawCenteredText(chapter.name.uppercase(), pdfThemeStyle.chapterFont(), pdfThemeStyle.chapterTitleSize(), yCoord, pdfThemeStyle.accentColor)
                            yCoord -= pdfThemeStyle.chapterTitleSize() + 10f
                            setStrokeColor(contentStream, pdfThemeStyle.headerFillColor)
                            contentStream.setLineWidth(1f)
                            contentStream.moveTo(margin + 20f, yCoord)
                            contentStream.lineTo(pageSize.width - margin - 20f, yCoord)
                            contentStream.stroke()
                            yCoord -= 20f
                        }
                        ChapterLayout.LEFT_RULE -> {
                            ensureSpace(40f)
                            writeText(chapter.name.uppercase(), pdfThemeStyle.chapterFont(), pdfThemeStyle.chapterTitleSize(), color = pdfThemeStyle.accentColor)
                            yCoord -= 6f
                            writeText("Clinical report section", pdfThemeStyle.bodyFont(), 9f, color = pdfThemeStyle.ruleColor)
                            yCoord -= 12f
                        }
                        ChapterLayout.JOURNAL_HEADING -> {
                            ensureSpace(40f)
                            writeText(chapter.name, pdfThemeStyle.chapterFont(), pdfThemeStyle.chapterTitleSize(), color = Color.BLACK)
                            yCoord -= 8f
                            setStrokeColor(contentStream, pdfThemeStyle.ruleColor)
                            contentStream.setLineWidth(0.8f)
                            contentStream.moveTo(margin, yCoord)
                            contentStream.lineTo(pageSize.width - margin, yCoord)
                            contentStream.stroke()
                            yCoord -= 16f
                        }
                        ChapterLayout.FULL_WIDTH_BANNER -> {
                            ensureSpace(60f)
                            setFillColor(contentStream, pdfThemeStyle.headerFillColor)
                            contentStream.addRect(margin, yCoord - 45f, pageSize.width - (margin * 2f), 55f)
                            contentStream.fill()
                            
                            drawCenteredText(chapter.name.uppercase(), pdfThemeStyle.chapterFont(), pdfThemeStyle.chapterTitleSize(), yCoord - 32f, pdfThemeStyle.accentColor)
                            yCoord -= 60f
                        }
                    }

                    val renderedStructured = renderStructuredChapter(chapter)
                    if (!renderedStructured) {
                        val fallbackText = exportTextForChapter(chapter)
                        if (fallbackText.isBlank()) {
                            Log.w("ThesisExport", "PDF fallback chapter has no text: ${chapter.name}")
                        }
                        writeText(fallbackText, pdfThemeStyle.bodyFont(), 11f)
                    }

                    if (!renderedStructured) {
                        // ---- RENDER TABLES ----
                        chapter.tables.forEach { table ->
                            val normalizedTable = normalizeThesisTable(table)
                            Log.d("ThesisExport", "Rendering table: ${table.tableNumber} - ${table.title} in chapter ${chapter.name}")
                            yCoord -= 20f
                            ensureSpace(120f)
                            val newState = drawPdfTable(
                                pdf,
                                TableDrawingState(yCoord, contentStream),
                                normalizedTable.headers,
                                normalizedTable.rows,
                                normalizedTable.footnote,
                                pageSize,
                                margin,
                                headerFillColor = pdfThemeStyle.headerFillColor,
                                accentColor = pdfThemeStyle.accentColor,
                                tableLayout = pdfThemeStyle.tableLayout,
                                ruleColor = pdfThemeStyle.ruleColor,
                                newPage = { newPage() }
                            )
                            yCoord = newState.y
                            contentStream = newState.contentStream ?: contentStream
                        }

                        // ---- RENDER CHARTS (as images) ----
                        chapter.charts.forEach { chart ->
                            val normalizedChart = normalizeResultChart(chart)
                            Log.d("ThesisExport", "Rendering chart: ${normalizedChart.chartId} - ${normalizedChart.title} in chapter ${chapter.name}")
                            val chartBitmap = withContext(Dispatchers.Main) {
                                renderChartToBitmap(context, normalizedChart, pdfThemeStyle, widthPx = 900, heightPx = 560)
                            }
                            if (chartBitmap != null) {
                                yCoord -= 12f
                                drawScaledCenteredBitmap(chartBitmap, contentWidth() - 18f, 300f)
                                chartBitmap.recycle()
                            } else {
                                Log.e("ThesisExport", "Failed to render chart bitmap for: ${normalizedChart.title}")
                            }
                        }

                        // ---- RENDER FIGURES (images) ----
                        chapter.figures.forEach { figure ->
                            renderFigureBlock(
                                figure.figureNumber,
                                figure.title,
                                figure.caption,
                                figure.imageUrl.ifBlank { figure.sourceUrl },
                                figure.imageSearchQuery
                            )
                        }
                    }
                }

                closeContentStream()
                _uiState.update {
                    it.copy(
                        status = "Saving PDF document...",
                        progressCurrent = (exportChapters.size + 1).coerceAtLeast(1),
                        progressTotal = (exportChapters.size + 1).coerceAtLeast(1)
                    )
                }
                Log.d("ThesisExport", "PDF saving document pages=${pdf.numberOfPages} uri=$uri")
                savePdfDocument(context, uri, pdf)
                _uiState.update { it.copy(processing = false, status = "PDF exported", lastExportedUri = uri) }
                saveSessionToFirebase()
            } catch (e: Exception) {
                Log.e("ThesisExport", "PDF export failed for uri=$uri", e)
                _uiState.update { it.copy(processing = false, status = "PDF export failed: ${e.message}") }
            } finally {
                logoBitmap?.recycle()
                runCatching { pdfToClose?.close() }
                stopBackgroundWork(appContext)
            }
        }
    }

    private fun savePdfDocument(context: Context, uri: Uri, pdf: PDDocument) {
        val outputStream = if (uri.scheme.equals("file", ignoreCase = true)) {
            val path = uri.path ?: throw IllegalArgumentException("Invalid file destination")
            FileOutputStream(java.io.File(path))
        } else {
            context.contentResolver.openOutputStream(uri, "w")
                ?: throw IOException("Unable to open output stream")
        }

        outputStream.use { out ->
            pdf.save(out)
        }
    }

    fun exportAllChaptersToDocx(context: Context, uri: Uri) {
        reindexAllCitations()
        viewModelScope.launch(Dispatchers.IO) {
            val appContext = context.applicationContext
            startBackgroundWork(appContext, "Exporting thesis DOCX")
            try {
                _uiState.update { it.copy(processing = true, status = "Starting DOCX export...", progressCurrent = 0, progressTotal = 1) }
                val chapters = _uiState.value.chapters.filter { it.status == Chapter.ChapterStatus.SUCCESS }
                _uiState.update { it.copy(progressCurrent = 0, progressTotal = (chapters.size + 1).coerceAtLeast(1)) }
                val themeStyle = resolvePdfThemeStyle(_uiState.value.pdfTheme)
                val document = XWPFDocument()
                try {
                    addDocxCover(document, themeStyle)
                    chapters.forEachIndexed { index, chapter ->
                        _uiState.update {
                            it.copy(
                                status = "Exporting DOCX chapter ${index + 1}/${chapters.size}: ${chapter.name}",
                                progressCurrent = index + 1,
                                progressTotal = (chapters.size + 1).coerceAtLeast(1)
                            )
                        }
                        if (index > 0) document.createParagraph().createRun().addBreak(BreakType.PAGE)
                        Log.d("ThesisExport", "DOCX exporting chapter ${index + 1}/${chapters.size}: ${chapter.name}, contentChars=${chapter.content.length}, rawJsonChars=${chapter.rawJson.length}")
                        addDocxChapter(appContext, document, chapter, themeStyle)
                    }
                    _uiState.update {
                        it.copy(
                            status = "Saving DOCX document...",
                            progressCurrent = (chapters.size + 1).coerceAtLeast(1),
                            progressTotal = (chapters.size + 1).coerceAtLeast(1)
                        )
                    }
                    Log.d("ThesisExport", "DOCX saving chapters=${chapters.size} uri=$uri")
                    saveDocxDocument(appContext, uri, document)
                } finally {
                    document.close()
                }
                _uiState.update { it.copy(processing = false, status = "DOCX exported", lastExportedUri = uri) }
            } catch (e: Exception) {
                Log.e("ThesisExport", "DOCX export failed for uri=$uri", e)
                _uiState.update { it.copy(processing = false, status = "DOCX export failed: ${e.message}") }
            } finally {
                stopBackgroundWork(appContext)
            }
        }
    }

    fun exportAllChaptersToPptx(context: Context, uri: Uri) {
        reindexAllCitations()
        viewModelScope.launch(Dispatchers.IO) {
            val appContext = context.applicationContext
            startBackgroundWork(appContext, "Exporting thesis PPTX")
            try {
                _uiState.update { it.copy(processing = true, status = "Starting PPTX export...", progressCurrent = 0, progressTotal = 3) }
                val themeStyle = resolvePdfThemeStyle(_uiState.value.pdfTheme)
                _uiState.update { it.copy(status = "Building PPTX slides...", progressCurrent = 1, progressTotal = 3) }
                val slides = buildPptxSlides(appContext)
                Log.d("ThesisExport", "PPTX built slides=${slides.size} uri=$uri")
                _uiState.update { it.copy(status = "Saving PPTX presentation...", progressCurrent = 2, progressTotal = 3) }
                savePptxDocument(appContext, uri, slides, themeStyle)
                _uiState.update { it.copy(processing = false, status = "PPTX exported", lastExportedUri = uri) }
            } catch (e: Exception) {
                Log.e("ThesisExport", "PPTX export failed for uri=$uri", e)
                _uiState.update { it.copy(processing = false, status = "PPTX export failed: ${e.message}") }
            } finally {
                stopBackgroundWork(appContext)
            }
        }
    }

    private fun outputStreamForUri(context: Context, uri: Uri) =
        if (uri.scheme.equals("file", ignoreCase = true)) {
            val path = uri.path ?: throw IllegalArgumentException("Invalid file destination")
            FileOutputStream(java.io.File(path))
        } else {
            context.contentResolver.openOutputStream(uri, "w")
                ?: throw IOException("Unable to open output stream")
        }

    private fun saveDocxDocument(context: Context, uri: Uri, document: XWPFDocument) {
        outputStreamForUri(context, uri).use { output ->
            document.write(output)
        }
    }

    private fun addDocxCover(document: XWPFDocument, theme: PdfThemeStyle) {
        val title = _uiState.value.thesisTitle.ifBlank { "Thesis Report" }
        when (theme.titlePageLayout) {
            TitlePageLayout.CENTERED_UNIVERSITY -> {
                addDocxParagraph(document, "THESIS EXPORT", 11, true, ParagraphAlignment.CENTER, color = theme.ruleColor, spacingAfter = 120, theme = theme, role = DocxTextRole.META)
                addDocxParagraph(document, title, 26, true, ParagraphAlignment.CENTER, color = theme.accentColor, spacingAfter = 160, theme = theme, role = DocxTextRole.TITLE)
            }
            TitlePageLayout.LOGO_TOP_OFFICIAL -> {
                addDocxParagraph(document, "OFFICIAL THESIS FILE", 12, true, ParagraphAlignment.LEFT, color = theme.accentColor, spacingAfter = 90, theme = theme, role = DocxTextRole.META)
                addDocxParagraph(document, title, 24, true, ParagraphAlignment.LEFT, color = theme.accentColor, spacingAfter = 140, theme = theme, role = DocxTextRole.TITLE)
            }
            TitlePageLayout.JOURNAL_MANUSCRIPT -> {
                addDocxParagraph(document, "Manuscript Export", 11, false, ParagraphAlignment.CENTER, color = theme.ruleColor, spacingAfter = 90, theme = theme, role = DocxTextRole.META)
                addDocxParagraph(document, title, 22, true, ParagraphAlignment.CENTER, color = Color.BLACK, spacingAfter = 120, theme = theme, role = DocxTextRole.TITLE)
                addDocxParagraph(document, "____________________________________________________________", 8, false, ParagraphAlignment.CENTER, color = theme.ruleColor, spacingAfter = 120, theme = theme, role = DocxTextRole.META)
            }
            TitlePageLayout.MODERN_COVER -> {
                addDocxParagraph(document, "PREMIUM THESIS EXPORT", 12, true, ParagraphAlignment.LEFT, color = theme.ruleColor, spacingAfter = 80, theme = theme, role = DocxTextRole.META)
                addDocxParagraph(document, title, 28, true, ParagraphAlignment.LEFT, color = theme.accentColor, spacingAfter = 150, theme = theme, role = DocxTextRole.TITLE)
                addDocxParagraph(document, "________________________________________", 9, false, ParagraphAlignment.LEFT, color = theme.headerFillColor, spacingAfter = 120, theme = theme, role = DocxTextRole.META)
            }
        }
        addDocxParagraph(document, "Generated: ${java.text.SimpleDateFormat("MMM dd, yyyy HH:mm", java.util.Locale.getDefault()).format(java.util.Date())}", 11, false, ParagraphAlignment.CENTER, color = theme.ruleColor, spacingAfter = 60, theme = theme, role = DocxTextRole.META)
        addDocxParagraph(document, "Session: ${_uiState.value.sessionId.takeLast(12)}", 10, false, ParagraphAlignment.CENTER, color = theme.ruleColor, spacingAfter = 260, theme = theme, role = DocxTextRole.META)
        document.createParagraph().createRun().addBreak(BreakType.PAGE)
    }

    private suspend fun addDocxChapter(context: Context, document: XWPFDocument, chapter: Chapter, theme: PdfThemeStyle) {
        val structured = runCatching { parseThesisChapterJson(chapter.rawJson, chapter.name) }.getOrNull()
        when (theme.chapterLayout) {
            ChapterLayout.SIMPLE_TITLE -> {
                addDocxParagraph(document, chapter.name.uppercase(), 18, true, ParagraphAlignment.CENTER, color = theme.accentColor, spacingAfter = 90, theme = theme, role = DocxTextRole.CHAPTER)
                addDocxParagraph(document, "____________________________________________________________", 8, false, ParagraphAlignment.CENTER, color = theme.headerFillColor, spacingAfter = 160, theme = theme, role = DocxTextRole.META)
            }
            ChapterLayout.LEFT_RULE -> {
                addDocxParagraph(document, chapter.name.uppercase(), 18, true, ParagraphAlignment.LEFT, color = theme.accentColor, spacingAfter = 60, theme = theme, role = DocxTextRole.CHAPTER)
                addDocxParagraph(document, "Clinical report section", 10, false, ParagraphAlignment.LEFT, color = theme.ruleColor, spacingAfter = 120, theme = theme, role = DocxTextRole.META)
            }
            ChapterLayout.JOURNAL_HEADING -> {
                addDocxParagraph(document, chapter.name, 17, true, ParagraphAlignment.LEFT, color = Color.BLACK, spacingAfter = 50, theme = theme, role = DocxTextRole.CHAPTER)
                addDocxParagraph(document, "____________________________________________________________", 7, false, ParagraphAlignment.LEFT, color = theme.ruleColor, spacingAfter = 120, theme = theme, role = DocxTextRole.META)
            }
            ChapterLayout.FULL_WIDTH_BANNER -> {
                addDocxParagraph(document, chapter.name.uppercase(), 20, true, ParagraphAlignment.LEFT, color = theme.accentColor, spacingAfter = 70, theme = theme, role = DocxTextRole.CHAPTER)
                addDocxParagraph(document, "________________________________________", 9, false, ParagraphAlignment.LEFT, color = theme.headerFillColor, spacingAfter = 140, theme = theme, role = DocxTextRole.META)
            }
        }

        if (structured == null || structured.sections.isEmpty()) {
            val rawFallbackText = chapter.content.ifBlank { extractVisibleText(chapter.rawJson) }
            val fallbackText = if (chapterTypeFor(chapter.name) == "REFERENCES") {
                rawFallbackText
            } else {
                stripAppendedReferenceBlock(rawFallbackText)
            }
            if (fallbackText.isBlank()) {
                Log.w("ThesisExport", "DOCX fallback chapter has no text: ${chapter.name}")
            }
            addDocxMultilineText(document, fallbackText, theme)
        } else {
            val resolvedFigures = chapter.figures.ifEmpty { collectChapterFigures(structured) }
            structured.sections.forEach { section ->
                if (section.heading.isNotBlank() && !sameExportHeading(section.heading, chapter.name)) {
                    addDocxParagraph(document, section.heading, theme.docxHeadingSize(DocxTextRole.SECTION), true, color = theme.accentColor, spacingBefore = 140, spacingAfter = 70, theme = theme, role = DocxTextRole.SECTION)
                }
                section.content?.takeIf { it.isNotBlank() }?.let { addDocxMultilineText(document, it, theme) }
                section.bullets.forEach { addDocxParagraph(document, it, 11, false, bullet = true, theme = theme, role = DocxTextRole.BODY) }
                section.numberedPoints.forEachIndexed { index, point -> addDocxParagraph(document, "${index + 1}. $point", 11, false, theme = theme, role = DocxTextRole.BODY) }
                section.subsections.forEach { sub ->
                    if (sub.heading.isNotBlank()) addDocxParagraph(document, sub.heading, theme.docxHeadingSize(DocxTextRole.SECTION) - 1, true, color = theme.ruleColor, spacingBefore = 90, spacingAfter = 40, theme = theme, role = DocxTextRole.SECTION)
                    if (sub.content.isNotBlank()) addDocxMultilineText(document, sub.content, theme)
                }
                section.table?.let { addDocxTable(document, normalizeThesisTable(it), theme) }
                section.figures.forEach { addDocxFigure(context, document, resolveExportFigure(it, resolvedFigures), theme) }
            }

            structured.tables.map(::normalizeThesisTable).forEach { addDocxTable(document, it, theme) }
            collectChapterFigures(structured).forEach { addDocxFigure(context, document, resolveExportFigure(it, resolvedFigures), theme) }
            structured.charts.forEach { addDocxChart(context, document, it, theme) }
            structured.abbreviations.forEach { addDocxParagraph(document, "${it.shortForm} = ${it.fullForm}", 11, false, theme = theme, role = DocxTextRole.BODY) }
        }

        chapter.tables.map(::normalizeThesisTable).forEach { addDocxTable(document, it, theme) }
        chapter.figures.forEach { addDocxFigure(context, document, it, theme) }
        chapter.charts.forEach { addDocxChart(context, document, it, theme) }
        chapter.abbreviations.forEach { addDocxParagraph(document, "${it.shortForm} = ${it.fullForm}", 11, false, theme = theme, role = DocxTextRole.BODY) }
    }

    private fun addDocxMultilineText(document: XWPFDocument, text: String, theme: PdfThemeStyle) {
        text.lines().map { it.trim() }.filter { it.isNotBlank() }.forEach {
            addDocxParagraph(document, it, 11, false, color = Color.BLACK, firstLineIndent = 260, spacingAfter = 70, theme = theme, role = DocxTextRole.BODY)
        }
    }

    private fun addDocxParagraph(
        document: XWPFDocument,
        text: String,
        size: Int,
        bold: Boolean,
        alignment: ParagraphAlignment = ParagraphAlignment.LEFT,
        bullet: Boolean = false,
        color: Int = Color.BLACK,
        spacingBefore: Int = 0,
        spacingAfter: Int = 100,
        firstLineIndent: Int = 0,
        theme: PdfThemeStyle? = null,
        role: DocxTextRole = DocxTextRole.BODY
    ): XWPFParagraph {
        val paragraph = document.createParagraph()
        paragraph.alignment = alignment
        paragraph.verticalAlignment = TextAlignment.AUTO
        paragraph.spacingBefore = spacingBefore
        paragraph.spacingAfter = spacingAfter
        if (firstLineIndent > 0) paragraph.indentationFirstLine = firstLineIndent
        if (bullet) paragraph.indentationLeft = 420
        val paragraphText = if (bullet) "\u2022 $text" else text
        val fontFamily = theme?.docxFontFamily(role) ?: "Arial"
        parseBoldMarkdownRuns(paragraphText).forEach { segment ->
            val run = paragraph.createRun()
            run.fontFamily = fontFamily
            run.fontSize = size
            run.isBold = bold || segment.bold
            run.setColor(officeColor(color))
            run.setText(sanitizeOfficeText(segment.text))
        }
        return paragraph
    }

    private fun addDocxTable(document: XWPFDocument, table: ThesisTableJson, theme: PdfThemeStyle) {
        val normalized = normalizeThesisTable(table)
        val headers = normalized.headers.ifEmpty {
            List(normalized.rows.maxOfOrNull { it.size } ?: 0) { "Column ${it + 1}" }
        }
        if (headers.isEmpty()) return
        if (normalized.title.isNotBlank()) {
            addDocxParagraph(document, listOf(normalized.tableNumber, normalized.title).filter { it.isNotBlank() }.joinToString(": "), 11, true, color = theme.accentColor, spacingBefore = 140, spacingAfter = 60, theme = theme, role = DocxTextRole.SECTION)
        }
        val xwpfTable = document.createTable(normalized.rows.size + 1, headers.size)
        fillDocxRow(xwpfTable.getRow(0), headers, bold = true, theme = theme, header = true, shaded = true)
        normalized.rows.forEachIndexed { rowIndex, row -> fillDocxRow(xwpfTable.getRow(rowIndex + 1), row, bold = false, theme = theme, header = false, shaded = rowIndex % 2 == 0) }
        normalized.footnote?.takeIf { it.isNotBlank() }?.let { addDocxParagraph(document, "Note: $it", 9, false, color = theme.ruleColor, theme = theme, role = DocxTextRole.CAPTION) }
    }

    private fun fillDocxRow(row: XWPFTableRow, values: List<String>, bold: Boolean, theme: PdfThemeStyle, header: Boolean, shaded: Boolean) {
        values.forEachIndexed { index, value ->
            val cell = row.getCell(index) ?: row.addNewTableCell()
            cell.color = when {
                header -> officeColor(theme.accentColor)
                shaded -> officeColor(theme.footerFillColor)
                else -> "FFFFFF"
            }
            setDocxCellText(cell, value, bold, if (header) Color.WHITE else Color.BLACK, theme)
        }
    }

    private fun setDocxCellText(cell: XWPFTableCell, text: String, bold: Boolean, color: Int, theme: PdfThemeStyle) {
        val paragraph = cell.paragraphs.firstOrNull() ?: cell.addParagraph()
        paragraph.spacingBefore = 40
        paragraph.spacingAfter = 40
        val run = paragraph.createRun()
        run.fontFamily = theme.docxFontFamily(DocxTextRole.TABLE)
        run.fontSize = 9
        run.isBold = bold
        run.setColor(officeColor(color))
        parseBoldMarkdownRuns(text).forEachIndexed { index, segment ->
            val targetRun = if (index == 0) run else paragraph.createRun()
            targetRun.fontFamily = theme.docxFontFamily(DocxTextRole.TABLE)
            targetRun.fontSize = 9
            targetRun.isBold = bold || segment.bold
            targetRun.setColor(officeColor(color))
            targetRun.setText(sanitizeOfficeText(segment.text))
        }
    }

    private suspend fun addDocxFigure(context: Context, document: XWPFDocument, figure: FigureJson, theme: PdfThemeStyle) {
        val source = figure.imageUrl.ifBlank { figure.sourceUrl }
        if (figure.title.isNotBlank() || figure.caption.isNotBlank()) {
            addDocxParagraph(document, "Figure ${figure.figureNumber.ifBlank { "" }}: ${figure.title}".trim(), 11, true, color = theme.accentColor, spacingBefore = 140, spacingAfter = 50, theme = theme, role = DocxTextRole.CAPTION)
        }
        val bitmap = loadFigureBitmap(context, source, figure.imageSearchQuery)
        bitmap?.let {
            addDocxBitmap(document, it, 440, 260)
            it.recycle()
        }
        if (figure.caption.isNotBlank()) addDocxParagraph(document, figure.caption, 10, false, color = theme.ruleColor, theme = theme, role = DocxTextRole.CAPTION)
    }

    private suspend fun addDocxChart(context: Context, document: XWPFDocument, chart: ChartJson, theme: PdfThemeStyle) {
        addDocxParagraph(document, chart.title.ifBlank { "Chart" }, 11, true, color = theme.accentColor, spacingBefore = 140, spacingAfter = 50, theme = theme, role = DocxTextRole.CAPTION)
        val bitmap = withContext(Dispatchers.Main) {
            renderChartToBitmap(context, normalizeResultChart(chart), theme, widthPx = 900, heightPx = 560)
        }
        bitmap?.let {
            addDocxBitmap(document, it, 460, 285)
            it.recycle()
        }
    }

    private fun addDocxBitmap(document: XWPFDocument, bitmap: Bitmap, widthDp: Int, heightDp: Int) {
        val bytes = bitmapToPngBytes(bitmap)
        val paragraph = document.createParagraph()
        paragraph.alignment = ParagraphAlignment.CENTER
        val run = paragraph.createRun()
        run.addPicture(
            ByteArrayInputStream(bytes),
            Document.PICTURE_TYPE_PNG,
            "image_${UUID.randomUUID()}.png",
            org.apache.poi.util.Units.toEMU(widthDp.toDouble()),
            org.apache.poi.util.Units.toEMU(heightDp.toDouble())
        )
    }

    private data class PptxSlide(
        val title: String,
        val bodyLines: List<String> = emptyList(),
        val tables: List<ThesisTableJson> = emptyList(),
        val images: List<ByteArray> = emptyList(),
        val layout: String = "content",
        val eyebrow: String = ""
    )

    private data class PptxChapterSection(
        val heading: String = "",
        val lines: List<String> = emptyList()
    )

    private data class ExportTextRun(
        val text: String,
        val bold: Boolean
    )

    private fun sameExportHeading(left: String, right: String): Boolean {
        fun normalize(value: String): String {
            return value.lowercase()
                .replace(Regex("[^a-z0-9]+"), " ")
                .trim()
        }
        return normalize(left) == normalize(right)
    }

    private fun parseBoldMarkdownRuns(text: String): List<ExportTextRun> {
        val runs = mutableListOf<ExportTextRun>()
        var index = 0
        while (index < text.length) {
            val start = text.indexOf("**", startIndex = index)
            if (start < 0) {
                if (index < text.length) runs += ExportTextRun(text.substring(index), bold = false)
                break
            }

            if (start > index) {
                runs += ExportTextRun(text.substring(index, start), bold = false)
            }

            val end = text.indexOf("**", startIndex = start + 2)
            if (end < 0) {
                runs += ExportTextRun(text.substring(start), bold = false)
                break
            }

            runs += ExportTextRun(text.substring(start + 2, end), bold = true)
            index = end + 2
        }

        return runs.filter { it.text.isNotEmpty() }
    }

    private fun stripBoldMarkdown(text: String): String =
        parseBoldMarkdownRuns(text).joinToString("") { it.text }

    private fun appendExportRun(runs: MutableList<ExportTextRun>, text: String, bold: Boolean) {
        if (text.isEmpty()) return
        val last = runs.lastOrNull()
        if (last != null && last.bold == bold) {
            runs[runs.lastIndex] = last.copy(text = last.text + text)
        } else {
            runs += ExportTextRun(text, bold)
        }
    }

    private fun wrapBoldMarkdownForExport(text: String, maxChars: Int = 170): List<String> {
        val lines = mutableListOf<String>()
        text.lines().forEach { sourceLine ->
            val words = parseBoldMarkdownRuns(sourceLine)
                .flatMap { run ->
                    run.text.trim().split(Regex("\\s+"))
                        .filter { it.isNotBlank() }
                        .map { ExportTextRun(it, run.bold) }
                }
            if (words.isEmpty()) return@forEach

            val current = StringBuilder()
            var currentPlainLength = 0
            words.forEach { word ->
                val encoded = if (word.bold) "**${word.text}**" else word.text
                val nextPlainLength = if (currentPlainLength == 0) word.text.length else currentPlainLength + 1 + word.text.length
                if (current.isNotEmpty() && nextPlainLength > maxChars) {
                    lines += current.toString()
                    current.clear()
                    currentPlainLength = 0
                }
                if (current.isNotEmpty()) current.append(' ')
                current.append(encoded)
                currentPlainLength = if (currentPlainLength == 0) word.text.length else currentPlainLength + 1 + word.text.length
            }
            if (current.isNotEmpty()) lines += current.toString()
        }
        return lines
    }

    private fun wrapPptxTextLine(text: String, maxChars: Int = 170): List<String> {
        return wrapBoldMarkdownForExport(text, maxChars)
    }

    private fun buildPptxChapterSlides(
        chapterTitle: String,
        sections: List<PptxChapterSection>,
        eyebrow: String = "CHAPTER"
    ): List<PptxSlide> {
        val slides = mutableListOf<PptxSlide>()
        val maxLinesPerSlide = 7

        sections.forEach { section ->
            val wrappedLines = section.lines.flatMap { wrapPptxTextLine(it) }
            if (wrappedLines.isEmpty() && section.heading.isBlank()) return@forEach

            val chunks = wrappedLines.chunked(
                if (section.heading.isBlank()) maxLinesPerSlide else maxLinesPerSlide - 1
            ).ifEmpty { listOf(emptyList()) }

            chunks.forEach { chunk ->
                val body = buildList {
                    if (section.heading.isNotBlank()) add(section.heading)
                    addAll(chunk)
                }
                slides += PptxSlide(
                    title = chapterTitle,
                    bodyLines = body,
                    layout = "content",
                    eyebrow = eyebrow
                )
            }
        }

        return slides.ifEmpty {
            listOf(PptxSlide(chapterTitle, layout = "content", eyebrow = eyebrow))
        }
    }

    private fun exportTextForPptxChapter(chapter: Chapter): String {
        val text = chapter.content.ifBlank { extractVisibleText(chapter.rawJson) }
        return if (chapterTypeFor(chapter.name) == "REFERENCES") text else stripAppendedReferenceBlock(text)
    }

    private suspend fun buildPptxSlides(context: Context): List<PptxSlide> {
        val themeStyle = resolvePdfThemeStyle(_uiState.value.pdfTheme)
        val slides = mutableListOf<PptxSlide>()
        slides += PptxSlide(
            title = _uiState.value.thesisTitle.ifBlank { "Thesis Report" },
            bodyLines = listOf("Exported thesis report", "Session: ${_uiState.value.sessionId.takeLast(12)}"),
            layout = "cover",
            eyebrow = "EDULABS"
        )
        _uiState.value.chapters.filter { it.status == Chapter.ChapterStatus.SUCCESS }.forEach { chapter ->
            val structured = runCatching { parseThesisChapterJson(chapter.rawJson, chapter.name) }.getOrNull()
            if (structured == null || structured.sections.isEmpty()) {
                val fallbackText = exportTextForPptxChapter(chapter)
                if (fallbackText.isBlank()) {
                    Log.w("ThesisExport", "PPTX fallback chapter has no text: ${chapter.name}")
                }
                slides += buildPptxChapterSlides(
                    chapter.name,
                    listOf(
                        PptxChapterSection(
                            lines = fallbackText.lines().map { it.trim() }.filter { it.isNotBlank() }
                        )
                    )
                )
            } else {
                val chapterSections = structured.sections.map { section ->
                    PptxChapterSection(
                        heading = section.heading
                            .takeIf { it.isNotBlank() && !sameExportHeading(it, chapter.name) }
                            .orEmpty(),
                        lines = buildList {
                            section.content?.takeIf { it.isNotBlank() }?.let { add(it) }
                            addAll(section.bullets.map { "\u2022 $it" })
                            addAll(section.numberedPoints.mapIndexed { index, item -> "${index + 1}. $item" })
                            section.subsections.forEach { sub ->
                                if (sub.heading.isNotBlank()) add(sub.heading)
                                if (sub.content.isNotBlank()) add(sub.content)
                            }
                        }
                    )
                }.filter { it.heading.isNotBlank() || it.lines.isNotEmpty() }

                slides += buildPptxChapterSlides(
                    chapter.name,
                    chapterSections.ifEmpty {
                        listOf(PptxChapterSection(lines = listOf(exportTextForPptxChapter(chapter))))
                    }
                )
                structured.tables.map(::normalizeThesisTable).forEach {
                    slides += PptxSlide(it.title.ifBlank { "Table" }, tables = listOf(it), layout = "table", eyebrow = "TABLE")
                }
                val resolvedFigures = chapter.figures.ifEmpty { collectChapterFigures(structured) }
                collectChapterFigures(structured).forEach { figure ->
                    val resolved = resolveExportFigure(figure, resolvedFigures)
                    val source = resolved.imageUrl.ifBlank { resolved.sourceUrl }
                    val image = loadFigureBitmap(context, source, resolved.imageSearchQuery)?.let { bitmap ->
                        bitmapToPngBytes(bitmap).also { bitmap.recycle() }
                    }
                    slides += PptxSlide(
                        title = "Figure ${resolved.figureNumber}: ${resolved.title}".trim(),
                        bodyLines = listOfNotNull(resolved.caption.takeIf { it.isNotBlank() }),
                        images = listOfNotNull(image),
                        layout = "media",
                        eyebrow = "FIGURE"
                    )
                }
                structured.charts.forEach { chart ->
                    val image = withContext(Dispatchers.Main) {
                        renderChartToBitmap(context, normalizeResultChart(chart), themeStyle, widthPx = 900, heightPx = 560)
                    }?.let { bitmap ->
                        bitmapToPngBytes(bitmap).also { bitmap.recycle() }
                    }
                    slides += PptxSlide(chart.title.ifBlank { "Chart" }, images = listOfNotNull(image), layout = "media", eyebrow = "CHART")
                }
            }
        }
        return slides
    }

    private fun savePptxDocument(context: Context, uri: Uri, slides: List<PptxSlide>, theme: PdfThemeStyle) {
        outputStreamForUri(context, uri).use { output ->
            ZipOutputStream(output).use { zip ->
                zipText(zip, "[Content_Types].xml", pptxContentTypes(slides.size))
                zipText(zip, "_rels/.rels", pptxRootRels())
                zipText(zip, "docProps/core.xml", pptxCoreProperties())
                zipText(zip, "docProps/app.xml", pptxAppProperties(slides.size))
                zipText(zip, "ppt/presentation.xml", pptxPresentation(slides.size))
                zipText(zip, "ppt/_rels/presentation.xml.rels", pptxPresentationRels(slides.size))
                zipText(zip, "ppt/theme/theme1.xml", pptxTheme(theme))
                zipText(zip, "ppt/slideMasters/slideMaster1.xml", pptxSlideMaster())
                zipText(zip, "ppt/slideMasters/_rels/slideMaster1.xml.rels", pptxSlideMasterRels())
                zipText(zip, "ppt/slideLayouts/slideLayout1.xml", pptxSlideLayout())
                zipText(zip, "ppt/slideLayouts/_rels/slideLayout1.xml.rels", pptxSlideLayoutRels())
                slides.forEachIndexed { index, slide ->
                    val slideNumber = index + 1
                    zipText(zip, "ppt/slides/slide$slideNumber.xml", pptxSlideXml(slide, slideNumber, theme))
                    zipText(zip, "ppt/slides/_rels/slide$slideNumber.xml.rels", pptxSlideRels(slide, slideNumber))
                    slide.images.forEachIndexed { imageIndex, bytes ->
                        zipBytes(zip, "ppt/media/slide${slideNumber}_image${imageIndex + 1}.png", bytes)
                    }
                }
            }
        }
    }

    private fun bitmapToPngBytes(bitmap: Bitmap): ByteArray {
        return ByteArrayOutputStream().use { output ->
            bitmap.compress(Bitmap.CompressFormat.PNG, 100, output)
            output.toByteArray()
        }
    }

    private fun zipText(zip: ZipOutputStream, path: String, text: String) {
        zip.putNextEntry(ZipEntry(path))
        zip.write(text.toByteArray(Charsets.UTF_8))
        zip.closeEntry()
    }

    private fun zipBytes(zip: ZipOutputStream, path: String, bytes: ByteArray) {
        zip.putNextEntry(ZipEntry(path))
        zip.write(bytes)
        zip.closeEntry()
    }

    private fun xml(value: String): String = value
        .let(::sanitizeOfficeText)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\"", "&quot;")
        .replace("'", "&apos;")

    private fun pptxText(value: String): String = xml(value)

    private fun pptxContentTypes(slideCount: Int): String = buildString {
        append("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">""")
        append("""<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/>""")
        append("""<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/><Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>""")
        append("""<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/><Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/><Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/><Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>""")
        repeat(slideCount) { append("""<Override PartName="/ppt/slides/slide${it + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>""") }
        append("</Types>")
    }

    private fun pptxRootRels(): String =
        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/></Relationships>"""

    private fun pptxCoreProperties(): String =
        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>${xml(_uiState.value.thesisTitle.ifBlank { "Thesis Report" })}</dc:title><dc:creator>EduLabs</dc:creator><cp:lastModifiedBy>EduLabs</cp:lastModifiedBy><dcterms:created xsi:type="dcterms:W3CDTF">2026-06-06T00:00:00Z</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">2026-06-06T00:00:00Z</dcterms:modified></cp:coreProperties>"""

    private fun pptxAppProperties(slideCount: Int): String =
        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>EduLabs</Application><PresentationFormat>On-screen Show (16:9)</PresentationFormat><Slides>$slideCount</Slides><Notes>0</Notes><HiddenSlides>0</HiddenSlides><MMClips>0</MMClips><ScaleCrop>false</ScaleCrop><HeadingPairs><vt:vector size="2" baseType="variant"><vt:variant><vt:lpstr>Slides</vt:lpstr></vt:variant><vt:variant><vt:i4>$slideCount</vt:i4></vt:variant></vt:vector></HeadingPairs><TitlesOfParts><vt:vector size="$slideCount" baseType="lpstr">${(1..slideCount).joinToString("") { "<vt:lpstr>Slide $it</vt:lpstr>" }}</vt:vector></TitlesOfParts><Company>EduLabs</Company><LinksUpToDate>false</LinksUpToDate><SharedDoc>false</SharedDoc><HyperlinksChanged>false</HyperlinksChanged><AppVersion>16.0000</AppVersion></Properties>"""

    private fun pptxPresentation(slideCount: Int): String = buildString {
        append("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rIdMaster1"/></p:sldMasterIdLst><p:sldIdLst>""")
        repeat(slideCount) { append("""<p:sldId id="${256 + it}" r:id="rId${it + 1}"/>""") }
        append("""</p:sldIdLst><p:sldSz cx="12192000" cy="6858000" type="screen16x9"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>""")
    }

    private fun pptxPresentationRels(slideCount: Int): String = buildString {
        append("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">""")
        repeat(slideCount) { append("""<Relationship Id="rId${it + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide${it + 1}.xml"/>""") }
        append("""<Relationship Id="rIdMaster1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>""")
        append("""<Relationship Id="rIdTheme1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>""")
        append("</Relationships>")
    }

    private fun pptxSlideRels(slide: PptxSlide, slideNumber: Int): String = buildString {
        append("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">""")
        append("""<Relationship Id="rIdLayout1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>""")
        slide.images.forEachIndexed { index, _ ->
            append("""<Relationship Id="rIdImage${index + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/slide${slideNumber}_image${index + 1}.png"/>""")
        }
        append("</Relationships>")
    }

    private fun pptxSlideXml(slide: PptxSlide, slideNumber: Int, theme: PdfThemeStyle): String {
        val shapes = StringBuilder()
        shapes.append(pptxDesignBlocks(theme, slide.layout))
        when (slide.layout) {
            "cover" -> {
                shapes.append(pptxTextShape(2, slide.eyebrow.ifBlank { "EDULABS" }, 760000, 980000, 2500000, 360000, 13, true, theme.ruleColor))
                shapes.append(pptxTextShape(3, slide.title, 760000, 1500000, 8800000, 1400000, 36, true, theme.accentColor))
                shapes.append(pptxTextShape(4, slide.bodyLines.joinToString("\n"), 800000, 3200000, 5600000, 800000, 18, false, Color.BLACK))
                shapes.append(pptxRectShape(5, 760000, 2920000, 3600000, 70000, theme.headerFillColor, null))
            }
            "media" -> {
                shapes.append(pptxTextShape(2, slide.eyebrow, 650000, 380000, 2000000, 260000, 11, true, theme.ruleColor))
                shapes.append(pptxTextShape(3, slide.title, 650000, 560000, 10800000, 520000, 22, true, theme.accentColor))
                shapes.append(pptxRectShape(4, 1300000, 1580000, 9600000, 4480000, theme.footerFillColor, theme.ruleColor))
                slide.images.forEachIndexed { index, _ ->
                    shapes.append(pptxPictureShape(10 + index, "rIdImage${index + 1}", 1500000, 1780000, 9200000, 4050000))
                }
                val caption = slide.bodyLines.joinToString("\n").take(260)
                if (caption.isNotBlank()) {
                    shapes.append(pptxTextShape(20, caption, 1500000, 5920000, 9200000, 450000, 13, false, theme.ruleColor))
                }
            }
            "table" -> {
                shapes.append(pptxTextShape(2, slide.eyebrow, 650000, 380000, 2000000, 260000, 11, true, theme.ruleColor))
                shapes.append(pptxTextShape(3, slide.title, 650000, 560000, 10800000, 520000, 22, true, theme.accentColor))
                slide.tables.firstOrNull()?.let { table ->
                    val tableText = buildString {
                        val headers = table.headers.ifEmpty {
                            List(table.rows.maxOfOrNull { it.size } ?: 0) { "Column ${it + 1}" }
                        }
                        appendLine(headers.joinToString("     |     "))
                        table.rows.take(9).forEach { appendLine(it.joinToString("     |     ")) }
                        table.footnote?.takeIf { it.isNotBlank() }?.let { appendLine(); appendLine("Note: $it") }
                    }
                    shapes.append(pptxRectShape(4, 700000, 1550000, 10800000, 420000, theme.accentColor, null))
                    shapes.append(pptxRectShape(5, 700000, 1970000, 10800000, 4050000, theme.footerFillColor, theme.ruleColor))
                    shapes.append(pptxTextShape(6, tableText, 920000, 1690000, 10300000, 4150000, 14, false, Color.BLACK))
                }
            }
            else -> {
                shapes.append(pptxTextShape(2, slide.eyebrow, 650000, 380000, 2000000, 260000, 11, true, theme.ruleColor))
                shapes.append(pptxTextShape(3, slide.title, 650000, 560000, 10800000, 520000, 22, true, theme.accentColor))
                slide.bodyLines.take(7).forEachIndexed { index, line ->
                    val y = 1650000 + (index * 610000)
                    shapes.append(pptxRectShape(20 + index, 820000, y, 10350000, 460000, if (index % 2 == 0) theme.footerFillColor else Color.WHITE, theme.headerFillColor))
                    shapes.append(pptxTextShape(40 + index, line.take(190), 1050000, y + 90000, 9900000, 300000, 15, index == 0, if (index == 0) theme.accentColor else Color.BLACK))
                }
            }
        }
        return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>$shapes</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>"""
    }

    private fun pptxTextShape(id: Int, text: String, x: Int, y: Int, cx: Int, cy: Int, size: Int, bold: Boolean, color: Int): String {
        val paragraphs = text.lines().ifEmpty { listOf("") }.joinToString("") { line ->
            val runs = parseBoldMarkdownRuns(line).ifEmpty { listOf(ExportTextRun("", false)) }
            val xmlRuns = runs.joinToString("") { run ->
                val runBold = bold || run.bold
                """<a:r><a:rPr lang="en-US" sz="${size * 100}"${if (runBold) """ b="1"""" else ""}><a:solidFill><a:srgbClr val="${officeColor(color)}"/></a:solidFill></a:rPr><a:t>${pptxText(run.text)}</a:t></a:r>"""
            }
            "<a:p>$xmlRuns</a:p>"
        }
        return """<p:sp><p:nvSpPr><p:cNvPr id="$id" name="Text $id"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="$x" y="$y"/><a:ext cx="$cx" cy="$cy"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr><p:txBody><a:bodyPr wrap="square"/><a:lstStyle/>$paragraphs</p:txBody></p:sp>"""
    }

    private fun pptxDesignBlocks(theme: PdfThemeStyle, layout: String): String {
        return buildString {
            append(pptxRectShape(90, 0, 0, 12192000, 6858000, Color.WHITE, null))
            when (theme.pageChromeLayout) {
                PageChromeLayout.FORMAL_FRAME -> {
                    if (layout == "cover") {
                        append(pptxRectShape(95, 0, 0, 470000, 6858000, theme.accentColor, null))
                        append(pptxRectShape(96, 9400000, 0, 2792000, 6858000, theme.footerFillColor, null))
                    } else {
                        append(pptxRectShape(91, 0, 0, 12192000, 300000, theme.accentColor, null))
                    }
                    append(pptxRectShape(92, 0, 6500000, 12192000, 358000, theme.footerFillColor, null))
                    append(pptxRectShape(93, 550000, 1110000, 11100000, 45000, theme.ruleColor, null))
                    append(pptxRectShape(94, 550000, 1165000, 1800000, 110000, theme.headerFillColor, null))
                }
                PageChromeLayout.CLINICAL_REPORT -> {
                    append(pptxRectShape(91, 0, 0, 210000, 6858000, theme.accentColor, null))
                    append(pptxRectShape(92, 210000, 0, 11982000, 540000, theme.footerFillColor, null))
                    append(pptxRectShape(93, 650000, 1120000, 10550000, 45000, theme.ruleColor, null))
                }
                PageChromeLayout.JOURNAL_ARTICLE -> {
                    append(pptxRectShape(91, 650000, 980000, 10880000, 26000, theme.ruleColor, null))
                    append(pptxRectShape(92, 650000, 6150000, 10880000, 26000, theme.ruleColor, null))
                }
                PageChromeLayout.PREMIUM_PRESENTATION -> {
                    append(pptxRectShape(91, 0, 0, 12192000, 680000, theme.accentColor, null))
                    append(pptxRectShape(92, 9900000, 0, 2292000, 6858000, theme.footerFillColor, null))
                    append(pptxRectShape(93, 650000, 1120000, 1900000, 105000, theme.headerFillColor, null))
                }
                PageChromeLayout.OFFICIAL_BINDER -> {
                    append(pptxRectShape(91, 0, 0, 250000, 6858000, theme.accentColor, null))
                    append(pptxRectShape(92, 250000, 0, 11942000, 560000, theme.headerFillColor, null))
                    append(pptxRectShape(93, 620000, 1120000, 10850000, 62000, theme.ruleColor, null))
                    append(pptxRectShape(94, 620000, 6120000, 10850000, 42000, theme.ruleColor, null))
                }
                PageChromeLayout.MINIMAL_JOURNAL -> {
                    append(pptxRectShape(91, 760000, 960000, 10680000, 18000, theme.ruleColor, null))
                    append(pptxRectShape(92, 760000, 6180000, 10680000, 18000, theme.ruleColor, null))
                    append(pptxRectShape(93, 760000, 1120000, 1180000, 58000, theme.softColor, null))
                }
                PageChromeLayout.ACADEMIC_INSET -> {
                    append(pptxRectShape(91, 520000, 420000, 11152000, 6020000, theme.softColor, null))
                    append(pptxRectShape(92, 700000, 620000, 10790000, 5620000, Color.WHITE, theme.accentColor))
                    append(pptxRectShape(93, 920000, 1150000, 10100000, 76000, theme.headerFillColor, null))
                }
                PageChromeLayout.DASHBOARD_RAIL -> {
                    append(pptxRectShape(91, 0, 0, 640000, 6858000, theme.accentColor, null))
                    append(pptxRectShape(92, 640000, 0, 11552000, 780000, theme.footerFillColor, null))
                    append(pptxRectShape(93, 880000, 1160000, 2800000, 86000, theme.headerFillColor, null))
                }
                PageChromeLayout.DEFENSE_PRESENTATION -> {
                    append(pptxRectShape(91, 0, 0, 12192000, 760000, theme.accentColor, null))
                    append(pptxRectShape(92, 10100000, 0, 2092000, 6858000, theme.footerFillColor, null))
                    append(pptxRectShape(93, 700000, 1160000, 2500000, 90000, theme.headerFillColor, null))
                    append(pptxRectShape(94, 700000, 6200000, 9000000, 36000, theme.ruleColor, null))
                }
                PageChromeLayout.EDITORIAL_FOLIO -> {
                    append(pptxRectShape(91, 820000, 0, 340000, 6858000, theme.footerFillColor, null))
                    append(pptxRectShape(92, 820000, 970000, 2200000, 70000, theme.accentColor, null))
                    append(pptxRectShape(93, 820000, 6120000, 8400000, 26000, theme.ruleColor, null))
                    append(pptxRectShape(94, 8600000, 1280000, 1600000, 900000, theme.softColor, null))
                }
                PageChromeLayout.ATLAS_PLATE -> {
                    append(pptxRectShape(91, 0, 0, 12192000, 620000, theme.accentColor, null))
                    append(pptxRectShape(92, 760000, 1120000, 10670000, 4500000, theme.footerFillColor, theme.accentColor))
                    append(pptxRectShape(93, 1120000, 1520000, 9600000, 45000, theme.ruleColor, null))
                    append(pptxRectShape(94, 1120000, 5000000, 2600000, 340000, theme.headerFillColor, null))
                }
                PageChromeLayout.EXECUTIVE_SUMMARY -> {
                    append(pptxRectShape(91, 0, 0, 12192000, 820000, theme.accentColor, null))
                    append(pptxRectShape(92, 820000, 1340000, 10480000, 760000, theme.softColor, null))
                    append(pptxRectShape(93, 820000, 1340000, 140000, 760000, theme.accentColor, null))
                    append(pptxRectShape(94, 10100000, 1040000, 250000, 5150000, theme.ruleColor, null))
                }
                PageChromeLayout.MONOGRAPH_CLASSIC -> {
                    append(pptxRectShape(91, 450000, 320000, 11290000, 6218000, theme.softColor, null))
                    append(pptxRectShape(92, 720000, 560000, 10750000, 5738000, Color.WHITE, null))
                    append(pptxRectShape(93, 1400000, 1100000, 9400000, 26000, theme.ruleColor, null))
                    append(pptxRectShape(94, 1400000, 5920000, 9400000, 26000, theme.ruleColor, null))
                    append(pptxRectShape(95, 5550000, 880000, 1080000, 70000, theme.accentColor, null))
                }
                PageChromeLayout.CASEBOOK_FILE -> {
                    append(pptxRectShape(91, 0, 0, 12192000, 6858000, theme.footerFillColor, null))
                    append(pptxRectShape(92, 650000, 430000, 10900000, 6000000, Color.WHITE, null))
                    append(pptxRectShape(93, 0, 0, 12192000, 760000, theme.accentColor, null))
                    append(pptxRectShape(94, 10100000, 760000, 1300000, 360000, theme.headerFillColor, null))
                    append(pptxRectShape(95, 820000, 1180000, 10300000, 36000, theme.ruleColor, null))
                }
                PageChromeLayout.LAB_NOTEBOOK -> {
                    append(pptxRectShape(91, 0, 0, 12192000, 6858000, Color.WHITE, null))
                    append(pptxRectShape(92, 820000, 690000, 10550000, 390000, theme.accentColor, null))
                    append(pptxRectShape(93, 820000, 1260000, 1900000, 90000, theme.headerFillColor, null))
                    append(pptxRectShape(94, 820000, 6150000, 10550000, 26000, theme.ruleColor, null))
                }
                PageChromeLayout.SYSTEMATIC_REVIEW -> {
                    append(pptxRectShape(91, 760000, 820000, 10680000, 26000, theme.ruleColor, null))
                    append(pptxRectShape(92, 6090000, 1200000, 24000, 4900000, theme.ruleColor, null))
                    append(pptxRectShape(93, 760000, 1240000, 10680000, 90000, theme.softColor, null))
                    append(pptxRectShape(94, 760000, 1120000, 1100000, 65000, theme.accentColor, null))
                }
                PageChromeLayout.SIGNATURE_PORTFOLIO -> {
                    append(pptxRectShape(91, 0, 0, 12192000, 6858000, theme.footerFillColor, null))
                    append(pptxRectShape(92, 620000, 480000, 10950000, 5900000, Color.WHITE, theme.ruleColor))
                    append(pptxRectShape(93, 620000, 480000, 340000, 1180000, theme.accentColor, null))
                    append(pptxRectShape(94, 1250000, 980000, 9200000, 90000, theme.headerFillColor, null))
                }
            }
        }
    }

    private fun pptxRectShape(id: Int, x: Int, y: Int, cx: Int, cy: Int, fill: Int, stroke: Int?): String {
        val line = stroke?.let { """<a:ln w="9525"><a:solidFill><a:srgbClr val="${officeColor(it)}"/></a:solidFill></a:ln>""" } ?: "<a:ln><a:noFill/></a:ln>"
        return """<p:sp><p:nvSpPr><p:cNvPr id="$id" name="Block $id"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="$x" y="$y"/><a:ext cx="$cx" cy="$cy"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:solidFill><a:srgbClr val="${officeColor(fill)}"/></a:solidFill>$line</p:spPr><p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody></p:sp>"""
    }

    private fun pptxPictureShape(id: Int, relId: String, x: Int, y: Int, cx: Int, cy: Int): String =
        """<p:pic><p:nvPicPr><p:cNvPr id="$id" name="Image $id"/><p:cNvPicPr/><p:nvPr/></p:nvPicPr><p:blipFill><a:blip r:embed="$relId"/><a:stretch><a:fillRect/></a:stretch></p:blipFill><p:spPr><a:xfrm><a:off x="$x" y="$y"/><a:ext cx="$cx" cy="$cy"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>"""

    private fun pptxSlideMaster(): String =
        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill><a:effectLst/></p:bgPr></p:bg><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld><p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/><p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rIdLayout1"/></p:sldLayoutIdLst><p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles></p:sldMaster>"""

    private fun pptxSlideMasterRels(): String =
        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rIdLayout1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/><Relationship Id="rIdTheme1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/></Relationships>"""

    private fun pptxSlideLayout(): String =
        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1"><p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>"""

    private fun pptxSlideLayoutRels(): String =
        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rIdMaster1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/></Relationships>"""

    private fun pptxTheme(theme: PdfThemeStyle): String =
        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="EduLabs ${officeColor(theme.accentColor)}"><a:themeElements><a:clrScheme name="EduLabs"><a:dk1><a:srgbClr val="${officeColor(theme.accentColor)}"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="${officeColor(theme.ruleColor)}"/></a:dk2><a:lt2><a:srgbClr val="${officeColor(theme.footerFillColor)}"/></a:lt2><a:accent1><a:srgbClr val="${officeColor(theme.accentColor)}"/></a:accent1><a:accent2><a:srgbClr val="${officeColor(theme.headerFillColor)}"/></a:accent2><a:accent3><a:srgbClr val="${officeColor(theme.ruleColor)}"/></a:accent3><a:accent4><a:srgbClr val="${officeColor(theme.softColor)}"/></a:accent4><a:accent5><a:srgbClr val="334155"/></a:accent5><a:accent6><a:srgbClr val="64748B"/></a:accent6><a:hlink><a:srgbClr val="${officeColor(theme.accentColor)}"/></a:hlink><a:folHlink><a:srgbClr val="${officeColor(theme.ruleColor)}"/></a:folHlink></a:clrScheme><a:fontScheme name="EduLabs"><a:majorFont><a:latin typeface="Arial"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont><a:minorFont><a:latin typeface="Arial"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont></a:fontScheme><a:fmtScheme name="EduLabs"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:gradFill rotWithShape="1"><a:gsLst><a:gs pos="0"><a:schemeClr val="phClr"/></a:gs><a:gs pos="100000"><a:schemeClr val="phClr"/></a:gs></a:gsLst><a:lin ang="5400000" scaled="0"/></a:gradFill><a:gradFill rotWithShape="1"><a:gsLst><a:gs pos="0"><a:schemeClr val="phClr"/></a:gs><a:gs pos="100000"><a:schemeClr val="phClr"/></a:gs></a:gsLst><a:lin ang="5400000" scaled="0"/></a:gradFill></a:fillStyleLst><a:lnStyleLst><a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln><a:ln w="25400"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln><a:ln w="38100"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme></a:themeElements><a:objectDefaults/><a:extraClrSchemeLst/></a:theme>"""

    private fun resolveExportFigure(figure: FigureJson, resolvedFigures: List<FigureJson>): FigureJson {
        val normalizedNumber = figure.figureNumber.trim()
        val normalizedTitle = normalizeReferenceText(figure.title)
        val match = resolvedFigures.firstOrNull { candidate ->
            candidate.figureNumber.trim().isNotBlank() &&
                candidate.figureNumber.trim() == normalizedNumber
        } ?: resolvedFigures.firstOrNull { candidate ->
            normalizedTitle.isNotBlank() && normalizeReferenceText(candidate.title) == normalizedTitle
        }

        if (match == null) return figure

        return figure.copy(
            figureNumber = figure.figureNumber.ifBlank { match.figureNumber },
            title = figure.title.ifBlank { match.title },
            caption = figure.caption.ifBlank { match.caption },
            imageSearchQuery = figure.imageSearchQuery.ifBlank { match.imageSearchQuery },
            imageUrl = figure.imageUrl.ifBlank { match.imageUrl },
            sourceUrl = figure.sourceUrl.ifBlank { match.sourceUrl }
        )
    }

    suspend fun loadFigureBitmap(context: Context, source: String, searchQuery: String?): Bitmap? {
        val sourceBitmap = source
            .takeIf { it.isNotBlank() }
            ?.let { loadBitmapFromSource(context, it) }
        if (sourceBitmap != null) return sourceBitmap

        val searchedBitmap = searchQuery
            ?.takeIf { it.isNotBlank() }
            ?.let { loadBitmapFromSource(context, buildFigureImageSearchUrl(it)) }
        if (searchedBitmap != null) return searchedBitmap

        return searchQuery
            ?.takeIf { it.isNotBlank() }
            ?.let { createFigurePlaceholderBitmap(it) }
    }

    fun createFigurePlaceholderBitmap(query: String): Bitmap {
        val width = 1200
        val height = 760
        val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        val background = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.rgb(245, 248, 255)
            style = Paint.Style.FILL
        }
        val border = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.rgb(93, 134, 232)
            style = Paint.Style.STROKE
            strokeWidth = 6f
        }
        val titlePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.rgb(31, 41, 55)
            typeface = Typeface.create(Typeface.DEFAULT, Typeface.BOLD)
            textSize = 42f
        }
        val bodyPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.rgb(71, 85, 105)
            textSize = 30f
        }

        canvas.drawRect(0f, 0f, width.toFloat(), height.toFloat(), background)
        canvas.drawRoundRect(RectF(42f, 42f, width - 42f, height - 42f), 28f, 28f, border)
        canvas.drawText("Figure image pending", 86f, 150f, titlePaint)

        val lines = wrapPlainText("Search query: $query", bodyPaint, width - 172f).take(5)
        var y = 230f
        lines.forEach { line ->
            canvas.drawText(line, 86f, y, bodyPaint)
            y += 42f
        }
        canvas.drawText("Add or resolve an image URL to replace this placeholder.", 86f, height - 110f, bodyPaint)
        return bitmap
    }

    private fun wrapPlainText(text: String, paint: Paint, maxWidth: Float): List<String> {
        val words = text.split(Regex("\\s+")).filter { it.isNotBlank() }
        val lines = mutableListOf<String>()
        var current = ""
        words.forEach { word ->
            val candidate = if (current.isBlank()) word else "$current $word"
            if (paint.measureText(candidate) <= maxWidth) {
                current = candidate
            } else {
                if (current.isNotBlank()) lines += current
                current = word
            }
        }
        if (current.isNotBlank()) lines += current
        return lines.ifEmpty { listOf(text.take(60)) }
    }

    suspend fun loadBitmapFromSource(context: Context, source: String): Bitmap? = withContext(Dispatchers.IO) {
        try {
            when {
                source.startsWith("content://", ignoreCase = true) -> {
                    val uri = Uri.parse(source)
                    context.contentResolver.openInputStream(uri)?.use { input ->
                        BitmapFactory.decodeStream(input)
                    }
                }

                source.startsWith("file://", ignoreCase = true) -> {
                    val uri = Uri.parse(source)
                    val filePath = uri.path ?: source.removePrefix("file://")
                    val file = java.io.File(filePath)
                    if (file.exists()) BitmapFactory.decodeFile(file.absolutePath) else null
                }

                source.startsWith("/") -> {
                    BitmapFactory.decodeFile(source)
                }

                source.startsWith("http://", ignoreCase = true) || source.startsWith("https://", ignoreCase = true) -> {
                    val request = Request.Builder()
                        .url(source)
                        .header("User-Agent", "EduLabsRTM/1.0")
                        .build()
                    rawClient.newCall(request).execute().use { response ->
                        if (!response.isSuccessful) return@withContext null
                        val contentType = response.header("Content-Type").orEmpty()
                        if (contentType.isNotBlank() && !contentType.startsWith("image/", ignoreCase = true)) {
                            return@withContext null
                        }
                        val bytes = response.body?.bytes() ?: return@withContext null
                        BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                    }
                }

                else -> {
                    val file = java.io.File(source)
                    if (file.exists()) BitmapFactory.decodeFile(file.absolutePath) else null
                }
            }
        } catch (_: Exception) {
            null
        }
    }

    private suspend fun loadCollegeLogoBitmap(context: Context, selectedLogoUri: String): Bitmap? {
        val selected = selectedLogoUri
            .takeIf { it.isNotBlank() }
            ?.let { loadBitmapFromSource(context, it) }

        if (selected != null) return selected

        return withContext(Dispatchers.IO) {
            runCatching {
                BitmapFactory.decodeResource(context.resources, R.drawable.medigyaan_logo)
                    ?: BitmapFactory.decodeResource(context.resources, R.mipmap.ic_launcher)
            }.getOrNull()
        }
    }

    private fun buildFigureImageSearchUrl(query: String): String {
        val encoded = java.net.URLEncoder.encode(query.ifBlank { "medical thesis diagram" }, "UTF-8")
        return "https://source.unsplash.com/featured/1200x800/?$encoded"
    }

    private suspend fun renderSpecialFormChapterBitmap(context: Context, logoBitmap: Bitmap?, theme: PdfThemeStyle, chapter: Chapter): Bitmap? {
        val chapterName = chapter.name.trim().lowercase()
        val isHindiConsent = chapterName == "patient consent form (hindi)"

        return when (chapterName) {
            "title" -> {
                val parsed = runCatching {
                    gson.fromJson(extractJsonBlock(chapter.rawJson), TitlePageJson::class.java)
                }.getOrNull()
                val visibleText = extractVisibleText(chapter.rawJson).ifBlank { chapter.content }
                val titleData = parsed?.let {
                    if (it.title.isBlank() && it.author.isBlank() && it.guide.isBlank() && it.institution.isBlank() && it.department.isBlank() && it.degree.isBlank() && it.year.isBlank()) null else it
                } ?: if (visibleText.isNotBlank()) {
                    TitlePageJson(title = visibleText)
                } else {
                    buildTitlePageDataFromVariables()
                }
                renderTitlePageBitmap(context, logoBitmap, theme, titleData, chapter.name)
            }

            "proforma" -> {
                val parsed = runCatching {
                    gson.fromJson(extractJsonBlock(chapter.rawJson), ProformaJson::class.java)
                }.getOrElse { ProformaJson() }
                val visibleText = extractVisibleText(chapter.rawJson).ifBlank { chapter.content }
                val hasStructuredText = listOf(
                    parsed.patientName,
                    parsed.age,
                    parsed.sex,
                    parsed.opdIpNo,
                    parsed.address,
                    parsed.history,
                    parsed.examination,
                    parsed.investigations,
                    parsed.diagnosis
                ).any { it.isNotBlank() }
                val proforma = if (hasStructuredText) {
                    parsed.copy(history = parsed.history.ifBlank { visibleText })
                } else {
                    parsed.copy(history = visibleText.ifBlank { "Proforma details" })
                }
                renderProformaBitmap(proforma, chapter.name, logoBitmap, theme)
            }

            "certificate" -> {
                val parsed = runCatching {
                    gson.fromJson(extractJsonBlock(chapter.rawJson), CertificateJson::class.java)
                }.getOrNull()
                val visibleText = extractVisibleText(chapter.rawJson)
                val certificate = parsed?.copy(
                    body = parsed.body.ifBlank { visibleText.ifBlank { parsed.body } }
                ) ?: CertificateJson(body = visibleText.ifBlank { "CERTIFICATE" })
                renderCertificateBitmap(certificate, chapter.name, logoBitmap, theme)
            }

            "declaration" -> {
                val parsed = runCatching {
                    gson.fromJson(extractJsonBlock(chapter.rawJson), DeclarationJson::class.java)
                }.getOrNull()
                val visibleText = extractVisibleText(chapter.rawJson)
                val declaration = parsed?.copy(
                    statement = parsed.statement.ifBlank { visibleText.ifBlank { parsed.statement } }
                ) ?: DeclarationJson(statement = visibleText.ifBlank { "I hereby declare..." })
                renderDeclarationBitmap(declaration, chapter.name, logoBitmap, theme)
            }

            "acknowledgements" -> {
                val parsed = runCatching {
                    gson.fromJson(extractJsonBlock(chapter.rawJson), AcknowledgementsJson::class.java)
                }.getOrNull()
                val visibleText = extractVisibleText(chapter.rawJson)
                val acknowledgements = parsed?.acknowledgements.orEmpty().ifEmpty {
                    listOfNotNull(visibleText.takeIf { it.isNotBlank() })
                }
                renderAcknowledgementsBitmap(AcknowledgementsJson(acknowledgements), chapter.name, logoBitmap, theme)
            }

            "patient consent form (english)", "patient consent form (hindi)" -> {
                val parsed = runCatching {
                    gson.fromJson(extractJsonBlock(chapter.rawJson), ConsentFormJson::class.java)
                }.getOrElse { ConsentFormJson(title = chapter.name.uppercase()) }
                val visibleText = extractVisibleText(chapter.rawJson).ifBlank { chapter.content }
                val hasStructuredText = listOf(
                    parsed.introduction,
                    parsed.procedure,
                    parsed.risks,
                    parsed.benefits,
                    parsed.confidentiality
                ).any { it.isNotBlank() }
                val consent = if (hasStructuredText) {
                    parsed.copy(
                        title = parsed.title.ifBlank { chapter.name.uppercase() },
                        introduction = parsed.introduction.ifBlank { visibleText }
                    )
                } else {
                    parsed.copy(
                        title = parsed.title.ifBlank { chapter.name.uppercase() },
                        introduction = visibleText.ifBlank { chapter.name.uppercase() }
                    )
                }
                renderConsentBitmap(consent, chapter.name, isHindiConsent, logoBitmap, theme)
            }

            else -> null
        }
    }

    private suspend fun buildTitlePageDataFromVariables(): TitlePageJson {
        val variables = _uiState.value.variables
        fun pick(vararg names: String, fallback: String = ""): String {
            return variables.firstOrNull { variable ->
                names.any { variable.name.equals(it, ignoreCase = true) || variable.name.contains(it, ignoreCase = true) }
            }?.value?.trim().orEmpty().ifBlank { fallback }
        }

        return TitlePageJson(
            title = pick("Title", fallback = "RESEARCH THESIS"),
            subtitle = pick("Subtitle"),
            author = pick("Student Name", "Author"),
            guide = pick("Guide"),
            coGuide = pick("Co-guide", "Co Guide").ifBlank { null },
            institution = pick("Institution", fallback = "INSTITUTION NAME"),
            department = pick("Department"),
            degree = pick("Degree", fallback = "Thesis"),
            year = pick("Year", fallback = "")
        )
    }

    private suspend fun renderTitlePageBitmap(context: Context, logoBitmap: Bitmap?, theme: PdfThemeStyle, titlePage: TitlePageJson, chapterTitle: String): Bitmap {
        val width = 1240
        val height = 1754
        val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        canvas.drawColor(Color.WHITE)

        val borderPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = theme.accentColor
            style = Paint.Style.STROKE
            strokeWidth = 4f
        }
        val titlePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = theme.accentColor
            textSize = when (theme.pageChromeLayout) {
                PageChromeLayout.JOURNAL_ARTICLE,
                PageChromeLayout.MINIMAL_JOURNAL,
                PageChromeLayout.EDITORIAL_FOLIO,
                PageChromeLayout.MONOGRAPH_CLASSIC,
                PageChromeLayout.SYSTEMATIC_REVIEW -> 46f
                PageChromeLayout.ATLAS_PLATE,
                PageChromeLayout.EXECUTIVE_SUMMARY,
                PageChromeLayout.CASEBOOK_FILE,
                PageChromeLayout.SIGNATURE_PORTFOLIO -> 52f
                else -> 50f
            }
            typeface = theme.androidTypeface(DocxTextRole.TITLE)
            textAlign = Paint.Align.CENTER
        }
        val subtitlePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = theme.accentColor
            textSize = when (theme.pageChromeLayout) {
                PageChromeLayout.JOURNAL_ARTICLE,
                PageChromeLayout.MINIMAL_JOURNAL,
                PageChromeLayout.EDITORIAL_FOLIO,
                PageChromeLayout.MONOGRAPH_CLASSIC,
                PageChromeLayout.SYSTEMATIC_REVIEW -> 22f
                else -> 24f
            }
            typeface = theme.androidTypeface(DocxTextRole.SECTION)
            textAlign = Paint.Align.CENTER
        }
        val bodyPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.BLACK
            textSize = when (theme.pageChromeLayout) {
                PageChromeLayout.JOURNAL_ARTICLE,
                PageChromeLayout.MINIMAL_JOURNAL,
                PageChromeLayout.EDITORIAL_FOLIO,
                PageChromeLayout.MONOGRAPH_CLASSIC,
                PageChromeLayout.SYSTEMATIC_REVIEW -> 24f
                else -> 26f
            }
            typeface = theme.androidTypeface(DocxTextRole.BODY)
            textAlign = Paint.Align.CENTER
        }
        val labelPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = theme.accentColor
            textSize = when (theme.pageChromeLayout) {
                PageChromeLayout.JOURNAL_ARTICLE,
                PageChromeLayout.MINIMAL_JOURNAL,
                PageChromeLayout.EDITORIAL_FOLIO,
                PageChromeLayout.MONOGRAPH_CLASSIC,
                PageChromeLayout.SYSTEMATIC_REVIEW -> 22f
                else -> 24f
            }
            typeface = theme.androidTypeface(DocxTextRole.META)
            textAlign = Paint.Align.CENTER
        }
        val rulePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = theme.ruleColor
            style = Paint.Style.STROKE
            strokeWidth = 2f
        }
        val bannerPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = theme.headerFillColor
            style = Paint.Style.FILL
        }

        fun wrapCanvasText(text: String, paint: Paint, maxWidth: Float): List<String> {
            val normalized = text.replace("\r", "").trim()
            if (normalized.isBlank()) return emptyList()

            val lines = mutableListOf<String>()
            normalized.split('\n').forEachIndexed { index, paragraph ->
                val words = paragraph.trim().split(Regex("\\s+")).filter { it.isNotBlank() }
                if (words.isEmpty()) {
                    if (index < normalized.lineSequence().count() - 1) lines += ""
                    return@forEachIndexed
                }

                var current = StringBuilder()
                fun flush() {
                    if (current.isNotBlank()) {
                        lines += current.toString().trim()
                        current = StringBuilder()
                    }
                }

                for (word in words) {
                    val candidate = if (current.isEmpty()) word else "${current} $word"
                    if (paint.measureText(candidate) <= maxWidth) {
                        current = StringBuilder(candidate)
                    } else {
                        flush()
                        current = StringBuilder(word)
                    }
                }
                flush()
            }

            return lines.ifEmpty { listOf(normalized) }
        }

        fun drawCenteredWrappedText(
            text: String,
            paint: Paint,
            maxWidth: Float,
            startY: Float,
            lineGap: Float = 12f
        ) {
            val lines = wrapCanvasText(text, paint, maxWidth)
            val lineHeight = (paint.fontMetrics.descent - paint.fontMetrics.ascent) + lineGap
            var y = startY
            lines.forEach { line ->
                canvas.drawText(line, width / 2f, y, paint)
                y += lineHeight
            }
        }

        when (theme.titlePageLayout) {
            TitlePageLayout.LOGO_TOP_OFFICIAL -> {
                canvas.drawRect(0f, 0f, width.toFloat(), 170f, bannerPaint)
                canvas.drawRect(0f, (height - 90).toFloat(), width.toFloat(), height.toFloat(), bannerPaint)
                canvas.drawRect(54f, 54f, (width - 54).toFloat(), (height - 54).toFloat(), borderPaint)
                logoBitmap?.let {
                    val targetSize = 128
                    val scaled = Bitmap.createScaledBitmap(it, targetSize, targetSize, true)
                    canvas.drawBitmap(scaled, 74f, 42f, null)
                    if (scaled != it) scaled.recycle()
                }
                subtitlePaint.textAlign = Paint.Align.LEFT
                labelPaint.textAlign = Paint.Align.LEFT
                bodyPaint.textAlign = Paint.Align.LEFT
                canvas.drawText(titlePage.institution.ifBlank { chapterTitle }.uppercase(), 230f, 92f, labelPaint)
                canvas.drawText(titlePage.department.ifBlank { "Department" }, 230f, 132f, subtitlePaint)
                var y = 330f
                titlePaint.textAlign = Paint.Align.LEFT
                val titleText = titlePage.title.ifBlank { "RESEARCH THESIS" }.uppercase()
                wrapCanvasText(titleText, titlePaint, width - 190f).take(5).forEach {
                    canvas.drawText(it, 84f, y, titlePaint)
                    y += 62f
                }
                y += 80f
                canvas.drawText("Submitted by", 84f, y, labelPaint)
                y += 44f
                canvas.drawText(titlePage.author.ifBlank { "Candidate Name" }, 84f, y, bodyPaint)
                y += 96f
                canvas.drawText("Under the guidance of", 84f, y, labelPaint)
                y += 44f
                canvas.drawText(titlePage.guide.ifBlank { "Guide Name" }, 84f, y, bodyPaint)
                y = 1450f
                canvas.drawText(titlePage.degree.ifBlank { "Thesis" }, 84f, y, labelPaint)
                canvas.drawText(titlePage.year.ifBlank { "" }, width - 250f, y, bodyPaint)
                return bitmap
            }
            TitlePageLayout.JOURNAL_MANUSCRIPT -> {
                canvas.drawRect(76f, 86f, (width - 76).toFloat(), 94f, rulePaint)
                canvas.drawRect(76f, (height - 110).toFloat(), (width - 76).toFloat(), (height - 102).toFloat(), rulePaint)
                var y = 250f
                titlePaint.textSize = 44f
                val titleText = titlePage.title.ifBlank { "Research Thesis" }
                drawCenteredWrappedText(titleText, titlePaint, width - 260f, y, lineGap = 12f)
                y += (wrapCanvasText(titleText, titlePaint, width - 260f).size * 68f) + 40f
                drawCenteredWrappedText(titlePage.author.ifBlank { "Candidate Name" }, bodyPaint, width - 280f, y)
                y += 82f
                drawCenteredWrappedText(titlePage.institution.ifBlank { chapterTitle }, subtitlePaint, width - 280f, y)
                y += 60f
                drawCenteredWrappedText(titlePage.department.ifBlank { "" }, subtitlePaint, width - 280f, y)
                y += 150f
                val abstractBox = RectF(150f, y, (width - 150).toFloat(), y + 310f)
                canvas.drawRect(abstractBox, rulePaint)
                labelPaint.textAlign = Paint.Align.LEFT
                bodyPaint.textAlign = Paint.Align.LEFT
                canvas.drawText("MANUSCRIPT DETAILS", abstractBox.left + 28f, abstractBox.top + 54f, labelPaint)
                canvas.drawText("Guide: ${titlePage.guide.ifBlank { "Guide Name" }}", abstractBox.left + 28f, abstractBox.top + 106f, bodyPaint)
                canvas.drawText("Degree: ${titlePage.degree.ifBlank { "Thesis" }}", abstractBox.left + 28f, abstractBox.top + 154f, bodyPaint)
                canvas.drawText("Year: ${titlePage.year.ifBlank { "" }}", abstractBox.left + 28f, abstractBox.top + 202f, bodyPaint)
                return bitmap
            }
            TitlePageLayout.MODERN_COVER -> {
                canvas.drawRect(0f, 0f, width.toFloat(), height.toFloat(), Paint(Paint.ANTI_ALIAS_FLAG).apply {
                    color = theme.footerFillColor
                    style = Paint.Style.FILL
                })
                canvas.drawRect(0f, 0f, width.toFloat(), 360f, Paint(Paint.ANTI_ALIAS_FLAG).apply {
                    color = theme.accentColor
                    style = Paint.Style.FILL
                })
                canvas.drawRect((width - 280).toFloat(), 0f, width.toFloat(), 360f, bannerPaint)
                logoBitmap?.let {
                    val targetSize = 128
                    val scaled = Bitmap.createScaledBitmap(it, targetSize, targetSize, true)
                    canvas.drawBitmap(scaled, (width - 190).toFloat(), 74f, null)
                    if (scaled != it) scaled.recycle()
                }
                subtitlePaint.color = Color.WHITE
                labelPaint.color = Color.WHITE
                labelPaint.textAlign = Paint.Align.LEFT
                subtitlePaint.textAlign = Paint.Align.LEFT
                canvas.drawText(titlePage.institution.ifBlank { chapterTitle }.uppercase(), 84f, 118f, labelPaint)
                canvas.drawText(titlePage.department.ifBlank { "" }, 84f, 160f, subtitlePaint)
                titlePaint.textAlign = Paint.Align.LEFT
                titlePaint.textSize = 52f
                var y = 520f
                wrapCanvasText(titlePage.title.ifBlank { "RESEARCH THESIS" }.uppercase(), titlePaint, width - 170f).take(5).forEach {
                    canvas.drawText(it, 84f, y, titlePaint)
                    y += 70f
                }
                y += 130f
                labelPaint.color = theme.accentColor
                bodyPaint.textAlign = Paint.Align.LEFT
                canvas.drawText("Candidate", 84f, y, labelPaint)
                y += 48f
                canvas.drawText(titlePage.author.ifBlank { "Candidate Name" }, 84f, y, bodyPaint)
                y += 86f
                canvas.drawText("Guide", 84f, y, labelPaint)
                y += 48f
                canvas.drawText(titlePage.guide.ifBlank { "Guide Name" }, 84f, y, bodyPaint)
                canvas.drawRect(84f, 1465f, (width - 84).toFloat(), 1472f, bannerPaint)
                canvas.drawText(titlePage.degree.ifBlank { "Thesis" }, 84f, 1536f, bodyPaint)
                canvas.drawText(titlePage.year.ifBlank { "" }, width - 210f, 1536f, bodyPaint)
                return bitmap
            }
            TitlePageLayout.CENTERED_UNIVERSITY -> Unit
        }

        canvas.drawRect(36f, 36f, (width - 36).toFloat(), (height - 36).toFloat(), borderPaint)
        canvas.drawRect(52f, 52f, (width - 52).toFloat(), (height - 52).toFloat(), rulePaint)
        canvas.drawRect(36f, 36f, (width - 36).toFloat(), 96f, bannerPaint)
        canvas.drawRect(36f, (height - 96f), (width - 36).toFloat(), (height - 36).toFloat(), bannerPaint)

        logoBitmap?.let {
            val targetSize = 140
            val scaled = Bitmap.createScaledBitmap(it, targetSize, targetSize, true)
            val left = width - 120f - targetSize
            canvas.drawBitmap(scaled, left, 70f, null)
            if (scaled != it) scaled.recycle()
        }

        var y = 300f
        drawCenteredWrappedText(
            titlePage.institution.ifBlank { chapterTitle }.uppercase(),
            subtitlePaint,
            width - 240f,
            y
        )
        y += 42f
        drawCenteredWrappedText(
            titlePage.department.ifBlank { "" }.uppercase(),
            labelPaint,
            width - 240f,
            y
        )
        y += 72f
        val titleText = titlePage.title.ifBlank { "RESEARCH THESIS" }.uppercase()
        val titlePaintMinSize = 34f
        while (titlePaint.textSize > titlePaintMinSize && wrapCanvasText(titleText, titlePaint, width - 220f).size > 3) {
            titlePaint.textSize -= 2f
        }
        drawCenteredWrappedText(titleText, titlePaint, width - 220f, y, lineGap = 10f)
        titlePage.subtitle?.takeIf { it.isNotBlank() }?.let {
            y += 46f
            drawCenteredWrappedText(it, subtitlePaint, width - 240f, y)
        }

        y = 760f
        canvas.drawText("SUBMITTED BY", width / 2f, y, labelPaint)
        y += 46f
        canvas.drawText(titlePage.author.ifBlank { "CANDIDATE NAME" }.uppercase(), width / 2f, y, bodyPaint)

        y += 96f
        canvas.drawText("UNDER THE GUIDANCE OF", width / 2f, y, labelPaint)
        y += 42f
        canvas.drawText(titlePage.guide.ifBlank { "GUIDE NAME" }, width / 2f, y, bodyPaint)
        titlePage.coGuide?.takeIf { it.isNotBlank() }?.let {
            y += 54f
            canvas.drawText("CO-GUIDE", width / 2f, y, labelPaint)
            y += 40f
            canvas.drawText(it, width / 2f, y, bodyPaint)
        }

        y = 1360f
        canvas.drawText(titlePage.degree.ifBlank { "THESIS" }.uppercase(), width / 2f, y, labelPaint)
        y += 46f
        canvas.drawText(titlePage.year.ifBlank { "" }, width / 2f, y, bodyPaint)

        return bitmap
    }

    private fun renderProformaBitmap(proforma: ProformaJson, chapterTitle: String, logoBitmap: Bitmap?, theme: PdfThemeStyle): Bitmap {
        val width = 1240
        val height = 1754
        val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        canvas.drawColor(Color.WHITE)

        val borderPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = theme.accentColor
            style = Paint.Style.STROKE
            strokeWidth = 4f
        }
        val titlePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.BLACK
            textSize = 44f
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
            textAlign = Paint.Align.CENTER
        }
        val subtitlePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.BLACK
            textSize = 24f
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.NORMAL)
            textAlign = Paint.Align.CENTER
        }
        val labelPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.BLACK
            textSize = 26f
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
        }
        val valuePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.BLACK
            textSize = 24f
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.NORMAL)
        }
        val headingPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.BLACK
            textSize = 24f
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
        }
        val accentFillPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = theme.softColor
            style = Paint.Style.FILL
        }
        val bannerPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = theme.headerFillColor
            style = Paint.Style.FILL
        }

        canvas.drawRect(36f, 36f, (width - 36).toFloat(), (height - 36).toFloat(), borderPaint)
        logoBitmap?.let {
            val targetSize = 78
            val scaled = Bitmap.createScaledBitmap(it, targetSize, targetSize, true)
            canvas.drawBitmap(scaled, width - 120f - targetSize, 64f, null)
            if (scaled != it) scaled.recycle()
        }
        canvas.drawRect(36f, 36f, (width - 36).toFloat(), 98f, bannerPaint)
        canvas.drawRect(36f, (height - 96f), (width - 36).toFloat(), (height - 36).toFloat(), bannerPaint)
        canvas.drawText("PROFORMA", width / 2f, 110f, titlePaint)
        canvas.drawText(chapterTitle, width / 2f, 150f, subtitlePaint)

        var y = 190f

        fun drawField(label: String, value: String, boxHeight: Float = 112f, fullWidth: Boolean = true) {
            val left = 70f
            val right = (width - 70).toFloat()
            val boxBottom = y + boxHeight
            canvas.drawRoundRect(RectF(left, y, right, boxBottom), 16f, 16f, borderPaint)
            canvas.drawRect(left, y, right, y + 34f, accentFillPaint)
            canvas.drawText(label, left + 18f, y + 28f, headingPaint)
            drawWrappedText(canvas, value.ifBlank { " " }, left + 18f, y + 60f, right - left - 36f, valuePaint, 1.25f, boxBottom - 18f)
            y = boxBottom + 16f
        }

        drawField("Patient Name", proforma.patientName, 96f)

        val halfGap = 16f
        val boxWidth = (width - 70f * 2f - halfGap) / 2f
        fun drawSmallField(x: Float, label: String, value: String) {
            val boxHeight = 96f
            val boxBottom = y + boxHeight
            canvas.drawRoundRect(RectF(x, y, x + boxWidth, boxBottom), 16f, 16f, borderPaint)
            canvas.drawRect(x, y, x + boxWidth, y + 34f, accentFillPaint)
            canvas.drawText(label, x + 18f, y + 28f, headingPaint)
            drawWrappedText(canvas, value.ifBlank { " " }, x + 18f, y + 60f, boxWidth - 36f, valuePaint, 1.25f, boxBottom - 18f)
        }

        drawSmallField(70f, "Age", proforma.age)
        drawSmallField(70f + boxWidth + halfGap, "Sex", proforma.sex)
        y += 112f

        drawField("OPD/IP No", proforma.opdIpNo, 96f)
        drawField("Address", proforma.address, 120f)
        drawField("History", proforma.history, 190f)
        drawField("Examination", proforma.examination, 190f)
        drawField("Investigations", proforma.investigations, 180f)
        drawField("Diagnosis", proforma.diagnosis, 150f)

        return bitmap
    }

    private fun renderCertificateBitmap(certificate: CertificateJson, chapterTitle: String, logoBitmap: Bitmap?, theme: PdfThemeStyle): Bitmap {
        val width = 1240
        val height = 1754
        val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        canvas.drawColor(Color.WHITE)

        val borderPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = theme.accentColor
            style = Paint.Style.STROKE
            strokeWidth = 4f
        }
        val titlePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.BLACK
            textSize = 42f
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
            textAlign = Paint.Align.CENTER
        }
        val bodyPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.BLACK
            textSize = 24f
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.NORMAL)
            textAlign = Paint.Align.LEFT
        }
        val centerPaint = Paint(bodyPaint).apply { textAlign = Paint.Align.CENTER }
        val labelPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.BLACK
            textSize = 22f
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
        }
        val bannerPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = theme.headerFillColor
            style = Paint.Style.FILL
        }

        canvas.drawRect(36f, 36f, (width - 36).toFloat(), (height - 36).toFloat(), borderPaint)
        logoBitmap?.let {
            val targetSize = 78
            val scaled = Bitmap.createScaledBitmap(it, targetSize, targetSize, true)
            canvas.drawBitmap(scaled, width - 120f - targetSize, 64f, null)
            if (scaled != it) scaled.recycle()
        }
        canvas.drawRect(36f, 36f, (width - 36).toFloat(), 98f, bannerPaint)
        canvas.drawRect(36f, (height - 96f), (width - 36).toFloat(), (height - 36).toFloat(), bannerPaint)
        canvas.drawText(certificate.title.ifBlank { "CERTIFICATE" }, width / 2f, 110f, titlePaint)
        canvas.drawText(chapterTitle, width / 2f, 150f, centerPaint)

        var y = 240f
        val left = 70f
        val right = (width - 70).toFloat()
        canvas.drawRoundRect(RectF(left, y, right, y + 1020f), 18f, 18f, borderPaint)
        drawWrappedText(canvas, certificate.body.ifBlank { " " }, left + 20f, y + 54f, right - left - 40f, bodyPaint, 1.28f)

        y = 1390f
        canvas.drawText("Guide Signature", left, y, labelPaint)
        canvas.drawLine(left + 210f, y + 6f, width / 2f - 50f, y + 6f, borderPaint)
        canvas.drawText(certificate.guideSignature.ifBlank { "___________________" }, left + 210f, y + 6f, bodyPaint)

        y += 70f
        canvas.drawText("HOD Signature", left, y, labelPaint)
        canvas.drawLine(left + 210f, y + 6f, width / 2f - 50f, y + 6f, borderPaint)
        canvas.drawText(certificate.hodSignature.ifBlank { "___________________" }, left + 210f, y + 6f, bodyPaint)

        y += 70f
        canvas.drawText("Date", left, y, labelPaint)
        canvas.drawLine(left + 120f, y + 6f, width - 120f, y + 6f, borderPaint)
        canvas.drawText(certificate.date.ifBlank { "" }, left + 120f, y + 6f, bodyPaint)

        return bitmap
    }

    private fun renderDeclarationBitmap(declaration: DeclarationJson, chapterTitle: String, logoBitmap: Bitmap?, theme: PdfThemeStyle): Bitmap {
        val width = 1240
        val height = 1754
        val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        canvas.drawColor(Color.WHITE)

        val borderPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = theme.accentColor
            style = Paint.Style.STROKE
            strokeWidth = 4f
        }
        val titlePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.BLACK
            textSize = 42f
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
            textAlign = Paint.Align.CENTER
        }
        val bodyPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.BLACK
            textSize = 24f
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.NORMAL)
            textAlign = Paint.Align.LEFT
        }
        val centerPaint = Paint(bodyPaint).apply { textAlign = Paint.Align.CENTER }
        val labelPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.BLACK
            textSize = 22f
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
        }
        val bannerPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = theme.headerFillColor
            style = Paint.Style.FILL
        }

        canvas.drawRect(36f, 36f, (width - 36).toFloat(), (height - 36).toFloat(), borderPaint)
        logoBitmap?.let {
            val targetSize = 78
            val scaled = Bitmap.createScaledBitmap(it, targetSize, targetSize, true)
            canvas.drawBitmap(scaled, width - 120f - targetSize, 64f, null)
            if (scaled != it) scaled.recycle()
        }
        canvas.drawRect(36f, 36f, (width - 36).toFloat(), 98f, bannerPaint)
        canvas.drawRect(36f, (height - 96f), (width - 36).toFloat(), (height - 36).toFloat(), bannerPaint)
        canvas.drawText("DECLARATION", width / 2f, 110f, titlePaint)
        canvas.drawText(chapterTitle, width / 2f, 150f, centerPaint)

        var y = 240f
        val left = 70f
        val right = (width - 70).toFloat()
        canvas.drawRoundRect(RectF(left, y, right, y + 1040f), 18f, 18f, borderPaint)
        drawWrappedText(canvas, declaration.statement.ifBlank { "I hereby declare that..." }, left + 20f, y + 54f, right - left - 40f, bodyPaint, 1.28f)

        y = 1400f
        canvas.drawText(declaration.studentName.ifBlank { "STUDENT NAME" }, width / 2f, y, titlePaint)
        y += 68f
        canvas.drawText("Signature", left, y, labelPaint)
        canvas.drawLine(left + 180f, y + 6f, width - 120f, y + 6f, borderPaint)
        canvas.drawText(declaration.signature.ifBlank { "___________________" }, left + 180f, y + 6f, bodyPaint)
        y += 72f
        canvas.drawText("Date", left, y, labelPaint)
        canvas.drawLine(left + 120f, y + 6f, width - 120f, y + 6f, borderPaint)
        canvas.drawText(declaration.date.ifBlank { "" }, left + 120f, y + 6f, bodyPaint)

        return bitmap
    }

    private fun renderAcknowledgementsBitmap(acknowledgements: AcknowledgementsJson, chapterTitle: String, logoBitmap: Bitmap?, theme: PdfThemeStyle): Bitmap {
        val width = 1240
        val height = 1754
        val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        canvas.drawColor(Color.WHITE)

        val borderPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = theme.accentColor
            style = Paint.Style.STROKE
            strokeWidth = 4f
        }
        val titlePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.BLACK
            textSize = 42f
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
            textAlign = Paint.Align.CENTER
        }
        val bodyPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.BLACK
            textSize = 24f
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.NORMAL)
            textAlign = Paint.Align.LEFT
        }
        val centerPaint = Paint(bodyPaint).apply { textAlign = Paint.Align.CENTER }
        val bannerPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = theme.headerFillColor
            style = Paint.Style.FILL
        }

        canvas.drawRect(36f, 36f, (width - 36).toFloat(), (height - 36).toFloat(), borderPaint)
        logoBitmap?.let {
            val targetSize = 78
            val scaled = Bitmap.createScaledBitmap(it, targetSize, targetSize, true)
            canvas.drawBitmap(scaled, width - 120f - targetSize, 64f, null)
            if (scaled != it) scaled.recycle()
        }
        canvas.drawRect(36f, 36f, (width - 36).toFloat(), 98f, bannerPaint)
        canvas.drawRect(36f, (height - 96f), (width - 36).toFloat(), (height - 36).toFloat(), bannerPaint)
        canvas.drawText("ACKNOWLEDGEMENTS", width / 2f, 110f, titlePaint)
        canvas.drawText(chapterTitle, width / 2f, 150f, centerPaint)

        var y = 250f
        val left = 70f
        val right = (width - 70).toFloat()
        canvas.drawRoundRect(RectF(left, y, right, 1510f), 18f, 18f, borderPaint)
        acknowledgements.acknowledgements.forEachIndexed { index, paragraph ->
            y = drawWrappedText(
                canvas,
                paragraph.ifBlank { " " },
                left + 20f,
                if (index == 0) y + 54f else y + 40f,
                right - left - 40f,
                bodyPaint,
                1.28f
            ) + 20f
        }

        return bitmap
    }

    private fun renderConsentBitmap(consent: ConsentFormJson, chapterTitle: String, isHindi: Boolean, logoBitmap: Bitmap?, theme: PdfThemeStyle): Bitmap {
        val width = 1240
        val height = 1754
        val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        canvas.drawColor(Color.WHITE)

        val borderPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = theme.accentColor
            style = Paint.Style.STROKE
            strokeWidth = 4f
        }
        val titlePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.BLACK
            textSize = 42f
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
            textAlign = Paint.Align.CENTER
        }
        val subtitlePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.BLACK
            textSize = 24f
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.NORMAL)
            textAlign = Paint.Align.CENTER
        }
        val headerPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.BLACK
            textSize = 24f
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.BOLD)
        }
        val bodyPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.BLACK
            textSize = if (isHindi) 24f else 23f
            typeface = Typeface.create(Typeface.SANS_SERIF, Typeface.NORMAL)
        }
        val bannerPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = theme.headerFillColor
            style = Paint.Style.FILL
        }

        canvas.drawRect(36f, 36f, (width - 36).toFloat(), (height - 36).toFloat(), borderPaint)
        logoBitmap?.let {
            val targetSize = 78
            val scaled = Bitmap.createScaledBitmap(it, targetSize, targetSize, true)
            canvas.drawBitmap(scaled, width - 120f - targetSize, 64f, null)
            if (scaled != it) scaled.recycle()
        }
        canvas.drawRect(36f, 36f, (width - 36).toFloat(), 98f, bannerPaint)
        canvas.drawRect(36f, (height - 96f), (width - 36).toFloat(), (height - 36).toFloat(), bannerPaint)
        canvas.drawText("PATIENT CONSENT FORM", width / 2f, 96f, titlePaint)
        canvas.drawText(chapterTitle, width / 2f, 134f, subtitlePaint)
        canvas.drawText(consent.title.ifBlank { chapterTitle }, width / 2f, 172f, subtitlePaint)

        var y = 210f

        fun drawSection(title: String, content: String, boxHeight: Float) {
            val left = 70f
            val right = (width - 70).toFloat()
            val boxBottom = y + boxHeight
            canvas.drawRoundRect(RectF(left, y, right, boxBottom), 16f, 16f, borderPaint)
            canvas.drawText(title, left + 18f, y + 30f, headerPaint)
            drawWrappedText(canvas, content.ifBlank { " " }, left + 18f, y + 64f, right - left - 36f, bodyPaint, 1.28f, boxBottom - 18f)
            y = boxBottom + 16f
        }

        drawSection("INTRODUCTION", consent.introduction, 250f)
        drawSection("PROCEDURE", consent.procedure, 250f)
        drawSection("RISKS", consent.risks, 210f)
        drawSection("BENEFITS", consent.benefits, 210f)
        drawSection("CONFIDENTIALITY", consent.confidentiality, 210f)

        val sigLeft = 90f
        val sigTop = y + 26f
        val sigLineRight = width / 2f - 40f
        canvas.drawText("Signature", sigLeft, sigTop, bodyPaint)
        canvas.drawLine(sigLeft + 150f, sigTop + 6f, sigLineRight, sigTop + 6f, borderPaint)
        canvas.drawText(consent.signatureLine.ifBlank { "___________________" }, sigLeft + 150f, sigTop + 6f, bodyPaint)

        canvas.drawText("Date", width / 2f + 20f, sigTop, bodyPaint)
        canvas.drawLine(width / 2f + 90f, sigTop + 6f, width - 120f, sigTop + 6f, borderPaint)
        if (consent.date.isNotBlank()) {
            canvas.drawText(consent.date, width / 2f + 90f, sigTop + 6f, bodyPaint)
        }

        return bitmap
    }

    private fun drawWrappedText(
        canvas: Canvas,
        text: String,
        startX: Float,
        startY: Float,
        maxWidth: Float,
        paint: Paint,
        lineSpacingMultiplier: Float = 1.25f,
        maxBottom: Float? = null
    ): Float {
        val fontMetrics = paint.fontMetrics
        val lineHeight = (fontMetrics.descent - fontMetrics.ascent) * lineSpacingMultiplier
        var currentY = startY - fontMetrics.ascent
        var currentLine = StringBuilder()

        fun flushLine() {
            val line = currentLine.toString().trim()
            if (line.isNotBlank()) {
                if (maxBottom == null || currentY <= maxBottom) {
                    canvas.drawText(line, startX, currentY, paint)
                }
                currentY += lineHeight
            }
            currentLine = StringBuilder()
        }

        val plainText = stripBoldMarkdown(text)
        plainText.replace("\r", "").split('\n').forEachIndexed { index, paragraph ->
            val words = paragraph.split(Regex("\\s+")).filter { it.isNotBlank() }
            if (words.isEmpty()) {
                flushLine()
                currentY += lineHeight * 0.35f
                return@forEachIndexed
            }

            words.forEach { word ->
                val candidate = if (currentLine.isEmpty()) word else "${currentLine} $word"
                if (paint.measureText(candidate) <= maxWidth) {
                    currentLine = StringBuilder(candidate)
                } else {
                    flushLine()
                    currentLine = StringBuilder(word)
                }
            }
            flushLine()
            if (index < plainText.lineSequence().count() - 1) {
                currentY += lineHeight * 0.2f
            }
        }

        return currentY
    }

    private fun drawCenteredText(
        cs: PDPageContentStream,
        text: String,
        font: PDType1Font,
        size: Float,
        pageWidth: Float,
        y: Float
    ) {
        // Sanitize text for standard font compatibility
        val sanitized = stripBoldMarkdown(text).replace("\u03c3", "sigma").replace("\u03a3", "Sigma")
            .filter { char ->
                try {
                    font.getStringWidth(char.toString())
                    true
                } catch (e: Exception) {
                    false
                }
            }
        val titleWidth = (font.getStringWidth(sanitized) / 1000f) * size
        cs.beginText()
        cs.setFont(font, size)
        cs.newLineAtOffset((pageWidth - titleWidth) / 2f, y)
        cs.showText(sanitized)
        cs.endText()
    }
    private fun wrapText(
        text: String,
        font: PDType1Font,
        fontSize: Float,
        maxWidth: Float
    ): List<String> {
        val words = text.replace("\n", " \n ").split(Regex("\\s+")).filter { it.isNotEmpty() }
        val lines = mutableListOf<String>()
        var currentLine = StringBuilder()

        fun textWidth(s: String): Float {
            return try {
                (font.getStringWidth(s) / 1000f) * fontSize
            } catch (e: Exception) {
                // Fallback for illegal characters during wrapping
                (s.length * fontSize * 0.5f)
            }
        }

        for (word in words) {
            if (word == "\n") {
                lines.add(currentLine.toString())
                currentLine = StringBuilder()
                continue
            }
            val candidate = if (currentLine.isEmpty()) word else "${currentLine} $word"
            if (textWidth(candidate) <= maxWidth) {
                currentLine.append(if (currentLine.isEmpty()) word else " $word")
            } else {
                if (currentLine.isNotEmpty()) lines.add(currentLine.toString())
                currentLine = StringBuilder(word)
            }
        }
        if (currentLine.isNotEmpty()) lines.add(currentLine.toString())
        return lines.ifEmpty { listOf("") }
    }

    fun resolveAndRefreshFigures() {
        viewModelScope.launch {
            _uiState.update { it.copy(processing = true, status = "Resolving figure images...") }
            val updated = resolveFigureImages(_uiState.value.chapters)
            _uiState.update {
                it.copy(
                    chapters = updated,
                    processing = false,
                    status = "Figures resolved"
                )
            }
            saveSessionToFirebase()
        }
    }

    fun updateFigureImageUrl(
        chapterName: String,
        figureNumber: String,
        newUrl: String
    ) {
        _uiState.update { state ->
            val updatedChapters = state.chapters.map { chapter ->
                if (chapter.name != chapterName) return@map chapter

                val updatedFigures = chapter.figures.map { figure ->
                    if (figure.figureNumber == figureNumber) {
                        figure.copy(imageUrl = newUrl)
                    } else {
                        figure
                    }
                }
                chapter.copy(figures = updatedFigures)
            }
            state.copy(chapters = updatedChapters)
        }
        saveSessionToFirebase()
    }

    fun refreshPubMedFigures(context: Context) {
        viewModelScope.launch(Dispatchers.IO) {
            val appContext = context.applicationContext
            val pmids = collectVerifiedPmids()
            if (pmids.isEmpty()) return@launch
            val alreadyCheckedPmids = (
                _uiState.value.pubMedFigureCheckedPmids +
                    _uiState.value.pubMedFigures.map { it.pmid }
                )
                .map { it.trim() }
                .filter { it.isNotBlank() }
                .toSet()
            val pendingPmids = pmids.filterNot { it in alreadyCheckedPmids }
            if (pendingPmids.isEmpty()) {
                _uiState.update {
                    it.copy(status = "PubMed figures already checked for ${pmids.size} PMID references")
                }
                return@launch
            }
            startBackgroundWork(appContext, "Downloading PubMed figures")

            try {
                _uiState.update {
                    it.copy(
                        processing = true,
                        status = "Downloading PubMed figures...",
                        progressCurrent = 0,
                        progressTotal = pendingPmids.size
                    )
                }

                val downloaded = mutableListOf<PubMedFigureJson>()
                val checkedThisRun = mutableListOf<String>()
                pendingPmids.forEachIndexed { index, pmid ->
                    _uiState.update {
                        it.copy(
                            status = "Downloading PubMed figures ${index + 1}/${pendingPmids.size}: PMID $pmid",
                            progressCurrent = index + 1,
                            progressTotal = pendingPmids.size
                        )
                    }
                    val newFigures = fetchPubMedFiguresForPmid(appContext, pmid)
                    downloaded += newFigures
                    checkedThisRun += pmid
                    val mergedFigures = (_uiState.value.pubMedFigures + newFigures)
                        .filter { it.localUri.isNotBlank() || it.imageUrl.isNotBlank() }
                        .distinctBy {
                            listOf(it.pmid, it.pmcId, it.figureId, it.imageUrl).joinToString("|")
                        }
                    val checkedPmids = (
                        _uiState.value.pubMedFigureCheckedPmids +
                            _uiState.value.pubMedFigures.map { it.pmid } +
                            checkedThisRun
                        )
                        .map { it.trim() }
                        .filter { it.isNotBlank() }
                        .distinct()

                    _uiState.update {
                        it.copy(
                            pubMedFigures = mergedFigures,
                            pubMedFigureCheckedPmids = checkedPmids,
                            status = "PubMed figures downloaded: ${downloaded.size}; cached: ${mergedFigures.size}"
                        )
                    }
                    saveSessionToFirebase()
                }

                _uiState.update {
                    it.copy(
                        processing = false,
                        status = "PubMed figures downloaded: ${downloaded.size}; cached: ${_uiState.value.pubMedFigures.size}"
                    )
                }
            } finally {
                stopBackgroundWork(appContext)
            }
        }
    }

    private fun collectVerifiedPmids(): List<String> {
        val chapterPmids = _uiState.value.chapters
            .flatMap { it.chapterReferences }
            .mapNotNull { it.pmid?.trim()?.takeIf { pmid -> pmid.isNotBlank() } }

        val variablePmids = parseReferencesVariable(_uiState.value.variables)
            .mapNotNull { it.pmid?.trim()?.takeIf { pmid -> pmid.isNotBlank() } }

        return (chapterPmids + variablePmids).distinct()
    }

    private suspend fun fetchPubMedFiguresForPmid(context: Context, pmid: String): List<PubMedFigureJson> = withContext(Dispatchers.IO) {
        pubMedFigureCache[pmid]?.let { return@withContext it }

        val pubMedFigures = fetchPubMedPageFigures(context, pmid)
        if (pubMedFigures.isNotEmpty()) {
            pubMedFigureCache[pmid] = pubMedFigures
            return@withContext pubMedFigures
        }

        val pmcIds = fetchLinkedPmcIds(pmid)
        if (pmcIds.isEmpty()) {
            pubMedFigureCache[pmid] = emptyList()
            return@withContext emptyList()
        }

        val figures = pmcIds.flatMap { pmcId ->
            fetchPmcFigures(context, pmid, pmcId)
        }
        pubMedFigureCache[pmid] = figures
        figures
    }

    private suspend fun fetchPubMedPageFigures(context: Context, pmid: String): List<PubMedFigureJson> = withContext(Dispatchers.IO) {
        runCatching {
            val articleUrl = "https://pubmed.ncbi.nlm.nih.gov/$pmid/"
            val request = Request.Builder()
                .url(articleUrl)
                .header("User-Agent", "EduLabsRTM/1.0")
                .build()

            rawClient.newCall(request).execute().use { response ->
                if (!response.isSuccessful) return@runCatching emptyList()

                val html = response.body?.string().orEmpty()
                val document = Jsoup.parse(html, articleUrl)

                document.select("a.figure-link[href]").mapIndexedNotNull { index, link ->
                    val imageUrl = link.absUrl("href").ifBlank { link.attr("href") }
                    if (imageUrl.isBlank()) return@mapIndexedNotNull null

                    val thumbUrl = link.selectFirst("img")?.absUrl("src").orEmpty()
                    val figureId = link.attr("data-figure-id").ifBlank { "F${index + 1}" }
                    val pmcId = link.attr("data-pmc-id")
                    val captionId = link.attr("aria-describedby")
                    val caption = captionId
                        .takeIf { it.isNotBlank() }
                        ?.let { document.getElementById(it)?.text() }
                        .orEmpty()
                    val title = link.selectFirst("img")?.attr("alt")?.ifBlank { figureId }.orEmpty().ifBlank { figureId }
                    val localUri = downloadPubMedFigure(context, pmid, pmcId.ifBlank { "pubmed" }, figureId, imageUrl)

                    PubMedFigureJson(
                        pmid = pmid,
                        pmcId = pmcId,
                        figureId = figureId,
                        title = title,
                        caption = caption,
                        imageUrl = imageUrl,
                        thumbnailUrl = thumbUrl,
                        localUri = localUri,
                        articleUrl = articleUrl
                    )
                }.distinctBy { it.imageUrl }
            }
        }.onFailure {
            Log.e("ThesisViewModel", "PubMed figure scrape failed for PMID $pmid", it)
        }.getOrDefault(emptyList())
    }

    private suspend fun fetchLinkedPmcIds(pmid: String): List<String> = withContext(Dispatchers.IO) {
        runCatching {
            val url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?dbfrom=pubmed&db=pmc&id=$pmid&retmode=json"
            rawClient.newCall(Request.Builder().url(url).build()).execute().use { response ->
                if (!response.isSuccessful) return@runCatching emptyList()
                val json = response.body?.string().orEmpty()
                val root = JsonParser.parseString(json).asJsonObject
                root.getAsJsonArray("linksets")
                    ?.flatMap { linkset ->
                        linkset.asJsonObject.getAsJsonArray("linksetdbs")
                            ?.flatMap { db ->
                                db.asJsonObject.getAsJsonArray("links")
                                    ?.mapNotNull { it.asString.trim().takeIf { value -> value.isNotBlank() } }
                                    .orEmpty()
                            }
                            .orEmpty()
                    }
                    ?.distinct()
                    .orEmpty()
            }
        }.getOrDefault(emptyList())
    }

    private suspend fun fetchPmcFigures(context: Context, pmid: String, pmcId: String): List<PubMedFigureJson> = withContext(Dispatchers.IO) {
        runCatching {
            val articleUrl = "https://pmc.ncbi.nlm.nih.gov/articles/PMC$pmcId/"
            val request = Request.Builder()
                .url(articleUrl)
                .header("User-Agent", "EduLabsRTM/1.0")
                .build()
            rawClient.newCall(request).execute().use { response ->
                if (!response.isSuccessful) return@runCatching emptyList()
                val html = response.body?.string().orEmpty()
                val document = Jsoup.parse(html, articleUrl)

                document.select("a.figure-link[href], a.figpopup[href]").mapIndexedNotNull { index, link ->
                    val imageUrl = link.absUrl("href").takeIf { it.isNotBlank() } ?: return@mapIndexedNotNull null
                    val thumbUrl = link.selectFirst("img")?.absUrl("src").orEmpty()
                    val figureId = link.attr("data-figure-id").ifBlank {
                        link.attr("data-fig-id").ifBlank { "F${index + 1}" }
                    }
                    val captionId = link.attr("aria-describedby")
                    val caption = captionId
                        .takeIf { it.isNotBlank() }
                        ?.let { document.getElementById(it)?.text() }
                        .orEmpty()
                    val title = link.selectFirst("img")?.attr("alt")?.ifBlank { figureId }.orEmpty().ifBlank { figureId }
                    val localUri = downloadPubMedFigure(context, pmid, pmcId, figureId, imageUrl)

                    PubMedFigureJson(
                        pmid = pmid,
                        pmcId = "PMC$pmcId",
                        figureId = figureId,
                        title = title,
                        caption = caption,
                        imageUrl = imageUrl,
                        thumbnailUrl = thumbUrl,
                        localUri = localUri,
                        articleUrl = articleUrl
                    )
                }.distinctBy { it.imageUrl }
            }
        }.getOrDefault(emptyList())
    }

    private suspend fun downloadPubMedFigure(
        context: Context,
        pmid: String,
        pmcId: String,
        figureId: String,
        imageUrl: String
    ): String = withContext(Dispatchers.IO) {
        runCatching {
            val extension = imageUrl.substringBefore('?')
                .substringAfterLast('.', "jpg")
                .lowercase()
                .takeIf { it in setOf("jpg", "jpeg", "png", "gif", "webp") }
                ?: "jpg"
            val figureDir = java.io.File(context.filesDir, "pubmed_figures").apply { mkdirs() }
            val safeFigureId = figureId.lowercase().replace(Regex("[^a-z0-9]+"), "_").trim('_').ifBlank { "figure" }
            val file = java.io.File(figureDir, "pmid_${pmid}_pmc_${pmcId}_${safeFigureId}.$extension")
            if (file.exists() && file.length() > 0L) return@runCatching Uri.fromFile(file).toString()

            rawClient.newCall(
                Request.Builder()
                    .url(imageUrl)
                    .header("User-Agent", "EduLabsRTM/1.0")
                    .build()
            ).execute().use { response ->
                if (!response.isSuccessful) return@runCatching ""
                val contentType = response.header("Content-Type").orEmpty()
                if (contentType.isNotBlank() && !contentType.startsWith("image/", ignoreCase = true)) {
                    return@runCatching ""
                }
                val bytes = response.body?.bytes() ?: return@runCatching ""
                if (bytes.isEmpty()) return@runCatching ""
                file.writeBytes(bytes)
                Uri.fromFile(file).toString()
            }
        }.getOrDefault("")
    }

    private suspend fun resolveFigureImages(chapters: List<Chapter>): List<Chapter> = withContext(Dispatchers.IO) {
        chapters.map { chapter ->
            val updatedFigures = chapter.figures.map { fig ->
                if (fig.imageUrl.isNotBlank()) {
                    fig
                } else {
                    val url = searchImageFromQuery(fig.imageSearchQuery)
                    fig.copy(imageUrl = url)
                }
            }
            chapter.copy(figures = updatedFigures)
        }
    }

    private suspend fun searchImageFromQuery(query: String): String = withContext(Dispatchers.IO) {
        if (query.isBlank()) return@withContext ""

        return@withContext try {
            val encoded = java.net.URLEncoder.encode(query, "UTF-8")
            "https://source.unsplash.com/800x600/?$encoded"
        } catch (e: Exception) {
            Log.e("ThesisViewModel", "Image query encoding failed", e)
            ""
        }
    }

    private fun buildRetryPrompt(chapterName: String, variables: List<Variable>): String {
        val schema = chapterSchemas[chapterName.lowercase()]
        return buildChapterPrompt(chapterName, variables, schema, forceDetailed = true)
    }

    private fun parseGeneratedChapterValue(chapterName: String, rawJson: String, schema: ChapterSchema?): Any? {
        return if (schema != null) {
            schema.parser(rawJson)
                ?.takeIf { isMeaningfulParsedChapterValue(chapterName, it) }
                ?: fallbackParsedChapterValue(chapterName, rawJson)
                    ?.takeIf { isMeaningfulParsedChapterValue(chapterName, it) }
        } else {
            val generic = parseThesisChapterJson(rawJson, chapterName)
            if (isMeaningfulThesisChapter(generic)) generic else null
        }
    }

    private fun saveChapterVersion(chapterName: String, content: String, rawJson: String) {
        val list = chapterVersions.getOrPut(chapterName) { mutableListOf() }
        list += ChapterVersion(
            versionNo = list.size + 1,
            content = content,
            rawJson = rawJson
        )
    }

    fun getChapterVersions(chapterName: String): List<ChapterVersion> {
        return chapterVersions[chapterName].orEmpty()
    }

    private fun computeCompletionPercent(chapters: List<Chapter>): Int {
        if (chapters.isEmpty()) return 0
        val done = chapters.count { it.status == Chapter.ChapterStatus.SUCCESS }
        return ((done.toFloat() / chapters.size.toFloat()) * 100f).toInt()
    }

    private fun PubMedMatch.toCacheJson(): PubMedMatchCacheJson {
        return PubMedMatchCacheJson(
            pmid = pmid,
            doi = doi,
            articleTitle = articleTitle,
            canonicalReference = canonicalReference
        )
    }

    private fun PubMedMatchCacheJson.toPubMedMatchOrNull(): PubMedMatch? {
        val cleanPmid = pmid.trim()
        if (cleanPmid.isBlank()) return null
        return PubMedMatch(
            pmid = cleanPmid,
            doi = doi?.trim()?.takeIf { it.isNotBlank() },
            articleTitle = articleTitle,
            canonicalReference = canonicalReference
        )
    }

    private fun cachedPubMedMatchesSnapshot(): List<PubMedMatchCacheJson> {
        return pubMedPmidCache.values
            .distinctBy { it.pmid.trim() }
            .map { it.toCacheJson() }
    }

    private fun cachedPubMedSearchMatchesSnapshot(): List<PubMedSearchMatchCacheJson> {
        return pubMedSearchCache.entries
            .filter { it.key.isNotBlank() && it.value.pmid.isNotBlank() }
            .map { PubMedSearchMatchCacheJson(key = it.key, match = it.value.toCacheJson()) }
    }

    private fun cachedAbstractSourcesSnapshot(): List<PubMedAbstractSourceJson> {
        return (_uiState.value.verifiedPubMedAbstractSources + pubMedAbstractSourceCache.values)
            .filter { it.pmid.trim().isNotBlank() }
            .distinctBy { it.pmid.trim() }
    }

    private fun cachedVerifiedReferencesSnapshot(): List<ReferenceJson> {
        return (_uiState.value.verifiedPubMedReferences + verifiedReferenceCache.values)
            .filter { it.hasRequiredPmid() }
            .distinctBy { ref -> referenceIdentity(ref) ?: canonicalReferenceTextKey(ref.referenceText) }
    }

    private fun buildReferenceCachePayload(sessionId: String): ThesisReferenceCachePayload {
        return ThesisReferenceCachePayload(
            sessionId = sessionId,
            updatedAt = System.currentTimeMillis(),
            verifiedPubMedReferences = _uiState.value.verifiedPubMedReferences,
            verifiedPubMedAbstractSources = _uiState.value.verifiedPubMedAbstractSources,
            cachedPubMedMatches = cachedPubMedMatchesSnapshot(),
            cachedPubMedSearchMatches = cachedPubMedSearchMatchesSnapshot(),
            cachedPubMedAbstractSources = cachedAbstractSourcesSnapshot(),
            cachedVerifiedReferences = cachedVerifiedReferencesSnapshot(),
            pubMedFigureCheckedPmids = _uiState.value.pubMedFigureCheckedPmids,
            pubMedFigures = _uiState.value.pubMedFigures
        )
    }

    private fun firestoreSafeDocumentId(value: String, fallback: String): String {
        val clean = value.trim()
        val base = clean
            .lowercase()
            .replace(Regex("[^a-z0-9._-]+"), "_")
            .trim('_')
            .take(120)
            .ifBlank { fallback }
        return "${base}_${Integer.toHexString(clean.hashCode())}"
    }

    private fun referenceCacheDocumentId(reference: ReferenceJson, index: Int): String {
        val identity = referenceIdentity(reference)
            ?: reference.pmid?.trim()?.takeIf { it.isNotBlank() }
            ?: reference.doi?.trim()?.takeIf { it.isNotBlank() }
            ?: reference.referenceText
        return firestoreSafeDocumentId(identity, "reference_$index")
    }

    private fun shouldWriteFirestoreChunk(label: String, value: Any): Boolean {
        val chars = runCatching { gson.toJson(value).length }.getOrDefault(Int.MAX_VALUE)
        if (chars > maxFirestoreChunkChars) {
            Log.w("ThesisViewModel", "Skipping oversized Firestore $label chunk ($chars chars)")
            return false
        }
        return true
    }

    private fun referenceCacheSignature(
        references: List<ReferenceJson>,
        abstractSources: List<PubMedAbstractSourceJson>,
        pubMedMatches: List<PubMedMatchCacheJson>,
        pubMedSearchMatches: List<PubMedSearchMatchCacheJson>,
        pubMedFigures: List<PubMedFigureJson>
    ): String {
        val seed = buildString {
            append("refs=")
            append(references.mapNotNull { it.pmid?.trim() }.sorted().joinToString(","))
            append("|abstracts=")
            append(abstractSources.map { it.pmid.trim() }.sorted().joinToString(","))
            append("|matches=")
            append(pubMedMatches.map { it.pmid.trim() }.sorted().joinToString(","))
            append("|searches=")
            append(pubMedSearchMatches.map { it.key.trim() }.sorted().joinToString(","))
            append("|figures=")
            append(pubMedFigures.map { "${it.pmid.trim()}:${it.figureId}:${it.imageUrl}" }.sorted().joinToString(","))
        }
        return Integer.toHexString(seed.hashCode())
    }

    fun syncVerifiedReferenceCacheNow() {
        saveSessionToFirebase(immediate = true)
    }

    private fun mergeReferenceCacheIntoSession(
        session: ThesisSessionPayload,
        cache: ThesisReferenceCachePayload?
    ): ThesisSessionPayload {
        if (cache == null) return session
        return session.copy(
            verifiedPubMedReferences = (session.verifiedPubMedReferences + cache.verifiedPubMedReferences)
                .filter { it.hasRequiredPmid() }
                .distinctBy { ref -> referenceIdentity(ref) ?: canonicalReferenceTextKey(ref.referenceText) },
            verifiedPubMedAbstractSources = (session.verifiedPubMedAbstractSources + cache.verifiedPubMedAbstractSources)
                .filter { it.pmid.trim().isNotBlank() }
                .distinctBy { it.pmid.trim() },
            cachedPubMedMatches = (session.cachedPubMedMatches + cache.cachedPubMedMatches)
                .filter { it.pmid.trim().isNotBlank() }
                .distinctBy { it.pmid.trim() },
            cachedPubMedSearchMatches = (session.cachedPubMedSearchMatches + cache.cachedPubMedSearchMatches)
                .filter { it.key.trim().isNotBlank() && it.match.pmid.trim().isNotBlank() }
                .distinctBy { it.key.trim() },
            cachedPubMedAbstractSources = (session.cachedPubMedAbstractSources + cache.cachedPubMedAbstractSources)
                .filter { it.pmid.trim().isNotBlank() }
                .distinctBy { it.pmid.trim() },
            cachedVerifiedReferences = (session.cachedVerifiedReferences + cache.cachedVerifiedReferences)
                .filter { it.hasRequiredPmid() }
                .distinctBy { ref -> referenceIdentity(ref) ?: canonicalReferenceTextKey(ref.referenceText) },
            pubMedFigureCheckedPmids = (session.pubMedFigureCheckedPmids + cache.pubMedFigureCheckedPmids)
                .map { it.trim() }
                .filter { it.isNotBlank() }
                .distinct(),
            pubMedFigures = (session.pubMedFigures + cache.pubMedFigures)
                .filter { it.pmid.trim().isNotBlank() }
                .distinctBy { "${it.pmid.trim()}|${it.figureId}|${it.imageUrl}" }
        )
    }

    private fun saveReferenceCacheToFirestore(uid: String, sessionId: String, force: Boolean = false) {
        if (uid.isBlank() || sessionId.isBlank()) return
        if (!force && _uiState.value.referenceCacheSyncInProgress) return
        _uiState.update {
            it.copy(
                referenceCacheSyncInProgress = true,
                referenceCacheSyncCurrent = 0,
                referenceCacheSyncTotal = 1,
                status = "Syncing thesis session to VPS backend...",
                referenceCacheSyncError = null
            )
        }
        viewModelScope.launch(Dispatchers.IO) {
            try {
                saveSessionToFirebase(immediate = true)
                lastUploadedReferenceCacheSignature = referenceCacheSignature(
                    cachedVerifiedReferencesSnapshot(),
                    cachedAbstractSourcesSnapshot(),
                    cachedPubMedMatchesSnapshot(),
                    cachedPubMedSearchMatchesSnapshot(),
                    _uiState.value.pubMedFigures
                )
                val syncedAt = System.currentTimeMillis()
                _uiState.update {
                    it.copy(
                        referenceCacheLastSyncedAt = syncedAt,
                        referenceCacheSyncInProgress = false,
                        referenceCacheSyncCurrent = 1,
                        referenceCacheSyncTotal = 1,
                        status = "Thesis session synced to VPS backend",
                        referenceCacheSyncError = null
                    )
                }
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(
                        referenceCacheSyncInProgress = false,
                        status = "VPS thesis sync failed",
                        referenceCacheSyncError = e.localizedMessage ?: "VPS thesis sync failed"
                    )
                }
            }
        }
    }

    private fun restoreSessionWithFirestoreCache(session: ThesisSessionPayload) {
        restoreSession(session)
        viewModelScope.launch {
            ensureAbstractSourcesHydratedAfterSessionLoad(session)
        }
    }

    private suspend fun ensureAbstractSourcesHydratedAfterSessionLoad(session: ThesisSessionPayload) = withContext(Dispatchers.IO) {
        val loadedSources = _uiState.value.verifiedPubMedAbstractSources
        val needsRefresh = loadedSources.isEmpty() ||
            loadedSources.any { source ->
                source.abstractText.isBlank() || (source.abstractSections.isEmpty() && source.similarArticles.isEmpty() && source.citedBy.isEmpty())
            }
        if (!needsRefresh) return@withContext

        val pmids = (
            session.verifiedPubMedReferences +
                session.cachedVerifiedReferences +
                session.chapters.flatMap { it.chapterReferences } +
                parseReferencesVariable(session.variables)
            )
            .mapNotNull { it.pmid?.trim()?.takeIf { pmid -> pmid.isNotBlank() } }
            .distinct()

        if (pmids.isEmpty()) {
            Log.d("ThesisViewModel", "Session load abstract audit found no PMIDs to hydrate.")
            return@withContext
        }

        Log.i(
            "ThesisViewModel",
            "Session load abstract audit hydrating PubMed abstracts: pmids=${pmids.size}, existingSources=${loadedSources.size}"
        )
        refreshVerifiedPubMedEvidence(pmids.map { pmid -> ReferenceJson(pmid = pmid, referenceText = pmid) })
    }

    private fun postReferenceCacheBackend(payload: Map<String, Any?>): JsonObject {
        val requestBody = gson.toJson(payload)
            .toRequestBody("application/json; charset=utf-8".toMediaType())
        val failures = mutableListOf<String>()
        for (url in referenceCacheBackendUrls) {
            try {
                rawClient.newCall(
                    Request.Builder()
                        .url(url)
                        .post(requestBody)
                        .build()
                ).execute().use { response ->
                    val raw = response.body?.string().orEmpty()
                    if (!response.isSuccessful) {
                        throw IOException("PHP cache backend HTTP ${response.code}: $raw")
                    }
                    val json = JsonParser.parseString(raw).asJsonObject
                    if (json.get("ok")?.asBoolean != true) {
                        throw IOException(json.get("error")?.asString ?: "PHP cache backend returned ok=false")
                    }
                    return json
                }
            } catch (e: Exception) {
                failures += "$url -> ${e.localizedMessage ?: e.javaClass.simpleName}"
            }
        }
        throw IOException("PHP cache backend handshake failed. Tried: ${failures.joinToString(" | ")}")
    }

    private inline fun <reified T> parseBackendArray(root: JsonObject, name: String): List<T> {
        val array = root.getAsJsonArray(name) ?: JsonArray()
        return array.mapNotNull { element ->
            runCatching { gson.fromJson(element, T::class.java) }.getOrNull()
        }
    }

    private fun loadReferenceCacheFromPhp(uid: String, sessionId: String): ThesisReferenceCachePayload {
        val response = postReferenceCacheBackend(
            mapOf(
                "action" to "get_cache",
                "user_id" to uid,
                "session_id" to sessionId
            )
        )
        val meta = response.getAsJsonObject("meta")
        val signature = meta?.get("cache_signature")?.asString.orEmpty()
        if (signature.isNotBlank()) {
            lastUploadedReferenceCacheSignature = signature
        }
        val updatedAt = meta?.get("updated_at")?.asLong ?: 0L
        if (updatedAt > 0L) {
            _uiState.update {
                it.copy(
                    referenceCacheLastSyncedAt = updatedAt,
                    referenceCacheSyncError = null
                )
            }
        }
        val abstractSources = parseBackendArray<PubMedAbstractSourceJson>(response, "abstract_sources")
        response.getAsJsonArray("abstract_sources")?.forEach { element ->
            val obj = element.takeIf { it.isJsonObject }?.asJsonObject ?: return@forEach
            val pmid = obj.get("pmid")?.asString?.trim().orEmpty()
            val fetchedAt = obj.get("lastFetchedAt")?.asLong
                ?: obj.get("last_fetched_at")?.asLong
                ?: updatedAt
            if (pmid.isNotBlank() && fetchedAt > 0L) {
                pubMedAbstractFetchedAt[pmid] = fetchedAt
            }
        }
        return ThesisReferenceCachePayload(
            sessionId = sessionId,
            updatedAt = updatedAt.takeIf { it > 0L } ?: System.currentTimeMillis(),
            verifiedPubMedReferences = parseBackendArray(response, "references"),
            verifiedPubMedAbstractSources = abstractSources,
            cachedPubMedMatches = parseBackendArray(response, "pubmed_matches"),
            cachedPubMedSearchMatches = parseBackendArray(response, "search_matches"),
            cachedPubMedAbstractSources = abstractSources,
            cachedVerifiedReferences = parseBackendArray(response, "references"),
            pubMedFigures = parseBackendArray(response, "pubmed_figures")
        )
    }

    private fun restorePubMedCachesFromSession(session: ThesisSessionPayload) {
        session.cachedPubMedMatches.forEach { cached ->
            cached.toPubMedMatchOrNull()?.let { match ->
                pubMedPmidCache[match.pmid.trim()] = match
            }
        }
        session.cachedPubMedSearchMatches.forEach { cached ->
            val key = cached.key.trim()
            val match = cached.match.toPubMedMatchOrNull()
            if (key.isNotBlank() && match != null) {
                pubMedSearchCache[key] = match
                pubMedPmidCache[match.pmid.trim()] = match
            }
        }
        (session.cachedPubMedAbstractSources + session.verifiedPubMedAbstractSources)
            .filter { it.pmid.trim().isNotBlank() }
            .forEach { source ->
                val pmid = source.pmid.trim()
                pubMedAbstractSourceCache[pmid] = source
                pubMedAbstractFetchedAt.putIfAbsent(pmid, System.currentTimeMillis())
            }
        (session.cachedVerifiedReferences + session.verifiedPubMedReferences)
            .filter { it.hasRequiredPmid() }
            .forEach(::cacheVerifiedReference)
    }

    private fun uploadCurrentVerifiedReferenceCacheToFirestore(reason: String, force: Boolean = false) {
        val auth = FirebaseAuth.getInstance()
        val uid = auth.currentUser?.uid
        if (uid.isNullOrBlank()) {
            _uiState.update {
                it.copy(
                    referenceCacheSyncInProgress = true,
                    referenceCacheSyncCurrent = 0,
                    referenceCacheSyncTotal = 1,
                    referenceCacheSyncError = "Sign in is required before syncing verified references.",
                    status = "Signing in to sync verified reference cache..."
                )
            }
            auth.signInAnonymously()
                .addOnSuccessListener {
                    uploadCurrentVerifiedReferenceCacheToFirestore(reason, force)
                }
                .addOnFailureListener { e ->
                    val message = e.localizedMessage ?: "Firebase Auth sign-in failed"
                    _uiState.update {
                        it.copy(
                            referenceCacheSyncInProgress = false,
                            referenceCacheSyncError = message,
                            status = "Reference cache sync sign-in failed"
                        )
                    }
                    Log.e("ThesisViewModel", "Firebase Auth sign-in failed before reference cache sync", e)
                }
            return
        }
        val sessionId = _uiState.value.sessionId
        if (sessionId.isBlank()) {
            _uiState.update {
                it.copy(
                    referenceCacheSyncInProgress = false,
                    referenceCacheSyncError = "Open or create a thesis session before syncing.",
                    status = "Reference cache sync needs an active session"
                )
            }
            return
        }
        val verifiedCount = cachedVerifiedReferencesSnapshot().size
        val abstractCount = cachedAbstractSourcesSnapshot().size
        val figureCount = _uiState.value.pubMedFigures.count { it.pmid.trim().isNotBlank() }
        if (verifiedCount == 0 && abstractCount == 0 && figureCount == 0) {
            _uiState.update {
                it.copy(
                    referenceCacheSyncInProgress = false,
                    referenceCacheSyncError = "No verified references or abstracts are available to sync yet.",
                    status = "No verified reference cache to sync"
                )
            }
            return
        }

        Log.i(
            "ThesisViewModel",
            "Uploading verified reference cache to PHP backend after $reason: refs=$verifiedCount abstracts=$abstractCount figures=$figureCount"
        )
        saveReferenceCacheToFirestore(uid, sessionId, force = force)
    }

    fun saveSessionToFirebase(immediate: Boolean = false) {
        val uid = getUid() ?: return
        val sessionId = _uiState.value.sessionId.ifBlank { newSessionId() }

        if (!_uiState.value.autoSyncEnabled && !immediate) {
            Log.d("ThesisViewModel", "Skip session save: autoSyncEnabled = false")
            return
        }

        val runSave = {
            val payloadUpdates = hashMapOf<String, Any?>()
            payloadUpdates["sessionId"] = sessionId
            payloadUpdates["thesisTitle"] = _uiState.value.thesisTitle
            payloadUpdates["updatedAt"] = System.currentTimeMillis()
            payloadUpdates["status"] = if (_uiState.value.processing) "IN_PROGRESS" else "IDLE"
            payloadUpdates["currentChapter"] = _uiState.value.progressCurrent
            payloadUpdates["totalChapters"] = _uiState.value.progressTotal
            payloadUpdates["completionPercent"] = _uiState.value.completionPercent
            payloadUpdates["selectedProvider"] = _uiState.value.selectedProvider
            payloadUpdates["collegeLogoUri"] = _uiState.value.collegeLogoUri
            payloadUpdates["pdfTheme"] = _uiState.value.pdfTheme
            payloadUpdates["variables"] = _uiState.value.variables
            payloadUpdates["verifiedPubMedReferences"] = _uiState.value.verifiedPubMedReferences
            payloadUpdates["referenceSequenceCounter"] = _uiState.value.referenceSequenceCounter
            payloadUpdates["vpsAutoCompleteEnabled"] = _uiState.value.vpsAutoCompleteEnabled
            payloadUpdates["autoSyncEnabled"] = _uiState.value.autoSyncEnabled
            payloadUpdates["lastWorkerSyncTime"] = _uiState.value.lastWorkerSyncTime
            payloadUpdates["exportMargin"] = _uiState.value.exportMargin
            payloadUpdates["exportFont"] = _uiState.value.exportFont
            payloadUpdates["exportLineSpacing"] = _uiState.value.exportLineSpacing
            payloadUpdates["exportLogoPlacement"] = _uiState.value.exportLogoPlacement
            payloadUpdates["exportPageNumbering"] = _uiState.value.exportPageNumbering
            payloadUpdates["exportHeaderFooter"] = _uiState.value.exportHeaderFooter
            payloadUpdates["exportWatermark"] = _uiState.value.exportWatermark
            payloadUpdates["exportAutoToc"] = _uiState.value.exportAutoToc
            payloadUpdates["exportAutoLists"] = _uiState.value.exportAutoLists
            payloadUpdates["promptSectionSplittingEnabled"] = _uiState.value.promptSectionSplittingEnabled
            payloadUpdates["promptMaxChars"] = _uiState.value.promptMaxChars
            payloadUpdates["masterChartColumns"] = _uiState.value.masterChartColumns
            payloadUpdates["masterChartCsv"] = _uiState.value.masterChartCsv
            payloadUpdates["masterChartGeneratedAt"] = _uiState.value.masterChartGeneratedAt
            payloadUpdates["masterDataFileName"] = _uiState.value.masterDataFileName
            payloadUpdates["masterDataHeaders"] = _uiState.value.masterDataHeaders
            payloadUpdates["masterDataRows"] = _uiState.value.masterDataRows
            payloadUpdates["masterDataMappings"] = _uiState.value.masterDataMappings
            payloadUpdates["masterDataValidationIssues"] = _uiState.value.masterDataValidationIssues
            payloadUpdates["masterDataResultTables"] = _uiState.value.masterDataResultTables
            payloadUpdates["masterDataImportedAt"] = _uiState.value.masterDataImportedAt
            payloadUpdates["aiLogs"] = _uiState.value.aiLogs

            val currentChapters = _uiState.value.chapters
            val lastChapters = lastSavedChapters
            if (lastChapters == null || lastChapters.size != currentChapters.size) {
                payloadUpdates["chapters"] = currentChapters
            } else {
                for (i in currentChapters.indices) {
                    if (currentChapters[i] != lastChapters[i]) {
                        payloadUpdates["chapters/$i"] = currentChapters[i]
                    }
                }
            }

            Log.d("ThesisViewModel", "Executing Firebase update for session: $sessionId")
            FirebaseDatabase.getInstance()
                .reference
                .child("users")
                .child(uid)
                .child("thesis_sessions")
                .child(sessionId)
                .updateChildren(payloadUpdates)
                .addOnSuccessListener {
                    Log.i("ThesisViewModel", "Firebase update successful for session: $sessionId")
                    lastSavedChapters = currentChapters.map { it.copy() }
                    attachCurrentSessionWorkerListener(sessionId)
                }
                .addOnFailureListener { e ->
                    Log.e("ThesisViewModel", "Firebase update FAILED for session: $sessionId", e)
                }
        }

        val backendUrl = ApiKeys.THESIS_SESSION_BACKEND_URL.trim()
        if (backendUrl.isNotBlank()) {
            val launchBackendSave = {
                viewModelScope.launch(Dispatchers.IO) {
                    val payload = buildThesisSessionPayload(sessionId)
                    val saved = runCatching { saveThesisSessionToBackend(backendUrl, payload) }.getOrElse { error ->
                        Log.w("ThesisViewModel", "VPS thesis session save failed", error)
                        false
                    }
                    if (saved) {
                        lastSavedChapters = payload.chapters.map { it.copy() }
                        Log.i("ThesisViewModel", "Thesis session saved to VPS backend: $sessionId")
                        withContext(Dispatchers.Main) {
                            attachCurrentSessionWorkerListener(sessionId)
                        }
                    } else {
                        withContext(Dispatchers.IO) {
                            runSave()
                        }
                    }
                }
            }
            firebaseSaveJob?.cancel()
            if (immediate) {
                launchBackendSave()
            } else {
                firebaseSaveJob = viewModelScope.launch(Dispatchers.IO) {
                    delay(500)
                    val payload = buildThesisSessionPayload(sessionId)
                    val saved = runCatching { saveThesisSessionToBackend(backendUrl, payload) }.getOrElse { error ->
                        Log.w("ThesisViewModel", "VPS thesis session save failed", error)
                        false
                    }
                    if (saved) {
                        lastSavedChapters = payload.chapters.map { it.copy() }
                        Log.i("ThesisViewModel", "Thesis session saved to VPS backend: $sessionId")
                        withContext(Dispatchers.Main) {
                            attachCurrentSessionWorkerListener(sessionId)
                        }
                    } else {
                        withContext(Dispatchers.IO) {
                            runSave()
                        }
                    }
                }
            }
            return
        }

        if (immediate) {
            firebaseSaveJob?.cancel()
            runSave()
        } else {
            firebaseSaveJob?.cancel()
            firebaseSaveJob = viewModelScope.launch(Dispatchers.Main) {
                delay(500)
                withContext(Dispatchers.IO) {
                    runSave()
                }
            }
        }
    }

    fun setAutoSyncEnabled(enabled: Boolean) {
        _uiState.update { it.copy(autoSyncEnabled = enabled) }
        if (enabled) {
            attachCurrentSessionWorkerListener(_uiState.value.sessionId)
            saveSessionToFirebase(immediate = true)
        } else {
            detachCurrentSessionWorkerListener()
        }
    }

    fun refreshFromWorker() {
        val uid = getUid() ?: return
        val sessionId = _uiState.value.sessionId
        if (sessionId.isBlank()) return
        _uiState.update { it.copy(loadingState = "Refreshing from worker...") }
        viewModelScope.launch {
            val backendUrl = ApiKeys.THESIS_SESSION_BACKEND_URL.trim()
            val session = if (backendUrl.isNotBlank()) {
                runCatching {
                    withContext(Dispatchers.IO) { loadThesisSessionFromBackend("load", uid, sessionId) }
                }.getOrNull()
            } else {
                null
            }
            if (session != null) {
                viewModelScope.launch(Dispatchers.Default) {
                    val remoteChapters = session.chapters.map { chapter ->
                        reparseWorkerChapterForApp(chapter)
                    }
                    mergeRemoteWorkerChapters(session, remoteChapters)
                    _uiState.update { it.copy(loadingState = null, lastWorkerSyncTime = System.currentTimeMillis()) }
                }
                return@launch
            }
            FirebaseDatabase.getInstance()
                .reference
                .child("users")
                .child(uid)
                .child("thesis_sessions")
                .child(sessionId)
                .get()
                .addOnSuccessListener { snapshot ->
                    val legacySession = parseThesisSessionSnapshot(snapshot) ?: run {
                        _uiState.update { it.copy(loadingState = null) }
                        return@addOnSuccessListener
                    }
                    viewModelScope.launch(Dispatchers.Default) {
                        val remoteChapters = legacySession.chapters.map { chapter ->
                            reparseWorkerChapterForApp(chapter)
                        }
                        mergeRemoteWorkerChapters(legacySession, remoteChapters)
                        _uiState.update { it.copy(loadingState = null, lastWorkerSyncTime = System.currentTimeMillis()) }
                    }
                }
                .addOnFailureListener {
                    _uiState.update { it.copy(loadingState = null) }
                }
        }
    }

    fun pushLocalChanges() {
        saveSessionToFirebase(immediate = true)
    }

    fun toggleChapterSelection(chapterName: String) {
        _uiState.update { state ->
            val next = if (state.selectedChapters.contains(chapterName)) {
                state.selectedChapters - chapterName
            } else {
                state.selectedChapters + chapterName
            }
            state.copy(selectedChapters = next)
        }
    }

    fun clearChapterSelection() {
        _uiState.update { it.copy(selectedChapters = emptySet()) }
    }

    private fun syncRemoteThemeLayoutsOnStart() {
        viewModelScope.launch {
            try {
                val context = EduLabsApplication.instance.applicationContext
                syncRemoteThemeLayouts(context)
            } catch (_: Exception) { }
        }
    }

    fun tryLoadLatestSession() {
        if (FirebaseAuth.getInstance().currentUser != null) {
            viewModelScope.launch {
                val uid = getUid() ?: return@launch
                val backendUrl = ApiKeys.THESIS_SESSION_BACKEND_URL.trim()
                if (backendUrl.isNotBlank()) {
                    val session = runCatching {
                        withContext(Dispatchers.IO) { loadThesisSessionFromBackend("latest", uid) }
                    }.getOrNull()
                    if (session != null) {
                        restoreSessionWithFirestoreCache(session)
                        return@launch
                    }
                }
                loadLatestSessionFromFirebase()
            }
        }
    }

    private fun loadLatestSessionFromFirebase() {
        val uid = getUid() ?: return

        Log.d("ThesisViewModel", "Attempting to load latest session for user: $uid")

        FirebaseDatabase.getInstance()
            .reference
            .child("users")
            .child(uid)
            .child("thesis_sessions")
            .orderByChild("updatedAt")
            .limitToLast(1)
            .get()
            .addOnSuccessListener { snapshot ->
                Log.d(
                    "ThesisViewModel",
                    "Firebase fetch success. Children count: ${snapshot.childrenCount}"
                )
                val child = snapshot.children.firstOrNull() ?: run {
                    Log.i("ThesisViewModel", "No existing sessions found for user.")
                    return@addOnSuccessListener
                }
                val session = parseThesisSessionSnapshot(child) ?: run {
                    Log.w("ThesisViewModel", "Failed to parse session payload from Firebase.")
                    return@addOnSuccessListener
                }
                Log.i("ThesisViewModel", "Restoring session: ${session.sessionId}")
                restoreSessionWithFirestoreCache(session)
            }
            .addOnFailureListener {
                Log.e("ThesisViewModel", "Load session failed", it)
            }
    }

    fun loadPreviousSessions() {
        val uid = getUid() ?: return
        viewModelScope.launch {
            val backendUrl = ApiKeys.THESIS_SESSION_BACKEND_URL.trim()
            val backendSessions = if (backendUrl.isNotBlank()) {
                runCatching {
                    withContext(Dispatchers.IO) { listThesisSessionsFromBackend(uid, 50) }
                }.getOrElse { error ->
                    Log.w("ThesisViewModel", "VPS thesis session list failed; falling back to Firebase", error)
                    emptyList()
                }
            } else {
                emptyList()
            }
            if (backendSessions.isNotEmpty()) {
                _uiState.update { it.copy(previousSessions = backendSessions) }
                return@launch
            }

            FirebaseDatabase.getInstance()
                .getReference("users")
                .child(uid)
                .child("thesis_sessions")
                .limitToLast(50)
                .get()
                .addOnSuccessListener { snapshot ->

                    val sessions = snapshot.children.mapNotNull { child ->

                        val sessionId = child.child("sessionId")
                            .getValue(String::class.java)
                            ?: return@mapNotNull null

                        val title = child.child("thesisTitle")
                            .getValue(String::class.java)
                            ?: ""

                        val updatedAt = child.child("updatedAt")
                            .getValue(Long::class.java)
                            ?: 0L

                        val chaptersCount = child.child("chapters")
                            .childrenCount
                            .toInt()

                        SessionItem(
                            sessionId = sessionId,
                            thesisTitle = title,
                            timestamp = updatedAt,
                            chaptersCount = chaptersCount
                        )
                    }.sortedByDescending { it.timestamp }

                    _uiState.update {
                        it.copy(previousSessions = sessions)
                    }
                }
                .addOnFailureListener { e ->
                    _uiState.update {
                        it.copy(
                            status = "Failed to load sessions: ${e.localizedMessage}"
                        )
                    }
                }
        }
    }

    fun loadSession(sessionId: String) {
        val uid = getUid() ?: return

        _uiState.update {
            it.copy(
                processing = true,
                status = "Loading session...",
                activeChapterName = ""
            )
        }

        viewModelScope.launch {
            val backendUrl = ApiKeys.THESIS_SESSION_BACKEND_URL.trim()
            val session = if (backendUrl.isNotBlank()) {
                runCatching {
                    withContext(Dispatchers.IO) { loadThesisSessionFromBackend("load", uid, sessionId) }
                }.getOrNull()
            } else {
                null
            }
            if (session != null) {
                restoreSessionWithFirestoreCache(session)
                return@launch
            }

            FirebaseDatabase.getInstance()
                .reference
                .child("users")
                .child(uid)
                .child("thesis_sessions")
                .child(sessionId)
                .get()
                .addOnSuccessListener { snapshot ->
                    val legacy = parseThesisSessionSnapshot(snapshot)

                    if (legacy == null) {
                        _uiState.update {
                            it.copy(
                                processing = false,
                                status = "Session data not found"
                            )
                        }
                        return@addOnSuccessListener
                    }

                    restoreSessionWithFirestoreCache(legacy)
                }
                .addOnFailureListener { e ->
                    _uiState.update {
                        it.copy(
                            processing = false,
                            status = "Failed to load session: ${e.localizedMessage}"
                        )
                    }
                }
        }
    }

    private fun parseThesisSessionSnapshot(snapshot: com.google.firebase.database.DataSnapshot): ThesisSessionPayload? {
        runCatching { snapshot.getValue(ThesisSessionPayload::class.java) }
            .getOrNull()
            ?.let { return it }

        val rawValue = snapshot.value ?: return null
        val normalized = normalizeThesisSessionJson(gson.toJsonTree(rawValue))
        return runCatching {
            gson.fromJson(normalized, ThesisSessionPayload::class.java)
        }.getOrNull()
    }

    private fun normalizeThesisSessionJson(element: com.google.gson.JsonElement): com.google.gson.JsonElement {
        if (!element.isJsonObject) return element
        val root = element.asJsonObject
        root.getAsJsonArray("chapters")?.forEach { chapterElement ->
            if (chapterElement.isJsonObject) {
                normalizeChapterJson(chapterElement.asJsonObject)
            }
        }
        return root
    }

    private fun normalizeChapterJson(chapter: JsonObject) {
        val abbreviations = chapter.getAsJsonArray("abbreviations") ?: return
        val normalized = JsonArray()
        abbreviations.forEach { element ->
            when {
                element.isJsonObject -> normalized.add(element)
                element.isJsonPrimitive -> {
                    val text = element.asString.trim()
                    if (text.isNotBlank()) {
                        normalized.add(
                            JsonObject().apply {
                                addProperty("short_form", text)
                                addProperty("full_form", "")
                            }
                        )
                    }
                }
            }
        }
        chapter.add("abbreviations", normalized)
    }

    private fun attachCurrentSessionWorkerListener(sessionId: String) {
        val uid = getUid()
        if (uid.isNullOrBlank() || sessionId.isBlank()) return

        val backendUrl = ApiKeys.THESIS_SESSION_BACKEND_URL.trim()
        if (backendUrl.isNotBlank()) {
            if (vpsPollingJob != null && currentSessionListenerSessionId == sessionId) return
            detachCurrentSessionWorkerListener()

            currentSessionListenerSessionId = sessionId
            vpsPollingJob = viewModelScope.launch(Dispatchers.IO) {
                while (isActive && currentSessionListenerSessionId == sessionId) {
                    try {
                        val session = loadThesisSessionFromBackend("load", uid, sessionId)
                        if (session != null) {
                            val signature = remoteWorkerSignature(session)
                            if (signature.isNotBlank() && signature != lastRemoteWorkerSignature) {
                                lastRemoteWorkerSignature = signature
                                val remoteChapters = session.chapters.map { chapter ->
                                    reparseWorkerChapterForApp(chapter)
                                }
                                withContext(Dispatchers.Default) {
                                    mergeRemoteWorkerChapters(session, remoteChapters)
                                }
                            }
                        }
                    } catch (e: Exception) {
                        Log.w("ThesisViewModel", "VPS session poll failed: ${e.message}")
                    }
                    delay(12000) // Poll every 12 seconds
                }
            }
            return
        }

        val existingRef = currentSessionListenerRef
        val existingListener = currentSessionListener
        if (existingRef != null && existingListener != null && currentSessionListenerSessionId == sessionId) return

        detachCurrentSessionWorkerListener()

        val ref = FirebaseDatabase.getInstance()
            .reference
            .child("users")
            .child(uid)
            .child("thesis_sessions")
            .child(sessionId)

        val listener = object : ValueEventListener {
            override fun onDataChange(snapshot: DataSnapshot) {
                val session = parseThesisSessionSnapshot(snapshot) ?: return
                val signature = remoteWorkerSignature(session)
                if (signature.isBlank() || signature == lastRemoteWorkerSignature) return
                lastRemoteWorkerSignature = signature

                remoteSessionMergeJob?.cancel()
                remoteSessionMergeJob = viewModelScope.launch(Dispatchers.Default) {
                    val remoteChapters = session.chapters.map { chapter ->
                        reparseWorkerChapterForApp(chapter)
                    }
                    mergeRemoteWorkerChapters(session, remoteChapters)
                }
            }

            override fun onCancelled(error: DatabaseError) {
                Log.w("ThesisViewModel", "Worker session listener cancelled: ${error.message}")
            }
        }

        currentSessionListenerRef = ref
        currentSessionListener = listener
        currentSessionListenerSessionId = sessionId
        ref.addValueEventListener(listener)
    }

    private fun detachCurrentSessionWorkerListener() {
        vpsPollingJob?.cancel()
        vpsPollingJob = null

        val ref = currentSessionListenerRef
        val listener = currentSessionListener
        if (ref != null && listener != null) {
            ref.removeEventListener(listener)
        }
        currentSessionListenerRef = null
        currentSessionListener = null
        currentSessionListenerSessionId = ""
        remoteSessionMergeJob?.cancel()
        remoteSessionMergeJob = null
        lastRemoteWorkerSignature = ""
        lastNotifiedChapterSuccessSignature = ""
    }

    private fun chapterSuccessNotificationSignature(sessionId: String, chapter: Chapter): String {
        return listOf(
            sessionId,
            chapter.name.lowercase(),
            chapter.syncedAt.toString(),
            chapter.completedByLabel,
            chapter.completedByProvider,
            chapter.completedByModel
        ).joinToString("|")
    }

    private fun notifyChapterCompleted(sessionId: String, chapter: Chapter) {
        val context = EduLabsApplication.instance.applicationContext
        val channelId = "thesis_worker_updates"
        val notificationId = (sessionId.hashCode() * 31 + chapter.name.hashCode()).hashCode()
        val intent = android.content.Intent(context, ThesisAnalyzerActivity::class.java).apply {
            flags = android.content.Intent.FLAG_ACTIVITY_NEW_TASK or android.content.Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra("session_id", sessionId)
            putExtra("chapter_name", chapter.name)
        }
        val pendingIntent = PendingIntent.getActivity(
            context,
            notificationId,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val manager = NotificationManagerCompat.from(context)
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
            val systemManager = context.getSystemService(NotificationManager::class.java)
            val channel = NotificationChannel(
                channelId,
                "Thesis Worker Updates",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Alerts when the VPS worker completes a thesis chapter"
            }
            systemManager?.createNotificationChannel(channel)
        }

        val completedBy = chapter.completedByLabel.ifBlank {
            listOf(chapter.completedByProvider, chapter.completedByModel)
                .filter { it.isNotBlank() }
                .joinToString(" / ")
        }

        val title = "Chapter completed: ${chapter.name}"
        val body = if (completedBy.isNotBlank()) {
            "Completed by $completedBy"
        } else {
            "The VPS worker finished this chapter."
        }

        val notification = NotificationCompat.Builder(context, channelId)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setContentIntent(pendingIntent)
            .build()

        runCatching { manager.notify(notificationId, notification) }
            .onFailure { Log.w("ThesisViewModel", "Chapter completion notification failed", it) }
    }

    private fun remoteWorkerSignature(session: ThesisSessionPayload): String {
        if (session.sessionId.isBlank()) return ""
        return session.chapters.joinToString("|") { chapter ->
            listOf(
                chapter.name,
                chapter.status.name,
                chapter.workerStatus,
                chapter.retryCount.toString(),
                chapter.lastRetryAt.toString(),
                chapter.lastWorkerError,
                chapter.lockedBy,
                chapter.lockedUntil.toString(),
                chapter.syncedAt.toString(),
                chapter.completedByProvider,
                chapter.completedByModel,
                chapter.completedByLabel,
                chapter.rawJson.hashCode().toString(),
                chapter.content.hashCode().toString(),
                chapter.tables.size.toString(),
                chapter.figures.size.toString(),
                chapter.charts.size.toString(),
                chapter.chapterReferences.size.toString()
            ).joinToString(":")
        }
    }

    private fun shouldMergeRemoteWorkerChapter(local: Chapter, remote: Chapter): Boolean {
        if (!local.name.equals(remote.name, ignoreCase = true)) return false
        if (remote.syncedAt > local.syncedAt) return true
        if (remote.workerStatus != local.workerStatus) return true
        if (remote.retryCount != local.retryCount) return true
        if (remote.lastRetryAt != local.lastRetryAt) return true
        if (remote.lastWorkerError != local.lastWorkerError) return true
        if (remote.lockedBy != local.lockedBy) return true
        if (remote.lockedUntil != local.lockedUntil) return true
        if (remote.completedByProvider != local.completedByProvider) return true
        if (remote.completedByModel != local.completedByModel) return true
        if (remote.completedByLabel != local.completedByLabel) return true
        if (remote.status != local.status) return true
        if (remote.rawJson != local.rawJson) return true
        if (remote.content != local.content) return true
        return false
    }

    private fun mergeRemoteWorkerChapter(local: Chapter, remote: Chapter): Chapter {
        val newAuditEntries = mutableListOf<AuditEntry>()
        if (local.status != Chapter.ChapterStatus.SUCCESS && remote.status == Chapter.ChapterStatus.SUCCESS) {
            newAuditEntries.add(
                AuditEntry(
                    action = "Worker Sync",
                    provider = remote.completedByProvider,
                    model = remote.completedByModel,
                    notes = "Completed and synced successfully"
                )
            )
        } else if (remote.status == Chapter.ChapterStatus.ERROR && local.status != Chapter.ChapterStatus.ERROR) {
            newAuditEntries.add(
                AuditEntry(
                    action = "Worker Error",
                    provider = remote.completedByProvider,
                    model = remote.completedByModel,
                    notes = remote.lastWorkerError ?: "Failed during generation"
                )
            )
        }

        val mergedTrail = local.auditTrail + remote.auditTrail + newAuditEntries
        val distinctTrail = mergedTrail.distinctBy { "${it.action}_${it.timestamp}_${it.notes}" }

        val merged = remote.copy(
            workerPrompt = remote.workerPrompt.ifBlank { local.workerPrompt },
            workerPromptUpdatedAt = remote.workerPromptUpdatedAt.takeIf { it > 0L } ?: local.workerPromptUpdatedAt,
            syncEnabled = remote.syncEnabled || local.syncEnabled,
            textBoxes = remote.textBoxes.ifEmpty { local.textBoxes },
            auditTrail = distinctTrail
        )
        return if (merged.textBoxes.isEmpty() && merged.status == Chapter.ChapterStatus.SUCCESS) {
            merged.copy(textBoxes = ensureChapterTextBoxes(merged))
        } else {
            merged
        }
    }

    private fun isVpsWrittenChapter(chapter: Chapter): Boolean {
        return chapter.syncedAt > 0L ||
            chapter.workerStatus.equals("synced", ignoreCase = true) ||
            chapter.completedByLabel.isNotBlank() ||
            chapter.completedByProvider.isNotBlank() ||
            chapter.completedByModel.isNotBlank()
    }

    private fun mergeRemoteWorkerChapters(session: ThesisSessionPayload, remoteChapters: List<Chapter>) {
        if (session.sessionId.isBlank() || session.sessionId != _uiState.value.sessionId) return
        val remoteByName = remoteChapters.associateBy { it.name.lowercase() }
        var changed = false
        val completedChapters = mutableListOf<Chapter>()

        _uiState.update { state ->
            val mergedChapters = state.chapters.map { local ->
                val remote = remoteByName[local.name.lowercase()] ?: return@map local
                if (shouldMergeRemoteWorkerChapter(local, remote)) {
                    changed = true
                    val merged = mergeRemoteWorkerChapter(local, remote)
                    if (
                        local.status != Chapter.ChapterStatus.SUCCESS &&
                        merged.status == Chapter.ChapterStatus.SUCCESS &&
                        merged.syncedAt > 0L
                    ) {
                        completedChapters += merged
                    }
                    merged
                } else {
                    local
                }
            }
            if (!changed) return@update state

            state.copy(
                chapters = mergedChapters,
                vpsAutoCompleteEnabled = session.vpsAutoCompleteEnabled || state.vpsAutoCompleteEnabled,
                progressCurrent = session.currentChapter.takeIf { it > 0 } ?: state.progressCurrent,
                progressTotal = session.totalChapters.takeIf { it > 0 } ?: state.progressTotal,
                completionPercent = computeCompletionPercent(mergedChapters),
                hasErrors = mergedChapters.any { it.status == Chapter.ChapterStatus.ERROR },
                processing = false,
                lastWorkerSyncTime = System.currentTimeMillis(),
                activeChapterName = mergedChapters.firstOrNull {
                    it.workerStatus.equals("running", ignoreCase = true) ||
                        it.status == Chapter.ChapterStatus.LOADING
                }?.name.orEmpty(),
                status = when {
                    mergedChapters.any { it.workerStatus.equals("running", ignoreCase = true) } -> "VPS worker is writing chapters"
                    mergedChapters.any { it.workerStatus.equals("queued", ignoreCase = true) } -> "Waiting for VPS worker"
                    mergedChapters.any { it.workerStatus.equals("synced", ignoreCase = true) } -> "Worker updates synced"
                    else -> state.status
                }
            )
        }

        completedChapters.forEach { chapter ->
            val signature = chapterSuccessNotificationSignature(session.sessionId, chapter)
            if (signature != lastNotifiedChapterSuccessSignature) {
                lastNotifiedChapterSuccessSignature = signature
                notifyChapterCompleted(session.sessionId, chapter)
            }
        }

        if (changed) {
            viewModelScope.launch {
                if (areAllNormalChaptersCompleted(_uiState.value.chapters)) {
                    _uiState.update {
                        it.copy(
                            processing = true,
                            status = "Generating thesis lists and references..."
                        )
                    }
                    assembleAutoGeneratedFrontMatter()
                    saveSessionToFirebase(immediate = true)
                    _uiState.update {
                        it.copy(
                            processing = false,
                            status = "All chapters and lists completed"
                        )
                    }
                } else {
                    saveSessionToFirebase()
                }
            }
        }
    }

    private suspend fun reparseWorkerChapterForApp(chapter: Chapter): Chapter {
        val preferWorkerRawJson = isVpsWrittenChapter(chapter)
        val workerRawJson = when {
            preferWorkerRawJson && chapter.rawJson.isNotBlank() -> chapter.rawJson
            preferWorkerRawJson && looksLikeJsonObject(chapter.content) -> chapter.content
            preferWorkerRawJson && (
                chapter.content.contains("\"chapter_name\"", ignoreCase = true) ||
                    chapter.content.contains("\"sections\"", ignoreCase = true) ||
                    chapter.content.contains("\"tables\"", ignoreCase = true) ||
                    chapter.content.contains("\"chapter_references\"", ignoreCase = true)
                ) -> chapter.content
            chapter.rawJson.isNotBlank() -> chapter.rawJson
            looksLikeJsonObject(chapter.content) -> chapter.content
            chapter.content.contains("\"chapter_name\"", ignoreCase = true) ||
                chapter.content.contains("\"sections\"", ignoreCase = true) ||
                chapter.content.contains("\"tables\"", ignoreCase = true) ||
                chapter.content.contains("\"chapter_references\"", ignoreCase = true) -> chapter.content
            else -> ""
        }

        val parsedChapterFromRaw = parseChapterFromRawJson(workerRawJson, chapter.name)
        val parsedResultsFromRaw = parseResultsFromRawJson(workerRawJson)
        val schema = chapterSchemas[chapter.name.lowercase()]
        val parsedValueFromRaw = if (workerRawJson.isNotBlank()) {
            runCatching { parseGeneratedChapterValue(chapter.name, workerRawJson, schema) }.getOrNull()
        } else {
            null
        }

        val rawTables = when {
            parsedResultsFromRaw != null -> parsedResultsFromRaw.tables.map(::normalizeResultTable)
            parsedChapterFromRaw != null -> (parsedChapterFromRaw.tables + parsedChapterFromRaw.sections.mapNotNull { it.table })
                .map(::normalizeThesisTable)
            else -> emptyList()
        }
        val rawCharts = when {
            parsedResultsFromRaw != null -> parsedResultsFromRaw.charts.map(::normalizeResultChart)
            parsedChapterFromRaw != null -> sanitizeChartsForUse(parsedChapterFromRaw.charts, chapter.name).map(::normalizeResultChart)
            else -> emptyList()
        }
        val rawFigures = parsedChapterFromRaw?.let(::collectChapterFigures).orEmpty()
        val rawReferences = parsedChapterFromRaw
            ?.let(::collectChapterReferences)
            .orEmpty()
            .filter { it.referenceText.isNotBlank() || it.citation.isNotBlank() || !it.pmid.isNullOrBlank() }

        val restoredContent = when {
            preferWorkerRawJson && parsedValueFromRaw != null && schema != null ->
                runCatching { schema.formatter(parsedValueFromRaw) }.getOrNull().orEmpty()
            preferWorkerRawJson && parsedChapterFromRaw != null && isMeaningfulThesisChapter(parsedChapterFromRaw) ->
                formatChapterPreview(parsedChapterFromRaw)
            preferWorkerRawJson && parsedResultsFromRaw != null ->
                formatResultsPreview(parsedResultsFromRaw)
            chapter.content.isNotBlank() && !looksLikeJsonObject(chapter.content) && !isWeakChapterContent(chapter.content) ->
                chapter.content
            parsedValueFromRaw != null && schema != null -> runCatching { schema.formatter(parsedValueFromRaw) }.getOrNull().orEmpty()
            parsedChapterFromRaw != null && isMeaningfulThesisChapter(parsedChapterFromRaw) -> formatChapterPreview(parsedChapterFromRaw)
            parsedResultsFromRaw != null -> formatResultsPreview(parsedResultsFromRaw)
            workerRawJson.isNotBlank() && looksLikeJsonObject(workerRawJson) -> workerRawJson
            else -> chapter.content
        }

        val restoredReferences = (chapter.chapterReferences + rawReferences)
            .filter { it.referenceText.isNotBlank() || it.citation.isNotBlank() || !it.pmid.isNullOrBlank() }
            .distinctBy { ref -> referenceIdentity(ref) ?: canonicalReferenceTextKey(ref.referenceText) }

        val restoredStatus = if (
            chapter.workerStatus.equals("synced", ignoreCase = true) &&
            restoredContent.isNotBlank() &&
            !isWeakChapterContent(restoredContent)
        ) {
            Chapter.ChapterStatus.SUCCESS
        } else {
            chapter.status
        }

        val rawSections = when {
            parsedChapterFromRaw != null -> parsedChapterFromRaw.sections
            parsedValueFromRaw != null -> convertStructuredPayloadToSections(chapter.name, parsedValueFromRaw)
            else -> emptyList()
        }

        val reparsed = chapter.copy(
            content = restoredContent,
            rawJson = chapter.rawJson.ifBlank { workerRawJson },
            status = restoredStatus,
            errorMessage = if (restoredStatus == Chapter.ChapterStatus.SUCCESS) null else chapter.errorMessage,
            tables = chapter.tables.ifEmpty { rawTables },
            charts = chapter.charts.ifEmpty { rawCharts },
            figures = chapter.figures.ifEmpty { rawFigures },
            chapterReferences = restoredReferences,
            sections = chapter.sections.ifEmpty { rawSections }
        )
        return if (reparsed.status == Chapter.ChapterStatus.SUCCESS) {
            reparsed.copy(textBoxes = ensureChapterTextBoxes(reparsed))
        } else {
            reparsed
        }
    }


    private fun restoreSession(session: ThesisSessionPayload) {
        Log.d(
            "ThesisViewModel",
            "Restore session: ${session.thesisTitle}, Chapters=${session.chapters.size}"
        )

        restorePubMedCachesFromSession(session)

        viewModelScope.launch {
            _uiState.update { it.copy(loadingState = "Restoring session...") }
            val restoredChapters = mutableListOf<Chapter>()
            val total = session.chapters.size

            withContext(Dispatchers.Default) {
                session.chapters.forEachIndexed { index, chapter ->
                    _uiState.update {
                        it.copy(loadingState = "Parsing chapter ${index + 1} of $total: ${chapter.name}")
                    }

                    val refreshedFigures = try {
                        chapter.figures
                    } catch (e: Exception) {
                        emptyList()
                    }

                    val workerRawJson = when {
                        chapter.rawJson.isNotBlank() -> chapter.rawJson
                        chapter.content.takeIf { looksLikeJsonObject(it) } != null -> chapter.content
                        chapter.content.contains("\"chapter_name\"", ignoreCase = true) ||
                            chapter.content.contains("\"sections\"", ignoreCase = true) ||
                            chapter.content.contains("\"tables\"", ignoreCase = true) -> chapter.content
                        else -> ""
                    }
                    val parsedChapterFromRaw = parseChapterFromRawJson(workerRawJson, chapter.name)
                    val parsedFromRaw = parseResultsFromRawJson(workerRawJson)
                    val rawTables = parsedFromRaw?.tables?.map(::normalizeResultTable).orEmpty()
                    val rawCharts = parsedFromRaw?.charts?.map(::normalizeResultChart).orEmpty()
                    val rawReferences = parsedChapterFromRaw
                        ?.let(::collectChapterReferences)
                        .orEmpty()
                        .filter { it.referenceText.isNotBlank() || it.citation.isNotBlank() || !it.pmid.isNullOrBlank() }
                    val restoredReferences = (
                        chapter.chapterReferences +
                            rawReferences.mapIndexed { idx, reference ->
                                reference.copy(citation = reference.citation.ifBlank { serializedCitation(idx + 1) })
                            }
                        )
                        .filter { it.referenceText.isNotBlank() || it.citation.isNotBlank() || !it.pmid.isNullOrBlank() }
                        .distinctBy { ref ->
                            referenceIdentity(ref) ?: canonicalReferenceTextKey(ref.referenceText)
                        }

                    val restoredTables = if (chapter.tables.isEmpty()) {
                        rawTables
                    } else {
                        chapter.tables.mapIndexed { idx, table ->
                            val normalized = normalizeThesisTable(table)
                            if (normalized.headers.isNotEmpty() && normalized.rows.isNotEmpty()) {
                                normalized
                            } else {
                                rawTables.firstOrNull { it.title.equals(table.title, ignoreCase = true) }
                                    ?: rawTables.getOrNull(idx)
                                    ?: normalized
                            }
                        }
                    }

                    val restoredCharts = if (chapter.charts.isEmpty()) {
                        rawCharts
                    } else {
                        chapter.charts.mapIndexed { idx, chart ->
                            val normalized = normalizeResultChart(chart)
                            if (normalized.datasets.any { it.values.isNotEmpty() }) {
                                normalized
                            } else {
                                rawCharts.firstOrNull { it.title.equals(chart.title, ignoreCase = true) }
                                    ?: rawCharts.getOrNull(idx)
                                    ?: normalized
                            }
                        }
                    }
                    val schema = chapterSchemas[chapter.name.lowercase()]
                    val parsedValueFromRaw = if (workerRawJson.isNotBlank()) {
                        runCatching { parseGeneratedChapterValue(chapter.name, workerRawJson, schema) }.getOrNull()
                    } else {
                        null
                    }
                    val restoredContent = when {
                        chapter.content.isNotBlank() && !looksLikeJsonObject(chapter.content) && !isWeakChapterContent(chapter.content) -> chapter.content
                        parsedValueFromRaw != null && schema != null -> runCatching { schema.formatter(parsedValueFromRaw) }.getOrNull().orEmpty()
                        parsedChapterFromRaw != null && isMeaningfulThesisChapter(parsedChapterFromRaw) -> formatChapterPreview(parsedChapterFromRaw)
                        parsedFromRaw != null -> formatResultsPreview(parsedFromRaw)
                        workerRawJson.isNotBlank() && looksLikeJsonObject(workerRawJson) -> workerRawJson
                        else -> chapter.content
                    }
                    val restoredStatus = if (session.vpsAutoCompleteEnabled) {
                        chapter.status
                    } else if (
                        chapter.status == Chapter.ChapterStatus.SUCCESS &&
                        (restoredContent.isBlank() || isWeakChapterContent(restoredContent)) &&
                        chapter.name.lowercase() !in autoGeneratedChapterNames
                    ) {
                        Chapter.ChapterStatus.ERROR
                    } else {
                        chapter.status
                    }

                    val reparsed = chapter.copy(
                        content = restoredContent,
                        status = restoredStatus,
                        errorMessage = if (restoredStatus == Chapter.ChapterStatus.ERROR) {
                            chapter.errorMessage ?: "Worker output could not be parsed into a complete chapter"
                        } else {
                            chapter.errorMessage
                        },
                        figures = refreshedFigures,
                        tables = restoredTables,
                        charts = restoredCharts,
                        chapterReferences = restoredReferences,
                        rawJson = chapter.rawJson.ifBlank { workerRawJson }
                    )
                    restoredChapters.add(reparsed)
                }
            }

            val normalizedRestoredChapters = normalizeRestoredChapterList(restoredChapters)

            val restoredPubMedFigureCheckedPmids = (
                session.pubMedFigureCheckedPmids +
                    session.pubMedFigures.map { it.pmid }
                )
                .map { it.trim() }
                .filter { it.isNotBlank() }
                .distinct()
            session.pubMedFigures
                .groupBy { it.pmid.trim() }
                .filterKeys { it.isNotBlank() }
                .forEach { (pmid, figures) -> pubMedFigureCache[pmid] = figures }
            session.verifiedPubMedAbstractSources
                .filter { it.pmid.isNotBlank() }
                .forEach { source -> pubMedAbstractSourceCache[source.pmid.trim()] = source }
            val restoredAbstractSources = cachedAbstractSourcesSnapshot()
            val restoredVerifiedReferences = (
                (session.cachedVerifiedReferences + session.verifiedPubMedReferences)
                    .ifEmpty {
                        normalizedRestoredChapters.flatMap { it.chapterReferences } +
                            parseReferencesVariable(session.variables)
                    }
                )
                .filter { it.hasRequiredPmid() }
                .distinctBy { it.pmid?.trim().orEmpty() }
            seedVerifiedReferenceCache(restoredVerifiedReferences)

            _uiState.update {
                it.copy(
                    sessionId = session.sessionId.ifBlank { newSessionId() },
                    thesisTitle = session.thesisTitle,
                    variables = ensureDiseaseTopicVariable(session.variables, session.thesisTitle),
                    chapters = normalizedRestoredChapters,
                    selectedProvider = session.selectedProvider.ifBlank { it.selectedProvider },
                    collegeLogoUri = session.collegeLogoUri,
                    pdfTheme = session.pdfTheme.ifBlank { it.pdfTheme },
                    verifiedPubMedReferences = restoredVerifiedReferences,
                    verifiedPubMedAbstractSources = restoredAbstractSources,
                    referenceSequenceCounter = session.referenceSequenceCounter.takeIf { it > 0 }
                        ?: nextReferenceSequence(restoredVerifiedReferences),
                    pubMedFigureCheckedPmids = restoredPubMedFigureCheckedPmids,
                    pubMedFigures = session.pubMedFigures,
                    vpsAutoCompleteEnabled = session.vpsAutoCompleteEnabled,
                    autoSyncEnabled = session.autoSyncEnabled,
                    lastWorkerSyncTime = session.lastWorkerSyncTime.takeIf { it > 0 } ?: System.currentTimeMillis(),
                    exportMargin = session.exportMargin.ifBlank { it.exportMargin },
                    exportFont = session.exportFont.ifBlank { it.exportFont },
                    exportLineSpacing = session.exportLineSpacing.ifBlank { it.exportLineSpacing },
                    exportLogoPlacement = session.exportLogoPlacement.ifBlank { it.exportLogoPlacement },
                    exportPageNumbering = session.exportPageNumbering.ifBlank { it.exportPageNumbering },
                    exportHeaderFooter = session.exportHeaderFooter,
                    exportWatermark = session.exportWatermark,
                    exportAutoToc = session.exportAutoToc,
                    exportAutoLists = session.exportAutoLists,
                    promptSectionSplittingEnabled = session.promptSectionSplittingEnabled,
                    promptMaxChars = session.promptMaxChars.coerceIn(4000, 30000),
                    masterChartColumns = session.masterChartColumns,
                    masterChartCsv = session.masterChartCsv,
                    masterChartGeneratedAt = session.masterChartGeneratedAt,
                    masterDataFileName = session.masterDataFileName,
                    masterDataHeaders = session.masterDataHeaders,
                    masterDataRows = session.masterDataRows,
                    masterDataMappings = session.masterDataMappings,
                    masterDataValidationIssues = session.masterDataValidationIssues,
                    masterDataResultTables = session.masterDataResultTables,
                    masterDataImportedAt = session.masterDataImportedAt,
                    aiLogs = session.aiLogs,
                    progressCurrent = session.currentChapter,
                    progressTotal = session.totalChapters,
                    completionPercent = session.completionPercent,
                    processing = false,
                    hasErrors = normalizedRestoredChapters.any { ch ->
                        ch.status == Chapter.ChapterStatus.ERROR
                    },
                    status = "Session restored. Syncing existing verified cache only.",
                    activeChapterName = "",
                    loadingState = null 
                )
            }

            lastSavedChapters = normalizedRestoredChapters.map { it.copy() }
            if (_uiState.value.autoSyncEnabled) {
                attachCurrentSessionWorkerListener(_uiState.value.sessionId)
            }
            uploadCurrentVerifiedReferenceCacheToFirestore("session restore")
        }
    }

    private fun normalizeRestoredChapterList(restoredChapters: List<Chapter>): List<Chapter> {
        val restoredByName = restoredChapters.associateBy { it.name.lowercase() }
        val normalized = initialChapterList().map { expected ->
            restoredByName[expected.name.lowercase()] ?: expected
        }
        val knownNames = normalized.map { it.name.lowercase() }.toSet()
        val extraChapters = restoredChapters.filter { it.name.lowercase() !in knownNames }
        return normalized + extraChapters
    }

    private fun isChapterIncompleteAfterRestore(chapter: Chapter): Boolean {
        if (chapter.name.lowercase() in autoGeneratedChapterNames) return false
        if (chapter.status != Chapter.ChapterStatus.SUCCESS) return true
        return chapter.content.isBlank() &&
            chapter.rawJson.isBlank() &&
            chapter.tables.isEmpty() &&
            chapter.figures.isEmpty() &&
            chapter.charts.isEmpty() &&
            chapter.chapterReferences.isEmpty()
    }

    private fun isChapterQueueCandidateForVps(chapter: Chapter): Boolean {
        if (chapter.name.lowercase() in autoGeneratedChapterNames) return false
        return true
    }

    private fun areAllNormalChaptersCompleted(chapters: List<Chapter>): Boolean {
        val normalChapters = chapters.filter { it.name.lowercase() !in autoGeneratedChapterNames }
        return normalChapters.isNotEmpty() && normalChapters.all { it.status == Chapter.ChapterStatus.SUCCESS }
    }

    private suspend fun completeRemainingRestoredChaptersAndGenerateLists(
        restoredReferencesFromRaw: Boolean,
        forceGenerateLists: Boolean
    ) {
        if (_uiState.value.processing) return

        val pendingNames = _uiState.value.chapters
            .filter {
                if (_uiState.value.vpsAutoCompleteEnabled) {
                    isChapterQueueCandidateForVps(it)
                } else {
                    isChapterIncompleteAfterRestore(it)
                }
            }
            .map { it.name }
            .filter { it.isNotBlank() }
            .toSet()

        if (pendingNames.isEmpty() && !forceGenerateLists) {
            if (restoredReferencesFromRaw) saveSessionToFirebase()
            _uiState.update { state -> state.copy(status = "Session restored") }
            return
        }

        val appContext = EduLabsApplication.instance.applicationContext
        startBackgroundWork(appContext, "Completing restored thesis session")
        try {
            if (pendingNames.isNotEmpty()) {
                _uiState.update { state ->
                    val updated = state.chapters.map { chapter ->
                        if (chapter.name in pendingNames) {
                            chapter.copy(
                                status = Chapter.ChapterStatus.LOADING,
                                errorMessage = null
                            )
                        } else {
                            chapter
                        }
                    }
                    state.copy(
                        chapters = updated,
                        processing = true,
                        hasErrors = false,
                        status = "Completing restored chapters: ${pendingNames.joinToString(", ")}"
                    )
                }
                generateAllChapters(
                    targetChapterNames = pendingNames,
                    finalStatus = "Restored chapters complete; generating lists"
                )
            }

            if (areAllNormalChaptersCompleted(_uiState.value.chapters)) {
                _uiState.update {
                    it.copy(
                        processing = true,
                        status = "Generating thesis lists and references..."
                    )
                }
                assembleAutoGeneratedFrontMatter()
                saveSessionToFirebase(immediate = true)
                _uiState.update {
                    it.copy(
                        processing = false,
                        hasErrors = it.chapters.any { chapter -> chapter.status == Chapter.ChapterStatus.ERROR },
                        completionPercent = computeCompletionPercent(it.chapters),
                        status = "Session restored and completed"
                    )
                }
            } else {
                _uiState.update {
                    it.copy(
                        processing = if (it.vpsAutoCompleteEnabled) false else it.processing,
                        hasErrors = it.chapters.any { chapter -> chapter.status == Chapter.ChapterStatus.ERROR },
                        completionPercent = computeCompletionPercent(it.chapters),
                        status = if (it.vpsAutoCompleteEnabled) "Queued for VPS auto-complete" else "Restored chapters generating..."
                    )
                }
            }
        } finally {
            stopBackgroundWork(appContext)
        }
    }

    private fun autoRetryRestoredStuckChapters() {
        val retryNames = _uiState.value.chapters
            .filter { chapter ->
                chapter.status == Chapter.ChapterStatus.ERROR ||
                    chapter.status == Chapter.ChapterStatus.LOADING
            }
            .map { it.name }
            .filter { it.isNotBlank() }
            .toSet()

        if (retryNames.isEmpty() || _uiState.value.processing) return

        viewModelScope.launch {
            val appContext = EduLabsApplication.instance.applicationContext
            startBackgroundWork(appContext, "Auto retrying restored thesis chapters")
            try {
                _uiState.update { state ->
                    val updated = state.chapters.map { chapter ->
                        if (chapter.name in retryNames) {
                            chapter.copy(
                                status = Chapter.ChapterStatus.LOADING,
                                errorMessage = null
                            )
                        } else {
                            chapter
                        }
                    }
                    state.copy(
                        chapters = updated,
                        processing = true,
                        hasErrors = updated.any { it.status == Chapter.ChapterStatus.ERROR },
                        status = "Auto retrying restored chapters: ${retryNames.joinToString(", ")}"
                    )
                }
                generateAllChapters(
                    targetChapterNames = retryNames,
                    finalStatus = "Auto retry complete"
                )
            } finally {
                stopBackgroundWork(appContext)
            }
        }
    }

    private suspend fun recheckRestoredReferences() {
        val appContext = EduLabsApplication.instance.applicationContext
        startBackgroundWork(appContext, "Rechecking PubMed references")
        val state = _uiState.value
        val chapters = state.chapters.toMutableList()
        var changed = false

        try {
            for ((chapterIndex, chapter) in chapters.withIndex()) {
                if (chapter.chapterReferences.isEmpty()) continue

                _uiState.update {
                    it.copy(status = "Rechecking restored references: ${chapter.name}")
                }

                val verified = if (requiresPubMedCitations(chapter.name)) {
                    runCatching { requirePubMedVerifiedReferences(chapter.chapterReferences, chapter.name) }
                        .getOrElse { chapter.chapterReferences }
                } else {
                    val rechecked = verifyReferencesWithPubMed(chapter.chapterReferences)
                        .filter { it.hasRequiredPmid() }
                        .mapIndexed { index, ref -> ref.copy(citation = ref.citation.ifBlank { serializedCitation(index + 1) }) }
                    rechecked.ifEmpty { chapter.chapterReferences }
                }

                if (verified != chapter.chapterReferences) {
                    chapters[chapterIndex] = chapter.copy(chapterReferences = verified)
                    changed = true
                    _uiState.update { it.copy(chapters = chapters.toList()) }
                }
            }
            
            val variableReferences = parseReferencesVariable(_uiState.value.variables)
            if (variableReferences.isNotEmpty()) {
                _uiState.update { it.copy(status = "Rechecking restored References_Vancouver") }
                val verifiedVariableReferences = verifyReferencesWithPubMed(variableReferences)
                    .filter { it.hasRequiredPmid() }
                if (verifiedVariableReferences.isNotEmpty()) {
                    updateVariable("References_Vancouver", formatReferencesForVariable(verifiedVariableReferences))
                    changed = true
                }
            }
            if (changed) {
                if (areAllNormalChaptersCompleted(_uiState.value.chapters)) {
                    assembleAutoGeneratedFrontMatter()
                    saveSessionToFirebase(immediate = true)
                }
            }
        } finally {
            stopBackgroundWork(appContext)
        }
    }

    private fun shouldRebuildReferenceSections(variables: List<Variable>, chapters: List<Chapter>): Boolean {
        val referencesVariableMissing = parseReferencesVariable(variables).isEmpty()
        val chapterReferencesPresent = chapters.any { chapter ->
            chapter.chapterReferences.isNotEmpty() || chapter.rawJson.contains("\"chapter_references\"", ignoreCase = true)
        }
        val autoReferenceChaptersMissing = chapters.none { chapter ->
            chapter.name.equals("References", ignoreCase = true) ||
                chapter.name.equals("Bibliography", ignoreCase = true) ||
                chapter.name.equals("List of References", ignoreCase = true)
        }
        return referencesVariableMissing && (chapterReferencesPresent || autoReferenceChaptersMissing)
    }

    override fun onCleared() {
        detachCurrentSessionWorkerListener()
        super.onCleared()
    }


// AI Request/Response Model definitions used within ViewModel

    data class GeminiRequest(
        val contents: List<GeminiContent>,
        val generationConfig: GeminiGenerationConfig
    )

    data class GeminiContent(
        val parts: List<GeminiPart>
    )

    data class GeminiPart(
        val text: String
    )

    data class GeminiGenerationConfig(
        val temperature: Double = 0.2,
        val maxOutputTokens: Int = 8192,
        val responseMimeType: String = "application/json"
    )

    data class CloudflareRequest(
        val messages: List<CloudflareMessage>,
        val temperature: Double = 0.2,
        @SerializedName("max_tokens") val maxTokens: Int = 6000,
        val stream: Boolean = false
    )

    data class CloudflareMessage(
        val role: String,
        val content: String
    )

    data class CohereRequest(
        val model: String,
        val message: String,
        val temperature: Double
    )

    data class ReplicateRequest(
        val input: ReplicateInput
    )

    data class ReplicateInput(
        val prompt: String,
        val system_prompt: String,
        val temperature: Double,
        @SerializedName("max_new_tokens") val max_new_tokens: Int
    )
}
// Add inside ThesisViewModel class

private data class TableDrawingState(
    var y: Float,
    var contentStream: PDPageContentStream?
)

private fun drawPdfTable(
    pdf: PDDocument,
    state: TableDrawingState,
    headers: List<String>,
    rows: List<List<String>>,
    footnote: String?,
    pageSize: PDRectangle,
    margin: Float,
    lineSpacing: Float = 14f,
    headerFillColor: Int = Color.LTGRAY,
    accentColor: Int = Color.BLACK,
    tableLayout: TableLayout = TableLayout.FULL_GRID,
    ruleColor: Int = Color.BLACK,
    newPage: () -> PDPageContentStream
): TableDrawingState {
    val normalizedHeaders = headers.ifEmpty {
        val maxColumns = rows.maxOfOrNull { it.size } ?: 0
        List(maxColumns) { "Column ${it + 1}" }
    }
    val colCount = normalizedHeaders.size
    if (colCount == 0) return state

    val startX = margin
    val tableWidth = pageSize.width - margin * 2
    val colWidth = tableWidth / colCount
    val cellPadding = 6f
    var y = state.y
    var cs = state.contentStream ?: return state
    Log.d("TableDraw", "Drawing table with $colCount columns at Y: $y")

    fun ensureTableSpace(requiredHeight: Float): Boolean {
        if (y - requiredHeight < margin + 10f) {
            cs.close()
            cs = newPage()
            y = pageSize.height - margin - 86f
            return true
        }
        return false
    }

    fun drawHeader() {
        cs.setStrokingColor(
            Color.red(ruleColor) / 255f,
            Color.green(ruleColor) / 255f,
            Color.blue(ruleColor) / 255f
        )
        cs.setLineWidth(0.6f)
        val effectiveHeaderFill = when (tableLayout) {
            TableLayout.JOURNAL_MINIMAL -> Color.WHITE
            TableLayout.DATA_DASHBOARD -> accentColor
            else -> headerFillColor
        }
        cs.setNonStrokingColor(
            Color.red(effectiveHeaderFill) / 255f,
            Color.green(effectiveHeaderFill) / 255f,
            Color.blue(effectiveHeaderFill) / 255f
        )
        val headerHeight = if (tableLayout == TableLayout.DATA_DASHBOARD) 34f else 30f
        cs.addRect(startX, y - headerHeight + 4f, tableWidth, headerHeight)
        if (tableLayout != TableLayout.JOURNAL_MINIMAL) cs.fill()
        if (tableLayout == TableLayout.JOURNAL_MINIMAL) {
            cs.setLineWidth(1f)
            cs.moveTo(startX, y - headerHeight + 4f)
            cs.lineTo(startX + tableWidth, y - headerHeight + 4f)
            cs.stroke()
            cs.moveTo(startX, y + 4f)
            cs.lineTo(startX + tableWidth, y + 4f)
            cs.stroke()
        }

        normalizedHeaders.forEachIndexed { i, header ->
            cs.setStrokingColor(
                Color.red(ruleColor) / 255f,
                Color.green(ruleColor) / 255f,
                Color.blue(ruleColor) / 255f
            )
            cs.setLineWidth(0.6f)
            if (tableLayout != TableLayout.JOURNAL_MINIMAL) {
                cs.addRect(startX + i * colWidth, y - headerHeight + 4f, colWidth, headerHeight)
                cs.stroke()
            }

            val headerLines = wrapPdfCellText(
                sanitizePdfText(header),
                PDType1Font.HELVETICA_BOLD,
                9f,
                colWidth - (cellPadding * 2f)
            ).take(3)
            val headerBaseY = y - 8f
            headerLines.forEachIndexed { lineIndex, line ->
                cs.beginText()
                cs.setFont(PDType1Font.HELVETICA_BOLD, 9f)
                if (tableLayout == TableLayout.DATA_DASHBOARD) {
                    cs.setNonStrokingColor(1f, 1f, 1f)
                } else {
                    cs.setNonStrokingColor(
                        Color.red(accentColor) / 255f,
                        Color.green(accentColor) / 255f,
                        Color.blue(accentColor) / 255f
                    )
                }
                cs.newLineAtOffset(startX + i * colWidth + cellPadding, headerBaseY - (lineIndex * 9.5f))
                cs.showText(line)
                cs.endText()
            }
        }

        y -= headerHeight + 4f
    }

    fun drawRow(row: List<String>) {
        val wrappedCells = List(colCount) { columnIndex ->
            wrapPdfCellText(
                sanitizePdfText(row.getOrNull(columnIndex).orEmpty()),
                PDType1Font.HELVETICA,
                8.5f,
                colWidth - (cellPadding * 2f)
            )
        }
        val maxLines = wrappedCells.maxOfOrNull { it.size }?.coerceAtLeast(1) ?: 1
        val rowHeight = (maxLines * lineSpacing) + 12f
        val pageBreak = ensureTableSpace(rowHeight + 14f)
        if (pageBreak) drawHeader()

        if (tableLayout == TableLayout.CLINICAL_BOXED || tableLayout == TableLayout.DATA_DASHBOARD) {
            cs.setNonStrokingColor(
                Color.red(Color.rgb(248, 250, 252)) / 255f,
                Color.green(Color.rgb(248, 250, 252)) / 255f,
                Color.blue(Color.rgb(248, 250, 252)) / 255f
            )
            cs.addRect(startX, y - rowHeight + 4f, tableWidth, rowHeight)
            cs.fill()
        }

        cs.setStrokingColor(
            Color.red(ruleColor) / 255f,
            Color.green(ruleColor) / 255f,
            Color.blue(ruleColor) / 255f
        )
        cs.setLineWidth(0.6f)
        if (tableLayout != TableLayout.JOURNAL_MINIMAL) {
            cs.addRect(startX, y - rowHeight + 4f, tableWidth, rowHeight)
            cs.stroke()
        } else {
            cs.moveTo(startX, y - rowHeight + 4f)
            cs.lineTo(startX + tableWidth, y - rowHeight + 4f)
            cs.stroke()
        }

        wrappedCells.forEachIndexed { i, lines ->
            if (tableLayout != TableLayout.JOURNAL_MINIMAL) {
                cs.setStrokingColor(
                    Color.red(ruleColor) / 255f,
                    Color.green(ruleColor) / 255f,
                    Color.blue(ruleColor) / 255f
                )
                cs.setLineWidth(0.6f)
                cs.addRect(startX + i * colWidth, y - rowHeight + 4f, colWidth, rowHeight)
                cs.stroke()
            }

            lines.forEachIndexed { lineIndex, line ->
                val textY = y - 8f - (lineIndex * lineSpacing)
                cs.beginText()
                cs.setFont(PDType1Font.HELVETICA, 8.5f)
                cs.setNonStrokingColor(0f)
                cs.newLineAtOffset(startX + i * colWidth + cellPadding, textY)
                cs.showText(line)
                cs.endText()
            }
        }

        y -= rowHeight + 2f
    }

    drawHeader()
    rows.forEach { row -> drawRow(row) }

    footnote?.let {
        val note = "Note: ${sanitizePdfText(it)}"
        val noteLines = wrapPdfCellText(note, PDType1Font.HELVETICA_OBLIQUE, 9f, tableWidth)
        if (ensureTableSpace(noteLines.size * lineSpacing + 10f)) drawHeader()
        y -= 4f
        noteLines.forEach { line ->
            cs.beginText()
            cs.setFont(PDType1Font.HELVETICA_OBLIQUE, 9f)
            cs.setNonStrokingColor(0f)
            cs.newLineAtOffset(startX, y)
            cs.showText(line)
            cs.endText()
            y -= lineSpacing
        }
    }

    return TableDrawingState(y, cs)
}
// Add inside ThesisViewModel class


private fun normalizeAiTable(table: AiTable): ThesisTableJson {
    return try {
        when {
            !table.headers.isNullOrEmpty() && !table.rows.isNullOrEmpty() -> {
                ThesisTableJson(
                    tableNumber = "",
                    title = table.title,
                    headers = table.headers,
                    rows = table.rows.map { row -> row.map { it?.toString() ?: "" } },
                    footnote = null
                )
            }

            !table.data.isNullOrEmpty() -> {
                val headers = table.data.first().keys.toList()
                val rows = table.data.map { row -> headers.map { key -> row[key]?.toString() ?: "" } }
                ThesisTableJson(
                    tableNumber = "",
                    title = table.title,
                    headers = headers,
                    rows = rows,
                    footnote = null
                )
            }

            else -> ThesisTableJson(title = table.title)
        }
    } catch (e: Exception) {
        Log.e("TableParser", "Failed to normalize table ${table.title}", e)
        ThesisTableJson(title = table.title)
    }
}

private fun normalizeResultTable(table: TableJson): ThesisTableJson {
    if (table.headers.isEmpty() && table.rows.isEmpty() && table.data.isNotEmpty()) {
        val headers = table.data.first().keys.toList()
        return ThesisTableJson(
            tableNumber = table.tableNumber,
            title = table.title,
            headers = headers,
            rows = table.data.map { row -> headers.map { header -> row[header]?.toString().orEmpty() } },
            data = table.data,
            footnote = table.footnote
        )
    }

    return ThesisTableJson(
        tableNumber = table.tableNumber,
        title = table.title,
        headers = table.headers,
        rows = table.rows,
        data = table.data,
        footnote = table.footnote
    )
}

private fun normalizeThesisTable(table: ThesisTableJson): ThesisTableJson {
    if (table.headers.isNotEmpty() && table.rows.isNotEmpty()) return table
    if (table.data.isEmpty()) return table

    val headers = table.data.first().keys.toList()
    return table.copy(
        headers = headers,
        rows = table.data.map { row -> headers.map { header -> row[header]?.toString().orEmpty() } }
    )
}

private fun normalizeAiChart(chart: AiChart): ChartJson {
    return try {
        val datasets = chartDatasetsFromRaw(
            title = chart.title,
            labelsHint = chart.labels.orEmpty(),
            valuesHint = chart.values.orEmpty(),
            data = chart.data
        )
        val chartType = inferSupportedChartType(chart.type, chart.chartTemplate, datasets)

        ChartJson(
            chartId = chart.title.lowercase().replace(Regex("[^a-z0-9]+"), "_").trim('_'),
            title = chart.title,
            type = chartType,
            chartTemplate = chart.chartTemplate,
            datasets = datasets,
            options = mapOf("labels" to datasets.firstOrNull()?.labels.orEmpty())
        )
    } catch (e: Exception) {
        Log.e("ChartParser", "Failed to normalize chart ${chart.title}", e)
        ChartJson(title = chart.title, type = chart.type)
    }
}

fun normalizeResultChart(chart: ChartJson): ChartJson {
    return try {
        val datasets = if (chart.datasets.isNotEmpty()) {
            chart.datasets
        } else {
            chartDatasetsFromRaw(
                title = chart.title,
                labelsHint = chart.labels,
                valuesHint = chart.values,
                data = chart.data
            )
        }
        val chartType = inferSupportedChartType(chart.type, chart.chartTemplate, datasets)

        chart.copy(
            chartId = chart.chartId.ifBlank {
                chart.title.lowercase().replace(Regex("[^a-z0-9]+"), "_").trim('_')
            },
            type = chartType,
            chartTemplate = chart.chartTemplate,
            datasets = datasets,
            options = chart.options ?: mapOf("labels" to datasets.firstOrNull()?.labels.orEmpty())
        )
    } catch (e: Exception) {
        Log.e("ChartParser", "Failed to normalize result chart ${chart.title}", e)
        ChartJson(title = chart.title, type = chart.type)
    }
}

private fun inferSupportedChartType(rawType: String, chartTemplate: String, datasets: List<ChartDatasetJson>): String {
    val lower = rawType.lowercase().trim()
    val template = chartTemplate.lowercase().trim()

    when {
        lower in setOf("bar", "line", "pie", "scatter", "horizontal_bar", "histogram") -> return lower
        template.contains("horizontal") -> return "horizontal_bar"
        template.contains("scatter") -> return "scatter"
        template.contains("hist") -> return "histogram"
        template.contains("line") -> return "line"
        template.contains("pie") -> return "pie"
        template.contains("bar") -> return if (template.contains("horizontal")) "horizontal_bar" else "bar"
    }

    return when {
        datasets.size > 1 -> "line"
        datasets.firstOrNull()?.values.orEmpty().size <= 5 -> "pie"
        else -> "bar"
    }
}

private fun parseResultsFromRawJson(rawJson: String): ResultsJson? {
    if (rawJson.isBlank()) return null
    return runCatching {
        val cleaned = extractTopLevelJsonObject(rawJson)
        Gson().fromJson(cleaned, ResultsJson::class.java)
    }.onFailure {
        Log.e("ChartParser", "Failed to parse results rawJson for table/chart restore", it)
    }.getOrNull()
}

private fun formatResultsPreview(results: ResultsJson): String {
    return buildString {
        results.sections.forEach { section ->
            if (section.heading.isNotBlank()) appendLine(section.heading)
            if (section.content.isNotBlank()) appendLine(section.content)
            section.observations.orEmpty()
                .filter { it.isNotBlank() }
                .forEach { appendLine("- $it") }
            appendLine()
        }
        if (results.tables.isNotEmpty()) {
            appendLine("TABLES")
            results.tables.forEach { table -> appendLine("${table.tableNumber}: ${table.title}") }
        }
        if (results.charts.isNotEmpty()) {
            appendLine("CHARTS")
            results.charts.forEach { chart -> appendLine("${chart.chartId}: ${chart.title} (${chart.type})") }
        }
    }.trim()
}

private fun chartDataLabels(data: Any?): List<String> {
    return when (data) {
        is Map<*, *> -> data.keys.map { it.toString() }
        is List<*> -> data.mapIndexedNotNull { index, item ->
            when (item) {
                is AiChartPoint -> item.label
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
                is AiChartPoint -> item.value
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

private fun extractTopLevelJsonObject(text: String): String {
    val trimmed = text.trim()
        .removePrefix("```json")
        .removePrefix("```")
        .removeSuffix("```")
        .trim()

    val first = trimmed.indexOf('{')
    val last = trimmed.lastIndexOf('}')
    return if (first >= 0 && last > first) trimmed.substring(first, last + 1) else trimmed
}

private fun chartPaletteForTheme(theme: PdfThemeStyle): List<Int> {
    return when (theme.chartLayout) {
        ChartLayout.SIMPLE_ACADEMIC -> listOf(
            theme.accentColor,
            Color.parseColor("#16A085"),
            Color.parseColor("#E67E22"),
            Color.parseColor("#8E44AD"),
            Color.parseColor("#C0392B")
        )
        ChartLayout.CLINICAL_MUTED -> listOf(
            theme.accentColor,
            theme.ruleColor,
            Color.parseColor("#6B7280"),
            Color.parseColor("#94A3B8"),
            Color.parseColor("#0F766E")
        )
        ChartLayout.JOURNAL_CLEAN -> listOf(
            Color.parseColor("#111827"),
            Color.parseColor("#4B5563"),
            Color.parseColor("#6B7280"),
            Color.parseColor("#9CA3AF"),
            theme.ruleColor
        )
        ChartLayout.PRESENTATION_BOLD -> listOf(
            theme.accentColor,
            Color.parseColor("#2563EB"),
            Color.parseColor("#F97316"),
            Color.parseColor("#10B981"),
            Color.parseColor("#DB2777")
        )
    }
}


@SuppressLint("Recycle")
suspend fun renderChartToBitmap(
    context: Context,
    chartJson: ChartJson,
    theme: PdfThemeStyle,
    widthPx: Int = 500,
    heightPx: Int = 350
): Bitmap? = withContext(Dispatchers.Main) {
    val normalizedChart = normalizeResultChart(chartJson)
    Log.d(
        "ChartRender",
        """
        Title=${normalizedChart.title}
        Type=${normalizedChart.type}
        Datasets=${normalizedChart.datasets}
        """.trimIndent()
    )
    // 1. Create a container (not attached to any window)
    val container = FrameLayout(context).apply {
        layoutParams = ViewGroup.LayoutParams(widthPx, heightPx)
        setWillNotDraw(false)   // ensure container draws its children
    }

    // 2. Create the chart view based on type
    val chartView: com.github.mikephil.charting.charts.Chart<*> = when (normalizedChart.type.lowercase()) {
        "bar" -> BarChart(context)
        "horizontal_bar" -> HorizontalBarChart(context)
        "line" -> LineChart(context)
        "pie" -> PieChart(context)
        "scatter" -> ScatterChart(context)
        "histogram" -> BarChart(context)
        else -> BarChart(context)
    }

    val datasets = normalizedChart.datasets.ifEmpty { return@withContext null }
    val dataset = datasets.firstOrNull() ?: return@withContext null
    val labels = chartLabels(normalizedChart, dataset)
    val chartPalette = chartPaletteForTheme(theme)

    // 4. Configure chart appearance
    val chartBackground = when (theme.chartLayout) {
        ChartLayout.JOURNAL_CLEAN -> Color.WHITE
        ChartLayout.PRESENTATION_BOLD -> theme.softColor
        else -> theme.footerFillColor
    }
    val gridColor = when (theme.chartLayout) {
        ChartLayout.JOURNAL_CLEAN -> Color.parseColor("#E5E7EB")
        ChartLayout.PRESENTATION_BOLD -> theme.headerFillColor
        else -> theme.softColor
    }
    val axisTextColor = when (theme.chartLayout) {
        ChartLayout.JOURNAL_CLEAN -> Color.parseColor("#111827")
        else -> theme.ruleColor
    }
    chartView.setBackgroundColor(chartBackground)

    when (chartView) {
        is BarChart -> {
            chartView.xAxis.position = XAxis.XAxisPosition.BOTTOM
            chartView.xAxis.labelRotationAngle = -45f
            chartView.xAxis.textSize = 10f
            chartView.xAxis.textColor = axisTextColor
            chartView.axisLeft.textSize = 10f
            chartView.axisLeft.textColor = axisTextColor
            chartView.axisLeft.gridColor = gridColor
            chartView.axisRight.isEnabled = false
            if (labels.isNotEmpty()) {
                chartView.xAxis.valueFormatter = IndexAxisValueFormatter(labels)
                chartView.xAxis.granularity = 1f
            }

            val barWidth = 0.8f / datasets.size.coerceAtLeast(1)
            val barDataSets = datasets.mapIndexed { index, ds ->
                val offset = (index.toFloat() - (datasets.size - 1) / 2f) * barWidth
                BarDataSet(
                    ds.values.mapIndexed { entryIndex, value -> BarEntry(entryIndex.toFloat() + offset, value.toFloat()) },
                    ds.label.ifBlank { "Series ${index + 1}" }
                ).apply {
                    color = chartPalette[index % chartPalette.size]
                    valueTextSize = 10f
                    valueTextColor = theme.accentColor
                }
            }
            chartView.data = BarData(barDataSets).apply {
                this.barWidth = barWidth
            }
        }
        is HorizontalBarChart -> {
            chartView.xAxis.position = XAxis.XAxisPosition.BOTTOM
            chartView.xAxis.labelRotationAngle = -45f
            chartView.xAxis.textSize = 10f
            chartView.xAxis.textColor = axisTextColor
            chartView.axisLeft.textSize = 10f
            chartView.axisLeft.textColor = axisTextColor
            chartView.axisLeft.gridColor = gridColor
            chartView.axisRight.isEnabled = false
            if (labels.isNotEmpty()) {
                chartView.xAxis.valueFormatter = IndexAxisValueFormatter(labels)
                chartView.xAxis.granularity = 1f
            }

            val barWidth = 0.8f / datasets.size.coerceAtLeast(1)
            val barDataSets = datasets.mapIndexed { index, ds ->
                val offset = (index.toFloat() - (datasets.size - 1) / 2f) * barWidth
                BarDataSet(
                    ds.values.mapIndexed { entryIndex, value -> BarEntry(entryIndex.toFloat() + offset, value.toFloat()) },
                    ds.label.ifBlank { "Series ${index + 1}" }
                ).apply {
                    color = chartPalette[index % chartPalette.size]
                    valueTextSize = 10f
                    valueTextColor = theme.accentColor
                }
            }
            chartView.data = BarData(barDataSets).apply {
                this.barWidth = barWidth
            }
        }
        is LineChart -> {
            chartView.xAxis.position = XAxis.XAxisPosition.BOTTOM
            chartView.xAxis.labelRotationAngle = -45f
            chartView.xAxis.textSize = 10f
            chartView.xAxis.textColor = axisTextColor
            chartView.axisLeft.textSize = 10f
            chartView.axisLeft.textColor = axisTextColor
            chartView.axisLeft.gridColor = gridColor
            chartView.axisRight.isEnabled = false
            if (labels.isNotEmpty()) {
                chartView.xAxis.valueFormatter = IndexAxisValueFormatter(labels)
                chartView.xAxis.granularity = 1f
            }

            val lineDataSets = datasets.mapIndexed { index, ds ->
                val entries = ds.values.mapIndexed { entryIndex, value ->
                    Entry(entryIndex.toFloat(), value.toFloat())
                }
                LineDataSet(entries, ds.label.ifBlank { "Series ${index + 1}" }).apply {
                    val color = chartPalette[index % chartPalette.size]
                    this.color = color
                    setCircleColor(color)
                    lineWidth = if (theme.chartLayout == ChartLayout.PRESENTATION_BOLD) 3f else 2f
                    circleRadius = if (theme.chartLayout == ChartLayout.JOURNAL_CLEAN) 2.8f else 4f
                    valueTextSize = 10f
                    valueTextColor = theme.accentColor
                }
            }
            chartView.data = LineData(lineDataSets)
        }
        is ScatterChart -> {
            chartView.xAxis.position = XAxis.XAxisPosition.BOTTOM
            chartView.xAxis.labelRotationAngle = -45f
            chartView.xAxis.textSize = 10f
            chartView.xAxis.textColor = axisTextColor
            chartView.axisLeft.textSize = 10f
            chartView.axisLeft.textColor = axisTextColor
            chartView.axisLeft.gridColor = gridColor
            chartView.axisRight.isEnabled = false
            if (labels.isNotEmpty()) {
                chartView.xAxis.valueFormatter = IndexAxisValueFormatter(labels)
                chartView.xAxis.granularity = 1f
            }

            val scatterSets = datasets.mapIndexed { index, ds ->
                val entries = ds.values.mapIndexed { entryIndex, value ->
                    Entry(entryIndex.toFloat(), value.toFloat())
                }
                ScatterDataSet(entries, ds.label.ifBlank { "Series ${index + 1}" }).apply {
                    color = chartPalette[index % chartPalette.size]
                    setScatterShapeSize(8f)
                    valueTextSize = 10f
                    valueTextColor = theme.accentColor
                }
            }
            chartView.data = ScatterData(scatterSets)
        }
        is PieChart -> {
            chartView.isDrawHoleEnabled = true
            chartView.setHoleColor(android.graphics.Color.TRANSPARENT)

            val pieEntries = dataset.values.mapIndexed { index, value ->
                val sliceLabel = labels.getOrNull(index) ?: "${dataset.label} ${index + 1}"
                PieEntry(value.toFloat(), sliceLabel)
            }
            val pieDataSet = PieDataSet(pieEntries, dataset.label).apply {
                colors = chartPalette
                valueTextSize = 12f
                valueTextColor = theme.accentColor
            }
            chartView.data = MPPieData(pieDataSet)
        }
    }

    chartView.description.isEnabled = false
    chartView.legend.textSize = 12f
    chartView.legend.textColor = if (theme.chartLayout == ChartLayout.JOURNAL_CLEAN) Color.BLACK else theme.accentColor
    chartView.setExtraOffsets(
        16f,
        if (theme.chartLayout == ChartLayout.PRESENTATION_BOLD) 28f else 20f,
        16f,
        28f
    )
    chartView.setTouchEnabled(false)
    chartView.visibility = View.VISIBLE

    // 5. Important: Measure and layout in the correct order
    container.addView(chartView, ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)

    // Measure the container with exact dimensions
    val widthSpec = View.MeasureSpec.makeMeasureSpec(widthPx, View.MeasureSpec.EXACTLY)
    val heightSpec = View.MeasureSpec.makeMeasureSpec(heightPx, View.MeasureSpec.EXACTLY)
    container.measure(widthSpec, heightSpec)
    container.layout(0, 0, container.measuredWidth, container.measuredHeight)

    // Force chart to recalculate its internal layout
    chartView.measure(widthSpec, heightSpec)
    chartView.layout(0, 0, container.measuredWidth, container.measuredHeight)
    chartView.data?.notifyDataChanged()
    chartView.notifyDataSetChanged()
    chartView.invalidate()
    chartView.requestLayout()

    // 6. Draw onto a bitmap
    val bitmap = Bitmap.createBitmap(container.measuredWidth, container.measuredHeight, Bitmap.Config.ARGB_8888)
    val canvas = Canvas(bitmap)
    canvas.drawColor(chartBackground)
    container.draw(canvas)

    // 7. Clean up
    container.removeAllViews()

    // 8. Log success or failure (optional)
    if (bitmap.width == 0 || bitmap.height == 0) {
        Log.e("ChartRender", "Bitmap size zero for chart: ${chartJson.title}")
        null
    } else {
        Log.d("ChartRender", "Successfully rendered chart to bitmap: ${bitmap.width}x${bitmap.height}")
        bitmap
    }
}

private fun chartLabels(chart: ChartJson, dataset: ChartDatasetJson): List<String> {
    if (dataset.labels.isNotEmpty()) return dataset.labels
    val optionLabels = chart.options?.get("labels")
    if (optionLabels is List<*>) return optionLabels.map { it.toString() }
    return List(dataset.values.size) { "${it + 1}" }
}

private fun stripBoldMarkdownForPlainExport(text: String): String {
    val out = StringBuilder()
    var index = 0
    while (index < text.length) {
        val start = text.indexOf("**", startIndex = index)
        if (start < 0) {
            out.append(text.substring(index))
            break
        }
        out.append(text.substring(index, start))
        val end = text.indexOf("**", startIndex = start + 2)
        if (end < 0) {
            out.append(text.substring(start))
            break
        }
        out.append(text.substring(start + 2, end))
        index = end + 2
    }
    return out.toString()
}

private fun sanitizePdfText(text: String): String {
    return stripBoldMarkdownForPlainExport(text)
        .replace("\u03c3", "sigma")
        .replace("\u03a3", "Sigma")
        .replace(Regex("\\s+"), " ")
        .trim()
        .filter { char ->
            runCatching { PDType1Font.HELVETICA.getStringWidth(char.toString()) }.isSuccess
        }
}

private fun wrapPdfCellText(
    text: String,
    font: PDType1Font,
    fontSize: Float,
    maxWidth: Float
): List<String> {
    if (text.isBlank()) return listOf("")
    val words = text.split(Regex("\\s+")).filter { it.isNotBlank() }
    val lines = mutableListOf<String>()
    var currentLine = ""

    fun width(value: String): Float {
        return runCatching { (font.getStringWidth(value) / 1000f) * fontSize }
            .getOrDefault(value.length * fontSize * 0.5f)
    }

    for (word in words) {
        val candidate = if (currentLine.isBlank()) word else "$currentLine $word"
        if (width(candidate) <= maxWidth) {
            currentLine = candidate
        } else {
            if (currentLine.isNotBlank()) lines.add(currentLine)
            currentLine = word
        }
    }
    if (currentLine.isNotBlank()) lines.add(currentLine)
    return lines.ifEmpty { listOf("") }
}
