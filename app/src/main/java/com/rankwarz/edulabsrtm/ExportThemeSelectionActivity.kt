package com.rankwarz.edulabsrtm

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Cloud
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import kotlinx.coroutines.delay
import androidx.compose.ui.Alignment
import androidx.compose.ui.draw.scale
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.rankwarz.edulabsrtm.ui.theme.ThesisExtractorTheme
import com.rankwarz.edulabsrtm.viewmodel.PdfTheme
import kotlinx.coroutines.launch

class ExportThemeSelectionActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val currentTheme = intent.getStringExtra(EXTRA_CURRENT_THEME).orEmpty()
        val thesisTitle = intent.getStringExtra(EXTRA_THESIS_TITLE).orEmpty()
        val previewChapterTitle = intent.getStringExtra(EXTRA_PREVIEW_CHAPTER_TITLE).orEmpty()
        val previewChapterText = intent.getStringExtra(EXTRA_PREVIEW_CHAPTER_TEXT).orEmpty()

        setContent {
            ThesisExtractorTheme(darkTheme = isSystemInDarkTheme()) {
                ExportThemeSelectionScreen(
                    initialSelection = currentTheme,
                    thesisTitle = thesisTitle.ifBlank { "Thesis Report" },
                    previewChapter = ExportPreviewChapter(
                        title = previewChapterTitle.ifBlank { "Generate one normal chapter to preview real text" },
                        text = previewChapterText
                    ),
                    onBack = { finish() },
                    onSelect = { selection ->
                        setResult(
                            Activity.RESULT_OK,
                            Intent().putExtra(EXTRA_SELECTED_THEME, selection)
                        )
                        finish()
                    }
                )
            }
        }
    }

    companion object {
        const val EXTRA_CURRENT_THEME = "extra_current_theme"
        const val EXTRA_SELECTED_THEME = "extra_selected_theme"
        const val EXTRA_THESIS_TITLE = "extra_thesis_title"
        const val EXTRA_PREVIEW_CHAPTER_TITLE = "extra_preview_chapter_title"
        const val EXTRA_PREVIEW_CHAPTER_TEXT = "extra_preview_chapter_text"
    }
}

private data class ExportPreviewChapter(
    val title: String,
    val text: String
)

private data class ExportThemePreviewSpec(
    val theme: PdfTheme,
    val label: String,
    val accent: Color,
    val soft: Color,
    val header: Color,
    val footer: Color,
    val rule: Color,
    val layoutName: String,
    val cover: String,
    val page: String,
    val table: String,
    val chart: String,
    val layoutId: String = ""
)

private data class ExportLayoutOption(
    val id: String,
    val label: String,
    val cover: String,
    val page: String,
    val table: String,
    val chart: String
)

private val exportLayoutOptions = listOf(
    ExportLayoutOption("FORMAL", "Formal Thesis", "Centered university title", "Double academic border", "Full grid tables", "Academic charts"),
    ExportLayoutOption("JOURNAL", "Research Journal", "Manuscript opening", "Thin journal rules", "Minimal tables", "Clean line charts"),
    ExportLayoutOption("CLINICAL", "Clinical Report", "Logo official header", "Clinical left rail", "Boxed findings", "Muted charts"),
    ExportLayoutOption("BINDER", "Official Binder", "Authority cover band", "Binder spine frame", "Registrar grid", "Formal evidence"),
    ExportLayoutOption("DASHBOARD", "Data Dashboard", "Control header", "Metric side rail", "Dashboard blocks", "Bold results"),
    ExportLayoutOption("MINIMAL", "Minimal Journal", "Quiet manuscript", "Whitespace system", "Sparse rules", "Mono charts"),
    ExportLayoutOption("ACADEMIC", "Academic Clinical", "Inset academic page", "Soft paper frame", "Clinical boxes", "Muted comparison"),
    ExportLayoutOption("PREMIUM", "Premium Cover", "Editorial hero cover", "Wide hero band", "Premium table", "Presentation charts"),
    ExportLayoutOption("DEFENSE", "Defense Presentation", "Viva-ready cover", "Slide-inspired chrome", "High contrast data", "Defense charts"),
    ExportLayoutOption("INSTITUTIONAL", "Institutional Report", "Submission header", "Seal-style frame", "Admin report grid", "Clinical report charts"),
    ExportLayoutOption("EDITORIAL", "Editorial Folio", "Magazine-style thesis opener", "Asymmetric folio margins", "Light manuscript tables", "Editorial line charts"),
    ExportLayoutOption("ATLAS", "Atlas Plate", "Plate catalogue identity", "Topographic plate frame", "Specimen data panels", "Plate comparison charts"),
    ExportLayoutOption("EXECUTIVE", "Executive Summary", "Premium boardroom title", "Summary band and side index", "KPI-style tables", "High contrast summaries"),
    ExportLayoutOption("MONOGRAPH", "Classic Monograph", "Traditional book title", "Book-like running rules", "Scholarly grid tables", "Conservative academic charts"),
    ExportLayoutOption("CASEBOOK", "Casebook File", "Case file cover tab", "Clinical dossier header", "Case evidence tables", "Outcome trend blocks"),
    ExportLayoutOption("LABBOOK", "Lab Notebook", "Specimen notebook cover", "Grid-paper research page", "Experiment data sheets", "Lab result charts"),
    ExportLayoutOption("REVIEW", "Systematic Review", "Evidence review opener", "Split evidence manuscript", "PRISMA-style tables", "Evidence synthesis charts"),
    ExportLayoutOption("SIGNATURE", "Signature Portfolio", "Luxury portfolio cover", "Floating folio sheet", "Premium summary tables", "Signature presentation charts"),
    ExportLayoutOption("COMPACT", "Compact Clinical", "Tight clinical header", "Dense information layout", "Compact data grid", "Minimal inline charts"),
    ExportLayoutOption("ELEGANT", "Elegant Academic", "Decorative title spread", "Refined typography rules", "Graceful bordered tables", "Subtle tone charts"),
    ExportLayoutOption("MODERN", "Modern Clean", "Sleek modern cover", "Clean thin rules layout", "Minimal bordered tables", "Bold flat charts"),
    ExportLayoutOption("VINTAGE", "Vintage Classic", "Ornate vintage title", "Decorative double borders", "Classic ruled tables", "Traditional bar charts"),
    ExportLayoutOption("CONTRAST", "High Contrast", "Bold high-impact cover", "Strong thick borders", "High contrast zebra grids", "Vivid saturated charts"),
    ExportLayoutOption("MINIMALIST", "Ultra Minimal", "Bare essential cover", "Maximum whitespace", "Borderless light tables", "Thin line charts only"),
    ExportLayoutOption("GRADIENT", "Gradient Flow", "Gradient hero cover", "Smooth color transitions", "Modern gradient headers", "Gradient filled charts"),
    ExportLayoutOption("NOTEBOOK", "Spiral Notebook", "Notebook cover label", "Red margin + ruled lines", "Handwritten-style tables", "Sketch-style charts"),
    ExportLayoutOption("SLIDES", "Presentation Slides", "Slide-style cover", "Speaker notes footer", "Slide data blocks", "Presentation bold charts"),
    ExportLayoutOption("WIDESCREEN", "Widescreen Format", "Panoramic cover band", "Wide side panel layout", "Wide columnar tables", "Extended horizontal charts"),
    // Academic
    ExportLayoutOption("ABSTRACTA", "Abstract Art", "Geometric art cover", "Asymmetric diagonal rules", "Modern minimalist grid", "Abstract shape charts"),
    ExportLayoutOption("ANTIQUE", "Antique Parchment", "Parchment-style title", "Aged document borders", "Vintage ledger tables", "Sepia-toned charts"),
    ExportLayoutOption("ARGENT", "Silver Professional", "Silver foil title", "Clean metallic rules", "Silver-stripe tables", "Monochromatic charts"),
    ExportLayoutOption("BRONZE", "Bronze Classic", "Bronze emblem cover", "Warm bronze borders", "Bronze-accent grids", "Earthy tone charts"),
    ExportLayoutOption("CAMEO", "Cameo Portrait", "Portrait-style frame", "Elegant oval cutouts", "Rounded corner tables", "Delicate line charts"),
    ExportLayoutOption("CANVAS", "Canvas Texture", "Artists canvas cover", "Textured background rules", "Hand-drawn style tables", "Watercolor charts"),
    ExportLayoutOption("CEDAR", "Cedar Wood", "Wood grain title", "Natural wood borders", "Wood-toned grids", "Earthy bar charts"),
    ExportLayoutOption("CERAMIC", "Ceramic Glaze", "Glazed ceramic cover", "Smooth glossy borders", "Polished surface tables", "Glossy 3D charts"),
    ExportLayoutOption("CHALK", "Chalkboard", "Chalk dust cover", "Chalk-style borders", "Handwritten tables", "Chalk sketch charts"),
    ExportLayoutOption("CLASSICAL", "Classical Scholar", "Greek key motif cover", "Classical column borders", "Doric order tables", "Classic academic charts"),
    // Journal
    ExportLayoutOption("COTTON", "Cotton Soft", "Soft cotton cover", "Gentle rounded borders", "Soft tinted tables", "Pastel tone charts"),
    ExportLayoutOption("CRYSTAL", "Crystal Clear", "Transparent crystal cover", "Clean glass rules", "See-through grids", "Crystal clear charts"),
    ExportLayoutOption("DENIM", "Denim Blue", "Denim textured cover", "Stitched border rules", "Denim stripe tables", "Blue denim charts"),
    ExportLayoutOption("FLINT", "Flint Stone", "Stone-textured cover", "Sharp angular borders", "Stone slab tables", "Flint spark charts"),
    ExportLayoutOption("FOAM", "Foam Green", "Foam wave cover", "Organic rounded borders", "Bubble-style tables", "Wave form charts"),
    ExportLayoutOption("FROST", "Frost Ice", "Frosted glass cover", "Icy cool borders", "Crystal ice tables", "Winter frost charts"),
    ExportLayoutOption("GINGER", "Ginger Spice", "Spice-toned cover", "Warm amber borders", "Golden spice tables", "Saffron tone charts"),
    ExportLayoutOption("HAZEL", "Hazel Natural", "Hazel nut cover", "Nature-inspired borders", "Forest green tables", "Earthy tone charts"),
    ExportLayoutOption("IVORY", "Ivory Classic", "Cream ivory cover", "Elegant ivory borders", "Pearl finish tables", "Ivory tone charts"),
    ExportLayoutOption("LACE", "Lace Delicate", "Lace patterned cover", "Delicate filigree borders", "Fine lace grids", "Elegant thin charts"),
    // Clinical
    ExportLayoutOption("BRICK", "Brick Textured", "Brick wall cover", "Masonry-style borders", "Brick grid tables", "Structural block charts"),
    ExportLayoutOption("CORAL", "Coral Reef", "Underwater coral cover", "Ocean wave borders", "Coral-colored grids", "Reef tone charts"),
    ExportLayoutOption("CORK", "Cork Board", "Cork pinboard cover", "Pin border accents", "Pin-up card tables", "Pushpin charts"),
    ExportLayoutOption("EARTH", "Earth Tone", "Terrestrial globe cover", "Geological strata borders", "Layered earth tables", "Mineral tone charts"),
    ExportLayoutOption("GARNET", "Garnet Red", "Deep garnet cover", "Ruby red borders", "Garnet-accent grids", "Red tone charts"),
    ExportLayoutOption("GRANITE", "Granite Solid", "Granite stone cover", "Stone block borders", "Solid granite tables", "Rock solid charts"),
    ExportLayoutOption("JADE", "Jade Green", "Jade stone cover", "Jade carved borders", "Jade-inlay tables", "Green gem charts"),
    ExportLayoutOption("LEATHER", "Leather Bound", "Leather book cover", "Stitched leather borders", "Embossed leather tables", "Tooled leather charts"),
    ExportLayoutOption("LINEN", "Linen Texture", "Linen woven cover", "Fabric weave borders", "Linen stripe tables", "Woven pattern charts"),
    ExportLayoutOption("MAGMA", "Magma Lava", "Volcanic lava cover", "Molten rock borders", "Lava flow tables", "Eruption pattern charts"),
    // Premium
    ExportLayoutOption("AURORA", "Aurora Gradient", "Aurora borealis cover", "Northern lights header", "Aurora glow tables", "Gradient-filled charts"),
    ExportLayoutOption("BAMBOO", "Bamboo Natural", "Bamboo forest cover", "Bamboo stalk borders", "Bamboo segment tables", "Vertical bamboo charts"),
    ExportLayoutOption("BUBBLE", "Bubble Modern", "Bubble wrap cover", "Circular motif borders", "Bubble cell tables", "Bubble scatter charts"),
    ExportLayoutOption("CARBON", "Carbon Fiber", "Carbon weave cover", "Technical grid borders", "Carbon mesh tables", "Tech-style charts"),
    ExportLayoutOption("CHROME", "Chrome Metallic", "Mirror chrome cover", "Brushed metal borders", "Chrome finish tables", "Metallic bar charts"),
    ExportLayoutOption("CLOUD", "Cloud Light", "Cloud sky cover", "Soft cloud borders", "Light airy tables", "Bubble line charts"),
    ExportLayoutOption("COBALT", "Cobalt Blue", "Deep cobalt cover", "Electric blue borders", "Cobalt shine tables", "Blue intensity charts"),
    ExportLayoutOption("COPPER", "Copper Warm", "Copper patina cover", "Warm copper borders", "Copper-toned grids", "Rustic warmth charts"),
    ExportLayoutOption("GOLD", "Gold Premium", "Gold foil cover", "Golden ratio borders", "Gold-accent tables", "Luxury gold charts"),
    ExportLayoutOption("INDIGO", "Indigo Deep", "Deep indigo cover", "Indigo gradient borders", "Indigo shaded tables", "Twilight tone charts"),
    // Report
    ExportLayoutOption("CHARCOAL", "Charcoal Dark", "Charcoal sketch cover", "Dark mode borders", "High contrast dark tables", "Neon on dark charts"),
    ExportLayoutOption("EBONY", "Ebony Dark", "Ebony wood cover", "Dark elegant borders", "Ebony finish tables", "Midnight tone charts"),
    ExportLayoutOption("GHOST", "Ghost Minimal", "Ghostly transparent cover", "Faded invisible borders", "Phantom light tables", "Ghost line charts"),
    ExportLayoutOption("GLASS", "Glass Transparent", "Clear glass cover", "Glass pane borders", "Frosted glass tables", "Clear lucite charts"),
    ExportLayoutOption("JET", "Jet Black", "Glossy jet cover", "Sleek black borders", "High-gloss black tables", "Luminous color charts"),
    // Book
    ExportLayoutOption("BURLAP", "Burlap Weave", "Burlap textured cover", "Rough woven borders", "Burlap-pattern tables", "Natural fiber charts"),
    ExportLayoutOption("FIESTA", "Fiesta Bright", "Fiesta celebration cover", "Colorful festive borders", "Bright patterned tables", "Festive color charts"),
    ExportLayoutOption("LAVENDER", "Lavender Soft", "Lavender field cover", "Floral soft borders", "Lavender tinted tables", "Purple tone charts"),
    ExportLayoutOption("LEMON", "Lemon Fresh", "Citrus bright cover", "Zesty yellow borders", "Fresh lemon tables", "Citrus burst charts"),
    ExportLayoutOption("LILAC", "Lilac Purple", "Lilac blossom cover", "Purple gradient borders", "Lilac shaded tables", "Amethyst tone charts")
)

private fun combinationSpec(
    colorTheme: PdfTheme,
    layoutId: String,
    remoteLayouts: Map<String, RemoteThemeLayout> = emptyMap()
): ExportThemePreviewSpec {
    val base = colorTheme.selectionSpec()

    // Handle remote (server-synced) layouts — use their actual colors
    if (layoutId.startsWith("SERVER:")) {
        val key = layoutId.removePrefix("SERVER:")
        val remote = remoteLayouts[key]
        if (remote != null) {
            return ExportThemePreviewSpec(
                theme = colorTheme,
                label = "${colorTheme.label} - ${remote.layout_name.ifBlank { key }}",
                accent = parseHexColor(remote.accent_color)?.let { Color(it) } ?: base.accent,
                soft = parseHexColor(remote.soft_color)?.let { Color(it) } ?: base.soft,
                header = parseHexColor(remote.header_fill_color)?.let { Color(it) } ?: base.header,
                footer = parseHexColor(remote.footer_fill_color)?.let { Color(it) } ?: base.footer,
                rule = parseHexColor(remote.rule_color)?.let { Color(it) } ?: base.rule,
                layoutName = remote.layout_name.ifBlank { key },
                cover = remote.cover.ifBlank { "Server-synced layout" },
                page = remote.page.ifBlank { "Custom layout" },
                table = remote.table.ifBlank { "Custom table" },
                chart = remote.chart.ifBlank { "Custom chart" },
                layoutId = layoutId
            )
        }
    }

    val layout = exportLayoutOptions.firstOrNull { it.id == layoutId } ?: exportLayoutOptions.first()
    return base.copy(
        label = "${base.label} - ${layout.label}",
        layoutName = layout.label,
        cover = layout.cover,
        page = layout.page,
        table = layout.table,
        chart = layout.chart,
        layoutId = layout.id
    )
}

private fun defaultLayoutIdForTheme(theme: PdfTheme): String = when (theme) {
    PdfTheme.CLASSIC -> "FORMAL"
    PdfTheme.NAVY -> "JOURNAL"
    PdfTheme.EMERALD -> "CLINICAL"
    PdfTheme.MAROON -> "BINDER"
    PdfTheme.TEAL -> "DASHBOARD"
    PdfTheme.SLATE -> "MINIMAL"
    PdfTheme.OLIVE -> "ACADEMIC"
    PdfTheme.SAND -> "PREMIUM"
    PdfTheme.ROYAL -> "DEFENSE"
    PdfTheme.CRIMSON -> "INSTITUTIONAL"
}

private data class LayoutFamily(
    val id: String,
    val label: String
)

private val exportLayoutFamilies = listOf(
    LayoutFamily("All", "All"),
    LayoutFamily("Academic", "Academic"),
    LayoutFamily("Journal", "Journal"),
    LayoutFamily("Clinical", "Clinical"),
    LayoutFamily("Premium", "Premium"),
    LayoutFamily("Report", "Report"),
    LayoutFamily("Book", "Book"),
    LayoutFamily("Server", "Server")
)

private fun layoutFamilyFor(layoutId: String, remoteLayouts: Map<String, RemoteThemeLayout> = emptyMap()): String {
    val id = layoutId.uppercase()
    if (id.startsWith("SERVER:")) {
        val key = id.removePrefix("SERVER:")
        val remote = remoteLayouts[key]
        return remote?.family?.ifBlank { "Server" } ?: "Server"
    }
    return when (id) {
        "FORMAL", "ACADEMIC", "ELEGANT", "ABSTRACTA", "ANTIQUE", "ARGENT", "BRONZE", "CAMEO", "CANVAS", "CEDAR", "CERAMIC", "CHALK", "CLASSICAL" -> "Academic"
        "JOURNAL", "MINIMAL", "REVIEW", "MINIMALIST", "COTTON", "CRYSTAL", "DENIM", "FLINT", "FOAM", "FROST", "GINGER", "HAZEL", "IVORY", "LACE" -> "Journal"
        "CLINICAL", "BINDER", "INSTITUTIONAL", "CASEBOOK", "COMPACT", "BRICK", "CORAL", "CORK", "EARTH", "GARNET", "GRANITE", "JADE", "LEATHER", "LINEN", "MAGMA" -> "Clinical"
        "DASHBOARD", "PREMIUM", "DEFENSE", "EXECUTIVE", "SIGNATURE", "MODERN", "GRADIENT", "SLIDES", "AURORA", "BAMBOO", "BUBBLE", "CARBON", "CHROME", "CLOUD", "COBALT", "COPPER", "GOLD", "INDIGO" -> "Premium"
        "ATLAS", "LABBOOK", "CONTRAST", "WIDESCREEN", "CHARCOAL", "EBONY", "GHOST", "GLASS", "JET" -> "Report"
        "MONOGRAPH", "EDITORIAL", "VINTAGE", "NOTEBOOK", "BURLAP", "FIESTA", "LAVENDER", "LEMON", "LILAC" -> "Book"
        else -> "Report"
    }
}

private fun PdfTheme.selectionSpec(): ExportThemePreviewSpec = when (this) {
    PdfTheme.CLASSIC -> ExportThemePreviewSpec(this, "Classic - Formal Thesis", Color(0xFF1B3A57), Color(0xFFDDEBF7), Color(0xFFBFD4EA), Color(0xFFEEF5FB), Color(0xFF6E93B8), "Formal frame", "Centered university title", "Double academic border", "Full grid tables", "Academic charts")
    PdfTheme.NAVY -> ExportThemePreviewSpec(this, "Navy - Research Journal", Color(0xFF081C2E), Color(0xFFD5DEEA), Color(0xFFB3C2D3), Color(0xFFEAF0F6), Color(0xFF5F7690), "Research journal", "Manuscript opening", "Thin journal rules", "Minimal tables", "Clean line charts")
    PdfTheme.EMERALD -> ExportThemePreviewSpec(this, "Emerald - Clinical Report", Color(0xFF0A5C4E), Color(0xFFD0F0E9), Color(0xFFA7E1D5), Color(0xFFECFAF6), Color(0xFF48B49E), "Clinical report", "Logo official header", "Clinical left rail", "Boxed findings", "Muted charts")
    PdfTheme.MAROON -> ExportThemePreviewSpec(this, "Maroon - Official Binder", Color(0xFF5C1717), Color(0xFFF4DADA), Color(0xFFEAB6B6), Color(0xFFFFF1F1), Color(0xFFC46E6E), "Official binder", "Authority cover band", "Binder spine frame", "Registrar grid", "Formal evidence")
    PdfTheme.TEAL -> ExportThemePreviewSpec(this, "Teal - Data Dashboard", Color(0xFF075B5B), Color(0xFFD3F3F0), Color(0xFFA9E0DA), Color(0xFFEBFAF8), Color(0xFF45AFA8), "Data dashboard", "Control header", "Metric side rail", "Dashboard blocks", "Bold results")
    PdfTheme.SLATE -> ExportThemePreviewSpec(this, "Slate - Minimal Journal", Color(0xFF1F2A37), Color(0xFFDDE3EA), Color(0xFFBEC9D6), Color(0xFFEEF2F7), Color(0xFF6E7D90), "Minimal journal", "Quiet manuscript", "Whitespace system", "Sparse rules", "Mono charts")
    PdfTheme.OLIVE -> ExportThemePreviewSpec(this, "Olive - Academic Clinical", Color(0xFF3E5121), Color(0xFFE4ECD4), Color(0xFFCFDDAE), Color(0xFFF6FAEC), Color(0xFF8EA35E), "Academic clinical", "Inset academic page", "Soft paper frame", "Clinical boxes", "Muted comparison")
    PdfTheme.SAND -> ExportThemePreviewSpec(this, "Sand - Premium Cover", Color(0xFF6A4B22), Color(0xFFF4E4CA), Color(0xFFE4C18D), Color(0xFFFFF7ED), Color(0xFFB88449), "Premium cover", "Editorial hero cover", "Wide hero band", "Premium table", "Presentation charts")
    PdfTheme.ROYAL -> ExportThemePreviewSpec(this, "Royal - Premium Presentation", Color(0xFF163FA3), Color(0xFFD8E6FF), Color(0xFFB9CEFF), Color(0xFFF5F8FF), Color(0xFF5D86E8), "Defense presentation", "Viva-ready cover", "Slide-inspired chrome", "High contrast data", "Defense charts")
    PdfTheme.CRIMSON -> ExportThemePreviewSpec(this, "Crimson - Institutional Report", Color(0xFF6D1111), Color(0xFFF8D6D6), Color(0xFFEEB0B0), Color(0xFFFFF2F2), Color(0xFFC95D5D), "Institutional report", "Submission header", "Seal-style frame", "Admin report grid", "Clinical report charts")
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ExportThemeSelectionScreen(
    initialSelection: String,
    thesisTitle: String,
    previewChapter: ExportPreviewChapter,
    onBack: () -> Unit,
    onSelect: (String) -> Unit
) {
    val context = LocalContext.current

    var remoteLayouts by remember { mutableStateOf<List<RemoteThemeLayout>>(emptyList()) }

    // Always fetch fresh layouts from server when screen opens
    LaunchedEffect(Unit) {
        val cached = getCachedRemoteThemeLayouts(context)
        if (cached.isNotEmpty()) remoteLayouts = cached
        try {
            val fresh = fetchRemoteThemeLayouts()
            if (fresh.isNotEmpty()) {
                remoteLayouts = fresh
                cacheRemoteThemeLayouts(context, fresh, System.currentTimeMillis())
            }
        } catch (_: Exception) { }
    }

    // Merge built-in layouts with remote server layouts
    val allLayoutOptions = remember(exportLayoutOptions, remoteLayouts) {
        val builtIn = exportLayoutOptions.map { ExportLayoutOption(
            id = it.id,
            label = it.label,
            cover = it.cover,
            page = it.page,
            table = it.table,
            chart = it.chart
        )}
        val remote = remoteLayouts.map { layout ->
            ExportLayoutOption(
                id = "SERVER:${layout.layout_key}",
                label = layout.layout_name.ifBlank { layout.layout_key },
                cover = layout.cover,
                page = layout.page,
                table = layout.table,
                chart = layout.chart
            )
        }
        builtIn + remote
    }

    val remoteLayoutMap = remember(remoteLayouts) {
        remoteLayouts.associateBy { it.layout_key }
    }

    val initialColor = PdfTheme.fromName(initialSelection)
    val initialLayoutToken = initialSelection.substringAfter("|", missingDelimiterValue = "").let { token ->
        if (token.isBlank()) defaultLayoutIdForTheme(initialColor) else token
    }
    var selectedColor by rememberSaveable { mutableStateOf(initialColor.name) }
    var selectedLayout by rememberSaveable { mutableStateOf(initialLayoutToken) }
    var selectedLayoutFamily by rememberSaveable { mutableStateOf(layoutFamilyFor(initialLayoutToken)) }
    val selected = PdfTheme.fromName(selectedColor)
    val selectedSpec = combinationSpec(selected, selectedLayout, remoteLayoutMap)
    val visibleLayouts = allLayoutOptions.filter {
        val family = if (it.id.startsWith("SERVER:")) {
            remoteLayoutMap[it.id.removePrefix("SERVER:")]?.family ?: "Server"
        } else {
            layoutFamilyFor(it.id)
        }
        selectedLayoutFamily == "All" || family == selectedLayoutFamily
    }

    fun buildSelectionValue(): String {
        val colorName = selected.name
        val layoutId = selectedLayout
        if (layoutId.startsWith("SERVER:")) {
            val key = layoutId.removePrefix("SERVER:")
            val remote = remoteLayoutMap[key]
            val label = remote?.layout_name?.trim().orEmpty().ifBlank { key }
            return "${colorName.uppercase()}|SERVER:$key|$label"
        }
        return "$colorName|$layoutId"
    }

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = Color(0xFFF5F7FA)
    ) {
        Column(modifier = Modifier.fillMaxSize()) {
            CenterAlignedTopAppBar(
                title = { Text("Export Design") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    Button(onClick = { onSelect(buildSelectionValue()) }) {
                        Icon(Icons.Default.Check, contentDescription = null)
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Use")
                    }
                }
            )

            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(horizontal = 16.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                item {
                    var carouselIdx by rememberSaveable { mutableIntStateOf(0) }
                    val carouselLayouts = remember(allLayoutOptions) {
                        allLayoutOptions.filter { it.id == selectedLayout || !it.id.startsWith("SERVER:") }
                            .ifEmpty { allLayoutOptions }
                    }
                    val totalCarousel = carouselLayouts.size.coerceAtLeast(1)

                    // Auto-advance timer
                    LaunchedEffect(Unit) {
                        while (true) {
                            delay(5000)
                            carouselIdx = (carouselIdx + 1) % totalCarousel
                        }
                    }

                    LayoutCarousel(
                        currentIndex = carouselIdx,
                        total = totalCarousel,
                        layout = carouselLayouts.getOrNull(carouselIdx),
                        colorTheme = selected,
                        remoteLayoutMap = remoteLayoutMap,
                        onSelect = { id ->
                            selectedLayout = id
                            val family = if (id.startsWith("SERVER:")) {
                                remoteLayoutMap[id.removePrefix("SERVER:")]?.family ?: "Server"
                            } else layoutFamilyFor(id)
                            selectedLayoutFamily = family
                        },
                        onPrev = { carouselIdx = (carouselIdx - 1 + totalCarousel) % totalCarousel },
                        onNext = { carouselIdx = (carouselIdx + 1) % totalCarousel },
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(top = 8.dp)
                    )
                }

                item {
                    CombinationStatusCard(spec = selectedSpec)
                }

                item {
                    ThemeDetailPanel(spec = selectedSpec)
                }

                item {
                    StepHeader("1", "Select layout", "Choose the document structure first")
                }

                item {
                    LayoutFamilyRow(
                        selectedFamily = selectedLayoutFamily,
                        onSelect = { family ->
                            selectedLayoutFamily = family
                        }
                    )
                }

                items(visibleLayouts) { layout ->
                    val spec = combinationSpec(selected, layout.id, remoteLayoutMap)
                    ThemeLayoutCard(
                        spec = spec,
                        selected = layout.id == selectedLayout,
                        onClick = {
                            selectedLayout = layout.id
                            val family = if (layout.id.startsWith("SERVER:")) {
                                remoteLayoutMap[layout.id.removePrefix("SERVER:")]?.family ?: "Server"
                            } else {
                                layoutFamilyFor(layout.id)
                            }
                            selectedLayoutFamily = family
                        }
                    )
                }

                item {
                    StepHeader("2", "Select colour", "Apply the selected palette to this layout")
                }

                items(PdfTheme.entries) { theme ->
                    ThemeColorCard(
                        spec = combinationSpec(theme, selectedLayout, remoteLayoutMap),
                        selected = theme.name == selectedColor,
                        onClick = { selectedColor = theme.name }
                    )
                }

                item {
                    Spacer(modifier = Modifier.height(16.dp))
                }
            }
        }
    }
}

@Composable
private fun StepHeader(number: String, title: String, caption: String) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 4.dp),
        horizontalArrangement = Arrangement.spacedBy(10.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(28.dp)
                .background(Color(0xFF111827), RoundedCornerShape(14.dp)),
            contentAlignment = Alignment.Center
        ) {
            Text(number, style = MaterialTheme.typography.labelMedium, color = Color.White, fontWeight = FontWeight.Bold)
        }
        Column(modifier = Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
            Text(caption, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun LayoutFamilyRow(
    selectedFamily: String,
    onSelect: (String) -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(Color.White, RoundedCornerShape(8.dp))
            .border(1.dp, Color(0xFFDDE3EC), RoundedCornerShape(8.dp))
            .padding(10.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Text(
            text = "Quick filters",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            fontWeight = FontWeight.Bold
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            exportLayoutFamilies.forEach { family ->
                FilterChip(
                    selected = family.id == selectedFamily,
                    onClick = { onSelect(family.id) },
                    label = { Text(family.label, maxLines = 1, overflow = TextOverflow.Ellipsis) }
                )
            }
        }
    }
}

@Composable
private fun LayoutCarousel(
    currentIndex: Int,
    total: Int,
    layout: ExportLayoutOption?,
    colorTheme: PdfTheme,
    remoteLayoutMap: Map<String, RemoteThemeLayout>,
    onSelect: (String) -> Unit,
    onPrev: () -> Unit,
    onNext: () -> Unit,
    modifier: Modifier = Modifier
) {
    val spec = remember(layout, colorTheme, remoteLayoutMap) {
        if (layout != null) combinationSpec(colorTheme, layout.id, remoteLayoutMap)
        else colorTheme.selectionSpec().let { s -> s.copy(layoutName = "All layouts loaded") }
    }
    Card(
        modifier = modifier
            .fillMaxWidth()
            .clickable { layout?.let { onSelect(it.id) } },
        shape = RoundedCornerShape(14.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 8.dp),
        colors = CardDefaults.cardColors(containerColor = spec.footer)
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(260.dp)
                .background(
                    Brush.verticalGradient(listOf(spec.accent.copy(alpha = 0.12f), spec.soft, spec.footer)),
                    RoundedCornerShape(14.dp)
                )
        ) {
            // Animated slide content
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(12.dp)
            ) {
                AnimatedContent(
                    targetState = currentIndex,
                    transitionSpec = {
                        val direction = if (targetState > initialState) 1 else -1
                        (slideInHorizontally(
                            animationSpec = tween(400),
                            initialOffsetX = { fullWidth -> direction * fullWidth }
                        ) + fadeIn(animationSpec = tween(300)))
                            .togetherWith(
                                slideOutHorizontally(
                                    animationSpec = tween(400),
                                    targetOffsetX = { fullWidth -> -direction * fullWidth }
                                ) + fadeOut(animationSpec = tween(300))
                            )
                    },
                    label = "carousel_slide"
                ) { idx ->
                    if (layout != null) {
                        val currentSpec = combinationSpec(colorTheme, layout.id, remoteLayoutMap)
                        CarouselSlideContent(
                            spec = currentSpec,
                            layout = layout,
                            total = total,
                            index = idx
                        )
                    } else {
                        Box(
                            modifier = Modifier.fillMaxSize(),
                            contentAlignment = Alignment.Center
                        ) {
                            Text("No layouts available", style = MaterialTheme.typography.bodyMedium)
                        }
                    }
                }
            }

            // Prev arrow
            IconButton(
                onClick = onPrev,
                modifier = Modifier
                    .align(Alignment.CenterStart)
                    .padding(start = 4.dp)
                    .size(36.dp)
                    .background(Color.Black.copy(alpha = 0.15f), CircleShape)
            ) {
                Icon(
                    Icons.Default.ArrowBack,
                    contentDescription = "Previous",
                    tint = Color.White,
                    modifier = Modifier.size(20.dp)
                )
            }

            // Next arrow
            IconButton(
                onClick = onNext,
                modifier = Modifier
                    .align(Alignment.CenterEnd)
                    .padding(end = 4.dp)
                    .size(36.dp)
                    .background(Color.Black.copy(alpha = 0.15f), CircleShape)
            ) {
                Icon(
                    Icons.Default.ArrowBack,
                    contentDescription = "Next",
                    tint = Color.White,
                    modifier = Modifier.size(20.dp).scale(scaleX = -1f, scaleY = 1f)
                )
            }

            // Dots
            Row(
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .padding(bottom = 8.dp),
                horizontalArrangement = Arrangement.spacedBy(5.dp)
            ) {
                repeat(total.coerceIn(1, 30)) { i ->
                    Box(
                        modifier = Modifier
                            .size(if (i == currentIndex) 20.dp else 7.dp, 7.dp)
                            .background(
                                if (i == currentIndex) spec.accent else spec.rule.copy(alpha = 0.35f),
                                RoundedCornerShape(4.dp)
                            )
                    )
                }
            }

            // Glass gloss overlay
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(
                        Brush.verticalGradient(
                            listOf(Color.White.copy(alpha = 0.08f), Color.Transparent, Color.Black.copy(alpha = 0.05f))
                        )
                    )
            )
        }
    }
}

@Composable
private fun CarouselSlideContent(
    spec: ExportThemePreviewSpec,
    layout: ExportLayoutOption,
    total: Int,
    index: Int
) {
    Row(
        modifier = Modifier.fillMaxSize(),
        horizontalArrangement = Arrangement.spacedBy(14.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        // Layout preview box
        Box(
            modifier = Modifier
                .width(120.dp)
                .aspectRatio(0.707f)
                .background(Color.White, RoundedCornerShape(8.dp))
                .border(1.dp, spec.rule.copy(alpha = 0.15f), RoundedCornerShape(8.dp))
                .padding(4.dp)
        ) {
            PremiumThemePagePreview(
                spec = spec,
                title = spec.layoutName,
                previewChapter = ExportPreviewChapter(spec.page, spec.cover),
                modifier = Modifier.fillMaxSize()
            )
        }

        // Info column
        Column(
            modifier = Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            // Badge
            Box(
                modifier = Modifier
                    .background(spec.accent, RoundedCornerShape(4.dp))
                    .padding(horizontal = 8.dp, vertical = 3.dp)
            ) {
                Text(
                    text = spec.layoutName,
                    style = MaterialTheme.typography.labelSmall,
                    color = Color.White,
                    fontWeight = FontWeight.Bold,
                    maxLines = 1
                )
            }

            // Layout key
            Text(
                text = if (layout.id.startsWith("SERVER:")) layout.id.removePrefix("SERVER:") else layout.id,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = spec.accent,
                maxLines = 1
            )

            // Descriptions
            Text(
                text = "Cover: ${spec.cover}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
            Text(
                text = "Page: ${spec.page}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )

            // Color palette
            Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                listOf(spec.accent, spec.soft, spec.header, spec.footer, spec.rule).forEach { color ->
                    Box(
                        modifier = Modifier
                            .size(16.dp)
                            .background(color, RoundedCornerShape(3.dp))
                            .border(0.5.dp, Color.Black.copy(alpha = 0.08f), RoundedCornerShape(3.dp))
                    )
                }
            }

            // Tap hint
            Text(
                text = "Tap to select this layout",
                style = MaterialTheme.typography.labelSmall,
                color = spec.accent.copy(alpha = 0.6f)
            )
        }
    }
}

@Composable
private fun ThemeHeroPreview(
    spec: ExportThemePreviewSpec,
    thesisTitle: String,
    previewChapter: ExportPreviewChapter,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(
                        Brush.horizontalGradient(listOf(spec.accent, spec.rule, spec.header)),
                        RoundedCornerShape(6.dp)
                    )
                    .border(1.dp, spec.rule.copy(alpha = 0.18f), RoundedCornerShape(6.dp))
                    .padding(12.dp),
                horizontalArrangement = Arrangement.spacedBy(10.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .width(5.dp)
                        .height(46.dp)
                        .background(Color.White.copy(alpha = 0.88f), RoundedCornerShape(3.dp))
                )
                Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                    Text(spec.layoutName, style = MaterialTheme.typography.titleMedium, color = Color.White, fontWeight = FontWeight.Bold)
                    Text(spec.theme.label, style = MaterialTheme.typography.labelMedium, color = Color.White.copy(alpha = 0.82f))
                }
                SelectCheckBadge(spec = spec, selected = true)
            }
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(
                        Brush.verticalGradient(listOf(Color(0xFFE9EDF3), Color(0xFFF8FAFC))),
                        RoundedCornerShape(8.dp)
                    )
                    .border(1.dp, Color.Black.copy(alpha = 0.06f), RoundedCornerShape(8.dp))
                    .padding(horizontal = 18.dp, vertical = 14.dp),
                contentAlignment = Alignment.Center
            ) {
                PremiumThemePagePreview(
                    spec = spec,
                    title = thesisTitle,
                    previewChapter = previewChapter,
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(min = 340.dp, max = 500.dp)
                )
            }
        }
    }
}

@Composable
private fun CombinationStatusCard(spec: ExportThemePreviewSpec) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(Color.White, RoundedCornerShape(8.dp))
            .border(1.dp, Color(0xFFDDE3EC), RoundedCornerShape(8.dp))
            .padding(10.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        CombinationPill("Layout", spec.layoutName, spec.accent, Modifier.weight(1f))
        CombinationPill("Colour", spec.theme.label, spec.rule, Modifier.weight(1f))
    }
}

@Composable
private fun CombinationPill(label: String, value: String, color: Color, modifier: Modifier = Modifier) {
    Row(
        modifier = modifier
            .background(color.copy(alpha = 0.1f), RoundedCornerShape(6.dp))
            .border(1.dp, color.copy(alpha = 0.28f), RoundedCornerShape(6.dp))
            .padding(horizontal = 9.dp, vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(10.dp)
                .background(color, RoundedCornerShape(5.dp))
        )
        Column(modifier = Modifier.weight(1f)) {
            Text(label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(value, style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
    }
}

@Composable
private fun ThemeDetailPanel(spec: ExportThemePreviewSpec) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Box(
                modifier = Modifier
                    .width(5.dp)
                    .height(128.dp)
                    .background(spec.accent, RoundedCornerShape(3.dp))
            )
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                PaletteStrip(spec)
                ThemeDetailRow("Cover", spec.cover)
                ThemeDetailRow("Page", spec.page)
                ThemeDetailRow("Tables", spec.table)
                ThemeDetailRow("Charts", spec.chart)
            }
        }
    }
}

@Composable
private fun ThemeDetailRow(label: String, value: String) {
    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        Text(
            text = label,
            modifier = Modifier.widthIn(min = 56.dp, max = 70.dp),
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
private fun ThemeLayoutCard(
    spec: ExportThemePreviewSpec,
    selected: Boolean,
    onClick: () -> Unit
) {
    val isRemote = spec.layoutId.startsWith("SERVER:")
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .border(
                width = if (selected) 2.dp else 1.dp,
                color = if (selected) spec.accent else Color(0xFFD8DEE8),
                shape = RoundedCornerShape(8.dp)
            ),
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = if (selected) spec.footer else Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = if (selected) 4.dp else 1.dp)
    ) {
        Row(
            modifier = Modifier.padding(12.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .width(4.dp)
                    .height(96.dp)
                    .background(if (selected) spec.accent else Color(0xFFE1E7EF), RoundedCornerShape(3.dp))
            )
            Box(
                modifier = Modifier
                    .width(96.dp)
                    .aspectRatio(0.707f)
                    .background(Color(0xFFE8ECF2), RoundedCornerShape(6.dp))
                    .padding(5.dp)
            ) {
                PremiumThemePagePreview(
                    spec = spec,
                    title = spec.layoutName,
                    previewChapter = ExportPreviewChapter(spec.page, spec.cover),
                    modifier = Modifier.fillMaxSize()
                )
            }
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        spec.layoutName,
                        modifier = Modifier.weight(1f),
                        style = MaterialTheme.typography.titleSmall,
                        color = spec.accent,
                        fontWeight = FontWeight.Bold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                    if (isRemote) {
                        Icon(
                            Icons.Default.Cloud,
                            contentDescription = "Server layout",
                            tint = spec.accent.copy(alpha = 0.6f),
                            modifier = Modifier.size(16.dp)
                        )
                    }
                    Text(
                        if (isRemote) "SERVER" else spec.layoutId,
                        style = MaterialTheme.typography.labelSmall,
                        color = spec.accent,
                        fontWeight = FontWeight.Bold,
                        maxLines = 1
                    )
                }
                Text(spec.page, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 2, overflow = TextOverflow.Ellipsis)
                PaletteStrip(spec)
            }
            SelectCheckBadge(spec = spec, selected = selected)
        }
    }
}

@Composable
private fun ThemeColorCard(
    spec: ExportThemePreviewSpec,
    selected: Boolean,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .border(
                width = if (selected) 2.dp else 1.dp,
                color = if (selected) spec.accent else Color(0xFFD8DEE8),
                shape = RoundedCornerShape(8.dp)
            ),
        shape = RoundedCornerShape(8.dp),
        colors = CardDefaults.cardColors(containerColor = if (selected) spec.footer else Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = if (selected) 4.dp else 1.dp)
    ) {
        Row(
            modifier = Modifier.padding(12.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            ColorPreviewStack(spec)
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(7.dp)
            ) {
                Row(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(spec.theme.label, modifier = Modifier.weight(1f), style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
                    ColorNamePill(spec)
                }
                PaletteStrip(spec)
            }
            SelectCheckBadge(spec = spec, selected = selected)
        }
    }
}

@Composable
private fun ColorPreviewStack(spec: ExportThemePreviewSpec) {
    Box(
        modifier = Modifier
            .size(56.dp)
            .background(spec.footer, RoundedCornerShape(8.dp))
            .border(1.dp, spec.rule.copy(alpha = 0.2f), RoundedCornerShape(8.dp))
            .padding(6.dp)
    ) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(Color.White, RoundedCornerShape(5.dp))
                .border(1.dp, spec.rule.copy(alpha = 0.18f), RoundedCornerShape(5.dp))
        )
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(10.dp)
                .background(spec.accent, RoundedCornerShape(topStart = 5.dp, topEnd = 5.dp))
        )
        Column(
            modifier = Modifier
                .align(Alignment.BottomStart)
                .padding(6.dp),
            verticalArrangement = Arrangement.spacedBy(3.dp)
        ) {
            Box(Modifier.fillMaxWidth(0.72f).height(4.dp).background(spec.header, RoundedCornerShape(2.dp)))
            Box(Modifier.fillMaxWidth(0.48f).height(4.dp).background(spec.rule.copy(alpha = 0.5f), RoundedCornerShape(2.dp)))
        }
    }
}

@Composable
private fun ColorNamePill(spec: ExportThemePreviewSpec) {
    val textColor = if (spec.accent.luminance() > 0.45f) Color(0xFF111827) else Color.White
    Text(
        text = spec.theme.name.lowercase().replaceFirstChar { it.uppercase() },
        modifier = Modifier
            .background(spec.accent, RoundedCornerShape(5.dp))
            .padding(horizontal = 7.dp, vertical = 4.dp),
        style = MaterialTheme.typography.labelSmall,
        color = textColor,
        fontWeight = FontWeight.Bold,
        maxLines = 1
    )
}

@Composable
private fun SelectCheckBadge(spec: ExportThemePreviewSpec, selected: Boolean) {
    Box(
        modifier = Modifier
            .size(28.dp)
            .background(if (selected) spec.accent else Color.Transparent, RoundedCornerShape(14.dp))
            .border(1.dp, if (selected) spec.accent else Color(0xFFC9D1DC), RoundedCornerShape(14.dp)),
        contentAlignment = Alignment.Center
    ) {
        if (selected) {
            Icon(Icons.Default.Check, contentDescription = "Selected", tint = Color.White, modifier = Modifier.size(17.dp))
        }
    }
}

@Composable
private fun PaletteStrip(spec: ExportThemePreviewSpec) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(6.dp)
    ) {
        listOf(spec.accent, spec.header, spec.soft, spec.footer, spec.rule).forEach { color ->
            Box(
                modifier = Modifier
                    .weight(1f)
                    .height(12.dp)
                    .background(color, RoundedCornerShape(3.dp))
                    .border(1.dp, Color.Black.copy(alpha = 0.08f), RoundedCornerShape(3.dp))
            )
        }
    }
}

@Composable
private fun PremiumThemePagePreview(
    spec: ExportThemePreviewSpec,
    title: String,
    previewChapter: ExportPreviewChapter,
    modifier: Modifier = Modifier
) {
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(6.dp),
        shadowElevation = 2.dp,
        color = Color.White
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(0.707f)
                .background(Color.White)
        ) {
            PremiumPageChrome(spec)
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(horizontal = 18.dp, vertical = 16.dp),
                verticalArrangement = Arrangement.spacedBy(7.dp)
            ) {
                val whiteHeader = spec.layoutId in setOf("BINDER", "DASHBOARD", "PREMIUM", "DEFENSE", "INSTITUTIONAL", "ATLAS", "EXECUTIVE", "CASEBOOK", "LABBOOK", "SIGNATURE", "COMPACT", "CONTRAST", "GRADIENT", "NOTEBOOK", "SLIDES", "WIDESCREEN")
                Text(
                    text = spec.layoutName.uppercase(),
                    style = MaterialTheme.typography.labelSmall,
                    color = if (whiteHeader) Color.White else spec.accent,
                    fontWeight = FontWeight.Bold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Text(
                    text = title,
                    style = MaterialTheme.typography.titleSmall,
                    color = if (whiteHeader) Color.White else spec.accent,
                    fontWeight = FontWeight.Bold,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )
                MiniCoverIdentity(spec)
                MiniSectionPreview(spec, previewChapter)
                MiniTablePreview(spec)
                MiniChartPreview(spec)
                MiniFigurePreview(spec)
            }
        }
    }
}

@Composable
private fun PremiumPageChrome(spec: ExportThemePreviewSpec) {
    Canvas(modifier = Modifier.fillMaxSize()) {
        val w = size.width
        val h = size.height
        drawRect(Color.White)
        when (spec.layoutId) {
            "FORMAL" -> {
                drawRect(spec.accent, topLeft = Offset(w * 0.045f, h * 0.035f), size = Size(w * 0.91f, h * 0.93f), style = Stroke(3f))
                drawRect(spec.rule, topLeft = Offset(w * 0.072f, h * 0.06f), size = Size(w * 0.856f, h * 0.88f), style = Stroke(1.4f))
                drawRect(spec.header, topLeft = Offset(w * 0.08f, h * 0.09f), size = Size(w * 0.84f, h * 0.045f))
            }
            "JOURNAL" -> {
                drawRect(spec.footer, topLeft = Offset(w * 0.1f, h * 0.18f), size = Size(w * 0.8f, h * 0.13f))
                drawRect(spec.rule, topLeft = Offset(w * 0.1f, h * 0.12f), size = Size(w * 0.8f, 2f))
                drawRect(spec.rule, topLeft = Offset(w * 0.1f, h * 0.89f), size = Size(w * 0.8f, 2f))
            }
            "CLINICAL" -> {
                drawRect(spec.footer, size = Size(w, h * 0.13f))
                drawRect(spec.accent, size = Size(w * 0.045f, h))
                drawRect(spec.rule, topLeft = Offset(w * 0.1f, h * 0.17f), size = Size(w * 0.78f, 2f))
            }
            "BINDER" -> {
                drawRect(spec.header, size = Size(w, h * 0.12f))
                drawRect(spec.accent, topLeft = Offset(0f, 0f), size = Size(w * 0.07f, h))
                drawRect(spec.accent, topLeft = Offset(w * 0.07f, h * 0.08f), size = Size(w * 0.86f, h * 0.84f), style = Stroke(3f))
            }
            "DASHBOARD" -> {
                drawRect(spec.accent, size = Size(w * 0.14f, h))
                drawRect(spec.soft, topLeft = Offset(w * 0.14f, 0f), size = Size(w * 0.86f, h * 0.18f))
                drawRect(spec.header, topLeft = Offset(w * 0.22f, h * 0.23f), size = Size(w * 0.3f, 7f))
            }
            "MINIMAL" -> {
                drawRect(spec.rule, topLeft = Offset(w * 0.12f, h * 0.11f), size = Size(w * 0.76f, 1.5f))
                drawRect(spec.rule, topLeft = Offset(w * 0.12f, h * 0.9f), size = Size(w * 0.76f, 1.5f))
                drawRect(spec.soft, topLeft = Offset(w * 0.12f, h * 0.72f), size = Size(w * 0.26f, h * 0.11f))
            }
            "ACADEMIC" -> {
                drawRect(spec.soft, topLeft = Offset(w * 0.06f, h * 0.06f), size = Size(w * 0.88f, h * 0.88f))
                drawRect(Color.White, topLeft = Offset(w * 0.09f, h * 0.09f), size = Size(w * 0.82f, h * 0.82f))
                drawRect(spec.accent, topLeft = Offset(w * 0.09f, h * 0.09f), size = Size(w * 0.82f, h * 0.82f), style = Stroke(2.4f))
            }
            "PREMIUM" -> {
                drawRect(spec.footer, size = Size(w, h))
                drawRect(spec.accent, size = Size(w, h * 0.2f))
                drawRect(spec.soft, topLeft = Offset(w * 0.68f, h * 0.2f), size = Size(w * 0.22f, h * 0.7f))
                drawRect(spec.header, topLeft = Offset(w * 0.1f, h * 0.28f), size = Size(w * 0.56f, 8f))
            }
            "DEFENSE" -> {
                drawRect(spec.accent, size = Size(w, h * 0.16f))
                drawRect(spec.footer, topLeft = Offset(w * 0.74f, 0f), size = Size(w * 0.26f, h))
                drawRect(spec.header, topLeft = Offset(w * 0.1f, h * 0.2f), size = Size(w * 0.36f, 7f))
            }
            "INSTITUTIONAL" -> {
                drawRect(spec.footer, topLeft = Offset(w * 0.06f, h * 0.05f), size = Size(w * 0.88f, h * 0.9f))
                drawRect(spec.accent, size = Size(w, h * 0.095f))
                drawRect(spec.accent, topLeft = Offset(w * 0.06f, h * 0.05f), size = Size(w * 0.88f, h * 0.9f), style = Stroke(2.5f))
            }
            "EDITORIAL" -> {
                drawRect(spec.footer, topLeft = Offset(w * 0.08f, 0f), size = Size(w * 0.12f, h))
                drawRect(spec.accent, topLeft = Offset(w * 0.1f, h * 0.08f), size = Size(w * 0.18f, 5f))
                drawRect(spec.rule, topLeft = Offset(w * 0.1f, h * 0.88f), size = Size(w * 0.72f, 2f))
                drawRect(spec.soft, topLeft = Offset(w * 0.64f, h * 0.14f), size = Size(w * 0.18f, h * 0.18f))
            }
            "ATLAS" -> {
                drawRect(spec.accent, size = Size(w, h * 0.12f))
                drawRect(spec.footer, topLeft = Offset(w * 0.08f, h * 0.18f), size = Size(w * 0.84f, h * 0.62f))
                drawRect(spec.accent, topLeft = Offset(w * 0.08f, h * 0.18f), size = Size(w * 0.84f, h * 0.62f), style = Stroke(2.2f))
                drawRect(spec.rule, topLeft = Offset(w * 0.14f, h * 0.25f), size = Size(w * 0.72f, 2f))
                drawRect(spec.header, topLeft = Offset(w * 0.14f, h * 0.7f), size = Size(w * 0.24f, h * 0.07f))
            }
            "EXECUTIVE" -> {
                drawRect(spec.footer, size = Size(w, h))
                drawRect(spec.accent, size = Size(w, h * 0.18f))
                drawRect(spec.soft, topLeft = Offset(w * 0.08f, h * 0.24f), size = Size(w * 0.84f, h * 0.16f))
                drawRect(spec.accent, topLeft = Offset(w * 0.08f, h * 0.24f), size = Size(w * 0.035f, h * 0.16f))
                drawRect(spec.rule, topLeft = Offset(w * 0.72f, h * 0.2f), size = Size(w * 0.055f, h * 0.7f))
            }
            "MONOGRAPH" -> {
                drawRect(spec.soft, topLeft = Offset(w * 0.05f, h * 0.04f), size = Size(w * 0.9f, h * 0.92f))
                drawRect(Color.White, topLeft = Offset(w * 0.08f, h * 0.07f), size = Size(w * 0.84f, h * 0.86f))
                drawRect(spec.rule, topLeft = Offset(w * 0.16f, h * 0.14f), size = Size(w * 0.68f, 2f))
                drawRect(spec.rule, topLeft = Offset(w * 0.16f, h * 0.84f), size = Size(w * 0.68f, 2f))
                drawRect(spec.accent, topLeft = Offset(w * 0.43f, h * 0.1f), size = Size(w * 0.14f, 5f))
            }
            "CASEBOOK" -> {
                drawRect(spec.footer, size = Size(w, h))
                drawRect(Color.White, topLeft = Offset(w * 0.08f, h * 0.08f), size = Size(w * 0.84f, h * 0.84f))
                drawRect(spec.accent, size = Size(w, h * 0.13f))
                drawRect(spec.header, topLeft = Offset(w * 0.66f, h * 0.13f), size = Size(w * 0.22f, h * 0.06f))
                drawRect(spec.rule, topLeft = Offset(w * 0.1f, h * 0.22f), size = Size(w * 0.78f, 2f))
            }
            "LABBOOK" -> {
                drawRect(Color.White, size = Size(w, h))
                val grid = spec.soft.copy(alpha = 0.68f)
                var gx = w * 0.12f
                while (gx < w * 0.88f) {
                    drawLine(grid, Offset(gx, h * 0.18f), Offset(gx, h * 0.86f), strokeWidth = 1f)
                    gx += w * 0.08f
                }
                var gy = h * 0.2f
                while (gy < h * 0.86f) {
                    drawLine(grid, Offset(w * 0.1f, gy), Offset(w * 0.9f, gy), strokeWidth = 1f)
                    gy += h * 0.055f
                }
                drawRect(spec.accent, topLeft = Offset(w * 0.1f, h * 0.08f), size = Size(w * 0.8f, h * 0.07f))
                drawRect(spec.header, topLeft = Offset(w * 0.1f, h * 0.2f), size = Size(w * 0.24f, 7f))
            }
            "REVIEW" -> {
                drawRect(Color.White, size = Size(w, h))
                drawRect(spec.soft, topLeft = Offset(w * 0.1f, h * 0.18f), size = Size(w * 0.8f, h * 0.08f))
                drawRect(spec.accent, topLeft = Offset(w * 0.1f, h * 0.14f), size = Size(w * 0.2f, 5f))
                drawLine(spec.rule, Offset(w * 0.1f, h * 0.12f), Offset(w * 0.9f, h * 0.12f), strokeWidth = 2f)
                drawLine(spec.rule, Offset(w * 0.5f, h * 0.3f), Offset(w * 0.5f, h * 0.86f), strokeWidth = 1.4f)
                drawLine(spec.rule, Offset(w * 0.1f, h * 0.88f), Offset(w * 0.9f, h * 0.88f), strokeWidth = 2f)
            }
            "SIGNATURE" -> {
                drawRect(spec.footer, size = Size(w, h))
                drawRect(Color.White, topLeft = Offset(w * 0.08f, h * 0.08f), size = Size(w * 0.84f, h * 0.82f))
                drawRect(spec.accent, topLeft = Offset(w * 0.08f, h * 0.08f), size = Size(w * 0.08f, h * 0.22f))
                drawRect(spec.header, topLeft = Offset(w * 0.22f, h * 0.15f), size = Size(w * 0.56f, 7f))
                drawRect(spec.rule, topLeft = Offset(w * 0.08f, h * 0.08f), size = Size(w * 0.84f, h * 0.82f), style = Stroke(2f))
                drawRect(spec.soft, topLeft = Offset(w * 0.7f, h * 0.62f), size = Size(w * 0.14f, h * 0.16f))
            }
            "COMPACT" -> {
                drawRect(spec.accent, topLeft = Offset(0f, 0f), size = Size(w, h * 0.06f))
                drawRect(spec.rule, topLeft = Offset(0f, h * 0.92f), size = Size(w, 2f))
                drawRect(spec.soft, topLeft = Offset(w * 0.04f, h * 0.1f), size = Size(3f, h * 0.78f))
            }
            "ELEGANT" -> {
                drawRect(spec.accent, topLeft = Offset(w * 0.08f, h * 0.07f), size = Size(w * 0.84f, 2f))
                drawRect(spec.rule, topLeft = Offset(w * 0.08f, h * 0.1f), size = Size(w * 0.84f, 1.2f))
                drawRect(spec.soft, topLeft = Offset(w * 0.08f, h * 0.88f), size = Size(w * 0.84f, h * 0.04f))
                drawRect(spec.accent, topLeft = Offset(w * 0.08f, h * 0.88f), size = Size(w * 0.06f, h * 0.04f))
            }
            "MODERN" -> {
                drawRect(spec.accent, topLeft = Offset(0f, 0f), size = Size(w, 3f))
                drawRect(spec.rule, topLeft = Offset(0f, h * 0.9f), size = Size(w, 1.5f))
                drawRect(spec.header, topLeft = Offset(w * 0.9f, h * 0.12f), size = Size(5f, h * 0.7f))
            }
            "VINTAGE" -> {
                drawRect(spec.accent, topLeft = Offset(w * 0.04f, h * 0.03f), size = Size(w * 0.92f, h * 0.94f), style = Stroke(2.5f))
                drawRect(spec.rule, topLeft = Offset(w * 0.07f, h * 0.06f), size = Size(w * 0.86f, h * 0.88f), style = Stroke(1f))
                val corner = w * 0.02f
                drawRect(spec.accent, topLeft = Offset(w * 0.04f - corner, h * 0.03f - corner), size = Size(corner * 3, corner * 3))
                drawRect(spec.accent, topLeft = Offset(w * 0.96f - corner * 2, h * 0.03f - corner), size = Size(corner * 3, corner * 3))
                drawRect(spec.accent, topLeft = Offset(w * 0.04f - corner, h * 0.97f - corner * 2), size = Size(corner * 3, corner * 3))
                drawRect(spec.accent, topLeft = Offset(w * 0.96f - corner * 2, h * 0.97f - corner * 2), size = Size(corner * 3, corner * 3))
            }
            "CONTRAST" -> {
                drawRect(spec.accent, topLeft = Offset(0f, 0f), size = Size(w * 0.08f, h))
                drawRect(spec.accent, topLeft = Offset(0f, 0f), size = Size(w, h * 0.1f))
                drawRect(spec.rule, topLeft = Offset(0f, h * 0.95f), size = Size(w, 5f))
                drawRect(spec.header, topLeft = Offset(w * 0.15f, h * 0.15f), size = Size(w * 0.7f, h * 0.04f))
            }
            "MINIMALIST" -> {
                drawRect(spec.rule, topLeft = Offset(w * 0.1f, h * 0.06f), size = Size(w * 0.8f, 1f))
                drawRect(spec.accent, topLeft = Offset(w * 0.9f, h * 0.9f), size = Size(w * 0.06f, 3f))
            }
            "GRADIENT" -> {
                drawRect(spec.accent, size = Size(w, h * 0.12f))
                drawRect(spec.rule, topLeft = Offset(0f, h * 0.88f), size = Size(w, h * 0.04f))
                drawRect(spec.soft, topLeft = Offset(w * 0.04f, h * 0.16f), size = Size(w * 0.06f, h * 0.68f))
            }
            "NOTEBOOK" -> {
                drawRect(Color.White, size = Size(w, h))
                val redLine = Color(android.graphics.Color.parseColor("#CC3333"))
                drawRect(redLine, topLeft = Offset(w * 0.1f, h * 0.08f), size = Size(2f, h * 0.84f))
                drawRect(spec.accent, topLeft = Offset(0f, 0f), size = Size(w, h * 0.06f))
                var gy = h * 0.16f
                while (gy < h * 0.9f) {
                    drawLine(spec.soft.copy(alpha = 0.4f), Offset(w * 0.14f, gy), Offset(w * 0.92f, gy), strokeWidth = 1f)
                    gy += h * 0.04f
                }
            }
            "SLIDES" -> {
                drawRect(Color.White, size = Size(w, h))
                drawRect(spec.accent, topLeft = Offset(0f, 0f), size = Size(w, 2f))
                drawRect(spec.footer, topLeft = Offset(0f, h * 0.88f), size = Size(w, h * 0.12f))
                drawRect(spec.accent, topLeft = Offset(w * 0.05f, h * 0.91f), size = Size(w * 0.15f, 5f))
                drawRect(spec.rule, topLeft = Offset(w * 0.22f, h * 0.91f), size = Size(w * 0.08f, 5f))
                drawRect(spec.header, topLeft = Offset(w * 0.32f, h * 0.91f), size = Size(w * 0.08f, 5f))
            }
            "WIDESCREEN" -> {
                drawRect(spec.footer, size = Size(w, h))
                drawRect(spec.accent, topLeft = Offset(0f, 0f), size = Size(w, h * 0.09f))
                drawRect(Color.White, topLeft = Offset(w * 0.06f, h * 0.13f), size = Size(w * 0.64f, h * 0.78f))
                drawRect(spec.soft, topLeft = Offset(w * 0.72f, h * 0.13f), size = Size(w * 0.24f, h * 0.78f))
                drawRect(spec.header, topLeft = Offset(w * 0.1f, h * 0.2f), size = Size(w * 0.52f, h * 0.035f))
            }
        }
    }
}

@Composable
private fun MiniCoverIdentity(spec: ExportThemePreviewSpec) {
    val whiteSurface = spec.layoutId in setOf("BINDER", "DASHBOARD", "PREMIUM", "DEFENSE", "INSTITUTIONAL", "ATLAS", "EXECUTIVE", "CASEBOOK", "LABBOOK", "SIGNATURE", "COMPACT", "CONTRAST", "GRADIENT", "NOTEBOOK", "SLIDES", "WIDESCREEN")
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(if (whiteSurface) Color.White.copy(alpha = 0.92f) else spec.footer, RoundedCornerShape(5.dp))
            .padding(7.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(28.dp)
                .background(spec.accent, RoundedCornerShape(if (spec.layoutId in setOf("JOURNAL", "MINIMAL", "EDITORIAL", "MONOGRAPH", "REVIEW", "LABBOOK")) 2.dp else 14.dp))
        )
        Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Box(Modifier.fillMaxWidth(0.72f).height(5.dp).background(spec.accent.copy(alpha = 0.85f), RoundedCornerShape(2.dp)))
            Box(Modifier.fillMaxWidth(0.48f).height(4.dp).background(spec.rule.copy(alpha = 0.38f), RoundedCornerShape(2.dp)))
        }
        Box(Modifier.width(34.dp).height(18.dp).background(spec.header, RoundedCornerShape(4.dp)))
    }
}

@Composable
private fun MiniSectionPreview(spec: ExportThemePreviewSpec, previewChapter: ExportPreviewChapter) {
    val boxed = spec.layoutId in setOf("CLINICAL", "INSTITUTIONAL", "DASHBOARD", "ACADEMIC", "PREMIUM", "DEFENSE", "ATLAS", "EXECUTIVE", "CASEBOOK", "LABBOOK", "SIGNATURE", "COMPACT", "ELEGANT", "CONTRAST", "GRADIENT", "SLIDES", "WIDESCREEN")
    val previewLines = previewChapter.text
        .lines()
        .map { it.trim() }
        .filter { it.isNotBlank() }
        .ifEmpty {
            listOf(
                "Complete at least one normal chapter to preview real exported text.",
                "Title, certificate, consent, proforma, and references are excluded."
            )
        }
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(min = 86.dp, max = 128.dp)
            .background(if (boxed) spec.soft else Color.Transparent, RoundedCornerShape(4.dp))
            .then(if (boxed) Modifier.border(1.dp, spec.rule.copy(alpha = 0.16f), RoundedCornerShape(4.dp)) else Modifier)
            .padding(7.dp),
        verticalArrangement = Arrangement.spacedBy(3.dp)
    ) {
        Text(
            text = previewChapter.title,
            style = MaterialTheme.typography.labelSmall,
            color = spec.accent,
            fontWeight = FontWeight.Bold,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis
        )
        previewLines.take(4).forEach { line ->
            Text(
                text = line,
                style = MaterialTheme.typography.labelSmall,
                color = Color(0xFF222222),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
        }
    }
}

@Composable
private fun MiniTablePreview(spec: ExportThemePreviewSpec) {
    val journal = spec.layoutId in setOf("JOURNAL", "MINIMAL", "EDITORIAL", "MONOGRAPH", "REVIEW", "MINIMALIST", "VINTAGE")
    val dashboard = spec.layoutId in setOf("DASHBOARD", "PREMIUM", "DEFENSE", "ATLAS", "EXECUTIVE", "CASEBOOK", "LABBOOK", "SIGNATURE", "COMPACT", "MODERN", "CONTRAST", "GRADIENT", "NOTEBOOK", "SLIDES", "WIDESCREEN")
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, if (journal) spec.rule.copy(alpha = 0.35f) else spec.accent.copy(alpha = 0.45f), RoundedCornerShape(if (dashboard) 5.dp else 0.dp))
            .background(if (dashboard) spec.footer else Color.White, RoundedCornerShape(if (dashboard) 5.dp else 0.dp))
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(if (journal) Color.White else spec.accent)
                .padding(5.dp),
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            repeat(3) { Box(Modifier.weight(1f).height(5.dp).background(if (journal) spec.accent else Color.White, RoundedCornerShape(2.dp))) }
        }
        repeat(if (dashboard) 2 else 3) { row ->
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(if (!journal && row % 2 == 0) spec.footer else Color.White)
                    .padding(5.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                repeat(3) { Box(Modifier.weight(1f).height(4.dp).background(spec.rule.copy(alpha = 0.32f), RoundedCornerShape(2.dp))) }
            }
        }
    }
}

@Composable
private fun MiniChartPreview(spec: ExportThemePreviewSpec) {
    val chartColors = listOf(spec.accent, spec.rule, Color(0xFFE67E22), Color(0xFF16A085))
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(54.dp)
            .background(if (spec.layoutId in setOf("DASHBOARD", "PREMIUM", "DEFENSE", "ATLAS", "EXECUTIVE", "CASEBOOK", "LABBOOK", "SIGNATURE", "COMPACT", "MODERN", "CONTRAST", "GRADIENT", "NOTEBOOK", "SLIDES", "WIDESCREEN")) spec.soft else spec.footer, RoundedCornerShape(3.dp))
            .padding(8.dp),
        horizontalArrangement = Arrangement.spacedBy(7.dp),
        verticalAlignment = Alignment.Bottom
    ) {
        chartColors.forEachIndexed { index, color ->
            if (spec.layoutId in setOf("JOURNAL", "MINIMAL", "EDITORIAL", "MONOGRAPH", "REVIEW", "MINIMALIST", "VINTAGE", "ELEGANT")) {
                Canvas(Modifier.weight(1f).height(38.dp)) {
                    val y = size.height - (index * size.height * 0.18f) - 8f
                    drawLine(color, Offset(0f, y), Offset(size.width, y - 10f), strokeWidth = 4f)
                    drawCircle(color, radius = 5f, center = Offset(size.width * 0.72f, y - 7f))
                }
            } else {
                Box(Modifier.weight(1f).height((16 + index * 7).dp).background(color, RoundedCornerShape(topStart = 3.dp, topEnd = 3.dp)))
            }
        }
    }
}

@Composable
private fun MiniFigurePreview(spec: ExportThemePreviewSpec) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(48.dp)
            .background(Brush.horizontalGradient(listOf(spec.footer, if (spec.layoutId in setOf("DASHBOARD", "PREMIUM", "DEFENSE", "ATLAS", "EXECUTIVE", "CASEBOOK", "LABBOOK", "SIGNATURE", "COMPACT", "MODERN", "CONTRAST", "GRADIENT", "NOTEBOOK", "SLIDES", "WIDESCREEN")) spec.soft else Color.White)))
            .border(1.dp, spec.rule.copy(alpha = 0.25f))
            .padding(7.dp)
    ) {
        Box(Modifier.size(34.dp).background(spec.header, RoundedCornerShape(4.dp)))
        Column(
            modifier = Modifier
                .padding(start = 44.dp)
                .align(Alignment.CenterStart),
            verticalArrangement = Arrangement.spacedBy(5.dp)
        ) {
            Box(Modifier.fillMaxWidth(0.54f).height(5.dp).background(spec.accent, RoundedCornerShape(2.dp)))
            Box(Modifier.fillMaxWidth(0.78f).height(4.dp).background(spec.rule.copy(alpha = 0.34f), RoundedCornerShape(2.dp)))
        }
    }
}
